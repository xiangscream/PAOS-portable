---
name: clean-writing
schema: paos-skill/v1
id: clean-writing
title: Clean Writing
description: Create or revise clear, high-quality professional writing by intelligently choosing the right language mode for the audience, artifact type, and publication state. Use for product documents, PRDs, reports, project results, executive summaries, technical explanations, decision memos, research outputs, status updates, and other informational writing where AI-like padding, defensive or audit-heavy prose, exposed reasoning, version-history leakage, fragmented structure, vague qualifiers, and terminology drift should be removed while preserving facts, uncertainty, evidence, constraints, and reader-relevant rationale. Also use when asked to make writing cleaner, more readable, less AI-like, less process-oriented, more concise, more professional, or publication-ready.
tags: writing, review, communication
status: active
version: 1
---

# Clean Writing

Produce writing that is easy to understand because its information architecture, semantic content, and sentence form fit the reader's job.

Do not treat "clean" as "short" or "confident." Preserve necessary uncertainty, evidence, exceptions, safety constraints, and technical detail. Remove only what does not help the intended reader understand, decide, or act.

## 适用任务与输入

Use for product documents, PRDs, reports, project results, executive summaries, technical explanations, decision memos, research outputs, status updates, external communication, and other informational writing where AI-like padding, defensive or audit-heavy prose, exposed reasoning, version-history leakage, fragmented structure, vague qualifiers, and terminology drift should be removed while preserving facts, uncertainty, evidence, constraints, and reader-relevant rationale.

Infer the writing situation from the request and available context. Do not ask the user to specify these when they are clear enough.

- **Audience**: self, working team, cross-functional team, management, technical implementer, customer/public, evaluator/reviewer.
- **Artifact**: work note, project result, product definition, PRD/spec, decision memo, research report, executive summary, status update, external communication, or another professional artifact.
- **State**: exploratory, working, review, final, publication.
- **Reader job**: understand, decide, implement, verify, approve, compare, or act.
- **Evidence need**: hidden/supporting, selectively visible, or central to the artifact.
- **Material at hand**: drafts, facts, sources, meeting records, constraints, and the limits on them.

If the working environment provides its own concise-writing rulebook, that rulebook is the single authority for expression rules. This skill then adds method, structure, and examples; it does not restate those rules.

## Core principle

Separate the language needed to **do the work** from the language needed to **present the result**.

A model may reason with research trails, rejected options, risk checks, evidence quality, internal debate, and version history. A final artifact should expose those only when the artifact's purpose requires them.

For final or publication-state writing, apply this rule:

> Write the current product, system, decision, or finding as a first-time reader needs to understand it. Do not narrate how the writer arrived there unless that process is itself part of the deliverable.

## 基本方法

### 1. 选择语言模式

Choose one primary mode and adapt it if needed:

- **Publication**: current-state, reader-first, minimal process/history.
- **Executive**: conclusion first, dense, selective evidence, decision-oriented.
- **Specification**: precise, stable terminology, testable requirements, explicit boundaries.
- **Decision**: recommendation plus material tradeoffs, uncertainty, and evidence needed for the decision.
- **Research**: findings and evidence are visible; research mechanics are not unless methodology matters.
- **Status**: what changed, current state, blockers, next actions; avoid replaying the entire work log.
- **Working**: process and open questions may remain visible because collaboration is the purpose.

Do not force publication-style compression onto a research report, safety notice, legal/medical/high-stakes explanation, or decision memo when evidence and caveats are part of the reader's job.

Read `references/language-modes.md` when mode selection is ambiguous or the task mixes multiple artifact types.

### 2. 整理信息

Build an information contract before writing. Classify source material into two groups:

**Usually reader-facing** — CURRENT_FACT, USER_BEHAVIOR, REQUIREMENT, BOUNDARY, RESULT, ACTION, DECISION, NECESSARY_RATIONALE, MATERIAL_UNCERTAINTY, MATERIAL_EVIDENCE.

**Usually support-layer only** — PROCESS_HISTORY, VERSION_HISTORY, AUTHOR_META, REASONING_TRACE, DEFENSIVE_EVIDENCE, AUDIT_TRAIL, REJECTED_OPTION_DETAIL, TOOL_OR_RESEARCH_LOG.

The second group is not "bad information." It belongs in the main text only when the artifact's purpose makes it reader-relevant. For publication-state outputs, default to excluding it.

Read `references/semantic-review.md` for the label definitions and the per-mode keep/remove rules.

### 3. 语义与结构改写

Do not clean text by deleting flagged words one by one. Rewrite the semantic unit, and prefer an information shape that matches the content.

