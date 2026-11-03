---
name: wechat-smart-organizer
description: 微信聊天记录智能整理技能。当用户想要读取微信聊天记录、提取关键信息、存储到Obsidian笔记、或创建日历事件时使用此技能。功能包括：查询会话、读取聊天记录、搜索关键词、提取任务/时间/待办事项、智能分类存储到Obsidian、创建日历提醒、自动补全链接URL。
agent_created: true
version: 1.8.0
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
PY=/Users/peterpan/.workbuddy/binaries/python/envs/default/bin/python3
SCRIPT="/Users/peterpan/.workbuddy/skills/wechat-smart-organizer/scripts/wechat_preflight.py"
"$PY" "$SCRIPT"          # 人类可读输出
"$PY" "$SCRIPT" --json   # 机器可读（供自动化判断）
"$PY" "$SCRIPT" --chat "5-TGO和朋友们的AGI"   # 指定目标群（默认即 TGO 群）
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
> 按全局最新判断会在**目标群其实没数据**时误报"数据新鲜"（2026-10-17 实测踩过这个坑）。
> `--json` 输出里的 `judged_by` 字段会告诉你这次是依据哪个会话判断的。

> ⚠️ **"数据新鲜"≠"区间数据完整"**：客户端重连后**只同步各会话的最新消息**（用于刷新会话列表），
> 某个群的完整历史需要**在微信里打开该群**才会从服务器拉取。因此若目标群"最后消息时间正常"
> 但"目标区间消息条数明显偏少"（例如某几天完全没有消息），应先让用户在微信里打开该群补齐，
> 再生成总结——不要把"缺口"当成"群里那几天很安静"。

### 关键排查经验：微信"启动即退出"（无窗口）

**症状**：前置检查报 `微信未运行`；手动 `open -b com.tencent.xinWeChat` 后主进程只活约 10 秒
就消失；`wechat-cli sessions` 的会话时间戳全部冻结在某个过去时刻。

**机制（2026-10-17 实测确认）**：

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

#### ⚠️ 先判断「是否真的需要重新 init」

**重新签名是不可逆的**：`codesign --force --sign -` 会把 App Store 原始签名替换为 ad-hoc 签名，**没有命令能改回去**，只能从 App Store 重新下载安装整个 App 才能恢复。所以在动手前先确认真的需要：

```bash
# 1) 已有密钥是否还能用？（绝大多数情况可以，密钥存在即不必重新 init）
ls -la ~/.wechat-cli/all_keys.json
# 2) 当前签名是不是已经是 adhoc？（说明之前已经签过一次，别再签）
codesign -dvvv /Applications/WeChat.app 2>&1 | grep -E "Signature|TeamIdentifier"
```

**关键事实（实测）**：

| 事实 | 含义 |
|---|---|
| `get-task-allow` 只对**重签名之后新启动**的进程生效 | 正在运行的微信仍没有该权限，`task_for_pid` 必然继续失败，**必须重启微信** |
| 重签名会保留原 entitlements（sandbox / app-groups / network 等） | 微信功能通常不受影响，`codesign --verify` 仍通过 |
| 但 `Signature=adhoc`、`TeamIdentifier=not set` | App Store 更新可能失败，只能靠重装恢复官方签名 |
| `task_for_pid` 失败**不代表密钥不可用** | 老的 `all_keys.json` 往往仍能解开本地库，不必为此重签 |

> 建议：**除非确实读不到数据，否则不要跑 `sudo wechat-cli init`**。本技能的图片解密、DB 导出都只用磁盘密钥，与 `init` 无关。

#### 消息显示为「当前微信版本不支持展示该内容」

`wechat-cli` 遇到不认识的消息类型（常见于**视频号转发**）会输出
`[链接/文件] 当前微信版本不支持展示该内容，请升级至最新版本。`

**这句话是 `wechat-cli` 的兜底文案，不是库里存的内容**（实测：17 个本地库里搜不到该字符串，`wechat-cli search` 也为 0 命中）。原始载荷仍在磁盘上，只是解析器读不出来。

推荐解法（按成本从低到高）：

1. **收藏法（最省事，已验证）**：在手机上把这批消息**收藏**，然后
   ```bash
   wechat-cli favorites --type video --limit 30 --format json
   wechat-cli favorites --limit 30 --format json
   ```
   收藏会保存完整标题/描述，实测 `--type video` 能返回视频号的完整文案。**不需要 sudo、不需要解密、不需要改微信签名。**
