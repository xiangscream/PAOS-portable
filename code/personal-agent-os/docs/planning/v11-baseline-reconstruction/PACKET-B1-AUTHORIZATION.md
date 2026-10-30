# PAOS V1.1 Stage 1 — Packet B1 Authorization

> zrx authorization after Packet B0 local evidence. Packet B1 establishes only a trustworthy execution source and empty canonical shared Library roots. It does **not** migrate Workflow content, Skill content, Project content, Agent Workstations, Runtime activation ownership, or legacy hooks.

## Approved baseline

At authorization time:

```text
PAOS main before this authorization: 9e1c69fe7aa299b379538031ec9c6568e228486a
Packet B0 handoff branch: handoff/v11-m0-20260920
Packet B0 latest handoff commit: b765722
```

Execution must pin to the **approved main SHA after this authorization is merged**.

## B0 decisions that make B1 safe

### Dirty/local canonical claims

The dirty primary workspace is preserved as the factual source for local-only material.

Packet B1 does not decide the final wording of local divergent Guides. It only assigns each claim a later migration owner:

- fixed/local Workstations and `.paos` stay in place;
- `docs/workflows` and `WORKFLOW-PHILOSOPHY.md` are M1 source material;
- divergent tracked Guides remain untouched and are compared during M1-002;
- planning/problem packs/reviews remain evidence;
- `private-data` remains the installation entity and is excluded from runners.

Therefore the clean runner is allowed to provide executable PAOS code without pretending to contain the full Project truth.

### Activation owner

Production Rooms remain on their current legacy owner throughout Packet B1.

For 3002:

```text
room-e7f0cfaa5c5f
activation_owner = null / legacy cat
```

s027/s029 continue through the already-live legacy CAT/OpenCode path.

Packet B1 does not:

- set `activation_owner=paos`;
- stop/start legacy OpenCode adapters;
- edit Codex Stop hooks;
- edit Wake bindings/current.json;
- create CAT Participants;
- use a new Runtime path merely to demonstrate the new architecture.

If an Agent's existing Runtime dies and continuing would require an owner switch, stop that Agent's Packet B1 task and return to Coordinator.

### Entry authority

Packet B1 does not create/cut over Workstations.

Current transition authority remains:

```text
s027  legacy .paos/agents ENTRY/current Runtime
s029  existing live Runtime/Cycle only
s010  current Coordinator Runtime/TODO
s031  existing fixed Workstation (not required for B1)
```

No fresh s029/s010 Runtime is started from an inferred entry.

---

# B1A — Clean migration runner

## Owner / reviewer

```text
Owner:    3002-s027
Reviewer: 3002-s029
Coordinator: 3002-s010
```

## Allowed mutation

Create a new clean worktree/clone only.

Do not modify the primary dirty worktree except the executing Agent's own TODO.

## Required sequence

1. Update s027 TODO with accepted task and exact authorization baseline.
2. Record primary dirty worktree path and leave it untouched.
3. If stale Git worktree metadata blocks creation, prove it is prunable first; prune metadata only, never delete a real worktree directory as cleanup.
4. Create a dedicated clean PAOS migration runner pinned to the exact approved main SHA.
5. Record:
   - runner path;
   - exact HEAD;
   - branch/detached state;
   - `git status --short`;
   - Python/CLI import sanity.
6. Verify the runner does **not** contain copied primary:
   - `.paos/`;
   - `Workstations/`;
   - `private-data/`;
   - dirty/untracked candidate canonical files.
7. Verify the runner default Library registry is absent/unregistered.
8. Do not create `PAOS-Libraries` yet.
9. s029 independently verifies all B1A facts.

## B1A PASS

All must be true:

- exact runner HEAD == approved main;
- runner Git status clean;
- primary dirty worktree unchanged;
- no copied installation/Workstation state;
- runner library CLI is available;
- runner default registry has not become a second fact source;
- s029 reports no P1.

If any fails: STOP before B1B.

---

# B1B — Versioned empty Library roots + primary registry

Starts only after Coordinator records B1A reviewer PASS.

## Owner / reviewer

