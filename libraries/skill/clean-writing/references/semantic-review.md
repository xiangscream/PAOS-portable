# Semantic Clean Review

## Contents

1. Semantic labels
2. Publication decision rules
3. Defensive language test
4. Process leakage test
5. Evidence test
6. Uncertainty test
7. Structural test
8. Rewrite procedure

## 1. Semantic labels

Assign the dominant function of a sentence, paragraph, table row, or section.

### Reader-facing labels

**CURRENT_FACT** — what the subject is now.

**USER_BEHAVIOR** — what a user can do or experiences.

**REQUIREMENT** — what the system must/should satisfy.

**BOUNDARY** — scope, exclusion, condition, or limit.

**RESULT** — a finding, output, measured outcome, or delivered capability.

**ACTION** — what must happen next.

**DECISION** — a selected direction or choice.

**NECESSARY_RATIONALE** — explanation the reader needs to interpret or use the current design.

**MATERIAL_UNCERTAINTY** — uncertainty that changes interpretation, decision, implementation, or risk.

**MATERIAL_EVIDENCE** — evidence the artifact's reader needs to verify or evaluate the claim.

### Support-layer labels

**PROCESS_HISTORY** — how the work unfolded.

**VERSION_HISTORY** — what previous drafts or versions contained.

**AUTHOR_META** — commentary about what the writer intends to explain or how the document is organized.

**REASONING_TRACE** — chain of thought or inference steps that are not needed by the reader.

**DEFENSIVE_EVIDENCE** — evidence included mainly to show diligence or defend the author.

**AUDIT_TRAIL** — confidence logs, source bookkeeping, review state, internal traceability.

**REJECTED_OPTION_DETAIL** — dead alternatives no longer relevant to the reader's choice.

**TOOL_OR_RESEARCH_LOG** — search steps, prompts, tools, pages read, or agent activity.

## 2. Publication decision rules

For Publication and Specification modes:

- Keep reader-facing labels.
- Convert material support-layer content into a reader-facing form when possible.
- Remove support-layer content when it adds no reader value.
- Move traceability to appendices, evidence ledgers, decision records, or links when available.

For Decision and Research modes:

- Keep more rationale/evidence.
- Still remove diary-like process and unnecessary self-defense.

For Status mode:

- Keep change history only for the relevant reporting period.

## 3. Defensive language test

Ask: "If the reader already trusted that the writer did competent work, would this sentence still be needed?"

If no, the sentence is probably defensive.

Common defensive moves:

- naming several competitors before a basic conclusion;
- saying research was comprehensive;
- saying a claim is "well supported" instead of showing the material support;
- repeating caveats after they have already bounded the claim;
- giving evidence that does not change the reader's interpretation.

Rewrite by keeping one of:

- the current fact;
- the material boundary;
- the decisive evidence.

Delete the rest.

## 4. Process leakage test

Ask:

- Does the sentence mention "this round," "previous version," "after discussion," "we later decided," or similar history?
- Would a first-time reader care how the team arrived here?
- Is the artifact a changelog, retrospective, status report, or decision record?

If history is not the subject, compile it into current state.

Pattern:

`old state + debate + reason + new state` → `new state + material boundary`

## 5. Evidence test

Classify evidence as:

**Central** — needed to evaluate the artifact. Keep it visible.

**Decision-relevant** — keep selectively.

**Support-only** — keep outside the main text.

**Decorative/defensive** — remove.

Do not confuse "evidence exists" with "evidence must be displayed here."

## 6. Uncertainty test

Remove uncertainty only if it is non-material verbal padding.

Keep uncertainty when it affects:

- safety;
- feasibility;
- acceptance criteria;
- investment/approval;
- interpretation of results;
- legal/compliance exposure;
- a significant product or technical decision.

Bad cleaning:

> "The system may support 5 m/s depending on terrain." → "The system supports 5 m/s."

Better:

> "Target speed is 5 m/s on the defined test surface; performance on rough terrain remains unverified."

## 7. Structural test

Flag structure when:

- several adjacent headings each contain one small point;
- a paragraph lists many parallel parameters;
- the same conclusion is repeated in multiple sections;
- background appears before the answer even though the reader needs the answer first;
- an artifact contains generic sections that have no specific content.

Rewrite by merging, tabulating, reordering, or deleting.

## 8. Rewrite procedure

When a unit fails semantic review:

1. Identify the one reader-relevant fact/decision/requirement inside it.
2. Identify material uncertainty or boundary that must survive.
3. Identify whether evidence must remain visible.
4. Remove process, author meta, defensive proof, dead alternatives, and repeated framing.
5. Restate the surviving information directly.
6. Check that the rewrite does not overclaim.
