---
name: wechat-smart-organizer
description: 微信聊天记录智能整理技能。当用户想要读取微信聊天记录、提取关键信息、存储到Obsidian笔记、或创建日历事件时使用此技能。功能包括：查询会话、读取聊天记录、搜索关键词、提取任务/时间/待办事项、智能分类存储到Obsidian、创建日历提醒、自动补全链接URL。
agent_created: true
version: 1.5.1
author: ppj
tags: [wechat, organizer, obsidian, productivity, v2-decrypt]
homepage: https://github.com/pjpan/ppj-skills/tree/master/wechat-smart-organizer
---

# 微信聊天记录智能整理技能

本技能整合 wechat-cli、Obsidian 笔记系统和日历系统，帮助用户从微信聊天记录中提取关键信息并智能整理。

## 核心能力

1. **读取微信数据** - 通过 wechat-cli 访问本地微信聊天记录
2. **智能信息提取** - 从聊天内容中识别任务、截止日期、会议、联系人等关键信息
3. **链接URL补全** - 对[链接]类型消息自动通过搜索引擎补全原文URL，使Obsidian中可直接跳转
4. **Obsidian 存储** - 将整理后的信息存储到 Obsidian 知识库
5. **日历事件创建** - 识别时间相关事项并创建日历事件和提醒

## ⚠️ wechat-cli 调用方式（重要）

`wechat-cli` 通过 node wrapper 调用，直接使用时**不会打印任何内容**（只有 node 警告）。
必须用以下方式调用底层二进制：

```bash
BINARY="/opt/homebrew/lib/node_modules/@canghe_ai/wechat-cli/node_modules/@canghe_ai/wechat-cli-darwin-arm64/bin/wechat-cli"
"$BINARY" history "群名" --limit 50
```

或者把输出重定向到文件再读取：
```bash
"$BINARY" history "群名" --start-time "2026-06-01" > /tmp/msgs.json 2>&1
```

不要用 `wechat-cli history ... 2>&1 | python3 ...`（管道不生效），必须先输出到文件。

## 🚨 第 0 步：数据新鲜度前置检查（任何拉取前必做）

**wechat-cli 读取的是微信 Mac 客户端的本地数据库。** 如果微信客户端没有运行（或启动即崩），
本地库就停止更新——**wechat-cli 仍然"能跑通"、退出码为 0，但取不到任何新消息**。
这是一种**静默失败**，历史上曾导致周报自动化空跑 30–75 分钟后被取消或超时。

因此**每次拉取微信数据前，必须先跑前置检查**：

```bash
PY="python3"
PREFLIGHT="scripts/wechat_preflight.py"   # 相对于本 skill 目录
"$PY" "$PREFLIGHT"          # 人类可读输出
"$PY" "$PREFLIGHT" --json   # 机器可读（供自动化判断）
"$PY" "$PREFLIGHT" --chat "5-TGO和朋友们的AGI"   # 指定目标群（默认即 TGO 群）
```

退出码含义：

| 退出码 | 含义 | 应该怎么做 |
|-------|------|-----------|
| `0` | 微信在运行，**目标群**数据新鲜 | 正常继续 |
| `2` | 微信未运行且自动拉起失败 | **中止任务**，提示用户人工打开微信并登录 |
| `3` | **目标群**数据过期 | **中止任务**，提示用户在微信里打开该群触发同步 |
| `4` | 无法读取会话（wechat-cli 异常） | 检查 wechat-cli 安装与权限 |
| `1` | 其他错误 | 人工排查 |

**判定逻辑（v1.5.1 起）**：**优先取目标群会话的最后消息时间**，与当前时间比较；
只有会话列表里找不到目标群时，才回退为"非服务会话中最新的时间戳"。
默认 `--max-age-hours 30`（超过则告警）、`--hard-fail-hours 48`（超过则中止）；
目标群可用 `--chat` 或环境变量 `WECHAT_TARGET_CHAT` 指定。

> ⚠️ **为什么不能按"全局最新会话"判断**：微信的 `brandsessionholder` /
> `brandservicesessionholder` 这类内部服务会话一联网就立刻更新，而群消息可能完全没同步。
> 按全局最新判断会在**目标群其实没数据**时误报"数据新鲜"。`--json` 输出里的
> `judged_by` 字段会告诉你这次是依据哪个会话判断的。

