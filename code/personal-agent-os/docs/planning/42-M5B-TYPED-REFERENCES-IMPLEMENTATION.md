# M5B Typed Evidence References — Implementation Plan

## Goal

Complete M5 by adding typed references to the existing PAOS work language without introducing a new workflow engine or relation database.

M5B adds three semantics:

- `Artifact.subject_refs`: what this Artifact discusses or reviews;
- `Artifact.source_refs`: what materials or discussions contributed to it;
- `evidence_refs`: which ordinary PAOS Artifacts support a Decision or Work judgment.

M5A remains the authority for Artifact revision lineage and current registered heads.

## Baseline

Development starts from the merged M5A main tree. M4 remains a separate Draft and is not an M5B dependency.

No CAT repository change is required. CAT Exchange references are stored only as coordinates.

## Design boundaries

### Keep the existing workflow owners

M5B does not add Artifact, Decision, Review, Work-completion, or Promote routes.

Existing workflows continue to own:

- Artifact creation;
- Decision proposal creation;
- Human Work review/evaluation;
- Coordinator Work transition;
- M1A execution tenure and operation idempotency.

A narrow typed-reference hook extracts reference metadata before lower request normalizers discard unknown fields. A per-call Store facade attaches the metadata inside the same existing `mutate_v2` apply operation.

The facade does not write files, advance revision, append Ledger directly, allocate business IDs, or perform a second mutation.

### Reference types stay domain-specific

`reference_contracts.py` centralizes the small shared shape validator, but stored JSON keeps the domain field names. There is no persisted `Relation` object.

V0 allows:

```text
subject_refs  -> Artifact only
evidence_refs -> Artifact only
source_refs   -> Artifact | CAT Exchange | external locator
```

Artifact-backed references must point to a currently visible ordinary Artifact in the same Project. Agent Working Memory is excluded.

### External sources remain opaque

CAT and external source refs are stored as source coordinates. M5B does not call CAT, Git, Feishu, or the web and does not claim the source is verified or permanently recoverable.

### Evidence stays optional

No Work completion path gains a mandatory evidence or Technical Review gate.

Human accept/evaluation can attach evidence to the evaluation entry. Coordinator `status=done` can attach `completion_evidence_refs`. Decision proposals can attach evidence at proposal creation.

Human Decision review does not mutate proposal evidence. Work cancellation does not create an evidence channel.

## Atomicity and idempotency

Typed Artifact targets are checked before the lower business apply executes.

When references are present, the canonical request hash includes the normalized reference plan. Therefore:

- exact replay returns the original receipt;
- the same operation with changed references conflicts;
- a missing reference aborts the entire containing mutation;
- no partial Work/Decision/Artifact update is committed.

The existing Store remains the final authority for tenure, revision conflict, Restore replay boundaries, validation, Ledger append, receipts, backup, and atomic replacement.

## Historical explanation

For a successful mutation with non-empty typed references, M5B adds `details.typed_reference_evidence` to the existing Ledger event.

This is a small metadata snapshot of the declared reference plan. It exists only to explain what the historical mutation said.

It does not:

- restore hidden Artifacts or Decisions;
- populate current reverse references;
- select current Artifact heads;
- replace current Project truth.

M5A dedicated Artifact registration evidence also sees the attached `subject_refs` / `source_refs` because they are added before the existing event-details callback is evaluated.

## Projection

`reference_projection.py` derives current reverse Artifact usage by scanning current Project objects.

It can report that an Artifact is currently referenced as:

- an Artifact subject;
- an Artifact source;
- Decision evidence;
- Work completion evidence;
- Work evaluation evidence.

`referenced_by` is never stored on an Artifact.

A bounded projection is included in Context Pack and live Agent Detail. It includes only compact IDs and source coordinates; no Artifact file bodies, CAT chat bodies, or external source content are loaded.

## Files

### New

- `attention-dashboard-v1-static/reference_contracts.py`
- `attention-dashboard-v1-static/reference_projection.py`
- `attention-dashboard-v1-static/typed_reference_hooks.py`
- `attention-dashboard-v1-static/tests/test_typed_references_m5b.py`
- `docs/contracts/ARTIFACT-EVIDENCE-REFERENCES-V0.md`
- `docs/planning/42-M5B-TYPED-REFERENCES-IMPLEMENTATION.md`

### Modified

- `attention-dashboard-v1-static/workflow_service.py` — compose the typed-reference hook and expose an internal read-only reverse projection.

No ProjectStore core, local-server route, CAT code, Blob store, external adapter, or UI relation editor is added.

## Verification matrix

Focused tests must cover:

1. `subject_refs` and `evidence_refs` accept only same-Project ordinary Artifact IDs.
2. `source_refs` accepts only the three V0 source kinds and rejects duplicate/malformed refs.
3. Session Update can atomically create an Artifact with sources and a Decision with evidence.
4. A dangling reference aborts every other change in the same mutation.
5. Dedicated Artifact Add carries refs into M5A registration evidence.
6. Working Memory cannot become subject/source/evidence content for M5B.
7. Typed refs participate in operation idempotency.
8. Human Work accept/evaluation stores evidence on the evaluation entry.
9. Coordinator direct `done` may store completion evidence without making evidence mandatory.
10. Invalid completion evidence leaves Work status unchanged.
11. Reverse `referenced_by` is derived only and not persisted.
12. Context and live Agent Detail expose bounded typed-reference semantics.
13. Historical typed-reference metadata appears only in Ledger details and does not become current state.
14. Existing M1A/M1B/M2/M3/M5A regressions remain green.

## Review focus

Independent review should challenge:

- whether the Store facade can bypass or duplicate existing transaction semantics;
- whether M1A execution claims still wrap Agent writes with typed refs;
- whether same-operation changed refs conflict;
- whether M5A registration evidence receives the final Artifact refs;
- whether Working Memory is still isolated;
- whether any code infers evidence quality, preferred branch, or Promote policy;
- whether Context stays bounded;
- whether current reverse relations can accidentally read Restore-hidden history.

M5B is complete when these semantics pass the full repository verifier and exact-head independent review. It does not require an M5C unless real dogfood reveals a new stable need.
