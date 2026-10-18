#!/usr/bin/env python3
"""
微信本地数据库离线解密 / 内容抽取（只读，不改动任何微信数据）。

背景
----
`wechat-cli history` 只输出「时间 + 发送者 + 渲染后的内容」。遇到它解析不了的
消息类型时，会输出一句兜底文案：

    当前微信版本不支持展示该内容，请升级至最新版本。

这句话**不是微信存的内容**（实测在 17 个本地库里都搜不到，`wechat-cli search`
也命中 0）。真正的内容仍可能在库里，只是 wechat-cli 没能解码。

本脚本绕过 wechat-cli 的渲染层，直接解密本地库并抽取原始内容。

已知可用的解密参数（微信 4.1.15 / macOS）
----------------------------------------
- 密钥：`~/.wechat-cli/all_keys.json`（由 `sudo wechat-cli init` 生成，按库给 64 hex）
- 算法：AES-256-CBC，**原始密钥**（不做 PBKDF2）
- 页大小 4096，reserve 80（16B IV + 64B HMAC-SHA512）
- 第 1 页：前 16 字节为 salt（明文），密文从 16 开始；其余页密文从 0 开始
- IV 位于每页 `page_size - reserve` 处

⚠️ 该参数对大多数库有效（已实测 message_0 / message_fts / favorite / contact /
sns / session 等），但存在两个已知限制：

1. **这些 `.db` 不是原生 SQLCipher SQLite 布局**——解密后的页首字节不是 SQLite
   的 b-tree 页类型（2/5/10/13），也拿不到 `SQLite format 3` 魔数（对照组
   `message_0.db` 同样如此，而它的 `<msg>` XML 确实能完整解出）。所以别指望
   「解密 → 拼回合法 .db → 用 sqlite3 查询」这条路，本脚本走的是**字节流抽取**。
2. `message_resource.db` 用同一参数解不开（输出近似随机）；已排除密钥映射错误
   （17 个库的密钥全部互试过）、PBKDF2 派生、以及 IV 位于页首/页尾的各种组合。
   它的密钥可能已轮换，而 `~/.wechat-cli/all_keys.json` 是旧文件（root 所有，
   由 `sudo wechat-cli init` 生成）——**建议用 `sudo wechat-cli init --force`
   重新提取一次密钥**后再试。
   `media_0.db` 用 reserve=64 可解，但内容是语音消息表 `VoiceInfo`，与链接类消息无关。

用法
----
    # 列出可解的库及其内容特征
    python3 wechat_db_dump.py --scan

    # 抽取某个库里所有 <msg>...</msg> 原始 XML
    python3 wechat_db_dump.py --db message/message_0.db --mode msgs

    # 抽取所有 URL（去重）
    python3 wechat_db_dump.py --db message/message_fts.db --mode urls

    # 全文检索（明文关键词）
    python3 wechat_db_dump.py --db message/message_0.db --mode grep --keyword 不支持
"""

import argparse
import json
import os
import re
import sys

DEFAULT_KEYS = os.path.expanduser("~/.wechat-cli/all_keys.json")
DEFAULT_DB_DIR = os.path.expanduser(
    "~/Library/Containers/com.tencent.xinWeChat/Data/Documents/"
    "xwechat_files/wpppj001_1414/db_storage"
)

PAGE_SIZE = 4096
RESERVE = 80  # 16B IV + 64B HMAC-SHA512


def load_keys(path):
    with open(path) as fh:
        return json.load(fh)


def decrypt_db(path, key_hex, page_size=PAGE_SIZE, reserve=RESERVE):
    """解密整个库，返回拼接后的明文（每页 page_size-reserve 字节）。"""
    from Crypto.Cipher import AES

    key = bytes.fromhex(key_hex)
    data = open(path, "rb").read()
    npages = len(data) // page_size
    out = bytearray()
    for i in range(npages):
        page = data[i * page_size:(i + 1) * page_size]
        skip = 16 if i == 0 else 0
        ct = page[skip:page_size - reserve]
        iv = page[page_size - reserve:page_size - reserve + 16]
        if len(iv) < 16 or not ct or len(ct) % 16:
            continue
        out += AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
    return bytes(out), npages


def looks_decrypted(plain):
    """粗判解密是否成功：正常明文有较多 0x00 且含可读结构。"""
    if not plain:
        return False
    zeros = plain.count(b"\x00") / len(plain)
    return zeros > 0.10 and (plain.count(b"http") + plain.count(b"<msg")) > 0


def extract_msgs(plain):
    """抽取 <msg ...> 片段。

    注意：记录可能跨页，`</msg>` 常被页边界截断（实测 favorite.db 有 776 个
    `<msg` 但 0 个完整块）。因此这里优先取闭合标签，取不到就截到下一个
    `<msg` 之前或固定长度，保证能拿到可用内容。
    """
    out = []
    for m in re.finditer(rb"<msg[^>]*>", plain):
        start = m.start()
        end = plain.find(b"</msg>", m.end())
        if end < 0:
            nxt = plain.find(b"<msg", m.end())
            end = nxt if nxt > 0 else min(len(plain), start + 1200)
        else:
            end += len(b"</msg>")
        out.append(plain[start:min(end, start + 4000)])
    return out


