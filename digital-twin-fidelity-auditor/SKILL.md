---
name: digital-twin-fidelity-auditor
description: >
  Audit the completeness, operational quality, replication fidelity, robustness, and application
  readiness of a personal digital twin, persona agent, perspective agent, role-simulation prompt,
  character skill, user-clone system, or delegated personal agent. Use when the user asks what
  dimensions of a person are replicated or missing, whether modeled traits actually affect runtime,
  whether the system captures the specific individual rather than an archetype, whether it
  generalizes to unseen situations, remains internally and temporally consistent, calibrates
  uncertainty, or has credible evidence of human fidelity. Also use to validate replication
  scorecards, compare twin implementations, design holdout/shadow benchmarks, or judge readiness
  for useful/delegated tasks. Never infer fidelity from prompt richness, biography volume, named
  heuristics, or stylistic similarity alone.
---

# Digital Twin Fidelity Auditor

Audit a twin as a **replication system**, not merely as a persona prompt.

Use three distinct layers:

1. **复刻了什么 — Replication Dimensions**
2. **复刻得怎么样 — Replication Quality**
3. **能不能真正应用 — Application Readiness**

Never collapse these into one score.

Core evidence principle:

> **写进 Prompt 只能证明设计覆盖；进入运行时只能证明机制生效；跨场景、跨时间且经过独立真人对照，才能证明高质量复刻。**

## 1. Establish the audit contract

Identify:

- target individual;
- artifact: prompt, skill, model, agent, architecture, dataset, benchmark, or full system;
- intended use;
- claimed twin level;
- available evidence;
- applicable domains;
- time scope;
- whether delegated action is claimed.

If only design artifacts are available, evaluate design coverage and operationalization potential. Do not claim measured human fidelity.

Use `N/A` for genuinely non-applicable dimensions.

---

# 2. Layer One — Replication Dimensions

Audit five replication layers.

| Layer | Core question | Main dimensions |
|---|---|---|
| **表征** | 我是谁？ | 人格、价值观、世界观、个人记忆 |
| **认知** | 我怎么看？ | 当前状态、问题表征、世界模型、关键因素 |
| **决策** | 我怎么选？ | 当前目标、偏好/效用、风险/约束、推理策略、决策策略、拒绝/升级 |
| **表达** | 我怎么说？ | 词汇、句式、语气、结构、节奏、修辞、受众/渠道适配 |
| **行为** | 我怎么做？ | 任务分解、工具使用、行动序列、委托行为 |

Treat **表征 → 认知 → 决策 → 委托行为** as a maturity progression when appropriate.

Do NOT make expression a maturity prerequisite. It is an output dimension.

Also audit cross-cutting systems:

- 元认知
- 持续学习
- 数据与证据治理
- 安全与授权
- 独立保真度评测

Read `references/dimension-rubric.md` for detailed definitions.

---

# 3. Layer Two — Replication Quality

Evaluate the applicable replication dimensions across eight quality axes.

| Axis | Core question |
|---|---|
| **Q1 覆盖全面性** | 需要复刻的变量有没有建模？ |
| **Q2 机制有效性** | 建模内容是否真正影响运行过程？ |
| **Q3 个体特异性** | 学到的是这个人，还是一个人物原型？ |
| **Q4 跨场景泛化性** | 换到未见问题/组合/领域后还像本人吗？ |
| **Q5 内部一致性** | 跨问题、多轮、跨层是否仍然自洽？ |
| **Q6 时间适应性** | 能否区分不同时间的本人并跟随变化？ |
| **Q7 不确定性校准** | 不知道、不像、证据不足时是否知道？ |
| **Q8 验证可信度** | “像本人”的结论有多强的独立证据？ |

Read `references/quality-rubric.md` for detailed scoring and test design.

### Default 0–3 score semantics

For most axes:

- **0** = absent / unvalidated / fails;
- **1** = weak / static / anecdotal;
- **2** = meaningful but incomplete;
- **3** = systematic and independently supported.

Do not mechanically average axes that measure different things.

---

# 4. Key quality tests

## Q1 — Coverage

Do not count labels as full coverage.

A heading named “values”, “risk”, or “world model” proves only that the concept is mentioned.

Check whether the concept has:

- definition;
- evidence;
- relationship to other states;
- runtime role.

## Q2 — Operationalization

Distinguish:

1. documentation only;
2. static Prompt/Profile injection;
3. context-dependent runtime use;
4. closed-loop state with evidence, runtime influence, feedback, and updates.