> ⚠️ **"数据新鲜"≠"区间数据完整"**：客户端重连后**只同步各会话的最新消息**（用于刷新会话列表），
> 某个群的完整历史需要**在微信里打开该群**才会从服务器拉取。因此若目标群"最后消息时间正常"
> 但"目标区间消息条数明显偏少"（例如某几天完全没有消息），应先让用户在微信里打开该群补齐，
> 再生成总结——不要把"缺口"当成"群里那几天很安静"。

### 关键排查经验：微信"启动即退出"（无窗口）

**症状**：前置检查报 `微信未运行`；手动 `open -b com.tencent.xinWeChat` 后主进程只活约 10 秒
就消失；`wechat-cli sessions` 的会话时间戳全部冻结在某个过去时刻。

**机制（实测确认）**：

- 主进程启动 → 联网 → 协商插件版本 → 拉起 `WeChatAppEx`（Flue/Chromium 渲染运行时）
- **但窗口从未出现**。微信主界面是 NSRemoteView，由 `WeChatAppEx` 承载渲染
  （日志特征：`WindowServer ... <token: viewbridge-key-window>`、`RemoteView`）
- `sample <pid> 5` 显示主线程数千个样本都停在 AppKit 事件循环里空闲等待（不是在等锁）
- 约 10 秒后主进程**干净退出**（`launchservicesd` 打印 `QUITTING`，**主进程不产生崩溃报告**）
- 真正崩的是渲染侧：`app_data/crashinfo/WeChatAppEx_*.dmp`（minidump）+
  `app_data/magicdy/targets/{wxutility,wxocr}/cp/LD_CRASH_MARKER_<pid>` 不断累积
- ⚠️ **不是 macOS 自动终止**：微信自己写的是 `_kLSApplicationWouldBeTerminatedByTALKey=0`（拒绝被终止），
  写 `defaults write ... NSDisableAutomaticTermination` 也无效

**已实测排除的原因（别重复浪费时间）**：

| 假设 | 实测结论 |
|---|---|
| 重签名破坏 / Gatekeeper | ❌ App 是原件 Apple MAS 签名，无 `get-task-allow`，`spctl` = Mac App Store |
| App 包资源缺失 | ❌ `codesign --verify --deep --strict` 通过，sealed resources 完整，`_MASReceipt` 在 |
| 容器里有 root 属主文件 | ❌ `find ~/Library/Containers/com.tencent.xinWeChat ! -user $USER` 为空 |
| 系统/App 在故障窗口更新过 | ❌ `InstallHistory.plist` 无对应记录 |
| 热更新插件损坏 | ❌ 按 `file_component.xml` 校验 18/18 md5+length 全对 |
| 插件元数据不一致 | ❌ 移开 `xplugin/info/plugin_command_info*` 让客户端重建，仍失败 |
| Flue 运行时数据（`app_data/radium`，1.3G）损坏 | ❌ 整个移开仍失败 |
| Chromium Code/GPU 缓存损坏 | ❌ 移开 `Library/Caches/profiles/*/Code Cache` 仍失败 |
| 插件载荷需要重新下载 | ❌ 只活 10 秒，下不完 436MB，反而更糟 |

**实测有效的恢复流程**：

```bash
C=~/Library/Containers/com.tencent.xinWeChat/Data/Documents/app_data
# 1) 把 magicdy 运行时状态（含累积崩溃标记 + targets）整体移开，让客户端重建
mv "$C/magicdy" "$C/magicdy.bak_$(date +%Y%m%d_%H%M%S)"
# 2) 连续启动多次（每次观察 30 秒）；常需 3-5 次才成功
for n in 1 2 3 4 5; do
  open -b com.tencent.xinWeChat
  for i in $(seq 1 15); do
    ps -Ao pid,comm | grep -F "/Applications/WeChat.app/Contents/MacOS/WeChat" | grep -v AppEx | grep -v grep >/dev/null || break
    sleep 2
  done
done
```

**如何确认真的修好了**（不要只看进程活着）：

