# Language Modes

Use this reference when the correct writing style is not obvious from the request.

## Mode selection matrix

| Mode | Primary reader job | Process visibility | Evidence visibility | Uncertainty visibility | Default density |
|---|---|---:|---:|---:|---:|
| Publication | Understand the current subject | Very low | Low/selective | Material only | High |
| Executive | Decide/approve | Low | Selective, decision-relevant | Material only | Very high |
| Specification | Implement/verify | Very low | Usually low | Explicit where it changes requirement | High |
| Decision | Choose among options | Medium | Medium/high | High | High |
| Research | Evaluate findings | Low for work log; high for evidence | High | High | Medium/high |
| Status | Know what changed and what blocks progress | Medium | Low/selective | High for blockers | High |
| Working | Collaborate and reason | High | High as needed | High | Variable |

## Publication mode

Use for final product definitions, project results, formal reports whose job is to describe the current state, finalized proposals, and other reader-facing artifacts.

Write as if the reader is seeing the subject for the first time.

Prefer:
- current facts;
- capabilities and behavior;
- requirements and boundaries;
- user flows;
- concise necessary rationale.

Suppress by default:
- "we first thought";
- "after discussion";
- research diary language;
- rejected alternatives;
- internal confidence bookkeeping;
- evidence used only to defend ordinary claims.

## Executive mode

Use for management or approval contexts.

Lead with:
1. decision or conclusion;
2. why it matters;
3. material evidence/tradeoff;
4. action or ask.

Do not bury the decision behind research history.

Retain uncertainty only where it affects the decision.

## Specification mode

Use for PRDs, requirements, APIs, operational procedures, technical design requirements, acceptance criteria, and capability contracts.

Prefer:
- stable terminology;
- explicit subjects;
- observable behavior;
- conditions and thresholds;
- must/should/may only when their meaning is controlled;
- tables for structured parameters.

Avoid:
- persuasive prose;
- vague adjectives;
- hidden assumptions;
- historical rationale inside requirements.

## Decision mode

Use when the reader must choose or approve.

A clean decision memo is not process-free. It should show the reasoning that changes the decision, but not the entire exploration trail.

Prefer:
- recommendation;
- alternatives that remain genuinely viable;
- material tradeoffs;
- decisive evidence;
- unresolved uncertainties;
- reversibility and consequences when relevant.

Suppress dead-end exploration that no longer affects the decision.

## Research mode

Use when evidence quality, comparison, or methodology is part of the value.

Show:
- findings;
- evidence;
- limitations;
- contradictions;
- methodology only to the degree needed to evaluate the findings.

Do not turn a research report into a diary of searches, prompts, pages opened, or tool calls.

## Status mode

Use for weekly updates, project updates, handoffs, and progress summaries.

The artifact may legitimately include change history, but only the change relevant to the reporting window.

Prefer:
- current state;
- what changed;
- decision/blocker;
- next action/owner/date when applicable.

Avoid replaying old history just to demonstrate activity.

## Working mode

Use for brainstorming, investigation notes, design exploration, and collaborative reasoning.

Process, uncertainty, competing hypotheses, and evidence may be visible. Do not over-clean information that collaborators need to continue the work.

Still keep terminology stable and avoid empty AI filler.

## Mixed artifacts

If one document contains several jobs, apply modes by section rather than forcing one style everywhere.

Example:
- Executive summary → Executive
- Product definition → Publication
- Requirements table → Specification
- Evidence appendix → Research
- Changelog → Status/history

The visible hierarchy should make these layers distinct.
