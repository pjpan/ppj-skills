#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
周报链接补全的「可恢复 + 幂等」工具。

背景
----
第二阶段自动化（补全周报里的 `(待补全)` 链接）历史上 3 次运行 0 成功：
两次都死在约 16 分钟，且因为「先把所有搜索做完、最后一次性回写」，
被中断时 10 次搜索的成果全部丢失，文件仍是 84 条 `(待补全)`。

本工具把状态从「模型上下文」搬到「磁盘」：
  - record  每确认一条就立即落盘（sidecar JSON），中断不丢
  - apply   幂等地把已确认结果写回 md 文件，可重复执行
  - list    只列出还没处理的条目，供分批消费
  - status  打印进度，供调度器/人快速判断

于是「搜索 → 落盘 → 回写」可以拆成任意多轮，任何一轮被杀都不影响已完成部分。

用法
----
  # 1) 看进度 / 列待办
  python3 report_links.py status --report 报告.md
  python3 report_links.py list   --report 报告.md --limit 5

  # 2) 每查到一条就记录（可反复调用）
  python3 report_links.py record --report 报告.md --index 3 --url "https://..."
  python3 report_links.py record --report 报告.md --index 7 --unresolved

  # 3) 把已记录的结果回写进 md（幂等，随时可跑）
  python3 report_links.py apply  --report 报告.md

  # 4) 若想重试「未检索到」的条目
  python3 report_links.py record --report 报告.md --reset-unresolved

