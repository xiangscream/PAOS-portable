# PAOS V1.1 — M4/M5 Post-Cutover Convergence Plan

Status: authorized planning baseline
Date: 2026-09-23

## 1. Current state

Project 3002 has completed the production cutover.

~~~text
Project 3002 revision      656
canonical root             C:\Users\remo\Desktop\agent学习计划\PAOS-Projects\3002-Personal-Agent-OS
runtime/source baseline    3b86ac555a7526fcd5160fb7dd8404c98bad9733
Artifacts                  86
key_files                  18
migration Work w057        done
fresh Workstations         s010 / s027 / s029 / s031
old root                   preserved legacy evidence
~~~

s031 has completed the first fresh-Workstation readback.

s010 / s027 / s029 have now completed new-Workstation onboarding readback. s027 required a fresh OpenCode Runtime because the old native session restored obsolete context. Together with the earlier s031 readback, all four baseline Workstations are usable entry points.

The generated new Workstation TODOs may still show historical Work state. Do not manually rewrite PAOS facts to make the files look cleaner. New post-cutover Work/Session assignments must establish current responsibility naturally.

Project-3002 relocation is complete. The remaining work is post-cutover convergence, not another root migration.

## 2. Two parallel tracks

~~~text
Track A — Project 3002 convergence
  real cold starts
  -> legacy dependency scan
  -> knowledge consolidation
  -> legacy-root retirement
  -> M5 acceptance

Track B — Skill Library reconstruction
  read-only arrangement
  -> bounded refactor / promotion decisions
  -> small promotion batches
  -> usage feedback

                    ↓
                  M5
~~~

Track B does not block ordinary Project-3002 work.
Track A does not wait for the Skill Library to become exhaustive.

# 3. Track A — Project 3002 convergence

## A1 — Establish real post-cutover Work

Create one real closeout Work instead of hand-editing the four new TODOs:

~~~text
V1.1 Stage-1 Final Acceptance and Legacy Retirement
~~~

Purpose:
- drive the remaining fresh-Workstation / fresh-Runtime validation;
- verify new Project World navigation under real work;
- detect any old-root dependency;
- close the known legacy-knowledge question;
- retire the old root from daily use;
- produce the final M5 acceptance packet.

Roles:

~~~text
s010  Coordinator / closeout owner
s027  implementation + legacy dependency / knowledge closure
s031  Runtime / activation evidence
s029  independent final reviewer
~~~

s029 stays outside the implementation path until review evidence is ready.

Skill Library arrangement remains useful Project-3002 work, but it is not required to close V1.1.

Do not create fake Work solely to make a TODO look current.
## A2 — Fresh-Workstation cold-start matrix

Run one real fresh Session for each baseline Agent:

~~~text
s010
s027
s029
s031
~~~

Each fresh Runtime must identify, without reading the old root:
- stable role;
- canonical Project root;
- current Work;
- current TODO;
- Workflow Library root;
- Skill Library root;
- Source repository;
- where durable outputs belong;
- collaboration / escalation path.

The test should happen during real Work, not as four synthetic questionnaire exercises where avoidable.

s031's existing readback is valid evidence, but its new real responsibility should still replace historical TODO context naturally.

Acceptance:

~~~text
4/4 daily-entry authority = new Project Workstations
old ENTRY/TODO not required for normal work
~~~

## A3 — No-new-write / legacy dependency observation

After fresh cold starts, inspect actual work rather than performing another full migration audit.

Look for:
- new current outputs written under the old personal-agent-os root;
- direct Agent navigation to old .paos/agents or old Workstations;
- scripts/configs that still assume the old Project root;
- Artifact/key-file/current INDEX links that route normal work back to legacy paths;
- activation or runtime paths that require the old root as a working location.

Historical Artifact pointers and preserved runtime evidence do not count as a failure by themselves.

Classify every remaining old-root dependency:

~~~text
HISTORICAL-ONLY
EXTERNAL/RUNTIME-EVIDENCE
TEMPORARY-COMPATIBILITY
CURRENT-BLOCKER
~~~

Default target:

~~~text
CURRENT-BLOCKER = 0
TEMPORARY-COMPATIBILITY = 0 unless explicitly justified
~~~

## A4 — Legacy knowledge consolidation

Before the old root is archived, inspect only documents that may still contain unique durable knowledge.

First known target:

~~~text
docs/WORKFLOW-PHILOSOPHY.md
~~~

Compare it against current authorities:
- PRODUCT-AND-DESIGN-PHILOSOPHY.md;
- wf-agent-work-cycle;
- wf-coordinator-governance-cycle;
- guide-project-work-world.md;
- accepted Skill/Workflow architecture decisions.

For each unique still-valid principle:

~~~text
product/system philosophy
    -> current Source philosophy/docs

universal Work-management principle
    -> Workflow Library

task execution technique
    -> Skill candidate/reference

already covered / obsolete
    -> historical only
~~~

Do not copy legacy documents wholesale into the new Source merely to preserve filenames.