1. 主进程存活 > 30 秒（此前约 10 秒即消失）
2. `wechat-cli sessions` 的**会话时间戳开始推进**（仍是旧日期 = 没修好）
3. 目标群 `unread` 归零
4. `find .../db_storage/message -type f -newermt '-3 minutes'` 有写入

积压多天时同步需要几分钟，**此期间不要再次启动/杀掉微信**，否则会打断补齐。

**预防**：任何拉取前先跑 `wechat_preflight.py`。微信没运行 → 直接中止任务，
不要让自动化空跑到超时（历史上连续空跑 30–75 分钟被取消）。

## 前置检查

### 检查 wechat-cli 安装状态

```bash
which wechat-cli
```

如果未安装，提示用户执行：
```bash
npm install -g @canghe_ai/wechat-cli
# 或
pip install wechat-cli
```

### 初始化微信数据访问

首次使用需要初始化：
```bash
sudo wechat-cli init
```

> ⚠️ macOS 用户需要授予终端「完全磁盘访问权限」

### macOS 报错 `task_for_pid failed`

部分 macOS 系统上，**即使用 `sudo` 运行，`init` 仍可能失败并报 `task_for_pid failed`**。这是 macOS 对「进程内存访问」的安全限制，与磁盘权限无关，所以授予完全磁盘访问权限也解决不了。

`wechat-cli` 会自动尝试修复：给 WeChat 重新签名并附加所需 entitlement（**原有 entitlements 会被保留**）。按屏幕提示操作即可：

1. 工具自动重新签名 WeChat
2. **完全退出**微信（不是最小化，用 `⌘Q` 或右键退出）
3. 重新打开微信并登录
4. 再次运行 `sudo wechat-cli init`

如果自动重签名失败，可手动执行（先完全退出微信）：

```bash
sudo codesign --force --sign - --entitlements /dev/stdin /Applications/WeChat.app <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.get-task-allow</key>
    <true/>
</dict>
</plist>
EOF
```

重签名完成后重新打开微信、登录，再执行 `sudo wechat-cli init`。

> 说明：`get-task-allow` 只放开**进程内存读取**，供 `init` 阶段探测数据结构用。本技能的 V2 图片解密走**磁盘派生密钥**路线（见下文），并不依赖该 entitlement——即使 init 暂时不可用，图片解密仍可独立完成。
>
> 副作用提醒：重签名会让微信的签名指纹变化，个别系统安全策略（如企业 MDM）可能提示异常；如遇问题可用同一命令重新签名回原状态，或升级/重装微信后重试。

## 核心命令参考

### 会话管理
```bash
wechat-cli sessions                    # 最近会话列表
wechat-cli sessions --limit 10        # 指定数量
wechat-cli unread                     # 未读会话
```

### 聊天记录读取
```bash
wechat-cli history "联系人/群名" --limit 50           # 最近50条
wechat-cli history "联系人" --start-time "2026-01-01" --end-time "2026-01-31"  # 时间范围
wechat-cli history "群名" --type link                  # 仅链接类消息
```

### 搜索功能
```bash
wechat-cli search "关键词"                              # 全局搜索
wechat-cli search "deadline" --chat "项目群"          # 指定聊天搜索
wechat-cli search "会议" --type text                   # 仅文本消息
```

### 联系人与统计
```bash
wechat-cli contacts --query "姓名"     # 搜索联系人
wechat-cli stats "群名"               # 群聊统计
wechat-cli members "群名"            # 群成员列表
```

### 导出功能
```bash
"$BINARY" export "联系人" --format markdown --output chat.md
"$BINARY" favorites                   # 微信收藏
```

## 链接URL补全流程（群聊总结必做步骤）

### 背景

微信的「[链接]」类型消息（分享的文章卡片，type=49）在 wechat-cli 中**只输出标题**，URL存储在消息XML中，wechat-cli 目前不暴露。

有两种情况需要区分：
- **文本消息里直接有URL**（如 `https://luma.com/xxx`）→ 原样保留，无需处理
- **[链接] 卡片消息**（如 `[链接] Token必须死？`）→ 需要通过搜索引擎补全URL

### 补全步骤

1. **获取所有链接消息标题**：
```bash
"$BINARY" history "群名" --start-time "YYYY-MM-DD" --end-time "YYYY-MM-DD" --type link > /tmp/links.json 2>&1
```

