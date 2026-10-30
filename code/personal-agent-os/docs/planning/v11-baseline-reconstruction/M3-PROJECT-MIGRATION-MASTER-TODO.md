# PAOS V1.1 Stage 1 — M3 Project Migration Master TODO

Decision owner: zrx  
Evidence baseline: M3A handoff  
Canonical PAOS baseline: main after #86

## 0. Purpose

This file is the execution truth for M3 after the read-only M3A Project truth refresh.

M3 is not “move every file into six folders”.

It has three jobs:

1. give each **currently migrated Project** one unambiguous canonical housing;
2. separate shared material from Project-specific truth without duplicating it;
3. leave dormant/unhoused/ambiguous Projects explicit rather than fabricating clean Vaults.

No task below is authorized merely because it is listed. Each mutation task becomes executable only when its prerequisite gate is marked approved.

---

# 1. M3A scope freeze

## 1.1 Stage-1 migration set

### Shared OBSBOT cluster — migrate in M3

```text
1001 周报
1002 调研
1004 文档整理
2001 LRC101
```

These four Projects currently share one physical root. They must be treated as one migration cluster until the shared-material boundary and canonical parent are frozen.

They do **not** need four copies of the same materials.

### 3002 Personal Agent OS — clean baseline reconstruction

Human decision supersedes the earlier preserve-root/defer-content approach.

Frozen target:

```text
C:\Users\remo\Desktop\agent学习计划\PAOS-Projects\3002-Personal-Agent-OS
```

Target Project Work World:

```text
INDEX.md
Inbox/
Materials/
Works/
Decisions/
Workstations/
Archive/
Source/personal-agent-os/   fresh accepted-main checkout
```

Shared Workflow/Skill Libraries remain outside the Project Vault.

The old `C:\Users\remo\Desktop\agent学习计划\personal-agent-os` root is preserved as legacy evidence after cutover, not as a compatibility target.

M3F now builds the clean Project/runtime baseline before M4. M4 will create fresh Workstations in the new root rather than migrate legacy daily-entry files.

See `M3F-3002-CLEAN-BASELINE-DECISION.md`, `M3F-3002-E-PRODUCTION-CUTOVER-DECISION.md`, and `M4-M5-POST-CUTOVER-CONVERGENCE-PLAN.md`.

### Explicitly deferred in Stage 1

```text
1003 汇报准备
1005 周课
2002 CD101
2003 RC101应用场景调研
3001 obs-agent
```

Disposition:

- 1003 = `UNHOUSED-PENDING-HUMAN`
  - configured `Desktop\lesson` path is invalid;
  - do not repair or create it automatically.
- 1005 / 2002 / 2003 = `UNHOUSED-DEFERRED`
  - real Work exists but no trustworthy root/housing source exists;
  - do not create empty Vaults.
- 3001 = `DORMANT-RETAIN`
  - dedicated root exists and is internally coherent;
  - low activity does not justify Stage-1 content migration.

These Projects stay in registry/history unchanged unless a later Human decision reactivates housing work.

This is an intentional Stage-1 scope decision, not a lifecycle/status mutation.

---

# 2. Canonical shared-root principle

The old invariant “one Project ID = one dedicated canonical Project root” still holds for Projects that complete Stage-2 cutover.

Shared material keeps one authoritative source, but an active Project may also keep Project-local reference snapshots when that materially improves normal Human/Agent work. Global deduplication must not turn a Project Vault into a thin index.

Preferred model:

```text
<canonical OBSBOT parent>/
├─ Shared-Materials/
└─ Projects/
   ├─ 1001-周报/
   ├─ 1002-调研/
   ├─ 1004-文档整理/
   └─ 2001-LRC101/
```

Each dedicated Project root owns:

- its Work artifacts;
- its Decisions;
- its Agent homes;
- its Project-specific Materials;
- Project-local reference snapshots needed for practical working locality.

Cross-Project/shared material remains authoritative in its shared source. Project-local copies are allowed as explicitly labeled reference snapshots with provenance; they are not competing authoritative sources.

## Project-first canonical storage

Human architecture decision:

> Monthly workspaces were useful as a temporary stage-based capture mechanism, but long-term canonical work must be organized by Project, not by month.

Therefore:

- `OBSBOT-first-month-workspace` and `OBSBOT-workspace-M` are **legacy monthly/phase workspaces**, not future canonical Project roots;
- M3 must reconcile their useful current content into Project-specific roots plus shared materials;
- once Project roots are complete, references are switched, and no live writes remain, the monthly workspaces become immutable archive/history;
- future monthly reporting should be generated as Project views/reports/snapshots, not as a new writable canonical workspace.

The monthly dimension becomes **time metadata / reporting / archive**, not the ownership axis of working files.

