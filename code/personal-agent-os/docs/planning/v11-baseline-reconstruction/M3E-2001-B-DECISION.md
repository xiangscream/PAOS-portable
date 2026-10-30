# PAOS V1.1 — M3E-2001-B Decision

Decision owner: zrx
Evidence baseline: M3E-2001-A handoff `aa24b329bcf5856ecb7310a9e520bf571d067aee`

## 1. Verdict

M3E-2001-A is accepted.

Current Project 2001 remains unchanged:

```text
revision = 1068
root_path = C:\Users\remo\Desktop\OBSBOT-first-month-workspace
key_files = 10
artifacts = 377
new Vault = absent
```

The accepted disposition is:

```text
M3E-2001-A = NEED-CONTRACT-EXTENSION
migration = NOT AUTHORIZED
```

The next packet is:

```text
M3E-2001-B = READ-ONLY CONTRACT + OWNERSHIP CLOSURE
```

## 2. Mainline decisions

### 2.1 Human-DND policy

Current Human-authored LRC101 material is protected by default.

When a later staging packet is authorized, Human-DND material may be copied only under these rules:

- byte-for-byte copy;
- preserve filename;
- preserve meaningful relative grouping;
- no semantic rewrite;
- no merge;
- no rename for tidiness;
- no frontmatter injection;
- no deletion;
- source remains intact through cutover verification.

This policy decision does not create a no-write window now.

The final mutation packet must still require a scoped T1 checkpoint over the exact files selected for cutover. Current LRC101 work does not need to stop during M3E-B.

### 2.2 Obsidian / WorkBuddy state

Legacy `.obsidian/` and `.workbuddy/` directories are application state, not Project content.

Default disposition:

```text
legacy .obsidian/  -> EXCLUDE
legacy .workbuddy/ -> EXCLUDE
```

The future independent Vault may create its own local `.obsidian/` state after or during normal Obsidian use. It must not inherit a shared legacy workspace configuration wholesale.

The mere existence of writers inside excluded application-state directories does not block Project migration. A writer blocks cutover only if it can modify a file in the selected Project-content source set.

### 2.3 Runtime evidence

Current `FM/.paos/**` Agent, Workstation and Cycle evidence does not move into the LRC101 Obsidian Vault.

Default disposition:

```text
FM/.paos/agents/2001-*        -> RETAIN-IN-PLACE until M4
FM/.paos/workstations/2001-*  -> RETAIN-IN-PLACE until M4
runtime/cycle Artifact paths  -> RETAIN-IN-PLACE unless a later M4 action moves them
```

This is a temporary compatibility state, not the long-term Stage-2 destination.

### 2.4 No pre-migration path cleanup

Do not run a separate bulk path-normalization mutation before migration.

Current registry strings are evidence. M3E-B classifies them exactly as stored. A later relocation transaction may write canonical destination paths for entries that actually move.

Do not rewrite paths merely to make `C:\`, `C:/`, `C://`, `/mnt/c` or relative forms look uniform.

## 3. Relocation contract direction

M3E-A proves that the current v1 contract is insufficient for Project 2001.

Mainline freezes the desired next semantic contract as:

```text
paos-project-root-relocate/v2
same Human-only /relocate-root semantic action
```

The v2 design must preserve the v1 safety model and add two capabilities.

### 3.1 Exact key_files replacement

The request carries both:

```text
from_key_files
to_key_files
```

Rules:

- `from_key_files` must exactly match the current ordered list before mutation;
- `to_key_files` is the complete desired post-cutover list;
- unchanged external URLs and root-outside references may remain identical;
- moved Project-local references may change to new canonical paths;
- no implicit URL localization or path normalization;
- replay remains idempotent;
- rollback receipt records the full pre-cutover key_files list.

This keeps key_files atomic with root and Artifact pointer changes without forcing every key_file to live under the new root.

### 3.2 Explicit Artifact retain-in-place exceptions

The request may contain:

```text
artifact_moves[]
artifact_retains[]
```

Every Artifact currently housed under `from_root_path` must be accounted for by exactly one of:

```text
MOVE
RETAIN-IN-PLACE
```

A retain entry must include:

```text
id
path
retention_class
reason
```

Allowed retention classes for this migration design:

```text
runtime_evidence
external_reference
cross_project_reference
historical_evidence
```

Rules:

- retained path is an exact current-path precondition and is not rewritten;
- moved destination paths must remain inside `to_root_path`;
- no Artifact may appear in both move and retain;
- omitted old-root Artifact remains a hard rejection;
- receipt records moved and retained sets;
- rollback before-state includes root, Artifact paths and key_files.

The contract does not change Work, Session, Request, Decision or Artifact lineage/status.

## 4. Why v2 stays narrow

Do not turn root relocation into general Project cleanup.

M3E-B must not use the relocation transaction to:

- rewrite Artifact purpose/type;
- repair lineage;
- deduplicate logical documents;
- retire historical Artifact records;
- move Runtime sessions;
- create Workstations;
- rewrite external URLs;
- clean application state.

Those are separate concerns.

## 5. M3E-B goal

M3E-B must produce the exact migration input needed to implement and later exercise v2 safely.

It must close:

1. all 10 key_files dispositions;
2. all old-root Artifact MOVE vs RETAIN accounting;
3. all six relative/no-root Artifact ownership cases;
4. Downloads and 3002-repo cross-Project ownership cases;
5. shared-vs-2001 ownership for the named ambiguous directories/packages;
6. selected Human/current content source set;
7. exact writer set for that selected source set;
8. current Agent continuity dependency that must survive root cutover.

M3E-B is read-only. It does not create the Vault and does not implement v2.

## 6. Exit verdict

Coordinator must return exactly one:

```text
READY-FOR-CONTRACT-IMPLEMENTATION
NEED-HUMAN-OWNERSHIP-DECISION
BLOCKED-UNKNOWN-CONTENT-WRITER
BLOCKED-UNRESOLVED-ARTIFACT
```

`READY-FOR-CONTRACT-IMPLEMENTATION` means the v2 contract shape and 2001 disposition tables are complete enough to implement and test against disposable data.

It does not authorize 2001 staging or cutover.
