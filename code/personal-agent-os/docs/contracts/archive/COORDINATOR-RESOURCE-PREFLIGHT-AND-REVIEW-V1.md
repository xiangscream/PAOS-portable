> 历史合同（2026-10 Workless 收敛后退役）：本文件描述的 preflight/review-setup、ACK/Cycle/Work 前置与旧 Review 责任已在现行 Workless 接口中退役（`paos workstation preflight/prepare` 与 `coordinator work-*/review-setup` 均已删除；定向 Request 保留）。这里保留原文仅作历史依据，不作现行操作指南。
>
# Coordinator resource preflight and Reviewer responsibility v1

Status: S3-2 implementation contract.

## Product result

Before a Coordinator creates a new directed responsibility, PAOS must make the relevant current resources inspectable and fail closed when the target Agent, Work or local materials are not ready. Independent review must be represented by existing PAOS facts rather than an informal CAT message or a new Review object.

S3-2 therefore adds two narrow capabilities:

1. a read-only Coordinator resource preflight that combines current PAOS facts with the Runtime-local workspace checks introduced in S3-1;
2. one atomic Coordinator review-setup action that creates a blocked Review Work plus one directed `request_type=review` Request to the Reviewer.

No Workflow, Run, Review, Workstation, Mailbox or Message persistence object is added.

## Resource preflight

`paos coordinator preflight` is a query/local-check command. It performs only GET requests to PAOS and local filesystem reads/access checks. It does not create a Work, Request, Cycle, Workstation or Runtime action.

The caller supplies:

- Project;
- current Coordinator Agent;
- target Agent;
- target Work;
- optional Reviewer Agent;
- optional workspace root override and explicit material paths.

The result reports named checks and issues. `ready=true` is allowed only when all S3-owned checks pass.

### Coordinator checks

The Project `organization.coordinator_session_id` must point to the supplied Coordinator. The Coordinator must be active and acknowledged. The command reports its current Cycle / Context Pack but does not refresh or manufacture a claim.

### Target Agent checks

The target Agent must:

- exist;
- not be terminated (a live Session needs no entry procedure, so Acknowledge is not a precondition);
- have a non-empty current Runtime binding;
- expose a current Cycle and Context Pack;
- not already be on the target Work.

S3-2 intentionally requires an available current Runtime before directed dispatch. If the Agent is closed or unbound, preflight fails and the next action remains a Human lifecycle/Runtime step. S3-2 does not gain Open/Continue/Runtime-start authority.

### Target Work checks

The target Work must exist and remain enterable by the existing `switch_work` contract (`todo`, `doing` or `blocked`). `review`, `done` and `cancelled` are not dispatch targets.

If switching the target Agent away from a `doing` Work would leave that Work with no other active/pending Agent, preflight fails with an orphan-work issue. PAOS does not silently downgrade or reassign that old Work.

### Optional Reviewer checks

When a Reviewer is supplied, it must be a distinct Agent from both the execution target and Coordinator, active, acknowledged and Runtime-bound. Its current Work must not be the source/target Work being independently reviewed.

### Workspace/material checks

The command reuses S3-1 runtime-local path preflight:

- default root is Project `root_path`, with explicit override allowed;
- root must be readable/writable;
- Project `key_files` and explicit materials must exist and be readable in the current Runtime environment;
- failure produces no `.paos` directory or other filesystem write.

### Collaboration boundary

S3-2 does **not** claim CAT/Adapter ownership readiness. The preflight response must say that transport ownership is deferred to S5. A green S3 preflight is not a Supported-auto-collaboration claim.

## Atomic Reviewer setup

`paos coordinator review-setup` wraps one canonical PAOS mutation. The request schema is `paos-coordinator-review-setup/v1`.

Inputs:

- Coordinator Agent and current execution claim under the existing Coordinator rules;
- source Work being reviewed;
- Reviewer Agent;
- Review Work title, objective and Done When;
- directed review request description.

One successful mutation creates exactly:

- one new Work with `status=blocked`, `created_by=coordinator`, `depends_on=[source_work_id]` and a note that it waits for review evidence readiness;
- one new open Request with `request_type=review`, `target_session_id=reviewer_session_id` and `target_work_item_id=<new review work>`.

The Request is the formal responsibility edge. The blocked Review Work is the formal unit of review work. CAT text alone changes neither.

If any validation fails, neither object is committed. Idempotent replay of the same operation returns the same Work/Request rather than allocating replacements.

### Reviewer validation

The Reviewer must exist, be active and acknowledged, have a Runtime binding, differ from the current Coordinator, and not currently execute the source Work. The source Work must exist and must not be `done` or `cancelled`.

These checks are repeated inside the mutation. A successful earlier preflight is useful evidence, not a lock.

## Handoff after review setup

Review setup does not start review execution. The intended existing path is:

1. Review Work + review Request are created atomically while Review Work is blocked;
2. the source Artifact becomes available;
3. Coordinator uses the existing Work transition action to move Review Work out of blocked;
4. Reviewer reads Mailbox and uses existing `session switch-work --coordination-request-id ...` to accept responsibility and start a new Cycle;
5. Reviewer registers its result as an Artifact;
6. final acceptance of the main Work remains Human Work Review.

S3-2 does not auto-transition the Review Work when an Artifact appears and does not add a background watcher.

## Authority

The new durable action is Coordinator-only. It does not grant:

- Human Work Review;
- Decision acceptance/rejection;
- Project Restore;
- Agent Open/Continue;
- external Runtime launch;
- CAT ownership or wake rights.

The Authority Manifest must expose `coordinator.review.setup` as a Coordinator action. Read-only preflight is not a durable authority action and does not need a manifest row.

## Acceptance

S3-2 is accepted only when the exact candidate proves:

- Coordinator preflight uses GET/local reads only and missing resources produce no durable/filesystem mutation;
- preflight reports orphan-doing-Work risk and unavailable Runtime/lifecycle state explicitly;
- transport ownership is reported as deferred to S5 rather than silently passed;
- review setup allocates one blocked Review Work + one open review Request in the same Project revision;
- review setup failure leaves neither object behind;
- replay of the same operation is idempotent;
- the review Request targets the newly allocated Review Work and requested Reviewer;
- existing Coordinator execution-claim validation still rejects stale tenure;
- Reviewer acceptance still goes through existing `switch_work` and does not bypass the blocked Work gate;
- Human Work Review authority remains unchanged;
- focused tests, the repository verifier and `git diff --check` pass.

## Not in S3-2

- Guide diff/promotion or Practice flywheel;
- Project browser redesign;
- CAT wake, ownership generation/fence or restart recovery;
- automatic Agent selection;
- automatic Open/Continue/Runtime launch;
- automatic transition when review evidence arrives;
- new persistence schema or database;
- merge of old M4/Supervisor branches.
