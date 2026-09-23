#!/usr/bin/env python3
"""
微信 V2 图片解密工具（macOS 优化版）— 支持离线磁盘派生密钥

核心算法（来自 r266-tech/wxkey）：
  aes_key = hex(MD5(str(code) + wxid))[:16]
  xor_key = code & 0xFF
  code    = 第一个 key_{code}_{rest}.statistic 文件名段（uint32）
  wxid    = xwechat_files 子目录名（形如 <wxid>_<hex4>，末尾 _hex4 自动剥离）

优势：
  ✅ 完全无需 sudo、进程内存访问或代码重签名
  ✅ 派生密钥缓存到 ~/.cache/wechat-v2-decrypt/image_key.json，下次直接复用
  ✅ 失败时回退到传统 --aes-key 手动指定模式

用法：
  # 1. 自动派生（推荐，无需任何权限）
  python3 wechat_v2_image_decrypt.py --tgo

  # 2. 解密指定月份
  python3 wechat_v2_image_decrypt.py --tgo --months 2026-07

  # 3. 手动指定密钥（兼容旧模式）
  python3 wechat_v2_image_decrypt.py --aes-key f9d50efd079ab290 --xor-key 0x60

  # 4. 派生并显示密钥（不解密）
  python3 wechat_v2_image_decrypt.py --derive-only
"""

import os
import sys
import glob
import struct
import json
import argparse
import hashlib
import re
from datetime import datetime
from pathlib import Path

# V2 格式常量
V2_MAGIC_FULL = b'\x07\x08V2\x08\x07'
V1_MAGIC_FULL = b'\x07\x08V1\x08\x07'
V1_FIXED_KEY = b'cfcd208495d565ef'

# 默认路径（均可用环境变量覆盖，便于跨机器使用）
_HOME = os.path.expanduser("~")
WECHAT_CONTAINER = os.environ.get(
    "WECHAT_CONTAINER",
    os.path.join(_HOME, "Library/Containers/com.tencent.xinWeChat/Data/Documents"),
)


def _discover_wxid_dir(container):
    """自动发现 xwechat_files 下的用户子目录（形如 <wxid>_<hex4>）"""
    pattern = os.path.join(container, "xwechat_files", "*_*")
    matches = sorted(
        (p for p in glob.glob(pattern) if os.path.isdir(p)),
        key=os.path.getmtime,
        reverse=True,
    )
    return matches[0] if matches else os.path.join(container, "xwechat_files")


# 微信用户数据根目录（xwechat_files/<wxid>_<hex4>）
WECHAT_BASE = os.environ.get("WECHAT_WXID_DIR") or _discover_wxid_dir(WECHAT_CONTAINER)

# 群聊 attach hash（默认 TGO 群；其他群可用 --attach-dir 或 TGO_ATTACH_HASH 指定）
TGO_ATTACH_HASH = os.environ.get("TGO_ATTACH_HASH", "372ccdfb50bce33523e512d8f22a22ae")
TGO_ATTACH_DIR = os.path.join(WECHAT_BASE, "msg/attach", TGO_ATTACH_HASH)
TGO_OBSIDIAN = os.environ.get(
    "TGO_OBSIDIAN",
    os.path.join(_HOME, "Documents/obsidian/ppj/30-AI与大模型/资料附件/群聊图片"),
)
# 密钥缓存路径：用户可写目录（~/.wechat-cli 可能是 root 拥有）
KEY_CACHE_DIR = os.path.expanduser("~/.cache/wechat-v2-decrypt")
KEY_CACHE = os.path.join(KEY_CACHE_DIR, "image_key.json")
os.makedirs(KEY_CACHE_DIR, exist_ok=True)


# ---------- 密钥派生 ----------