The exact `<canonical OBSBOT parent>` is not frozen yet because M3A found two related workspaces:

```text
OBSBOT-first-month-workspace
OBSBOT-workspace-M
```

Human clarification after M3A:

- `OBSBOT-workspace-M` contains an embedded/continued copy of `OBSBOT-first-month-workspace`;
- after that, Agents appear to have continued writing new documents back into the standalone `OBSBOT-first-month-workspace`.

Therefore the two roots must be treated as a **diverged workspace family**, not as a simple “old root -> newer superset root” chain.

M3B must establish three sets:

```text
COMMON BASELINE
= material present in the embedded first-month lineage

FIRST-MONTH POST-FORK DELTA
= newer/unique material written only back into OBSBOT-first-month-workspace

WORKSPACE-M DELTA
= material unique to OBSBOT-workspace-M, including later-month/continuation content
```

Default architectural recommendation is now:

```text
CREATE-NEUTRAL-PARENT
```

unless M3B proves one existing root actually contains both deltas with no live divergence.

The neutral parent must be a sibling/new canonical workspace, not nested inside either legacy root. Exact path/name still requires M3B evidence and zrx approval before creation.

After successful cutover, both legacy monthly workspaces should move to a **Legacy Monthly Workspace Archive** state. Do not delete them in Stage 1. Archive eligibility requires:

```text
all current Project artifacts reconciled
+ all live references switched
+ no relevant new writes during final checkpoint
+ migration manifest/integrity evidence complete
+ rollback no longer depends on writable legacy state
```

The archive may preserve the original directory trees read-only for provenance; Project-specific current work must not continue there.

---

# 3. First mutation sample decision

Do **not** use `3002/.paos/agents/3002-s027` as the first Project migration sample.

Reason:

- it is Agent/runtime history, not Project Vault content;
- it overlaps M4 legacy-entry/TODO migration;
- using it would validate the wrong boundary.

The preferred first Project mutation sample is:

```text
1004 文档整理
```

Why:

- it has identifiable Project-owned material (`90-Agent-Ops/1004-s003-scan`);
- it is lower activity than 2001;
- it is inside the shared-root problem we actually need to solve;
- it can demonstrate dedicated root + shared references without touching LRC101 Human material;
- rollback can be copy-first / registry-last.

M3C-1004 remains blocked until M3B freezes the canonical OBSBOT parent and exact source manifest.

---

# 4. Task graph

## M3B-001 — OBSBOT root-family relationship

Status: DONE — M3B read-only reconciliation accepted

Owner: s027  
Reviewer: s029

Determine the relationship between:

```text
C:\Users\remo\Desktop\OBSBOT-first-month-workspace
C:\Users\remo\Desktop\OBSBOT-workspace-M
```

Human fact already establishes a likely fork/divergence: workspace-M contains the first-month lineage, but standalone first-month later received additional Agent writes.

Therefore M3B-001 should not spend effort asking only “which root is newer?”. It must produce a **delta reconciliation map**.

Required evidence:

- tree/top-level comparison;
- modification history where available;
- current live references from registry/Work/Agent outputs;
- which one contains newer unique material;
- embedded/ancestor relationship between the first-month lineage and workspace-M;
- exact post-fork files unique/newer in standalone first-month;
- exact files/subtrees unique to workspace-M;
- whether both locations are still receiving writes;
- whether a neutral common parent is needed instead of choosing either as canonical.

Return one recommendation:

```text
CREATE-NEUTRAL-PARENT
USE-FIRST-MONTH-AS-PARENT   # only if it provably contains workspace-M delta too
USE-WORKSPACE-M-AS-PARENT   # only if it provably contains post-fork first-month delta too
DECISION-REQUIRED
```

Given the Human clarification, `CREATE-NEUTRAL-PARENT` is the default unless one-root-superset is proven by file-level evidence.

No directory creation.

## M3B-002 — 1004 ownership/source manifest

Status: PARTIAL — six-file candidate set found; file-index/shared semantics require M3B-REF

Owner: s027  
Reviewer: s029

Freeze the exact 1004-owned source set.

At minimum inspect:

```text
90-Agent-Ops/1004-s003-scan/
registry-declared artifact paths
current Work/Session references
any 1004-specific outputs outside that subtree
```

Classify each item:

```text
PROJECT-SPECIFIC
SHARED-REFERENCE
RUNTIME-EVIDENCE
HISTORICAL
UNKNOWN
```

Produce exact copy/move candidates, references that must survive, and hashable source manifest.

## M3B-003 — shared-cluster dedicated-root plan

Status: PARTIAL — Project-first direction accepted; exact cutover roots remain blocked by reference inventory

Owner: s027  
Reviewer: s029  
Coordinator: s010

