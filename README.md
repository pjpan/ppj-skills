# ppj-skills

个人维护的 [Agent Skills](https://code.claude.com/docs/en/skills) 集合。每个 skill 是一个独立的目录，遵循 `SKILL.md` + YAML frontmatter 的通用格式，可被支持该格式的 agent 运行时（Claude Code、ZCode、Codex 等）自动加载或按名调用。

当前包含四个 skill：一个用于读取与整理本地微信聊天记录（含 macOS 图片解密），一个用于审计数字孪生/人格 agent 的复刻保真度，一个用于撰写和评审结构化技术报告，一个用于评审与重构面向管理层的业务/技术汇报。

## 包含的 Skills

| Skill | 解决什么问题 | 典型触发场景 |
|---|---|---|
| [`wechat-smart-organizer`](./wechat-smart-organizer/SKILL.md) | 本地微信聊天记录的读取与整理 | “帮我读一下某个群的聊天记录”“把这个群最近一周的讨论总结一下”“从聊天里找出待办/会议/联系人”“解密微信图片并存到 Obsidian” |
| [`digital-twin-fidelity-auditor`](./digital-twin-fidelity-auditor/SKILL.md) | 数字孪生/人格 agent 的复刻保真度审计 | “这个 twin 复刻了哪些维度、缺了什么”“它学到的是这个人还是一个原型”“结论有多少独立证据支撑” |
| [`structured-technical-report`](./structured-technical-report/SKILL.md) | 技术报告的结构架构与评审 | 白皮书、架构报告、研究/战略文档的撰写、重构、评审；或“内容都对但读起来不成体系” |
| [`ppj-report-review`](./ppj-report-review/SKILL.md) | 管理层汇报的逻辑诊断与重构 | 汇报评审、修改汇报逻辑、准备项目汇报、把零散材料整理成决策稿 |

---

## 1. wechat-smart-organizer

把微信聊天记录当作**本地可检索的数据源**来处理，而不是靠截图和手工复制。

核心约束（决定了它的使用方式）：

> macOS 上微信 4.x 的图片是 **V2 加密格式**（`07 08 56 32 08 07` 魔数 + AES + 原始数据 + XOR），无法直接打开；但密钥可以从磁盘缓存**离线派生**——`aes_key = hex(MD5(str(code) + wxid))[:16]`、`xor_key = code & 0xFF`——**全程不需要 sudo、也不需要读进程内存**。

### 能力

| 能力 | 说明 |
|---|---|
| 读取聊天记录 | 按会话、时间范围、消息类型（文本/链接/图片）读取；关键词搜索 |
| 智能信息提取 | 识别任务/待办、截止日期、会议约定、联系人、地址、金额、附件 |
| 链接 URL 补全 | `[链接]` 卡片消息只输出标题，需通过搜索引擎补全原文 URL，才能在笔记里直接跳转 |
| Obsidian 存储 | 先检测 vault 真实路径（不假设 `~/Obsidian/`），按类型写入任务/会议/联系人/项目笔记 |
| 日历事件 | 识别时间表达式并创建提醒；多方会议可转交会议 skill |
| V2 图片解密 | 批量解密群聊图片/视频到本地目录，附 `decrypt_manifest.json` 清单 |

### 上手要点

- `wechat-cli` 必须调用**底层二进制**（node wrapper 直接调用不输出任何内容），且输出要**先重定向到文件**再解析（管道不生效）。
- 首次使用需 `sudo wechat-cli init`，并给终端授予 macOS「完全磁盘访问权限」。
- `init` 报 `task_for_pid failed` 是 macOS **进程内存访问**限制（与磁盘权限无关）：先让 wechat-cli 自动重签名 WeChat，或按 SKILL.md 里的 `codesign` 命令手动重签名，然后完全退出微信、重新打开登录、再 init。
- 脚本默认路径全部可用环境变量覆盖（`WECHAT_CONTAINER`、`WECHAT_WXID_DIR`、`TGO_ATTACH_HASH`、`TGO_OBSIDIAN`），换机器/换账号无需改代码。
- 已知限制：`wechat-cli` 对最近几天的消息有同步延迟，补拉近几日数据可能需要隔天重试。

### 参考文档

| 文件 | 内容 |
|---|---|
| [`references/commands.md`](./wechat-smart-organizer/references/commands.md) | wechat-cli 常用命令速查 |
| [`scripts/wechat_v2_image_decrypt.py`](./wechat-smart-organizer/scripts/wechat_v2_image_decrypt.py) | V2 图片/视频离线解密（磁盘派生密钥） |
| [`scripts/extract_key_info.py`](./wechat-smart-organizer/scripts/extract_key_info.py) | 从聊天记录提取任务/时间/联系人等结构化信息 |
| [`scripts/save_to_obsidian.py`](./wechat-smart-organizer/scripts/save_to_obsidian.py) | 按类型写入 Obsidian 笔记 |

---

## 2. digital-twin-fidelity-auditor

把数字孪生当作一个**复刻系统**来审计，而不是当作一段 persona prompt。

核心证据原则：

> 写进 Prompt 只能证明设计覆盖；进入运行时只能证明机制生效；跨场景、跨时间且经过独立真人对照，才能证明高质量复刻。

### 三层审计结构

| 层 | 回答的问题 |
|---|---|
| **复刻了什么** — Replication Dimensions | 表征、认知、决策、表达、行为五个复刻层，以及元认知、持续学习、数据治理、安全授权、独立评测等横切系统 |
| **复刻得怎么样** — Replication Quality | Q1 覆盖全面性、Q2 机制有效性、Q3 个体特异性、Q4 跨场景泛化性、Q5 内部一致性、Q6 时间适应性、Q7 不确定性校准、Q8 验证可信度 |
| **能不能真正应用** — Application Readiness | A1 任务有效性、A2 可替代性、A3 风险适配、A4 授权准备度 |

三层不合并成单一分数。审计中会显式识别九类**复刻错觉**（标签覆盖、丰富度、启发式、风格、原型、历史重放、静态快照、自信、架构完整），并按 P0/P1/P2 给出关键缺口与升级优先级。

### 适用 / 不适用

- 适用：个人数字孪生、persona agent、视角 agent、角色扮演 prompt、角色 skill、user-clone 系统、委托型个人 agent 的审计与对比；复刻记分卡校验；holdout / shadow benchmark 设计。
- 不适用：不提供证据支撑的“复刻得像不像”的主观判断——该 skill 明确禁止从 prompt 丰富度、传记体量、命名启发式或风格相似度单独推断保真度。

### 参考文档

| 文件 | 内容 |
|---|---|
| [`references/dimension-rubric.md`](./digital-twin-fidelity-auditor/references/dimension-rubric.md) | 复刻维度细定义（人格、价值观、世界观、个人记忆、问题表征、世界模型等） |
| [`references/quality-rubric.md`](./digital-twin-fidelity-auditor/references/quality-rubric.md) | Q1–Q8 的详细评分标准与测试设计 |
| [`references/fidelity-benchmark.md`](./digital-twin-fidelity-auditor/references/fidelity-benchmark.md) | 基准设计：数据集切分、时间 holdout、泄漏检查、人类基线 |
| [`references/application-readiness.md`](./digital-twin-fidelity-auditor/references/application-readiness.md) | A1–A4 就绪度评分标准 |

---

## 3. structured-technical-report

让报告读起来是**成体系的思想结构**，而不是一堆各自正确的段落。

优化目标链：概念完整性 → 语义层级 → 证据 → 架构耐久性 → 独立评估 → 信息密度 → 独立成篇的终稿质量。

### 主要方法

- **先定文档契约**：读者、报告类型、必须支撑的决策、深度、是否终稿；写一句内部 thesis（“本文存在的目的是确立 ______”），据此删除有意思但结构上不必要的内容。
- **先建语义树再写正文**：H1 只放独立主题，H2 放其组成维度，H3 放定义/机制/证据；宁可少而强的顶层章节，不并列一堆同级章节。
- **总–分–总叙事**：定义与边界 → 理论基础 → 概念框架 → 分解 → 数据与假设 → 技术实现 → 独立评估 → 演进与治理 → 路线图 → 总结。
- **分离抽象层级**：理论、概念模型、产品能力、数据、系统架构、运行机制、实现技术、评估、治理不混写。
- **分离 WHAT/WHY 与 HOW**：先写耐久的需求，再提机制；对任何技术选型都问“如果明年换掉它，概念架构是否仍然成立”。
- **评价作为独立系统**：每个重要论断都要有被验证的能力、ground truth、指标、数据、基线、与构建/调参的独立性、失败分类、不确定性。
- **论断强度匹配证据强度**：区分既有事实、外部研究发现、实证结果、工程判断、假设、待验证假设、建议；不把“某次测试有效”写成“最优架构”。
- **终稿意识**：清除“原方案”“旧架构”“如之前讨论”等起草残留，改写为当前状态的原则表述。
- **修订是累积的**：提取此前已接受的约束 → 合并新反馈 → 检测冲突 → 判断改动层级 → 传播到所有受影响章节 → 全局复查术语与结构。

### 评审 8 道关

结构、概念、架构、证据、评估、技术中立性、终稿质量、修订完整性。

### 参考文档

| 文件 | 内容 |
|---|---|
| [`references/review-checklist.md`](./structured-technical-report/references/review-checklist.md) | 逐项评审清单与常见失败模式 |
| [`references/writing-principles.md`](./structured-technical-report/references/writing-principles.md) | 更深层的原理、示例与报告结构模式（仅在复杂重构或审计时加载） |

---

## 4. ppj-report-review

把草稿、项目笔记或汇报提纲转化为**便于管理层理解与决策**的材料。方法上是金字塔原理（结论先行、分层论证）与战略叙事的结合，流程是「先诊断，再重构，最后自检」。

### 三种工作模式

按请求选择**评审**、**重构**或**模板**模式；默认输出诊断与重构稿，仅要求评审时不扩写全文，仅要求模板时不虚构原稿问题。

### 一、诊断逻辑问题

围绕七个维度检查实际存在的问题，每项问题给出原文短引或位置、影响及具体修改建议，并区分「影响决策的关键问题」与「表达优化」，不为凑数制造问题。

| 维度 | 检查重点 |
|---|---|
| 业务价值 | 是否只列了做了什么，而没说为谁解决什么问题、为什么值得投入 |
| 结论与层级 | 是否结论先行；同层条目是否同一分类标准；是否把战略收益与功能任务混列 |
| 分类完整性 | 尽量 MECE（不重叠且覆盖当前范围），但不强行凑三个维度 |
| 证据与因果 | 收益是否有来源、基线、统计口径与时间范围；是否把相关性写成因果、把目标写成成果 |
| 优先级与验证 | 为什么先选这个场景；可行性、验证成本、代表性、成功标准是否清楚 |
| 执行与决策 | 交付物、里程碑、责任方、依赖、风险与资源诉求是否足以支持下一步决策 |
| 叙事衔接 | 章节间是否有因果、时间或角色递进；是否有无论据支撑的跳跃 |

**事实约束**：保留原材料的数字、单位、日期和限定条件；区分已验证事实、用户目标、推断与待验证假设。缺失信息标注「待补充」并说明需补什么证据，不编造客户、数据、试点成果、承诺或来源；不默认承诺 10 倍收益，尚无试点时给出验证计划。

### 二、重构汇报

先用一至三句话交代核心结论、证据与期望获得的决策，再默认按四阶段组织正文（用户已有强制模板时映射到该模板；按项目阶段缩减不适用部分，不把日常进展汇报扩成平台战略）。

| 阶段 | 应回答的问题 |
|---|---|
| 1. 背景与核心价值（Why） | 为什么现在做、业务价值是什么（用 SCQA 串联现状/矛盾/关键问题/回答，再以结论先行顺序呈现） |
| 2. 聚焦场景与验证（Where / How） | 为什么先做这里、如何判断有效（场景选择理由、MVP、试点证据及局限） |
| 3. 交付与推广（What） | 交付什么、给谁用、何时落地（按角色或业务环节组织，列里程碑、责任、依赖、风险） |
| 4. 后续行动与决策诉求（Next） | 需要谁决定什么、下一步如何推进（资源、支持方、决策事项、时间要求、检查点） |

### 三、默认输出

评审主要问题（按重要性列「原文依据 → 问题及影响 → 修改建议」，材料足够好时明确指出，无须强行批评）、重构后的汇报（已填入现有事实，或按用户指定格式的可直接使用稿，保留必要的「待补充」标记）、叙事改进与待补信息（两至三条表达建议 + 影响决策的最小关键补充项，建议与事实分开表述）。

### 交付前自检

So What（开头能否让读者知道业务价值与所需决策）、Why This（起点选择是否有依据、验证方案能否支持下一步）、MECE（同层分类是否一致）、事实（是否把愿景写成结果或新增无来源数字与承诺）、可行动（读者是否知道谁做什么、何时检查、还缺什么证据）。用户未要求时不输出内部自检过程。

该 skill 为自包含设计，没有 `references/`，也不依赖特定平台、联网服务或本地路径——没有文件工具时可直接处理粘贴的正文。

---

## 目录结构

```
.
├── wechat-smart-organizer/
│   ├── SKILL.md                      # 主文件：frontmatter + 工作流程
│   ├── agents/openai.yaml            # 接口元数据（display name、icon、可用产品）
│   ├── assets/icon.svg               # skill 图标
│   ├── references/
│   │   └── commands.md               # wechat-cli 命令速查
│   └── scripts/
│       ├── wechat_v2_image_decrypt.py  # V2 图片/视频离线解密
│       ├── extract_key_info.py         # 关键信息提取
│       └── save_to_obsidian.py         # 写入 Obsidian
├── digital-twin-fidelity-auditor/
│   ├── SKILL.md                      # 主文件：frontmatter + 审计流程
│   ├── agents/openai.yaml            # 接口元数据（display name、icon、可用产品）
│   ├── assets/icon.svg               # skill 图标
│   └── references/                   # 按需加载的详细评分标准
│       ├── dimension-rubric.md
│       ├── quality-rubric.md
│       ├── fidelity-benchmark.md
│       └── application-readiness.md
├── structured-technical-report/
│   ├── SKILL.md
│   ├── agents/openai.yaml
│   ├── assets/icon.svg
│   └── references/
│       ├── review-checklist.md
│       └── writing-principles.md
└── ppj-report-review/
    ├── SKILL.md                      # 自包含，无 references/
    └── agents/openai.yaml
```

## 安装与使用

把需要的 skill 目录复制或软链到你的 agent 运行时的 skills 目录即可，例如：

```bash
# 个人级安装（以 ~/.agents/skills 为例）
git clone git@github.com:pjpan/ppj-skills.git
cp -R ppj-skills/wechat-smart-organizer          ~/.agents/skills/
cp -R ppj-skills/digital-twin-fidelity-auditor   ~/.agents/skills/
cp -R ppj-skills/structured-technical-report     ~/.agents/skills/
cp -R ppj-skills/ppj-report-review               ~/.agents/skills/
```

或直接软链，便于 `git pull` 后生效：

```bash
ln -s "$PWD/ppj-skills/wechat-smart-organizer" ~/.agents/skills/wechat-smart-organizer
```

安装后由运行时根据 `SKILL.md` 的 frontmatter `description` 决定是否自动加载，也可以按名显式调用（如 `/wechat-smart-organizer`）。

> `wechat-smart-organizer` 额外依赖本机环境：`wechat-cli`、运行中的微信客户端、macOS 完全磁盘访问权限，以及脚本用的 Python 3。

### 格式说明

- `SKILL.md` 的 frontmatter 只依赖 `name` 和 `description` 两个字段，因此不绑定特定厂商的运行时；`agents/openai.yaml` 是 OpenAI/Codex 侧的接口元数据，缺失不影响其他运行时使用。
- `references/*.md` 由主文件按需引用，用来把详细评分标准、清单、设计指南与主流程分离，避免 `SKILL.md` 过长。

## 设计约定

这些 skill 共享同一套写作约定：主流程保持精简，只在需要时引导模型读取详细参考文档；概念必须可区分、术语必须一致；论断强度必须匹配证据强度，不把演示效果当作能力证据。

在目录与 `SKILL.md` 层面，所有 skill 都符合 Agent Skills 规范：frontmatter 仅使用 `name` 与 `description`（`name` 为必填、全小写连字符格式且与目录名一致），`references/` 中的每个文件都由 `SKILL.md` 显式引用并说明读取时机，主文件保持在 500 行以内。

## License

仓库暂未附带 LICENSE 文件。如需对外复用，请先补充许可证。
