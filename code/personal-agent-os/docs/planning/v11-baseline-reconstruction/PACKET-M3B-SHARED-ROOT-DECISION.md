# PAOS V1.1 Stage 1 — Packet M3B Shared-root Decision

Decision owner: zrx  
Prerequisite: M3A accepted  
Mutation class: read-only mapping/reporting only

## 0. Purpose

M3B resolves the last root/source facts that block the first real Project migration.

It does not move files.

Primary goal:

> turn the OBSBOT shared workspace from an ambiguous month-based/four-Project working world into an explicit **Project-first** parent/shared-material/dedicated-root plan, and freeze the exact 1004 first-mutation source set.

Human architecture decision:

- monthly workspaces are legacy phase containers;
- Project roots become the long-term canonical working homes;
- after successful Project cutover, `OBSBOT-workspace-M` and `OBSBOT-first-month-workspace` are archived rather than kept as writable working roots;
- monthly views may continue as generated reports/snapshots, not as canonical storage.

## 1. Canonical decisions already frozen

Do not reopen these unless new evidence directly contradicts them:

- Human clarification: `OBSBOT-workspace-M` contains the first-month lineage, but standalone `OBSBOT-first-month-workspace` later received additional Agent-written documents. Treat the pair as a diverged workspace family, not a simple old/new replacement chain.

- 1003 is `UNHOUSED-PENDING-HUMAN`; no automatic repair.
- 1005/2002/2003 are `UNHOUSED-DEFERRED`; no empty Vault creation.
- 3001 is `DORMANT-RETAIN`; no Stage-1 migration.
- 3002 repo root remains its Project root.
- top-level `Workstations/` = stable Agent homes.
- `.paos/workstations/` = Cycle evidence.
- `.paos/agents/` = legacy/transitional until M4.
- 3002 source/docs are not moved into Vault dirs.
- first Project mutation candidate is 1004, not 3002 Agent history;
- future canonical ownership axis is Project, not month;
- both legacy monthly workspaces are eventual archive sources after reconciliation/cutover, not future Project roots.

## 2. s027 — primary mapping

Update own TODO before execution.

### M3B-001 — OBSBOT root-family relationship

Compare only bounded known roots:

```text
C:\Users\remo\Desktop\OBSBOT-first-month-workspace
C:\Users\remo\Desktop\OBSBOT-workspace-M
```

Return evidence for:

- top-level/tree relationship;
- same-name file families;
- exact embedded/ancestor relationship for the first-month lineage;
- **FIRST-MONTH POST-FORK DELTA**: files newer/unique only in standalone `OBSBOT-first-month-workspace`;
- **WORKSPACE-M DELTA**: files/subtrees unique to `OBSBOT-workspace-M`;
- modification-time ranges where useful;
- registry references;
- Work/Session/Agent output references;
- whether either root is still written by live work.

Do not infer canonicality from newer mtime alone.

Build a three-set reconciliation table:

```text
COMMON BASELINE
FIRST-MONTH POST-FORK DELTA
WORKSPACE-M DELTA
```

Choose one recommendation:

```text
CREATE-NEUTRAL-PARENT
USE-FIRST-MONTH-AS-PARENT
USE-WORKSPACE-M-AS-PARENT
DECISION-REQUIRED
```

`CREATE-NEUTRAL-PARENT` is now the default recommendation. Selecting either existing root requires proof that it already contains the other branch's unique delta and is not still diverging.

If `CREATE-NEUTRAL-PARENT`, propose the parent path but do not create it. It must be a sibling/new canonical workspace, not nested under either legacy root.

### M3B-002 — 1004 exact ownership/source manifest

At minimum inspect:

```text
90-Agent-Ops/1004-s003-scan/
1004 registry-declared paths
1004 current/historical Work references
1004 Agent/Session outputs if they name source files
other 1004-specific artifacts in the shared workspace
```

Every candidate item gets:

```text
path
classification:
  PROJECT-SPECIFIC
  SHARED-REFERENCE
  RUNTIME-EVIDENCE
  HISTORICAL
  UNKNOWN
current consumer/reference
size/hash if file
proposed future destination
copy/move/reference/archive-later/no-action
rollback source
```

Do not include `90-Agent-Ops` as a whole merely because one 1004 subtree lives there.

### M3B-003 — exact shared-cluster root plan

For 1001/1002/1004/2001 propose:

```text
project_id
future dedicated root
Project-specific content classes
shared material references
Workstation location
registry-switch prerequisites
rollback path
```

Rules:

- shared material stays single-copy;
- Project root can be thin;
- root path must be stable and understandable to Windows-native and WSL tools;
- avoid symlink/junction dependence unless there is a proven reason;
- 2001 remains last mutation in this cluster;
- do not move 2001 `.paos`/Workstations in M3B;
- no future Project root may be named or structured primarily by month;
- monthly/phase summaries belong inside Project history/reporting or the eventual legacy archive, not as a writable parallel workspace.