For 1001/1002/1004/2001, propose exact future roots relative to the M3B-001 canonical parent.

Rules:

- no shared-content duplication;
- no 2001 runtime/Workstation move in this task;
- 1001/1002 may have “thin” Project roots containing their own Works/Decisions/Workstations plus references to shared materials;
- 2001 remains last mutation in the cluster;
- registry switch happens only after destination exists, content/reference verification passes, and rollback is recorded.

## M3B-004 — 3002 boundary reference check

Status: DONE — no live semantic contradiction; M4 transition remains

Owner: s029  
Evidence owner: s027 as needed

Only verify that the frozen 3002 taxonomy above does not contradict a live consumer.

Specifically check whether anything currently treats:

- `.paos/workstations/` as a stable Agent home;
- top-level `Workstations/` as Cycle evidence;
- `reviews/` as an authoritative lifecycle store;
- Vault dirs as replacements for repo source tree.

If no contradiction, close M3B-004. Do not produce another broad 3002 inventory.

---

# 4.1 M3B-REF — Reference / writer / consumer gate

Status: APPROVED READ-ONLY

Before M3C-1004, resolve:

- semantic classification of old-path references;
- producer/consumer/ownership of the six 1004 files;
- Project-scoped writer map;
- 1004-scoped no-new-writes checkpoint;
- archive blockers.

See `M3B-REFERENCE-INVENTORY-DECISION.md` and `PACKET-M3B-REF-REFERENCE-INVENTORY.md`.

Important migration rule:

> FM can remain writable for 2001 while 1004 migrates, provided the 1004 source set and its consumers/writers are stable and the final cutover preserves a single write authority.

Temporary verified copies are staging artifacts, not competing truth, as long as the registry/reference switch occurs only after verification and old/new are never both writable canonical locations.

---

# 5. Future mutation tasks

These are **planned but not yet authorized**.

## M3C-1004 — First bounded Project migration

Status: DONE — first Project-first root and atomic governance cutover proven

Frozen destination:

```text
C:\Users\remo\Desktop\OBSBOT-Projects\1004-文档整理
```

Frozen Work package:

```text
Works\1004-s003-scan\
  file-index.jsonl
  scan-summary.json
  INDEX.md
  agent-session-map.md
  project-files-map.md
  scan-methodology.md
```

`file-index.jsonl` = 1004-owned generated-rebuildable snapshot. Keep with the Work package; do not put a second copy in Shared-Materials.

Prerequisites:

- M3B-REF accepted;
- T0 source hash/writer/consumer checkpoint PASS;
- destination path absent or empty of conflicting user content;
- no manual 1004 scan rerun during the batch;
- s029 staged-copy review PASS before governance switch.

Expected strategy:

```text
T0 full source checkpoint
→ create dedicated 1004 Project root
→ initialize standard Vault structure
→ copy six-file Work package to Works/1004-s003-scan
→ hash verification
→ s029 staged-copy PASS
→ T1 final source checkpoint
→ update current 1004 root/artifact governance references LAST
→ verify through real PAOS read path
→ s029 post-cutover review
→ keep old source intact
```

Registry/governance update is last, not first. The old source remains rollback evidence until the legacy monthly workspace archive phase.

## M3D-1001 / M3D-1002 — Thin routine Project roots

Status: DEFERRED BEHIND ACTIVE-PROJECT PRIORITY

1004 has proven the shared-root migration pattern. 1001/1002 remain valid later thin-root migrations, but are no longer a prerequisite for starting 2001 reconstruction.

Likely shape:

- dedicated current Work/Decision/Workstation home;
- shared materials referenced from canonical shared location;
- no bulk copy of OBSBOT research trees.

## M3E-2001 — LRC101 dedicated housing

Status: DONE — CUTOVER-PASS; canonical Project root switched at revision 1069

Human priority decision after successful M3C-1004: start the active LRC101 Project before the thin 1001/1002 roots.

Frozen intended destination:

```text
C:\Users\remo\Desktop\OBSBOT-Projects\2001-LRC101
```

The destination itself will be both the PAOS canonical Project root and the independent Obsidian Vault. No nested `Vault/` layer.

Earlier reconstruction scope:

- map current LRC101 canonical artifact families across FM + workspace-M;
- map writers/readers, registry Artifacts, key_files and Work/Session references;
- classify Human-DND, shared material and runtime evidence;
- map stable Workstation continuity;
- determine whether the current relocation contract is sufficient, especially for live key_files.

M3E-A returned NEED-CONTRACT-EXTENSION. M3E-B now closes key_files, Artifact MOVE/RETAIN accounting, ownership, Human-DND policy and writer scope before code implementation.