- Use a **table** for parallel parameters, capabilities, comparisons, owners, or status fields.
- Use **prose** for causal explanation, narrative, synthesis, and nuanced judgment.
- Use **bullets** when scanability matters and the items are genuinely parallel.
- Merge micro-sections that each contain only one small point.
- Put the most decision-relevant or defining information first.
- Do not repeat the same conclusion in an introduction, body, summary, and "key takeaway."

Sentence-level defaults:

- One stable term per concept; prefer direct subjects and active verbs.
- Prefer verbs over abstract noun phrases ("analyze" over "perform an analysis of").
- Keep one main judgment per sentence; split sentences with several independent claims.
- Remove filler openings, marketing adjectives, synonym rotation, and hedging stacks.
- Preserve a qualifier when removing it would make the claim materially less accurate.
- Avoid "AI completeness": do not add generic benefits, risks, future directions, or summaries merely because they are common report sections.

Read `references/semantic-review.md` for the full tests (defensive language, process leakage, evidence, uncertainty, structure) and the step-by-step rewrite procedure. Read `references/examples.md` for worked transformations.

### 4. 检查真实条件

Never turn uncertainty into certainty for stylistic neatness. Preserve, in the shortest useful form:

- unresolved facts that affect a decision;
- confidence limits that affect interpretation;
- safety, compliance, legal, technical, or operational constraints;
- assumptions that change the meaning of a result;
- conflicting evidence when the conflict is material;
- source attribution or citations when required by the task.

Clean writing is not confident laundering.

Before delivering final text, test it from the perspective of a first-time reader:

- The reader can tell what the subject **is now**.
- The reader does not need the internal meeting or old version to decode it.
- Research effort is not displayed as a substitute for product information.
- The text does not expose unnecessary reasoning traces or author self-commentary.
- Each section earns its place; parallel information is easy to scan; terminology is stable.
- Important uncertainty and boundaries remain visible, and cutting process/history did not cut necessary information.

If any test fails, revise before delivering.

## Creation vs. revision

### Creating new content

1. Infer the language mode.
2. Extract the information contract from the user's facts and sources.
3. Design the structure before prose.
4. Draft directly in the selected mode.
5. Run semantic, structural, and sentence-level review.
6. Deliver only the finished artifact unless the user asks for rationale or review notes.

### Revising existing content

1. Preserve the intended meaning and supported facts.
2. Identify semantic leakage and structural problems before sentence polishing.
3. Rewrite at paragraph/section level where needed.
4. Do not preserve internal history merely because it existed in the source draft.
5. Keep material caveats and evidence required by the artifact type.
6. Return a clean full version, not a patchwork of local edits, unless the user asks for tracked changes or comments.

## Evidence, history, and citations

Distinguish **evidence-backed writing** from **evidence-displaying writing**. A product definition may be strongly evidence-backed while showing little evidence in the main body. A research report may need evidence in nearly every section. A decision memo may need only the evidence that changes the decision.

Do not remove citations required by the environment or the user's request. Instead, reduce defensive framing around them.

For final product or result language, compile history into current state. Keep history only in a changelog, decision record, retrospective, migration note, or status update where change itself is the subject.

Bad:

> The earlier design included dynamic configuration, but after several rounds of discussion we decided to weaken it in this version because implementation complexity is high.

Better:

> The initial release supports fixed default settings. Dynamic configuration is out of scope.

## Adaptive local overrides

This skill is designed to improve without bloating the universal rules.

If the user or working environment provides a local clean-writing policy or correction corpus, apply it after this skill's universal rules. A useful local structure is:

- `clean-writing.local.md` — organization/user-specific rules.
- `clean-writing.examples.local.md` — real bad → good correction pairs.

Give explicit user instructions and local examples higher priority than generic examples, unless they conflict with system or safety requirements.

Do not silently invent local preferences.

Read `references/upgrade-protocol.md` when the user asks to improve, update, train, or calibrate this skill from real corrections.

## Optional mechanical lint

For plain-text or Markdown files in an environment where scripts can run, `scripts/clean_lint.py` can flag mechanical risk signals such as long sentences, process/version cues, author-meta cues, hedging stacks, and fragmented micro-sections.

The script is advisory only. Never treat a flagged word as an automatic violation. Semantic review has priority.

Limitation: the bundled script's signal patterns currently cover Chinese text; it is a starting signal set, not a language-complete checker, and should be extended per language as needed.

Example:

```bash
python scripts/clean_lint.py draft.md
```

Use the script when it materially helps with a long document. Do not run it for every short answer.

## Output behavior

When the user asks for finished writing, output the finished writing rather than a review report unless they request commentary.

When the user asks for critique, explain the few highest-impact language problems and show representative transformations.

When the user asks for both critique and rewrite, keep the critique concise and make the revised artifact the primary output.

Do not append a generic "key takeaway," "next steps," or "in summary" section unless the artifact needs it.
