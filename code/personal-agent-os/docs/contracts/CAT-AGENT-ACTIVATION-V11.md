# CAT Agent Activation V1.1

## Purpose

B2c3 makes CAT immediate collaboration **Agent-first**.

The caller addresses a stable PAOS Agent. CAT keeps the durable conversation;
PAOS chooses the Agent's current Runtime through the existing Wake binding.

```text
Agent A
→ CAT Exchange for stable Agent B
→ CAT durable inbox
→ PAOS verifies the exact pending Exchange
→ Agent B activation
→ generic Wake binding
→ B's current Runtime
```

No Agent-facing CAT command chooses OpenCode, Codex, a native session, or a
Wake driver.

## Duplicate-wake ownership fence

Legacy CAT Rooms write marker files that Runtime Adapters consume.

If PAOS Agent Activation also woke the same target, one Exchange could create
two model turns.

Therefore B2c3 requires CAT Rooms with:

```json
{
  "activation_owner": "paos",
  "wake_mode": "event",
  "paos_binding": {
    "project_id": "<project>"
  }
}
```

In this mode CAT persists Exchange/inbox/ACK facts but does not project a
Runtime marker. Marker rearm is disabled.

Legacy/default `activation_owner=cat` Rooms remain supported by CAT itself but
are rejected by `paos agent chat` / CAT Agent Activation.

## Stable Agent mapping

CAT Participant identity remains channel-local.

The mapping to PAOS is:

```text
participant.paos_session_id
→ stable PAOS Agent id
```

Before send/activation PAOS requires an exact unique mapping.

A caller uses:

```text
--to <stable-agent-id>
--from-agent <stable-agent-id>
```

and never needs the Participant id.

Human sender remains CAT's canonical `human` endpoint.

## Primary CLI

```text
paos agent chat <project> \
  --room <room-id> \
  --to <stable-agent-id> \
  --body <text|@FILE|-> \
  [--from-agent <stable-agent-id>] \
  [--message-id <stable-id>] \
  [--reply-to <exchange-id>] \
  [--cat-base <origin>]
```

Ordered phases:

```text
verify PAOS-owned CAT Room + Agent mapping
→ persist idempotent CAT Exchange
→ re-read durable Exchange history
→ verify target inbox still contains the exact unacked Exchange
→ Agent Activation
→ Wake
```

This is deliberately not a fake atomic transaction.

## Recovery / existing Exchange

```text
paos agent notify <project> \
  --cat-exchange <room-id>:<exchange-id> \
  [--agent <expected-stable-agent-id>] \
  [--cat-base <origin>]
```

This is useful when:
- CAT Exchange was persisted while the Agent was unbound;
- the process stopped between Exchange persistence and Agent Activation;
- an operator wants to retry the exact durable source.

## Source verification

Before CAT can cross the Wake boundary, all of these must hold:

1. Room exists and is `open`.
2. Room is not expired.
3. `activation_owner == paos`.
4. Room `paos_binding.project_id` matches the PAOS Project.
5. Exchange exists exactly once in durable CAT history.
6. Exchange target Participant still maps to one stable PAOS Agent.
7. If an expected Agent was supplied, it matches exactly.
8. An unacknowledged Exchange is still present in that target's inbox.

If history says unacknowledged but inbox does not contain it, activation fails
closed instead of guessing.

If the Exchange is already ACKed:

```text
state = already_consumed
wake_requested = false
```

No stale conversation turn is created.

## Idempotency

Agent-level `--message-id` derives a stable CAT `operation_id`.

CAT therefore owns send idempotency:

```text
same message-id + same CAT request
→ same Exchange
```

The resulting Exchange creates the Agent activation source:

```text
source_kind = cat
source_id   = <room-id>:<exchange-id>
```

B2c/B2a then derive the same per-Agent Wake attempt.

So a retry after a crash can safely cross both layers:

```text
CAT Exchange replay
→ same Exchange id
→ same Agent activation
→ same Wake attempt
→ no second model turn
```

If the same CAT operation id is reused with changed sender/target/body/reply,
CAT rejects it.

## Unbound Agent

If CAT Exchange is durable and pending but the stable Agent currently has no
Wake binding:

```text
activation = unbound
Exchange remains in CAT inbox
```

After binding, `agent notify --cat-exchange ...` may issue the first Wake.

## ACK remains CAT truth

Agent Activation does not mark the Exchange read or completed.

After wake:

```text
Agent reads CAT inbox
→ performs collaboration step
→ ACKs exact Exchange with current ownership_generation
```

Only CAT ACK removes the item from pending inbox.

Therefore:

```text
Exchange persisted
!= Agent woken
!= Exchange ACKed
!= Work completed
!= PAOS review accepted
```

## Runtime independence

The CAT orchestration module calls only the generic Agent Activation primitive.

It does not inspect:
- Runtime id;
- native session/thread;
- Wake driver;
- OpenCode/Codex configuration.

OpenCode and Codex remain below the Wake binding.

## Evidence privacy

CAT owns message body storage.

PAOS Wake operational state records only:
- `source_kind=cat`;
- `source_id=<room>:<exchange>`;
- wake prompt hash and normal Wake metadata.

The CAT business body is not copied into Wake state.

## Acceptance

1. Stable Agent id is the public target; Participant id is hidden from callers.
2. CAT Room must explicitly give activation ownership to PAOS.
3. PAOS-owned Room creates durable Exchange/inbox without legacy marker wake.
4. Exact Project binding and unique Participant→Agent mapping are required.
5. Exact pending Exchange is verified before Wake.
6. ACKed Exchange never creates a new Wake.
7. Same CAT message id does not create a second Exchange or model turn.
8. Unbound Agent keeps the pending Exchange and can activate after later bind.
9. Changed-content replay fails through CAT idempotency.
10. CAT body is absent from Wake operational evidence.
11. Agent-facing result contains no Runtime/driver/native-session details.
12. No new collaboration truth store is introduced.
13. Existing CAT-owned Rooms and legacy adapters remain backward compatible.
14. PAOS governance state remains unchanged.
15. Cross-repo real OpenCode Agent-first CAT E2E passes.