2. **手机复制链接** → 转发到「文件传输助手」或直接粘贴给 Agent。
3. **手机「聊天记录迁移到电脑」** → 同时补齐历史缺失区间。

> 不要为这类消息去重签微信或反复折腾 `init`——投入产出比极低，收藏法一条命令就解决。

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

## 微信收藏文章精读

### 1. 取收藏清单

```bash
"$BINARY" favorites --limit 500 --format json > /tmp/fav.json
"$BINARY" favorites --type article --limit 50 --format json   # 只看文章
```

返回字段只有 `id / type / time / summary / from / source_chat`，**没有 URL**。

### 2. 从收藏库取原文链接

`favorite.db` 里每条 `<favitem>` 是完整明文 XML，含 `pagetitle` / `pagedesc` / `link`：

```bash
PY=/Users/peterpan/.workbuddy/binaries/python/envs/default/bin/python3
"$PY" ~/.workbuddy/skills/wechat-smart-organizer/scripts/wechat_db_dump.py \
    --db favorite/favorite.db --mode msgs > /tmp/fav_msgs.txt
```

用 `<favitem type="5">` 定位文章类，正则取 `<link>…</link>`，记得 `html.unescape`（URL 里是 `&amp;`）。

> ⚠️ 多数 `<favitem>` **没有 `<createtime>`**（只有少数有）。**日期一律以 `favorites` CLI 返回的 `time` 为准**，用标题匹配库里条目，不要试图在库里按时间筛。

### 3. 取全文（关键坑）

`mp.weixin.qq.com` 对非浏览器请求一律返回「环境异常，完成验证后即可继续访问」——
`curl` 加浏览器 UA 也一样（返回的是 JS 空壳，不存在 `js_content`）。

**可行做法**：用**标题**做 WebSearch，结果里常能直接带出大段正文；再对可读镜像 WebFetch 取全文。
常见镜像：`53ai.com`、`c163.com` / `163.com`、`news.qq.com`、`leiphone.com`、`bestblogs.dev`、`ima.qq.com`。

> 判断抓取是否成功：页面应出现 `js_content` 或大段正文中文；如果只剩「视频 小程序 赞」这类导航文字，就是被验证页拦了。

### 4. 精读产出

写入 Obsidian（建议单独目录 `收藏精读/`，命名 `收藏精读_{起}_{止}.md`），结构建议：
清单表 → 一句话导读 → 逐篇精读（论点/论据/数据/我的判断）→ **横向对照** → 可落地清单 → 金句 → 抓取说明与原文链接。

> 多篇同主题时**不要逐篇平行总结**。找出它们互相矛盾的地方（对瓶颈的判断不同、数据不可比），那才是精读的价值。

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
- 搜索不到的链接标注 `（未检索到公开地址）` 而非留空
- `[链接/文件]-不支持的消息` 无法获取标题和URL，直接跳过
- `mp.weixin.qq.com` 对 curl / WebFetch **一律返回「环境异常」验证页**（JS 空壳，无 `js_content`），
  加浏览器 UA 也没用。只能靠 WebSearch 拿镜像/转载地址（53ai、163、qq、凤凰、huxiu 等）

### 大规模补全（>20 条）：必须用可恢复脚本

**踩过的坑**：一次性补 80+ 条链接时，若「先全部搜完再一次性回写」，一旦被中断
（499 canceled / 超时 / 后端重启）**全部成果归零**。实测两次运行分别死在 953s、977s，
各完成约 10 次搜索，文件仍是 84 条 `(待补全)`。

`scripts/report_links.py` 把进度从「模型上下文」搬到磁盘，做到**可恢复 + 幂等**：

```bash
PY="python3"
LINKS="scripts/report_links.py"
REPORT="/path/to/群聊总结_xxx.md"

"$PY" "$LINKS" status --report "$REPORT"                    # 进度：仍有几条待补
"$PY" "$LINKS" list   --report "$REPORT" --limit 5          # TSV：编号<TAB>日期<TAB>标题

# 每确认一条立即落盘（sidecar: 同名 .links.json）
"$PY" "$LINKS" record --report "$REPORT" --index 11 --url "https://..."
"$PY" "$LINKS" record --report "$REPORT" --index 13 --unresolved

# 每批结束立刻回写（幂等，可反复执行）
"$PY" "$LINKS" apply  --report "$REPORT"
```