This batch may identify a small number of other legacy-only design documents, but must not reopen whole-root archaeology.

## A5 — Legacy-root retirement

Only after A2-A4 PASS:
1. establish a no-new-write checkpoint;
2. verify no normal Agent entry requires the old root;
3. preserve rollback/archive evidence;
4. mark the old root explicitly historical / read-only;
5. move or rename it into the chosen legacy archive location if useful.

Do not delete it as part of the same batch.

Old Artifact locators that intentionally preserve historical evidence may continue to point to a stable archived locator.

Result:

> the old Project root stops being a workspace and becomes an archive.

# 4. Track B — Skill Library reconstruction

## B1 — Read-only arrangement review

Keep the current canonical baseline stable:

~~~text
skill-engineering-change
skill-independent-review
clean-writing
~~~

Do not bulk-import the 15 local curated Skills.

Read-only review must produce:
- one-line contract for each curated candidate: trigger / input / output / not_for / nearest overlap;
- semantic overlap matrix for the product-definition family;
- clean-writing refactor specification;
- candidate promotion tiers;
- external reference-pool index strategy.

### clean-writing decision

Do not split it into multiple top-level Skills at this stage.

Refactor direction:
- narrow trigger to final/reader-facing writing;
- keep evidence preservation as a hard internal constraint;
- keep lint as an internal tool;
- move detailed modes/examples/review rules into references;
- preserve stable ID clean-writing.

### Product-definition family

Working hypothesis to validate:

~~~text
product-definition-research
        ↓
product-definition-workbench
        ↓
write-prd
~~~

product-feature-mining is a merge/module candidate until semantic diff proves an independent recurring trigger.

## B2 — Promotion decision

After B1 review, Human/mainline selects a small batch.

Default high-value candidates:

~~~text
technical-research
write-prd
docx-safe-editing
feishu-doc-edit
~~~

This is a proposal, not automatic promotion.

Promotion gate:
1. clear source/provenance;
2. crisp trigger/input/output/not-for contract;
3. no serious trigger collision;
4. real-use evidence;
5. independent review.

Do not make metadata itself a second governance system.

## B3 — Bounded promotion/refactor batches

Promote or refactor one family at a time.

Suggested sequence:

~~~text
B3a  clean-writing internal refactor
B3b  technical-research + write-prd
B3c  format/tool adapters
B3d  product-definition family after overlap decision
~~~

Every batch:

~~~text
source freeze
-> normalize
-> scenario/real-use test
-> independent review
-> Catalog rebuild
-> usage observation
~~~

Do not combine unrelated Skill families into one mutation packet.

## B4 — External reference pool

The ~1,201 external Skills remain a reference pool.

Build only a lightweight read-only index when useful:

~~~text
source repo/package
relative path
declared name
description
content hash
license/provenance if available
duplicate group
~~~

Use it to compare a small relevant set when promoting a concrete candidate.

Do not add the external pool to the canonical Skill Catalog.

# 5. M5 — convergence acceptance

M5 begins after:
- Track A fresh Workstation acceptance is complete;
- no current legacy-root dependency remains;
- Workflow/Skill roots resolve;
- canonical Skill baseline is internally consistent.

M5 does not require every local Skill candidate to be promoted.

## M5-001 — method roots / Catalog

Verify:
- Workflow Catalog;
- Skill Catalog;
- duplicate IDs = 0;
- references resolve;
- new Agents can discover the correct method layer.

## M5-002 — Project truth

Verify:
- Project 3002 new root is the normal daily work world;
- current outputs have one discoverable canonical location;
- legacy root is historical-only;
- external/shared sources remain clearly external.

## M5-003 — Workstations

Verify:
- s010/s027/s029/s031 each has one daily ENTRY;
- current TODO reflects real current Work;
- mailbox works;
- old ENTRY/TODO/Cycle evidence is not daily authority.

## M5-004 — fresh Runtime matrix

Use real or bounded fresh Sessions to prove:

~~~text
role
responsibility
Project root
Source
Workflow/Skill roots
collaboration
output location
closeout
~~~

## M5-005 — legacy-path scan

Final scan for accidental live dependence on old Project-3002 paths.

## M5-006 — V1.1 baseline close

If M5 passes:

> Stage-1 migration closes. Further friction is treated as product/workflow iteration, not unfinished migration.

# 6. Immediate next packet

Start one real closeout Work:

~~~text
V1.1 Stage-1 Final Acceptance and Legacy Retirement
~~~

Use that Work as the real operating evidence for the new Workstations, no-new-write observation, legacy knowledge closure, old-root retirement and M5 acceptance.

Skill Library promotion is no longer on the V1.1 closeout critical path. The existing 3-Skill baseline is sufficient for Stage-1 acceptance.

Rooter configuration is also deferred until the current 3002 closeout responsibility finishes.

Do not manually clean the new TODOs before assignment. Do not delete the old root.

See `M5-V11-FINAL-CLOSEOUT-PACKET.md`.