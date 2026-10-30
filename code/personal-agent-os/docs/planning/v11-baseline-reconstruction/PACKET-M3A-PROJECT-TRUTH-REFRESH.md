# PAOS V1.1 Stage 1 — Packet M3A Project Truth Refresh / Migration Scope

Decision owner: zrx  
Prerequisite: C3B accepted  
Mutation class: read-only Project/registry/filesystem mapping + report writing

## 0. Purpose

M3A is the first Project/Vault packet.

It does **not** reorganize files.

It answers:

> Which PAOS Projects are truly active enough to migrate now, where does each Project's real work world currently live, and what would a safe dedicated-root/Vault migration need to do?

The old registry `status=active` flag is not enough. Stage 1 needs a current evidence-backed Project disposition.

## 1. Current known starting facts

From Packet A:

```text
1001 周报                  SHARED-ROOT
1002 调研                  SHARED-ROOT
1003 汇报准备              UNHOUSED / root verification pending
1004 文档整理              SHARED-ROOT
1005 周课                  UNHOUSED
2001 LRC101                SHARED-ROOT / DO NOT DISTURB
2002 CD101                 UNHOUSED
2003 RC101应用场景调研      UNHOUSED
3001 obs-agent             MIGRATE-ACTIVE candidate
3002 Personal Agent OS     MIGRATE-ACTIVE / DO NOT DISTURB
```

Shared root:

```text
C:\Users\remo\Desktop\OBSBOT-first-month-workspace
  used by 1001 / 1002 / 1004 / 2001
```

These are historical M0 dispositions, not the final M3 scope.

## 2. Core rule

M3A separates four facts:

```text
registry lifecycle
current Work / Session responsibility
filesystem location
current user/project relevance
```

Do not infer one from another.

Examples:

- `active` registry status does not prove current use;
- no active Session does not prove dormant;
- existing files do not prove canonical root;
- empty root does not authorize creating one;
- recent agent activity does not prove every old Project artifact is current.

## 3. Final disposition vocabulary

Each Project must end M3A with one proposed Stage-1 disposition:

```text
MIGRATE-NOW
  Current real Project; Stage 1 should construct/clean its canonical Vault now.

SHARED-ROOT-MIGRATE
  Current Project whose content is entangled with other Project IDs in one root.

UNHOUSED-MIGRATE
  Current Project with real Work/content but no usable dedicated root.

DORMANT-RETAIN
  Not current enough to justify full Stage-1 migration; preserve registry/history and do not invent a clean active Vault.

ARCHIVE-CANDIDATE
  Clearly ended; still requires later explicit lifecycle/archive decision. M3A does not archive it.

DECISION-REQUIRED
  Facts are insufficient or conflicting; Human/zrx decision needed before mutation.
```

No Project is marked `ARCHIVE-CANDIDATE` merely because it is old.

## 4. Roles

### s027 — primary Project mapper

- update own TODO first;
- read current PAOS registry/Work/Session facts;
- inspect bounded configured roots and known candidate roots;
- build Project truth matrix;
- build filesystem/root maps;
- do not move/create/archive anything.

Outputs:

```text
s027/V11-M3A-PROJECT-TRUTH-MATRIX.md
s027/V11-M3A-PROJECT-ROOT-DRY-RUN-MAP.md
```

### s029 — independent truth-source reviewer

- update own TODO first;
- independently challenge activity/disposition claims;
- inspect competing truth sources and retirement assumptions;
- verify 'looks old' is not used as evidence of dormancy;
- verify shared/unhoused Project proposals do not fabricate roots;
- use `skill-independent-review` if genuinely useful and log honest usage only if used.

Output:

```text
s029/V11-M3A-PROJECT-TRUTH-INDEPENDENT-REVIEW.md
```

### s010 — Coordinator

- use the Coordinator Workflow Kernel;
- provide current responsibility/Work context;
- preserve unresolved Project meaning decisions;
- request a narrow readback from an existing Project Agent only when filesystem/registry evidence cannot determine current truth;
- do not wake stale Agents merely to fill a table;
- return final reconciliation + TODO.

Outputs:

```text
coordinator/V11-M3A-PROJECT-TRUTH-COORDINATOR-READBACK.md
coordinator/COORDINATOR-TODO-AFTER-M3A.md
```

### Other Project Agents

No broad assignment.

A narrow factual question is allowed only when:

- the Agent is already live/reachable;
- it owns a current Project responsibility;
- the question asks for factual source-of-truth / do-not-disturb information;
- no migration mutation is requested.

## 5. Project truth matrix

One row per Project:

```text
project_id
name
registry_status
current Work IDs + states
latest meaningful Work evidence
active/pending Session evidence
configured root
root existence: Windows
root existence: WSL/relevant Runtime if needed
actual content candidate root(s)
shared root relationship
current canonical artifact/source candidates
competing truth sources
do-not-disturb
recent user/project relevance evidence
proposed Stage-1 disposition
reason
confidence
needs zrx/Human decision
```

`latest meaningful Work evidence` means actual progress/result/responsibility evidence, not merely an old lifecycle flag.

## 6. Shared OBSBOT root mapping

For:

```text
1001
1002
1004
2001
```

map the current shared workspace without moving it.

Required:

```text
source subtree / file group
which Project(s) consume it
is it Project-specific or genuinely shared material
current references
current canonical-looking artifact
duplicate/version family
proposed future dedicated Project root or shared-material location
move | copy-reference | archive-later | retain-shared | decision-needed
risk
```

Hard rule:

> Stage-2 cutover cannot leave four Project IDs with the identical canonical `root_path`.

