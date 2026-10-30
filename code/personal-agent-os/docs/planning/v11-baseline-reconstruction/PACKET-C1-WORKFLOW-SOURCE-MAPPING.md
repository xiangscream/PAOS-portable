# PAOS V1.1 Stage 1 — Packet C1R Two-Layer Source Mapping

Decision owner: zrx  
Task: M1-002 only  
Mutation class: read-only mapping / report writing

> This packet supersedes the earlier C1 framing that tried to map sources into a broad 12-Workflow / 6-Guide / 6-Template catalog.

## 0. Purpose

V1.1 now uses only two conceptual method layers:

```text
Workflow Kernel
= universal Work-management / TODO / collaboration / acceptance / handoff protocol

Skill Library
= reusable task/domain execution experience
```

C1R answers:

> Which existing practices belong to the universal operating kernel, and which should be preserved as Skills instead of being frozen into task-class Workflows?

The goal is not to design more Workflows. The goal is to prevent Workflow from competing with Agent intelligence.

## 1. Baseline

Canonical PAOS main at authorization is the main containing the two-layer architecture decision.

Shared Library remains:

```text
C:\Users\remo\Desktop\agent学习计划\PAOS-Libraries
├─ workflow   # empty baseline
└─ skill      # empty baseline
```

The primary registry remains canonical `C:/...` and must not be edited during C1R.

## 2. Participants

### s027 — primary mapper

- update own TODO first;
- inventory current Workflow/Guide/Skill-like sources;
- compare approved-main and local-dirty versions;
- split files into semantic units;
- classify each semantic unit into the two-layer model;
- connect claims to real Run evidence;
- produce the primary source map + Kernel/Skill Boundary Matrix;
- do not author canonical Workflow or Skill files.

### s029 — independent semantic reviewer

- update own TODO first;
- challenge whether a proposed Workflow rule is truly universal;
- push task/domain execution methods toward Skill unless governance semantics require Workflow;
- detect duplicate concepts and hidden Project/Runtime leakage;
- verify real successful behavior is not discarded merely because it is undocumented;
- return alternate classifications and P1/P2.

### s010 — Coordinator

- keep C1R read-only;
- provide current Work/consumer context only when file evidence is ambiguous;
- preserve disagreements for zrx rather than silently resolving them;
- return reconciliation + TODO state.

### s031

No broad assignment. Request only narrow factual clarification if a Runtime-specific source cannot be classified otherwise.

## 3. Required source scope

At minimum inspect:

```text
docs/AGENT-EMPLOYEE-GUIDE.md
docs/COORDINATOR-OPERATING-GUIDE.md
docs/WORKFLOW-PHILOSOPHY.md
docs/USER-AND-ARCHITECTURE-GUIDE.md
docs/runbooks/PAOS-DEVELOPMENT-WORKFLOW.md
docs/workflows/*
README.md
AGENTS.md
START-HERE.md
docs/planning/workflow-problem-pack-20260914/
relevant local planning / review evidence
```

Also inspect the reusable operating lessons demonstrated by:

```text
B2b2 OpenCode Wake
B2c Mail -> Agent activation
B2c3 CAT -> Agent activation
M0 reconnaissance
Packet A review
Packet B0 transition mapping
Packet B1 clean-runner / Library-root migration
Packet B1 path-P1 exact-head cross-runtime gate
```

Do not archive every report into the Library. Extract only repeated lessons.

## 4. Primary classification

Each semantic unit gets exactly one primary destination:

```text
WORKFLOW-KERNEL
WORKFLOW-SUPPORT-GUIDE
WORKFLOW-SUPPORT-TEMPLATE
SKILL-CANDIDATE
PROJECT-LOCAL
REPO-DOC
EVIDENCE-ONLY
NO-PROMOTION
```

### WORKFLOW-KERNEL test

Use only when the content answers a universal organizational question such as:

- who owns the Work?
- what is the current responsibility?
- what should the Agent do on resume?
- how should TODO stay current?
- when should another Agent / Coordinator / Human be involved?
- what evidence is needed before review/acceptance?
- what must happen before closeout/handoff/standby?

If the content explains how to perform a profession/task, it fails this test.

### SKILL-CANDIDATE test

Use when the content is about execution experience, for example:

- software change / exact-head engineering technique;
- code review technique;
- research synthesis;
- PRD/product definition;
- clean writing;
- migration planning;
- evidence analysis;
- project-material ingestion.

A Skill may be opinionated and task-specific. It must not own PAOS Work status or acceptance authority.

### REPO-DOC test

Use when the content is specific to PAOS source maintenance, exact scripts, adapters, repo layout or developer runbooks.

### PROJECT-LOCAL test

Use when the rule only makes sense inside one Project.

## 5. Required source-map fields

For each semantic unit:

```text
source_id
source_path
source_version:
  approved-main | local-dirty | local-only | historical-evidence | real-run

section / semantic unit
current meaning
current consumers / references
current authority:
  current | transitional | evidence-only | unclear

real-run evidence

primary classification:
  WORKFLOW-KERNEL
  WORKFLOW-SUPPORT-GUIDE
  WORKFLOW-SUPPORT-TEMPLATE
  SKILL-CANDIDATE
  PROJECT-LOCAL
  REPO-DOC
  EVIDENCE-ONLY
  NO-PROMOTION

target ID / candidate name
recommended action:
  extract | adapt | keep-local | keep-repo-specific | not-promote | deprecate-later

conflict / overlap
canonical recommendation
retirement condition
open decision
confidence
```

If one source contains multiple methods, split it into multiple rows.

## 6. Divergent tracked-doc rule

For each relevant tracked file modified in the dirty primary workspace:

1. capture approved-main semantics;
2. capture local-working-tree semantics;
3. compare meaning, not only line diff;
4. classify changes:
   - factual correction;
   - V1.1 architecture update;
   - task-specific method;
   - in-flight experiment;
   - writing cleanup;
   - obsolete wording;
5. recommend:
   - Workflow Kernel extraction;
   - Skill candidate extraction;
   - repo-specific patch;
   - Project-local retention;
   - no promotion.

Do not reset/stash/checkout/edit these source files during C1R.

## 7. Kernel Coverage Matrix

The Workflow Kernel baseline hypothesis is deliberately small.

### Core Workflows

```text
wf-agent-work-cycle
wf-coordinator-governance-cycle
```

### Support candidates

```text
guide-todo-and-self-management
guide-truth-collaboration-and-escalation
guide-evidence-review-and-acceptance
guide-workflow-and-skill-boundary

tpl-work-brief
tpl-handoff-summary
```

For each item report:

```text
artifact ID
why it exists
source coverage
real-run evidence
missing input
overlap
keep / merge / split / remove / rename
reviewer position
open decision
```

A missing support file is acceptable if the rule can live cleanly inside one of the two Workflows.

## 8. Skill Candidate Matrix

Do not author Skills yet. Build the first candidate map.

At minimum evaluate whether existing evidence supports candidates like:

```text
clean-writing
software-change
independent-review
research-to-decision
product-definition / prd-structuring
migration-planning
evidence-analysis
project-material-ingest
```

This is not a mandatory list.

For each candidate:

```text
candidate skill ID
source evidence
real-run evidence
reusable capability
known failure modes
Project/Runtime leakage to strip
overlap with another candidate
promotion recommendation:
  promote-next | later | project-local | repo-specific | reject
```

## 9. Required questions

C1R must explicitly answer:

1. What is the smallest Workflow Kernel that still gives Agent/Coordinator a complete business loop?
2. Which old task-class Workflow ideas should become Skills?
3. Which “workflow” content is actually PAOS repo maintenance and should stay repo-specific?
4. Which local-dirty Guide changes contain universal V1.1 operating truth?
5. Which local changes are task/domain experience and belong to Skills?
6. Which important operating rules are proven by real Runs but missing from docs?
7. Which Skill candidates are mature enough for the first Skill baseline?
8. Which candidates would over-constrain model judgment and should not be promoted?
9. What source docs can eventually become historical/redirect-only, and only after what replacement exists?
10. What exact first authoring batch should follow C1R?

## 10. Prohibited mutations

C1R does not authorize:

- editing `PAOS-Libraries/workflow`;
- editing `PAOS-Libraries/skill`;
- editing/moving/archiving source docs;
- changing `library-roots.json`;
- Project root/status changes;
- Project Vault cleanup;
- Workstation creation/cutover;
- Runtime activation-owner/adapter/hook/binding/Room/Participant changes;
- Session/Work lifecycle edits.

## 11. Outputs

s027:

```text
s027/V11-M1-002-TWO-LAYER-SOURCE-MAP.md
s027/V11-M1-002-KERNEL-SKILL-MATRIX.md
```

s029:

```text
s029/V11-M1-002-TWO-LAYER-INDEPENDENT-REVIEW.md
```

Coordinator:

```text
coordinator/V11-M1-002-TWO-LAYER-COORDINATOR-READBACK.md
coordinator/COORDINATOR-TODO-AFTER-M1-002.md
```

Use the existing handoff branch/folder unless Coordinator has a stronger canonical convention.

## 12. Stop gate

After reports complete:

```text
STOP
```

Do not start M1-003/M1-004, M2, M3 or M4.

zrx will freeze:

1. the final small Workflow Kernel;
2. the first Skill promotion batch;
3. the authoring order.

## 13. Done When

C1R is done when:

- all required sources are mapped semantically;
- divergent tracked docs have explicit dispositions;
- the two core Workflow candidates have coverage evidence;
- the Skill Candidate Matrix exists;
- task-class methods are not silently preserved as Workflow;
- s029 reports no unresolved classification P1;
- Coordinator preserves remaining canonical decisions for zrx;
- no unauthorized mutation occurred.
