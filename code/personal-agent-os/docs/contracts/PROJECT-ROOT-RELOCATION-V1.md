# Project Root Relocation Contract V1

Status: candidate implementation contract
Schema: `paos-project-root-relocate/v1`

## Purpose

Move a Project's canonical root without splitting Project truth.

Generic `project.update` must not change `root_path`; root relocation is only valid through this dedicated contract.

The action updates, in one Project revision:

- `root_path`;
- explicitly listed existing Artifact `path` values.

It does not copy or delete filesystem content. Filesystem staging is completed and independently verified before this action is called.

## Authority

`project.root.relocate` is Human-only.

```text
POST /api/projects/{project_id}/relocate-root
```

The action requires:

- exact `base_revision`;
- idempotent `operation_id`;
- exact old root;
- explicit old/new path for every Artifact being relocated.

## Request

```json
{
  "schema": "paos-project-root-relocate/v1",
  "operation_id": "op-project-relocate-1004-001",
  "base_revision": 7,
  "from_root_path": "C:\\old-project-root",
  "to_root_path": "C:\\new-project-root",
  "artifact_moves": [
    {
      "id": "1004-a001",
      "from_path": "C:\\old-project-root\\Works\\a.txt",
      "to_path": "C:\\new-project-root\\Works\\a.txt"
    }
  ],
  "reason": "Project-first root migration after staged-copy verification."
}
```

## Validation

The action rejects the request when:

- the Project revision is not exactly `base_revision`;
- current `root_path` does not match `from_root_path`;
- an Artifact ID does not exist or does not belong to the Project;
- an Artifact's current path does not match its declared `from_path`;
- a destination Artifact path is outside `to_root_path`;
- two Artifact moves share a destination;
- an Artifact still housed under the old root is omitted from the operation.

The last rule prevents:

```text
root_path -> new root
artifact.path -> old root
```

from becoming a committed Project state.

## Atomic mutation

The Store applies the root and Artifact path changes to one in-memory Project copy, validates the complete Project, then commits through `ProjectStore.mutate_v2`.

One successful operation produces:

- one Project revision;
- one `project.root.relocated` Ledger event;
- one operation receipt;
- one normal Project backup.

Existing Work, Sessions, Requests, Decisions and historical Ledger entries are preserved.

## Receipt and rollback data

The operation receipt contains a nested `relocation_receipt`:

```json
{
  "schema": "paos-project-root-relocate-receipt/v1",
  "operation_id": "op-project-relocate-1004-001",
  "project_id": "1004",
  "revision": 8,
  "from_root_path": "C:\\old-project-root",
  "to_root_path": "C:\\new-project-root",
  "artifact_moves": [],
  "rollback": {
    "root_path": "C:\\old-project-root",
    "artifact_paths": []
  }
}
```

The receipt describes governance rollback facts. It does not delete or move filesystem content.

## Idempotency

Replaying the same `operation_id` with the same request returns the original receipt and does not advance revision again.

Reusing the same `operation_id` with different content is rejected.

A new relocation operation requires the exact current Project revision.

## Filesystem boundary

This contract assumes staging has already passed:

```text
source checkpoint
-> staged copy
-> hash verification
-> independent review
-> final source checkpoint
-> project.root.relocate
```

The endpoint does not verify file hashes or create directories. Those remain migration-workflow evidence.

## Historical data

The action changes canonical Artifact pointers only.

It does not rewrite old path strings inside:

- snapshots;
- reports;
- registry backups;
- historical context packs;
- generated indexes.

Historical content remains historical evidence.

## Restore

Normal Project backup/restore remains available as Human-only recovery.

A restore may invalidate replay eligibility of an older relocation receipt under the existing `mutate_v2` restore boundary.
