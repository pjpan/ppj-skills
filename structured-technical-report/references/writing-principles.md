# Writing Principles Reference

Read this reference when the task requires substantial restructuring, theoretical framing, or a full report audit.

## 1. Durable-content hierarchy

Place content higher in the report when it is expected to remain valid longer.

| Content type | Typical lifetime |
|---|---|
| Principle | Long |
| Conceptual architecture | Long |
| Capability requirement | Medium to long |
| Interface / contract | Medium to long |
| Algorithm choice | Medium |
| Framework / vendor choice | Short to medium |
| Parameters / configuration | Short |

This reduces report churn and prevents volatile implementation detail from dominating long-lived architecture.

## 2. Generic information architecture

A strong whitepaper often follows:

### Definition and boundaries
Establish object, audience, objectives, scope, exclusions, and capability levels.

### Theory or analytical foundation
Introduce external frameworks needed to make abstract terminology understandable.

### Core framework
Present the whole first, then children and relationships.

### Data / evidence
Clarify what information the framework depends on, its provenance, quality, and semantic roles.

### System realization
Map concepts to responsibilities and interfaces without binding prematurely to one technology.

### Evaluation
Independently test the claims made by previous chapters.

### Evolution / operations
Explain how the system changes, learns, or is maintained.

### Risk / governance
Explain failure modes, trade-offs, controls, ownership, safety, privacy, and authorization where relevant.

### Roadmap / synthesis
Show dependencies, sequencing, and final integrated form.

## 3. Comparison-table pattern

Use when concepts are easy to confuse:

| Dimension | Concept A | Concept B | Concept C |
|---|---|---|---|
| Core question | | | |
| Scope | | | |
| Time scale | | | |
| Stability | | | |
| Input | | | |
| Output | | | |
| Example | | | |

## 4. Theory-anchor pattern

For abstract concepts:

| Concept | Plain definition | External anchor | Boundary | Role |
|---|---|---|---|---|

The purpose of external research is not decorative citation. It should clarify the meaning or justify a claim.

## 5. Technology-binding classification

Classify named implementation choices as:

- **Architecture-essential** — removing it changes the conceptual contract.
- **Candidate implementation** — one practical way to realize a capability.
- **Illustrative example** — included only to make an idea concrete.
- **Unnecessary detail** — does not affect the reader's current decision.

Only the first category belongs naturally in a core architecture diagram.

## 6. Evaluation design

For each claim ask:

| Question | Purpose |
|---|---|
| What exactly is claimed? | Avoid vague evaluation |
| What is the target? | Establish reference |
| What metric measures it? | Avoid proxy drift |
| What data is used? | Check representativeness |
| Was the test data used in construction? | Check leakage |
| What is the baseline? | Establish comparative meaning |
| What failures matter? | Improve diagnosis |
| What uncertainty remains? | Prevent overclaiming |

## 7. Examples versus evidence

Examples explain.
Evidence supports claims.

Never use a vivid example as a substitute for evidence unless the report explicitly presents it as a case study.

## 8. Stable versus dynamic state

When behavior depends on context, separate long-term characteristics from current state.

Generic conceptual relationship:

`Current behavior ← stable characteristics + history + current context + objective + constraints`

Do not force a literal formula unless the domain provides one.

## 9. Presentation-density rules

Prefer:

`Input → Interpretation → Decision → Output → Feedback`

over vertically stacked arrow paragraphs.

Use a table when three or more objects are being compared on common dimensions.

Merge subsections when each would contain only one short paragraph and they share a parent concept.

## 10. Terminology map

Before final drafting, build:

| Preferred term | Definition | Parent | Nearby terms | Avoided aliases |
|---|---|---|---|---|

Terminology inconsistency often reveals conceptual inconsistency.
