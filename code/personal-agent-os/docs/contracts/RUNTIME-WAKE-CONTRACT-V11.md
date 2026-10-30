# Runtime Wake Contract V1.1

## Purpose

The V1.1 **Wakeup layer（唤醒器）** exists for one narrow reason:

> ask the currently bound native Runtime to continue the same PAOS Agent.

It is a Runtime connectivity layer, not a task engine.

Wakeup does not own:

- Project / Work / Request / Decision truth;
- Agent TODO state;
- Workstation Mail content;
- CAT conversation content;
- task completion;
- review / acceptance;
- Coordinator routing policy.

A normal wake prompt should therefore be small and referential:

```text
检查 Workstation mailbox 或 CAT，并从当前工位继续。
```

The durable Mail/CAT fact must exist **before** wake is requested.

## Layers

V1.1 keeps three facts separate:

```text
durable communication state
    Workstation Mail / CAT

Runtime connectivity state
    Wake binding / probe / wake attempt

work execution state
    TODO / PAOS Work / Request / review
```

Therefore:

```text
Mail persisted != Runtime woken
Runtime woken != Agent read
Agent read != work completed
work completed != accepted
```

## Unified Wake operations

Every native Runtime implementation must fit the same outward contract:

```text
bind / setup
status
probe
wake
recover
stop
unbind
test
```

CLI names in B2a:

```text
paos wake bind
paos wake status
paos wake probe
paos wake trigger
paos wake recover
paos wake stop
paos wake unbind
paos wake test
```

`trigger` is the CLI verb for the contract's `wake` operation.

### bind / setup

Bind one stable PAOS Agent to the currently intended native Runtime and one Wake driver.

Binding records:

- Project ID;
- Agent ID;
- runtime ID;
- native session/thread ID;
- driver name;
- driver-specific operational config;
- immutable binding fingerprint.

A different binding cannot replace the current one accidentally. Replacement is explicit.

Bindings are operational data, not Project governance facts.

### status

Read persisted operational facts only.

Status must not create a model turn and must not silently probe or repair.

At minimum it exposes:

- bound/unbound/stopped state;
- runtime/native-session locator;
- driver;
- latest probe;
- latest wake;
- latest recover/stop/test;
- in-flight attempts;
- uncertain attempts.

Driver config values are not echoed by the status view.

### probe

Ask the native implementation whether the bound Runtime is reachable/ready without creating a model turn.

Standard reachability vocabulary may include:

- `online`
- `offline`
- `degraded`
- `unknown`
- `manual`

Runtime-specific drivers can return additional detail, but callers must not infer Work progress from reachability.

### wake

Before entering any external Runtime side effect, the controller persists an attempt in:

```text
state = triggering
```

Only then may the Runtime driver attempt continuation.

Controller receipts after the driver returns:

- `accepted` — an asynchronous driver accepted the attempt; native delivery remains pending or unknown;
- `woken` — driver reported its native delivery success boundary;
- `failed` — driver reported a definite failure;
- `manual_required` — this binding cannot be woken automatically;
- `uncertain` — an exception or recovery boundary means the external result cannot be known safely.

Neither receipt means that the model read Mail/CAT or completed work. Codex startup acceptance stays `accepted`; later native delivery is read from its binding-scoped worker evidence without replaying or rewriting the original controller receipt.

### wake idempotency

Each wake attempt has a stable `attempt_id`.

The durable attempt identity includes:

- binding fingerprint;
- source kind;
- source ID;
- wake prompt hash.

The prompt body is not copied into wake operational state.

Replaying the same attempt ID:

- with the same identity returns the existing receipt;
- never automatically creates a second external wake;
- with different source/prompt/binding fails visibly.

This is specifically designed to avoid duplicate model turns.

### crash safety

The controller writes `triggering` before the external side effect.

If the controller disappears after the native Runtime accepted the wake but before the final result was persisted, the attempt can remain `triggering`.

That state must never be blindly replayed.

`recover` converts persisted `triggering` attempts to `uncertain` before repairing connectivity. A new model turn requires a new explicit attempt ID after the operator/Agent decides that another wake is appropriate.

### recover

Repair Runtime connectivity without intentionally creating a model turn.

Examples for future native drivers:

- restart/rebind a sidecar;
- detect and clear a stale PID;
- reconnect to a native server;
- reinstall/revalidate a hook/heartbeat bridge;
- then probe.

Recovery must not replay uncertain wake attempts.

### stop / unbind

`stop` stops driver-owned runtime connectivity components when applicable but keeps the binding.

`unbind` stops the driver, archives the binding, and removes the current binding.

If stop fails, normal unbind fails closed. If a driver reports `safe_to_rebind=false`, normal unbind also fails closed so unresolved Runtime work cannot be orphaned. Force-unbind is an explicit operator action and must report that it was forced.

### test

A non-turn-producing driver self-test.

`test` must never be implemented as “send a harmless model prompt.” If a native Runtime cannot test connectivity without producing a turn, it should report that limitation.

## Operational storage

Per Project:

