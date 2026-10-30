# Workstation Mail V1.1

## Purpose

V1.1 adds durable Markdown communication to each stable Agent Workstation:

```text
<Project Root>/Workstations/<agent-id>/mailbox/
  <message-id>.md
```

This is **Workstation Mail**: durable communication that an Agent can read after Runtime replacement, restart, or delayed wakeup.

It is not PAOS governance authority.

## Important naming boundary

PAOS already has an older `Agent Mailbox V0` projection over canonical Request / Assignment responsibility.

The two concepts are different:

- **Responsibility Mailbox** (`paos session mailbox`): read-only projection of formal PAOS responsibility facts.
- **Workstation Mail** (`mailbox/*.md`): durable human/Agent/system communication.

A Workstation Mail message does not assign Work, resolve Request state, accept review, or grant authority. Formal responsibility continues to use canonical PAOS workflows.

CAT remains the immediate/conversational channel. Workstation Mail is the persistent channel.

## Message file

Each recipient gets one immutable Markdown file:

```markdown
---
schema: paos-workstation-mail/v1
message_id: "mail-..."
project_id: "3002"
recipient_agent_id: "3002-s010"
created_at: "..."
sender_kind: "coordinator"
sender_id: "3002-s001"
audience: "targeted"
subject: "Review the result"
---

# Review the result

Markdown body...
```

The sender fields are descriptive metadata, not authentication or PAOS authority.

V1.1 B1 does not add read/unread state. Reading a message must not mutate Project, Session, Ledger or the message file.

## Dispatch envelope

The first send creates an immutable dispatch envelope:

```text
<Project Root>/.paos/mail/dispatch/<message-id>.json
```

The envelope records:

- Project;
- message ID;
- creation time;
- sender metadata;
- targeted/broadcast audience;
- subject;
- body hash;
- frozen recipient set;
- expected recipient file path/hash.

It is operational transport metadata, not a Project governance fact.

## Broadcast semantics

Broadcast freezes the recipient set at first send.

V1.1 B1 broadcast recipients are all Project Agents whose current PAOS Session record is not `historical`.

If a new Agent appears after the first send, retrying the same `message_id` does **not** add that Agent.

This makes partial delivery recoverable and prevents a retry from silently changing the original audience.

## Delivery and retry

Order:

```text
resolve Project + recipient set
→ persist immutable dispatch envelope
→ deliver Markdown file to each recipient Workstation mailbox
→ report per-recipient delivery result
```

Possible per-recipient results:

- `delivered`
- `already_delivered`
- `workstation_missing`

An existing recipient file with the same message ID is accepted only when its content hash matches the immutable dispatch expectation. Otherwise delivery fails closed with `mail_delivery_conflict`; PAOS never overwrites the file.

Retrying the same message ID:

- requires the same sender, subject, body and audience;
- targeted mail also requires the same recipient set;
- broadcast reuses the original frozen recipient set;
- already delivered recipient files are preserved byte-for-byte;
- previously missing Workstations can receive the message later.

## CLI

```text
paos mail send <project> --to <agent> [--to <agent> ...] \
  --subject <text> --body <text|@FILE|-> \
  [--sender-kind human|system|coordinator|agent] \
  [--sender-id <id>] [--message-id <id>]

paos mail send <project> --broadcast \
  --subject <text> --body <text|@FILE|-> \
  [--sender-kind ...] [--sender-id ...] [--message-id ...]

paos mail list <project> <agent>
paos mail read <project> <agent> <message-id>
paos mail status <project> <message-id>
```

The CLI reads the Project through PAOS HTTP only to resolve `root_path` and canonical Agent IDs. It performs no PAOS HTTP writes.

## Relationship to Agent Activation

B1 itself still does not wake a Runtime.

B2c adds an Agent-first orchestration surface:

```text
persist Workstation Mail first
→ verify immutable recipient delivery
→ notify stable Agent identity
→ Agent Activation resolves that Agent's Wake binding
→ generic Wake contract continues the current Runtime
→ Runtime checks Workstation mailbox
```

Normal Agent-first CLI:

```text
paos agent send <project> --to <agent> --subject ... --body ...
```

This persists B1 Mail first and then activates verified recipients.

For an already-persisted Mail (recovery/selective retry):

```text
paos agent notify <project> --mail <message-id>
```

For broadcasts, B2c consumes this document's **frozen dispatch recipients** and
never recalculates the audience from current Project Sessions.

Mail delivery state and Wake state remain separate.

Therefore:

```text
message persisted != Runtime woken
Runtime woken != message read
message read != task completed
```

Wake status must not be inferred from Mail delivery status.

## Acceptance

1. Targeted mail creates human-readable Markdown in the exact stable Workstation mailbox.
2. Message files are immutable and retry-safe.
3. Same message ID with different body/sender/subject/audience fails visibly.
4. Targeted retry cannot silently change recipients.
5. Broadcast freezes its recipient set at first send.
6. Missing recipient Workstation produces explicit partial delivery and can be repaired by retry.
7. New Agents are not added to an old broadcast retry.
8. Existing conflicting mailbox files are never overwritten.
9. Dispatch status derives delivery integrity from expected file hashes.
10. List/read use the same on-disk Markdown source and do not create separate message state.
11. Mail CLI uses PAOS GET only and does not mutate revision, Session, Request or Ledger.
12. Existing Responsibility Mailbox semantics remain unchanged.
13. A1/A2/A3 regressions, full verifier and diff hygiene pass.
