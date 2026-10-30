# PAOS V1.1 Stage 1 — Packet C3B clean-writing Normalize / Import

Decision owner: zrx  
Prerequisite: C3A accepted  
Mutation scope: PAOS-Libraries Skill package only

## 0. Goal

Bring the user's existing `clean-writing` Skill into the PAOS shared Skill Library **without recreating it, renaming it, or copying Runtime-specific packaging wholesale**.

Target canonical identity:

```text
PAOS-Libraries/skill/clean-writing/
```

Final activation is allowed only after independent review passes.

## 1. Exact source

Use only:

```text
C:\Users\remo\.codex\skills\clean-writing\
```

as the source-of-origin.

Do not use as source:

- Desktop mirror;
- Downloads zip;
- Temp extraction;
- A3 short test variant;
- memory/reconstruction.

Before authoring, s027 must record source file list + hashes and verify the source still matches the C3A evidence.

Unexpected source drift is a STOP condition.

## 2. Stable ID

Use:

```text
id: clean-writing
directory: clean-writing/
schema: paos-skill/v1
version: 1
status: candidate
```

Do not rename to `skill-clean-writing`.

## 3. C3B-A — Source review + normalization plan

Owner: s027  
Reviewer: s029

Before writing the PAOS package, produce a source mapping:

| Source file | Reusable semantic role | Runtime/UI leakage | Keep / Adapt / Exclude | Reason |
|---|---|---|---|---|

At minimum review:

```text
SKILL.md
references/examples.md
references/language-modes.md
references/semantic-review.md
references/upgrade-protocol.md
scripts/clean_lint.py
agents/openai.yaml
assets/icon.svg
```

### Required content review

s027 must explicitly identify whether the original Skill contains:

- Codex/OpenAI-specific invocation language;
- tool names or loader instructions;
- absolute paths;
- prompt-wrapper behavior;
- overly rigid wording rules;
- duplicate process/governance instructions;
- audit/process-history language that conflicts with current clean-writing intent;
- assumptions about document type that should become optional modes.

No package mutation until the mapping exists.

## 4. C3B-B — Candidate package authoring

Starts only after C3B-A mapping has no unresolved P1.

Allowed target:

```text
PAOS-Libraries/skill/clean-writing/
```

### Required `SKILL.md` frontmatter

```yaml
---
schema: paos-skill/v1
id: clean-writing
title: Clean Writing
description: ...
tags: ...
status: candidate
version: 1
---
```

### Semantic goals

The normalized Skill should help an Agent produce reader-facing content that is:

- clean;
- readable;
- concise enough for the context;
- structurally clear;
- semantically faithful;
- free of unnecessary defensive/audit/process-history language;
- adapted to audience and artifact type.

It should preserve the user's earlier principle:

> The reader should receive the product/result they need, not the writer's internal iteration history.

### Non-goals

The Skill must not:

- force one tone or one prose style;
- erase meaningful uncertainty;
- remove evidence needed by technical/review artifacts;
- rewrite exact quotes/logs/contracts that require fidelity;
- own PAOS Work/TODO/acceptance;
- require use on every output;
- become a generic "AI style detector".

### Supporting files

Retain only supporting files whose content is still useful and runtime-independent.

`scripts/clean_lint.py` may be included only if s027 verifies:

- no unsafe/destructive mutation;
- no Codex-specific path/import dependency;
- its output is advisory, not authoritative;
- it does not implement naive keyword deletion that would damage semantics.

`agents/openai.yaml` and `assets/icon.svg` are excluded from the PAOS package unless an explicit PAOS contract later needs them.

One bounded Library commit for the candidate package.

## 5. C3B-C — Independent semantic review

s029 reviews the exact candidate commit.

Use `skill-independent-review` if genuinely useful, and log one honest usage event if used.

Review dimensions:

### Boundary

- execution Skill only;
- no Work/TODO/governance authority;
- no mandatory global usage.

### Fidelity

- does not remove uncertainty/evidence merely to sound clean;
- preserves technical meaning;
- does not hide relevant limitations.

### Anti-process-language behavior

- removes internal iteration history when it is not reader-relevant;
- does not erase provenance required by review/audit artifacts.

### Adaptivity

Scenario-test at least:

```text
product/PRD prose
technical decision memo
research summary
handoff/status report
reader-facing user guide
evidence-heavy review report
```

Pass condition:

- same Skill adapts by artifact/audience;
- it does not force all six outputs into the same tone or length;
- evidence-heavy review remains evidence-heavy;
- reader-facing docs shed internal process chatter.

### Supporting script

If `clean_lint.py` is included, independently inspect and run only against disposable test text. No real artifact mutation during review.

## 6. C3B-D — Activation / Catalog

If C3B-C returns no P1:

1. change `clean-writing` from `candidate` to `active`;
2. rebuild Skill Catalog;
3. verify:
   - exactly 3 active Skills;
   - no duplicate ID;
   - existing `skill-independent-review` usage event is reflected in generated usage stats;
   - no duplicate event was created;
   - package directory == id;
   - no Runtime-local package was modified.

One bounded activation/Catalog commit.

If review has P1:

- return to C3B-B with a narrow fix;
- do not activate.

## 7. Original source preservation

C3B never modifies or deletes:

```text
C:\Users\remo\.codex\skills\clean-writing\
C:\Users\remo\Desktop\skill库\...
Downloads copies
Temp copies
```

Duplicate cleanup is later Project/local hygiene, not C3B.

The PAOS package is a normalized shared derivative with its own Git history.

## 8. Runtime loading boundary

Do not change Codex/OpenCode config to auto-load PAOS-Libraries in C3B.

C3B establishes canonical Skill content only.

Runtime consumption / Workstation discovery belongs to later integration / Workstation migration.

## 9. Prohibited mutation

C3B does not authorize:

- additional Skill imports;
- Workflow changes;
- Project/Vault cleanup;
- source-doc cleanup;
- Workstation migration;
- Runtime activation-owner changes;
- hook/binding/Room/Participant changes;
- deletion of mirrors/zips/temp files;
- changes to original clean-writing source.

## 10. Required handoff

s027:

```text
s027/V11-C3B-CLEAN-WRITING-SOURCE-MAP.md
s027/V11-C3B-CLEAN-WRITING-NORMALIZATION.md
```

s029:

```text
s029/V11-C3B-CLEAN-WRITING-INDEPENDENT-REVIEW.md
```

Coordinator:

```text
coordinator/V11-C3B-CLEAN-WRITING-COORDINATOR-READBACK.md
coordinator/COORDINATOR-TODO-AFTER-C3B.md
```

Reports must include exact PAOS-Libraries commit SHAs and Catalog result.

Every executing Agent updates its own TODO before handoff.

## 11. Stop gate

After activation/Catalog evidence:

```text
STOP
```

Do not import any other Skill and do not enter M3 automatically.

zrx reviews the final 3-Skill baseline. If clean, next packet begins Project/Vault reconstruction.