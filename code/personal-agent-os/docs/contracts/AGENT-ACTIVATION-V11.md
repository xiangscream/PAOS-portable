# Agent Activation V1.1

## Purpose

B2c introduces the **Agent-first** orchestration surface above Runtime Wake.

Callers address a stable PAOS Agent:

```text
Agent
  ↓
durable source fact
  ↓
Agent Activation
  ↓
Wake binding
  ↓
Runtime driver
```

The caller does **not** choose Codex/OpenCode/harness-specific behavior.
The current Wake binding remains the only Runtime locator.

The first B2c package connects Workstation Mail to Agent Activation. CAT will
reuse the same Agent-level primitive after its durable exchange reference is
verified.

## Why Agent-first

PAOS treats:

- Agent = long-lived worker identity;
- Workstation = stable Project home;
- Runtime = replaceable execution carrier.

Therefore normal collaboration should say:

> notify Agent B that durable work is waiting

not:

> call OpenCode session X

Runtime-specific wake mechanics belong behind the Wake contract.

## No new truth source

B2c intentionally does **not** introduce a new mutable orchestration database.

Existing authorities remain:

```text
Workstation Mail dispatch + Markdown file
    = durable communication truth

Wake binding + Wake attempt
    = Runtime activation truth

TODO / Work / Request / review
    = work execution / governance truth
```

Agent Activation derives its result from those layers.

There is no separate “notification delivered” flag competing with Mail or Wake.

## CLI

Primary B2c surface:

```text
paos agent send <project> --to <agent-id> \
  --subject <text> --body <text|@FILE|-> \
  [--message-id <stable-id>]

paos agent send <project> --broadcast \
  --subject <text> --body <text|@FILE|-> \
  [--message-id <stable-id>]
```

This one Agent-level operation performs two ordered phases:

```text
B1 persist/deliver Workstation Mail
→ B2c activate only recipients whose durable copy verifies
```

It is intentionally not fake-atomic. If the process exits after Mail delivery
but before Wake, re-running the same explicit `message-id` safely resumes:
Mail reuses its immutable dispatch and Agent Activation reuses stable Wake
attempt ids.

Recovery / selective activation surface:

```text
paos agent notify <project> --mail <message-id>

paos agent notify <project> --mail <message-id> \
  --agent <agent-id> [--agent <agent-id> ...]
```

No Runtime, driver, native session or harness argument is accepted.

When `--agent` is omitted, `notify` processes the durable Mail dispatch's
entire frozen recipient set. When supplied, every selected Agent must already
belong to that frozen set.

## Durable-first rule

For Workstation Mail:

```text
dispatch exists
→ recipient is in frozen dispatch set
→ recipient Markdown copy hash is valid
→ only then may Agent Activation call Wake
```

If Mail delivery is:

- missing;
- unreadable;
- conflicted;

that Agent is **not** woken.

The durable source is repaired first.

This preserves the B2 rule:

```text
source persisted before wake
```

and prevents “wake now, maybe create the message later.”

## Frozen broadcast rule

B1 already freezes broadcast recipients at first send.

B2c consumes that exact frozen set.

It never recalculates recipients from current Project Sessions.

Example:

```text
T0 Mail broadcast freezes [A, B]
T1 Agent C joins Project
T2 agent notify --mail <same id>

activation targets [A, B], never C
```

This guarantees that an Agent is not woken for a Mail file it was never sent.

## Stable per-Agent activation identity

One Mail dispatch may target many Agents.

B2c derives one stable Wake attempt id per:

- Project;
- Agent;
- source kind;
- source id.

Shape:

```text
agent-mail-<sha256-prefix>
```

Runtime/harness/binding is deliberately absent from this derivation.

This creates one Agent-level activation intent for one durable fact.

B2a still includes the current binding fingerprint in Wake attempt identity.
Therefore a source already attempted under an old Runtime cannot silently wake
again after a rebind. That mismatch fails closed and requires an explicit new
operator decision.

## Source verification

