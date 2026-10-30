# PAOS V1.1 — Packet M3E-2001-B Contract / Ownership Closure

Decision owner: zrx
Mode: read-only
Project: 2001 LRC101

## 0. Goal

Turn the M3E-A findings into an exact migration contract and exact Project-2001 disposition map.

No filesystem or Project mutation is authorized.

## 1. Baseline

Use live PAOS Project 2001 first. Record:

```text
deployed build SHA
project revision
root_path
ordered key_files
Artifact count and exact stored paths
active/recent Work
active/non-terminal Sessions
current stable/legacy Agent entry locations
```

If live facts differ from M3E-A, report the delta. Do not silently reuse revision 1068.

## 2. s027 — primary closure map

Update own TODO first.

### B-001 key_files disposition

Produce an exact table for all current key_files:

```text
index
current_value
kind = PROJECT-LOCAL | SHARED-REFERENCE | EXTERNAL-URL | ROOT-OUTSIDE | LEGACY-ROOT | INVALID
post_cutover_value
action = CHANGE | KEEP | REMOVE
reason
source evidence
```

Do not mutate the list.

The output must be sufficient to construct exact `from_key_files` and `to_key_files` arrays later.

### B-002 Artifact disposition

Produce a machine-readable Artifact disposition file plus a readable summary.

Required machine-readable output:

```text
s027/V11-M3E-2001-B-ARTIFACT-DISPOSITION.jsonl
```

One row per current Artifact:

```json
{
  "id": "2001-a001",
  "current_path": "...",
  "class": "PROJECT_CONTENT | RUNTIME_EVIDENCE | EXTERNAL_REFERENCE | CROSS_PROJECT_REFERENCE | HISTORICAL_EVIDENCE | UNKNOWN",
  "cutover_action": "MOVE | RETAIN | UNRESOLVED",
  "proposed_path": "... or null",
  "owner": "2001 | SHARED | 3002 | EXTERNAL | UNKNOWN",
  "reason": "..."
}
```

Rules:

- do not infer ownership from filename alone;
- all Artifacts physically under the old FM root must end as MOVE, RETAIN or UNRESOLVED;
- runtime evidence under `.paos/**` should default RETAIN unless contrary evidence exists;
- external URLs should default RETAIN;
- 3002-repo and Downloads paths require explicit ownership reasoning;
- relative/no-root paths require source resolution or UNRESOLVED;
- duplicate logical documents may remain separate registry rows in this packet; identify likely duplicate families in the summary, but do not mutate or deduplicate them.

Readable summary:

```text
s027/V11-M3E-2001-B-ARTIFACT-SUMMARY.md
```

Include counts by class/action and all unresolved IDs.

### B-003 Project-content source set

Produce the exact candidate content set that a future staged copy would use.

Output:

```text
s027/V11-M3E-2001-B-CONTENT-SOURCE-MANIFEST.md
```

For each selected file/directory:

```text
source path
owner
truth class
Human-DND yes/no
writer
consumer
future Vault location
copy mode
hash/size/mtime where practical
```

Exclude by default:

```text
legacy .obsidian/
legacy .workbuddy/
FM/.paos/agents/
FM/.paos/workstations/
other Runtime/Cycle evidence
```

Do not exclude a directory merely because its parent is excluded if a live Project file is explicitly referenced inside it; report such a conflict.

### B-004 ownership closure

Resolve the specific M3E-A ambiguous sets:

- six relative/no-root Artifacts;
- four Downloads Artifacts;
- three 3002-repo Artifacts;
- FM `90-Agent-Ops` references used by 2001;
- workspace-M `软件资料库`;
- workspace-M `ob子库`;
- `LRC101-产品定义工作台.zip`.

For each, return:

```text
owner
current role
move/retain/reference disposition
evidence
remaining uncertainty
```

No mutation.

### B-005 writer boundary

Writer closure is scoped to the selected Project-content source set, not the whole legacy workspace.

Identify every process/person/Agent that can write a selected source path.

`.obsidian` or `.workbuddy` internal state writers do not count as blockers unless evidence shows they also mutate a selected Project-content file.

Return the exact condition required for a future T1 no-new-writes checkpoint.

## 3. s029 — independent review

