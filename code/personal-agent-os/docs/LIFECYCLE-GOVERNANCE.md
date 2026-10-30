# Lifecycle Governance

PAOS separates durable Project state from Agent execution state. A Project keeps
its Requests, Decisions and Cycles whether or not any Agent Session is currently
running. Facts that look inconsistent should be visible to the user and to a
future Project Coordinator rather than silently repaired.

## Read-only findings

`GET /api/projects/<project_id>/lifecycle-findings`

returns a pure projection (`paos-lifecycle-findings/v1`). It does not mutate the
Project and it does not add anything to Needs Me.

G1 intentionally reports only mechanically provable facts:

- `INACTIVE_COORDINATOR` — Project coordinator points at a missing/terminal Session.
- `STALE_ASSIGNMENT_TARGET` — open Assignment targets a missing/terminal Session.

These are **governance signals**, not automatic mutation instructions. PAOS does
not infer that an old Decision is obsolete, or that the user must intervene.

## G2: Close vs Abandon

PAOS has two different Session-ending semantics:

- **Close** is Agent testimony. `POST /api/projects/<pid>/sessions/<sid>/close` records an
  Agent-authored `close_result` on the current Cycle. Formal acceptance of the
  responsibility is a separate Human/Coordinator decision.
- **Abandon** is governance. `POST /api/projects/<pid>/sessions/<sid>/abandon` ends an
  active/pending Session because management no longer wants that Agent to carry the
  responsibility. No Agent `close_result` is fabricated.
- A Project Coordinator can abandon another worker through
  `POST /api/projects/<pid>/coordinator/sessions/<sid>/abandon`. A Coordinator cannot
  abandon itself. Human abandon also refuses the current Coordinator until it is explicitly
  revoked or replaced.

Abandon evidence lives on the Cycle:

```text
end_kind = human_abandon | coordinator_abandon
end_reason = <required reason>
abandon_operation_id = <operation id>
close_result = null
```

The durable Ledger event is `session.abandoned`. Historical JSON is not rewritten.

### Idempotency and audit

Abandon uses the same `mutate_v2` revision/idempotency/receipt path as other narrow writes.
Replaying the same operation returns the original receipt without creating another Ledger
event or advancing revision.
