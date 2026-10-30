# PAOS V1.1 Stage 1 — Packet C2 Kernel + First Skills

Decision owner: zrx  
Prerequisite: C1R accepted  
Mutation scope: shared Workflow/Skill Libraries only

## 0. Goal

Create the first usable two-layer baseline:

```text
Workflow Kernel
  wf-agent-work-cycle
  wf-coordinator-governance-cycle

Skill Library
  skill-engineering-change
  skill-independent-review
```

No other shared Workflow, Guide, Template or Skill is authorized in this packet.

## 1. Fixed semantic boundaries

### Workflow Kernel

Owns:

- current responsibility / authority check;
- TODO self-management;
- next meaningful action;
- peer collaboration vs escalation;
- reviewable result requirement;
- acceptance boundary;
- handoff / closeout / standby.

Does not own:

- professional execution method;
- task-class decomposition;
- test commands;
- PRD structure;
- research method;
- code-review heuristics;
- Runtime-specific wake mechanics.

### Skill

Owns reusable “how to execute better”.

Does not own:

- Work/Request/Session state;
- Agent responsibility;
- acceptance authority;
- current TODO;
- Coordinator governance.

## 2. Authority/lifecycle rule

Both Workflow files must **reference**, not reproduce, authoritative PAOS governance.

Forbidden:

- copied Human authority matrix;
- copied Work/Request/Session state machine;
- invented acceptance states;
- local aliases for lifecycle truth.

Required wording should make clear:

> Before taking an authority-sensitive action, read the current authoritative PAOS governance fact.

## 3. Universal communication/evidence semantics

The Agent cycle must state the following without transport-specific implementation detail:

```text
message stored
≠ activation accepted
≠ model turn
≠ Agent consumed
≠ task result
≠ accepted result
```

And:

- ACK is not handoff;
- inbox empty is not Work complete;
- executor “done” is not acceptance;
- Agent updates its own TODO before handoff/report;
- no new responsibility → standby is valid.

Runtime-specific proof details belong in Skills/repo contracts.

---

# C2A — Author Workflow Kernel

## Owner / reviewer

```text
Owner:    s027
Reviewer: s029
Coordinator: s010
```

## Files to author

In canonical Workflow root only:

```text
workflow/README.md
workflow/Workflows/wf-agent-work-cycle.md
workflow/Workflows/wf-coordinator-governance-cycle.md
```

Do not create Guide or Template files.

## Workflow README

README should explain only:

- two-layer architecture;
- Workflow Kernel vs Skill boundary;
- two canonical Workflow IDs;
- Skills are discovered separately;
- no task-class Workflow creation by default;
- promotion rule:
  - universal Work-management rule → Kernel change;
  - execution method → Skill;
  - Project-only → Project;
  - incidental → no promotion.

Keep it short.

## `wf-agent-work-cycle`

Required semantic sections:

```text
Outcome
Role / Boundary
Resume
Current responsibility
TODO discipline
Execution boundary
Collaboration / escalation
Evidence / reporting
Closeout / handoff
Standby
Stop conditions
```

Required truths:

- read fixed Workstation first;
- read current TODO/Mailbox/relevant live context;
- use live PAOS governance for authority/lifecycle;
- choose next meaningful action proactively;
- load Skills only when useful;
- ordinary domain collaboration goes peer-to-peer;
- governance/priority/resource/decision blockers go upward;
- communication/wake/ACK layers are not completion;
- write durable Artifact/evidence;
- update own TODO before meaningful report/handoff;
- no responsibility means standby, not invented maintenance.

## `wf-coordinator-governance-cycle`

Required semantic sections:

```text
Outcome
Role / Boundary
Thin-state intake
Responsibility / Work assignment
Worker autonomy
Review / acceptance
Integration / closeout
Human judgment points
Stop conditions
```

Required truths:

- read compact current state, not full Project by default;
- assign Goal / Context / Authority / Done When;
- do not maintain Worker TODO on their behalf;
- do not route ordinary Agent-Agent collaboration;
- request independent review when risk warrants;
- acceptance follows PAOS governance, not executor self-report;
- close/integrate current Work before spawning unnecessary branches;
- Human attention reserved for real judgment/authority points.

## Authoring sources

Use:

- approved-main Agent/Coordinator Guides;
- C1R source map;
- real Run evidence;
- C1R freeze decision.

Do not copy local-only docs wholesale.

## C2A versioning

Use existing `paos-workflow/v1` frontmatter.

Both Workflow files start:

```text
status: candidate
version: 1
```

They become `active` only after C2B.

## C2A Git

Commit shared Library changes in the standalone `PAOS-Libraries` repo.

One bounded commit for C2A.

Do not touch PAOS source repo dirty workspace except own TODO/handoff reports.

---

# C2B — Independent Kernel review + scenario test

Starts only after C2A commit.

s029 independently reviews.

## P1 checks

1. **Task-class leakage**
   - software / PRD / research / document-revision technique must not appear as required Workflow steps.

2. **Authority duplication**
   - no copied authority/lifecycle matrix.