**必须遵守的三条纪律**
1. **`apply` 之前不开下一批搜索**——宁可少搜几条，也不能让结果只停在内存里
2. **单轮上限 12–15 条**（约 13 分钟）。超过这个量级就会撞上被杀的时间点
3. **剩余条目留给下一轮**——脚本会跳过已完成的，续跑天然接续

`apply` 会把状态行改写成累计口径：
`> 状态：链接补全 28/84（可打开 24 · 无公开地址 4），剩余 56 条待补｜更新于 ...`

### 上游配套：控制表格规模

第二阶段每轮只能稳定处理 12–15 条，所以**第一步写骨架时链接表最多 30 条**
（只收头部要闻/投融资/技术产品相关的），其余零散链接用一行文字说明即可。
表开得越大，越做不完——这是「能完成」比「看起来全」更重要的取舍。

## 长任务写作：分段落盘

适用于周报/长文这类要写几十 KB 的任务。原则：**绝不允许把写文件放到最后一次性完成**。

1. **先落盘骨架**：结构完整（元信息、全部章节标题、闭合的表格），正文先写 `（待补充）`
2. **再逐节 Edit 填充**，每节写完立刻落盘
3. **收尾即结束**：写完不再复核、不重复读文件、不重新统计

这样任何时刻被打断，磁盘上都有一个可用的产物，而不是零产出。
历史教训：11/01 那次第一阶段跑了 39 分钟，产出完整但因为后端重启打断收尾，
状态只能记为 `partial_delivered`；若过程中已分段落盘，中断也只是「少最后一节」。

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
SCRIPT="/Users/peterpan/.workbuddy/skills/wechat-smart-organizer/scripts/wechat_v2_image_decrypt.py"
PY="/Users/peterpan/.workbuddy/binaries/python/envs/default/bin/python3"

# 1. 仅派生并显示密钥（不解密）
"$PY" "$SCRIPT" --derive-only

# 2. 解密 TGO 群当前月份所有图片到 Obsidian
"$PY" "$SCRIPT" --tgo --months 2026-07 \
    --output "/Users/peterpan/Documents/obsidian/ppj/30-AI与大模型/资料附件/群聊图片/2026-07"

# 3. 测试模式（只解 5 个文件）
"$PY" "$SCRIPT" --tgo --months 2026-07 --output /tmp/test --limit 5 --verbose
```

### 默认路径（脚本内置）

| 项目 | 路径 |
|------|------|
| 微信容器 | `~/Library/Containers/com.tencent.xinWeChat/Data/Documents` |
| 用户子目录 | `xwechat_files/wpppj001_1414` |
| TGO 群 attach | `msg/attach/372ccdfb50bce33523e512d8f22a22ae/{YYYY-MM}/Img/` |
| Obsidian 输出 | `~/Documents/obsidian/ppj/30-AI与大模型/资料附件/群聊图片/{YYYY-MM}/` |
| 密钥缓存 | `~/.cache/wechat-v2-decrypt/image_key.json` |
| 解密清单 | 输出目录下的 `decrypt_manifest.json` |

### 输出文件命名规则

```
<md5>_<MMDD>_<类型>.<格式>
类型: orig / hd / thumb
格式: jpg / png / hevc（wechat 专有视频容器）
```

### wxgf（HEVC 静帧）解码：解出来的 `.hevc` 打不开怎么办

微信 4.x 的图片有一类走 `wxgf` 容器，解码脚本会输出 `*.hevc`，但：

- `file` 显示 `data`（不是标准 HEIF/MP4，没有容器头）
- **`sips` / 预览 / 双击都打不开**；系统自带 `ffmpeg` 通常也没有

结构：文件头是 ASCII `wxgf` + 约 36 字节元数据，**真正的 HEVC Annex-B 码流从 `00 00 00 01 40 01`（VPS）开始**。

可靠解法（纯 Python，不依赖系统 ffmpeg）：

```bash
PY=/Users/peterpan/.workbuddy/binaries/python/envs/default/bin/python3
"$PY" -m pip install av          # PyAV，自带 FFmpeg 库
```

```python
import av
data = open('xxx.hevc','rb').read()
i = data.find(b'\x00\x00\x00\x01\x40\x01')   # 跳过 wxgf 头
open('/tmp/x.h265','wb').write(data[i:])
c = av.open('/tmp/x.h265', format='hevc')
for fr in c.decode(video=0):
    fr.to_image().save('xxx.png')             # 只取第一帧
    break