Mail/CAT activation primitives may not be called with an unverified source.

For `mail`, verification comes from the immutable B1 dispatch and mailbox file
hash.

The generic internal Agent activation primitive rejects `mail` or `cat`
when `source_verified=false`.

Future CAT integration must verify its durable exchange reference before using
the same primitive.

## Agent activation result

Agent-facing output contains:

- Project id;
- stable Agent id;
- source kind/id;
- stable Wake attempt id;
- whether source verification passed;
- whether a Wake binding exists;
- whether a new Wake request was issued;
- Wake state;
- replay/idempotency state.

It deliberately does not expose:

- runtime id;
- native session/thread id;
- driver;
- harness-specific config.

Those remain available through the lower-level `paos wake ...` operational
surface for diagnostics.

## Unbound Agent

Durable communication does not require a live Runtime.

If a verified Mail exists but the Agent has no Wake binding:

```text
state = unbound
wake_requested = false
```

The Mail remains durable.

After the Agent is bound again, re-running the same Agent notification derives
the same stable activation id and may perform the first Wake.

## Partial broadcast

Broadcast activation is per Agent.

Example:

```text
A Mail delivered + bound   -> Wake A
B Mail missing             -> block B
C Mail delivered + unbound -> preserve Mail, report unbound
```

One recipient failure does not erase or roll back successful durable delivery
or activation for other recipients.

## Idempotency

Re-running the same Mail notification for the same Agent reuses the same B2a
Wake attempt id.

If it already completed:

```text
replayed = true
wake_requested = false
```

No second model turn is requested.

## Layered evidence

B2c keeps evidence separate:

```text
Mail delivered
!=
Wake requested
!=
Runtime woken
!=
Agent read Mail
!=
TODO/Work completed
!=
review accepted
```

The batch response presents Mail delivery and Agent activation as separate
sections.

## Runtime independence

The B2c implementation imports only the generic Wake controller.

It does not branch on:

- OpenCode;
- Codex;
- native session shape;
- driver config.

OpenCode is the primary V1.1 Runtime and Codex is the secondary validated
Runtime, but that choice is invisible to Agent Activation.

DeepSeek Harness support is intentionally outside V1.1 scope.

## Acceptance

1. Public orchestration targets stable Agent ids, not Runtime/harness ids.
2. `agent send` persists Workstation Mail before any Wake side effect and is
   retry-safe when the caller reuses the same explicit message id.
3. Existing Workstation Mail must be verified before Wake.
3. Broadcast activation uses the Mail dispatch's frozen recipients.
4. New Project Agents are never added to an old Mail activation.
5. Missing/conflicted Mail blocks only that recipient's Wake.
6. Unbound Agent preserves the durable source and reports `unbound`.
7. Same source + Agent derives the same Wake attempt and does not create a
   second model turn on retry.
8. Optional Agent selector can only choose members of the frozen recipient set.
9. Agent-level result does not expose Runtime/driver/native-session details.
10. No new competing orchestration truth store is created.
11. Agent CLI reads PAOS Project metadata through GET only.
12. B1 Mail and B2a/B2b1/B2b2 behavior remains unchanged.
13. Full verifier and diff hygiene stay green.

## CAT immediate collaboration

B2c3 attaches verified CAT Exchange references to the same
`activate_agent()` primitive.

Normal CAT path:

```text
paos agent chat <project> --room <room> --to <agent> --body ...
```

Recovery path:

```text
paos agent notify <project> --cat-exchange <room>:<exchange>
```

CAT remains the conversation/inbox/ACK authority. PAOS owns Agent activation.

To prevent duplicate Runtime turns, this path only accepts CAT Rooms with
`activation_owner=paos`; those Rooms keep durable inbox facts but suppress the
legacy marker Runtime wake projection.

See `CAT-AGENT-ACTIVATION-V11.md`.

## B2c status

- B2c1: Agent activation primitive — accepted.
- B2c2: Workstation Mail → Agent — accepted.
- B2c3: CAT Exchange → Agent — current package.