3. **Duplicate support layer**
   - no hidden Guide/Template semantics recreated as large appendices.

4. **Communication semantics**
   - ACK/inbox/wake/result/acceptance are correctly separated.

5. **TODO autonomy**
   - Worker owns its TODO; Coordinator does not become secretary.

6. **Coordinator thin-context**
   - no requirement to reload entire Project or route all collaboration.

## Scenario test

Evaluate the same Agent Workflow against at least:

```text
software code change
product/PRD definition
research synthesis
document cleanup
migration task
independent review task
```

Pass condition:

- same `wf-agent-work-cycle` applies to all;
- only relevant Skill choice changes;
- no scenario needs a new Workflow to proceed.

Evaluate Coordinator cycle against the same task classes.

Pass condition:

- assignment/review/acceptance loop remains unchanged by task class.

## C2B outcome

If no P1:

- change the two Workflow statuses from `candidate` to `active`;
- version remains 1 if only status activation changes in the same accepted baseline;
- rebuild Workflow Catalog;
- commit activation/Catalog as a second bounded Library commit.

If P1:

- return to C2A;
- do not start C2C.

---

# C2C — Author first two Skills

Starts only after C2B PASS.

## Skill 1 — `skill-engineering-change`

Purpose:

> Help an Agent implement and land a software change with risk-proportional evidence.

Must synthesize, not mechanically concatenate:

- exact candidate / exact HEAD discipline;
- intended-contract read;
- bounded implementation;
- focused regression;
- full verifier/diff hygiene when applicable;
- independent review when risk warrants;
- real-machine / cross-runtime smoke when native behavior matters;
- historical issue vs introduced regression;
- merge gate evidence.

Critical rule:

> Validation depth is selected by risk and changed surface. This Skill is not a fixed ritual that always runs every possible test.

Do not own merge authority or Work acceptance.

## Skill 2 — `skill-independent-review`

Purpose:

> Help a reviewer independently test whether a candidate actually satisfies its contract.

Must include:

- freeze exact candidate/baseline;
- understand intended contract;
- inspect changed surface;
- challenge hidden assumptions;
- use focused evidence;
- distinguish P1 / P2 / historical issue;
- distinguish source behavior from environment issue;
- do not patch executor's work by default;
- report evidence + decision-relevant findings.

Do not own acceptance authority.

## Skill status

Start both as:

```text
status: candidate
version: 1
```

Use existing `paos-skill/v1` contract.

## C2C source discipline

The Skills may use evidence from real PAOS Runs, but strip:

- Project IDs;
- PR numbers;
- fixed Runtime names where not essential;
- one-off local paths;
- PAOS governance facts.

Examples may remain generic.

One bounded Library commit for C2C.

---

# C2D — Skill review + activation

s029 independently reviews:

- Skill vs Workflow boundary;
- unnecessary rigidity;
- Project/Runtime leakage;
- overlap between the two Skills;
- whether exact-head/smoke advice is risk-proportional;
- whether review Skill accidentally takes acceptance authority.

## Scenario test

Use at least:

```text
small pure-Python change
native Windows/WSL path behavior change
documentation-only change
high-risk Runtime integration change
```

Expected:

- `skill-engineering-change` adapts depth;
- it does not require real-machine smoke for docs-only changes;
- `skill-independent-review` can review all cases without becoming a second Workflow.

If no P1:

- mark both Skills `active`;
- rebuild Skill Catalog;
- commit activation/Catalog as a second bounded Skill commit.

---

# 4. Deferred candidates

Do not author in C2:

```text
runtime-wake-verification
agent-first-delivery-verification
local-fact-reconnaissance
migration-runner-isolation
cross-runtime-path-registry
activation-owner-transition
migration-planning-review
handoff-settlement
clean-writing (source discovery pending)
product-definition
research-to-decision
document-revision
project-material-ingest
```

They remain candidates for later M2.

---

# 5. Prohibited mutation

C2 does not authorize:

- Project/Vault cleanup;
- Workstation migration;
- legacy ENTRY retirement;
- activation-owner change;
- hook/binding/Room/Participant changes;
- PAOS Project registry root/status changes;
- source-guide cleanup;
- dirty primary repo cleanup;
- import of local-only docs as-is.

---

# 6. Required handoff

s027:

```text
V11-C2A-WORKFLOW-KERNEL-AUTHORING.md
V11-C2C-FIRST-SKILLS-AUTHORING.md
```

s029:

```text
V11-C2B-KERNEL-INDEPENDENT-REVIEW.md
V11-C2D-SKILL-INDEPENDENT-REVIEW.md
```

Coordinator:

```text
V11-C2-COORDINATOR-READBACK.md
COORDINATOR-TODO-AFTER-C2.md
```

Reports must include exact `PAOS-Libraries` commit SHAs and Catalog result.

Every Agent updates its own TODO before handoff.

---

# 7. Stop gate

After C2D:

```text
STOP
```

Do not automatically continue to:

- broader Skill promotion;
- Project cleanup;
- Workstation migration;
- activation-owner cutover.

zrx reviews the resulting real Library before the next migration packet.
