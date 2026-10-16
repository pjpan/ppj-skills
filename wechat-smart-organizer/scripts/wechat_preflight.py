#!/usr/bin/env python3
"""
wechat-cli 前置检查（preflight）——确保微信在运行、且本地消息库是新鲜的。

背景：wechat-cli 读取的是微信 Mac 客户端的**本地数据库**。如果微信客户端没有运行，
本地库就停止更新，wechat-cli 仍然"能跑通"但取不到新消息（静默失败）。
历史上这导致周报自动化空跑 30–75 分钟后超时/被取消。

本脚本在拉取消息前执行：
  1) 检查微信客户端进程是否在运行，不在则尝试自动拉起
  2) 检查本地消息库的新鲜度（最新消息时间戳）
  3) 用退出码明确告诉调用方该继续还是该中止

退出码：
  0  通过——微信在运行，数据新鲜，可以继续
  2  微信未运行，且自动拉起失败（需要人工打开微信）
  3  微信在运行，但本地数据过期（需要人工打开微信/等待同步完成）
  4  无法读取会话数据（wechat-cli 异常）
  1  其他未预期错误

用法：
  python3 wechat_preflight.py                 # 检查；必要时尝试拉起微信
  python3 wechat_preflight.py --no-launch     # 只检查，不尝试拉起
  python3 wechat_preflight.py --max-age-hours 30 --hard-fail-hours 48
  python3 wechat_preflight.py --json          # 机器可读输出
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


def newest_timestamp(sessions):
    """返回会话列表中最新的消息时间戳（秒）。"""
    newest = 0
    newest_chat = ""
    for s in sessions:
        ts = s.get("timestamp") or 0
        try:
            ts = int(ts)
        except (TypeError, ValueError):
            continue
        if ts > newest:
            newest = ts
            newest_chat = s.get("chat") or ""
    return newest, newest_chat


def main():
    ap = argparse.ArgumentParser(description="wechat-cli 前置检查")
    ap.add_argument("--binary", help="wechat-cli 二进制路径（默认取环境变量或内置默认）")
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

    # ---- 3. 数据新鲜度 ----
    newest, newest_chat = newest_timestamp(sessions)
    if newest <= 0:
        result["verdict"] = "会话中不含任何时间戳"
        result["exit_code"] = EXIT_CLI_ERROR
        return finish(result, args.json, quiet)

    newest_dt = datetime.fromtimestamp(newest)
    age_hours = (datetime.now() - newest_dt).total_seconds() / 3600.0
    result["newest_message_time"] = newest_dt.strftime("%Y-%m-%d %H:%M")
    result["newest_chat"] = newest_chat
    result["age_hours"] = round(age_hours, 2)

    log(f"📨 最新消息：{result['newest_message_time']}（{newest_chat}）", quiet)
    log(f"⏱  距现在 {age_hours:.1f} 小时", quiet)

    if age_hours >= args.hard_fail_hours:
        result["verdict"] = (
            f"本地消息库已过期 {age_hours:.1f} 小时（≥ {args.hard_fail_hours}h）"
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
            log("\n处理建议：请在微信里打开对应群聊触发同步，或稍后重试。", quiet)
    return result["exit_code"]


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