Rich prose does not imply strong operationalization.

## Q3 — Individual Specificity

Ask:

> Is this the target person, or merely a believable archetype?

Use identity ablation when useful:

- remove name;
- remove famous quotes;
- remove iconic labels;
- reduce identity-revealing biography;
- compare against a generic archetype.

Strong specificity requires **Target Signal > Archetype Signal**.

## Q4 — Generalization

Test progressively:

- same domain / unseen case;
- unseen combination of familiar factors;
- value-conflict cases;
- extreme resource/risk contexts;
- unseen domain within claimed scope.

Known historical replay is not generalization.

## Q5 — Consistency

Distinguish:

- horizontal consistency across topics;
- longitudinal consistency across long interactions;
- cross-layer consistency between representation, cognition, and decisions;
- explainable context-sensitive change.

Consistency does not mean always choosing the same action.

## Q6 — Temporal Adaptation

For living targets, test controlled updates from new human evidence.

For historical targets, test time-sliced reconstruction and prevent future information from contaminating earlier states.

For static roles where temporal adaptation is irrelevant, use N/A.

## Q7 — Calibration

Audit:

- confidence;
- evidence sufficiency;
- abstention;
- escalation;
- domain-boundary recognition;
- overconfidence.

Distinguish factual uncertainty from uncertainty about what the person would do.

## Q8 — Evidence Validity

Evidence strength should progress roughly from:

`persona description → quotes → repeated behavior → source-linked decisions → decision trajectories → independent holdout → live shadow comparison`

Inspect leakage, sample size, judge independence, scenario diversity, and baselines.

---

# 5. Layer Three — Application Readiness

Fidelity and application value are related but different.

Audit four readiness dimensions:

| Dimension | Core question |
|---|---|
| **A1 任务有效性** | 在目标任务上是否真的产生价值？ |
| **A2 可替代性** | 哪些任务能替本人做到什么程度？ |
| **A3 风险适配** | 当前复刻误差是否匹配任务失败代价？ |
| **A4 授权准备度** | 即使能力足够，是否明确被允许代表本人行动？ |

Read `references/application-readiness.md` when the user asks whether the twin is ready for real tasks or delegation.

Keep these concepts separate:

**Fidelity ≠ Confidence ≠ Risk ≠ Authorization**

---

# 6. Detect replication illusions

Always inspect for these failure patterns.

| Illusion | What happens |
|---|---|
| **标签覆盖错觉** | 有概念标题，但没有运行机制 |
| **丰富度错觉** | 传记/资料很多，但不会处理新情境 |
| **启发式错觉** | 规则很多，但缺当前目标、偏好、风险和状态 |
| **风格错觉** | 说话很像，被误认为认知/决策也像 |
| **原型错觉** | 像某一类人，而不是这个具体的人 |
| **历史重放错觉** | 已知答案复现被当成预测 |
| **静态快照错觉** | 某一时期的人设被当成永久人格 |
| **自信错觉** | 角色语气的确定性被当成预测置信度 |
| **架构完整错觉** | 模块齐全，但没有真人独立验证 |

Name detected illusions explicitly.

---

# 7. Process-replication audit

Use this reference chain:

**外部情境 → 当前状态 → 问题表征 → 相关记忆/证据 → 世界模型 → 当前目标 → 偏好/风险 → 推理策略 → 元认知 → 决策策略 → 内部判断 → 表达/行动**

For each important transition ask:

- Is the state represented?
- What evidence populates it?
- Static or dynamic?
- Does it influence downstream behavior?
- Does it carry target-specific signal?
- Does it generalize?
- Is it temporally appropriate?
- Has it been validated?

Equivalent mechanisms count. Do not require literal modules with these exact names.

Identify the **first weak link** in the chain, because upstream mismatch can explain downstream decision mismatch.

---

# 8. Result-fidelity audit

Evaluate independently:

### 表征保真度
Stable characteristics, values, worldview, beliefs, memory.

### 认知 / 过程保真度
Problem framing, key factors, causal predictions, information seeking, uncertainty handling.

### 决策保真度
Current goal, trade-offs, risk, option ranking, final choice, abstention.

### 风格保真度
Vocabulary, syntax, tone, rhythm, framing, audience adaptation.

### 行为保真度
Action sequence under matched information, resources, constraints, and permissions.

Never use style similarity as evidence of decision fidelity.

---

# 9. Scoring and aggregation

Do NOT output one universal “replication percentage” by default.

