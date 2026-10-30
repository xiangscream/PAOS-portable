# PAOS V1.1 — M3B Reference Inventory Decision

Decision owner: zrx  
Evidence baseline: M3B handoff commit `64a3d31`

## 1. M3B verdict

M3B read-only reconciliation is accepted.

Key accepted facts:

- `OBSBOT-first-month-workspace` and `OBSBOT-workspace-M` are both still live;
- they are not a simple old/new replacement chain;
- 2001 currently consumes truth from both families;
- 2002 still references `workspace-M/第一个月`;
- 1004 has a small apparent Project-owned subtree, but `file-index.jsonl` indexes the larger shared root and needs ownership/consumer classification;
- 3002 Workstation/Vault taxonomy has no live semantic contradiction;
- monthly workspaces cannot be archived until Project roots/reference cutover and a no-new-writes checkpoint pass.

No filesystem mutation is authorized by this acceptance.

## 2. Important architecture correction: root-level live does not mean every Project is blocked

M3B correctly found that both monthly workspace roots are still receiving writes.

However, Project migration should not require the **entire legacy root** to become read-only before a low-risk Project can move.

The correct migration unit is:

```text
Project-owned source set
+ its live consumers/references
+ its write authority
```

not the whole monthly workspace.

Example:

- 2001 may continue writing elsewhere inside FM;
- 1004 may still become migratable if the exact 1004 source set is stable, no live writer targets it, and all of its consumers are known.

Therefore M3C-1004 should be gated by a **1004-scoped source checkpoint**, not by a global FM freeze.

## 3. Single-writer cutover contract

The concern that a neutral Project-first parent creates a third truth source is valid only if the new destination becomes another writable current root before cutover.

Future M3 mutation must follow this contract:

```text
legacy source = sole writable truth
new Project root = staged destination, not yet authoritative
    ↓
copy / materialize approved Project-owned set
    ↓
hash + reference verification
    ↓
final source checkpoint
    ↓
registry/reference switch
    ↓
new Project root = sole writable truth
legacy source = sealed migration source / archive candidate
```

A temporary duplicate created for verification is not a competing canonical truth if write authority is explicit and exclusive.

Do not permit simultaneous writes to both old and new Project locations.

## 4. Project-first parent remains the target

The long-term design remains Project-first.

Do not select FM or workspace-M as the final canonical Project parent merely because both are already populated.

Preferred logical shape:

```text
<OBSBOT project-first parent>/
├─ Projects/
│  ├─ 1001-周报/
│  ├─ 1002-调研/
│  ├─ 1004-文档整理/
│  └─ 2001-LRC101/
├─ Shared-Materials/
└─ Archive/
   └─ Legacy-Monthly-Workspaces/
```

The exact filesystem path is still not created or frozen by this packet.

Important correction to the M3B handoff suggestion:

> OBSBOT legacy monthly workspaces must **not** be archived under Project 3002 / PAOS `Archive/`.

They belong under the OBSBOT canonical work/archive world or another Human-approved external archive location.

## 5. 1004 `file-index.jsonl` decision remains open

`file-index.jsonl` has two possible semantics:

1. **Project Work artifact**
   - produced by 1004 as the result of a document-organization scan;
   - it may legitimately describe the whole shared root while still being owned by 1004.

2. **Shared scan evidence/index**
   - consumed by multiple Projects or intended as a common workspace index;
   - it should live under Shared-Materials / shared index storage rather than 1004.

File size or indexed scope alone does not decide ownership.

The next packet must establish:

- producer;
- declared artifact ownership;
- actual readers/consumers;
- whether any process expects the old absolute path;
- whether the file is authoritative, historical snapshot, or generated/rebuildable.

## 6. Reference inventory becomes the only next task

Before any M3C mutation, build a bounded live-reference inventory for:

- both monthly workspace families;
- 1004 six-file candidate subtree;
- 1001/1002/1004/2001/2002 registry/key-file references;
- active Agent/Workstation paths;
- PAOS planning/workflow/user docs that contain old absolute paths;
- known scripts/config that could write or resolve these paths.

Every path hit must be classified by **semantics**, not just grep occurrence:

```text
WRITE-AUTHORITY
READ-CONSUMER
GOVERNANCE-REFERENCE
HISTORICAL-DATA-STRING
GENERATED-SNAPSHOT
ARCHIVE-ONLY
UNKNOWN
```

This distinction is essential because an absolute path inside `file-index.jsonl` is historical data, while the same path in registry `root_path` is governance truth.

## 7. No-new-writes checkpoint becomes scoped

For each future Project migration, checkpoint evidence must include:

```text
source-set hash/mtime snapshot
known writer list
known consumer/reference list
short observation window
final recheck immediately before copy/switch
```

Global monthly-workspace no-new-writes is required only for final archive, not for every individual Project migration.

## 8. Archive gate

Monthly workspace archive occurs only after:

- all Project-specific current truth has moved or been deliberately retained elsewhere;
- shared materials have one canonical home;
- registry/key_files and current Agent references no longer point into monthly roots;
- active writers no longer target monthly roots;
- final full-root no-new-writes checkpoint passes;
- archive location is approved;
- legacy trees are preserved as immutable history, not deleted.

Until then they remain migration sources.

## 9. Next authorization

Authorize one read-only packet only:

```text
M3B-REF
reference / writer / consumer inventory
→ 1004 ownership decision
→ Project-scoped checkpoint design
→ STOP
```

No root creation, copy, registry edit, reference rewrite, write freeze or archive action is part of M3B-REF.