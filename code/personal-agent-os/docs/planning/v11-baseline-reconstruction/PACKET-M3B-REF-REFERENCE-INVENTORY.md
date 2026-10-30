# PAOS V1.1 Stage 1 — Packet M3B-REF Reference / Writer / Consumer Inventory

Decision owner: zrx  
Prerequisite: M3B accepted  
Mutation class: read-only only

## 0. Goal

Resolve the last live-reference and ownership ambiguity before the first Project filesystem mutation.

M3B-REF does not decide by directory name or mtime. It builds a path-level semantic inventory:

```text
path
→ who writes it?
→ who reads it?
→ what Project owns the resulting artifact?
→ is the path governance truth, runtime state, historical data, or a generated snapshot?
```

## 1. Scope

Bounded roots only:

```text
C:\Users\remo\Desktop\OBSBOT-first-month-workspace
C:\Users\remo\Desktop\OBSBOT-workspace-M
```

plus currently known PAOS references that point into those roots.

Do not broad-scan the disk.

## 2. s027 — primary inventory

Update own TODO first.

### REF-001 — live path/reference inventory

Collect references from:

- Project registry `root_path` / `key_files` / declared artifacts;
- current Work/Session/Agent outputs where paths are operationally used;
- current Workstation / legacy Agent entry paths;
- PAOS `docs/planning`, `docs/workflows`, user/architecture docs and runbooks;
- scripts/config only where a path is actually resolved or written;
- known manual/Agent output references in the two monthly workspaces.

Classify each hit:

```text
WRITE-AUTHORITY
READ-CONSUMER
GOVERNANCE-REFERENCE
HISTORICAL-DATA-STRING
GENERATED-SNAPSHOT
ARCHIVE-ONLY
UNKNOWN
```

Required row fields:

```text
reference_id
source file / registry object
referenced path
Project
consumer/writer
classification
currently active?
would path change break behavior?
replacement target class
rewrite needed before cutover?
evidence
confidence
```

Important: do not count a path string inside an index/log as a live reference without semantic evidence.

### REF-002 — 1004 six-file ownership inventory

Inspect exactly:

```text
FM/90-Agent-Ops/1004-s003-scan/
  file-index.jsonl
  INDEX.md
  agent-session-map.md
  project-files-map.md
  scan-methodology.md
  scan-summary.json
```

For each file record:

```text
declared 1004 artifact?
producer / Work
actual consumers
contains old absolute paths?
path strings are data or dependency?
rebuildable?
authoritative/current or snapshot?
recommended owner:
  1004-WORK
  SHARED-MATERIAL
  HISTORICAL-EVIDENCE
  GENERATED-REBUILDABLE
  UNKNOWN
future destination class
hash / size / mtime
```

For `file-index.jsonl`, sample/parse enough content to determine semantics without rewriting it.

### REF-003 — Project-scoped write map

For 1001 / 1002 / 1004 / 2001 / 2002, identify:

```text
current write targets
current read targets
current registry truth
current key-file truth
Agent/Workstation paths that can emit new files
monthly-root dependency that must survive until cutover
```

Do not stop writers.

Outputs:

```text
s027/V11-M3B-REF-LIVE-REFERENCE-INVENTORY.md
s027/V11-M3B-REF-1004-OWNERSHIP-MATRIX.md
s027/V11-M3B-REF-PROJECT-WRITE-MAP.md
```

## 3. s029 — independent review

Update own TODO first.

Independently challenge:

- live-reference vs historical-string classification;
- 1004 ownership, especially `file-index.jsonl`;
- whether any proposed future rewrite would silently break current behavior;
- whether a root-level writer is incorrectly treated as a 1004 writer;
- whether a Project-scoped checkpoint can safely replace a full-FM freeze for 1004;
- whether any current consumer makes 1004 unsuitable as first mutation.

Use `skill-independent-review` only if genuinely useful and log honest usage if used.

Output:

```text
s029/V11-M3B-REF-INDEPENDENT-REVIEW.md
```

## 4. s010 — Coordinator reconciliation

Use `wf-coordinator-governance-cycle`.

Return:

```text
coordinator/V11-M3B-REF-COORDINATOR-READBACK.md
coordinator/COORDINATOR-TODO-AFTER-M3B-REF.md
```

Coordinator must answer:

### A. 1004 ownership verdict

For each of six files:

```text
1004-owned / shared / historical / generated / unresolved
```

### B. 1004 first-mutation readiness

Explicitly state:

```text
source set complete?
known writer list complete?
known consumer list complete?
scoped checkpoint possible?
any P1 path rewrite blocker?
M3C-1004 recommended? yes/no
```

### C. Reference rewrite classes

Group future rewrites into:

```text
registry/governance
runtime/Agent entry
repo docs/planning
historical data — do not rewrite
generated snapshots — rebuild or retain
```

### D. Monthly-root archive blockers

List all remaining active writers/references that prevent final archive.

Do not archive.

## 5. Scoped checkpoint design

M3B-REF must propose the exact M3C-1004 checkpoint, but not execute it.

Expected shape:

```text
T0 capture 1004 source hashes/mtimes
T0 identify known 1004 writers
short observation window
T1 recheck source set
PASS if no relevant 1004 source change
copy staged destination
hash verify
pre-switch final recheck
registry/reference switch
new root becomes sole write authority
old 1004 subtree becomes sealed migration source
```

Important:

> 2001 writing somewhere else under FM does not automatically fail the 1004 checkpoint.

The checkpoint fails only if the 1004-owned source set or its live references/writers change.

## 6. Archive-location rule

Do not propose PAOS Project 3002 `Archive/` as the home for OBSBOT legacy workspaces.

Archive should live in:

- the eventual OBSBOT Project-first parent; or
- another Human-approved OBSBOT/external archive location.

Exact path remains undecided in this packet.

## 7. Prohibited mutation

M3B-REF does not authorize:

- creating the Project-first parent;
- creating any Project root;
- copying/moving files;
- editing registry/key_files;
- rewriting docs/planning/workflow references;
- stopping legacy workspace writes;
- making a path read-only;
- archiving/deleting anything;
- changing Workstation/Runtime/CAT state.

Only reports, personal TODO updates, and normal append-only Skill usage logging are allowed writes.

## 8. Stop conditions

STOP affected work if:

- reference semantics cannot be determined without mutating the source;
- a 1004 file is actively shared by another Project in a way that ownership cannot be separated;
- a current writer is hidden behind an unknown external process;
- path replacement would require changing runtime state outside M3 scope;
- current Project truth conflicts with registry and cannot be resolved from existing evidence.

## 9. Done When

M3B-REF is complete when:

- every known live monthly-root reference is semantically classified;
- all six 1004 files have an ownership recommendation;
- 1004 writer/consumer set is explicit;
- a scoped no-new-writes checkpoint is designed;
- archive blockers are enumerated;
- s029 independently reviews the boundary;
- Coordinator recommends or rejects M3C-1004;
- no migration mutation occurred.

Then STOP.

zrx will decide whether the first filesystem mutation can begin.