M3E-B returned BLOCKED-UNRESOLVED-ARTIFACT. M3E-C reduced the live root-sensitive set enough to stop Web-led file archaeology.

M3E-D completed the staged Vault and relocation-v2 implementation. PR #98 was merged and deployed. M3E-E then completed the Human-only atomic cutover.

Final live Project 2001 state:

```text
revision   1069
root       C:\Users\remo\Desktop\OBSBOT-Projects\2001-LRC101
key_files  10
Artifacts  377
```

The cutover atomically committed 85 Artifact MOVE pointers, 37 REBIND pointers, 168 explicit retained pointers, ordered key_files_after, and the new root. One `project.root.relocated` Ledger event and one v2 durable receipt were written; replay is idempotent.

Old FM/workspace-M sources remain preserved and are not yet archived. LRC101 migration work is closed. Future validation should happen through normal Project work, not another migration packet.

See also:

- `M3E-2001-B-DECISION.md`;
- `PACKET-M3E-2001-B-CONTRACT-OWNERSHIP-CLOSURE.md`;
- `M3E-2001-C-DECISION.md`;
- `PACKET-M3E-2001-C-ROOT-SENSITIVE-ARTIFACT-CLOSURE.md`;
- `M3E-2001-D-LOCAL-VAULT-IMPLEMENTATION-PLAN.md`;
- `M3E-2001-E-PRECUTOVER-COMPLETION.md`.

See:

- `M3E-2001-ACCELERATION-DECISION.md`;
- `PACKET-M3E-2001-LRC101-VAULT-RECON.md`.

LRC101 Vault policy is locality-first: Project-owned process/current documents become canonical inside the Vault, and commonly needed related files are copied into Materials as provenance-tracked reference snapshots where practical. See `M3E-2001-VAULT-LOCALITY-DECISION.md`.

This was the highest-value and highest-risk M3 Project migration and is now complete.

## M3F-3002 — Clean Project/runtime baseline

Status: DONE / CUTOVER-PASS

M3F constructs a new Project Work World instead of cleaning the old repo in place.

Core result:

```text
new dedicated Project root
+ fresh Source checkout
+ selected current Works/Decisions/Materials
+ controlled canonical private-data handoff
+ atomic Project-3002 root/key_files/Artifact cutover
+ old root frozen as legacy evidence
```

Compatibility with old daily ENTRY/TODO/Runtime paths is not required.

Historical PAOS governance facts remain preserved. Current Project truth is selectively promoted; old Runtime residue is not bulk imported.

Fresh Workstations were created after cutover. Follow-up now proceeds through M4 post-cutover convergence: real cold starts, legacy dependency observation, knowledge consolidation, and legacy-root retirement.

See `M3F-3002-CLEAN-BASELINE-DECISION.md`.

---

# 6. Deferred Project decisions

## D-M3-1003

Need Human fact:

- real replacement root, if any;
- otherwise leave as unhoused/dormant until reactivated.

No automatic path repair.

## D-M3-1005 / 2002 / 2003

Need a real housing source or Human reactivation decision before a Vault is created.

Do not use “has doing Work” alone as justification for an empty root.

## D-M3-3001

Remain dormant-retain unless new Work makes Vault migration useful.

---

# 6.1 Legacy monthly workspace archive policy

After 1001/1002/1004/2001 complete Project-root cutover:

```text
OBSBOT-first-month-workspace
OBSBOT-workspace-M
```

must no longer be writable working roots.

Preferred disposition:

```text
Archive/Legacy-Monthly-Workspaces/
  OBSBOT-first-month-workspace/
  OBSBOT-workspace-M/
```

or an equivalent Human-approved archive location.

Rules:

- preserve original structure for provenance;
- do not keep duplicate “current” copies inside the archive;
- do not use archived monthly roots as future Agent entry points;
- Project documents remain canonical in Project roots;
- shared materials remain canonical in the shared-material location;
- monthly/phase summaries may still be generated, but they are reports, not work roots.

Exact archive path is decided only after cutover evidence; no archive move is authorized by M3B.

---

# 7. No-delete rule

Stage-1 M3 default:

```text
copy / move / archive / reference
```

not delete.

Human-created evidence is never deleted merely because a canonical replacement exists.

Generated/rebuildable content can become `generated-delete-candidate` only after active references are proven absent.

---

# 8. M3 exit condition

M3 is complete enough to enter M4 when:

- shared-root cluster has dedicated current Project housing or explicit accepted exceptions;
- 2001 current Project root/housing is unambiguous;
- 3002 Vault/runtime/repo boundaries are frozen and not competing;
- deferred Projects have explicit non-migrated dispositions;
- no active Project migration relies on filename archaeology;
- every moved canonical artifact has source/rollback/reference evidence;
- no competing current root remains for migrated Projects.