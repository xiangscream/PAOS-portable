# PAOS V1.1 — Master Migration TODO V1

> Authoritative Stage-1 execution plan reconciled from the 2026-09-20 M0 handoff. This file turns local observations into bounded, reviewable migration work. Local Agent proposals are inputs; this is the first approved master plan.

## 0. Evidence baseline

Reconciled from:

- handoff branch `handoff/v11-m0-20260920` commit `ae6a678`;
- Coordinator Baseline Snapshot / Reconciliation Report / TODO;
- s027 local inventory + proposed TODO;
- s029 independent inventory + proposed TODO;
- s031 Runtime Workstation report.

Remote source baseline at reconciliation:

```text
PAOS main       b3db80219641f9bcba566e7d7d10f4546fcbc8ff
co-agent master f8aa18eabc942e9dec05d2db42fb2c33e695fd9a
#78 planning    merged at 9e1c69fe7aa299b379538031ec9c6568e228486a
#79 B1 auth     merged at 29d30b2c176929aae26a5bf172e68626fb9a0920
#80 path fix    merged at b3db80219641f9bcba566e7d7d10f4546fcbc8ff
```

Local dirty worktrees are evidence sources, not canonical source-code baselines.

---

# 1. Canonical decisions

These decisions resolve M0 disagreements. A local Agent may challenge them only with new factual evidence that changes the premise.

## C-001 — Shared Workflow / Skill roots

Canonical shared libraries will live **outside every Project Vault** under one shared parent:

```text
C:\Users\remo\Desktop\agent学习计划\PAOS-Libraries\workflow
C:\Users\remo\Desktop\agent学习计划\PAOS-Libraries\skill
```

Policy:

- `workflow` and `skill` are the two roots registered by A3b;
- parent `PAOS-Libraries` must have rollback/version history before content migration (Git-local or equivalent snapshot);
- `personal-agent-os/docs/workflows` is **not** the shared Workflow Library;
- repo docs may be source material and documentation, but cannot remain a competing canonical Workflow source after cutover;
- historical research directories such as `08-Agent研究实验室` / `09-Personal-Agent-OS-实施包` are not roots unless a later task explicitly promotes content.

Rationale: shared methods must survive Project and Runtime replacement and must not be owned by Project 3002's source repository.

## C-002 — Planning document identity

Numeric planning prefixes are not stable IDs.

V1.1 baseline planning lives under:

```text
docs/planning/v11-baseline-reconstruction/
  MASTER-PLAN.md
  EXECUTION-WORKFLOW.md
  LOCAL-AGENT-TODO-REPORT-TEMPLATE.md
  MASTER-MIGRATION-TODO.md
```

Existing numbered 38/39/40 historical files keep their names. Do not rename old planning merely to free numbers.

## C-003 — Stable Agent entry + transition-day authority

Canonical stable Agent home is:

```text
<Project Root>/Workstations/<agent-id>/
  ENTRY.md
  TODO.md
  mailbox/
```

Semantics:

- `ENTRY.md` = stable role/navigation, not current Work/Cycle/Runtime;
- `TODO.md` = current execution state;
- `.paos/workstations/<work>/<agent>/cycle-N/` = cycle evidence only;
- `.paos/agents/<agent>/ENTRY.md` = legacy/historical **after that Agent's explicit cutover**, never the long-term daily entry;
- edited/handwritten legacy ENTRY is never auto-deleted; preserve it, extract useful stable facts, archive it, then create fixed home;
- old TODO files are historical evidence after their current facts are reconciled; they do not remain competing current TODOs.

### Transition-day authority rule

Before an Agent passes its own M4 cold-start gate, **its pre-migration entry remains the only daily authority**. The new fixed Workstation may be created and reviewed, but it does not become authoritative merely because the files exist.

Per-Agent authority switches only at this point:

```text
old authority
→ create/reconcile fixed Workstation
→ reviewer verifies stable role + current TODO + roots
→ cold-start succeeds
→ Coordinator records cutover
→ fixed Workstation becomes sole daily authority
→ old entry becomes historical-only
```

There is never a period where two entries are both declared current.

For Project 3002, C-021 supersedes this compatibility-first per-Agent cutover. The new clean baseline creates fresh Workstations only after the new Project root/runtime are canonical; old daily-entry paths then become legacy evidence rather than compatibility targets.

Current transition authority from M0:

```text
s027  .paos/agents/3002-s027/ENTRY.md remains temporary authority until M4-027 cutover.
s031  Workstations/3002-s031/ENTRY.md is already the fixed authority; M4-031 normalizes its content.
s029  has no stable daily entry today; its current live Runtime/Cycle is transitional only.
      No fresh Runtime may cold-start s029 before M4-029 creates and accepts the fixed Workstation.
s010  current Coordinator Runtime/TODO remains transitional; no fresh Runtime cold-start before M4-010.
s028/s030 remain governed by P0-003 disposition and are not silently migrated.
```

During transition, Coordinator must not tell a fresh Runtime to “pick the newest-looking entry”. If an Agent has no accepted fixed Workstation, either continue the already-live Runtime or wait for its M4 migration.

Fixed Workstation stays minimal. Existing `outputs/` folders are transitional evidence locations, not a new long-term Workstation contract; formal reusable results belong in Project `Works/` or Project `Archive/` as appropriate.

## C-004 — Project migration eligibility

Registry `status=active`, Session state, and filesystem existence are different facts.

Every registry Project must receive one disposition:

```text
MIGRATE-ACTIVE       real active Project with a dedicated usable root
SHARED-ROOT          real Project, but current root is shared by multiple Project IDs
UNHOUSED             registry/current Work exists but root is empty or unavailable
DORMANT-RETAIN       not currently active enough to justify full migration; preserve history
ARCHIVE-CANDIDATE    clearly finished, only after explicit review
```

Hard invariant for Stage-2 cutover:

> one PAOS Project ID must resolve to one dedicated canonical Project root.

Multiple Project IDs may live under a common parent workspace, but their `root_path` values must not remain identical.

No registry status/root edit is authorized until its Project disposition + root map are reviewed.

## C-005 — Repository source used for migration

Do not run migration logic from dirty source worktrees, but do not assume the dirty worktree contains no current facts.

Policy:

- preserve the user's current dirty `personal-agent-os` and `co-agent-2` worktrees unchanged;
- **before the clean runner is allowed to drive mutations**, classify dirty/untracked files that currently claim or support canonical meaning;
- the clean runner controls executable PAOS code/version; it does **not** erase local Project facts that exist only in the dirty primary workspace;
- after #78 planning merges and P0-005 is reviewed, create a **new clean PAOS migration-runner worktree/clone** pinned to the approved `main`;
- Runtime-specific M4 verification later uses a separate clean co-agent runner pinned to approved `master`;
- runner code may target the real Project root/config explicitly; runner path itself is not a Project truth source;
- every command that intends to write the real installation registry must pass an explicit `--config` path to the primary installation. The clean runner's default registry path must never become a second truth source.

## C-006 — Single activation owner during transition

The migration must never allow two independent mechanisms to request a new model continuation for the same durable source.

Long-term rule:

```text
PAOS Agent Activation / Wake
= primary activation authority

Codex Stop hooks / legacy CAT Runtime adapters
= continuation plumbing only, or legacy-owned activation before that Agent/Room is migrated
```

Transition fence:

1. **Do not switch activation ownership during Packet B filesystem/library work.** Keep each currently working Agent on its already-observed activation path.
2. If a CAT Room is `activation_owner=paos`, no legacy CAT marker/adapter/bridge may independently wake that participant from the same Exchange. CAT #40 suppresses marker/rearm; any external legacy adapter still capable of wake must be proven stopped or placed in no-wake mode before `paos agent chat` is used for that target.
3. If an Agent still relies on a legacy activation path and the legacy path cannot be proven non-waking, PAOS Agent Activation is **not** enabled for that same source/target yet. Continue the existing path until M4 migration.
4. Codex Stop hooks may continue an already-running Codex turn only under their existing ownership fence; they are not allowed to replace or duplicate PAOS idle activation.
5. Every M4 Runtime cutover must record: old activation owner, new activation owner, exact disable/fence action, rollback, and an exactly-one-turn acceptance test.

P0-006 produces the read-only ownership map before any Runtime ownership change. M4-R02/R04 perform the actual cutover after rollback + fresh-Runtime evidence.

Before Stage-2 cutover, s031 must prove one unambiguous Stop/continuation chain per relevant Runtime path.

## C-007 — CAT Participant membership

CAT Participant membership is Room-local, not the global Agent roster.

