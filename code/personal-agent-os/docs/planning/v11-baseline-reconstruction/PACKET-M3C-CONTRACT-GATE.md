# PAOS V1.1 — Packet M3C-CONTRACT Project Root Relocation Gate

Decision owner: zrx
Production mutation: prohibited during this packet

## 0. Why this packet exists

M3C-1004 filesystem staging passed, but cutover correctly stopped because the current PAOS manual Project update can change `root_path` without atomically relocating existing Artifact pointers.

Legacy root-only bypass must be closed before merge: `project.update` must reject `root_path`, forcing all root changes through `project.root.relocate`.

The staged 1004 files are already valid and remain in place.

This packet validates one missing governance primitive:

```text
project.root.relocate
```

It is a product contract, not a one-off 1004 script.

## 1. Candidate contract

HTTP:

```text
POST /api/projects/{project_id}/relocate-root
```

Schema:

```text
paos-project-root-relocate/v1
```

Authority:

```text
Human only
```

Mutation:

```text
exact base revision
+ idempotent operation_id
+ current root precondition
+ explicit existing Artifact old/new paths
→ one Project revision
→ one Ledger event
→ one operation receipt
→ normal Project backup
```

The contract does not copy filesystem content.

## 2. Safety invariants

The implementation must prove all of these:

1. `root_path` and Artifact path moves commit in one Project JSON replacement.
2. Current root must match `from_root_path`.
3. Each Artifact must exist and its current path must match `from_path`.
4. Every Artifact still under the old root must be included in the same relocation operation.
5. Every moved Artifact destination must be under `to_root_path`.
6. Exact base revision is required for a new relocation.
7. Same `operation_id` + same request replays the original receipt without advancing revision.
8. Same `operation_id` + different request conflicts.
9. Existing Work/Sessions/Requests/Decisions are unchanged.
10. Existing Ledger is preserved; exactly one relocation event is appended.
11. Rollback facts are present in the operation receipt.
12. Historical backups/context/snapshot contents are not rewritten.
13. Restore semantics still invalidate replay when the existing Store rules require it.

## 3. s027 — exact-head implementation gate

Use a clean runner/worktree at the exact PR candidate HEAD.

Do not use the dirty primary worktree as the executable baseline.

Run at minimum:

```text
focused:
  test_project_store.py relocation tests
  test_authority_manifest.py

full:
  python scripts/verify.py
  git diff --check
```

Also run a disposable API smoke with a temporary registry:

```text
create disposable Project
with old root + at least two Artifact paths
→ POST relocate-root
→ assert revision +1
→ assert root + Artifact paths changed together
→ assert one operation receipt + Ledger event
→ replay identical operation
→ assert no second revision/event
→ stale/mismatched path case
→ assert 409/422 and no state mutation
```

Do not point the smoke at the real 1004 registry.

Output:

```text
s027/V11-M3C-CONTRACT-IMPLEMENTATION-GATE.md
```

Include:

- exact candidate SHA;
- focused/full test counts;
- disposable API payload/receipt summary;
- exact observed touched state;
- deployment notes;
- any unexpected contract friction.

## 4. s029 — independent review

Review the exact same candidate HEAD independently.

Focus on:

- whether the new action is genuinely atomic at Project-state level;
- whether exact-revision behavior still allows idempotent replay;
- whether omitted old-root Artifacts are rejected;
- whether the implementation accidentally mutates Work/Sessions/Requests/Decisions;
- whether rollback data is sufficient;
- whether Authority Manifest and HTTP route match;
- whether a malicious/accidental destination path can escape the new root;
- whether the new contract duplicates or weakens existing `project.update`;
- whether no-op or partial relocation can create split truth;
- whether `mutate_v2` change affects existing callers.

Use `skill-independent-review` if genuinely useful and log an honest usage event if used.

Output:

```text
s029/V11-M3C-CONTRACT-INDEPENDENT-REVIEW.md
```

Any P1 stops merge/deploy.

## 5. s031 — deployment readback, only after merge authorization

Do not deploy the PR candidate merely to test production.

After zrx merges an accepted candidate, s031 performs the runtime deployment/restart using the canonical service procedure.

Required evidence:

```text
running /api/health build/source commit == merged canonical main
relocate-root route present
authority endpoint reports project.root.relocate as Human-only
existing services recover normally
no duplicate dashboard writer process
```

Output after merge:

```text
s031/V11-M3C-CONTRACT-DEPLOYMENT-READBACK.md
```

## 6. Coordinator

During pre-merge gate:

- preserve the retained 1004 staged copy;
- do not rerun the scan;
- do not call root-only `project.update`;
- do not edit registry JSON;
- do not create the migration Decision yet;
- collect s027/s029 exact-head evidence.

Output:

```text
coordinator/V11-M3C-CONTRACT-COORDINATOR-READBACK.md
coordinator/COORDINATOR-TODO-AFTER-M3C-CONTRACT.md
```

## 7. Merge gate

zrx may merge only when:

- s027 exact-head implementation gate PASS;
- s029 has no unresolved P1;
- full verifier and diff check pass;
- disposable API smoke proves atomic root+Artifact relocation;
- no production 1004 mutation occurred.

After merge, deployment is a separate gate.

## 8. Production resume gate

M3C-1004 resumes only when:

1. merged canonical main is deployed;
2. running build SHA is verified;
3. 1004 still reads revision 7 / old root / old Artifact pointers;
4. retained staged copy still hash-matches source;
5. T1 recheck passes.

Then one Human-authorized `project.root.relocate` operation may perform the governance cutover.

No recopy is required unless source/staged drift is detected.

## 9. Stop gate

Pre-merge packet ends after s027/s029 evidence:

```text
STOP
```

Do not merge locally and do not deploy production without zrx acceptance.
