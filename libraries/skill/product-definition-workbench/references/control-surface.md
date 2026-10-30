# Minimal control surface

Use these templates only when the project lacks an equivalent current file. Prefer adapting existing files over creating duplicates.

## Workbench entry

- one-sentence current definition;
- links to current contract, decisions, evidence, changes, and PRD;
- top three active decisions;
- material-role map: current, reference, archive;
- routing rule for new information.

## Current product contract

~~~markdown
# Current product contract

## Problem
## First user and reference task
## Promised result
## Required capabilities
## Constraints and invariants
## Non-goals
## Evidence still needed
~~~

## Decision entry

~~~markdown
ID:
Question:
Why now:
Product must decide:
Technical or other teams must provide:
Options:
Gain / lose:
Evidence for / against:
Status:
Output location:
~~~

## Evidence entry

~~~markdown
Evidence ID:
Type: FACT / USER_SIGNAL / INFERENCE / HYPOTHESIS / DECISION
Source and date:
Claim supported or challenged:
Applicable boundary:
What it cannot prove:
Linked decision:
~~~

## Capability contract

Create this only after a product decision needs a system boundary.

~~~markdown
Capability:
Product result:
Input:
Output:
Normal behavior:
Failure and degradation:
Owning system:
Dependencies:
Open measurements:
Acceptance evidence:
~~~

## Definition change

~~~markdown
Change ID:
Date:
Status: proposed / accepted / rejected / deferred
Before:
After:
Reason and evidence:
Affected product contract / decision / PRD sections:
~~~

