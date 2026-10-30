# V1.1 Baseline Reconstruction Execution Workflow

> 这是一次重型迁移 Workflow。它的目标不是尽快移动文件，而是在本地事实充分可见的前提下，把旧工作世界收敛成一个 canonical V1.1 baseline。

## Outcome

形成一个可切换、可验收、无明显 competing truth 的 V1.1 baseline：

- canonical Workflow Library；
- canonical Skill Library；
- clean active Project Vaults；
- role-first Agent Workstations；
- one Master Migration TODO；
- 明确 legacy retirement plan；
- fresh-Runtime cold-start 可通过。

## Use When

适用于：

- 旧系统与新系统之间的大版本事实迁移；
- 大量文件 / Workflow / Skill / Agent entry 需要统一；
- 本地真实摩擦无法由网页端完整观察；
- 必须先建立可信 baseline 再进入增量飞轮。

## Do Not Use When

- 只修一个 bounded bug；
- 只新增一个 Workflow / Skill；
- 单个 Project 的普通资料整理；
- 日常小步 flywheel。

---

# Phase 0 — Freeze and declare scope

开始前冻结：

```text
PAOS main SHA
co-agent master SHA when relevant
canonical library root registry
active Project list
active / standby Agent list
current Coordinator TODO baseline
```

输出一个 `BASELINE-SNAPSHOT`。它不是复制所有文件，而是记录“我们从哪个事实状态开始迁移”。

禁止在 Phase 0 期间顺手清理文件。

Gate 0：所有参与者对 baseline identity 一致。

---

# Phase 1 — Independent local reconnaissance

本阶段网页端不假装掌握本地事实。

## s027

主执行盘点：

- canonical Workflow / Skill roots；
- roots registry；
- 当前 Library tree / Catalog；
- 已有 Workflow / Guide / Template / Skill；
- active Project roots；
- 每个 active Project 的 top-level tree；
- obvious duplicate / stale / legacy current-looking files；
- active Workstations；
- ENTRY / TODO / mailbox 状态；
- legacy entry / dual entry；
- local scripts / commands / generated files that current Runs actually rely on；
- 只有本地 Run 才能感知的 friction。

## s029

独立盘点，不抄 s027 结论：

- competing truth；
- duplicate Workflow / Guide / Skill；
- stale paths still referenced by Agent / docs / scripts；
- Project current-result ambiguity；
- workstation identity ambiguity；
- migration risk / rollback points；
- cold-start blockers；
- s027 可能忽略的 local-only friction。

## s031

只报告自己的专业面与工位：

- 自己当前 ENTRY / TODO / mailbox；
- Runtime-specific local assumptions；
- 哪些旧路径仍是 native reliability work 实际依赖；
- fresh-Runtime restart 可能遇到的问题。

不要求 s031 做全盘文件系统审计。

Gate 1：三份报告完成；未授权任何大规模 mutation。

---

# Phase 2 — Proposed TODO alignment

每个本地 Agent 必须把“发现”转换成 proposed TODO，而不是只写一篇散文报告。

每个 TODO 使用稳定 ID：

```text
M0-xxx  inventory / decision prep
M1-xxx  Workflow Library
M2-xxx  Skill Library
M3-xxx  Project cleanup
M4-xxx  Workstation migration
M5-xxx  integration / acceptance
```

每项至少包含：

```text
ID
Workstream
Object / path
Observed fact
Proposed action
Why
Risk
Dependencies
Done When
Evidence to return
Owner
Reviewer
Mutation class
Rollback / recovery
Decision needed
```

Mutation class 只允许：

```text
read-only
create
edit
move
archive
merge
generated-delete-candidate
retire-reference
```

`delete` 不作为默认 migration action。真正删除必须单独裁决。

### Alignment rule

s027 / s029 可以给出不同 TODO。

网页端 / Coordinator 的工作不是选一个照抄，而是：

```text
merge duplicate proposals
→ expose disagreements
→ resolve canonical decision
→ split oversized tasks
→ assign owner / reviewer
→ publish one Master Migration TODO
```

Gate 2：Master Migration TODO 发布，所有 destructive / path-changing task 都有明确 owner + reviewer + Done When。

---

# Phase 2.5 — Transition safety readback

Before the first canonical mutation, complete three transition checks:

### Entry authority

For every active migration Agent record exactly one current entry authority. A newly created fixed Workstation stays non-authoritative until reviewer + cold-start acceptance. If no stable entry exists, fresh Runtime startup is blocked; only the already-live Runtime may continue.

### Activation ownership

Record one current activation owner per Agent/source path. Do not switch Runtime activation ownership during Library/Project filesystem work. Any dual-wake ambiguity is a stop condition and is deferred to the dedicated Runtime migration batch.

### Dirty/untracked canonical claims

