---
name: structured-technical-report
description: >
  Create, restructure, or review professional technical whitepapers, architecture reports,
  research reports, technical strategy/planning documents, and executive-facing technical
  narratives. Use this skill whenever the user asks to write, rewrite, improve, review, organize,
  or finalize a substantial technical report whose quality depends on clear information hierarchy,
  consistent terminology, evidence-backed concepts, architecture-versus-implementation separation,
  independent evaluation, compact presentation, or cumulative revision quality. Also use it when
  a report feels like a collection of correct points but lacks a coherent structure. Do not use
  for lightweight messages, simple factual answers, slide decks, code-only tasks, or ordinary
  document formatting where report architecture and reasoning quality are not central.
---

# Structured Technical Report

Create reports that read as coherent systems of ideas rather than collections of individually correct sections.

Optimize for:

**conceptual integrity → semantic hierarchy → evidence → architecture durability → independent evaluation → information density → standalone final quality**

## Operating workflow

Follow this sequence for substantial creation, restructuring, or review tasks.

### 1. Establish the document contract

Identify:

- audience and assumed background;
- report type and purpose;
- decision or understanding the report must enable;
- expected depth;
- whether this is a final standalone report or an internal working document.

For a final whitepaper, assume the reader knows nothing about the drafting history unless the user explicitly says otherwise.

Write an internal thesis:

> This document exists to establish ______.

Use it to remove material that is interesting but not structurally necessary.

### 2. Build the semantic tree before drafting prose

Design headings as a parent-child hierarchy.

Use:

- H1 for independent top-level questions or themes;
- H2 for components or dimensions of the H1;
- H3 for definitions, mechanisms, examples, evidence, diagnostics, or implementation details inside an H2.

For every heading ask:

> Is this genuinely an independent theme, or is it a component of another theme?

Demote child concepts instead of placing all knowledge points at the same level.

Prefer a small number of strong top-level chapters over many parallel chapters.

### 3. Use a total–part–total narrative

A useful default order is:

1. definition, context, objective, and boundary;
2. theoretical or analytical foundation;
3. core conceptual framework;
4. decomposition of that framework;
5. data, evidence, and assumptions;
6. system or technical realization;
7. independent evaluation;
8. evolution, operations, risk, and governance;
9. roadmap or final integrated architecture;
10. summary.

Adapt this pattern to the task. Do not force irrelevant chapters.

Explain the whole before explaining its parts. Keep child concepts adjacent to their parent.

### 4. Keep abstraction levels explicit

Distinguish among:

- theory / research foundation;
- conceptual model;
- business or product capability;
- data / evidence;
- system architecture;
- runtime or operating mechanism;
- implementation technology;
- evaluation;
- governance.

Do not silently mix levels.

A conceptual chapter should not suddenly prescribe a database or algorithm. An implementation detail should not redefine a conceptual capability. Evaluation should remain independently understandable.

### 5. Separate WHAT and WHY from HOW

State the durable requirement before proposing a mechanism.

Prefer:

> The system needs to identify and organize information relevant to the current task.

over:

> The architecture must use a particular retrieval pipeline.

For every named technology, algorithm, vendor, framework, or database ask:

> If this were replaced next year, would the conceptual architecture remain valid?

If yes, treat it as an implementation option rather than an architectural requirement.

Keep volatile implementation details lower in the document or in companion implementation specifications.

### 6. Define abstract concepts with external anchors

When the report depends on abstract or discipline-specific concepts, explain:

1. **What** — plain-language definition;
2. **Reference anchor** — recognized academic, standards, or industry framework when useful;
3. **Boundary** — how it differs from adjacent concepts;
4. **Role** — why it matters here;
5. **Example** — one concrete example when clarification helps.

Do not present a convenient engineering decomposition as established scientific theory.

When credibility depends on external theory or evidence, prefer primary papers, standards, official documentation, original datasets, or authoritative institutions.

### 7. Make adjacent concepts distinguishable

When readers may confuse concepts, compare them directly.

Useful comparison dimensions include:

- core question;
- object;
- time scale;
- stability;
- input;
- output;
- role;
- example;
- failure mode.

A concept is not fully defined if readers cannot distinguish it from its neighbors.

### 8. Separate progression from orthogonal dimensions

Only place capabilities in a maturity ladder when each later level actually extends, includes, or requires the earlier level.

Treat independent concerns as cross-cutting dimensions.

Common cross-cutting concerns include:

- presentation or style;
- security;
- governance;
- observability;
- evaluation;
- accessibility;
- continuous learning.

Do not invent a false sequence merely to make a diagram look progressive.

### 9. Preserve semantic roles in data and evidence

Do not treat all records as generic knowledge.

Distinguish relevant categories such as:

- verified facts;
- observations;
- historical events;
- user or stakeholder statements;
- assumptions;
- decisions;
- outcomes;
- preferences;
- corrections;
- generated outputs;
- external evidence;
- current context.