`p-3002-s031` missing from one Room is a real assignment friction but **not** a reason to manufacture a Participant during baseline migration. Durable Workstation Mail remains valid for Agent assignment. Add a CAT Participant only when a real Room collaboration requires it and the stable Agent mapping is explicit.

## C-008 — Current baseline workforce

Baseline long-lived roles to migrate first:

```text
3002-s010  Project Lead / Coordinator
3002-s027  Implementation / Integration Engineer
3002-s029  Independent Reviewer / QA
3002-s031  Runtime Reliability Specialist
```

Packet A disposition:

- `3002-s028` = **transitional / in-flight**. Preserve its current Work/Session facts; do not make it a baseline long-lived employee role unless later Work proves that need.
- `3002-s030` = **current-scope inactive / standby candidate**. Preserve facts; do not migrate it into the baseline employee roster unless reactivated by a real responsibility.
- `3002-s020` remains current-scope inactive for Project 3002.

These are migration-scope decisions, not Session/Work lifecycle edits.

## C-009 — Packet B0 local-claim disposition

Packet B0 does **not** require the dirty primary workspace to be made clean before Packet B1. Instead, the local claims are given explicit ownership and later migration tasks:

| Local object | Canonical disposition before B1 | Later owner/task |
|---|---|---|
| `Workstations/3002-s031/` | **CURRENT-LOCAL-FACT**. Preserve in place. It is the current fixed authority for s031; do not copy into the runner. | M4-031 normalization |
| `.paos/agents/` | **CURRENT-LOCAL-FACT / transitional authority** where explicitly declared (notably s027). Preserve in place. | M4 per-Agent cutover |
| `.paos/workstations/` | **CYCLE/HISTORICAL EVIDENCE**. Preserve in place; never promote as stable home. | M3/M4 archive mapping |
| `docs/workflows/` | **CANDIDATE-CANONICAL SOURCE**, not the new shared root. Preserve untouched in primary. | M1-002 source mapping, then M1-003/004 synthesis |
| `docs/WORKFLOW-PHILOSOPHY.md` | **CANDIDATE-CANONICAL SOURCE**. Preserve untouched; no direct promotion merely because it is local-only. | M1-002 |
| tracked dirty `AGENT-EMPLOYEE-GUIDE.md`, `COORDINATOR-OPERATING-GUIDE.md`, `README.md`, `AGENTS.md`, `START-HERE.md`, staged PAOS development runbook and related guide edits | **DIVERGENT SOURCE MATERIAL**. Do not overwrite approved main and do not discard the local edit. Compare local-vs-main during M1-002; extract valid intent into shared Workflow/Guide or a separate repo-doc patch. | M1-002 + later reviewed repo-doc patch if needed |
| `docs/planning/47..58` and `workflow-problem-pack-20260914/` | **HISTORICAL / IN-FLIGHT EVIDENCE**. Preserve. They may inform M1 but are not imported wholesale. | M1-002 evidence input / M3 archive mapping |
| `reviews/`, gate results | **HISTORICAL EVIDENCE**. Preserve; not a canonical source. | M3 archive mapping |
| `private-data/` | **INSTALLATION ENTITY**. Never copy into runner/clone. Only explicitly authorized files may be changed in place. | M1-001 may create only `private-data/environment/library-roots.json` with explicit path |
| generated build/test clones/mojibake paths | **GENERATED / CLEANUP CANDIDATE**. Not a B1 input. | M3-090 / later explicit cleanup |

This resolves the B0 “clean runner misses local truth” P1 for **Packet B1 root setup**: the runner may execute approved code because all MUST-NOT-MISS local facts remain protected in the primary workspace and are explicitly scheduled for later mapping.

It does **not** resolve the content-level question “which local guide wording wins”. That decision belongs to M1-002 and is intentionally not required before empty Library roots exist.

## C-010 — Packet B0 activation-owner disposition

Current production activation owner remains **legacy CAT / existing Runtime paths** during Packet B1.

For Project 3002 production collaboration:

- Room `room-e7f0cfaa5c5f` remains `activation_owner=null` (legacy CAT owner);
- s027/s029 continue using their existing legacy CAT/OpenCode adapter path for B1 assignment/continuation;
- Coordinator must **not** use `paos agent chat` to switch that production Room to PAOS ownership during B1;
- any PAOS Wake binding that may exist is not treated as the assignment owner for the same CAT source while legacy adapters remain active;
- if an existing Runtime dies and safe restart would require changing activation ownership, stop that Agent's B1 task and return to Coordinator instead of improvising a second wake path.

For Codex/native:

- current global Stop-hook / bridge chains remain unchanged;
- no hook, current binding, Room owner, Participant or native Thread migration is part of B1;
- s031 is not required for B1 unless a narrow observation is explicitly requested.

The B0 activation map is accepted as sufficient to allow **filesystem/library** Packet B1 while keeping Runtime ownership frozen. Actual owner cutover remains blocked on M4-R02/R04 fresh-Runtime evidence.

## C-011 — Packet B0 transition-entry disposition

B0 confirmed the transition authority table in C-003. Packet B1 must use existing live/declared authorities only and must not create or cut over Agent Workstations.

- s027 may continue from its declared legacy ENTRY/current live Runtime;
- s029 uses its already-live Runtime for review; if that Runtime is lost, fresh start is blocked until M4-029;
- s010 remains the current Coordinator Runtime/TODO authority;
- s031 fixed Workstation remains untouched by B1.

Thus Packet B1 has **zero Workstation migration authority**.

## C-012 — Two-layer method architecture

V1.1 method architecture is now:

```text
Workflow Kernel
= universal Work-management / TODO / collaboration / acceptance / handoff protocol

Skill Library
= task/domain execution experience and capability
```

The previous “12 task-class Workflows / 6 Guides / 6 Templates” candidate baseline is superseded.

Task-class methods such as software development, PRD, research, document revision, product definition, independent review technique and migration planning must **not** be frozen as universal Workflows merely because they recur. They are Skill candidates unless the extracted rule is genuinely about universal Work management.

Baseline Workflow target:

```text
wf-agent-work-cycle
wf-coordinator-governance-cycle
```

Workflow support Guides/Templates may remain physically in the Workflow Library but are not a third conceptual method layer.

See:
`docs/planning/v11-baseline-reconstruction/TWO-LAYER-WORKFLOW-SKILL-ARCHITECTURE.md`.

## C-013 — C1R Kernel freeze

C1R handoff `2e1669d8ee280445ed8261a99c063a3802683438` is accepted.

Final Layer-1 baseline:

```text
wf-agent-work-cycle
wf-coordinator-governance-cycle
```

No mandatory Guide/Template baseline is required. Empty `Guides/` and `Templates/` are valid.

Boundary rules:

- Workflow owns universal Work management: responsibility, TODO, collaboration/escalation, evidence/acceptance boundary, handoff/standby.
- Workflow references authoritative PAOS authority/lifecycle facts and never copies their matrix/state machine.
- Skill owns task execution technique.
- ACK/inbox/wake signals are not Work completion or acceptance.
- exact-head / test ladder / real-machine smoke remain Skill technique, not Kernel.
- local `docs/workflows/` and `WORKFLOW-PHILOSOPHY.md` are not promoted as parallel shared artifacts; extract useful semantics, then retain as evidence until cleanup.

First Skill promotion batch:

```text
skill-engineering-change
skill-independent-review
```

`clean-writing` remains a known candidate but requires exact local source discovery before import.

See:
`C1R-KERNEL-FREEZE-DECISION.md`.

## C-014 — C2 accepted: first usable two-layer Library baseline

C2 handoff `e5c8328` is accepted.

Canonical external Library state:

```text
Workflow Kernel
  wf-agent-work-cycle                 active
  wf-coordinator-governance-cycle    active

Skill Library
  skill-engineering-change            active
  skill-independent-review            active
```

Accepted Library commits:

```text
1500b01f22cde59d7b7b6899dd51328303154df0  Workflow activation + Catalog
7669dc893063ea8d1f6e47334594158ee3054e3c  first two Skill candidates
f9962c0144948ae24ecfe3978bcf840bb9e956ee  Skill activation + Catalog
```

C2B caught one P1 where Kernel language leaked exact-head/push-style execution detail. The narrow fix was independently re-reviewed before activation. This is accepted as evidence that the Workflow/Skill boundary is functioning as intended.

C2 semantic scenario tests show:

- the same Agent Workflow applies to software, PRD/product, research, document cleanup, migration and review tasks;
- Coordinator behavior is task-class independent;
- Skills remain execution technique and do not own acceptance/governance.

C2 does **not** by itself prove long-run productivity benefit. Real-use evidence begins in later Stage-1 work and flywheel runs.

Deferred non-blocking C2 items:

