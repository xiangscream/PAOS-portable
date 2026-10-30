# PAOS V1.1 Stage 1 — Packet C3A Skill Baseline Source Inventory

Decision owner: zrx  
Prerequisite: C2 accepted  
Mutation class: read-only discovery/classification; normal Skill usage-event logging is allowed when a Skill is genuinely used

## 0. Why this packet exists

C2 established a valid two-layer baseline:

```text
Workflow Kernel
  wf-agent-work-cycle
  wf-coordinator-governance-cycle

Skill Library
  skill-engineering-change
  skill-independent-review
```

Before Project/Vault cleanup starts, Stage 1 should finish one more baseline task:

> discover and reconcile **existing mature reusable Skills** that already exist in the user's real work world.

This is different from inventing a large Skill catalog.

A complete Skill baseline means:

- known mature existing Skills have one canonical identity;
- duplicates/renamed copies are understood;
- Project-local or Runtime-specific wrappers are not silently promoted;
- missing source is reported rather than reconstructed from memory;
- speculative candidates remain candidates.

## 1. Hard scope

C3A is discovery only.

Do not:

- author a new Skill;
- edit an existing Skill source;
- copy a local Skill into `PAOS-Libraries`;
- change Workflow content;
- clean Project/Vault/Workstation files;
- change Runtime activation owner, hooks, bindings, Rooms or Participants;
- scan the whole disk indiscriminately.

Normal append-only Skill usage-event logging is allowed if a currently active Skill is actually used during C3A.

## 2. Mandatory discovery target

### Clean Writing lineage

Find the exact source package(s), if present, for the user's previously created clean-language / clean-writing Skill.

Search only bounded known locations first:

- current PAOS/agent workspace;
- known user Skill directories referenced by OpenCode/Codex/runtime configuration;
- current Project-local skill folders;
- archived handoff/outputs where an exact package path is referenced;
- existing configured plugin/Skill roots.

Do not recreate `clean-writing` from memory.

If no exact source is found after bounded search:

```text
status = SOURCE-MISSING
searched locations = [...]
evidence = [...]
next decision = ask Human / recover from prior artifact source
```

Do not block the rest of C3A.

## 3. Other source discovery

Look for actual reusable Skill-like assets already used or deliberately created.

Examples may include:

- writing / document-quality Skills;
- code/review Skills;
- research/product methods;
- runtime/tool Skills referenced by active Agent configs;
- Project-local Skill packages that may have escaped into reuse.

Do not promote ordinary docs/checklists merely because they look like a Skill.

## 4. Source record schema

For every discovered Skill-like source:

```text
source_id
exact path / source location
current owner
current consumers
source format
current id/name
last known use / evidence
Project-specific assumptions
Runtime-specific assumptions
overlap / duplicate candidates
maturity:
  mature-reusable
  candidate
  project-local
  runtime-wrapper
  historical
  unknown

recommended action:
  import-as-is
  normalize-then-import
  merge-with-existing
  keep-project-local
  keep-runtime-local
  reject
  source-missing

proposed stable skill id
supporting files required?
risk
open decision
confidence
```

## 5. Maturity test

A source is `mature-reusable` only if most of these are true:

- it was deliberately created as reusable method/capability;
- it has been used or reviewed beyond one accidental occurrence;
- it describes execution technique, not PAOS governance;
- it can be stripped of Project/Runtime-specific context without losing value;
- its boundary is understandable;
- it does not duplicate an active Skill under another name;
- its source is exact and inspectable.

“Useful idea” is not enough.

## 6. Existing active Skills

Do not rewrite:

```text
skill-engineering-change
skill-independent-review
```

C3A should record whether they are already referenced/used by real work after activation.

### First real-use evidence

s029 should use `skill-independent-review` for the C3A independent review **only if it genuinely helps**.

At closeout, record one append-only usage event with an honest usefulness score:

```text
0    not useful / misleading
0.3 limited
0.5 useful
1    strongly useful
```

Do not force a positive score.

s027 does not need to use `skill-engineering-change` merely to create usage.

## 7. Roles

### s027 — primary source inventory

- update own TODO first;
- inspect bounded known Skill locations;
- find exact Clean Writing lineage;
- build the source inventory;
- identify duplicates/overlap;
- do not copy/import anything.

Output:

```text
s027/V11-C3A-SKILL-SOURCE-INVENTORY.md
```

### s031 — Runtime Skill-location readback

Narrow scope only.

Report:

- Codex/native configured Skill directories;
- any Runtime-local Skill packages actually referenced;
- whether these are reusable source or Runtime wrapper;
- exact paths/refs;
- do not modify Runtime config.

Output:

```text
s031/V11-C3A-RUNTIME-SKILL-LOCATIONS.md
```

### s029 — independent maturity / duplication review

- update own TODO first;
- independently challenge promotion recommendations;
- use `skill-independent-review` if genuinely useful;
- distinguish reusable Skill from Project-local/repo-doc/runtime-wrapper;
- challenge duplicate IDs/names and giant catch-all Skills;
- verify `clean-writing` is exact source, not reconstruction;
- record usage event/score if Skill used.

Output:

```text
s029/V11-C3A-SKILL-BASELINE-INDEPENDENT-REVIEW.md
```

### s010 — Coordinator

- keep C3A read-only;
- preserve disagreements;
- do not resolve missing-source by asking an Agent to rewrite from memory;
- return one reconciliation table of import candidates and blockers.

Outputs:

```text
coordinator/V11-C3A-SKILL-BASELINE-COORDINATOR-READBACK.md
coordinator/COORDINATOR-TODO-AFTER-C3A.md
```

## 8. Required final matrix

Coordinator readback should contain:

| Proposed Skill | Exact source found? | Maturity | Duplicate/overlap | Recommended action | Reviewer position | Needs zrx/Human? |
|---|---|---|---|---|---|---|

Also list:

- source-missing known Skills;
- rejected promotion candidates;
- runtime/project-local assets intentionally not imported;
- active Skill usage evidence collected during C3A.

## 9. Stop conditions

Stop affected discovery if:

- a search would require broad/private disk crawling beyond known workspaces/configured roots;
- source provenance cannot be distinguished;
- an active Runtime depends on the source and inspection would require mutation;
- two packages have the same apparent stable ID but different semantics;
- a candidate mixes PAOS governance with execution technique and cannot be cleanly separated.

Report, do not “fix”.

## 10. Done When

C3A is complete when:

- bounded known Skill locations are inventoried;
- exact Clean Writing source is found or explicitly marked SOURCE-MISSING;
- all discovered assets have maturity + proposed action;
- s029 independently reviews promotion/duplication boundaries;
- current active Skill usage evidence is recorded if genuinely used;
- no unauthorized Skill/Project/Runtime mutation occurred.

Then:

```text
STOP
```

zrx decides:

- whether C3B imports one or more mature existing Skills;
- whether Skill baseline is complete enough to proceed to M3 Project Vault reconstruction.