Outputs:

```text
s027/V11-M3B-OBSBOT-ROOT-FAMILY-MAP.md
s027/V11-M3B-1004-SOURCE-MANIFEST.md
s027/V11-M3B-SHARED-CLUSTER-ROOT-PLAN.md
```

## 3. s029 — independent review + 3002 narrow check

Update own TODO first.

### Review M3B-001/002/003 independently

Challenge:

- whether the chosen parent is truly current/canonical;
- whether shared materials are accidentally duplicated;
- whether 1004-owned items are really owned by 1004;
- whether proposed registry switch would strand live references;
- whether target paths introduce a new competing root;
- whether any `archive-later` item is still current.

### M3B-004 — 3002 taxonomy contradiction check

Read-only, narrow.

Verify whether any current live consumer contradicts:

```text
Workstations/             stable Agent homes
.paos/workstations/       Cycle evidence
.paos/agents/             legacy/transitional
reviews/                  evidence/report collection, not lifecycle truth
Vault dirs                additive work-world, not repo-source replacement
```

If a contradiction exists, identify exact consumer/path and mark P1.

Do not perform another broad 3002 inventory.

Use `skill-independent-review` only if genuinely useful; log honest usage if used.

Outputs:

```text
s029/V11-M3B-SHARED-ROOT-INDEPENDENT-REVIEW.md
s029/V11-M3B-3002-BOUNDARY-CHECK.md
```

## 4. s010 — Coordinator reconciliation

Use `wf-coordinator-governance-cycle`.

Return:

```text
coordinator/V11-M3B-COORDINATOR-READBACK.md
coordinator/COORDINATOR-TODO-AFTER-M3B.md
```

Coordinator readback must contain:

### A. Root-family verdict

```text
canonical parent recommendation
common-baseline summary
first-month post-fork delta summary
workspace-M delta summary
whether either legacy root is still being written
evidence
remaining uncertainty
```

### B. 1004 migration-ready manifest verdict

```text
source-set complete?
live-reference blockers?
hash/rollback evidence ready?
```

### C. Exact four-Project root plan

| Project | Proposed dedicated root | Shared refs | Registry switch gate | DND |
|---|---|---|---|---|

### D. 3002 boundary check

PASS or exact contradiction.

### E. Legacy monthly workspace retirement plan

Coordinator must state:

```text
what remains current in each monthly workspace
what must be reconciled before archive
what live references still point there
what final no-new-writes checkpoint is required
proposed archive state/path after Project cutover
```

This is a plan only. M3B does not archive anything.

### F. First mutation recommendation

Coordinator may recommend M3C-1004 only if:

- parent decision is unambiguous;
- post-fork delta reconciliation is complete enough that 1004 source truth will not be lost;
- 1004 source manifest is complete;
- no P1 live reference blocker;
- target root has no existing conflicting user content;
- rollback is source-preserving;
- registry update can remain last.

If either legacy root is still receiving writes relevant to 1004, Coordinator must also propose a narrow execution-time source-freeze/checkpoint step for M3C rather than pretending the dry-run manifest will remain static.

## 5. Prohibited mutation

M3B does not authorize:

- creating a canonical parent or Projects/ directory;
- creating 1004 root;
- copying/moving/renaming/archiving any Project file;
- modifying registry `root_path` or status;
- changing Project/Work/Session lifecycle;
- moving `.paos` or Workstations;
- changing Runtime/CAT state;
- importing/editing Workflow/Skill.

Report writing and personal TODO updates are the only writes allowed outside normal append-only Skill usage logging.

## 6. Stop conditions

STOP affected work if:

- the two OBSBOT roots are both actively written and neither is clearly a parent/snapshot;
- 1004 source ownership overlaps 2001/other Project current truth;
- the proposed parent contains conflicting pre-existing `Projects/` content;
- a proposed move would break a live path reference;
- target root naming/path semantics are ambiguous;
- 3002 boundary check finds a live consumer using the opposite Workstation semantics.

## 7. Done When

M3B is complete when:

- root-family relationship has an evidence-backed recommendation;
- exact 1004 source manifest exists;
- exact dedicated-root proposal exists for all four shared-root Projects;
- s029 independently reviews root/source assumptions;
- 3002 taxonomy is confirmed or exact contradiction is surfaced;
- Coordinator recommends or rejects M3C-1004;
- monthly-workspace retirement/archive prerequisites are explicit;
- no Project mutation occurred.

Then STOP.

zrx will either authorize M3C-1004 or resolve the remaining root decision first.