- minor README frontmatter example drift;
- small overlap between the first two Skills around baseline/evidence discipline;
- real-machine smoke wording must remain conditional/risk-based;
- generated Catalog `root_path` may use runtime-local mount syntax.

Do not reopen C2 for these without real friction.

## C-015 — C3A accepted: known Skill source baseline

C3A handoff `1a3c421` is accepted.

Facts:

- exact `clean-writing` source exists at `C:\Users\remo\.codex\skills\clean-writing\`;
- desktop/zip/temp/test variants are copies or residues, not independent sources;
- Runtime/vendor/system packages remain Runtime-owned and are not mass-promoted;
- PAOS-Libraries is not currently auto-loaded by Codex;
- `skill-independent-review` received one real usage event at score `0.5`;
- no new Skill was imported during C3A.

C3B is authorized for **clean-writing only**:

```text
source verify
→ normalize to paos-skill/v1 as clean-writing
→ independent semantic review
→ activate if PASS
→ rebuild Skill Catalog
→ STOP
```

No other discovered Skill candidate is authorized for import.

See `C3A-SKILL-BASELINE-DECISION.md` and `PACKET-C3B-CLEAN-WRITING-IMPORT.md`.

## C-016 — C3B accepted: method baseline closed

C3B handoff `05e310a` is accepted.

Accepted PAOS-Libraries HEAD:

```text
e313e9377e7d189ec48a4b18ea926c64477d6348
```

Canonical method baseline:

```text
Workflow
  wf-agent-work-cycle
  wf-coordinator-governance-cycle

Skills
  skill-engineering-change
  skill-independent-review
  clean-writing
```

`clean-writing` passed source verification, normalization, independent review, one narrow P1 fix, follow-up review, activation and Catalog rebuild.

No further Skill promotion is required before M3.

The untracked usage-event vs committed Catalog replayability issue is deferred as `R2-SKILL-TELEMETRY-001`; do not reopen C3B.

Next authorized work is M3A read-only Project truth refresh. See `C3B-METHOD-BASELINE-CLOSE.md` and `PACKET-M3A-PROJECT-TRUTH-REFRESH.md`.

## C-017 — M3A accepted: Project scope frozen before mutation

M3A handoff is accepted.

Stage-1 Project scope is now:

```text
MIGRATE CLUSTER
  1001 周报
  1002 调研
  1004 文档整理
  2001 LRC101

PRESERVE ROOT / DEFER CONTENT MOVE
  3002 Personal Agent OS

DEFERRED / NO VAULT CREATION
  1003 汇报准备            UNHOUSED-PENDING-HUMAN
  1005 周课                UNHOUSED-DEFERRED
  2002 CD101              UNHOUSED-DEFERRED
  2003 RC101应用场景调研    UNHOUSED-DEFERRED
  3001 obs-agent           DORMANT-RETAIN
```

1003's invalid `Desktop\lesson` pointer is not auto-repaired. 1005/2002/2003 do not receive empty Vaults merely because Work is marked doing.

3002 taxonomy is frozen:

- `Workstations/` = stable Agent homes;
- `.paos/workstations/` = Cycle evidence;
- `.paos/agents/` = legacy/transitional until M4;
- Vault dirs are additive Project work-world directories;
- repo source/docs remain repo source/docs;
- 3002 content moves wait until M4 avoids competing Agent-entry truth.

The first mutation sample will **not** be `3002-s027` Agent history. Preferred first Project sample is 1004 after its source set and the canonical OBSBOT parent are frozen.

See `M3-PROJECT-MIGRATION-MASTER-TODO.md`.

## C-018 — M3B accepted: reference inventory required before first mutation

M3B handoff `64a3d31` is accepted.

Accepted facts:

- FM and workspace-M are both still live;
- 2001 consumes both root families;
- 2002 still references workspace-M/第一个月;
- 1004 has a bounded six-file candidate subtree, but `file-index.jsonl` ownership/consumer semantics remain unresolved;
- 3002 taxonomy has no live semantic contradiction;
- monthly workspaces remain migration sources and cannot yet be archived.

Architecture refinement:

- root-level writes do not automatically block a Project-scoped migration;
- future cutover uses an explicit single-writer contract: legacy source stays authoritative until staged copy + verify + final checkpoint + registry/reference switch;
- a staged destination is not a competing truth source if it is non-authoritative/non-writable before cutover;
- OBSBOT legacy monthly workspaces must not be archived under PAOS Project 3002.

M3C-1004 remains blocked.

Next authorized task is M3B-REF read-only reference/writer/consumer inventory.

See `M3B-REFERENCE-INVENTORY-DECISION.md` and `PACKET-M3B-REF-REFERENCE-INVENTORY.md`.

## C-019 — M3B-REF accepted: first Project mutation authorized

M3B-REF handoff `bc310ed` is accepted.

Decision:

```text
M3C-1004 = YES
canonical root = C:\Users\remo\Desktop\OBSBOT-Projects\1004-文档整理
```

`file-index.jsonl` is frozen as a 1004-owned generated-rebuildable snapshot and stays with the coherent six-file Work package under `Works/1004-s003-scan/`. Its old absolute paths are historical data and are not rewritten.

No additional 24–72h wait is required: the source set has been stable since 2026-08-24. M3C uses T0 and pre-switch T1 exact hash/writer/consumer checkpoints, and no manual rerun of the 1004 scan is allowed during the bounded batch.

The governance switch is registry-last. Source is preserved for rollback. No other Project root/reference is changed.

See `M3B-REF-DECISION.md` and `PACKET-M3C-1004-FIRST-PROJECT-MIGRATION.md`.

## C-020 — M3C-1004 staged PASS; cutover blocked on formal mutation contract

M3C-1004 handoff `bc7608c097b979e6a6ed5725130db70053f854b0` is accepted as a correct STOP.

Accepted state:

- destination Project root exists with the approved skeleton;
- six staged files hash/size match legacy source;
- source remains unchanged;
- T1 source/staged recheck PASS;
- Project 1004 remains revision 7 with old `root_path` and old Artifact pointers;
- no registry/reference cutover occurred.

Cutover blocker:

The deployed/current manual Project mutation contract can change `root_path` but cannot atomically relocate existing Artifact paths. Root-only mutation would create split Project truth.

Required system capability:

```text
project.root.relocate
Human-only
exact base revision
one operation_id
one Project revision
root_path + explicit existing Artifact path updates
one Ledger event + operation receipt
rollback before-state
```

The staged filesystem copy is retained. Do not recopy unless T1 later detects source/staged drift.

M3C-1004 remains BLOCKED until the relocation contract is exact-head tested, merged, deployed, and its running build is verified.

---

# 2. Status vocabulary

```text
APPROVED        may execute when dependencies are satisfied
READ-ONLY       evidence task; no canonical mutation
BLOCKED         requires listed dependency/decision
REVIEW          execution complete, waiting reviewer
DONE            accepted
DEFERRED        intentionally outside current Stage-1 critical path
```

Mutation classes keep the M0 vocabulary: `read-only`, `create`, `edit`, `move`, `archive`, `merge`, `generated-delete-candidate`, `retire-reference`.

---

# 3. P0 — Planning / source stabilization

## P0-001 — Merge canonical Stage-1 planning

Status: DONE — #78 merged as `main@9e1c69fe7aa299b379538031ec9c6568e228486a`

Owner: zrx/web lead  
Reviewer: s029 (planning consistency), s027 (local executability)

Action:

- keep V1.1 planning in the non-numbered `docs/planning/v11-baseline-reconstruction/` folder;
- include this Master Migration TODO;
- update #78 body/references;
- perform a narrow doc consistency review;
- merge #78 before local path-changing batches begin.

Done When:

- no new 38/39/40 collision from #78;
- planning paths are stable;
- local Agents can fetch one mainline planning baseline.

Rollback: Git revert.

## P0-002 — Create clean PAOS migration runner

Status: DONE — Packet B1A PASS

Owner: s027  
Reviewer: s029

Mutation: create only.

Action:

- leave `C:\Users\remo\Desktop\agent学习计划\personal-agent-os` dirty worktree untouched;
- prune only stale Git worktree metadata when reviewer confirms the path is genuinely prunable; do not remove a real worktree directory as part of this task;
- create a new clean worktree/clone dedicated to Stage-1 execution, pinned to the **post-#78 approved main SHA**;
- record exact path + HEAD + clean `git status`;
- do not copy `.paos`, Workstations, private Project artifacts, or dirty/untracked canonical candidates into the runner;
- runner code is the executable baseline; local facts remain in the primary Project root and are addressed explicitly;
- commands that mutate the real installation config/project root must use explicit target paths;
- for Library roots, always pass `--config "C:\Users\remo\Desktop\agent学习计划\personal-agent-os\private-data\environment\library-roots.json"`; never rely on the runner default.

Done When:

- runner `git status` clean;
- exact HEAD equals the approved post-#78 main;
- runner can run `python scripts/verify.py` or at least library/workstation CLI imports without touching the dirty Project root;
- reviewer confirms the runner's own default `private-data/environment/library-roots.json` has not become a second registry;
- no user changes lost.

## P0-003 — Resolve transitional Agent roster

Status: DONE (Packet A read-only)

Owner: Coordinator s010  
Reviewer: s029

Action:

- read live PAOS responsibility/Work facts for s028 and s030;
- classify each as `long-lived role`, `transitional until Work close`, or `historical`; 
- do not change Session/Work status;
- return current responsibility, why it must/must not survive baseline cutover, and migration timing.

Result:

- s028 = transitional/in-flight; excluded from baseline long-lived M4 roster for now;
- s030 = current-scope inactive/standby candidate; excluded from baseline long-lived M4 roster unless reactivated;
- no Session/Work state was changed.

Done When: M4 scope contains no unnamed active Agent.

## P0-004 — Project disposition table

Status: DONE (Packet A read-only)

Owner: s027  
Reviewer: s029  
Coordinator: s010

Action:

Produce one row for all 10 registry Projects:

```text
project_id
registry_status
recent Work/Session evidence
current root
root exists on Windows
root exists from WSL / relevant Runtime
shares root with which Project IDs
proposed disposition
proposed dedicated root if needed
do-not-disturb
```

Specific required callouts:

- 1001/1002/1004/2001 currently share `OBSBOT-first-month-workspace`; 
- 1003 root visibility must be checked on Windows, not inferred from WSL missing alone;
- 1005/2002/2003 have empty root_path and are `UNHOUSED` until resolved;
- 3001 and 3002 have unique roots but still need active-use confirmation.

Packet A result:

```text
1001  SHARED-ROOT
1002  SHARED-ROOT
1003  UNHOUSED / root verification pending
1004  SHARED-ROOT
1005  UNHOUSED
2001  SHARED-ROOT / DO NOT DISTURB
2002  UNHOUSED
2003  UNHOUSED
3001  MIGRATE-ACTIVE candidate
3002  MIGRATE-ACTIVE / DO NOT DISTURB
```

No Project was safely classified dormant/archive from current facts.

Done When: every Project has one proposed disposition; no filesystem move yet.

## P0-005 — Dirty/untracked canonical-claim inventory

Status: DONE — Packet B0 read-only; local claims dispositioned by C-009

Owner: s027  
Reviewer: s029  
Coordinator: s010 for current-Work meaning

Action:

- inventory the primary PAOS worktree's modified/untracked paths without cleaning it;
- scope at minimum: `docs/`, `docs/workflows/`, `docs/planning/`, `.paos/`, `Workstations/`, `private-data/`, plus any modified/untracked script/config path referenced by a current real Run;
- classify each relevant path as one of:

```text
CURRENT-LOCAL-FACT        real current fact/evidence that migration must preserve
CANDIDATE-CANONICAL      locally created content that claims future canonical meaning
IN-FLIGHT-WORK           belongs to an unfinished Work/PR; do not absorb into baseline
GENERATED-REBUILDABLE    derived/cache/test output
HISTORICAL-EVIDENCE      keep, but not current
UNKNOWN-DECISION         cannot safely classify
```

Required explicit callouts include:

- local `docs/workflows/README.md` and any workflow index not present on approved main;
- `docs/planning/workflow-problem-pack-20260914/` or equivalent local-only planning packs;
- local `.paos/` and `Workstations/` facts that current Agents actually use;
- any local script/config modification that a migration command would accidentally bypass.

For every `CANDIDATE-CANONICAL` or `UNKNOWN-DECISION`, propose whether it should be promoted, remain Project-local, be archived later, or block a batch.

Do **not** commit, delete, stash, reset, or copy these files into the clean runner during this task.

Done When:

- reviewer agrees every dirty/untracked path with possible canonical meaning has a disposition;
- the clean runner can be used as executable code without pretending local-only facts do not exist;
- unresolved `UNKNOWN-DECISION` entries explicitly block only the affected later batch.

## P0-006 — Activation-owner transition map

Status: DONE — Packet B0 read-only; owner frozen by C-010. **Any activation-owner switch remains blocked until M4.**

Owner: s031 for Codex/native paths; s027 for OpenCode/CAT paths  
Reviewer: s029  
Coordinator: s010

Action:

For each long-lived Agent currently used during migration, record:

```text
agent
current Runtime
current assignment/communication path
current activation owner
legacy wake-capable adapter/bridge/hook present?
PAOS Wake binding present?
can legacy path independently create a new continuation?
allowed migration communication path
owner-switch blocked until which M4 task
```

No hook, binding, Room owner, Participant, or adapter mutation occurs here.

Done When:

- there is one declared current activation owner per target/source path;
- Coordinator knows which current communication path is safe for Packet B assignments;
- any ambiguous dual-wake path is marked `DO NOT SWITCH OWNER` and deferred to M4-R02/R04.

---

## C-021 — Project 3002 clean baseline

Human decision supersedes the compatibility-first 3002 ordering.

Project 3002 will build a new Project Work World before fresh Agent Workstations are provisioned.

Target root:

```text
C:\Users\remo\Desktop\agent学习计划\PAOS-Projects\3002-Personal-Agent-OS
```

Target model:

```text
Project root
├─ INDEX / Inbox / Materials / Works / Decisions / Workstations / Archive
└─ Source/personal-agent-os   fresh accepted-main checkout

