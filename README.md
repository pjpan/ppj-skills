# ppj-skills

个人维护的 [Agent Skills](https://code.claude.com/docs/en/skills) 集合。每个 skill 是一个独立的目录，遵循 `SKILL.md` + YAML frontmatter 的通用格式，可被支持该格式的 agent 运行时（Claude Code、ZCode、Codex 等）自动加载或按名调用。

当前包含两个 skill：一个用于审计数字孪生/人格 agent 的复刻保真度，一个用于撰写和评审结构化技术报告。

## 包含的 Skills

| Skill | 解决什么问题 | 典型触发场景 |
|---|---|---|
| [`digital-twin-fidelity-auditor`](./digital-twin-fidelity-auditor/SKILL.md) | 数字孪生/人格 agent 的复刻保真度审计 | “这个 twin 复刻了哪些维度、缺了什么”“它学到的是这个人还是一个原型”“结论有多少独立证据支撑” |
| [`structured-technical-report`](./structured-technical-report/SKILL.md) | 技术报告的结构架构与评审 | 白皮书、架构报告、研究/战略文档的撰写、重构、评审；或“内容都对但读起来不成体系” |

---

## 1. digital-twin-fidelity-auditor

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

## 2. structured-technical-report

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

## 目录结构

```
.
├── digital-twin-fidelity-auditor/
│   ├── SKILL.md                      # 主文件：frontmatter + 审计流程
│   ├── agents/openai.yaml            # 接口元数据（display name、icon、可用产品）
│   ├── assets/icon.svg               # skill 图标
│   └── references/                   # 按需加载的详细评分标准
│       ├── dimension-rubric.md
│       ├── quality-rubric.md
│       ├── fidelity-benchmark.md
│       └── application-readiness.md
└── structured-technical-report/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── assets/icon.svg
    └── references/
        ├── review-checklist.md
        └── writing-principles.md
```

## 安装与使用

把需要的 skill 目录复制或软链到你的 agent 运行时的 skills 目录即可，例如：

```bash
# 个人级安装（以 ~/.agents/skills 为例）
git clone git@github.com:pjpan/ppj-skills.git
cp -R ppj-skills/digital-twin-fidelity-auditor ~/.agents/skills/
cp -R ppj-skills/structured-technical-report   ~/.agents/skills/
```

或直接软链，便于 `git pull` 后生效：

```bash
ln -s "$PWD/ppj-skills/digital-twin-fidelity-auditor" ~/.agents/skills/digital-twin-fidelity-auditor
```

安装后由运行时根据 `SKILL.md` 的 frontmatter `description` 决定是否自动加载，也可以按名显式调用（如 `/digital-twin-fidelity-auditor`）。

### 格式说明

- `SKILL.md` 的 frontmatter 只依赖 `name` 和 `description` 两个字段，因此不绑定特定厂商的运行时；`agents/openai.yaml` 是 OpenAI/Codex 侧的接口元数据，缺失不影响其他运行时使用。
- `references/*.md` 由主文件按需引用，用来把详细评分标准、清单、设计指南与主流程分离，避免 `SKILL.md` 过长。

## 设计约定

这两个 skill 共享同一套写作约定：主流程保持精简，只在需要时引导模型读取详细参考文档；概念必须可区分、术语必须一致；论断强度必须匹配证据强度，不把演示效果当作能力证据。

## License

仓库暂未附带 LICENSE 文件。如需对外复用，请先补充许可证。