## Replication-dimension coverage

For applicable dimensions:

`Coverage Rate = count(Q1 >= 2) / applicable dimensions`

Also report strong / partial / mention-only / missing.

## Quality profile

Keep Q1–Q8 visible.

If executive aggregation is useful, group rather than flatten:

### Architecture Readiness
- Q1 Coverage
- Q2 Operationalization

### Fidelity Robustness
- Q3 Specificity
- Q4 Generalization
- Q5 Consistency
- Q6 Temporal Adaptation
- Q7 Calibration

### Validation Strength
- Q8 Evidence Validity

Never call Architecture Readiness “Fidelity”.

## Application profile

Keep A1–A4 separate.

A narrow twin can have high task utility without being a high-fidelity whole-person twin.

---

# 10. Critical-gap logic

Prioritize gaps by impact.

### P0 — invalidates the claimed level

Examples:

- cognitive-twin claim without situation interpretation;
- decision-twin claim without contextual goals/preferences/risk;
- individual-twin claim dominated by archetype signal;
- generalization claim without unseen testing;
- predictive-fidelity claim without independent evidence;
- delegated-twin claim without authorization.

### P1 — materially limits replication quality

Examples:

- weak temporal memory;
- low consistency;
- static preferences;
- shallow causal/world model;
- poor calibration;
- weak provenance.

### P2 — enhancement

Examples:

- additional stylistic nuance for a decision-focused twin;
- more biography unrelated to target tasks;
- more examples of already-covered heuristics.

Recommend P0 → P1 → P2 fixes.

Do not default to adding more Prompt text.

---

# 11. Benchmark requirements

When a benchmark/scorecard exists, inspect:

- construction / validation / holdout separation;
- temporal leakage;
- answer leakage;
- identity leakage;
- archetype baseline;
- sample size;
- scenario/domain diversity;
- conflict and extreme cases;
- judge independence;
- human baseline;
- human-human consistency;
- process vs outcome;
- style vs decision;
- abstention;
- calibration;
- case-selection bias.

For historical figures, prefer temporal holdout.
For living people, prefer shadow evaluation.

Read `references/fidelity-benchmark.md` for benchmark design.

---

# 12. Default audit output

## 1. Executive conclusion

Use the least inflated label supported by evidence:

- style simulator;
- persona simulator;
- perspective agent;
- cognitive simulator;
- partially developed decision twin;
- empirically validated decision twin;
- delegated twin.

## 2. Replication-dimension matrix

| Dimension | Coverage | Operational | Evidence | Main evidence | Main gap |
|---|---:|---:|---:|---|---|

## 3. Eight-axis quality profile

| Quality axis | Score/status | Evidence | Interpretation |
|---|---|---|---|
| Coverage | | | |
| Operationalization | | | |
| Individual Specificity | | | |
| Generalization | | | |
| Consistency | | | |
| Temporal Adaptation | | | |
| Calibration | | | |
| Evidence Validity | | | |

## 4. Process replication
Compare actual process against the reference chain and locate weak links.

## 5. Result fidelity
Separate representation / cognition / decision / style / behavior.

## 6. Application readiness

| Dimension | Status | Evidence / limitation |
|---|---|---|
| Task Utility | | |
| Substitutability | | |
| Risk Readiness | | |
| Authorization Readiness | | |

## 7. Replication illusions
List detected illusion risks.

## 8. Critical gaps
List P0 / P1 / P2.

## 9. Upgrade priorities
Recommend the smallest high-impact interventions and the validation needed afterward.

---

# 13. Comparison mode

When comparing twins:

- use the same applicable dimensions;
- use the same quality axes;
- use the same benchmark split;
- use N/A consistently;
- show trade-offs rather than only one ranking.

Preserve differences such as “stronger style / weaker decisions” rather than hiding them in a total score.

---

# 14. Source discipline

When auditing supplied artifacts:

- cite the artifact for coverage claims;
- distinguish exact artifact content from inference;
- do not invent hidden data, runtime mechanisms, or test results;
- source lists are claimed provenance until inspected;
- clearly distinguish artifact findings from external research.

---

# Governing model

> **复刻了什么，决定完整度。**  
> **复刻得怎么样，决定保真度与鲁棒性。**  
> **能不能完成目标任务，决定应用价值。**

A twin is not validated because it is detailed, convincing, or stylistically accurate. It is validated when target-specific behavior survives independent tests across relevant contexts and time, with calibrated uncertainty and evidence appropriate to the claimed level.
