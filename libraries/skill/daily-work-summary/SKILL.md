---
schema: paos-skill/v1
id: daily-work-summary
title: Daily Work Summary
status: active
version: 1
name: daily-work-summary
description: create structured end-of-day work summaries from mixed notes, agent handoffs, task boards, file changes, meeting records, and partial drafts. supports both single-workline and multi-workline outputs, with optional modules for product research (硬/软排除, 原则, 决策判断, Gate 阶段) and technical learning (knowledge card inventory, evidence levels). use when the user asks for a 日总结, daily summary, end-of-day recap, work log, progress report, multi-agent work consolidation, manager update, or a clear account of what was completed, what changed, evidence strength, blockers, and the next priority.
---

# Daily Work Summary

Turn fragmented work records into a conclusion-first daily summary that supports project control and next-day execution. Supports both single-workline and multi-workline (2-3 parallel work lines) outputs.

## Workflow

1. **Establish the reporting scope.**
   - Identify the date or latest work node from the input.
   - Identify how many work lines are active (1 = single; 2-3 = multi).
   - Identify optional modules needed (product research? technical learning? process change?).
   - Do not ask for clarification when the scope is inferable; state the chosen scope briefly.

2. **Separate today's direct work from cumulative project state.**
   - Count as **today's work** only actions completed or decisions made in the reporting period.
   - Put earlier work that was merely consolidated today under **cumulative state**.
   - Never present a multi-day backlog as if it were all completed today.

3. **Normalize every input item into one or more of these classes:**
   - action completed;
   - artifact produced or revised;
   - decision or definition changed;
   - evidence added;
   - assumption weakened or strengthened;
   - blocker or risk;
   - next action.

4. **Reconcile contradictions before writing.**
   - Preserve exact dates, versions, names, prices, gate labels, and status terms.
   - When two notes conflict, do not silently choose one. State the conflict and use the most defensible formulation.
   - Distinguish precise status terms (e.g., "reviewed learning baseline closed" vs. "100% complete").

5. **For multi-workline outputs: handle each line independently then synthesize.**
   - Run steps 2-4 per work line.
   - Then do **cross-line synthesis**: today's key judgments, risk by line, target-map, next task per line.

6. **Map progress to objectives.**
   - Explain which monthly, weekly, project, or trial-period objective each work line advanced.
   - State what did not advance.
   - Do not reward activity that is unrelated to the active objective.

7. **Assess evidence strength.**
   - Apply the rules in `references/quality-rules.md`.
   - Use the user's existing evidence taxonomy when available; otherwise use strong/medium/weak/unknown.
   - Make weak evidence explicit. Do not turn a framework, desktop inference, or agent-generated hypothesis into validation.

8. **Produce the report using `references/report-template.md`.**
   - Default: both a manager-ready brief and a detailed archive version.
   - Single-workline: use base template.
   - Multi-workline: use multi-workline variant (preserves per-line structure + cross-line synthesis).
   - Adapt section depth to the amount of input, but preserve the logic: result → change → evidence → risk → next step.

9. **End with one next-day main task per active work line.**
   - For each active line, define one primary task with output, completion criteria, and explicit non-goals.
   - Allow at most one lightweight secondary task **per line** (not per day).
   - If two lines have a clear "must do tomorrow", present both; let the user choose.
   - Do not propose further framework or agent maintenance when the current framework is already sufficient.

## Optional Modules

Activate only when the work line is genuinely that kind of work. Do not force.

### A. Product research module

When the line is "new product direction / category research", include:

- **Product hypothesis freeze** — the current working hypothesis, written as one sentence
- **Design principles** — 3-7 principles the team has committed to (e.g., "Play-first", "Camera-anchored")
- **硬排除 vs 软约束** (hard exclusion vs soft constraint) — what is permanently out of scope vs what is not in v1 but not blocked forever
- **Decision judgments** — track 3-7 tracked judgments (e.g., "Direct competitors too few ⇒ market signal weak" — these need to be tracked as evidence accumulates)
- **Gate progression** — research stages the team commits to (e.g., Gate 0 hypothesis → Gate 1 competitive space → Gate 2 user evidence)
- **Stage conclusions** — at each Gate, what has been concluded, what is weak evidence, what is still open

### B. Technical learning module

When the line is "build a knowledge base for a technical domain", include:

- **Knowledge card inventory** — count and categorize (foundations, mid-tier, meta-cards, archived)
- **Card-by-card status** — working draft / reviewed / accepted / needs revision
- **Module coverage map** — which topics are covered, which are gaps
- **Accurate completion status** — distinguish "learning draft complete" from "formally admitted to library"
- **Per-card evidence level** — A (official) / B (internal) / C (inferred) / D (unverified)

### C. Process / agent-ops module

When the line is "improve how we work", include:

- **What changed** — new SOP, new agent role, new tool
- **Why** — specific failure that triggered the change
- **Daily limit** — e.g., 20 min/day on agent maintenance
- **Stop condition** — when to stop iterating

## Writing Rules

- Lead with the day's most important change, not a chronological diary.
- Use concrete verbs: completed, revised, rejected, confirmed, weakened, queued.
- Treat file counts as inventory, not impact. Explain what the outputs enable.
- Distinguish facts, interpretations, hypotheses, and recommendations.
- Preserve important caveats such as "learning draft complete, formal library not yet approved."
- Avoid inflated claims such as "fully validated," "market confirmed," or "100% complete" unless the completion definition is actually met.
- Prefer compact tables for workstream status, artifacts, evidence, and next actions.
- Keep the manager brief readable in under one minute.
- For multi-workline outputs: **per-line essence statement** (one sentence summarizing the line's current truth).
- Do not add external facts unless the user asks for verification or research.

## Input Handling

Accept any combination of:
- free-form personal notes;
- summaries from multiple agents;
- task boards or objective documents;
- file lists and revision logs;
- meeting notes;
- research conclusions;
- unresolved questions.

When inputs come from multiple agents:
- attribute work by workstream or role only when useful;
- merge duplicates;
- surface disagreements;
- separate research, review, and synthesis contributions;
- do not let an agent's confident wording determine evidence strength.

## References

- Read `references/report-template.md` for both base and multi-workline templates.
- Read `references/quality-rules.md` for evidence, completion, and contradiction rules.
- Read `references/example.md` for the multi-workline example (matching the upgraded structure).
