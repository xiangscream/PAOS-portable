# PAOS V1.1 Stage 1 — Packet M3C-1004 First Project Migration

Decision owner: zrx  
Prerequisite: M3B-REF accepted  
Mutation class: bounded create/copy + registry/reference cutover

## 0. Goal

Prove the Project-first migration pattern on one low-risk Project without disturbing the active monthly workspace cluster.

Source:

```text
C:\Users\remo\Desktop\OBSBOT-first-month-workspace\90-Agent-Ops\1004-s003-scan\
```

Destination:

```text
C:\Users\remo\Desktop\OBSBOT-Projects\1004-文档整理\Works\1004-s003-scan\
```

## 1. Roles

### s027 — executor

- update own TODO first;
- perform preflight, staged copy, hash verification and cutover only within this packet;
- preserve source;
- stop on any unexpected path/registry conflict.

### s029 — independent reviewer

- update own TODO first;
- review staged destination before registry switch;
- independently verify hashes/source stability/governance scope;
- review post-cutover state;
- use `skill-independent-review` only if genuinely useful and log honest usage if used.

### s010 — Coordinator

- use `wf-coordinator-governance-cycle`;
- enforce the checkpoint sequence;
- ensure no one reruns the 1004 scan into the old path during the packet;
- authorize the conditional cutover only after s029 staging PASS;
- preserve rollback evidence and STOP after final review.

## 2. M3C-A — preflight / T0

Before creating anything:

1. confirm canonical PAOS planning baseline from the merged authorization;
2. confirm source path exists and contains exactly the known six files;
3. capture **full SHA-256**, size and mtime for each file;
4. confirm no current 1004 writer/session/process is targeting the source subtree;
5. confirm no new Project/Agent consumer has appeared since M3B-REF;
6. confirm destination parent/root does not already contain user content;
7. capture current 1004 registry/governance before-state sufficient for rollback.

Six files:

```text
file-index.jsonl
scan-summary.json
INDEX.md
agent-session-map.md
project-files-map.md
scan-methodology.md
```

If any source hash/mtime unexpectedly differs from the accepted M3B-REF baseline, STOP and report before copy.

During this packet, do not manually rerun the scan into the old path.

## 3. M3C-B — create staged Project root + copy

Create only:

```text
C:\Users\remo\Desktop\OBSBOT-Projects\1004-文档整理\
  Inbox\
  Materials\
  Works\1004-s003-scan\
  Decisions\
  Workstations\
  Archive\
```

Use the existing canonical initializer if it creates exactly the standard Project structure **without prematurely changing registry truth**; otherwise create the approved directories directly.

Copy the six files byte-for-byte into `Works\1004-s003-scan\`.

Rules:

- copy, do not move;
- preserve source;
- do not rewrite historical absolute paths;
- do not edit file contents;
- no second copy in Shared-Materials;
- destination is staged/non-authoritative until cutover.

After copy:

- recompute full SHA-256 on destination;
- verify source == destination for all six;
- record exact source/destination manifest.

Create one migration decision/provenance record under:

```text
Decisions/V11-M3C-1004-ROOT-MIGRATION.md
```

It should contain only durable facts:

- old root/source path;
- new root;
- six-file manifest/hash;
- ownership decision for `file-index.jsonl`;
- cutover timestamp when it later occurs;
- rollback source.

Do not include process diary.

## 4. M3C-C — independent staged-copy gate

Before any registry/reference switch, s029 independently verifies:

- destination path is exactly approved;
- only approved directories/files were created;
- six destination hashes equal T0 source hashes;
- source six-file set is still unchanged;
- no new 1004 writer/consumer exists;
- `file-index.jsonl` remains intact and is not duplicated into Shared-Materials;
- the migration decision record is factual and clean;
- no 1001/1002/2001/2002 data or runtime state was touched.

Verdict:

```text
PASS → Coordinator may proceed to M3C-D in this same packet
P1   → STOP; no registry switch
```

## 5. M3C-D — final T1 + governance cutover

Immediately before switch:

1. re-hash/re-stat the source six files;
2. verify they still equal T0;
3. verify staged destination still matches;
4. verify no new 1004 writer/consumer;
5. verify rollback before-state is available.

Then update **only current 1004 governance/reference truth** required to make the dedicated root authoritative.

Required end state:

```text
1004.root_path
  -> C:\Users\remo\Desktop\OBSBOT-Projects\1004-文档整理

1004 active artifact pointers for the six files
  -> ...\Works\1004-s003-scan\<file>
```

If current 1004 context projection is generated from registry truth, regenerate/rebuild it using the supported PAOS mechanism after the registry switch.

Do not hand-edit historical backups/snapshots/context history merely to replace old strings.

Registry mutation requirements:

- use the supported canonical PAOS registry mutation mechanism where available;
- preserve/verify its normal backup or create one bounded before-state rollback artifact in the existing registry backup convention;
- no second registry;
- registry switch is the **last authority-changing step**.

## 6. M3C-E — post-cutover verification

After the switch, prove:

- Project 1004 resolves to the new dedicated root through the real PAOS read path/API;
- six current artifacts resolve from the new root;
- staged files still hash-match legacy source;
- old source subtree still exists unchanged;
- no new 1004 write has occurred in the old subtree;
- no other Project registry/root/key-file changed;
- FM remains available for 1001/1002/2001;
- monthly workspace archive state remains unchanged.

s029 independently reviews the final state.

## 7. Rollback

### Failure before governance switch

```text
source remains canonical
delete/remove only the staged 1004 destination if desired after evidence is captured
no registry rollback needed
```

### Failure after governance switch

```text
restore 1004 governance/reference before-state
verify old root/source is readable
leave staged copy in place as evidence until reviewed
do not delete legacy source
STOP and report P1
```

## 8. Source after successful cutover

Do not delete or physically archive the old six-file subtree yet.

Operational rule after PASS:

> no new 1004 work writes to the legacy subtree.

It remains a preserved migration source until the monthly workspace archive phase.

Do not chmod/read-only the whole FM root because 1001/1002/2001 still use it.

## 9. Explicitly out of scope

Do not:

- create 1001/1002/2001 roots;
- create Shared-Materials or legacy monthly archive directories unless the standard parent creation requires an empty container only;
- alter 2001/2002 references;
- alter `docs/workflows/README.md`; 
- rewrite planning/history old path strings;
- move `.paos/agents` or `.paos/workstations`;
- archive/delete monthly workspaces;
- touch 3002 Workstations/Runtime/CAT;
- expand Skill/Workflow baseline.

## 10. Required handoff

s027:

```text
s027/V11-M3C-1004-STAGED-MIGRATION.md
s027/V11-M3C-1004-CUTOVER.md
```

s029:

```text
s029/V11-M3C-1004-STAGING-REVIEW.md
s029/V11-M3C-1004-POST-CUTOVER-REVIEW.md
```

Coordinator:

```text
coordinator/V11-M3C-1004-COORDINATOR-READBACK.md
coordinator/COORDINATOR-TODO-AFTER-M3C-1004.md
```

Reports must include:

- exact source/destination paths;
- full hashes;
- registry before/after;
- exact mutation list;
- rollback evidence;
- P1/P2;
- current personal TODO closeout.

## 11. Stop gate

After post-cutover review:

```text
STOP
```

Do not automatically begin 1001/1002 or 2001 migration.

zrx will evaluate whether the first Project-first migration pattern is proven and then authorize M3D.