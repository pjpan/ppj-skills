#!/usr/bin/env python3
"""
wechat-cli 前置检查（preflight）——确保微信在运行、且本地消息库是新鲜的。

背景：wechat-cli 读取的是微信 Mac 客户端的**本地数据库**。如果微信客户端没有运行，
本地库就停止更新，wechat-cli 仍然"能跑通"但取不到新消息（静默失败）。
历史上这导致周报自动化空跑 30–75 分钟后超时/被取消。

本脚本在拉取消息前执行：
  1) 检查微信客户端进程是否在运行，不在则尝试自动拉起
  2) 检查本地消息库的新鲜度——**默认按目标群会话判断**，而不是全局最新会话
  3) 用退出码明确告诉调用方该继续还是该中止

⚠️ 为什么必须按目标群判断：微信的 `brandsessionholder` / `brandservicesessionholder`
这类内部服务会话在客户端一联网时就立刻更新，但群消息可能完全没同步。若按"全局最新会话"
判断，会在**目标群数据其实没更新**时误报"数据新鲜"，让自动化白跑一整轮。

另外注意：微信客户端重连后**只同步各会话的最新消息（用于刷新会话列表）**，
某个群的完整历史需要**在微信里打开该群**才会从服务器拉取。因此"群最后消息时间"正常
但"目标区间消息条数异常少"时，应提示用户去微信里打开该群触发补齐。

退出码：
  0  通过——微信在运行，目标群数据新鲜，可以继续
  2  微信未运行，且自动拉起失败（需要人工打开微信）
  3  目标群数据过期（需要人工打开微信/打开该群/等待同步完成）
  4  无法读取会话数据（wechat-cli 异常）
  1  其他未预期错误

用法：
  python3 wechat_preflight.py                 # 检查；必要时尝试拉起微信
  python3 wechat_preflight.py --no-launch     # 只检查，不尝试拉起
  python3 wechat_preflight.py --chat "5-TGO和朋友们的AGI"
  python3 wechat_preflight.py --max-age-hours 30 --hard-fail-hours 48
  python3 wechat_preflight.py --json          # 机器可读输出

目标群可用环境变量 `WECHAT_TARGET_CHAT` 指定（默认 TGO 群）。
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

# 微信客户端主程序路径（用于判断进程是否存在）
WECHAT_APP_PATH_MARKER = "WeChat.app/Contents/MacOS/WeChat"

# wechat-cli 底层二进制（node wrapper 调用无输出，必须用二进制）
DEFAULT_BINARY = (
    "/opt/homebrew/lib/node_modules/@canghe_ai/wechat-cli/"
    "node_modules/@canghe_ai/wechat-cli-darwin-arm64/bin/wechat-cli"
)

EXIT_OK = 0
EXIT_UNEXPECTED = 1
EXIT_LAUNCH_FAILED = 2
EXIT_STALE_DATA = 3
EXIT_CLI_ERROR = 4

# 默认目标群（可用 --chat 或 WECHAT_TARGET_CHAT 覆盖）
DEFAULT_TARGET_CHAT = "5-TGO和朋友们的AGI"

# 微信内部的服务/占位会话：一联网就立刻更新，不能代表群消息新鲜度
SERVICE_SESSION_PATTERNS = ("sessionholder",)


def log(msg, quiet=False):
    if not quiet:
        print(msg, flush=True)


def find_binary(explicit=None):
    return explicit or os.environ.get("WECHAT_CLI_BINARY") or DEFAULT_BINARY


def wechat_processes():
    """返回微信客户端相关进程的 (pid, command) 列表。"""
    try:
        out = subprocess.run(
            ["ps", "-Ao", "pid,command"],
            capture_output=True, text=True, timeout=20,
        ).stdout
    except Exception:
        return []
    procs = []
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        pid, _, cmd = line.partition(" ")
        if WECHAT_APP_PATH_MARKER in cmd:
            procs.append((pid.strip(), cmd.strip()))
    return procs


def wechat_running():
    return len(wechat_processes()) > 0


def launch_wechat(wait_seconds=60):
    """尝试拉起微信。返回 True 表示拉起成功（进程已存在）。"""
    # 优先用 bundle id（实测 `open -a <完整路径>` 在部分上下文下不生效）
    attempts = [
        ["open", "-b", "com.tencent.xinWeChat"],
        ["open", "-a", "WeChat"],
        ["open", "-a", "/Applications/WeChat.app"],
    ]
    for cmd in attempts:
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except Exception:
            continue
        deadline = time.time() + wait_seconds / len(attempts) + 5
        while time.time() < deadline:
            if wechat_running():
                return True
            time.sleep(2)
    return wechat_running()


def fetch_sessions(binary, limit=400):
    """调用 wechat-cli sessions，返回 (list_or_None, error_str)。"""
    tmp = f"/tmp/wechat_preflight_sessions_{os.getpid()}.json"
    try:
        with open(tmp, "w") as fh:
            r = subprocess.run(
                [binary, "sessions", "--limit", str(limit)],
                stdout=fh, stderr=subprocess.STDOUT, timeout=180,
            )
        if r.returncode != 0:
            return None, f"wechat-cli sessions 退出码 {r.returncode}"
        with open(tmp) as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return None, f"wechat-cli 返回非列表结构: {str(data)[:200]}"
        return data, None
    except json.JSONDecodeError as exc:
        return None, f"解析 wechat-cli 输出失败: {exc}"
    except Exception as exc:
        return None, f"调用 wechat-cli 失败: {exc}"
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def is_service_session(name):
    """判断是否为微信内部服务/占位会话。"""
    low = (name or "").lower()
    return any(p in low for p in SERVICE_SESSION_PATTERNS)


def newest_real_timestamp(sessions):
    """非服务会话中最新的消息时间戳（秒）。"""
    newest = 0
    newest_chat = ""
    for s in sessions:
        if is_service_session(s.get("chat")):
            continue
        ts = s.get("timestamp") or 0
        try:
            ts = int(ts)
        except (TypeError, ValueError):
            continue
        if ts > newest:
            newest = ts
            newest_chat = s.get("chat") or ""
    return newest, newest_chat


def find_chat_session(sessions, chat):
    """在会话列表中查找目标群；先精确匹配，再包含匹配。找不到返回 None。"""
    if not chat:
        return None
    for s in sessions:
        if (s.get("chat") or "") == chat:
            return s
    low = chat.lower()
    for s in sessions:
        if low in (s.get("chat") or "").lower():
            return s
    return None


def main():
    ap = argparse.ArgumentParser(description="wechat-cli 前置检查")
    ap.add_argument("--binary", help="wechat-cli 二进制路径（默认取环境变量或内置默认）")
    ap.add_argument("--chat", default=os.environ.get("WECHAT_TARGET_CHAT") or DEFAULT_TARGET_CHAT,
                    help="用于判断新鲜度的目标群名（默认取 WECHAT_TARGET_CHAT 或 TGO 群）")
    ap.add_argument("--max-age-hours", type=float, default=30.0,
                    help="数据陈旧告警阈值（小时），默认 30")
    ap.add_argument("--hard-fail-hours", type=float, default=48.0,
                    help="数据陈旧中止阈值（小时），默认 48")
    ap.add_argument("--no-launch", action="store_true", help="微信未运行时不要尝试自动拉起")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    binary = find_binary(args.binary)
    result = {
        "wechat_running": False,
        "launched": False,
        "binary": binary,
        "binary_exists": os.path.exists(binary),
        "target_chat": args.chat,
        "judged_by": None,
        "newest_message_time": None,
        "newest_chat": None,
        "age_hours": None,
        "verdict": "",
        "exit_code": EXIT_OK,
    }

    quiet = args.json

    # ---- 1. 微信是否在运行 ----
    result["wechat_running"] = wechat_running()
    if not result["wechat_running"]:
        log("⚠️  微信客户端未运行——本地消息库不会更新。", quiet)
        if args.no_launch:
            result["verdict"] = "微信未运行，且指定不自动拉起"
            result["exit_code"] = EXIT_LAUNCH_FAILED
            return finish(result, args.json, quiet)
        log("⏳ 尝试自动拉起微信客户端…", quiet)
        if launch_wechat():
            result["launched"] = True
            result["wechat_running"] = True
            log("✅ 微信客户端已拉起，等待其完成消息同步。", quiet)
        else:
            result["verdict"] = "微信未运行，自动拉起失败——请人工打开微信并登录"
            result["exit_code"] = EXIT_LAUNCH_FAILED
            return finish(result, args.json, quiet)

    # ---- 2. wechat-cli 可用性 ----
    if not result["binary_exists"]:
        result["verdict"] = f"wechat-cli 二进制不存在: {binary}"
        result["exit_code"] = EXIT_CLI_ERROR
        return finish(result, args.json, quiet)

    sessions, err = fetch_sessions(binary)
    if err:
        result["verdict"] = f"无法读取会话列表：{err}"
        result["exit_code"] = EXIT_CLI_ERROR
        return finish(result, args.json, quiet)
    if not sessions:
        result["verdict"] = "会话列表为空——微信可能尚未完成登录或同步"
        result["exit_code"] = EXIT_STALE_DATA
        return finish(result, args.json, quiet)

    # ---- 3. 数据新鲜度（优先按目标群判断，避免被服务会话误报）----
    chat_session = find_chat_session(sessions, args.chat)
    if chat_session is not None:
        try:
            newest = int(chat_session.get("timestamp") or 0)
        except (TypeError, ValueError):
            newest = 0
        newest_chat = chat_session.get("chat") or args.chat
        result["judged_by"] = "target_chat"
        try:
            result["target_unread"] = int(chat_session.get("unread") or 0)
        except (TypeError, ValueError):
            result["target_unread"] = None
        if newest <= 0:
            # 目标群时间戳异常 → 回退到非服务会话
            newest, newest_chat = newest_real_timestamp(sessions)
            result["judged_by"] = "newest_non_service_session"
    else:
        newest, newest_chat = newest_real_timestamp(sessions)
        result["judged_by"] = "newest_non_service_session"
        if args.chat:
            log(f"⚠️  会话列表里没有找到目标群「{args.chat}」，回退为按非服务会话判断", quiet)

    if newest <= 0:
        result["verdict"] = "会话中不含任何可用的时间戳"
        result["exit_code"] = EXIT_CLI_ERROR
        return finish(result, args.json, quiet)

    newest_dt = datetime.fromtimestamp(newest)
    age_hours = (datetime.now() - newest_dt).total_seconds() / 3600.0
    result["newest_message_time"] = newest_dt.strftime("%Y-%m-%d %H:%M")
    result["newest_chat"] = newest_chat
    result["age_hours"] = round(age_hours, 2)

    if result["judged_by"] == "target_chat":
        extra = ""
        if result.get("target_unread"):
            extra = f"，未读 {result['target_unread']}"
        log(f"📨 目标群「{newest_chat}」最后消息：{result['newest_message_time']}{extra}", quiet)
    else:
        log(f"📨 最新消息（非服务会话）：{result['newest_message_time']}（{newest_chat}）", quiet)
    log(f"⏱  距现在 {age_hours:.1f} 小时", quiet)

    if age_hours >= args.hard_fail_hours:
        result["verdict"] = (
            f"「{newest_chat}」已过期 {age_hours:.1f} 小时（≥ {args.hard_fail_hours}h）"
            "——微信可能未登录或同步未完成，请人工打开微信确认"
        )
        result["exit_code"] = EXIT_STALE_DATA
    elif age_hours >= args.max_age_hours:
        result["verdict"] = (
            f"数据偏旧（{age_hours:.1f}h，≥ {args.max_age_hours}h）——"
            "本次可继续，但结果可能不完整；建议确认微信已登录并完成同步"
        )
        result["exit_code"] = EXIT_OK
    else:
        result["verdict"] = "数据新鲜，可以继续"
        result["exit_code"] = EXIT_OK

    return finish(result, args.json, quiet)


def finish(result, as_json, quiet):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        icon = "✅" if result["exit_code"] == 0 else "❌"
        log(f"{icon} {result['verdict']}", quiet)
        if result["exit_code"] == EXIT_LAUNCH_FAILED:
            log("\n处理建议：请人工打开微信客户端并登录，然后重跑本任务。", quiet)
        elif result["exit_code"] == EXIT_STALE_DATA:
            target = result.get("target_chat") or "对应群聊"
            log(f"\n处理建议：请在微信里打开「{target}」触发同步，或稍后重试。"
                "\n         注意：客户端重连只会刷新各会话的最新消息，"
                "群的完整历史需要打开该群才会从服务器拉取。", quiet)
    return result["exit_code"]


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