2. **过滤出有效标题**（跳过「当前微信版本不支持」的消息）：
提取 `messages` 数组中 `[链接] ` 后的标题，排除含「不支持展示该内容」的条目。

3. **搜索补全URL**：
对每个标题用 WebSearch 工具搜索，取第一个相关结果的URL。
格式：`[标题](URL)` 供 Obsidian 直接使用。

4. **写入总结文件**：
在 Obsidian 总结文件的「重要报告与文章」或「链接汇总」表格中，将 `[链接] 标题` 替换为 `[标题](URL)`。

### 示例
```
原消息：[链接] Token必须死？
搜索词：Token必须死 AI
找到URL：https://m.huxiu.com/article/4861200.html
Obsidian格式：["Token"必须死？](https://m.huxiu.com/article/4861200.html)
```

### 批量处理建议
- 每次总结一般有 20-40 条链接，可并发搜索提升效率
- 搜索不到的链接标注 `（链接待补全）` 而非留空
- `[链接/文件]-不支持的消息` 无法获取标题和URL，直接跳过

## V2 图片解密（macOS 群聊图片必做步骤）

### 背景

微信 Mac 4.x 客户端的图片采用 **WxV2 加密格式**（[6B magic: 07 08 56 32 08 07] + AES 密文 + 原始数据 + XOR 密文），无法直接打开。
好消息：**密钥可从磁盘派生，无需 sudo 或进程内存访问。**

### 核心算法（来自 r266-tech/wxkey）

```python
aes_key = hex(MD5(str(code) + wxid))[:16]   # 16 字符
xor_key = code & 0xFF                        # 0-255
# code = key_{code}_{rest}.statistic 文件名第一段（uint32）
# wxid = xwechat_files 子目录名去尾 _hex4 后缀（如 <wxid>_<hex4> → <wxid>）
```

### 一键解密 TGO 群聊图片

```bash
PY="python3"
SCRIPT="scripts/wechat_v2_image_decrypt.py"   # 相对于本 skill 目录

# 1. 仅派生并显示密钥（不解密）
"$PY" "$SCRIPT" --derive-only

# 2. 解密 TGO 群指定月份所有图片到 Obsidian（默认输出见下表）
"$PY" "$SCRIPT" --tgo --months 2026-07 \
    --output "~/Documents/obsidian/ppj/30-AI与大模型/资料附件/群聊图片/2026-07"

# 3. 测试模式（只解 5 个文件）
"$PY" "$SCRIPT" --tgo --months 2026-07 --output /tmp/test --limit 5 --verbose
```

### 默认路径（脚本内置，均可用环境变量覆盖）

| 项目 | 路径 | 覆盖方式 |
|------|------|---------|
| 微信容器 | `~/Library/Containers/com.tencent.xinWeChat/Data/Documents` | `WECHAT_CONTAINER` |
| 用户子目录 | `xwechat_files/<wxid>_<hex4>`（自动发现最新的一个） | `WECHAT_WXID_DIR` |
| TGO 群 attach | `msg/attach/372ccdfb50bce33523e512d8f22a22ae/{YYYY-MM}/Img/` | `TGO_ATTACH_HASH` / `--attach-dir` |
| Obsidian 输出 | `~/Documents/obsidian/ppj/30-AI与大模型/资料附件/群聊图片/{YYYY-MM}/` | `TGO_OBSIDIAN` / `--output` |
| 密钥缓存 | `~/.cache/wechat-v2-decrypt/image_key.json` | — |
| 解密清单 | 输出目录下的 `decrypt_manifest.json` | — |

> 默认的 attach hash 属于 TGO 群，换群时请用 `--attach-dir` 指定该群的 attach 目录（位于 `xwechat_files/<wxid>_<hex4>/msg/attach/<hash>/`）。

### 输出文件命名规则

```
<md5>_<MMDD>_<类型>.<格式>
类型: orig / hd / thumb
格式: jpg / png / hevc（wechat 专有视频容器）
```

### 关键限制

