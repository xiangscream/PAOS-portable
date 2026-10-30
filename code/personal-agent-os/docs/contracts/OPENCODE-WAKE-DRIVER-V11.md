# OpenCode Wake Driver V1.1

## Purpose

B2b2 maps the unified PAOS Runtime Wake contract onto one explicit OpenCode
server + session.

The driver is intentionally independent from the existing co-agent CAT
OpenCode sidecar. CAT may remain a durable/event source, but native OpenCode
connectivity is owned here by the Wake layer.

## Revalidated native baseline

B2b2a revalidated OpenCode **1.18.31** independently on two OpenCode runtimes
(s027 main execution, s029 independent review). That historical smoke
established the native turn and failure semantics below.

Historical runtime observations:

1. `POST /session/:id/prompt_async` returns HTTP 204 when the request is
   accepted, but 204 does **not** prove that the model executed.
2. Success must be established from a real assistant turn.
3. Chinese prompts execute correctly when submitted as UTF-8 JSON.
4. A nonexistent exact session returns 404.
5. Provider failure can place the session in `retry` with an assistant
   `APIError`.
6. `POST /session/:id/abort` can clear the retry state.
7. Repeating the same text creates multiple turns; OpenCode provides no
   application-level Wake idempotency for PAOS.
8. Concurrent submissions create multiple turns. The PAOS driver must own
   serialization instead of relying on OpenCode to collapse duplicates.

