# Artifact Lineage V0

## Purpose

Artifact Lineage records how formal work results evolve so a later Agent can identify the current registered version, understand the latest change, and inspect earlier registrations when needed.

It does not archive file bytes, verify external revisions, decide which branch is better, require review, or define a Promote workflow.

## Artifact meaning

An Artifact is a formally registered work result. Its `source_session_id` identifies the PAOS Agent that registered it; it does not claim sole authorship.

`path` is a readable locator. It does not prove that the current bytes at that path are identical to the bytes present when the Artifact was registered.

Generic Artifact revision metadata is:

```json
{
  "replaces": "3002-a017",
  "change_summary": "根据实测结果修正延迟结论，并删除未验证声明",
  "version_ref": {
    "provider": "git",
    "revision": "<revision>",
    "path": "docs/report.md"
  }
}
```

`version_ref` is an opaque external version coordinate. PAOS V0 does not fetch the provider, calculate a digest, or assert that the external revision is currently resolvable.

## Registration contract

Generic Artifact revision metadata uses the existing Session Artifact Add endpoint:

```text
POST /api/projects/{project_id}/sessions/{session_id}/artifacts
schema = paos-session-artifact-add/v1
```

A generic Artifact with non-empty `replaces` must include a non-empty `change_summary`.

`version_ref`, when present, contains exactly `provider`, `revision`, and `path`, each as a non-empty string.

Session Update and Close bundles retain their existing plain Artifact capability. They must not carry generic `replaces`, `change_summary`, or `version_ref`; revision registration uses the dedicated Artifact Add route so the lineage metadata cannot be silently discarded.

`agent_working_memory` remains governed exclusively by `AGENT-WORKING-MEMORY-V0.md`. Generic Artifact rules do not change its exact-head or Restore semantics.

## Current lineage

Current generic lineage is derived only from the current `project.artifacts[]` projection.

A non-empty `replaces` must reference a currently visible generic Artifact in the same Project. It cannot target Agent Working Memory. Existing malformed lineage is surfaced as corruption instead of being extended.

A new generic Artifact may replace any valid current member. Generic lineage does not require exact-head replacement, so explicit branching is valid:

```text
a001 -> a004 -> a009
            \-> a010
```

Both `a009` and `a010` are current registered heads. PAOS does not choose between them by timestamp, Artifact ID, path modification time, or recent Agent activity.

Multiple unrelated Artifact trees remain separate lineages. There is no Project-wide single latest Artifact.

## Registered head versus file state

A lineage head means "current registered version". It is not a statement about the current bytes at the Artifact path.

If a file changes without a new Artifact registration, PAOS does not infer that change. A missing `version_ref` therefore means the Artifact is a current locator-based work result; it does not promise historical-byte recovery.

## Historical registration evidence

A generic Artifact created through the dedicated Artifact Add route stores an exact metadata snapshot in the same `session.artifact.added` Ledger event:

```text
Ledger.details.artifact_registration_evidence
```

The snapshot contains registration metadata only: Artifact ID, path, type, purpose, Work references, registrant, `replaces`, `change_summary`, optional `version_ref`, and creation time. It contains no file body.

This evidence answers "what was registered historically". It never participates in current-head selection.

Restore may remove a later Artifact from current `project.artifacts[]` while append-only registration evidence remains. That hidden registration is historical only and must not be resurrected as a current head or accepted as the predecessor of a new generic revision.

Plain Artifact registrations made through the older Update/Close bundle path retain their existing behavior and do not gain synthetic historical snapshots. PAOS does not backfill evidence it never recorded.

## Context

Context exposes a bounded index of lineages explicitly related to the current Agent or current Work. It prioritizes current registered heads, the latest explicit `change_summary`, optional external `version_ref`, and short lineage IDs.

Historical file bodies are never embedded. A branched lineage is shown as branched and is not resolved automatically.

Context wording must distinguish:

- current registered head;
- active path;
- external version reference that PAOS has not verified.

## Invariants

M5A protects these facts:

- revision registration with `replaces` requires `change_summary`;
- predecessor must be a currently visible generic Artifact;
- malformed/cyclic lineage is not silently extended;
- explicit branches are preserved and never resolved by recency;
- stale Runtime writes remain subject to M1A execution tenure;
- repeated operation IDs remain idempotent under the existing Store contract;
- Restore-hidden generic Artifacts remain historical rather than current;
- `agent_working_memory` retains its separate M1B lineage contract;
- `version_ref` never becomes an implicit PAOS verification claim.

M5A does not decide when an Agent should create a new revision, whether a result is correct, whether a review is required, or which branch should win.
