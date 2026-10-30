# Native Agent Workstation Provision V1.1

## Result

Opening a new PAOS Session through the local HTTP Session Open endpoint now also attempts to provision that Agent's stable Project-local workstation:

```text
<Project Root>/Workstations/<agent-id>/
├─ ENTRY.md
├─ TODO.md
└─ mailbox/
```

This is one user operation, but it is intentionally **not** represented as one cross-storage atomic transaction.

## Storage boundary

The ordering is fixed:

```text
validate Session Open
→ commit PAOS Session + Context Pack + Ledger/receipt
→ read the committed Session/Project
→ provision the local Project Vault workstation
→ return Session receipt + workstation result
```

PAOS governance state remains owned by `ProjectStore`. Project Vault files remain filesystem state.

The domain-level `WorkflowService.open_session()` does not touch the Project Vault. Native provisioning is owned by the local-server orchestration layer.

## Why Session commits first

There is no safe atomic transaction across the PAOS governance store and an arbitrary Project Vault on Windows/WSL/local disks.

Pretending otherwise would make recovery ambiguous.

Instead:

- if Session Open fails, no workstation provisioning is attempted;
- if Session Open succeeds and workstation provisioning succeeds, the response reports `workstation.status=ready`;
- if Session Open succeeds but provisioning fails, the Session remains committed and the response reports `workstation.status=repair_required`;
- the response always states `session_committed=true` and `atomic_with_session=false` for provisioning results.

A workstation failure must never trigger a compensating Session delete.

## Recovery and idempotency

The Session Open operation already has an `operation_id` idempotency receipt.

Retrying the same Open payload with the same operation ID:

1. resolves the already-created Session instead of creating another one;
2. re-attempts workstation provisioning;
3. preserves an existing edited `ENTRY.md` / `TODO.md`;
4. can finish a previously interrupted generated-legacy ENTRY retirement.

The response includes the explicit recovery command:

```text
paos workstation init <project> <agent>
```

This allows repair without replaying Session governance when the operator already knows the Session ID.

## Provision result

Schema:

```text
paos-session-workstation-provision/v1
```

Ready:

```json
{
  "status": "ready",
  "ready": true,
  "session_committed": true,
  "atomic_with_session": false,
  "workstation_path": "...",
  "entry_path": "...",
  "entry_markdown": "# Agent Workstation ...",
  "todo_path": "...",
  "mailbox_path": "..."
}
```

Repair required:

```json
{
  "status": "repair_required",
  "ready": false,
  "session_committed": true,
  "atomic_with_session": false,
  "error_code": "...",
  "error": "...",
  "retry_command": "paos workstation init ..."
}
```

The ready result also returns the exact current `ENTRY.md` body as `entry_markdown`, so a caller can immediately hand the stable entry prompt to the selected Runtime without inventing a second prompt source.

A missing Project `root_path` is an explicit repair-required result, not silent success.

An unknown or human-edited legacy `.paos/agents/<agent>/ENTRY.md` continues to fail closed under the A1 migration contract.

Unexpected post-commit filesystem errors are reported as `workstation_provision_internal_error`; the Session is not rolled back or recreated.

## Scope

A2 does not:

- change Session Open authority or add a new Human/Coordinator permission;
- add a second Session/Open API;
- move workstation files into PAOS private-data;
- make TODO a PAOS governance source;
- add Workflow Library or Skill Library behavior;
- add Mailbox delivery semantics;
- change Cycle-bound materialization.

It upgrades the existing canonical Session Open surface so every caller of that surface gets the same workstation provisioning behavior.

## Acceptance

A2 is accepted when the exact candidate HEAD proves:

1. direct domain `WorkflowService.open_session()` still performs no Project Vault writes;
2. HTTP Session Open with a valid `root_path` creates `ENTRY.md`, `TODO.md`, and `mailbox/`;
3. Open response reports the non-atomic storage boundary honestly and exposes the exact stable `ENTRY.md` body for Runtime handoff;
4. same-operation retry reuses the existing Session and repairs a missing workstation without increasing Project revision;
5. missing `root_path` returns committed Session + explicit repair-required workstation state;
6. human/unknown legacy ENTRY remains untouched and blocks only workstation provisioning;
7. an unexpected post-commit provisioning exception returns explicit partial success rather than fake rollback;
8. A1 fixed-workstation and Session lifecycle regressions remain green;
9. full `python scripts/verify.py` and `git diff main...HEAD --check` pass;
10. at least one real local smoke proves a new Session creates a workstation under a Project root containing spaces and non-ASCII characters.