```text
<Project Root>/.paos/wakeup/
├─ bindings/
│  └─ <agent>.json
├─ state/
│  └─ <agent>.json
├─ attempts/
│  └─ <agent>/
│     └─ <attempt>.json
└─ archive/
   └─ <agent>/
      └─ <old-binding>.json
```

This is local operational metadata.

It is not:

- Project JSON;
- Ledger;
- Workstation TODO;
- CAT;
- Workstation Mail.

The controller never advances PAOS revision.

## Binding and PAOS Runtime facts

PAOS Session/Cycle remains the canonical record of which Runtime the Agent says it is currently using.

The Wake binding is an operational locator used to reach that Runtime.

B2a allows `paos wake bind` to derive `runtime_id` and native session ID from current Session Detail, but it stores an explicit binding snapshot afterward.

Runtime handover can therefore make a Wake binding stale. Native integration work must make rebind/recovery explicit rather than silently pretending the old native session is current.

## Driver boundary

B2a introduces a new Wake driver interface instead of extending the old Collaboration Watcher `collab_adapters` contract.

The old adapters remain legacy compatibility for their existing watcher/run semantics.

New native Runtime work must target the Wake contract.

Internal driver methods:

```text
setup(binding)
probe(binding)
wake(binding, wake_prompt, attempt_id, source_kind, source_id)
recover(binding)
stop(binding)
test(binding)
```

B2a shipped:

- `mock` — deterministic contract testing;
- `manual` — explicit no-automation fallback.

B2b1/B2b2 add production native drivers:

- `codex` — Codex Desktop same-thread wake via the hardened native transport already maintained in co-agent-2; see `CODEX-WAKE-DRIVER-V11.md`.
- `opencode` — exact OpenCode server/session wake inheriting that session's selected model, with per-binding serialization, HTTP-204-as-accepted-only semantics, and real assistant-turn observation; see `OPENCODE-WAKE-DRIVER-V11.md`.

DeepSeek Harness is intentionally outside V1.1 scope. OpenCode is the primary
Agent Runtime and Codex is the secondary validated Runtime.

B2c builds an Agent-first activation layer **above** this contract; see
`AGENT-ACTIVATION-V11.md`. Normal orchestration targets a stable Agent and lets
the Wake binding hide the concrete Runtime.

## Native B2 status

V1.1 has two accepted production drivers behind this contract.

### Codex

B2b1 now implements this path. It reuses co-agent-2's hardened `CodexDesktop` native transport but does not require a CAT Room/scope for a Wake attempt.

- Native thread lookup/probe is non-turn-producing.
- One-shot wake workers defer an active thread until an idle boundary and then create exactly one continuation.
- Prompt content is sent to the worker over stdin and is not stored in PAOS Wake operational state.
- STOP is a hard local fence checked immediately before the native side effect.
- Recovery will not clear STOP while an accepted worker can still cross that boundary.
- co-agent adapter source location is explicit in driver config; an optional expected adapter HEAD can pin the validated native implementation.

The older CAT Event Bridge + Stop-hook path remains in co-agent-2 for CAT marker automation. The PAOS Wake driver does not replace or rewrite that system.

### OpenCode

B2b2a revalidated OpenCode 1.18.31 independently on two OpenCode runtimes, and
B2b2 implements the production driver.

Key semantics:

- exact `base_url + native_session_id`; never guess the latest session;
- `prompt_async` omits `model` so OpenCode uses the selection of the exact bound session;
- `prompt_async` HTTP 204 means accepted only;
- success requires a real completed assistant message whose `parentID` is the
  deterministic PAOS Wake user message id;
- duplicate/concurrent native prompts create multiple turns, so PAOS serializes
  Wake per binding and defers busy sessions until idle;
- retry/APIError is uncertain; explicit recover may abort retry, but never
  replays the prompt;
- STOP does not abort unattributed busy work.

### DeepSeek Harness

DSH native Wake support is intentionally skipped for V1.1. Its upstream
lifecycle is not stable enough to justify another production driver when
OpenCode already covers the primary Agent Runtime and Codex provides a second
independent Runtime shape.

This is a scope decision, not an unresolved acceptance blocker.


## Source references

Wake attempts may identify why continuation was requested:

- `mail:<message-id>`
- `cat:<exchange-id>`
- `manual`
- `system`

The Wake controller stores the reference and prompt hash, not the referenced message/exchange body.

## Acceptance for B2a

1. Bind/status/probe/wake/recover/stop/unbind/test share one contract.
2. Operational files live outside PAOS governance state.
3. CLI accesses PAOS via GET only to resolve Project/Session locators.
4. Wake attempt is durable in `triggering` before entering driver side effects.
5. Same attempt ID cannot create a second external wake.
6. Same attempt ID with changed source/prompt fails visibly.
7. Driver exceptions become `uncertain`, not false definite failure.
8. Recovery never automatically replays `triggering/uncertain` attempts.
9. status does not expose driver config values.
10. bind replacement is explicit and archives the previous binding.
11. manual driver accurately reports that external wake is unavailable.
12. mock driver proves the contract under tests.
13. Existing Collaboration Watcher behavior remains untouched.
14. Mail / Responsibility Mailbox / A1-A3 regressions and full verifier remain green.