PAOS-Libraries               external shared Workflow/Skill roots
old personal-agent-os root   preserved legacy evidence, not daily authority
```

Compatibility with old daily ENTRY/TODO/Runtime paths is not required. Durable PAOS governance history is preserved.

M3F-3002 now precedes M4. After Project/runtime cutover, M4 creates fresh Workstations instead of migrating legacy homes.

See `M3F-3002-CLEAN-BASELINE-DECISION.md`.

---

# 4. M1 — Workflow Library Reconstruction

## M1-001 — Establish canonical Workflow/Skill roots + registry

Status: DONE — Packet B1B + #80 cross-runtime path gate PASS

Owner: s027  
Reviewer: s029

Mutation: create + explicit config edit.

Action:

1. create shared parent `C:\Users\remo\Desktop\agent学习计划\PAOS-Libraries`;
2. **before creating Workflow/Skill content**, initialize the parent as a standalone local Git repository on branch `main`, add only a small root README describing purpose/ownership, and create the first baseline commit;
3. initialize roots:
   - `...\PAOS-Libraries\workflow`
   - `...\PAOS-Libraries\skill`;
4. commit the empty initialized Library skeleton as a second baseline commit before importing legacy content;
5. write the real installation registry at:
   - `C:\Users\remo\Desktop\agent学习计划\personal-agent-os\private-data\environment\library-roots.json`
   using the clean runner with the **mandatory explicit**:
   - `--config "C:\Users\remo\Desktop\agent学习计划\personal-agent-os\private-data\environment\library-roots.json"`;
6. verify both roots are distinct and initialized;
7. run `library roots show --config <same-primary-registry-path>`;
8. verify the clean runner's own default registry path remains absent/unregistered.

Do not import old Workflow/Skill content yet.

The local Git repository is the Stage-1 rollback/version mechanism for shared Library content. No remote is required in this batch.

Done When:

- registry exists and validates;
- Workflow root has README/Guides/Workflows/Templates/.paos;
- Skill root has README/.paos/usage-events;
- root show output matches exact paths;
- PAOS Project revision/Session/Request/Ledger unchanged.

Rollback:

- restore/delete only the newly created primary registry file if this batch must be rolled back;
- reset/remove only the newly created `PAOS-Libraries` local Git repository when it still contains no promoted user content;
- preserve the baseline commits/report as migration evidence before destructive rollback;
- never touch old repo docs during this rollback.

## M1-002 — Build Workflow/Skill boundary source mapping

Status: DONE — C1R read-only mapping accepted

Owner: s027  
Reviewer: s029

Mutation: read-only map first.

Map existing de-facto sources:

- `docs/AGENT-EMPLOYEE-GUIDE.md`
- `docs/COORDINATOR-OPERATING-GUIDE.md`
- `docs/WORKFLOW-PHILOSOPHY.md`
- `docs/USER-AND-ARCHITECTURE-GUIDE.md`
- `docs/runbooks/PAOS-DEVELOPMENT-WORKFLOW.md`
- `docs/workflows/*`
- any other referenced current workflow/guide/skill-like source discovered by reference scan.

For each semantic unit, classify to exactly one primary destination:

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

The mapping must answer:

- is this about universal Work management, or about how to execute a task?
- if execution-specific, what Skill candidate should own it?
- if universal, does it belong in Agent cycle, Coordinator cycle, or a small support Guide?
- is the content merely PAOS repo maintenance or Project-local context?
- what real Run proves the method is useful?

For tracked files that diverge between approved main and dirty primary, compare both versions side-by-side. Do not choose either by recency alone.

Produce a **Kernel / Skill Boundary Matrix**, not the old 12/6/6 Workflow coverage matrix.

No source moves, Library content authoring, Skill authoring, repo-doc rewrite, Workstation edit, Project cleanup, Runtime owner change or registry rewrite occurs in this task.

## M1-003 — Author Workflow Kernel baseline

Status: DONE — C2A/C2B PASS; two Workflows active

Owner: s027 first draft  
Reviewer: s029  
Coordinator/content escalation: s010 / zrx

Target baseline is deliberately small:

```text
wf-agent-work-cycle
wf-coordinator-governance-cycle
```

Author only the universal Work-management protocol proven by current Runs:

- responsibility / authority;
- TODO proactivity;
- truth navigation;
- direct collaboration / escalation;
- evidence / review / acceptance boundary;
- closeout / handoff / standby;
- Coordinator thin-context governance.

Hard constraints:

- no task-class execution recipe;
- no software-development / PRD / research / document-revision orchestration;
- no Runtime-specific identity;
- no Project-specific facts;
- no copied Skill implementation;
- no internal chain-of-thought/process diary.

## M1-004 — Workflow support files

Status: DONE BY DECISION — no mandatory support files in baseline

C1R showed the candidate Guides/Templates mostly duplicate the two core cycles. `Guides/` and `Templates/` may remain empty. Add support files only after a real Run proves repeated ambiguity that cannot be cleanly resolved inline.

## M1-005 — Kernel cold-start + Skill-boundary test

Status: DONE — C2B six-task semantic scenario PASS

Owner: s027  
Reviewer: s029

Action:

- rebuild Workflow Catalog;
- verify duplicate IDs = 0;
- fresh Agent can run the universal Agent Work Cycle without selecting from a menu of task-class Workflows;
- Coordinator can identify and use its governance cycle;
- give 4–6 task scenarios (software, research, PRD, writing, review, migration) and verify the Agent keeps the same Workflow Kernel while choosing different Skill candidates;
- any task-class method that leaks back into Workflow is a P1 for M1.

## M1-006 — Retire `docs/workflows` as canonical claim

Status: BLOCKED by M1-005; mutation happens late M1 / Stage-2 prep

Owner: s027  
Reviewer: s029

Policy:

- do not case-rename `docs/workflows`;
- do not move referenced files until reference scan passes;
- change repo documentation so `docs/workflows` is repo-specific/historical guidance, not the shared canonical Library;
- preserve old links or explicit redirect/reference notes as needed;
- daily Agent selection must use registered Workflow Catalog by cutover.

---

# 5. M2 — Skill Library Reconstruction

## M2-001 — Skill candidate discovery

Status: PARTIAL DONE — C1R candidate matrix + C2 first active Skills; C3A completes known-source inventory

Owner: s027  
Reviewer: s029

Mutation: read-only.

Discover actual reusable Skill candidates only from known Runtime/plugin/Project references and user-created assets. Do not scan the whole disk indiscriminately.

At minimum look for:

- Clean Writing / clean-language Skill lineage;
- any current Codex/OpenCode skill directories referenced by Runtime configuration;
- Project-local skills that may actually be reusable;
- duplicates or giant skills mixing orchestration + capability.

Output mapping:

```text
source
candidate stable id
reusable capability
project/runtime leakage
duplicate/overlap
promote / split / keep project-local / retire-candidate
```

## M2-002 — Normalize canonical Skills

Status: DONE FOR STAGE-1 BASELINE — 3 active Skills; no further promotion required before M3

Owner: s027 / skill-specific owner  
Reviewer: s029

Action:

- create only reviewed Skill directories `<skill-id>/SKILL.md`;
- strip Project/Runtime-specific context;
- keep stable IDs;
- preserve external supporting files only when the Skill contract needs them;
- do not turn Workflow orchestration into a Skill.

## M2-003 — Skill Catalog / usage preservation

Status: DONE FOR STAGE-1 BASELINE — Catalog active with 3 Skills; one real review usage event projects uses=1 / avg=0.5

Owner: s027  
Reviewer: s029

Done When:

- catalog rebuilds;
- duplicate skill ID = 0;
- usage events remain append-only;
- baseline Workflows reference only existing Skill IDs or explicitly say `none`/optional.

## M2-R4 — Skill Library arrangement review

Status: READY / READ-ONLY NEXT

Owner: s027  
Reviewer: s029  
Coordinator: s010

Use the new Project-3002 Workstation as a real post-cutover Work.

Inputs:

- current 3-Skill canonical baseline;
- 15 local curated Skill sources;
- external reference pool as comparison material only.

Required output:

- one-line contract for every curated candidate:
  `trigger / input / output / not_for / nearest overlap`;
- clean-writing internal-refactor specification;
- product-definition family semantic overlap matrix;
- promotion tiers;
- lightweight external reference-pool indexing proposal.

No Skill copy/import/delete/rename/Catalog mutation in M2-R4.

Current architectural defaults:

- keep `clean-writing` as one stable top-level Skill; narrow its trigger and move details into references;
- keep adapters separate from semantic Skills;
- treat `product-feature-mining` as a merge/module candidate until semantic diff proves a separate recurring trigger;
- do not promote `dispatching-parallel-agents` until its orchestration behavior is reconciled with Coordinator/PAOS authority.

## M2-R5 — Bounded Skill refactor / promotion

Status: BLOCKED by M2-R4 + Human/mainline selection

Default candidate order:

```text
R5a  clean-writing internal refactor
R5b  technical-research + write-prd
R5c  format/tool adapters
R5d  product-definition family after overlap decision
```

Each batch must use source freeze -> normalize -> real/scenario test -> independent review -> Catalog rebuild -> usage observation.

The external ~1,201-Skill pool never enters the canonical Catalog directly.

---

# 6. M3 — Project Vault Reconstruction

## M3-000 — Freeze Project dispositions

Status: DONE — C-017 / M3A scope freeze

Owner: zrx/Coordinator decision  
Evidence owners: s027/s029

Action:

- accept one disposition per registry Project;
- identify actual Stage-1 migration set;
- do not force a full Vault rebuild for dormant Projects;
- every non-migrated Project must still have an explicit reason/status so it is not ambiguous.

## M3-001 — Dedicated root map for shared/unhoused Projects

Status: APPROVED AS M3B READ-ONLY FOR SHARED OBSBOT CLUSTER; unhoused Projects deferred

Owner: s027  
Reviewer: s029  
Human decision required where Project meaning is unclear.

Hard rule:

- 1001/1002/1004/2001 cannot remain four Project IDs with one identical `root_path` at Stage-2 cutover.

Produce dry-run maps from current shared workspace subtrees/materials to proposed dedicated Project roots. Do not create/move until reviewer accepts mapping.

For 1005/2002/2003, either assign an existing real root, create a new dedicated root with a justified content source, or classify dormant/unhoused. Never fabricate an empty 'active' Vault merely to satisfy schema.

## M3-002 — Project 3002 cleanup map

Status: SUPERSEDED — clean-baseline reconstruction authorized before M4

Owner: s027  
Reviewer: s029

Map:

- standard Vault dirs (currently near-empty);
- repo source/docs that must remain repo source rather than be moved into Vault dirs;
- `.paos/agents` and `.paos/workstations` evidence;
- fixed `Workstations/` homes;
- formal current artifacts/results that should live in `Works/`;
- historical Agent outputs/TODOs that should live in `Archive/Agent-History/`;
- current Decisions that deserve canonical Decision files;
- references that must survive.

Do **not** attempt to force all source-code files into `Materials/` or `Works/`; Project Vault layout is additive, not an exclusive repo taxonomy.

## M3-003... — Bounded Project mutation batches

Status: M3C-1004 DONE; M3E-2001 DONE / CUTOVER-PASS; M3F-3002 DONE / CUTOVER-PASS; M4 POST-CUTOVER CONVERGENCE NEXT

Execution order is now governed by `M3-PROJECT-MIGRATION-MASTER-TODO.md`.

Preferred sequence:

```text
M3B  read-only root-family + 1004 source manifest + cluster root plan — DONE
M3C  1004 first bounded Project migration — DONE
M3E  2001 LRC101 independent Vault reconstruction — DONE / CUTOVER-PASS
M3F  3002 clean Project/runtime baseline — DONE / CUTOVER-PASS
M4    3002 post-cutover convergence + fresh-Workstation real use — NEXT
M3D  1001 / 1002 thin routine roots — later
```

The first mutation sample is 1004, not 3002 Agent history.

Each mutation batch must return:

- before tree/map;
- exact approved actions;
- actual actions;
- source/destination hashes where applicable;
- canonical truth after action;
- reference verification;
- registry before/after if touched;
- rollback point;
- open P2.

Default action for human evidence is retain/copy/move/archive, not delete.

## M3-090 — Downloads/test-clone cleanup

Status: DEFERRED / generated-delete-candidate

Owner: s027  
Reviewer: s029  
Human confirmation required before deletion.

Not a Stage-1 critical-path task. First prove no active reference. Cleanup may happen after canonical roots/workstations are stable.

---

# 7. M4 — Agent Workstation / Role Migration

## M4-000 — Freeze active employee roster

Status: DONE — baseline roster frozen after P0-003

Owner: Coordinator  
Reviewer: s029  
Final architecture: zrx

Frozen Stage-1 long-lived roster:

```text
s010  Project Lead / Coordinator
s027  primary implementer / integration
s029  independent reviewer / QA
s031  Runtime Reliability Specialist
```

s028 remains transitional and is excluded from the baseline long-lived roster. s030 remains inactive/standby and is excluded unless explicitly reactivated.

## M4-010 — Coordinator s010 fixed Workstation

Status: SUPERSEDED — replaced by fresh Workstation provision after M3F-3002

Owner: s010 (self-migration)  
Reviewer: s029

Create/reconcile fixed ENTRY/TODO/mailbox without overwriting current truth. Role: Project Lead / Coordinator. Historical TODO remains preserved outside the canonical current TODO after migration.

## M4-027 — s027 fixed Workstation migration

Status: SUPERSEDED — replaced by fresh Workstation provision after M3F-3002

Owner: s027 (self-migration)  
Reviewer: s029

Special handling:

- handwritten `.paos/agents/3002-s027/ENTRY.md` must be snapshotted and mapped; it will block automatic workstation init and must not be deleted;
- archive the legacy ENTRY only after stable facts are transferred and reviewer approves;
- create `Workstations/3002-s027/{ENTRY.md,TODO.md,mailbox/}` as the sole daily entry;
- reconcile 15 old TODO files: identify current facts, migrate one current TODO, archive historical TODOs to Project Archive;
- update role/default workflows after M1 Catalog exists.

Cold-start acceptance required before legacy entry becomes historical-only.

## M4-029 — s029 fixed Workstation migration

Status: SUPERSEDED — replaced by fresh Workstation provision after M3F-3002

Owner: s029 (self-migration)  
Reviewer: s027 or Coordinator for filesystem evidence; s029 cannot be its only reviewer

Action:

- preserve `.paos/workstations/.../cycle-*` as cycle evidence;
- create stable fixed Workstation;
- role = Independent Reviewer / QA;
- current TODO must reflect actual review responsibility, not old Cycle material;
- cold-start from fixed ENTRY must locate Catalog and live context.

## M4-031 — s031 fixed Workstation normalization

Status: SUPERSEDED — replaced by fresh Workstation provision after M3F-3002

Owner: s031 (self-migration)  
Reviewer: s029

Action:

- keep existing fixed home;
- correct stable role from reviewer-like wording to Runtime Reliability Specialist;
- add canonical Workflow/Skill roots/navigation;
- remove current Runtime/native Thread details from stable identity if present;
- preserve current operational facts in TODO/live context, not ENTRY;
- formal outputs are mapped to Project Works/Archive over time rather than expanding Workstation contract.

## M4-P01 — Fresh Project Workstations

Status: DONE — creation + onboarding readback PASS for s010/s027/s029/s031

Observed:

- fresh homes exist for s010/s027/s029/s031 under the new Project root;
- each has ENTRY.md / TODO.md / mailbox/;
- old Workstations and Cycle evidence were not copied;
- s031 fresh-Workstation readback PASS;
- s010/s027/s029 new-Workstation onboarding readback PASS; s027 required a fresh OpenCode Runtime because the old native session restored obsolete context.

## M4-P02 — Real post-cutover Work + cold-start matrix

Status: READY / FINAL REAL-WORK GATE

Create one real closeout Work:

```text
V1.1 Stage-1 Final Acceptance and Legacy Retirement
```

Use this Work to drive the final fresh Sessions for s010/s027/s031. s029 remains independent and enters through the final review path.

Do not create a separate Skill-arrangement Work merely to satisfy cold-start acceptance. Do not hand-edit TODOs to make them look current.

Done when all four Agents can operate from the new Project Work World without old daily-entry files and the final independent review passes.

## M4-P03 — Legacy dependency / no-new-write observation

Status: BLOCKED only by M4-P02 real closeout Work

Inspect actual post-cutover work for current writes or navigation back to the old Project root.

Classify remaining old-root dependencies as:

```text
HISTORICAL-ONLY
EXTERNAL/RUNTIME-EVIDENCE
TEMPORARY-COMPATIBILITY
CURRENT-BLOCKER
```

Target: CURRENT-BLOCKER = 0.

## M4-P04 — Legacy knowledge consolidation

Status: READY inside final closeout Work

First known target: `docs/WORKFLOW-PHILOSOPHY.md`.

Extract only still-unique durable principles into the correct current authority. Do not copy the legacy file wholesale into the new Source.

## M4-P05 — Legacy root retirement

Status: FINAL CLOSEOUT STEP after M4-P03 + M4-P04

After no-new-write and knowledge closure:

- freeze the old root as historical/read-only;
- preserve rollback/archive evidence;
- move/rename into explicit legacy archive if useful;
- do not delete in the same batch.

See `M4-M5-POST-CUTOVER-CONVERGENCE-PLAN.md`.

## M4-R01 — Clean co-agent Runtime runner

Status: BLOCKED until Runtime batch; not required for M1/M2/M3

Owner: s031  
Reviewer: s029

Create a clean co-agent runner pinned to approved `master` (`f8aa18e...` at M0 time or later explicit approved head). Preserve dirty `co-agent-2` worktree untouched.

## M4-R02 — Codex Stop/hook chain map + cutover proposal

Status: READ-ONLY after M4-R01

Owner: s031  
Reviewer: s029

Map:

- `.codex/hooks.json` entries;
- old `personal-agent-os/tools/collab-run/codex_stop_adapter.ps1`;
- `cat_stop_router.py` wrapper;
- canonical co-agent router;
- current binding pointer;
- multiple Codex executables.

Propose one continuation chain and exact rollback. Do not edit hooks yet.

## M4-R03 — Runtime restart card

Status: BLOCKED by M4-R01/R02

Owner: s031  
Reviewer: s029

Card must define read-only startup sequence:

```text
library roots show
workstation show
exact PAOS/co-agent source SHA
Wake binding/status/probe
Codex executable
native Thread locator
Desktop pipe / app-server evidence
STOP/recovery evidence
```

## M4-R04 — Fresh Codex Runtime acceptance

Status: BLOCKED by M4-R03 + reviewed hook proposal

Owner: s031  
Reviewer: s029 / Coordinator

Use a fresh disposable Thread. Prove stable Agent can continue from fixed Workstation with explicit binding and exactly one activation. Hook mutation/cutover is accepted only after this passes and rollback is demonstrated.

## M4-CAT — CAT membership policy check

Status: DEFERRED / on-demand

No blanket creation of `p-3002-s031`. Add Room participant only when a real CAT collaboration needs s031. Workstation Mail is the durable default assignment path.

---

### Packet M4-START — ACTIVE / POST-CUTOVER CONVERGENCE

Project 3002 is canonical at the new root and fresh fixed homes already exist for s010/s027/s029/s031.

Current work is no longer Workstation creation. It is post-cutover convergence:

```text
real post-cutover Work
-> fresh-session cold starts
-> no-new-write / legacy dependency observation
-> legacy knowledge consolidation
-> legacy-root retirement
-> M5 acceptance
```

s031 has one fresh-Workstation readback PASS. s010/s027/s029 onboarding mail is delivered; their first real fresh Sessions remain acceptance evidence.

Do not hand-edit new TODOs merely to hide historical Work. New Work/Session assignment must establish current responsibility naturally.

See `M4-M5-POST-CUTOVER-CONVERGENCE-PLAN.md`.

---

# 8. M5 — Integration / Baseline Acceptance

## M5-001 — Catalog / root acceptance

Status: READY ON CURRENT 3-SKILL BASELINE; rerun after any accepted Skill promotion

- Workflow Catalog rebuild;
- Skill Catalog rebuild;
- roots registry valid;
- duplicate IDs = 0;
- all baseline Workflow Skill references resolve.

## M5-002 — Project truth acceptance

Status: BLOCKED by M4-P03/M4-P05 legacy-world exit

- every registry Project has explicit disposition;
- every MIGRATE-ACTIVE Project has dedicated root;
- current canonical output/result has one discoverable location;
- old versions/historical files are clearly archive/history;
- no Project duplicates shared Workflow/Skill content.

## M5-003 — Workstation acceptance

Status: PARTIAL PASS — 4/4 onboarding readback PASS; real closeout Work pending

- active long-lived Agents have exactly one daily stable ENTRY;
- current TODO is unique/readable;
- mailbox ready;
- Cycle evidence remains evidence, not entry;
- legacy edited ENTRY/TODO evidence preserved;
- no Runtime identity frozen into stable role.

## M5-004 — Fresh-Runtime cold-start matrix

Status: FINAL REAL-WORK GATE

Test at least:

- s027 implementation role;
- s029 independent reviewer role;
- s031 Runtime reliability role;
- Coordinator s010.

Provide only fixed ENTRY, current TODO, Catalog access, and live context. They must identify role/current responsibility/material location/Workflow/collaboration/escalation/output/closeout without Coordinator re-explaining the Project.

## M5-005 — Legacy daily-path scan

Status: READY inside final closeout Work after fresh-session evidence

Reference scan must show which old paths are still live. Any remaining live legacy path either gets an explicit temporary compatibility reason or blocks Stage-2 cutover.

## M5-006 — V1.1 Stage-1 baseline close

Status: BLOCKED only by final closeout Work + independent review

Final output:

```text
V11-STAGE1-PASS
or
V11-STAGE1-BLOCKED
```

PASS means the migration is closed. Later Workflow, Skill, Rooter and Runtime improvements are ordinary Project-3002 product work, not unfinished migration.

---

# 9. Hard dependencies vs preferred ordering

## Hard dependencies

```text
P0-001 -> P0-005 [DONE]
P0-005 -> P0-002 [DONE gate]
P0-002 reviewer PASS -> M1-001
P0-006 -> any activation-owner switch / Runtime hook cutover [map DONE; switch still blocked]
M1-001 -> M1/M2 content + M4 root-aware workstation work
P0-004 -> M3-000
M3-000 -> shared/unhoused Project path changes
M4-000 -> active employee workstation mutations
dry-run map + reviewer -> every move/archive/retire-reference batch
M1-M4 accepted -> M5
M5 accepted -> V1.1 Stage-1 migration closed
```

## Preferred ordering

```text
1. merge planning (#78)
2. Packet B0:
   - dirty/untracked canonical-claim inventory
   - activation-owner transition map
3. create clean runner
4. initialize versioned shared Library roots + explicit primary registry
5. in parallel:
   - Workflow source mapping
   - Skill discovery
   - Project disposition/root mapping
   - employee roster disposition
6. author Workflow/Skill baseline
7. bounded Project cleanup
8. self-migrate Workstations with per-Agent authority cutover
9. Runtime-specific cleanup/activation-owner cutover
10. M5 integration
```

M3 mapping may run before M1 content is finished, but M4 final ENTRY/default-workflow edits wait for canonical roots/Catalog.

---

# 10. First executable packets

### Packet A — DONE

Packet A produced the planning reviews and Project/roster readback that led to the transition rules above.

### Packet B0 — DONE

Packet B0 completed P0-005/P0-006 and confirmed transition-entry authority. Its P1s are dispositioned by C-009/C-010/C-011.

### Packet B1A — clean execution source

Authorized:

- P0-002 only.
- s027 creates a clean PAOS migration runner pinned exactly to the approved main that contains this authorization.
- s029 verifies clean status, exact HEAD, no copied `.paos`/Workstations/private-data, and that the runner's default registry is absent/unregistered.
- no `PAOS-Libraries` root or primary registry mutation until s029 returns B1A PASS.

If B1A fails, stop before B1B.

### Packet B1B — versioned empty Library roots + primary registry

Authorized **only after B1A reviewer PASS**:

- M1-001 only.
- s027 creates `PAOS-Libraries`, initializes standalone local Git history first, then initializes empty Workflow/Skill roots.
- s027 writes the primary installation registry only with mandatory explicit `--config`.
- s029 verifies:
  - parent Git history exists before promoted content;
  - root skeletons match A3a contracts;
  - `library roots show --config <primary>` returns the exact roots;
  - the clean runner's own default registry remains absent/unregistered;
  - no Workflow/Skill legacy content has been imported;
  - PAOS governance revision/Session/Request/Ledger are unchanged.

### Packet B1 — DONE

Packet B1A/B1B passed. #80 closed the cross-runtime path P1 and the primary installation registry now stores canonical `C:/...` locators validated from both WSL and Windows-native runtimes.

Residual non-blocking hardening:
- explicit WSL `/mnt/<drive>/...` input can still be stored as POSIX syntax if a caller deliberately supplies it;
- repeated `roots set` updates `registered_at`, so registry bytes are not replay-idempotent.

Track these as later hardening; do not reopen B1.

### Packet C1R — two-layer Workflow / Skill source mapping

Supersedes the earlier C1 12/6/6 coverage framing.

Authorized task: **M1-002 only**.

Goals:
- map current Workflow/Guide/local method sources without moving them;
- classify each semantic unit as Workflow Kernel vs Skill candidate vs Project/Repo/Evidence;
- compare approved-main vs local-dirty divergent docs;
- connect real proven Runs to universal Work-management rules and reusable execution experience;
- produce one Kernel / Skill Boundary Matrix;
- expose conflicts/gaps before authoring.

Packet C1R has no authority to:
- create/edit canonical Workflow Kernel content;
- create/edit Skills;
- move/retire source docs;
- start Project cleanup or Workstation migration;
- change Runtime activation ownership/hooks/bindings/Rooms/Participants;
- rewrite Library roots or registry.

C1R evidence is accepted. Kernel/Skill freeze is recorded in C-013.

### Packet C2 — DONE

C2A→C2D completed and is accepted by C-014.

### Packet C3A — DONE

Known Skill source inventory is accepted by C-015.

### Packet C3B — DONE

C3B is accepted by C-016. Method baseline is closed for Stage 1.

### Packet M3A — DONE

M3A scope is accepted by C-017.

### Packet M3B — DONE

M3B reconciliation is accepted by C-018.

### Packet M3B-REF — DONE

M3B-REF is accepted by C-019.

### Packet M3C-1004 — DONE

Project 1004 completed the first bounded Project-first migration. The deployed relocation contract atomically switched `root_path` plus six Artifact pointers; old source remains preserved migration evidence.

### Packet M3E-2001-A — DONE / NEED-CONTRACT-EXTENSION

Human priority has moved the active LRC101 Project ahead of the thin 1001/1002 roots.

Authorized now:

```text
map live 2001 truth across FM + workspace-M
-> classify current Project truth / shared references / Human-DND / runtime evidence
-> map writers, consumers, Artifacts, key_files and stable Workstation dependencies
-> propose exact independent Vault mapping at C:\Users\remo\Desktop\OBSBOT-Projects\2001-LRC101
-> independent review
-> readiness verdict
-> STOP
```

No 2001 filesystem/registry mutation is authorized until that evidence is accepted.

### Packet M3E-2001-B — DONE / BLOCKED-UNRESOLVED-ARTIFACT

M3E-A established that Project 2001 needs a stronger migration contract and exact ownership closure before staging.

M3E-B is read-only and must produce:

```text
exact key_files before/after proposal
+ every current Artifact classified MOVE / RETAIN / UNRESOLVED
+ selected Human/current content source manifest
+ runtime-evidence retain boundary
+ ownership decisions for relative/Downloads/3002/shared candidates
+ scoped future T1 writer condition
+ independent review
```

Mainline contract direction is `paos-project-root-relocate/v2`: preserve v1 safety, add exact key_files replacement and explicit Artifact retain-in-place exceptions.

M3E-B does not create the Vault and does not implement v2.

### Packet M3E-2001-C — DONE / RESIDUALS DELEGATED TO LOCAL IMPLEMENTATION

Human locality decision: the target LRC101 Vault is a working corpus, not a pointer-only index. M3E-C must classify Project-owned process/current documents for canonical move and useful related inputs for Project-local copy with provenance. Runtime/application state remains outside.

M3E-B showed that the apparent 106 unresolved rows include several deterministic retain classes. M3E-C narrows the real blocker to relative/no-root Artifacts whose resolution can drift when `root_path` changes.

Mainline defaults:
- WSL-form FM `.paos` paths -> runtime RETAIN;
- 3002 repo -> cross-Project RETAIN;
- absolute Downloads/Desktop packages -> external RETAIN unless proven canonical content;
- absolute temporary/missing locators -> historical/data-quality RETAIN rather than root-cutover blockers.

M3E-C must resolve the live relative/no-root set using Artifact provenance and return MOVE / RETAIN / REBIND / UNRESOLVED.

No Project governance cutover was authorized during M3E-C.

### Packet M3E-2001-D — DONE / STAGED VAULT + RELOCATION V2 READY

M3E-D changes the execution model:

- Web/mainline freezes architecture and cutover invariants;
- s010/s027/s029 own the detailed local filesystem implementation;
- the remaining relative-path cases are resolved inside implementation rather than through another Web-led archaeology packet;
- the staged LRC101 Vault may now be created;
- relocation v2 may be implemented and tested against disposable data;
- real Project-2001 governance mutation still waits for mainline merge/deploy/cutover approval.

Full-corpus SHA-256 verification is not required. Integrity checks are proportional to risk; strong deterministic comparison is reserved for cutover-critical or ambiguous files.

See `M3E-2001-D-LOCAL-VAULT-IMPLEMENTATION-PLAN.md`.

### Packet M3E-2001-E — DONE / CUTOVER-PASS

Project 2001 completed the Human-only atomic relocation.

Final live state:

```text
revision   1069
root       C:\Users\remo\Desktop\OBSBOT-Projects\2001-LRC101
key_files  10
Artifacts  377
```

Committed transaction:

```text
MOVE    85
REBIND  37
RETAIN  168
Ledger  +1 project.root.relocated
receipt paos-project-root-relocate-receipt/v2
```

Exact replay does not advance revision. Work/Sessions/Requests/Decisions were not rewritten. Old FM/workspace-M sources remain preserved and unarchived.

M3E is closed. Do not open another LRC101 migration packet unless new evidence shows a regression.

See `M3E-2001-E-PRECUTOVER-COMPLETION.md` and the cutover handoff.

See `M3E-2001-C-DECISION.md` and `PACKET-M3E-2001-C-ROOT-SENSITIVE-ARTIFACT-CLOSURE.md`.

See `M3E-2001-B-DECISION.md` and `PACKET-M3E-2001-B-CONTRACT-OWNERSHIP-CLOSURE.md`.

See `M3E-2001-ACCELERATION-DECISION.md` and `PACKET-M3E-2001-LRC101-VAULT-RECON.md`.

### Packet M5-FINAL — READY

Current onboarding evidence:

```text
s010 new Workstation readback PASS
s027 new Workstation readback PASS on fresh OpenCode Runtime
s029 new Workstation readback PASS
s031 fresh-Workstation readback PASS
Wake binding / online probes PASS
Project revision remained 656 during onboarding-only checks
```

This proves the new fixed homes are usable entry points but does not replace real-Work acceptance.

Create one real closeout Work:

```text
V1.1 Stage-1 Final Acceptance and Legacy Retirement
```

Use it to complete:

```text
fresh-session operation
-> no-new-write / legacy dependency check
-> WORKFLOW-PHILOSOPHY knowledge closure
-> old-root historical-only declaration
-> M5 acceptance
-> s029 independent final review
```

Skill promotion and Rooter implementation are outside this closeout critical path.

See `M5-V11-FINAL-CLOSEOUT-PACKET.md`.

### Packet M3F-3002-CLEAN — DONE / CUTOVER-PASS

Owners:

```text
s010  local Coordinator / current-truth reconciliation
s027  Project Vault + Source staging / relocation payload
s029  independent Project/current-truth review
s031  runtime + installation-state handoff
```

Authorized now:

```text
read live 3002 facts
→ create staged clean Project root
→ fresh clone accepted main into Source/personal-agent-os
→ selectively promote current Works/Decisions/Materials
→ prepare baseline Decision + INDEX
→ map root-sensitive Artifact pointers
→ rehearse installation-state handoff / new-source deployment
→ build and dry-run relocation-v2 payload
→ return readiness verdict
→ STOP before real Project-3002 root relocation
```

Do not bulk-copy old Runtime state or legacy Workstations for compatibility.

Production result:

- runtime/source handoff PASS on exact `3b86ac555a7526fcd5160fb7dd8404c98bad9733`;
- Project relocation `654 -> 655` PASS;
- canonical root is `C:\Users\remo\Desktop\agent学习计划\PAOS-Projects\3002-Personal-Agent-OS`;
- 86 Artifacts / 18 key files / 73 REBIND / 13 RETAIN;
- idempotent replay remains revision 655;
- s029 post-cutover review PASS;
- `3002-w057` closed only after acceptance, revision `655 -> 656`;
- fresh Workstations created for s010/s027/s029/s031;
- INDEX now marks the Project World canonical / V1.1.

M3F is closed. Follow-up work moves to M4 post-cutover convergence.

`WORKFLOW-PHILOSOPHY.md` remains legacy design-source evidence pending M4-P04 knowledge consolidation.

See:
- `M3F-3002-CLEAN-BASELINE-DECISION.md`;
- `M3F-3002-R1-ARTIFACT-LOCATOR-CLOSURE.md`;
- `M3F-3002-E-PRODUCTION-CUTOVER-DECISION.md`.

### Packet M3C-CONTRACT — Project root relocation implementation gate

Current web/main candidate adds a dedicated Human-only semantic action:

```text
POST /api/projects/{project_id}/relocate-root
schema = paos-project-root-relocate/v1
```

Required gate before merge/deploy:

- exact-head focused tests for contract/store/API/Authority Manifest;
- full Python/Node verifier;
- independent s029 code/contract review;
- real clean-runner API smoke against disposable Project data;
- no production 1004 mutation during this gate.

After PASS, zrx merges the contract, then local runtime is redeployed from the accepted main and build SHA verified.

Only after deployment does M3C-1004 resume at:

```text
T1 recheck retained staged copy
→ one project.root.relocate operation
→ real PAOS read-path verification
→ migration Decision file
→ independent post-cutover review
→ STOP
```

Do not recopy the six files unless T1 detects drift.

---

# 10.1 Deferred hardening from Packet B1

## R1-LIBROOTS-001 — WSL mount-form input canonicalization

Status: DEFERRED / non-blocking

Current behavior: an explicit `/mnt/<drive>/...` roots input may remain stored as POSIX syntax. The supported canonical installation path is now `C:/...` and all Stage-1 authorized root operations use that form.

Possible later hardening: detect WSL specifically and reverse-map `/mnt/<drive>/...` to `<DRIVE>:/...`, or reject runtime-mount syntax for a Windows-hosted installation.

Do not change #80 or reopen B1 for this.

## R1-LIBROOTS-002 — roots-set replay byte idempotency

Status: DEFERRED / non-blocking

`registered_at` changes on repeated successful `roots set`, so identical semantic registration is not byte-idempotent. This does not create a second truth source and is outside Stage-1 critical path.

---

## R2-SKILL-TELEMETRY-001 — usage-event / Catalog replayability contract

Status: DEFERRED / non-blocking

Current fact:

- usage event is installation-local/untracked;
- generated Catalog commit can include its projected stats;
- a clone of committed tree alone cannot replay those stats.

Do not solve by blindly Git-tracking all telemetry.

Before Stage-2 cutover or when usage telemetry becomes operationally important, decide whether usage events are durable shared Library facts or installation-local telemetry whose stats should not be committed as replayable shared truth.

---
# 11. Do-not-touch until specific TODO authorizes it

- dirty primary `personal-agent-os` Git state except the explicit new library-roots registry file authorized by M1-001;
- dirty `co-agent-2` worktree;
- existing `docs/workflows` files;
- old numbered planning history;
- `.paos/agents` / `.paos/workstations` evidence;
- s027 handwritten legacy ENTRY;
- s010/s027/s029/s031 current TODO before each self-migration task;
- Project registry root/status fields before M3 decision;
- Codex hooks/bindings/current.json;
- Downloads test clones / mojibake paths;
- any non-generated historical evidence;
- any Project content whose canonical meaning is disputed.

---

# 12. Reporting / closeout

Every executable batch must update the executing Agent's own `TODO.md` before handoff and return:

```text
Accepted TODO IDs
Exact baseline
Actual mutation
Evidence
Unexpected local friction
New TODO proposals
P1
P2
Rollback state
Current personal TODO
Next safe action
```

Coordinator maintains the Master TODO projection; local proposals do not silently become approved tasks.

## Stage-1 success condition

Stage 1 ends only when the system has one trustworthy baseline from which later flywheel friction can be interpreted as **new-system friction**, not incomplete migration.