- **wxid 不匹配 → 无法派生**：如果切换了微信账号，用 `WECHAT_WXID_DIR` 环境变量指定新的 `xwechat_files/<wxid>_<hex4>` 目录
- **格式检测**：`file` 命令不识别微信 `wxgf` 视频容器（显示为 `data`），但解密正确，可在微信中或专用播放器打开
- **缩略图（`_t.dat`）**：当原图/高清版已存在时自动跳过，避免重复
- **V1 格式（极旧版本）**：使用固定密钥 `cfcd208495d565ef`（= MD5("0")[:16]），脚本自动处理

### 排查清单

| 症状 | 原因 | 解决 |
|------|------|------|
| `PermissionError: image_key.json` | `~/.wechat-cli/` 是 root 拥有 | 脚本已默认写到 `~/.cache/wechat-v2-decrypt/` |
| `磁盘派生失败` | kvcomm 缓存目录被清理 | 重新登录微信生成新缓存 |
| 解密后 `file` 显示 data | 正常，wxgf 是微信专有格式 | 用 ffmpeg `-i` 或微信播放 |
| 188 个文件但只有 50 个有图 | 部分月目录为空月 | 检查 `find ... -name "*.dat" \| wc -l` |

## Obsidian Vault 检测

### 获取 Obsidian Vault 列表

在 macOS 上，Obsidian vault 配置存储在：
```
~/Library/Application Support/obsidian/obsidian.json
```

**检测步骤：**

1. 读取 Obsidian 配置文件：
```bash
cat ~/Library/Application\ Support/obsidian/obsidian.json
```

2. 解析 vault 信息：
```json
{
  "vaults": {
    "vault_id_1": {
      "path": "/Users/xxx/Documents/obsidian/vault1",
      "ts": 1234567890,
      "open": true
    },
    "vault_id_2": {
      "path": "/Users/xxx/另一个笔记库",
      "ts": 1234567890,
      "open": false
    }
  }
}
```

3. **优先规则**：
   - 如果只有一个 vault，直接使用
   - 如果有多个 vault，询问用户选择
   - 优先使用 `open: true` 的 vault

### Obsidian 存储路径

**重要**：Obsidian vault 路径不是 `~/Obsidian/`，而是实际配置的路径。

常见路径格式：
- `/Users/{用户名}/Documents/obsidian/{vault名}/`
- `/Users/{用户名}/{自定义路径}/`

## 智能信息提取流程

### 步骤1：获取原始数据

根据用户需求选择合适的命令获取聊天记录：

- **日常浏览**：`wechat-cli sessions --limit 20`
- **特定联系人**：`wechat-cli history "姓名" --limit 100 --format json`
- **关键词搜索**：`wechat-cli search "关键词" --limit 50 --format json`

### 步骤2：识别关键信息

从聊天内容中智能识别以下类型的信息：

| 类型 | 识别关键词 | 示例 |
|------|-----------|------|
| 任务/待办 | "需要做"、"麻烦"、"帮我"、"记得" | "记得明天帮我带文件" |
| 截止日期 | "截止"、"deadline"、"周X"、"X号" | "这个任务截止到周五" |
| 会议/约定 | "会议"、"约"、"几点"、"什么时候" | "我们约明天下午3点开会" |
| 电话/联系方式 | "电话"、"微信"、"加我" | "加我微信: xxx" |
| 地址/位置 | "地址"、"去哪"、"位置" | "公司地址是xxx" |
| 金额/交易 | "多少钱"、"转账"、"收款" | "这个产品298元" |
| 重要文件 | "文件"、"发给你"、"附件" | "我把合同发给你" |

### 步骤3：分类存储

根据信息类型选择存储目标：

#### 存储到 Obsidian

**重要**：先检测 Obsidian vault 的实际路径，不要假设为 `~/Obsidian/`。

**步骤**：

1. **检测 Obsidian vault 路径**：
```bash
# 读取 Obsidian 配置文件
cat ~/Library/"Application Support"/obsidian/obsidian.json

# 解析 JSON，获取 vault 路径
# 格式：{"vaults":{"vault_id_1":{"path":"/actual/path","ts":...,"open":true}}}
```

2. **确定目标路径**：
   - 如果只有一个 vault，直接使用
   - 如果有多个 vault，询问用户选择
   - 优先使用 `open: true` 的 vault