Current model contract (official documentation): the [Server API](https://dev.opencode.ai/docs/server/)
marks `model` optional in the `/session/:id/message` schema shared by
`prompt_async`; the [Models guide](https://opencode.ai/v2/docs/models) says a
model selected for a session takes precedence over the configured default.
This documents the basis for omitting `model`; fresh-session runtime evidence
is tracked separately in Stage 2 acceptance.

The production driver may optionally pin `expected_version`. The historical
turn baseline above is 1.18.31; directory-scoped read-only validation also ran
against server 1.18.33 with a session created by 1.18.32.

## Binding

Driver name:

```text
opencode
```

Required driver config:

```json
{
  "base_url": "http://127.0.0.1:4102"
}
```

Wake requests intentionally omit the optional `model` field. A legacy
`model` member in driver config does not override the exact session's current
selection.

Optional:

```json
{
  "expected_version": "1.18.31",
  "agent": "build",
  "state_root": "C:/.../wake-native",
  "http_timeout_seconds": 20,
  "idle_wait_timeout_seconds": 120,
  "wake_timeout_seconds": 180,
  "recover_timeout_seconds": 20,
  "poll_seconds": 0.5,
  "lock_timeout_seconds": 5,
  "message_limit": 50
}
```

The PAOS Wake binding's `native_session_id` is the exact OpenCode session id.
The driver never guesses a latest session.

The driver reads `directory` from `GET /session/:id` and sends that exact value
as a URL-encoded query parameter on status, permission, message, prompt and
abort requests. Directory is resolved from the target session, without a new
binding field. Server paths remain unchanged across Windows/WSL clients.

## Setup and probe

Setup validates:

- Runtime id = `opencode`;
- exact native session id exists;
- `/global/health` is healthy;
- exact session and its directory can be read;
- `/session/status?directory=<target>` reports busy/retry or omits the idle session;
- optional expected version matches;
- current state is not `retry`.

Probe is non-turn-producing and maps OpenCode state as follows:

```text
exact session exists + absent from its directory's status map -> idle / online
busy entry  -> online / reachable
retry entry -> degraded / reachable
missing exact session -> offline
unknown transport/protocol state -> unknown (fail closed)
```

OpenCode 1.18.31 intentionally removes idle sessions from
`SessionStatus.list()`; therefore an absent status-map entry is interpreted as
idle **only after exact `GET /session/:id` proves that the bound session still
exists and the status query uses its directory**. The server's default
instance may omit a session that is busy in another directory. Missing or
unavailable directory information produces an explicit error and prevents
binding or prompt submission.

For a busy session, probe also reads `/permission` in the same directory and
reports only that session's pending permission IDs and permission types. It
never replies to permissions or copies command patterns/prompt metadata into
the diagnostic. An unavailable permission list is reported separately from
the established busy state.

## Active/concurrency policy

OpenCode can accept multiple concurrent `prompt_async` requests and will
create multiple turns.

V1.1 therefore chooses a conservative production policy:

```text
defer_until_idle
```

A wake waits for the exact session to become explicitly `idle`. It does not
enqueue while `busy`.

In addition, every binding has a cross-platform local advisory lock:

```text
<state-root>/<project>/<agent>/<binding-fingerprint>/wake.lock
```

Only one PAOS Wake attempt may own that binding's native submission path at a
time. A second caller that cannot obtain the lock within the configured bound
fails **before** any native side effect.

This does not claim that OpenCode itself is serialized; it only guarantees that
PAOS Wake does not create concurrent native wake turns for one binding.

## Deterministic message identity

Each PAOS Wake attempt derives one OpenCode user message id from:

- binding fingerprint;
- PAOS attempt id.

Shape:

```text
msg_paos_<sha256-prefix>
```

The OpenCode schema accepts message ids beginning with `msg`.

The deterministic id is used for **observation/correlation**, not as the
primary idempotency mechanism. B2a's durable PAOS attempt receipt remains the
authority that prevents a second external wake.

## Wake success

Wake flow:

```text
B2a durable attempt = triggering
→ acquire per-binding lock
→ wait for exact session idle
→ final STOP + idle check
→ write native attempt evidence
→ POST /session/:id/prompt_async
   with exact messageID + UTF-8 text; omit model
→ HTTP 204 = accepted only
→ GET exact session message history
→ find user message id
→ find assistant where parentID == that user message id
→ require assistant time.completed and no error
→ woken
```

A successful B2b2 Wake is therefore stronger than an HTTP acceptance receipt:
it proves that a real assistant turn associated with the exact PAOS wake
message completed.

## Native operational evidence

Per binding:

```text
<state-root>/<project>/<agent>/<binding-fingerprint>/
├─ STOP
├─ wake.lock
└─ attempts/
   └─ <attempt-id>.json
```

Attempt evidence stores:

- attempt id;
- binding fingerprint;
- exact OpenCode session id;
- deterministic OpenCode message id;
- source kind/id;
- prompt SHA-256;
- HTTP result;
- assistant message id / finish or bounded error metadata.

The prompt body is never persisted in native Wake evidence.

Existing native evidence for the same PAOS attempt is never used to re-submit
`prompt_async`. The driver may observe the existing message/assistant and
return its result, otherwise it returns uncertain.

## 204 is not success

`prompt_async` HTTP 204 only records:

```text
accepted
```

If no completed assistant turn is observed before the bounded wake timeout, the
result is:

```text
uncertain
```

The driver never upgrades 204 to `woken` by itself.

## Retry and assistant errors

If the exact assistant turn has an error and OpenCode status is `retry`:

```text
Wake result = uncertain
native evidence = retry
```

The driver does not silently wait forever and does not resubmit.

If the assistant turn is completed with a non-retrying error while the session
is no longer retrying:

```text
Wake result = failed
```

## STOP and recover

`stop` creates a binding-scoped STOP file.

It deliberately does **not** call OpenCode abort merely because the exact
session is busy: active work may be unrelated to this Wake request.

Binding replacement is allowed only when the exact session is idle:

```text
safe_to_rebind = native_state == idle
```

`recover` behavior:

- `idle`: clear STOP and return ready;
- `busy`: fail closed as `blocked_busy`; do not abort unattributed work;
- `retry`: require exactly one correlated unresolved PAOS Wake attempt, then call
  the exact session's `POST /abort`, wait boundedly for idle, mark
  `retry_aborted`, then clear STOP;
- missing/offline/unknown: fail visibly.

Recover never replays a prior Wake prompt.

## Relationship to the legacy co-agent OpenCode adapter

The existing co-agent sidecar remains responsible for its CAT marker lifecycle
and CAT-specific consumption/ACK observations.

B2b2 does not import or mutate:

- CAT scope;
- CAT marker claims;
- CAT ownership generation;
- CAT inbox/ACK state;
- the legacy OpenCode binding directory.

The only shared native concept is the documented OpenCode HTTP API.

## Acceptance

1. Driver is registered as `opencode` behind B2a.
2. OpenCode 1.18.31 exact session probe is non-turn-producing.
3. Missing exact session fails visibly.
4. Driver config does not require a model; each request omits `model` and
   inherits the selection of the exact OpenCode session.
5. Chinese UTF-8 prompt reaches the exact native session.
6. HTTP 204 alone never returns `woken`.
7. A real completed assistant child of the deterministic user message is
   required for `woken`.
8. Same PAOS attempt never re-submits a native prompt.
9. A second concurrent PAOS Wake on the same binding cannot submit while the
   first owns the binding lock.
10. Busy exact session is deferred; PAOS does not intentionally enqueue a
    second Wake while active, even if the default instance's status map is empty.
11. Provider retry/APIError produces uncertain, not false success.
12. Recover can use OpenCode abort to clear a **correlated** retry without replaying the prompt.
13. Recover does not abort unattributed/ambiguous retry or unattributed busy work.
14. Same-attempt idempotency is rechecked after acquiring the binding lock.
15. STOP blocks future trigger and unsafe rebind.
16. Prompt body and free-form provider/HTTP response text are absent from native operational evidence.
16. Project revision / Session / Request / Ledger remain unchanged by Wake.
17. B2a/B2b1/B1/A1-A3/full verifier/diff hygiene remain green.
