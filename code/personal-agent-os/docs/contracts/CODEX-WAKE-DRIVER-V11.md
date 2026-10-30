# Codex Wake Driver V1.1

## Purpose

The B2b1 Codex driver maps the unified PAOS Runtime Wake contract onto a real Codex Desktop thread.

It is designed for:

- Workstation Mail wake;
- CAT-originated wake;
- Coordinator/system/manual wake;
- the same stable PAOS Agent after Runtime/session rebinding.

It does not create a second task state machine.

## Native transport

The PAOS worker contains the Codex Desktop App Tools client it uses for `tools/list`, `read_thread`, and `send_message_to_thread`. It does not import the legacy co-agent bridge, CAT marker logic, or an app-server fallback.

Each caller supplies its own `CODEX_APP_TOOLS_PIPE_PATH` and `CODEX_THREAD_ID`. The caller thread ID is the App Tools RPC context; the bound `native_session_id` is passed separately as the target argument to `read_thread` and `send_message_to_thread`. The adapter does not discover a latest thread or borrow another session's caller context.

The official [Codex app-server documentation](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server) describes `thread/start` and resuming a thread ID saved by that app-server client. It does not establish app-server as a way to address an existing Desktop thread, so PAOS does not use it as a fallback.

The PAOS driver adds Wake-contract lifecycle, idempotency, STOP/recovery fencing, and Workstation-Mail independence around App Tools.

CAT Room/scope configuration is not required for one PAOS Wake attempt.

## Binding config

Driver name:

```text
codex
```

No driver-specific configuration is required on Windows. When the controller runs in WSL, it also requires:

```json
{
  "python_executable": "C:/.../python.exe",
  "state_root": "C:/.../wake-native"
}
```

Optional:

```json
{
  "wake_timeout_seconds": 600,
  "poll_seconds": 1,
  "startup_timeout_seconds": 3,
  "stop_settle_seconds": 5,
  "probe_timeout_seconds": 30
}
```

Older bindings may still contain `co_agent_root` or `expected_adapter_head`; the current driver does not read either field. The native transport is shipped with PAOS Source rather than loaded from that checkout.

The PAOS binding's `native_session_id` is the Codex Desktop task/thread ID used by the native transport.

When the controller runs in WSL, `python_executable` must point to Windows CPython and `state_root` must be an absolute path shared with Windows. The driver maps Windows drive locators through the existing workstation locator and converts worker paths with `wslpath`.

Both Windows and WSL callers must provide their own `CODEX_APP_TOOLS_PIPE_PATH` and `CODEX_THREAD_ID`. Missing caller capability returns `manual_required` before creating a launch receipt or worker. It must not be filled from another session. A source Runtime without this capability can persist Mail/Notice activation for the target Home's explicitly configured native consumer; activation alone is not delivery.

The WSL driver forwards the caller values to the Windows worker through `WSLENV` (`/w`); unavailable WSL interop prevents launch. WSL cannot prove Windows worker liveness with POSIX PID checks, so unresolved worker evidence remains blocking during recovery.

## Setup

`bind/setup` requires:

1. Windows, or WSL with the Windows worker configuration above;
2. `runtime_id` = `codex` or `codex-desktop`;
3. a non-empty native Codex thread ID;
4. current caller App Tools environment;
5. a successful non-turn-producing native thread probe.

Setup does not create a model turn.

## Probe

Probe starts a short helper process that imports the native Codex transport and runs thread lookup/read only.

Native states:

```text
idle
active
notLoaded
```

map to Wake reachability `online`.

A missing/unreachable thread maps to `offline`; an unsupported status maps to `unknown`.

Probe also includes the latest one-shot worker evidence. A reachable thread with a latest worker result of `failed`, `uncertain`, `timed_out`, `worker_lost`, or invalid evidence is reported as `degraded`.

Probe never sends a model prompt.

## Wake worker

Each Wake attempt first writes a binding-scoped **launch receipt** before `Popen`, then launches one detached worker.

Operational native state is namespaced by the exact Wake binding fingerprint:

```text
<state-root>/<project>/<agent>/<binding-fingerprint>/
├─ STOP
├─ launches/<attempt>.json
└─ attempts/<attempt>.json
```

This prevents evidence or STOP state from an old Codex Thread/binding from contaminating a replacement binding.

The launch receipt survives the gap before worker runtime evidence appears. Recovery treats missing/corrupt/foreign evidence as blocking rather than assuming no worker exists.

The worker receives:

- thread ID in argv;
- attempt ID in argv;
- operational file paths in argv;
- wake prompt **only over stdin**.

For `paos wake trigger --prompt -`, the CLI reads raw stdin bytes and decodes UTF-8 first, with strict native-Windows encoding fallbacks. This avoids surrogateescape corruption for normal non-ASCII Mail/CAT text. UTF-8 `@FILE` remains the deterministic fallback for environments with unusual native pipe encoding.

The parent→Codex-worker pipe has a stricter internal contract: the parent serializes the request as UTF-8 JSON, and the worker reads `sys.stdin.buffer` and decodes strict `utf-8-sig`. It never re-decodes that pipe through the worker process' inherited Windows text codepage.