```

> 注意：不要把 `.hevc` 直接交给 `av.open()`，必须先剥掉 `wxgf` 头，否则解不出帧。
> 同理，`_t.dat` 解出的 `_t.jpg` 往往只有 200–500px 宽，**只够看轮廓，不能用于 OCR 或打印**，必须解全尺寸文件。

### 从截图批量做题面 PDF（试卷重组）

手机截屏发来的题目常见形态：**每张图是一道题**，底部带 `【答案】：xxx`。重组成无答案试卷：

1. **排序**：不要用文件 mtime（同一批图时间戳可能只差 1–2 秒且乱序）。用 OCR 读出图片里的 `第 N 题`，按 N 排序。
2. **抹答案**：OCR 返回每段文字的 bbox，取包含 `答案` 的那一段，把 `[y-6, y+h+7]` 整行涂白。
   ⚠️ **不要"从答案行涂到图片底部"**——有的题答案在题干下方、图形上方，涂到底会把图删掉。
3. **排版**：按版心宽度等比缩放（同一批截图字号一致，**必须用统一缩放比例**，不要逐题拉伸），A4 流式拼版，放不下就换页。
4. **验收**：抹完再 OCR 一遍，确认 `答案` 命中数为 0；并渲染成 PNG 目视检查有没有误删。

macOS 上的 OCR 用系统 Vision 即可（无需装 tesseract）：

```bash
"$PY" -m pip install pyobjc-framework-Vision pyobjc-framework-Quartz
```

`VNRecognizeTextRequest` + `recognitionLanguages=["zh-Hans","en-US"]`，
`recognitionLevel` 设为 `0`（accurate）；bbox 是归一化坐标且**原点在左下**，
换算成像素：`y = (1 - origin.y - size.height) * H`。

> Swift 方案（`swiftc` + Vision）在本机会因 **Swift 6.3 与 macOS 26 SDK(6.4) 不匹配** 编译失败，直接用 pyobjc 更省事。

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

## 按群归档：图片 + 附件 → Obsidian

用户说「把某某群最近一个月的图片/附件存到 Obsidian」时走这套流程。**核心难点是找到该群的 attach 目录**——它不是按群名，而是 `md5(chatroom_id)`。

### 1. 定位 attach 目录

```bash
# a) 取 chatroom_id：解密 contact.db 搜群名
python3 - <<'EOF'
import json, os, re
from Crypto.Cipher import AES
KEYS=json.load(open(os.path.expanduser("~/.wechat-cli/all_keys.json")))
ROOT=os.path.expanduser("~/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/<wxid>_<hex4>/db_storage")
rel="contact/contact.db"; PAGE,R=4096,80
data=open(os.path.join(ROOT,rel),'rb').read(); key=bytes.fromhex(KEYS[rel]["enc_key"])
out=bytearray()
for i in range(len(data)//PAGE):
    pg=data[i*PAGE:(i+1)*PAGE]; sk=16 if i==0 else 0
    out+=AES.new(key,AES.MODE_CBC,pg[PAGE-R:PAGE-R+16]).decrypt(pg[sk:PAGE-R])
p=bytes(out)
i=p.find("群名关键字".encode())
print(p[max(0,i-300):i+100].decode("utf-8","replace"))
EOF

# b) attach 目录名 = md5(chatroom_id)
python3 -c "import hashlib;print(hashlib.md5(b'56901689217@chatroom').hexdigest())"
```

> 已验证：`md5("44136003054@chatroom") == 372ccdfb50bce33523e512d8f22a22ae`（TGO 群），规则可靠。

### 2. 判断图片真实可用质量（**最重要的一步**）

同一张图最多有 3 个文件，必须按体积取最大者：

| 后缀 | 含义 | 用途 |
|---|---|---|
| `<md5>_t.dat` | 缩略图 | 常仅 180–210 px，**只能看版式，不能读文字** |
| `<md5>.dat` | 普通图（wxgf/HEVC 容器） | 需解密 + 转码 |
| `<md5>_h.dat` | 高清原图 | 最优 |

**关键事实：微信只在「打开该会话」时才下载原图。** 群里有未读 → 多数图只有 `_t.dat`。所以：
- 先统计 `find ... -name "*_t.dat" | wc -l` 与 `-name "*.dat" ! -name "*_t.dat"` 的比例
- 若绝大多数只有缩略图，**如实告知用户**并给出补齐办法（让他打开群往上滚一下，再重跑），不要假装归档完整

按 base 去重取最优：

```python
base = re.sub(r'(_t|_h)?\.dat$', '', name)   # 同图分组
items.sort(reverse=True)                     # 体积降序 → [0] 即最高画质
```

### 3. 归档命名

`<YYYYmmdd_HHMMSS>_<hd|full|thumb>_<hash8>.jpg`，按 `月的 .dat mtime` 分 `图片/YYYY-MM/`。
日期用**源 `.dat` 的 mtime**（≈接收时间），不要用解密输出文件的 mtime（是复制时间）。

### 4. 附件

`msg/file/YYYY-MM/` 下按文件名 `find`，复制后必须 `md5` 比对并 `chmod u+w`（微信文件常是只读）。

### 5. 索引笔记

在归档目录写 `README.md`，至少包含：数据概况表、附件表（带 `[[附件/...]]` 链接）、图片清单、**数据说明**（缺失日期、缩略图比例、占位符条数）。
表格内的 wiki 链接别名要写 `\|`（反斜杠转义竖线），否则表格会被截断。

## 按群导出视频（无损，按 md5 精确匹配）

用户说「把某群的视频都下载下来」时走这套流程。产出**明文 MP4**，不涉及解密。

### 1. 取视频清单

```bash
wechat-cli history "<群名>" --type video --limit 500 --format json > /tmp/videos.json
```

`messages` 是字符串数组（`[时间] 发送者: [视频] <msg><videomsg .../></msg>`），
自己用正则抽 `md5` / `rawmd5` / `newmd5` / `length` / `rawlength` / `playlength`。

- `md5` → 压缩版；`rawmd5` → 原画（可达 150–320MB）；两者都命中时优先原画。
- 部分消息**只有 `newmd5`**（转发/新容器），此值与本地文件 MD5 对不上，只能退化为
  「字节数 + 时长」双条件且**全库唯一命中**才可认定，并在清单里标注「推定」。

### 2. 定位视频目录并全量 MD5

```bash
V=~/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/<wxid>_<hex4>/msg/video
find "$V" -name "*.mp4" -print0 | xargs -0 -n1 -P8 md5 -r > /tmp/mp4_md5.txt
```

- 微信 4.x 的聊天视频就是**标准可播放 MP4**，按 `YYYY-MM/` 分月存放，无需解密。
- 文件名的 `<hash>` **不是**消息里的 md5；但**文件内容 MD5 == 消息 XML 的 md5**（实测一致）。
- 所以精确匹配必须对整个 `msg/video` 做 MD5，**不能**靠文件名、大小或时长（只靠大小+时长会错配）。
- 已导出目录也要做一次 MD5，用来跳过重复导出。

### 3. 导出与校验

命名 `YYYYmmdd_HHMM_<序号>_<发送者>.mp4`，`cp -p` 后 `chmod u+w`（微信文件常只读）。
机器上通常没有 `ffprobe`；校验时长用 macOS 自带：

```bash
mdls -raw -name kMDItemDurationSeconds file.mp4   # 刚拷的文件可能返回 (null)
```

`(null)` 时不要当成坏文件——直接解析 `moov/mvhd`（纯 Python，无需依赖）即可拿到时长，
与消息 `playlength` 对齐视为通过。

### 4. 必须有清单

输出目录写 `清单.md`：总数 / 已导出 / 未下载三个数字 + 已导出表（序号、时间、时长、画质、文件名）+ 未下载表（时间、时长、大小）+ 补齐说明。
未下载不是脚本 bug：**微信只有被点开播放过才会把视频落到本地**，`wechat-cli` 能列出元数据但不触发下载。补齐只能人工在客户端逐个点开，然后重跑本流程（幂等，靠 MD5 跳过已有）。

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
| `task_for_pid failed`（init 时） | macOS 进程内存访问限制，与磁盘权限无关；见上文「macOS 报错 `task_for_pid failed`」。**先确认是否真需要重新 init**（重签名不可逆、且必须重启微信才生效） |
| 消息显示「当前微信版本不支持展示该内容」 | 是 wechat-cli 的兜底文案，不是库内容；用 `wechat-cli favorites` 或手机复制链接，不要重签微信 |
| "权限被拒绝" | 检查终端是否具有完全磁盘访问权限 |
| "找不到联系人" | 使用 `wechat-cli sessions` 确认正确的联系人名称 |