def extract_urls(plain, min_len=10):
    seen, out = set(), []
    pattern = rb"https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]{" + str(min_len).encode() + rb",180}"
    for m in re.finditer(pattern, plain):
        u = m.group(0).decode("utf-8", "ignore").rstrip(".,)")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def cmd_scan(keys, db_dir):
    print(f"{'库':<34}{'大小':>9}{'解密':>6}{'<msg>':>8}{'http':>7}{'URL去重':>9}")
    for rel in sorted(keys):
        path = os.path.join(db_dir, rel)
        if not os.path.exists(path):
            continue
        try:
            plain, _ = decrypt_db(path, keys[rel]["enc_key"])
        except Exception as exc:
            print(f"{rel:<34}{os.path.getsize(path)//1024:>7}KB   失败  {exc}")
            continue
        ok = looks_decrypted(plain)
        msgs = plain.count(b"<msg")
        http = plain.count(b"http")
        urls = len(extract_urls(plain)) if ok else 0
        print(f"{rel:<34}{os.path.getsize(path)//1024:>7}KB{'✅' if ok else '❌':>5}"
              f"{msgs:>8}{http:>7}{urls:>9}")


def main():
    ap = argparse.ArgumentParser(description="微信本地数据库离线解密 / 内容抽取（只读）")
    ap.add_argument("--keys", default=DEFAULT_KEYS, help="all_keys.json 路径")
    ap.add_argument("--db-dir", default=DEFAULT_DB_DIR, help="db_storage 目录")
    ap.add_argument("--db", help="要处理的库，如 message/message_0.db")
    ap.add_argument("--mode", choices=["scan", "msgs", "urls", "grep"], default="scan")
    ap.add_argument("--scan", action="store_true", help="等价于 --mode scan")
    ap.add_argument("--keyword", help="--mode grep 时的关键词")
    ap.add_argument("--limit", type=int, default=50, help="输出条数上限")
    ap.add_argument("--output", help="写入文件而不是 stdout")
    args = ap.parse_args()

    if not os.path.exists(args.keys):
        print(f"找不到密钥文件：{args.keys}\n请先执行：sudo wechat-cli init", file=sys.stderr)
        return 2

    keys = load_keys(args.keys)

    if args.mode == "scan":
        cmd_scan(keys, args.db_dir)
        return 0

    if not args.db:
        print("--mode 非 scan 时必须指定 --db", file=sys.stderr)
        return 2
    if args.db not in keys:
        print(f"密钥文件里没有 {args.db}", file=sys.stderr)
        return 2

    path = os.path.join(args.db_dir, args.db)
    if not os.path.exists(path):
        print(f"库不存在：{path}", file=sys.stderr)
        return 2

    plain, npages = decrypt_db(path, keys[args.db]["enc_key"])
    if not looks_decrypted(plain):
        print(f"⚠️ {args.db} 解密结果不像有效明文（zeros={plain.count(b'\\x00')/max(1,len(plain)):.2f}），"
              "可能该库用了不同的派生参数", file=sys.stderr)

    lines = []
    if args.mode == "msgs":
        blocks = extract_msgs(plain)
        lines.append(f"# {args.db}：{npages} 页，抽取到 {len(blocks)} 个完整 <msg> 块")
        for b in blocks[: args.limit]:
            lines.append("")
            lines.append(b.decode("utf-8", "replace"))
    elif args.mode == "urls":
        urls = extract_urls(plain)
        lines.append(f"# {args.db}：去重后 {len(urls)} 个 URL")
        lines.extend(urls[: args.limit])
    elif args.mode == "grep":
        if not args.keyword:
            print("--mode grep 需要 --keyword", file=sys.stderr)
            return 2
        kw = args.keyword.encode()
        hits, start = [], 0
        while len(hits) < args.limit:
            pos = plain.find(kw, start)
            if pos < 0:
                break
            seg = plain[max(0, pos - 200): pos + 400].decode("utf-8", "replace")
            seg = "".join(ch if (ch.isprintable() or ch in "\n\t") else "·" for ch in seg)
            hits.append(f"--- @ {pos}\n{seg.strip()}")
            start = pos + 1
        lines.append(f"# {args.db}：关键词 {args.keyword!r} 命中 {len(hits)} 处（上限 {args.limit}）")
        lines.extend(hits)

    text = "\n".join(lines)
    if args.output:
        with open(args.output, "w") as fh:
            fh.write(text)
        print(f"已写入 {args.output}（{len(text)} 字符）")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