3. **按类型创建/更新笔记**（使用检测到的 vault 路径）：
   - **任务** → `{vault_path}/待办事项/{日期}.md`
   - **会议** → `{vault_path}/会议记录/{日期}-{主题}.md`
   - **联系人** → `{vault_path}/联系人/{姓名}.md`
   - **项目** → `{vault_path}/项目/{项目名}/相关沟通.md`
   - **幼儿教育** → `{vault_path}/幼儿教育/{主题分类}/`

**注意**：
- Vault 路径可能包含空格（如 `/Users/xxx/Documents/obsidian/ppj/`），复制文件时需要用引号包裹路径
- 如果无法读取 Obsidian 配置，再回退到询问用户

**Obsidian 笔记模板格式**：
```markdown
---
type: wechat-extract
source: {联系人/群名}
created: {当前日期}
tags: [#微信 #待办] 或 [#微信 #会议]
---

# {标题}

## 原始内容
> {引用原文}

## 提取信息
{关键字段}

## 提取时间
{当前时间}

## 相关上下文
{周围聊天内容}
```

#### 存储到日历

对于包含明确时间的事项，创建日历事件：

1. 识别时间表达式（"明天3点"、"周五下午"、"下周一"）
2. 构建日历事件：
   - 事件标题：从聊天内容提取
   - 开始/结束时间：基于识别的时间
   - 提醒：提前15-30分钟
   - 备注：完整聊天上下文

**使用腾讯会议技能创建会议**（如涉及多方）：
```bash
# 调用 tencent-meeting-skill 创建会议
```

## 使用场景示例

### 场景1：整理项目沟通

```
用户：帮我把「项目A群」里关于「周五上线」的消息整理一下
```

执行流程：
1. `wechat-cli search "上线" --chat "项目A群" --format json`
2. 提取所有相关消息
3. 创建 Obsidian 笔记：`项目/项目A/周五上线沟通.md`
4. 如有明确时间，创建日历提醒

### 场景2：提取待办事项

```
用户：从和老板的聊天记录里找出所有待办
```

执行流程：
1. `wechat-cli history "老板" --limit 200 --format json`
2. 筛选包含待办关键词的消息
3. 生成待办清单
4. 存储到 `~/Obsidian/待办/老板安排.md`

### 场景3：备份重要联系人信息

```
用户：把最近加的联系人信息存到笔记里
```

执行流程：
1. `wechat-cli contacts --query "关键词"`
2. 获取联系人详情
3. 创建 Obsidian 联系人笔记

## 输出格式规范

### 终端输出
使用 `--format text` 参数获取人类可读的输出格式。

### JSON 输出
使用 `--format json` 参数获取结构化数据，便于程序处理。

### 文件导出
使用 `--output {文件名}` 将内容导出到文件。

## 注意事项

1. **隐私保护**：微信数据仅本地处理，不上传任何数据
2. **微信运行要求**：执行命令时微信需处于运行状态
3. **权限要求**：macOS 需授予「完全磁盘访问权限」
4. **首次使用**：先运行 `sudo wechat-cli init` 初始化；若报 `task_for_pid failed`，按上文「macOS 报错 `task_for_pid failed`」处理（与磁盘权限无关）
5. **Obsidian 路径检测**：**必须先检测 Obsidian vault 的实际路径**，不要假设为 `~/Obsidian/`
   - 读取 `~/Library/Application Support/obsidian/obsidian.json`
   - 解析 `vaults` 字段获取实际路径
   - 示例：`~/Documents/obsidian/<vault名>/`（不是 `~/Obsidian/`）
6. **时间识别**：时间表达式的解析需结合上下文确认准确性
7. **文件权限**：微信本地文件默认只读（`-r--r--r--`），复制后可能需要修改权限

## 错误处理

| 错误信息 | 解决方案 |
|---------|---------|
| "微信未运行" | 启动微信后重试 |
| "需要初始化" | 运行 `sudo wechat-cli init` |
| `task_for_pid failed`（init 时） | macOS 进程内存访问限制，与磁盘权限无关；见上文「macOS 报错 `task_for_pid failed`」，重新签名 WeChat 后重启并重试 |
| "权限被拒绝" | 检查终端是否具有完全磁盘访问权限 |
| "找不到联系人" | 使用 `wechat-cli sessions` 确认正确的联系人名称 |