def kvcomm_dir_candidates(root):
    """根据 root 路径生成 kvcomm 目录候选列表"""
    root = os.path.normpath(root)
    candidates = []
    parts = root.split(os.sep)
    for idx, part in enumerate(parts):
        if part == "xwechat_files":
            documents_root = os.sep.join(parts[:idx])
            candidates += [
                os.path.join(documents_root, "app_data", "net", "kvcomm"),
                os.path.join(documents_root, "xwechat", "net", "kvcomm"),
                os.path.join(documents_root, "app_data", "ilink", "kvcomm"),
                os.path.join(documents_root, "app_data", "roam", "ilink", "kvcomm"),
            ]
            radium_matches = glob.glob(os.path.join(documents_root, "app_data", "radium", "ilink", "*", "kvcomm"))
            candidates += radium_matches
            if idx >= 1:
                container_root = os.sep.join(parts[:idx-1])
                candidates += [
                    os.path.join(container_root, "Library", "Application Support", "com.tencent.xinWeChat", "xwechat", "net", "kvcomm"),
                    os.path.join(container_root, "Library", "Application Support", "com.tencent.xinWeChat", "net", "kvcomm"),
                ]
            break

    home = os.path.expanduser("~")
    candidates += [
        os.path.join(home, "Library", "Containers", "com.tencent.xinWeChat", "Data", "Documents", "app_data", "net", "kvcomm"),
        os.path.join(home, "Library", "Containers", "com.tencent.xinWeChat", "Data", "Documents", "app_data", "ilink", "kvcomm"),
    ]

    out, seen = [], set()
    for c in candidates:
        if c and c not in seen and os.path.isdir(c):
            seen.add(c)
            out.append(c)
    return out


def collect_kvcomm_codes(dirs):
    """从 key_{code}_{rest}.statistic 文件名提取所有 code (uint32)"""
    codes = set()
    for d in dirs:
        try:
            for entry in os.listdir(d):
                if not entry.startswith("key_"):
                    continue
                rest = entry[len("key_"):]
                code_text, _, _ = rest.partition("_")
                try:
                    code = int(code_text)
                    if 0 < code < 2**32:
                        codes.add(code)
                except ValueError:
                    continue
        except OSError:
            continue
    return sorted(codes)


def is_hex4(s):
    return len(s) == 4 and all(c in "0123456789abcdefABCDEF" for c in s)


def normalize_wxid(raw):
    """wxid 规范化: 剥离末尾 _hex4 后缀"""
    raw = raw.strip()
    if raw.startswith("wxid_"):
        rest = raw[len("wxid_"):]
        head, _, _ = rest.partition("_")
        if head:
            return "wxid_" + head
    idx = raw.rfind("_")
    if idx > 0:
        suffix = raw[idx+1:]
        if is_hex4(suffix):
            return raw[:idx]
    return raw


def wxid_candidates(root):
    """从 root 路径提取 wxid 候选"""
    leaf = os.path.basename(os.path.normpath(root))
    if leaf == "db_storage":
        leaf = os.path.basename(os.path.dirname(os.path.normpath(root)))
    out = []
    seen = set()
    for v in (leaf, normalize_wxid(leaf)):
        v = v.strip()
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def derive_image_key_from_code(code, wxid):
    """MD5(code + wxid) 派生 AES key"""
    raw = f"{code}{wxid}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def detect_image_key_from_disk(root, template_dat):
    """从磁盘派生并验证 AES 密钥

    Returns:
        dict with keys: aes_key, xor_key, code, wxid
        or None if derivation failed
    """
    if not os.path.exists(template_dat):
        return None

    # 提取模板密文
    with open(template_dat, "rb") as f:
        head = f.read(31)
    if head[:6] not in (V2_MAGIC_FULL, V1_MAGIC_FULL):
        return None
    template_ct = head[15:31]

    # 收集所有候选
    dirs = kvcomm_dir_candidates(root)
    codes = collect_kvcomm_codes(dirs)
    if not codes:
        print(f"  ⚠️  No kvcomm key files found in: {dirs}")
        return None
    wxids = wxid_candidates(root)
    if not wxids:
        print(f"  ⚠️  Cannot infer wxid from root: {root}")
        return None

    # 试遍所有组合
    from Crypto.Cipher import AES
    attempts = 0
    for wxid in wxids:
        for code in codes:
            attempts += 1
            key = derive_image_key_from_code(code, wxid)
            key_bytes = key.encode("ascii")[:16]
            try:
                cipher = AES.new(key_bytes, AES.MODE_ECB)
                dec = cipher.decrypt(template_ct)
            except Exception:
                continue
            if (dec[:3] == b'\xff\xd8\xff' or
                dec[:4] == b'\x89PNG' or
                dec[:4] == b'wxgf'):
                return {
                    "aes_key": key,
                    "xor_key": code & 0xFF,
                    "code": code,
                    "wxid": wxid,
                    "attempts": attempts,
                    "total_codes": len(codes),
                    "total_wxids": len(wxids),
                }
    print(f"  ⚠️  Tested {attempts} combinations, no match")
    return None


