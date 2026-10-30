# Guide review and promotion v1

Status: S3-3 implementation contract.

## Product result

A Workstation `GUIDE.md` is an editable Practice candidate for one exact execution Cycle. Editing it never changes Project facts or the Project-level canonical Practice automatically.

S3-3 adds a reviewable promotion path:

```text
canonical WORKFLOW-GUIDE.md
-> materialize exact Cycle
-> preserved seed snapshot + editable GUIDE.md
-> Agent edits GUIDE.md during real work
-> guide-diff compares candidate against that exact seed
-> Coordinator/Human reviews the diff
-> explicit hash-bound promotion
-> later Workstation seeds from the promoted canonical Guide
```

No Practice, Review, Workflow, Run or Workstation persistence object is added to PAOS.

## Filesystem layout

S3-3 keeps the S3-1 cycle-bound Workstation and adds one preserved review baseline:

```text
<root>/.paos/
├─ practice/
│  └─ WORKFLOW-GUIDE.md
└─ workstations/<work>/<agent>/cycle-<N>/
   ├─ ENTRY.md
   ├─ GUIDE.md
   ├─ inputs/
   ├─ outputs/
   └─ review/
      └─ GUIDE-SEED.md
```

`GUIDE-SEED.md` contains the exact canonical Guide bytes used to create that Cycle. PAOS tooling writes it during materialization and does not edit it afterward. It is a preserved baseline, not an OS-level read-only file.

The editable candidate is always `GUIDE.md`.

## Candidate review

Agent-facing read-only command:

```text
paos workstation guide-diff PROJECT AGENT \
  --work-id WORK --execution-cycle N [--root PATH]
```

Before local Guide access, the command verifies that the candidate Work and Session exist in the current Project and that the requested Session Cycle canonically belongs to that Work. Filesystem path components are validated before they are used.

The command reads the exact cycle `GUIDE-SEED.md`, editable `GUIDE.md`, and current canonical `WORKFLOW-GUIDE.md`. It returns:

- unified candidate-vs-seed diff;
- seed SHA-256;
- candidate SHA-256;
- current canonical SHA-256;
- whether the candidate changed;
- whether the current canonical still equals the seed.

The diff is always against the exact seed, not against the current canonical. A Human edit or another promotion after this Cycle was materialized therefore appears as canonical drift instead of being silently folded into the candidate diff.

`guide-diff` performs no PAOS POST and no filesystem write.

## Exact reviewed-candidate binding

A promotion is valid only for the exact candidate that was reviewed. The promotion command therefore requires both hashes returned by `guide-diff`:

- `expected_seed_sha256` binds the review to the exact baseline;
- `expected_candidate_sha256` binds the review to the exact edited candidate.

If either file changes after review, promotion fails and the diff must be reviewed again.

This is the local Practice equivalent of an exact-head review gate.

## Coordinator promotion surface

Worker/Workstation CLI does not expose canonical promotion. The dedicated Coordinator surface is:

```text
paos coordinator guide-promote PROJECT \
  --coordinator-session-id COORDINATOR \
  --candidate-work-id WORK \
  --candidate-session-id AGENT \
  --candidate-cycle N \
  --expected-seed-sha256 SHA \
  --expected-candidate-sha256 SHA \
  --change-summary TEXT \
  --execution-cycle COORDINATOR_CYCLE \
  --context-pack-id COORDINATOR_PACK \
  [--root PATH]
```

The command is a local filesystem action, not a PAOS durable mutation. It performs one Project GET to validate current Coordinator truth and resolve the default root path.

The CLI requires explicit `--execution-cycle` and `--context-pack-id`; omission is rejected by the parser. The Coordinator must:

- be the current `organization.coordinator_session_id`;
- be active and acknowledged;
- have a Runtime binding;
- present the exact current Coordinator Cycle / Context Pack supplied to that Runtime.

The command never auto-refreshes the Coordinator tenure.

Human may continue to edit the canonical Markdown file directly. S3-3 does not add a fake `actor=human` flag or an authentication/RBAC layer.

## Promotion safety

Promotion succeeds only when all of the following hold under a local cross-platform advisory lock:

1. seed and candidate files exist and are readable UTF-8 Markdown;
2. supplied review hashes match the exact files currently on disk;
3. candidate differs from seed and is non-empty;
4. current canonical bytes still equal the seed bytes, unless the exact candidate is already current from an earlier successful replay.

If canonical changed since the seed, promotion fails with an explicit drift error. The tool does not merge, overwrite or guess which edits to keep.

Successful publication writes a complete staged file and atomically replaces the canonical file while the promotion lock is held. A replay after successful promotion is a safe no-op when the canonical hash already equals the reviewed candidate hash.

## Artifact lineage

Canonical Guide promotion changes a local Practice file. It does not automatically create a PAOS Artifact because local file replacement and PAOS mutation cannot be made one atomic transaction without adding new persistence semantics.

When the promoted Guide should become durable project evidence, the Coordinator or relevant Agent uses the existing `session artifact-add` path and M5A/M5B lineage:

- Artifact path points to the canonical `WORKFLOW-GUIDE.md` or a versioned exported copy;
- `replaces + change_summary` records the next Process Artifact revision when applicable;
- source/evidence references point to the relevant Work/Review evidence when available.

S3-3 does not add a Practice database or special Guide Artifact type.

## Next-cycle consumption

After promotion, a later `workstation prepare` reads the current canonical Guide and writes both:

- the new Cycle editable `GUIDE.md`;
- the new Cycle preserved `review/GUIDE-SEED.md` baseline.

Both therefore contain the promoted canonical bytes at the start of the later Cycle. S7 still owns real Run 1 -> Run 2 consumption evidence.

## Failure behavior

On any failure:

- canonical Guide bytes remain unchanged;
- candidate and seed bytes remain unchanged;
- no PAOS business mutation occurs;
- no new execution claim is acquired;
- structured CLI errors expose a stable error code and relevant current/expected hashes or tenure coordinates.

## Not in S3-3

- automatic merge of multiple Agent Guide candidates;
- automatic judgment of whether an edit is generalizable;
- automatic Artifact registration;
- automatic Work/Request lifecycle changes;
- automatic Agent selection, Open/Continue, Runtime launch or wake;
- CAT ownership/recovery;
- new Practice/Review/Workflow persistence objects;
- S4 Project browser redesign.

## Acceptance

S3-3 is accepted only when the exact candidate proves:

1. new Workstations preserve `review/GUIDE-SEED.md` with the exact canonical bytes used for seeding;
2. editing `GUIDE.md` changes neither seed nor canonical automatically;
3. `workstation guide-diff` compares candidate to seed and reports seed/candidate/canonical hashes plus canonical drift;
4. Worker/Workstation surface cannot promote canonical Practice;
5. Coordinator promotion requires explicit current execution tenure and never auto-refreshes it;
6. promotion requires the exact reviewed seed and candidate hashes;
7. candidate-after-review changes fail closed without changing canonical;
8. canonical-after-seed drift fails closed without overwriting Human/other promotion edits;
9. successful promotion atomically publishes the reviewed candidate and safe replay does not create another change;
10. the next Cycle seeds both GUIDE and seed baseline from the promoted canonical version;
11. promotion performs one Project GET and zero PAOS POSTs;
12. existing Workstation, Agent CLI, Coordinator, tenure, Artifact lineage and authority tests remain green;
13. `python scripts/verify.py` and `git diff --check` pass.
