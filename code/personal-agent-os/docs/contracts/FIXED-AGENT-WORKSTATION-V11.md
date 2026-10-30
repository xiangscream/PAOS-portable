# Fixed Agent Workstation V1.1

## Purpose

V1.1 gives every long-lived Agent a stable, Project-local workstation that survives Work, Cycle, model, and Runtime changes.

The workstation is a visible part of the Project Vault. It is not a PAOS governance object and does not replace Session, Work, Request, review, Ledger, or operation receipts.

## Project Vault layout

The minimal visible Project Vault directories are:

```text
<Project Root>/
├─ Inbox/
├─ Materials/
├─ Works/
├─ Decisions/
├─ Workstations/
└─ Archive/
```

Initialization is non-destructive:

- an existing directory is reused;
- existing user files are not moved;
- if a reserved directory path is occupied by a file, initialization fails before creating any missing standard directories.

The layout is a placement contract, not a requirement to keep empty folders forever.

## Stable Agent home

One Project Agent owns:

```text
<Project Root>/Workstations/<agent-id>/
├─ ENTRY.md
├─ TODO.md
└─ mailbox/
```

This path is stable across Work, Cycle, Runtime and model changes.

### ENTRY.md

`ENTRY.md` is a copy-paste entry for a long-lived Project Agent. It contains:

- Project and Agent identity;
- the stable workstation, TODO and mailbox paths;
- optional Workflow Library and Skill Library references;
- the live PAOS context command;
- the default read order and collaboration rules.

It must not freeze a current Cycle, Context Pack, Runtime session, complete Project history, or full prompt.

### TODO.md

`TODO.md` is the Agent's current execution list and short upward-management status. Humans and Agents edit the same Markdown file.

The minimum format is:

```markdown
---
schema: paos-todo/v1
project_id: <project>
agent_id: <agent>
---

# 当前工作

Work：<current work>
目标：<goal>

## 状态摘要

阶段：<stage>
进展：<short result-oriented progress>
阻塞：<blocker or 无>
下一步：<next action>

## 待办

- [ ] T-001 <task>
  完成方式：（完成后填写）
  结果：（完成后填写）
  产出：<optional project artifact>
```

The parser treats checkbox items with stable task IDs as structured TODO items. The Markdown remains the source document; parsed data is a rebuildable read model.

A checked item means the Agent says that execution item is complete. It does not by itself accept a Work, resolve a Request, or complete Human review.

### mailbox/

`mailbox/` is reserved for V1.1 durable Markdown mail. A later package defines message envelope and delivery semantics. Creating the workstation creates the directory now so Agent entry is stable before mailbox delivery is enabled.

## Creation and repair

`paos workstation init <project> <agent>` creates or repairs the fixed workstation.

It may:

- ensure the Project Vault standard directories;
- create missing `ENTRY.md`, `TODO.md`, and `mailbox/`;
- seed the initial TODO from the Agent's current Work or mission.

It must not:

- overwrite an existing `ENTRY.md` or `TODO.md`;
- move existing Project files;
- mutate PAOS Project state;
- acquire or refresh a Session execution claim;
- infer a new Work or responsibility.

The command reads current PAOS facts to seed the local files. Re-running it after an Agent or human has edited the workstation is safe and preserves those edits.

`paos workstation show <project> <agent>` reads the same TODO and mailbox directory without mutation.

## Relationship to the existing cycle materialization

The existing `.paos/workstations/<work>/<agent>/cycle-N/` directories remain Cycle-bound execution evidence during the first V1.1 implementation slice.

They are not the V1.1 stable Agent home.

V1.1 establishes a single normal Agent entry path: `<Project Root>/Workstations/<agent-id>/ENTRY.md`.

`workstation init` performs a conservative migration check before creating the fixed home:

- the exact generated pre-V1.1 `.paos/agents/<agent>/ENTRY.md` locator may be retired automatically after the fixed home is published;
- an unknown, edited, unreadable, or path-conflicting legacy ENTRY blocks initialization before Project Vault directories are created;
- Cycle materialization no longer creates or refreshes `.paos/agents/<agent>/ENTRY.md`;
- `workstation show` refuses to choose silently if a legacy ENTRY reappears beside the fixed home.

The Cycle-specific `.paos/workstations/<work>/<agent>/cycle-N/ENTRY.md` remains valid execution evidence and is not a competing stable Agent entry.

## Acceptance for this slice

1. Project Vault initialization is non-destructive and fails visibly on reserved-path conflicts.
2. A new Agent home contains `ENTRY.md`, `TODO.md`, and `mailbox/`.
3. Re-running initialization never overwrites edited ENTRY/TODO bytes.
4. TODO parsing returns stable task IDs, checkbox state, result details, and short status.
5. `workstation init` performs PAOS GETs only.
6. `workstation show` reads the same source Markdown without PAOS mutation.
7. Cycle materialization keeps its non-overwrite evidence behavior but no longer publishes the retired stable Agent locator.
8. A known generated legacy stable locator is retired only after the fixed home is published.
9. Unknown/edited legacy ENTRY content blocks migration without creating a second current entry.
10. The normal Agent entry is unambiguous after successful initialization.