Update own TODO first and review without adopting s027 classifications by default.

Required report:

```text
s029/V11-M3E-2001-B-INDEPENDENT-REVIEW.md
```

Challenge:

- all 10 key_file dispositions;
- completeness of old-root Artifact MOVE/RETAIN accounting;
- every UNRESOLVED Artifact;
- ownership of Downloads / 3002 / shared-material candidates;
- whether runtime Artifact RETAIN semantics preserve Agent continuity without pretending FM remains the Project root;
- whether selected Human-DND content is complete;
- whether the writer checkpoint is scoped narrowly enough to be achievable;
- whether relocation v2 can stay limited to root + Artifact path accounting + key_files.

Do not propose moving Runtime evidence into the Vault merely to make the table complete.

## 4. s031 — runtime evidence only if requested

Use only when s010 needs independent Runtime evidence.

May inspect, read-only:

- which current 2001 Agents/Cycles still resolve files from FM runtime directories;
- whether root cutover alone changes their current Runtime locator behavior;
- which paths must stay reachable until M4.

No restart, rebind, stop or migration action is authorized.

If used, return:

```text
s031/V11-M3E-2001-B-RUNTIME-CONTINUITY.md
```

## 5. Coordinator

s010 collects the reports and writes:

```text
coordinator/V11-M3E-2001-B-COORDINATOR-READBACK.md
coordinator/COORDINATOR-TODO-AFTER-M3E-2001-B.md
```

The readback must include:

- current live 2001 revision/root;
- exact key_files before/after proposal;
- Artifact MOVE/RETAIN/UNRESOLVED counts;
- unresolved Artifact IDs;
- selected future staged-copy source families;
- Human-DND source families;
- writer checkpoint condition;
- whether Runtime continuity requires an M4-side action before cutover;
- P1/P2.

End with exactly one:

```text
READY-FOR-CONTRACT-IMPLEMENTATION
NEED-HUMAN-OWNERSHIP-DECISION
BLOCKED-UNKNOWN-CONTENT-WRITER
BLOCKED-UNRESOLVED-ARTIFACT
```

Then STOP.

## 6. Contract review checklist

The read-only packet should test the proposed v2 semantics against the real 2001 map.

Expected contract:

```text
schema = paos-project-root-relocate/v2
route  = POST /api/projects/{project_id}/relocate-root
authority = Human-only

request:
  operation_id
  base_revision
  from_root_path
  to_root_path
  from_key_files[]
  to_key_files[]
  artifact_moves[]
  artifact_retains[]
  reason
```

Required invariants:

- exact base revision;
- identical replay is idempotent;
- changed replay conflicts;
- current root matches from_root;
- current ordered key_files exactly match from_key_files;
- each Artifact under old root is exactly MOVE or RETAIN;
- MOVE current path must match from_path;
- MOVE destination must be inside new root;
- RETAIN current path must match and remain unchanged;
- no ID appears in both sets;
- root, moved Artifact paths and key_files update in one revision;
- one Ledger event;
- rollback receipt contains old root, old key_files, moved Artifact old paths and retained set;
- Work/Sessions/Requests/Decisions remain unchanged;
- v1 remains valid for simple migrations such as 1004;
- generic `project.update(root_path)` remains rejected.

If the real 2001 map proves this shape insufficient, report the smallest missing semantic requirement. Do not broaden the contract speculatively.

## 7. Prohibited actions

M3E-B does not authorize:

- creating `C:\Users\remo\Desktop\OBSBOT-Projects\2001-LRC101`;
- copying or moving any LRC101 file;
- editing Human content;
- modifying Project 2001 root/key_files/Artifacts;
- normalizing registry paths;
- changing Artifact lineage/status;
- moving Workstations or `.paos` runtime evidence;
- copying legacy `.obsidian` or `.workbuddy`;
- archiving monthly workspaces;
- implementing relocation v2.

Only reports, personal TODO updates, normal Work/Request lifecycle updates for this packet, and handoff evidence are allowed.

## 8. Work closeout

The findings from M3E-A are accepted. Coordinator may close/accept the M3E-A review Works after recording this decision according to normal PAOS Work governance.

M3E-B should use new bounded Work/Requests rather than reopening the A tasks.
