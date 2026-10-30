# WorkBuddy native Wake

This page preserves the historical Wake controller/Notice-consumer contract.
The current single-submit entry is [Runtime injection](../RUNTIME-INJECTION.md).
Installation still requires the product's supported extension and permission
path; these historical `extensions-dev` steps do not bypass the current host's
signed-extension gate or establish that a receiver is running.

`workbuddy` uses a locally installed platform extension to call the product's
`wb.conversations.sendPrompt(native_session_id, blocks, options)`. The user must
authorize the extension and explicit native targets. It requires only
`conversations.sendPrompt`; it never uses desktop gateway credentials, another
caller's identity, or an MCP panel.

Install `scripts/wakeup_native/workbuddy_extension/` into the configured
WorkBuddy `extensions-dev/paos-session-send` directory. Add a local
`targets.json` containing `{"targets": ["<authorized-native-id>"]}`. The runtime
and target files are excluded from Git. Normal product extension reload writes
`.runtime.json` with an own loopback endpoint, token and authorized targets.
Bind through `paos wake bind --driver workbuddy --native-session-id <id>` using
config `{"runtime_file":"<absolute-path>/.runtime.json","state_root":"<absolute-native-state-root>"}`.
The driver reads current metadata on every action, so product restarts and
port/token changes need no rebinding.

Probe calls only `GET /probe`. It proves extension reachability and the target
grant, not native idle or work completion. Wake submits once and returns
`accepted`, always `completed:false`; native queuing is retained in
`bridge_result`. The existing controller persists the attempt before sending
and owns idempotency. The product receives that attempt ID as `clientRequestId`.
Timeouts and possible SDK failures remain `uncertain` and are not retried.

## Explicit model for an authorized night send

`paos wake trigger <project> <agent> --prompt @<file> --source-kind system
--source-id <maintenance-source> --attempt-id <new-id> --model-id <actual-id>`
passes an explicit WorkBuddy model unchanged to native `sendPrompt` options.
Omitting `--model-id` preserves session-model inheritance and sends no model
field. Other Runtime drivers reject an explicit model before an attempt is
created. The model is part of attempt identity: reusing an attempt with a
different model or changing between explicit selection and inheritance is a
conflict, never another submission. Native queued receipts remain unchanged.
The request records the selected ID, not a claim about the actual response model.

Use this parameter only for Human-authorized night maintenance after checking
the product's current model ID, free status and available quota. This parameter
does not select a model by clock time, verify pricing, or change session defaults.
Do not substitute third-party aliases for the product's actual ID. The Notice
consumer continues to inherit the session model. The local helper also accepts
`node send.cjs <session_id> <message-file> [modelId]`; normal PAOS calls should use
the Wake controller so durable attempt identity remains enforced.

STOP is binding-scoped and fences future sends. It does not interrupt native
turns or drain accepted product queues. Recover only probes and explicitly
removes the STOP marker when the same extension is reachable; it does not start
WorkBuddy, copy credentials or replay attempts.

## Notice consumer

`scripts/wakeup_native/workbuddy_notice_worker.py --config <local-json>` is an
explicitly installed resident consumer, independent of the model turn. Its
config contains `not_before` (UTC adoption time) and `homes` (canonical
`paos-home-ref/v1` Project Agent locators). It reads only the existing
`activation_work` projection and submits via the existing Wake controller.
Only pending Notices with an explicit activation requested at/after adoption
are eligible. Historical requests are not replayed. A restart skips any
existing attempt, including `triggering`/`uncertain`. Offline means no
submission; the same extension can become reachable later. Once submitted,
failure/uncertainty requires a new explicit activation decision, never an
automatic retry. The model owns Notice handling, Mail reading and business
results. `--once` inspects one cycle for adoption verification without starting
a second resident consumer.

Run extension fixtures with `node --test scripts/wakeup_native/workbuddy_extension/test.cjs`
(set `WORKBUDDY_FORK_PRELOAD` to the installed native preload path). Python Wake
and Notice regression tests are part of normal `verify.py`.
