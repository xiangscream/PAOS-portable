# M5A Artifact Revision Registration — Implementation Plan

## Goal

Make ordinary PAOS Artifacts usable as an explicit revision lineage without turning PAOS into a file archive or workflow engine.

A later Agent should be able to identify current registered heads, see what changed from an explicitly named predecessor, detect branches, and distinguish current Project state from historical registration evidence.

## Product boundary

M5A adds only:

- explicit generic Artifact `replaces` semantics;
- required `change_summary` for a revision;
- optional opaque external `version_ref`;
- current lineage/head/branch projection;
- bounded lineage Context and live Session Detail projection;
- append-only metadata registration evidence for the dedicated Artifact Add path;
- a Session UI helper that prepares a revision-registration request for the current Runtime.

M5A does not read Artifact files, calculate hashes, validate Git/Feishu revisions, store blobs, choose a preferred branch, require reviews, create Evidence objects, or add a Promote API.

## Write path

Revision registration reuses:

```text
POST /api/projects/{project_id}/sessions/{session_id}/artifacts
schema = paos-session-artifact-add/v1
```

The existing M1A execution-tenure hook stays outside the M5A hook. The Store remains the final authority for revision, idempotency and execution claim.

`agent_working_memory` immediately delegates to M1B and keeps its separate exact-head/Restore rules.

Ordinary Artifact registration through this route stores `artifact_registration_evidence` in the same `session.artifact.added` Ledger event.

## Compatibility boundary

Session Update/Close bundles retain their existing plain Artifact capability. This avoids changing the meaning and evidence shape of an older multi-purpose mutation in M5A.

They cannot carry M5A revision metadata. If an ordinary bundle Artifact contains non-empty `replaces`, `change_summary`, or `version_ref`, the request is rejected before normalization can discard those fields and the caller must use the dedicated Artifact Add route.

Consequently, a plain first-version Artifact created through Update/Close does not gain an M5A registration-evidence snapshot. No historical evidence is fabricated for legacy registrations.

This is an explicit V0 boundary. If real use shows that every first registration needs the same append-only metadata evidence, enrich the existing bundle event in a separate narrow change rather than introducing another Artifact store.

## Current lineage

Current lineage is derived only from current `project.artifacts[]` and excludes `agent_working_memory`.

- one head: linear current registered result;
- multiple heads: valid branch, no automatic preference;
- missing predecessor / self-reference / cycle: corrupt projection;
- a new revision may replace any valid current member, so branching remains an Agent choice rather than a PAOS policy.

Ledger registration evidence is historical only. Restore-hidden generic Artifacts cannot become current heads or new predecessors.

## Context and live UI

Context adds a bounded `artifact_lineages` projection for lineages explicitly related to the current Agent or current Work. It contains metadata only and states that `version_ref` is not PAOS verification.

Session Detail exposes the same server-derived live lineage projection. Browser code consumes that projection rather than independently reconstructing head truth.

The Session “登记新版” helper:

- starts from a server-projected current head;
- pre-fills path/type/purpose/current Work/replaces;
- requires a human-readable change summary;
- treats external version coordinates as optional all-or-none metadata;
- copies a request for the current Runtime instead of submitting as the Agent;
- never reads, copies, refreshes or invents `execution_cycle/context_pack_id`. The Runtime uses the claim already issued in its own Context Pack.

## Acceptance matrix

### Lineage

- linear chain resolves to the explicit leaf;
- branching exposes all heads and never chooses by timestamp;
- missing predecessor/self-cycle/cycle is visible corruption;
- same path without `replaces` does not create lineage;
- unrelated Artifact trees remain separate.

### Registration

- revision with `replaces` requires `change_summary`;
- predecessor must be currently visible and generic;
- optional `version_ref` is stored exactly as coordinates and never marked verified;
- same operation replay does not allocate another Artifact;
- registration evidence equals the committed Artifact metadata.

### Restore

- Restore hiding a later generic revision makes the visible predecessor the current head again;
- hidden revision remains present in append-only registration evidence;
- hidden revision cannot be used as a new generic predecessor;
- no Ledger timestamp participates in current-head selection.

### Continuity and authority

- M1A current execution claim still guards post-takeover generic Artifact writes;
- M1B Working Memory writes keep their own receipt/evidence/head behavior;
- Mailbox and CAT Context remain unaffected.

### UI

- browser renders only server-projected heads;
- corrupt lineage gets no revision button;
- each branch head remains individually selectable;
- copied request contains no execution tenure claim;
- partial external version coordinates are rejected.

## Review focus

Review should attack semantic leakage rather than ask whether M5A could become a richer archive:

1. Does any current-head decision accidentally use Ledger recency or timestamps?
2. Can a Restore-hidden generic Artifact re-enter current lineage?
3. Can generic M5A rules change Working Memory semantics?
4. Can the UI mint or redistribute Runtime tenure?
5. Can bundle normalization silently discard revision metadata?
6. Does `version_ref` wording imply a verification PAOS does not perform?
7. Does Context remain bounded and avoid presenting a branch as resolved?

No M5B typed references, content adapters, assembly or review workflow belong in this package.
