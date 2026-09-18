# Fidelity Benchmark Guide

## 1. Dataset separation

Maintain:
- Construction set — may shape the twin.
- Validation set — may tune it.
- Holdout set — must not shape/tune it.

Known target answers in construction material cannot demonstrate predictive fidelity.

## 2. Historical figure

Choose cutoff T0.

Construct the twin using only information available before T0.
Test decisions after T0 without exposing their outcome/answer.

Also use multiple historical cutoffs when temporal adaptation matters.

## 3. Living person

Prefer shadow mode:

`same real problem → human independently decides + twin independently decides → compare afterward`

Prevent information leakage in both directions.

## 4. Case schema

When supported by evidence capture:
- timestamp;
- context;
- information available;
- current state;
- current goal;
- options;
- human problem framing;
- expected consequences;
- key factors;
- trade-offs;
- risks/constraints;
- final choice;
- confidence;
- outcome;
- later reflection.

Do not invent unavailable internal mental states.

## 5. Specificity benchmark

Include:
- generic-archetype baseline;
- identity ablation;
- target-swap controls when possible.

Ask whether target-specific evidence improves agreement beyond the archetype.

## 6. Generalization benchmark

Include:
- same-domain unseen cases;
- factor recombination;
- conflict cases;
- extreme context;
- cross-domain cases within claimed scope.

## 7. Consistency benchmark

Use semantically matched or logically linked prompts to test:
- cross-topic coherence;
- long-context drift;
- values-to-choice consistency;
- explainable context-sensitive changes.

## 8. Temporal benchmark

For time-varying targets test:
- T1 state with T1 evidence;
- T2 state with T2 evidence;
- no T2 leakage into T1 predictions.

Measure whether changes track the target instead of merely accumulating data.

## 9. Calibration benchmark

For each case collect:
- prediction/confidence;
- evidence availability;
- target agreement;
- abstention decision.

Evaluate whether low person-specific evidence produces appropriately lower confidence or more abstention.

## 10. Human consistency

When possible estimate human-human consistency on repeated/matched scenarios.
The target person is not assumed deterministic.

## 11. Process and outcome metrics

Representation:
- trait/value/worldview agreement.

Cognition:
- problem-frame agreement;
- key-factor overlap/ranking;
- consequence prediction agreement.

Decision:
- option-ranking correlation;
- top-choice agreement;
- pairwise preference accuracy;
- abstention/escalation agreement.

Style:
- blinded attribution;
- human similarity ratings.

Behavior:
- action-sequence similarity under matched constraints.

Track process and final outcome separately.

## 12. Judge independence

For important evaluations combine where appropriate:
- objective structured metrics;
- human raters;
- heterogeneous model judges;
- source-grounded comparison.

## 13. Validity warnings

Flag:
- tiny sample;
- one-domain-only sample;
- answer leakage;
- identity leakage;
- no archetype baseline;
- style used as decision proxy;
- no human baseline;
- weak historical evidence;
- post-hoc case selection;
- evaluator and generator strongly correlated.
