# Human-Agent entry and Runtime self-report v1

Status: S2-1 implementation contract.

## Product result

A Human can create a PAOS Agent without inventing the native Runtime, model, native session title or self-position that will eventually execute it.

The Human supplies the work intent PAOS actually needs at Open time: an existing Work, Identity, Mission/Done When, Context level and optional materials/Requests. PAOS creates the durable Agent in `active` and issues its Context Pack / Prompt. A newly opened Agent can start working immediately: Open is the only entry procedure, and there is no claim, Cycle or Acknowledge step that gates it.

The native Agent reports its own execution environment when it acknowledges. Acknowledge is optional self-report written as evidence, not a permit: it may be called at any time on a Session that has not been terminated, and it may be called more than once. If the Agent has no Runtime binding yet, Acknowledge must not succeed until the caller supplies a non-empty `runtime_id` plus a `runtime_session` object. `model_id` remains optional. The same Acknowledge mutation that records the reported Runtime binding also moves the Session from `pending_ack` to `active` when the state came from older data; there is no second repair write.

## Compatibility

The `paos-session-open/v1` schema remains backward compatible with older callers that explicitly provide `runtime_id`, `model_id` or `agent_label`. S2-1 removes the requirement to provide them; it does not reject those fields.

A pre-S2 Agent that was already opened with a Runtime binding and has never entered guarded Runtime handover may still Acknowledge without redundantly reporting the same binding. This compatibility path must not weaken M1A takeover: after a guarded Continue, the incoming Runtime is still required to report a fresh Runtime binding together with the current execution claim.

## Human and Agent authority

Open and Continue remain Human actions. Continue keeps the same durable `sNNN` and creates a new Cycle; it never creates a successor Agent ID. A Session that has just been opened or continued already carries responsibility, so no further Human action is needed to hand its Prompt to the native Agent.

Acknowledge, Update, Artifact registration and Close are Agent/Coordinator execution actions governed by the existing execution-tenure contract. Of these only Acknowledge is optional; the others are what a live Session does. Runtime self-report is execution metadata, not a new authentication token or identity subsystem.

The Agent CLI must not gain Human-only Continue, Reactivate, Work review, Decision review, Coordinator grant/revoke/replace or Restore commands as a side effect of this package.

## UI rule

The normal Project `+ Agent` / Start Agent launcher must not ask the Human for Runtime or show implementation-future text such as `H1 self-report`. The generated Open payload must omit empty Runtime/model/self-position fields instead of writing placeholder values such as `Manual` or `unknown`.

After Open, the copied Prompt and normal Ack path tell the native Agent to report its actual Runtime binding. Human correction/admin paths remain separate and are not the normal creation workflow. Prompt copy, `Update` and `Close` do not wait for Acknowledge.

## Failure semantics

If an unbound Agent attempts Acknowledge without `runtime_id`, the operation fails explicitly and does not advance Project revision, Session status or Cycle evidence.

If a Runtime binding is supplied, it is validated before the Store commit and is written atomically with the Acknowledge transition. An invalid or stale takeover execution claim continues to fail under the existing M1A Store guard.

## S2-1 acceptance

S2-1 is accepted only when all of the following are green on the exact candidate HEAD:

1. `WorkflowService.open_session()` succeeds when `runtime_id`, `model_id` and `agent_label` are absent and creates an unbound Agent that can already Update and Close without Acknowledge;
2. an unbound Agent cannot Acknowledge without reporting a Runtime and a failed attempt leaves revision unchanged;
3. an Ack with Runtime self-report atomically binds `runtime_id`, optional `model_id` and `runtime_session`, and records the Acknowledge evidence;
4. an older explicit-runtime Open remains accepted;
5. the Project Agent launcher contains no Runtime input / future implementation wording, and its Open payload does not synthesize Runtime/model/self-position placeholders;
6. M1A takeover / stale-claim tests, Session lifecycle tests and current Open/Ack HTTP tests remain green;
7. the current onboarding text describes same-Agent / new-Cycle Continue and does not reintroduce successor-Session guidance;
8. `scripts/verify.py` and `git diff --check` are clean, followed by a real browser Start Agent → copied Prompt → native Agent Ack smoke test on the candidate build.

## Not in S2-1

- Ready-for-Review normal UI wiring: S2-2;
- Agent CLI golden-path expansion and base URL configuration: S2-3;
- compact start/read payloads and detail expansion: later S2 package;
- wholesale WorkflowService/MRO decomposition: later S2 explicit-composition package;
- CAT consumer ownership/recovery: S5;
- Project information architecture / visual polish: S4;
- new authentication/RBAC or Runtime orchestration.