But M3A must not force physically shared material into duplicated Project copies.

A valid future design may be:

```text
<common OBSBOT parent>/
  Shared-Materials/
  Projects/
    1001-.../
    1002-.../
    1004-.../
    2001-LRC101/
```

or another evidence-backed layout.

M3A proposes; it does not create.

## 7. Unhoused/root-recovery mapping

For:

```text
1003
1005
2002
2003
```

search only bounded known locations and references.

Use:

- configured registry path;
- Work/Session artifact references;
- Agent outputs/TODOs;
- known Desktop/project workspaces;
- user-provided/project-known directories.

Do not scan the entire disk.

For each:

```text
configured root
why unusable
candidate real root(s)
evidence linking content to Project
current canonical artifact(s)
recent activity
root recovery proposal
or dormant/decision proposal
```

If no real content root can be established, say so. Do not create an empty Vault merely to satisfy structure.

## 8. 3001 / 3002 dedicated-root mapping

### 3001 obs-agent

Map:

- current source repo structure;
- existing Vault directories if any;
- current Works/Decisions/Materials candidates;
- Project artifacts vs source-code/repo docs;
- historical outputs that should later archive;
- active references that make a move unsafe.

### 3002 Personal Agent OS

Special rule: source repo structure stays source repo structure.

Do not propose moving:

```text
scripts/
attention-dashboard-v1-static/
docs/ contracts/runbooks/planning that are source-controlled product docs
tests/
```

merely because Vault directories exist.

Instead map the additive work-world layer:

```text
Inbox/
Materials/
Works/
Decisions/
Workstations/
Archive/
.paos/ legacy/cycle evidence
local dirty/untracked factual artifacts
handoff/output families
formal decisions/results
```

Required 3002 output questions:

1. Which dirty/untracked files are current source/repo work and must stay where they are?
2. Which are Project artifacts that belong in Works/Materials/Decisions?
3. Which Agent/Cycle outputs are historical evidence for Archive?
4. Which current Workstation/legacy ENTRY facts must remain untouched until M4?
5. Which local planning/problem packs are still referenced?
6. Which duplicates can only be retired after a canonical replacement exists?

No 3002 file mutation in M3A.

## 9. Canonical artifact/version-family mapping

For each MIGRATE/SHARED/UNHOUSED candidate, identify high-value competing current outputs such as:

```text
final.md
final-v2.md
reviewed.md
latest/
多个会议总结/报告副本
old/new Project status pages
```

Do not decide by filename alone.

Record:

```text
version family
candidate current canonical
evidence
old versions
references
proposed archive/retain action
decision needed
```

M3 later needs one discoverable current truth, not filename archaeology.

## 10. Do-not-disturb refresh

M3A must refresh DO-NOT-DISTURB for:

- current open Work;
- active/unreviewed deliverables;
- live Agent Workstations;
- dirty Git worktrees;
- Runtime/config state;
- current Project canonical outputs.

Anything in DO-NOT-DISTURB cannot enter the first mutation batch.

## 11. No deletion policy

M3A never proposes immediate delete for human-created evidence.

Allowed future labels:

```text
retain
move
archive
merge
retire-reference
generated-delete-candidate
decision-required
```

Only clearly generated/rebuildable/unreferenced material may become `generated-delete-candidate`.

## 12. Required Coordinator final table

Coordinator must reconcile all 10 Projects into:

| Project | Current real? | Root state | Stage-1 disposition | Proposed root action | DND? | Open decision |
|---|---|---|---|---|---|---|

Plus sections:

```text
Projects to migrate in Stage 1
Projects to retain dormant without migration
Projects requiring Human/zrx disposition
shared material that should not be duplicated
first safe M3 mutation candidates
blocked/high-risk Projects
```

## 13. First mutation recommendation

M3A should propose, not execute, the safest first mutation batch.

Preferred characteristics:

- dedicated root already exists;
- low ambiguity;
- few live references;
- easy rollback;
- demonstrates Vault structure without risking LRC101/PAOS active work.

Do not assume 3002 should be first merely because it is the current PAOS Project.

## 14. Prohibited mutation

M3A does not authorize:

- creating dedicated Project roots;
- moving/copying Project content;
- editing registry `root_path` or Project status;
- archiving/deleting files;
- changing Session/Work lifecycle;
- creating/migrating Workstations;
- retiring `.paos/agents` / cycle evidence;
- changing Runtime/CAT/activation owner;
- importing new Skills/Workflows.

## 15. Stop conditions

Stop affected mapping if:

- Project identity cannot be separated from another Project;
- two files are both plausible current canonical outputs;
- the apparent old file is still referenced by live Work;
- a root candidate depends on an unknown moved/deleted path;
- Project disposition would require interpreting stale lifecycle as current truth;
- an Agent or user-specific fact conflicts with filesystem evidence;
- source-code repo structure is being mistaken for Vault structure.

## 16. Done When

M3A is complete when:

- all 10 Projects have current truth rows;
- shared OBSBOT root is semantically mapped;
- all un-housed Projects have root recovery/disposition evidence;
- 3001/3002 have additive Vault dry-run maps;
- current canonical/version families are surfaced for migration candidates;
- DO-NOT-DISTURB is refreshed;
- s029 has independently challenged truth/disposition assumptions;
- Coordinator proposes Stage-1 migration scope + first safe mutation batch;
- no filesystem/registry/lifecycle mutation occurred.

Then:

```text
STOP
```

zrx freezes M3 scope and authorizes bounded M3B dry-run/root decisions or the first mutation batch as appropriate.