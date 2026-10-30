# Artifact Evidence References V0

## Purpose

PAOS records work results and the formal judgments that depend on them. This contract adds enough reference semantics to answer three questions without introducing a general relation graph:

- What does this Artifact discuss or review?
- What sources contributed to this Artifact?
- Which formal Artifacts support this Decision or Work judgment?

References preserve work meaning. They do not establish truth, quality, review status, or Human approval.

## Core distinctions

An **Artifact** is a formally registered work result or material.

A **subject reference** identifies the Artifact that another Artifact discusses, analyzes, or reviews.

A **source reference** records where an Artifact came from. A source can be another PAOS Artifact, a CAT Exchange coordinate, or an external locator.

An **evidence reference** records which formal PAOS Artifacts a Decision or Work judgment used as evidence.

These relations are not interchangeable:

```text
Artifact exists
!= Evidence for every claim
!= Reviewed
!= Human approved
```

Canonical means the record was formally registered in PAOS. It does not mean the content is objectively true.

## Artifact references

Ordinary Artifacts may carry two optional arrays.

### `subject_refs`

V0 accepts only PAOS Artifact references:

```json
{
  "subject_refs": [
    {"kind": "artifact", "id": "3002-a017"}
  ]
}
```

Use this when the new Artifact is about another Artifact. A review report, for example, can belong to one Work while its `subject_refs` identify the exact Artifact it reviewed.

### `source_refs`

V0 accepts three source kinds.

PAOS Artifact:

```json
{"kind": "artifact", "id": "3002-a011"}
```

CAT Exchange coordinate:

```json
{
  "kind": "cat_exchange",
  "room_id": "room-0123456789ab",
  "exchange_id": "x-123"
}
```

External locator:

```json
{
  "kind": "external",
  "provider": "web",
  "locator": "https://example.test/source"
}
```

CAT and external references are provenance coordinates only. PAOS V0 does not contact the source, verify availability, copy the source body, or promote that source to formal Evidence automatically.

An external or CAT source that must serve as formal evidence should first be represented by an appropriate PAOS Artifact.

## Evidence references

V0 `evidence_refs` accepts only currently visible ordinary PAOS Artifacts:

```json
{
  "evidence_refs": [
    {"kind": "artifact", "id": "3002-a021"}
  ]
}
```

Agent Working Memory is continuity state and cannot be used as `subject_refs`, Artifact-backed `source_refs`, or `evidence_refs`.

A Restore-hidden Artifact is historical registration evidence, not a valid target for a new current reference.

### Decision proposal

A Decision proposal may carry `evidence_refs`. The references belong to the proposal itself.

Human accept/reject changes Decision status but does not append, replace, or retarget the proposal evidence.

### Work completion and evaluation

Evidence is optional. PAOS does not require a Technical Review or evidence count before a Work can finish.

A Human Work accept/evaluation may record `evidence_refs` on the resulting evaluation entry.

A Coordinator transition to `done` may record `completion_evidence_refs` on the Work.

Work cancellation and Decision Human review do not create a second evidence channel.

## Referential integrity

Supported writes validate Artifact references inside the same canonical mutation that records the new Artifact or judgment.

A reference is rejected when it points to:

- an Artifact outside the current Project;
- an Artifact that is not currently visible;
- Agent Working Memory;
- an unsupported reference kind;
- malformed or duplicate coordinates.

A failed reference validation commits nothing from that mutation.

Typed references participate in the operation request identity. Replaying the same `operation_id` with the same references returns the original result; changing the references under the same `operation_id` conflicts instead of mutating history.

## Artifact revision semantics

M5A lineage remains authoritative for Artifact evolution.

```text
a017 -> a021
```

If a Review or Decision references `a017`, creating `a021` does not change that reference. PAOS never retargets an existing reference to the current lineage head.

`replaces` describes Artifact evolution. Typed references describe subject, source, and evidence relationships. They are separate semantics.

## Restore and history

Current reference truth is derived from the current Project projection.

When a supported mutation records non-empty typed references, its Ledger event also stores a small `typed_reference_evidence` metadata snapshot. This allows later inspection of what that historical mutation declared.

Ledger evidence does not restore hidden objects, choose current Artifact heads, or recreate current references after Restore.

## Reverse projection

`referenced_by` is derived at read time from current Project objects.

PAOS does not persist a reverse relation graph. A projection may show that an Artifact is currently used as a subject, source, Decision evidence, Work completion evidence, or Work evaluation evidence.

Malformed legacy/manual references are surfaced as projection issues. The projection does not repair them or choose replacement targets.

## Context

Context Packs and live Agent Detail may include a bounded typed-reference projection for the current Agent and Work.

The projection favors explicit IDs and compact relationships. It does not include source bodies, CAT chat bodies, external page contents, or an inferred evidence ranking.

Current PAOS objects remain authoritative over an older Context Pack snapshot.

## Promote

Promote remains an Agent practice:

```text
exploration
-> Agent decides a result deserves formal registration
-> chooses an existing PAOS object/action
```

There is no `/promote` API, automatic source ingestion, automatic evidence selection, or approval pipeline in this contract.

## Out of scope

V0 does not add:

- a top-level `evidence[]` entity;
- a generic Relation object or persisted graph;
- automatic evidence scoring or ranking;
- CAT, Git, Feishu, or web source verification;
- content hashing or Blob storage;
- automatic Artifact-head selection;
- mandatory Technical Review;
- automatic Promote;
- automatic retargeting after Artifact replacement.
