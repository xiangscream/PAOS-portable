# PAOS V1.1 — M3F-3002 Clean Baseline Decision

Decision owner: zrx  
Status: DONE / CUTOVER-PASS — Project 3002 canonical at new Project Work World

## 1. Decision

Project 3002 will not continue the previous compatibility-first Workstation migration.

Human decision:

> Clean the Project world first. A fresh baseline is acceptable; legacy daily paths do not need compatibility.

The new canonical Project root is:

```text
C:\Users\remo\Desktop\agent学习计划\PAOS-Projects\3002-Personal-Agent-OS
```

Target shape:

```text
3002-Personal-Agent-OS/
├─ INDEX.md
├─ Inbox/
├─ Materials/
├─ Works/
├─ Decisions/
├─ Workstations/
├─ Archive/
└─ Source/
   └─ personal-agent-os/
```

`Source/personal-agent-os/` is a fresh clean clone/worktree of the accepted GitHub `main`.

The old root:

```text
C:\Users\remo\Desktop\agent学习计划\personal-agent-os
```

becomes legacy evidence after cutover. It is not a compatibility target and must not remain a normal Agent entry point.

## 2. Boundaries

### Project Vault

Owns:

- Project navigation;
- Project-level Works;
- durable Decisions;
- Project-specific Materials;
- stable Agent Workstations;
- Project history/archive.

### Source repository

`Source/personal-agent-os/` remains the canonical source-code repository.

Code, tests, implementation contracts and repo-coupled engineering documentation stay in the repository. Do not duplicate the whole repo into `Works/`.

### Shared Libraries

Remain external:

```text
C:\Users\remo\Desktop\agent学习计划\PAOS-Libraries\workflow
C:\Users\remo\Desktop\agent学习计划\PAOS-Libraries\skill
```

The Project Vault references them. It does not copy them.

### Runtime / installation state

`private-data/`, Cycle materialization, logs, adapters and other Runtime state are not Project content.

The current service defaults its canonical registry/environment paths under repo-local `private-data/`. Therefore the new Source runtime must receive one controlled installation-state handoff before it becomes the only writer.

Do not add a new data-root abstraction merely for this migration unless local implementation proves it necessary.

## 3. Fresh-baseline rule

Do not migrate legacy daily-entry structure for compatibility.

These become historical evidence after the new baseline is accepted:

```text
old .paos/agents/
old .paos/workstations/
old top-level Workstations/
old ENTRY/TODO variants
old Runtime/session folders
dirty local Project organization
```

They are preserved in the old root until archive acceptance, but new Agents do not depend on them.

The new baseline keeps durable PAOS governance history. It does **not** create a new Project ID or erase Project/Work/Session/Ledger history.

Pre-baseline Work/Request/Session records remain historical facts. Only genuinely current responsibilities are carried forward into new TODOs or new Sessions.

## 4. Content promotion

Do not bulk-copy the old root.

Local Agents inspect the real filesystem and promote only material that has current Project value.

### Into Works/

- current Project plans and non-repo work products;
- current reviews/handoffs that are useful outside one Runtime;
- current baseline/status documents.

### Into Decisions/

- durable architecture/product decisions that remain operative.

### Into Materials/

- project-specific research/reference inputs worth keeping local.

### Stay in Source/

- code;
- tests;
- implementation contracts;
- repo-coupled technical docs;
- source-controlled planning that must version with code.

### Historical

Old Runtime outputs, superseded plans, old ENTRY/TODO and abandoned drafts do not need to be copied into the new daily corpus merely because they exist.

If needed later, preserve them through the frozen legacy root or a bounded Archive promotion.

## 5. Artifact and key-file policy

The new baseline does not require every historical Artifact body to move.

For current Project-owned Artifacts:

- move/rebind to the new Vault or new Source when they remain current.

For historical Artifacts:

- keep a stable historical locator;
- relative/no-root locators must not silently change meaning when `root_path` moves;
- rebind them to a stable absolute legacy/archive locator when necessary.

Post-cutover `key_files` must describe the new working world.

They should normally include:

- the new `INDEX.md`;
- the new Source repository or a stable repo entry;
- current Project-level plan/decision entry points;
- external Workflow/Skill roots where useful.

The old Project root must not remain a normal post-cutover key file.

## 6. Installation-state handoff

Before the new Source runtime becomes canonical:

```text
freeze old writer
→ snapshot current installation facts
→ transfer required canonical private-data
→ start exact accepted main from new Source
→ verify all Project registry revisions/facts
→ prove exactly one writer
→ keep old runtime stopped
```

Required carry-forward is determined locally, but at minimum preserve canonical Project registry/backup/receipt facts and the active environment/library-root configuration needed by the installation.

Logs, caches and other rebuildable Runtime residue do not need compatibility.

No two writable `private-data/project-registry` roots may coexist.

## 7. Execution sequence

### F1 — local truth snapshot

s010 coordinates. s027 maps:

- live Project 3002 root/revision/key_files;
- current Artifact path classes, especially root-relative paths;
- current open Work/Request/Session facts;
- dirty/untracked local files with current meaning;
- runtime/installation state needed for handoff.

s029 reviews only current-truth risks. Do not perform a full historical archaeology pass.

### F2 — build staged clean Project world

Create the new root and standard Project structure.

Create `Source/personal-agent-os/` from accepted remote `main`.

Create a clean `INDEX.md` that explains:

- current Project entry;
- Source location;
- Workflow/Skill roots;
- Works/Decisions/Materials;
- Workstations.

Promote only selected current Project content.

The new root remains staged/non-canonical.

### F3 — prepare fresh baseline state

Create one durable baseline Decision inside the staged Project:

```text
Decisions/3002-clean-baseline-2026-09-22.md
```

It records:

- new Project root;
- Source repo location + accepted SHA;
- shared Library roots;
- baseline long-lived roster;
- old root as legacy evidence;
- no-compatibility rule for old daily-entry paths.

Prepare the final root/key_files/Artifact relocation payload.

### F4 — runtime/source cutover

s031 owns the runtime switch.

Stop the old writer, transfer required canonical installation state, and start the service from the new Source checkout.

Verify:

- exact accepted SHA;
- same Project registry facts/revisions before Project-3002 relocation;
- same Workflow/Skill root registration;
- one service / one bridge / one writer;
- old service is no longer writable.

### F5 — Project 3002 atomic cutover

After F4 PASS:

- re-read live Project 3002 preconditions;
- execute one Human-only relocation-v2 operation;
- switch root/key_files and required Artifact move/rebind/retain pointers;
- verify receipt/Ledger/idempotency;
- old Project root becomes legacy evidence.

### F6 — fresh Workstations

After Project cutover, create fresh fixed homes for:

```text
s010  Project Lead / Coordinator
s027  Implementation / Integration
s029  Independent Reviewer / QA
s031  Runtime Reliability Specialist
```

Do not copy old ENTRY/TODO files into the new homes.

Seed only:

- stable role;
- Project navigation;
- Workflow/Skill roots;
- current responsibility if one genuinely exists.

New Runtime Sessions start from these Workstations.

### F7 — cold-start acceptance

A fresh Runtime for each baseline Agent must be able to identify:

- its role;
- new Project root;
- Source repo;
- Workflow/Skill roots;
- current responsibility;
- where outputs belong;
- collaboration/escalation rules.

No old Project-root path may be required for normal work.

## 8. Legacy disposition

Do not delete the old root during cutover.

After the new baseline passes real use:

- old repo/root becomes immutable legacy evidence;
- no new current output is written there;
- it may then be moved/renamed into an explicit legacy archive.

No compatibility shim is required.

The only rollback requirement is that the old root and pre-cutover installation snapshot remain available until the new baseline is accepted.

## 9. Acceptance

Return one of:

```text
READY-FOR-3002-CLEAN-CUTOVER
BLOCKED-CURRENT-TRUTH
BLOCKED-RUNTIME-STATE-HANDOFF
BLOCKED-NEW-VAULT-USABILITY
```

The target result is not “all legacy material migrated”.

The target result is:

> Project 3002 has one clean daily work world, one clean source checkout, one canonical runtime state, fresh stable Agent Workstations, and no normal dependency on the old workspace.


## 10. Current blocker

Local implementation has completed the staged Project World and exact-main Source checkout. The runtime/install-state handoff rehearsal also passed and the old runtime was restored.

s029 found 9 proposed Artifact rebind targets that do not exist. This is the only accepted M3F blocker.

Do not create missing historical files and do not reopen the full Artifact inventory.

Resolve only those 9 rows under:

`M3F-3002-R1-ARTIFACT-LOCATOR-CLOSURE.md`

Then rerun the narrow relocation-v2 dry-run/replay and independent delta review.


## 11. Mainline cutover authorization

M3F-R1 is closed. v4 and the s029 final delta review are accepted.

The production sequence is frozen in:

`M3F-3002-E-PRODUCTION-CUTOVER-DECISION.md`

Key ordering:

```text
freeze revision 654
-> production runtime/source handoff with zero Project mutation
-> exact v4 precondition read
-> Human-only relocation-v2
-> independent post-cutover review
-> close w057
-> create fresh Workstations
```

`WORKFLOW-PHILOSOPHY.md` remains legacy design-source evidence and does not block cutover.


## 12. Post-cutover result

Production cutover completed successfully.

```text
revision            654 -> 655 relocation -> 656 after w057 close
canonical root      C:\Users\remo\Desktop\agent学习计划\PAOS-Projects\3002-Personal-Agent-OS
Artifacts           86
key_files           18
REBIND               73
RETAIN               13
fresh Workstations  s010 / s027 / s029 / s031
```

s029 post-cutover review passed. The old root remains preserved as legacy evidence.

M3F is closed. Remaining work is governed by `M4-M5-POST-CUTOVER-CONVERGENCE-PLAN.md`.