退出码：0 正常；1 有未完成项（status/list 用）；2 参数或文件错误
"""

import argparse
import datetime as _dt
import json
import os
import re
import sys

PENDING = "(待补全)"
SIDECAR_SUFFIX = ".links.json"

ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|")


# --------------------------------------------------------------------------- #
# 报告解析
# --------------------------------------------------------------------------- #
def load_rows(path):
    """返回 [(index:int, date:str, sender:str, title:str, line_no:int, has_pending:bool)]"""
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            s = line.rstrip("\n")
            if not ROW_RE.match(s):
                continue
            if not s.endswith("|"):
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) < 4:
                continue
            try:
                idx = int(cells[0])
            except ValueError:
                continue
            has_pending = (PENDING in s)
            # 标题是倒数第 2 格（最后一格是 URL）
            title = cells[-2]
            date = cells[1] if len(cells) >= 4 else ""
            sender = cells[2] if len(cells) >= 5 else ""
            rows.append({
                "index": idx,
                "date": date,
                "sender": sender,
                "title": title,
                "line_no": i,
                "has_pending": has_pending,
            })
    return rows


def norm(t):
    return re.sub(r"\s+", "", t or "")


def sidecar_path(report):
    return os.path.splitext(report)[0] + SIDECAR_SUFFIX


def load_state(report):
    p = sidecar_path(report)
    if not os.path.exists(p):
        return {"report": os.path.basename(report), "urls": {}, "unresolved": [], "updated": None}
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    d.setdefault("urls", {})
    d.setdefault("unresolved", [])
    return d


def save_state(report, st):
    st["updated"] = _dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with open(sidecar_path(report), "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


# --------------------------------------------------------------------------- #
# 命令
# --------------------------------------------------------------------------- #
def cmd_status(args):
    rows = load_rows(args.report)
    st = load_state(args.report)
    pending = [r for r in rows if r["has_pending"]]
    total = len(rows)
    done = total - len(pending)
    have_url = len(st["urls"])
    unres = len(st["unresolved"])
    print(f"报告：{args.report}")
    print(f"链接总行数：{total}")
    print(f"文件中仍为 (待补全)：{len(pending)}")
    print(f"已记录可打开的 URL：{have_url}")
    print(f"已标记无公开地址：{unres}")
    pct = (done / total * 100) if total else 100.0
    print(f"进度：{done}/{total}（{pct:.0f}%）")
    if st.get("updated"):
        print(f"sidecar 最后更新：{st['updated']}")
    if not pending:
        print("✅ 无待补全条目")
        return 0
    print(f"⚠️ 仍有 {len(pending)} 条待处理")
    return 1


def cmd_list(args):
    rows = load_rows(args.report)
    st = load_state(args.report)
    known = {norm(t) for t in st["urls"]} | {norm(t) for t in st["unresolved"]}
    if args.reset_unresolved:
        known = {norm(t) for t in st["urls"]}

    out = []
    for r in rows:
        if not r["has_pending"]:
            continue
        if norm(r["title"]) in known:
            continue
        out.append(r)

    if args.limit and args.limit > 0:
        out = out[: args.limit]

    for r in out:
        print(f"{r['index']}\t{r['date']}\t{r['title']}")
    if not out:
        print("（没有待处理条目）")
        return 0
    return 0


def cmd_record(args):
    rows = load_rows(args.report)
    st = load_state(args.report)

    if args.reset_unresolved:
        st["unresolved"] = []
        save_state(args.report, st)
        print("已清空 unresolved 列表，下次 list 会重新给出这些条目")
        return 0

    if args.index is None:
        print("record 需要 --index（或使用 --reset-unresolved）", file=sys.stderr)
        return 2

    target = next((r for r in rows if r["index"] == args.index), None)
    if target is None:
        print(f"找不到编号 {args.index} 的行", file=sys.stderr)
        return 2
    if args.title and norm(args.title) != norm(target["title"]):
        print(f"标题不匹配：\n  期望：{target['title']}\n  传入：{args.title}", file=sys.stderr)
        return 2

    key = target["title"]
    if args.unresolved:
        st["unresolved"] = sorted(set(st["unresolved"]) | {key})
        st["urls"].pop(key, None)
        save_state(args.report, st)
        print(f"已标记无公开地址：#{args.index} {key}")
    else:
        if not args.url:
            print("record 需要 --url 或 --unresolved", file=sys.stderr)
            return 2
        st["urls"][key] = args.url.strip()
        st["unresolved"] = [t for t in st["unresolved"] if norm(t) != norm(key)]
        save_state(args.report, st)
        print(f"已记录：#{args.index} {key}\n        → {args.url.strip()}")
    return 0


def _cell(s):
    return s.replace("|", "\\|")


def cmd_apply(args):
    rows = load_rows(args.report)
    st = load_state(args.report)
    urls = {norm(k): v for k, v in st["urls"].items()}
    unres = {norm(t) for t in st["unresolved"]}

    with open(args.report, encoding="utf-8") as f:
        lines = f.readlines()

    changed = 0
    still = 0
    for r in rows:
        i = r["line_no"]
        if not r["has_pending"]:
            continue
        n = norm(r["title"])
        if n in urls:
            repl = f"| [打开]({urls[n]}) |"
        elif n in unres:
            repl = "| —（未检索到公开地址） |"
        else:
            still += 1
            continue
        # 只替换行尾的 `| (待补全) |`
        old = lines[i]
        if old.rstrip("\n").endswith(f"| {PENDING} |"):
            lines[i] = old.rstrip("\n")[: -len(f"| {PENDING} |")] + repl + "\n"
            changed += 1

    # 更新状态行（累计口径，便于多轮运行后一眼看出还剩多少）
    total = len(rows)
    pending_after = sum(1 for r in rows if r["has_pending"]) - changed
    body = "".join(lines)
    n_url = body.count("[打开](")
    n_unres = body.count("（未检索到公开地址）")
    done = total - pending_after
    status = (
        f"> 状态：链接补全 {done}/{total}"
        f"（可打开 {n_url} · 无公开地址 {n_unres}），剩余 {pending_after} 条待补"
        f"｜更新于 {_dt.datetime.now():%Y-%m-%d %H:%M}\n"
    )
    lines = [status if l.startswith("> 状态：") else l for l in lines]
    if not any(l.startswith("> 状态：") for l in lines):
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append("\n" + status)

    with open(args.report, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"已回写 {changed} 条；本次未能写入 {still} 条仍为 (待补全)")
    print(f"文件：{args.report}")
    return 0 if changed or still == 0 else 0


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="周报链接补全（可恢复/幂等）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status", help="查看进度")
    p.add_argument("--report", required=True)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("list", help="列出待处理条目（TSV）")
    p.add_argument("--report", required=True)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--reset-unresolved", action="store_true", help="把 unresolved 也当作待办重新列出")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("record", help="记录一条结果（立即落盘）")
    p.add_argument("--report", required=True)
    p.add_argument("--index", type=int)
    p.add_argument("--url")
    p.add_argument("--unresolved", action="store_true")
    p.add_argument("--title", help="可选，用于校验编号与标题是否对应")
    p.add_argument("--reset-unresolved", action="store_true")
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("apply", help="把已记录结果回写进 md（幂等）")
    p.add_argument("--report", required=True)
    p.set_defaults(func=cmd_apply)

    args = ap.parse_args()
    if not os.path.exists(args.report):
        print(f"文件不存在：{args.report}", file=sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
