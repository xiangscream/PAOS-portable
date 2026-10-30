# PAOS V1.1 — C3B Method Baseline Close

Decision owner: zrx  
Evidence baseline: C3B handoff commit `05e310a`  
PAOS-Libraries accepted HEAD: `e313e9377e7d189ec48a4b18ea926c64477d6348`

## 1. Verdict

C3B is accepted and the V1.1 shared method baseline is closed for Stage 1.

Canonical baseline:

```text
Workflow Kernel
  wf-agent-work-cycle                 active
  wf-coordinator-governance-cycle    active

Skill Library
  skill-engineering-change           active
  skill-independent-review           active
  clean-writing                      active
```

No additional Workflow or Skill promotion is required before Project/Vault reconstruction.

## 2. clean-writing acceptance

`clean-writing` passed:

- exact-source verification;
- bounded normalization from the Windows Codex source package;
- platform/runtime packaging removal;
- independent semantic review;
- one P1 narrow fix for product-domain examples;
- independent follow-up review;
- activation and Catalog rebuild.

Accepted shared package boundaries:

- method content + four references + advisory `clean_lint.py`;
- no `agents/openai.yaml`;
- no icon/UI asset;
- no PAOS governance ownership;
- no mandatory global invocation.

The remaining language-mode/lint limitations are P2 and should be improved only when real use produces friction.

## 3. Usage projection

The existing `skill-independent-review` event:

```text
su-d8d9685039594198a9e5151158a2e24b
score = 0.5
```

projects correctly into the rebuilt local Catalog:

```text
uses=1
uses_30d=1
usefulness_avg=0.5
project_count=1
agent_count=1
```

No duplicate event was generated.

## 4. Non-blocking telemetry P2

The usage event is currently installation-local/untracked while the generated Catalog commit includes its derived stats.

This is a real provenance/replayability question, but it does not block Project migration.

Do not solve it by simply Git-adding all usage telemetry.

Later contract work must choose one coherent model:

```text
A. usage events are durable shared Library facts and are versioned;
or
B. usage events remain installation-local telemetry and committed Catalog does not claim replayable local usage stats.
```

Until that decision:

- preserve the event in place;
- do not duplicate/rewrite it;
- do not interpret Git history alone as complete usage history;
- do not reopen C3B.

Track as `R2-SKILL-TELEMETRY-001` before Stage-2 cutover or when telemetry becomes operationally important.

## 5. PAOS-Libraries Runtime-loading boundary

Shared Skill active status does not mean a Runtime automatically loads it.

Current known fact remains:

- PAOS-Libraries is canonical shared content;
- Codex/OpenCode may have their own Runtime skill roots;
- Workstation/Agent discovery and Runtime consumption are integration concerns;
- no Runtime config is changed in this closeout.

## 6. Stage transition

The method layer is now sufficiently clean for the next Stage-1 workstream:

```text
M3 — Project Vault Reconstruction
```

M3 must begin with a read-only Project truth refresh and migration-scope freeze, not immediate file movement.

Reason:

- the 10 Project registry entries mix active, shared-root, un-housed and possibly stale lifecycle facts;
- four Projects still share one OBSBOT workspace root;
- several Projects have no usable root;
- 3002 remains a dirty live source repo with local facts that cannot be bulk-reorganized;
- Project content truth must be understood before any dedicated-root or archive mutation.

## 7. Next gate

Authorize only:

```text
M3A
Project truth refresh
→ current activity/disposition
→ root/source-of-truth mapping
→ dry-run migration scope
→ STOP
```

No Project filesystem mutation is authorized by this decision.