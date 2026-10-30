---
schema: paos-skill/v1
id: grill-me
title: Grill Me
status: active
version: 1
name: grill-me
description: Use this skill when the user asks to be challenged, grilled, questioned, stress-tested, cross-examined, or have a draft/idea/plan "挑刺", "拷问", "质询", "grill me", or "push back". Applies to ORID reflections, daily reports, product ideas, PRDs, project plans, demos, strategy notes, career reflections, and content plans. The skill should expose weak assumptions through focused questions, then help tighten the work after the user answers.
---

# Grill Me

## Overview

Use skeptical but useful questioning to sharpen a draft, idea, plan, or reflection. Do not perform a generic critique first; identify the central claim, ask high-leverage questions, then revise or summarize only after enough answers exist.

## Operating Rules

- Be direct and specific. Challenge weak claims, vague words, missing evidence, unclear users, undefined success, and overlarge scope.
- Ask in small batches: normally 3-6 questions. If the user is drafting a form with limited fields, ask only the questions that can materially improve the submission.
- Prefer concrete questions over abstract "why" chains.
- Preserve the user's voice. After the grill, rewrite only enough to make the work clearer, sharper, and more defensible.
- Separate "submission-safe" wording from private notes when the topic involves company, legal, product, confidential, or personnel information.
- Do not pressure the user to reveal secrets. Ask them to generalize, anonymize, or remove sensitive details.

## Workflow

1. Name the object being grilled in one sentence.
2. State the current central claim or goal in one sentence.
3. Choose the grill mode: ORID, product/PRD, project plan, strategy, content, or general.
4. Ask a focused batch of questions.
5. After the user answers, synthesize the answers into one of:
   - a tighter draft,
   - a decision memo,
   - a risk list,
   - a next-action plan,
   - or a revised ORID/PRD section.
6. Point out any remaining unresolved assumptions.

## Grill Modes

### ORID / Daily Reflection

Check:

- O: Are the facts concrete enough? Can a reader see what happened today?
- R: Is the feeling real, or just a conclusion like "有收获" or "有压力"?
- I: Is there an actual judgment, not a recap?
- D: Is there a next action with a subject, object, and near-term time horizon?
- Does the submission avoid confidential details and excessive technical sprawl?

Useful questions:

- Which exact event today changed your thinking?
- What was your role, not just the team's activity?
- What emotion did you actually feel, and what caused it?
- What is the one sentence you would defend if your mentor asked "so what?"
- What will you do tomorrow that proves this reflection changed your behavior?

### Product Idea / PRD

Check:

- Who is the user?
- What painful task are they trying to complete?
- What do they do today without this product?
- Why is the current workaround insufficient?
- What is the smallest valuable version?
- What proves it works?
- What are the non-goals?
- What could make the idea fail?
- Which claims are evidence-backed and which are intuition?

Prefer this question sequence:

1. Who specifically has this problem?
2. In what situation does the problem happen?
3. What is the user's current workaround?
4. What is the smallest solution that creates value?
5. What metric or observation proves value?
6. What risk, dependency, or constraint is most likely to break the plan?

### Project Plan

Check:

- Goal and success standard
- Scope and non-scope
- Owner and stakeholders
- Milestones and deadlines
- Dependencies
- Risks and fallback
- Review cadence
- Final artifact or delivery format

Ask especially:

- What does "done" look like?
- What can be cut if time is short?
- Who needs to approve or consume this?
- What is the first irreversible decision?
- What signal tells you to stop, pivot, or escalate?

### Strategy / Research

Check:

- Whether the thesis is distinguishable from a trend summary
- Whether the market/user segment is narrow enough
- Whether the idea is adjacent to current capabilities
- Whether near-term and long-term claims are separated
- Whether the next validation step is cheap and concrete

Ask:

- What is the falsifiable version of this thesis?
- What would make a smart skeptic reject it?
- Which part is true now, and which part is a long-term bet?
- What existing capability makes this credible?
- What is the smallest experiment that would teach something real?

### Content / Vlog / Presentation

Check:

- Audience
- Storyline
- Required shots or proof points
- Missing transitions
- Pacing
- Privacy and confidentiality
- Final call-to-action or takeaway

Ask:

- Who is supposed to care after watching?
- What is the one story arc?
- Which shots prove the story instead of merely decorating it?
- What must be removed for privacy or professionalism?
- What can be solved in editing instead of reshooting?

## Output Patterns

When the user says "先问我" or "grill me first", stop after the question batch.

When the user asks for a final rewrite after answering, use:

```text
核心判断：
...

可以提交/对外说的版本：
...

还没完全想清楚的点：
...
```

For ORID, use:

```text
O（学到了什么？）
...

R（感受是什么？）
...

I（思考是什么？）
...

D（行动计划是什么？）
...
```

For product work, use:

```text
用户：
场景：
痛点：
现有方案：
最小方案：
验证方式：
主要风险：
下一步：
```
