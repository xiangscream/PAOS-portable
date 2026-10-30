---
schema: paos-skill/v1
id: product-definition-workbench
title: Product Definition Workbench
status: active
version: 1
name: product-definition-workbench
description: Maintain a lightweight, decision-led product-definition workspace when product thinking is scattered across PRDs, research, interviews, demos, competitor notes, and Agent outputs. Use when the user asks to straighten out a product-definition workbench, identify the current definition, prioritize unresolved product decisions, route evidence, prevent document-version sprawl, or compile accepted decisions into a PRD. Do not use as the main skill for broad market research, detailed engineering calculations, sprint tracking, or polishing a PRD whose definition is already frozen.
---

# Product Definition Workbench

## Purpose

Reduce product-definition chaos by maintaining one small control surface:

1. Current product contract;
2. Decision backlog;
3. Evidence ledger;
4. Definition change log;
5. PRD as the compiled delivery view.

The workbench is not a folder taxonomy exercise. Create or change documents only when doing so removes ambiguity about the current product or the next decision.

## Start here

1. Read the workbench entry file.
2. Read the current product contract.
3. Read the top three active decisions.
4. Open evidence, interviews, Demo material, or competitor research only for those decisions.
5. Update existing current files rather than creating another summary or minor version.

If no entry or current contract exists, create the minimum versions using [control-surface.md](references/control-surface.md).

## Route every new input

Classify the input before writing:

- confirmed fact, test, or user signal → evidence ledger;
- unconfirmed claim that may change the product → decision backlog;
- accepted product choice → current product contract and affected PRD section;
- technical unknown → the relevant decision's technical-question field;
- method, long research, draft, or raw Agent output → reference/archive until cited;
- wording-only change → edit in place; do not create a new version.

Never promote an Agent self-report, vendor claim, or plausible inference to a product decision.

## Work on the upstream bottleneck

Keep at most three decisions active. Rank them by:

1. option-expiry date or structural irreversibility;
2. consequence for first-use success or P0 scope;
3. uncertainty of available evidence.

For each active decision, separate:

- what Product must decide: user result, supported boundary, trade-off, fallback;
- what technical teams must answer: feasible options, measurements, dependencies, failure modes;
- what test or interview would change the decision.

Product owns the outcome and boundary. Product does not invent motor, optical, compute, thermal, radio, or algorithm thresholds.

## Keep the current definition compact

The current product contract must fit these fields:

- Problem;
- First user and reference task;
- Promised outcome;
- Required capabilities;
- Constraints and invariants;
- Non-goals;
- Success evidence still needed.

Use plain language. A teammate should understand the current product without reading the research archive.

## Decide without framework theater

When a choice is mature enough to discuss, write:

- Decision;
- Gain;
- Lose;
- Why now;
- Evidence for and against;
- Status: accept, reject, defer, or unknown.

Do not add RICE scores, Gate labels, formal meeting rituals, or exhaustive personas unless the user explicitly needs them.

## Compile into PRD

Use the installed write-prd skill when turning accepted product choices into atomic requirements, states, exceptions, and acceptance criteria.

Only accepted decisions and current facts enter the PRD as baselines. Open decisions remain in the decision backlog and may appear in the PRD only as explicit open questions or TBDs.

Use product-definition-research only when an active decision requires new external evidence. Do not restart broad research merely because reference material exists.

## Version and archive rules

- Maintain one current entry, one current contract, one decision ledger, and one evidence ledger.
- Minor edits update the current file in place.
- Create a snapshot version only for a review milestone or meaningful product-definition change.
- Archive superseded files reversibly; never delete source evidence.
- Update indexes when a current file changes.

## Quality check

Before handing off:

- Can the user find the current product definition in one click?
- Are no more than three decisions active?
- Does every active question name what Product decides and what another team supplies?
- Can every strong claim point to evidence and its limitation?
- Did any Demo number accidentally become a product specification?
- Did any new function enter P0 without serving the first user task?
- Did this work reduce, rather than increase, the number of competing entry files?

