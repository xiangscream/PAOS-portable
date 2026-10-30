# PAOS V1.1 — Two-Layer Workflow / Skill Architecture

Decision owner: zrx  
Status: canonical architecture decision for V1.1 Stage 1

## 1. Decision

PAOS V1.1 does **not** build a catalog of task-class Workflows such as:

- software development;
- PRD writing;
- research;
- document revision;
- product definition;
- project cleanup.

Those activities are too contextual, model-sensitive and domain-sensitive to freeze as universal orchestration.

The V1.1 shared method system has only two conceptual layers:

```text
Layer 1 — Workflow Kernel
Stable organizational operating protocol

Layer 2 — Skill Library
Reusable task/domain experience and capability
```

Project Vault remains the work world's factual/context layer and is not a third method layer.

---

# 2. Why

A task-class Workflow looks attractive because it promises repeatability, but it tends to hard-code one decomposition of work.

For a capable Agent, that creates several failure modes:

- the Workflow competes with model judgment instead of supporting it;
- the same task can require different plans in different Projects;
- a software change, PRD, research task or migration can cross several domains at once;
- the Workflow grows into a long prompt or pseudo-program;
- improvements to one task class require maintaining another rigid workflow branch;
- Agents optimize for “following the procedure” rather than producing the result;
- repeated workflow layers duplicate what Skills and the model can already decide.

PAOS should standardize the **business operating system**, not the thought process of every profession.

The stable things are organizational:

```text
Who owns the Work?
What is the current responsibility?
What is the current TODO?
What facts are authoritative?
What is the next meaningful action?
When should another Agent be involved?
When should the Coordinator/Human be involved?
What evidence makes the result reviewable?
When is a Work actually accepted?
What must be updated before handoff/standby?
```

The unstable things belong to Skill/model judgment:

```text
How to design software
How to structure a PRD
How to research a market
How to review code
How to write clean prose
How to plan a migration
How to analyze evidence
```

---

# 3. Layer 1 — Workflow Kernel

The Workflow Layer is deliberately small.

It owns:

- Work intake / current responsibility;
- TODO self-management and proactivity;
- Project/Work truth navigation;
- collaboration / escalation;
- evidence / review / acceptance boundaries;
- closeout / handoff / standby;
- Coordinator thin-context governance.

It does **not** prescribe domain execution.

## 3.1 Canonical Workflow set

V1.1 baseline should target only two universal Workflows.

### `wf-agent-work-cycle`

The long-lived employee loop:

```text
Resume / Wake
→ locate stable Workstation
→ read current TODO + Mailbox + relevant live context
→ confirm current responsibility / authority
→ reconcile TODO and choose next meaningful action
→ execute using model judgment + Skills as needed
→ collaborate directly when another Agent owns relevant expertise
→ escalate only governance / priority / resource / decision issues
→ produce reviewable evidence / Artifact
→ update own TODO before reporting
→ continue, hand off, close, or standby
```

The Workflow does not tell the Agent how to code, research, write a PRD or revise a document.

### `wf-coordinator-governance-cycle`

The Project Lead loop:

```text
Read thin project/agent state
→ identify unresolved responsibility / decision / review need
→ assign or clarify bounded Work
→ avoid routing ordinary Agent-Agent collaboration
→ receive meaningful result / blocker
→ request independent review where warranted
→ accept / return / integrate
→ close current Work before opening unnecessary branches
→ keep Human attention on real judgment points
```

The Coordinator is not a giant context holder and not a personal assistant for every Worker.

## 3.2 Workflow support documents

Guides/Templates may exist physically under the Workflow Library because A3a already supports them, but they are **support files inside Layer 1**, not separate conceptual layers.

Likely baseline support:

```text
Guides/
  guide-todo-and-self-management.md
  guide-truth-collaboration-and-escalation.md
  guide-evidence-review-and-acceptance.md
  guide-workflow-and-skill-boundary.md

Templates/
  tpl-work-brief.md
  tpl-handoff-summary.md
```

