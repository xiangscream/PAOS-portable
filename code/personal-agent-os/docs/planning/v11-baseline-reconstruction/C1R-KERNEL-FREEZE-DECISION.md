# PAOS V1.1 — C1R Kernel Freeze Decision

Decision owner: zrx  
Evidence baseline: C1R handoff commit `2e1669d8ee280445ed8261a99c063a3802683438`

## 1. Final Layer-1 baseline

V1.1 Workflow Layer freezes at **two Workflows and no mandatory support Guide/Template baseline**.

```text
Workflows/
  wf-agent-work-cycle.md
  wf-coordinator-governance-cycle.md

Guides/
  (empty initially)

Templates/
  (empty initially)
```

The physical A3a directories stay because they are valid Library structure. They are not content quotas.

A support Guide or Template may be added later only if a real Run proves that keeping the rule inline in the two Workflows causes repeated ambiguity or duplication.

## 2. Why support files are not baseline requirements

C1R showed that the proposed four Guides and two Templates mostly restated material already owned by the two cycles:

- TODO / self-management belongs in the Agent cycle;
- collaboration / escalation belongs in Agent + Coordinator cycles;
- evidence / review / acceptance boundaries belong in the two cycles while authoritative lifecycle/authority remains in PAOS governance;
- Workflow-vs-Skill promotion rule fits the Workflow Library README / architecture contract;
- Work brief fields fit directly in the Coordinator assignment section;
- handoff fields fit directly in Agent closeout.

Creating six support files now would make the Kernel look modular while actually duplicating the same semantics across more files.

## 3. Authority and lifecycle boundary

The Workflow Kernel is **not** an authority or lifecycle source.

It must never copy or redefine:

- Human-only authority;
- Work/Request/Session lifecycle states;
- acceptance state;
- ownership generation;
- Project governance facts.

Kernel language should say:

> Read the current authoritative PAOS governance fact before acting.

Where needed, link to the existing authority/lifecycle contract or CLI surface. Do not reproduce the matrix/state machine inside Workflow text.

This resolves C1R P1 #2.

## 4. Same topic across Workflow and Skill

One topic may appear in both layers only when the semantic ownership differs.

Use this split:

| Topic | Workflow Kernel owns | Skill owns |
|---|---|---|
| Evidence | when evidence is required; self-report is not acceptance | how to gather/test/validate evidence |
| Review | when independent review is needed; reviewer independence | review technique, checks, heuristics |
| Collaboration | when to contact peer / Coordinator / Human | tool-specific or domain-specific collaboration technique |
| Handoff | what must be durably settled before stopping | optional domain-specific handoff technique |
| TODO | current execution truth, next action, blocker discipline | no separate task-execution method unless a specialized tool deserves one |
| Wake / ACK | transport/runtime signals are not Work completion | runtime-specific wake verification |
| Engineering gate | completion must be reviewable | exact-head, test ladder, real-machine smoke technique |

Rule:

```text
Workflow = when / who / authority / durable state / closeout
Skill    = how / technique / heuristics / quality
```

This resolves C1R P1 #1.

## 5. Real-Run rules that must enter Kernel

The following are universal operating semantics, proven repeatedly, and belong in the Agent/Coordinator cycles:

1. **ACK is not handoff.**
   A message/exchange ACK only proves the communication item was acknowledged under that transport contract.

2. **Inbox empty is not Work complete.**
   Empty Mail/CAT inbox is not evidence that responsibility, TODO or Work is closed.

3. **Wake/injection is not consumption.**
   Stored message → activation accepted → model turn → Agent read → task result → acceptance are distinct layers.

4. **Agent updates its own TODO before handoff/report.**
   Coordinator does not maintain Worker personal execution state on its behalf.

5. **No new responsibility means standby is valid.**
   Do not invent permanent maintenance Work to keep an Agent “active”.

6. **A blocker that changes governance/priority/resource/decision goes upward; ordinary domain collaboration goes peer-to-peer.**

7. **A result is not accepted merely because the executor says “done”.**
   Acceptance follows the relevant PAOS governance/review fact.

These are organizational rules, not domain Skills.

## 6. Real-Run rules that stay out of Kernel

The following are useful but task/runtime-specific:

- exact-head / focused / full verify / diff-check / real-machine smoke;
- OpenCode `204` vs actual assistant turn semantics;
- status-map idle interpretation;
- clean runner isolation;
- Windows/WSL path canonicalization;
- activation-owner cutover mechanics;
- registry atomic-replacement technique.

They remain Skill or repo-contract candidates.

This resolves C1R P1 #4 without bloating the Kernel.

## 7. Local source decisions

### `docs/workflows/`

Do not promote as a parallel Workflow library.

Disposition:

- extract only universal closeout/standby semantics into `wf-agent-work-cycle`;
- any task-specific content becomes Skill candidate or remains repo/project-local;
- the local index itself becomes historical/local evidence after replacement exists;
- do not create a second “support workflow” layer.

### `docs/WORKFLOW-PHILOSOPHY.md`

Do not promote as a standalone shared Guide.

Its useful two-layer boundary has already been superseded by:

- `TWO-LAYER-WORKFLOW-SKILL-ARCHITECTURE.md`;
- the Workflow Library README that will summarize promotion rules.

Preserve the local file as evidence until Project cleanup; no shared-library copy.

### Dirty `AGENT-EMPLOYEE-GUIDE.md` / `COORDINATOR-OPERATING-GUIDE.md`

Approved-main remains the repo canonical source.

Do not merge dirty versions wholesale.

During authoring:

- extract only semantically valid current V1.1 operating rules;
- ignore obsolete wording / older baseline structure;
- preserve dirty files untouched until later Project cleanup;
- any independent factual repo correction becomes a separate repo-doc patch, not Library authoring.

### `USER-AND-ARCHITECTURE-GUIDE.md` / README / START-HERE

Remain repo/user documentation. Their deduplication is not a blocker for Workflow/Skill baseline.

## 8. First Skill promotion batch

C1R produced many candidates, but the first batch should be small and proven.

### Promote first

#### `skill-engineering-change`

Purpose: reusable technique for safely implementing and landing code changes.

Sources to synthesize:

- exact-head discipline;
- focused regression;
- full verifier/diff hygiene;
- independent review where warranted;
- isolated real-machine smoke when native behavior matters;
- historical issue vs regression distinction.

This Skill absorbs the narrower candidates:

- exact-head-cross-runtime-gate;
- isolated-real-machine-smoke.

It must stay adaptable: the validation ladder is selected by risk, not blindly run as a fixed SOP.

#### `skill-independent-review`

Purpose: reusable independent-review technique.

Core experience:

- freeze exact candidate/baseline;
- read intended contract;
- inspect changed surface;
- challenge hidden assumptions;
- separate P1 / P2 / historical;
- do not patch by default;
- return evidence sufficient for the decision owner.

Acceptance authority remains outside this Skill.

### Keep as candidates, do not promote in first batch

- runtime-wake-verification;
- agent-first-delivery-verification;
- local-fact-reconnaissance;
- migration-runner-isolation;
- cross-runtime-path-registry;
- activation-owner-transition;
- migration-planning-review;
- handoff-settlement.

Reason: these are valuable but either Runtime/PAOS-migration specific, have significant overlap, or need one more reuse before a stable generic boundary is clear.

### Separate known external Skill

`clean-writing` remains a strong existing Skill candidate, but C1R did not identify its exact current package/source. It should be imported/reconciled in M2 only after local source discovery, not recreated from memory during this packet.

## 9. Authoring order

```text
C2A
Author two Workflow Kernel files + Workflow README

C2B
Cold-start semantic review of Kernel only

C2C
Author first two Skills:
  skill-engineering-change
  skill-independent-review

C2D
Skill review + Catalog rebuild + scenario test
```

Do not author the deferred Skill candidates in C2.

## 10. Success criteria

The baseline is correct when:

- a software task, research task, PRD task and migration task all use the **same** Agent Work Cycle;
- only the loaded Skill changes;
- Coordinator behavior does not depend on task class;
- Workflow files do not duplicate authority/lifecycle truth;
- ACK/inbox/wake/completion/acceptance are correctly separated;
- an Agent can remain proactive through TODO without a task-specific Workflow;
- the first Skills materially encode technique without becoming a second governance layer.