Track provenance and intended use.

A statement being observed does not make it objectively true. A fact being true does not imply every actor will interpret or act on it identically.

### 10. Design evaluation as an independent system

For every important claim define:

- capability being validated;
- target or ground truth;
- metric;
- evaluation data;
- baseline;
- independence from construction/tuning;
- failure taxonomy;
- uncertainty and limitations.

Do not hide heterogeneous capabilities inside one overall score.

Distinguish when relevant:

- correctness vs similarity;
- quality vs consistency;
- in-sample fit vs generalization;
- system performance vs business impact;
- leading indicators vs outcome metrics.

For predictive or generalization claims, use genuinely independent evidence rather than replaying known examples.

### 11. Match claim strength to evidence strength

Label the nature of important claims:

- established fact;
- external research finding;
- empirical result;
- engineering judgment;
- assumption;
- hypothesis;
- recommendation.

Do not convert:

> worked in one test

into:

> is the optimal architecture.

State scope and limitations when evidence is based on small samples, limited environments, simulations, proxies, or internal tests.

### 12. Separate surface quality from underlying capability

Do not use polished presentation as evidence that the underlying system, reasoning, analysis, or strategy is correct.

Examples:

- polished prose does not prove sound analysis;
- a polished interface does not prove backend reliability;
- a plausible explanation does not prove the internal mechanism followed it.

Evaluate the underlying capability separately when material.

### 13. Optimize information density

Write a document, not a slide deck pasted into Markdown.

Avoid:

- one phrase per paragraph;
- one arrow per line;
- excessive blank space;
- many tiny subsections;
- repeated conclusion labels;
- duplicated prose around tables.

Prefer:

- compact `A → B → C` flows;
- comparison tables;
- structured matrices;
- cohesive paragraphs;
- fewer, semantically stronger headings.

Use tables when they carry taxonomy, comparison, responsibility, evidence, metrics, risks, trade-offs, or roadmap structure.

### 14. Use consistent terminology

Create a canonical vocabulary for core concepts.

For each important term identify:

- preferred term;
- definition;
- parent concept;
- neighboring concepts;
- aliases to avoid.

Use the term consistently across theory, architecture, data, runtime, evaluation, and roadmap.

For Chinese reports, prefer Chinese terminology in normal prose. Keep English for canonical theory names, paper titles, standards, exact product/framework identifiers, or a glossary when useful. Avoid repeatedly writing `中文（English）`.

### 15. Write as a standalone final document

Unless historical comparison is the subject, remove drafting residue such as:

- old system;
- previous architecture;
- original solution;
- earlier version;
- as discussed before;
- we changed from;
- retain the old design.

Rewrite those statements as present-state principles.

Bad:

> The previous design separated these data types, and this should be retained.

Better:

> These data types should be managed separately because they serve different purposes.

### 16. Treat revisions as cumulative

When revising a mature report:

1. extract previously accepted constraints;
2. add the newest feedback;
3. detect conflicts;
4. determine whether the change is wording-, section-, hierarchy-, architecture-, evidence-, or evaluation-level;
5. propagate it to every affected section;
6. recheck terminology and structure globally;
7. preserve all compatible prior corrections.

Do not patch only the sentence that triggered the feedback.

## Chapter-writing pattern

For each major chapter:

1. open with the substantive takeaway in normal prose;
2. explain the core structure;
3. use a table or compact flow when it improves comprehension;
4. add evidence/theory only where it supports the chapter's claim;
5. avoid a repetitive heading such as “Core conclusion” or “Key conclusion.”

## Review procedure

Before finalizing, review the report against these gates:

1. **Structure** — headings reflect real parent-child relationships.
2. **Concepts** — important terms are clear, bounded, and consistently used.
3. **Architecture** — durable capabilities are separated from implementation choices.
4. **Evidence** — claim strength matches evidence strength.
5. **Evaluation** — core claims can be independently tested.
6. **Technology neutrality** — replaceable technology is not presented as timeless architecture.
7. **Final-document quality** — no drafting-history residue; presentation is compact and standalone.
8. **Revision integrity** — the latest change has not regressed previously accepted improvements.

For detailed review questions and common failure patterns, read [references/review-checklist.md](references/review-checklist.md).

For deeper rationale, examples, and report-structure patterns, read [references/writing-principles.md](references/writing-principles.md) only when a complex restructuring or audit requires them.

## Output expectations

When generating or rewriting a report:

- preserve the user's intended audience and decision context;
- use the primary report language consistently;
- prefer clear professional prose;
- use tables only when they improve semantic density;
- make assumptions and uncertainty visible;
- avoid claiming optimality without evidence;
- keep conceptual architecture durable;
- return a clean complete report when the user requests a final version.

When reviewing rather than rewriting, organize findings by structural impact rather than by the order in which sentences appear.

## Governing principle

> **Every revision should improve the system of the document, not merely patch the sentence that triggered the feedback.**