The prompt is not written to:

- PAOS Wake attempt state;
- worker argv;
- a prompt file;
- worker runtime evidence.

Worker evidence stores only `prompt_sha256`.

### Active thread behavior

If the native thread is `active`, the worker does not inject concurrently.

It records:

```text
deferred_active
```

and waits locally until:

- the thread becomes `idle` / `notLoaded`;
- STOP appears;
- timeout expires.

At the final wake boundary it checks STOP again before calling the native transport.

This keeps activation/continuation behavior deterministic without requiring the PAOS controller to poll model turns.

### Native side effect

Before the native call the worker records:

```text
triggering_native
```

Then it calls the native Codex client once.

If an `ActiveThreadWriter` race occurs, the worker returns to deferred waiting.

A generic exception at this boundary is recorded as:

```text
uncertain
```

because the native side may have accepted work before the transport error became visible.

Success records:

```text
woken
```

The driver returns `accepted` when the detached worker has published startup evidence. The B2a controller preserves `accepted` in its attempt and last-wake receipts; it does not label this `woken`. The worker may still be `waiting_runtime`, `deferred_active`, or `triggering_native`. Its later `woken` evidence confirms native transport acceptance only, not Mail consumption or business completion. Re-reading the same controller attempt does not launch another worker or upgrade its historical acceptance receipt.

## STOP and recovery

`paos wake stop` creates a driver-local STOP fence.

The worker checks this fence:

- on every wait loop;
- immediately before the native side effect.

`recover` never clears STOP while:

- an accepted/prepared launch has no trustworthy runtime evidence;
- launch/runtime evidence is corrupt or belongs to a different binding/thread;
- an accepted worker is still live;
- worker liveness cannot be safely disproved.

If a valid pending worker PID is positively dead, recovery marks its runtime evidence:

```text
worker_lost
```

On Windows, worker liveness is checked with native `OpenProcess + GetExitCodeProcess`, not `os.kill(pid, 0)`. This avoids CPython/Windows `SystemError` behavior while keeping unexpected/access-denied results fail-closed as unknown.

If a launch receipt is `accepted` but the worker dies before publishing runtime evidence, recovery may mark the launch `worker_lost_before_runtime_evidence` once the PID is positively dead. Missing evidence while the PID is live or unverifiable still blocks recovery.

and may continue.

If launch/runtime evidence remains unresolved, recovery returns:

```text
blocked_worker_evidence
```

and leaves STOP in place.

`setup` follows the same rule: it never blindly deletes an existing STOP. It may clear a stale STOP only after binding-scoped evidence proves there is no unresolved worker.

Binding replacement also requires the old driver's `stop` result to report `safe_to_rebind=true`; otherwise PAOS keeps the old binding and refuses replacement.

This prevents:

```text
stop
→ immediate recover
→ old accepted worker crosses the wake boundary afterward
```

Recovery never replays a B2a uncertain Wake attempt.

## Relationship to the legacy co-agent adapter

The PAOS Wake worker no longer depends on the co-agent Codex adapter. It does not replace or modify the existing CAT-specific:

- Event Bridge;
- current CAT binding pointer;
- marker generation fence;
- recovery watcher;
- Stop-hook continuation router.

Those remain responsible for existing CAT marker automation until B2c explicitly decides how Mail/CAT orchestration should use the unified Wake contract.

No B2b1 code imports or mutates CAT business content.

## Evidence baseline

The Codex transport is versioned with the PAOS Source revision. Runtime acceptance must report the exact PAOS Source revision used; it must not infer a Codex product/API support guarantee from this local adapter.

## Acceptance

1. Codex driver is registered behind the B2a contract.
2. Setup/probe produce no model turn.
3. A real Desktop native thread is identified explicitly; no “latest thread” guessing.
4. Idle real thread receives exactly one continuation.
5. Active real thread is not concurrently injected; delivery occurs after the idle boundary.
6. Wake prompt body is absent from PAOS attempt and worker runtime files.
7. Same B2a `attempt_id` replay does not launch a second worker/native turn.
8. STOP before final boundary prevents native wake.
9. Controller preserves a driver's explicit `uncertain` result as `uncertain`, never collapsing it to `failed`.
10. A launch receipt exists before worker creation and missing runtime evidence blocks recovery.
11. Corrupt/foreign launch or runtime evidence blocks recovery.
12. Recovery does not clear STOP while an accepted worker is live/unverifiable or evidence is unresolved.
13. `setup` never blindly clears STOP; rebind requires `safe_to_rebind=true`.
14. A positively dead pending worker becomes `worker_lost`.
15. Runtime evidence is scoped to the exact binding fingerprint/thread so old Thread evidence cannot affect a new binding.
16. Driver probe surfaces latest native worker failure/degradation.
17. `stop` does not kill unknown PIDs.
18. Project revision / Session / Request / Ledger remain unchanged by Wake operations.
19. Existing co-agent CAT Event Bridge remains operational and unchanged.
20. B2a/B1/A1-A3/full verifier/diff hygiene stay green.
