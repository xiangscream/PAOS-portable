# Human Work review entry v1

Status: S2-2 implementation contract.

## Product result

A Human can move ordinary active Work into formal review from the normal Project workflow, then accept or reject it without using Admin state correction.

The lifecycle is:

`doing / blocked -> review -> done | doing`

`Ready for Review` is a Work transition. It does not close, abandon, continue or otherwise rewrite an Agent Session. Agent Close remains handoff testimony and does not close the Work.

## Normal UI

For `doing` and `blocked` Work, both the NOW panel and the normal Work card expose **提交验收**. The action uses the existing `paos-work-ready-review/v1` endpoint and may carry an optional Human note.

Before submitting, the dialog shows the Work Done When and any recorded Agent close results. This is context for the Human action; it does not infer completion automatically.

For `review` Work, the NOW panel and Work card expose the existing Human review actions:

- **验收归档** -> `done`;
- **驳回继续** -> `doing`.

A button labelled Review must never route to the Agent launcher or create/continue a Session.

## Authority and state rules

Ready-for-Review and Work review remain Human actions. S2-2 does not add Worker/Coordinator authority, does not change the authority manifest, and does not introduce a second review state machine.

The existing backend remains authoritative:

- only `doing` / `blocked` may enter `review` through Ready-for-Review;
- only `review` may be accepted or rejected;
- acceptance requires the existing score/comment contract;
- rejection requires the existing reason contract;
- Ready-for-Review has no Session side effect.

## Acceptance

S2-2 is accepted only when the exact candidate HEAD satisfies all of the following:

1. focused Node tests verify the canonical Ready-for-Review payload and both normal UI entry points;
2. the existing P1a backend/HTTP Ready-for-Review -> Human review tests remain green;
3. existing Work review/cancel/evaluation and Project UI suites remain green;
4. `scripts/verify.py` and `git diff --check` are clean;
5. a real browser smoke proves `doing -> 提交验收 -> review -> 验收归档` and `review -> 驳回继续 -> doing` through the normal Project UI, with no Admin correction;
6. a `review` NOW card invokes Human review rather than Start/Continue Agent.

## Not in S2-2

- Agent CLI expansion: S2-3;
- compact context/read payload work;
- Coordinator planning or autonomous acceptance;
- broad Project information-architecture or visual polish;
- general WorkflowService/MRO refactor;
- CAT ownership/recovery.