def cache_key(info):
    """缓存派生结果到 ~/.wechat-cli/image_key.json"""
    info = dict(info)
    info["derived_at"] = datetime.now().isoformat()
    info["template_dir"] = TGO_ATTACH_DIR
    os.makedirs(os.path.dirname(KEY_CACHE), exist_ok=True)
    with open(KEY_CACHE, "w") as f:
        json.dump(info, f, indent=2)
    try:
        os.chmod(KEY_CACHE, 0o600)
    except OSError:
        pass
    return KEY_CACHE


def load_cached_key():
    """读取缓存的密钥"""
    if not os.path.exists(KEY_CACHE):
        return None
    try:
        with open(KEY_CACHE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def find_tgo_template():
    """在 TGO 群目录找一个 _t.dat 缩略图作为解密验证模板"""
    pattern = os.path.join(TGO_ATTACH_DIR, "*", "Img", "*_t.dat")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return files[0] if files else None


# ---------- 解密逻辑 ----------

def detect_image_format(header_bytes):
    if len(header_bytes) < 4:
        return 'bin'
    if header_bytes[:3] == b'\xff\xd8\xff':
        return 'jpg'
    if header_bytes[:4] == b'\x89PNG':
        return 'png'
    if header_bytes[:3] == b'GIF':
        return 'gif'
    if header_bytes[:2] == b'BM':
        return 'bmp'
    if len(header_bytes) >= 12 and header_bytes[:4] == b'RIFF' and header_bytes[8:12] == b'WEBP':
        return 'webp'
    if header_bytes[:4] == b'\x49\x49\x2a\x00':
        return 'tif'
    if header_bytes[:4] == b'wxgf':
        return 'hevc'
    return 'bin'


def aligned_aes_size(aes_size):
    return aes_size + (16 - aes_size % 16) if aes_size % 16 else aes_size + 16


def v2_decrypt(dat_path, aes_key, xor_key=0x60):
    """解密单个 V2/V1 .dat 文件

    Returns:
        (decrypted_bytes, format) 或 (None, None) 表示失败
    """
    with open(dat_path, "rb") as f:
        data = f.read()
    if len(data) < 15:
        return None, None
    sig = data[:6]
    if sig not in (V2_MAGIC_FULL, V1_MAGIC_FULL):
        return None, None

    key = V1_FIXED_KEY if sig == V1_MAGIC_FULL else aes_key
    if key is None:
        return None, None

    aes_size, xor_size = struct.unpack_from('<LL', data, 6)
    aligned = aligned_aes_size(aes_size)
    offset = 15
    if offset + aligned > len(data):
        return None, None

    from Crypto.Cipher import AES
    from Crypto.Util import Padding
    aes_data = data[offset:offset + aligned]
    try:
        cipher = AES.new(key[:16], AES.MODE_ECB)
        dec_aes = Padding.unpad(cipher.decrypt(aes_data), AES.block_size)
    except (ValueError, KeyError):
        return None, None

    offset += aligned
    raw_end = len(data) - xor_size
    raw_data = data[offset:raw_end] if offset < raw_end else b''
    xor_data = data[raw_end:]
    dec_xor = bytes(b ^ xor_key for b in xor_data)

    decrypted = dec_aes + raw_data + dec_xor
    fmt = detect_image_format(decrypted[:16])
    return decrypted, fmt


def batch_decrypt_tgo(aes_key, xor_key, months=None, output_dir=None, limit=0, verbose=False):
    """批量解密 TGO 群聊图片"""
    output_dir = output_dir or TGO_OBSIDIAN
    os.makedirs(output_dir, exist_ok=True)

    if months:
        dat_files = []
        for m in months:
            dat_files.extend(glob.glob(os.path.join(TGO_ATTACH_DIR, m, "Img", "*.dat")))
    else:
        dat_files = glob.glob(os.path.join(TGO_ATTACH_DIR, "*", "Img", "*.dat"))
    dat_files.sort(key=lambda f: os.path.getmtime(f))

    if limit > 0:
        dat_files = dat_files[:limit]

    results = {"total": len(dat_files), "success": 0, "failed": 0, "skipped": 0, "files": []}
    print(f"\n📦 解密 {len(dat_files)} 个 .dat 文件 → {output_dir}")

    for i, dat_path in enumerate(dat_files):
        basename = os.path.basename(dat_path)
        mtime = datetime.fromtimestamp(os.path.getmtime(dat_path))
        date_str = mtime.strftime("%m%d")
        is_thumb = basename.endswith('_t.dat')
        is_hd = basename.endswith('_h.dat')
        stem = basename.replace('.dat', '').replace('_t', '').replace('_h', '')
        type_tag = 'thumb' if is_thumb else ('hd' if is_hd else 'orig')

        # 已有原图/高清时跳过缩略图
        if is_thumb:
            if glob.glob(os.path.join(output_dir, f"{stem}_{date_str}_orig.*")) or \
               glob.glob(os.path.join(output_dir, f"{stem}_{date_str}_hd.*")):
                results['skipped'] += 1
                continue

        decrypted, fmt = v2_decrypt(dat_path, aes_key, xor_key)
        if decrypted is None:
            results['failed'] += 1
            if (i + 1) % 20 == 0:
                print(f"  [{i+1}/{len(dat_files)}] {basename} → FAILED")
            continue

        out_name = f"{stem}_{date_str}_{type_tag}.{fmt}"
        out_path = os.path.join(output_dir, out_name)
        with open(out_path, 'wb') as f:
            f.write(decrypted)
        results['success'] += 1
        results['files'].append({
            "source": basename, "output": out_name, "format": fmt,
            "size": len(decrypted), "date": mtime.strftime("%Y-%m-%d %H:%M"),
            "type": type_tag,
        })
        if verbose or (i + 1) % 10 == 0 or i == 0:
            print(f"  [{i+1}/{len(dat_files)}] {basename} → {out_name} ({fmt}, {len(decrypted):,}B)")

    return results


# ---------- 主入口 ----------

def main():
    parser = argparse.ArgumentParser(
        description='微信 V2 图片批量解密工具（macOS，无需 sudo）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # TGO 群聊图片，自动派生密钥
  python3 wechat_v2_image_decrypt.py --tgo

  # 仅派生并显示密钥
  python3 wechat_v2_image_decrypt.py --derive-only

  # 手动指定密钥（旧模式兼容）
  python3 wechat_v2_image_decrypt.py --aes-key f9d50efd079ab290 --xor-key 0x60

  # 自定义 attach 目录
  python3 wechat_v2_image_decrypt.py --attach-dir /path/to/attach --output /path/to/out
""")
    parser.add_argument('--aes-key', help='16 字符 AES 密钥（手动指定）')
    parser.add_argument('--xor-key', help='XOR 密钥（如 0x60 或 96）')
    parser.add_argument('--tgo', action='store_true', help='使用 TGO 群聊默认路径')
    parser.add_argument('--derive-only', action='store_true', help='仅派生密钥，不解密')
    parser.add_argument('--attach-dir', default=TGO_ATTACH_DIR, help='微信 attach 目录')
    parser.add_argument('--output', default=TGO_OBSIDIAN, help='输出目录')
    parser.add_argument('--months', nargs='*', help='指定月份 (如 2026-07 2026-06)')
    parser.add_argument('--wechat-root', default=WECHAT_BASE, help='微信 xwechat_files 子目录根')
    parser.add_argument('--limit', type=int, default=0, help='限制处理文件数 (0=全部)')
    parser.add_argument('--verbose', action='store_true', help='显示每个文件详情')
    args = parser.parse_args()

    print("=" * 60)
    print("🔓 微信 V2 图片批量解密工具（macOS）")
    print("=" * 60)

    # 决定密钥
    key_info = None
    aes_key_str = None
    xor_key = 0x60  # 默认 V2 实际是动态的，但磁盘派生会覆盖

    if args.aes_key:
        # 手动指定
        aes_key_str = args.aes_key
        xor_key = int(args.xor_key, 0) if args.xor_key else 0x60
        print(f"🔑 使用手动指定密钥: {aes_key_str[:4]}**** (XOR 0x{xor_key:02x})")
    else:
        # 1) 尝试磁盘派生
        template = find_tgo_template() if args.tgo else None
        if not template:
            # 退而求其次，找任意 .dat
            candidates = sorted(glob.glob(os.path.join(args.attach_dir, "*", "Img", "*_t.dat")),
                                key=os.path.getmtime, reverse=True)
            template = candidates[0] if candidates else None
        if not template:
            print(f"❌ 在 {args.attach_dir} 找不到任何 .dat 模板文件")
            sys.exit(1)
        print(f"📋 模板: {os.path.basename(template)}")
        print(f"🔍 从磁盘派生密钥...")
        key_info = detect_image_key_from_disk(args.wechat_root, template)
        if key_info:
            aes_key_str = key_info["aes_key"]
            xor_key = key_info["xor_key"]
            cache_path = cache_key(key_info)
            print(f"✅ 派生成功!")
            print(f"   wxid:  {key_info['wxid']}")
            print(f"   code:  {key_info['code']} (from kvcomm)")
            print(f"   AES:   {aes_key_str}")
            print(f"   XOR:   0x{xor_key:02x}")
            print(f"   尝试:  {key_info['attempts']}/{key_info['total_codes'] * key_info['total_wxids']} 组合")
            print(f"   缓存:  {cache_path}")
        else:
            # 2) 退到缓存
            cached = load_cached_key()
            if cached:
                aes_key_str = cached["aes_key"]
                xor_key = cached["xor_key"]
                print(f"📦 使用缓存密钥: {aes_key_str[:4]}**** (XOR 0x{xor_key:02x})")
                print(f"   (派生于 {cached.get('derived_at', '?')})")
            else:
                print("❌ 磁盘派生失败且无缓存")
                print("   请用 --aes-key 手动指定，或运行 wxkey image-key（需 sudo）")
                sys.exit(1)

    if args.derive_only:
        print("\n✅ 派生完成，未执行解密。")
        return

    # 准备 AES key
    aes_key_bytes = aes_key_str.encode("ascii")[:16]

    # 执行解密
    if args.tgo:
        results = batch_decrypt_tgo(aes_key_bytes, xor_key, args.months, args.output,
                                     limit=args.limit, verbose=args.verbose)
    else:
        # 通用模式
        os.makedirs(args.output, exist_ok=True)
        if args.months:
            dat_files = []
            for m in args.months:
                dat_files.extend(glob.glob(os.path.join(args.attach_dir, m, "Img", "*.dat")))
        else:
            dat_files = glob.glob(os.path.join(args.attach_dir, "*", "Img", "*.dat"))
        dat_files.sort(key=lambda f: os.path.getmtime(f))
        results = {"total": len(dat_files), "success": 0, "failed": 0, "skipped": 0, "files": []}
        print(f"\n📦 解密 {len(dat_files)} 个 .dat 文件 → {args.output}")
        for i, dat_path in enumerate(dat_files):
            basename = os.path.basename(dat_path)
            decrypted, fmt = v2_decrypt(dat_path, aes_key_bytes, xor_key)
            if decrypted is None:
                results['failed'] += 1
                continue
            out_name = f"{basename.replace('.dat', '')}.{fmt}"
            with open(os.path.join(args.output, out_name), 'wb') as f:
                f.write(decrypted)
            results['success'] += 1
            results['files'].append({"source": basename, "output": out_name, "format": fmt, "size": len(decrypted)})
            if (i + 1) % 10 == 0 or i == 0:
                print(f"  [{i+1}/{len(dat_files)}] {basename} → {out_name} ({fmt})")

    # 统计
    print()
    print("=" * 60)
    print(f"📊 总计: {results['total']} | ✅ 成功: {results['success']} | ❌ 失败: {results['failed']} | ⏭️  跳过: {results['skipped']}")
    print(f"📂 输出: {args.output}")
    print("=" * 60)

    manifest = os.path.join(args.output, "decrypt_manifest.json")
    with open(manifest, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"📋 清单: {manifest}")


if __name__ == '__main__':
    main()