```text
Owner:    3002-s027
Reviewer: 3002-s029
Coordinator: 3002-s010
```

## Target

```text
C:\Users\remo\Desktop\agent学习计划\PAOS-Libraries
├─ workflow
└─ skill
```

Primary registry:

```text
C:\Users\remo\Desktop\agent学习计划\personal-agent-os\private-data\environment\library-roots.json
```

## Required sequence

### 1. Pre-check

Record that:

- `PAOS-Libraries` does not already contain user content that would be overwritten;
- primary registry path does not already contain a conflicting registration;
- primary Project/Session/Work governance snapshot is captured for before/after comparison.

Unexpected existing content or registry conflict = STOP / report.

### 2. Establish history first

Create `PAOS-Libraries` and initialize a standalone local Git repository on branch `main`.

Before Workflow/Skill skeleton creation:

- add a small root README describing shared-library purpose and ownership;
- create the first baseline commit.

No remote is required.

### 3. Initialize empty roots

Using the clean PAOS runner:

- initialize Workflow root;
- initialize Skill root.

Expected Workflow foundation:

```text
workflow/
  README.md
  Guides/
  Workflows/
  Templates/
  .paos/
```

Expected Skill foundation:

```text
skill/
  README.md
  .paos/
    usage-events/
```

Do not import `docs/workflows`, local Guides, Skills, Workstation files or Project content.

Commit the empty initialized skeleton as the second Library baseline commit.

### 4. Register roots in the real installation

Every roots command must use the explicit primary config:

```text
--config C:\Users\remo\Desktop\agent学习计划\personal-agent-os\private-data\environment\library-roots.json
```

Never rely on the clean runner default.

Write:

```text
workflow_root = C:\Users\remo\Desktop\agent学习计划\PAOS-Libraries\workflow
skill_root    = C:\Users\remo\Desktop\agent学习计划\PAOS-Libraries\skill
```

Then run `library roots show` with the exact same explicit config.

### 5. Negative verification

Prove:

- clean runner's own default registry is still absent/unregistered;
- no old Workflow/Skill content was imported;
- primary dirty tracked/untracked files other than the new authorized registry remain unchanged;
- no Project revision / Session / Work / Request / Ledger mutation occurred;
- no Runtime activation owner / hook / binding / CAT Room / Participant changed.

### 6. Reviewer

s029 independently verifies:

- first Library commit predates skeleton/content initialization;
- second Library commit contains only initialized empty roots;
- registry points to exact roots;
- no second registry;
- no source-material migration has started;
- governance/runtime boundaries are unchanged.

## B1B PASS

Required:

- standalone Library Git history exists;
- two roots initialized and distinct;
- explicit primary registry validates;
- runner default registry remains absent;
- no local canonical source was overwritten or moved;
- no governance/runtime mutation;
- s029 no P1.

---

# B1 closeout

Every participant updates its own TODO before handoff.

Return in the existing handoff folder:

```text
coordinator/PACKET-B1-COORDINATOR-READBACK.md
s027/PACKET-B1A-CLEAN-RUNNER.md
s029/PACKET-B1A-INDEPENDENT-REVIEW.md
s027/PACKET-B1B-LIBRARY-ROOTS.md
s029/PACKET-B1B-INDEPENDENT-REVIEW.md
coordinator/COORDINATOR-TODO-AFTER-PACKET-B1.md
```

If B1A fails, B1B report files are not expected.

## Stop gate

After B1 evidence is complete:

```text
STOP
```

Do not start:

- M1-002 source mapping;
- M1-003/004 Library content authoring;
- M2 Skill migration;
- M3 Project cleanup;
- M4 Workstation/Runtime migration.

zrx reviews B1 and issues the next packet.

## What B1 deliberately does not solve

These remain later work, not B1 blockers:

- which divergent local Guide wording becomes canonical;
- promotion of `docs/workflows` / `WORKFLOW-PHILOSOPHY.md`;
- Project root remapping;
- Workstation cutover;
- migration from legacy CAT owner to PAOS activation owner;
- Codex hook consolidation;
- Skill content normalization.

B1 only builds the safe, versioned destination and the clean execution toolchain needed to solve those correctly.