Classify primary-workspace modified/untracked paths that may carry current truth. The clean runner is allowed to execute migration code only after affected local-only facts are explicitly preserved/dispositioned.

Gate 2.5: no unresolved transition ambiguity affects the next mutation batch.

# Phase 3 — Dry-run migration maps

真正移动前，每个重型 workstream 先生成 dry-run map。

## Workflow / Skill

```text
current file / id
current role
target id / path
action
references to update
reason
risk
```

## Project Vault

```text
source path
current meaning
target canonical path
action
canonical truth after move
references to update
risk
```

## Workstation

```text
agent
current role
current ENTRY state
current TODO state
target role
ENTRY edit
TODO edit
legacy path retirement
cold-start test
```

Gate 3：Reviewer 确认 dry-run map 不会制造第二个 current truth，也不会把历史证据误当垃圾删除。

---

# Phase 4 — Execute bounded batches

迁移必须分批，不做一次性“大扫除提交”。

推荐批次：

```text
Batch A — Workflow Library
Batch B — Skill Library
Batch C — Project Vault 1..N
Batch D — Agent Workstations
Batch E — references / roots / catalogs
```

每个 Batch：

```text
pre-check
→ execute approved TODO subset
→ rebuild relevant Catalog/index
→ verify references
→ reviewer check
→ update local TODO
→ report exact result
```

一个 Batch 有 P1 时暂停后续依赖 Batch。

---

# Phase 5 — Reconcile reality after each batch

本地 Agent 必须允许出现：

> 执行前计划是 A，但真实文件摩擦证明应该改成 B。

但不能静默改路线。

出现新事实时：

```text
stop affected task
→ add TODO proposal / amendment
→ describe local evidence
→ classify P1/P2/decision
→ wait for alignment when canonical meaning changes
```

普通机械差异如果不改变 canonical policy，可由 owner 自行处理并在结果中说明。

---

# Phase 6 — Integration acceptance

当 M1–M4 都完成后：

- rebuild Workflow Catalog；
- rebuild Skill Catalog；
- validate roots；
- scan active Project top-level / canonical outputs；
- scan active Workstations；
- check legacy current references；
- check duplicate current truth；
- perform cold-start tests。

Gate 6：s029 独立复核无 P1。

---

# Phase 7 — Cutover preparation

只在 Stage 1 Gate 通过后准备：

- which old daily paths become historical-only；
- which docs / prompts / entry points must stop referencing them；
- which compatibility shims remain temporarily；
- cold restart order；
- rollback point。

真正 cutover 属于 Stage 2，不在本 Workflow 的前半段提前执行。

---

# Local Agent reporting protocol

## Start-of-phase report

```text
Current local facts
Current TODO
Unknowns
Risks
Planned reads only
Need decision?
```

## Before-mutation report

```text
Accepted TODO IDs
Exact paths / objects affected
Dry-run map
Expected canonical result
Rollback / recovery
Reviewer
```

## End-of-batch report

```text
Completed TODO IDs
Actual changes
Evidence
Unexpected friction
New TODO proposals
P1
P2
Current local TODO
Next safe action
```

## Why TODO reporting is mandatory

这次迁移中，TODO 不只是个人任务清单，也是网页端与本地事实之间的同步面。

网页端知道架构和 canonical intent；本地 Agent 知道：

- 哪些文件真的存在；
- 哪些路径仍被脚本引用；
- 哪些 Runtime / shell / filesystem 行为有摩擦；
- 哪些旧文件看似废弃但仍在真实 Run 使用；
- 哪些 migration action 在 Windows / WSL 上实际不可行。

因此：

```text
web architecture
+ local factual TODO
+ independent review
= migration decision
```

---

# Stop conditions

遇到以下情况立即停止 affected mutation：

- 无法判断哪个是 current truth；
- 同一对象出现两个合理 canonical 候选；
- 发现未登记的 active Project / active Agent；
- legacy file 仍被真实 Run 使用；
- move / archive 会破坏 active reference；
- local state 与 Master TODO 假设冲突；
- 存在两个可能同时唤醒同一 durable source/target 的 activation owner；
- clean runner 将忽略一个尚未分类的 dirty/untracked canonical claim；
- Agent 的 transition-day current entry 无法唯一确定；
- reviewer 与 executor 对 source-of-truth 有实质分歧；
- 需要删除非生成历史证据。

停止后回报 TODO amendment，不自行扩大权限。

---

# Closeout

本 Workflow 完成后至少留下：

```text
Master Migration TODO
Baseline Snapshot
Workflow migration report
Skill migration report
one cleanup report per active Project
Agent workstation migration report
Catalog evidence
cold-start evidence
open P2 / deferred list
Stage 2 cutover proposal
```

只有这些结果齐全，Stage 1 才能宣告完成。