# Lifecycle Cleanup Runbook

Use official PAOS/CAT actions only. Never edit Project JSON, Ledger, receipt, Close evidence, CAT events, or acknowledgement history directly.

## 1. Inspect first

Read Project, lifecycle findings, Needs Me, relations and Stewardship. Classify each item as:
- current valid fact;
- valid history;
- mechanically actionable cleanup;
- Human semantic decision;
- obsolete technical projection/noise.

`doing + 0 active Agent` is legal. Do not automatically cancel the Work.

## 2. End Agent responsibility

For a current Session that must no longer act, use Human/Coordinator Abandon. Verify the Session becomes terminal and the linked Work is unchanged.

Do not fabricate Agent Close evidence.

## 3. Change Work only as a separate decision

Use the dedicated Work transition/correction action only when the Work itself is semantically done/cancelled/review-ready. Record operation id and receipt, then re-read the Project.

## 4. Retire CAT responsibility independently

Normal Participant removal is intentionally blocked by an unacknowledged inbox.

When the Participant is obsolete but historical unacknowledged Exchanges must remain evidence, use the governance retirement endpoint with a stable operation id and reason. Verify:
- Participant disappears from current membership;
- its runtime projection is removed;
- Exchange created/ack counts do not change;
- `participant.retired` is appended exactly once;
- exact retry replays idempotently.

## 5. Reconcile runtime scopes

Reopen/reconcile may update only hook-scope `expires_at` and remove stale non-member runtime directories. Existing `native_session_id`, `marker_file`, and `stop_file` must remain untouched.

## 6. Post-write verification

After every write:
- re-read the affected object;
- re-run lifecycle/stewardship projection;
- verify receipt/operation id;
- record before/after and recovery path;
- never infer success from optimistic UI state.
