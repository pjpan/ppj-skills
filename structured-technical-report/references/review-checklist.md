# Review Checklist

Use this checklist for a full report review or before delivering a mature final document.

## A. Structural integrity

- [ ] Each H1 is an independent top-level theme.
- [ ] Child concepts appear under their semantic parent.
- [ ] Related concepts are adjacent.
- [ ] The macro-narrative is easy to infer from the table of contents.
- [ ] The report explains the whole before deep-diving into parts.
- [ ] The number of top-level chapters is justified by distinct themes.

## B. Concept integrity

- [ ] Important abstract concepts have plain-language definitions.
- [ ] Easily confused concepts are explicitly differentiated.
- [ ] External theories or industry frameworks are used where they materially improve understanding.
- [ ] Engineering abstractions are not misrepresented as established scientific theories.
- [ ] Stable characteristics and dynamic states are separated where relevant.
- [ ] The same term preserves the same meaning throughout the report.

## C. Architecture integrity

- [ ] Conceptual capability is separated from implementation mechanism.
- [ ] Inputs, outputs, responsibilities, and boundaries are clear.
- [ ] Cross-cutting concerns are not forced into false maturity ladders.
- [ ] Presentation quality is not treated as proof of underlying capability.
- [ ] Governance/authorization is independent from technical capability when relevant.
- [ ] Data/evidence categories preserve source and intended use.

## D. Technology neutrality

- [ ] The core architecture is not unnecessarily bound to one vendor, algorithm, framework, or database.
- [ ] Replaceable technologies are presented at the implementation level.
- [ ] Current implementation is not presented as universally optimal without evidence.
- [ ] Volatile configuration details are pushed downward or to companion documents.

## E. Evidence quality

- [ ] Claim strength matches evidence strength.
- [ ] Important external claims have appropriate sources.
- [ ] Internal experiments state scope and limitations.
- [ ] Facts, assumptions, hypotheses, and recommendations are distinguishable.
- [ ] Examples are not used as universal evidence.
- [ ] Material uncertainty is visible.

## F. Evaluation quality

- [ ] Evaluation directly tests the capability being claimed.
- [ ] Independent dimensions are not hidden in one total score.
- [ ] Final evaluation is sufficiently independent from construction/tuning data where relevant.
- [ ] Appropriate baselines are provided.
- [ ] Generalization claims are not based only on reconstruction of known examples.
- [ ] Failures can be categorized and diagnosed.

## G. Final-document quality

- [ ] A first-time reader needs no drafting history.
- [ ] No unexplained “previous/old/original” residue remains.
- [ ] The primary report language is used consistently.
- [ ] Foreign terminology is included only when useful.
- [ ] Tables and flows are compact and purposeful.
- [ ] There are no unnecessary vertical arrow stacks.
- [ ] There are no repetitive “core conclusion” headings.
- [ ] Major chapters open with their substantive takeaway.
- [ ] The document reads like a report rather than a slide deck pasted into Markdown.

## H. Revision integrity

- [ ] The newest feedback is fully addressed.
- [ ] Previously accepted corrections remain intact.
- [ ] The change was propagated to all affected sections.
- [ ] No terminology or architecture regression was introduced.
- [ ] The final review covered the whole document, not only the edited paragraph.

## Common anti-patterns

| Anti-pattern | Repair |
|---|---|
| Many parallel H1 knowledge points | Rebuild parent-child hierarchy |
| Child concept is peer to its parent | Demote under the parent |
| Evaluation scattered through architecture | Create an independent evaluation section |
| Orthogonal concern in maturity ladder | Move to cross-cutting dimension |
| Named algorithm defines architecture | Raise to capability-level requirement |
| Infrastructure equated with business capability | Separate means from ends |
| Polished output treated as evidence of deep capability | Evaluate the underlying capability separately |
| Context-dependent behavior represented by one permanent scalar | Represent current state/context explicitly |
| Historical replay called prediction | Use independent evaluation |
| Mixed-language terminology everywhere | Use one primary language consistently |
| One arrow per line | Use compact flow or table |
| Editing-history language in final report | Rewrite as current principle |
| One total score hides multiple capabilities | Split into interpretable dimensions |
| One successful test becomes “optimal architecture” | State scope, uncertainty, and alternatives |