Do not create a support file merely to fill the directory.

---

# 4. Layer 2 — Skill Library

Skills contain reusable execution experience.

A Skill may be:

- domain-specific;
- task-specific;
- tool-specific;
- quality-specific;
- model/runtime-independent when possible.

Examples of possible Skills:

```text
clean-writing
software-change
independent-review
research-to-decision
product-definition
prd-structuring
migration-planning
evidence-analysis
project-material-ingest
```

These are **candidates**, not a mandatory baseline list.

A Skill may include:

- heuristics;
- checklists;
- decision criteria;
- tool usage;
- output quality rules;
- known failure modes;
- examples;
- a lightweight execution pattern.

A Skill should not own PAOS business truth:

- Work status;
- Agent responsibility;
- acceptance;
- current TODO;
- Project lifecycle;
- Coordinator authority.

Those stay in Layer 1 / PAOS governance.

---

# 5. Promotion rule

A real Run can produce one of four outcomes:

```text
Observed friction / successful practice
→ Workflow Kernel change
   only if it changes universal operating behavior

→ Skill change
   if it improves how a type of task/capability is executed

→ Project-local rule
   if it only matters inside one Project

→ no promotion
   if it was incidental or one-off
```

Default bias:

> If a method is about **how to do the work**, prefer Skill.
> If it is about **how an employee/Coordinator manages Work**, prefer Workflow Kernel.

---

# 6. Consequences for the previous 12-Workflow candidate set

The previous 12/6/6 candidate baseline is superseded.

Reclassification hypothesis:

| Previous candidate | New default classification |
|---|---|
| `wf-normal-agent-work-cycle` | keep, renamed/normalized as `wf-agent-work-cycle` |
| `wf-work-intake-and-planning` | fold into Agent Work Cycle + TODO Guide |
| `wf-handoff-and-resume` | fold into Agent Work Cycle |
| `wf-work-review-and-closeout` | fold into Agent/Coordinator cycles + Evidence Guide |
| `wf-engineering-change` | Skill candidate |
| `wf-research-to-decision` | Skill candidate |
| `wf-product-definition` | Skill candidate |
| `wf-document-revision` | Skill candidate |
| `wf-independent-review` | Skill candidate, while acceptance authority stays Workflow Layer |
| `wf-evidence-and-acceptance` | split: evidence technique → Skill; acceptance boundary → Workflow Guide |
| `wf-project-material-ingest` | Skill candidate / Project rule |
| `wf-lesson-to-library-promotion` | fold promotion rule into Workflow/Skill boundary Guide |

The exact Skill set is decided after source mapping; do not create these automatically.

---

# 7. C1 source-mapping implication

M1-002 no longer asks:

> Which of 12 task-class Workflows should we author?

It asks:

1. What content belongs to the universal Agent/Coordinator operating kernel?
2. What content is reusable execution experience and should become a Skill candidate?
3. What is PAOS-repo-specific documentation?
4. What is Project-local?
5. What is historical evidence only?

The source map therefore classifies semantic units into:

```text
WORKFLOW-KERNEL
WORKFLOW-SUPPORT-GUIDE
WORKFLOW-SUPPORT-TEMPLATE
SKILL-CANDIDATE
PROJECT-LOCAL
REPO-DOC
EVIDENCE-ONLY
NO-PROMOTION
```

C1 should also identify duplication between local documents and real operating behavior.

---

# 8. V1.1 baseline target

A “complete baseline” now means:

```text
Workflow Kernel complete enough that a long-lived Agent
can receive, manage, execute, collaborate, report, close and resume Work

+

Skill Library has a clean promotion mechanism and the
first set of real high-value Skills from existing experience

+

Project Vault / Workstation / Mail / Activation provide
the factual work world underneath
```

It does **not** mean every class of professional work has a formal Workflow.

This preserves Agent intelligence while giving PAOS the stable organizational structure it was built to provide.
