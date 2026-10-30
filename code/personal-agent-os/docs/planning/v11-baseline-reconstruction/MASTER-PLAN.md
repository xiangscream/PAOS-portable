# PAOS V1.1 Canonical Baseline Reconstruction — Master Plan

> V1.1 的后半程不是继续补底层机制，而是把已经完成的 Workstation / Library / Mail / Agent Activation 机制，迁移成一个干净、唯一、可长期迭代的工作世界。

## 0. Why this stage exists

PAOS V1.1 已完成两类基础设施：

```text
A. 稳定工作世界的机制
   Project Vault layout
   fixed Agent Workstation
   Workflow / Skill Library foundation
   canonical library roots

B. 稳定通信与续步
   Workstation Mail
   Wake Contract
   OpenCode / Codex drivers
   Agent-first Mail / CAT Activation
```

现在缺的不是另一套机制，而是一次事实性的 baseline reconstruction：

```text
旧目录 / 旧 Guide / 旧 Workflow / 旧 Agent 入口 / 现存 Skill
            ↓
盘点、裁决、归位、迁移、冷启动验收
            ↓
一个 canonical V1.1 working world
```

如果不先做这一步，后续每次摩擦都无法判断是新 Workflow 本身的问题，还是旧资产没有迁干净。

## 1. Overall three-stage plan

### Stage 1 — Canonical Baseline Reconstruction

一次性建立相对完整、干净、可使用的 V1.1 基线：

1. Workflow Library 完整基线；
2. Skill Library 全量盘点与规范化；
3. 所有 active Project Vault 清洗；
4. 长期 Agent 的岗位 / ENTRY / TODO / mailbox 迁移；
5. roots、Catalog、引用、事实源统一；
6. 冷启动与迁移验收。

Stage 1 允许较重的整理与迁移，但要求每一批都可审查、可恢复、可验证。

### Stage 2 — Cutover / Legacy Retirement

冻结 V1.1 canonical baseline，把 active Projects / Agents 正式切到新路径：

```text
new canonical paths become daily paths
→ old daily paths become historical only
→ no silent dual-current source
→ fresh Runtime cold restart
```

retire 不等于删除历史。历史证据保留，但不再参与日常导航和当前事实判断。

### Stage 3 — Real Work Flywheel

只有 Stage 1/2 完成后才进入小步迭代：

```text
Real Work
→ observed friction
→ bounded Workflow / Skill / Project rule change
→ next comparable Run
→ verify whether friction fell
```

Stage 3 默认禁止无证据的大范围重构。

---

# Stage 1 — Workstreams

## Transition-day safety rules

These rules apply from planning merge until each Agent/Runtime/Project passes its own cutover gate:

1. **Entry authority:** creating a new fixed Workstation does not automatically make it current. Each Agent keeps one declared current entry until reviewer + cold-start acceptance flips authority to the fixed Workstation. Agents with no stable entry may continue an already-live Runtime, but may not fresh-start from an ambiguous entry.
2. **Single activation owner:** do not enable PAOS Wake and a legacy wake-capable adapter/bridge/hook for the same durable source/target at the same time. Filesystem/library migration does not change Runtime activation ownership.
3. **Dirty local facts:** clean runners provide executable code, not truth replacement. Modified/untracked files in the primary workspace that claim current/canonical meaning must be inventoried and dispositioned before the runner drives migration.
4. **Explicit registry target:** any Library registry mutation executed from a clean runner must pass the primary installation registry path explicitly; runner-local defaults may not create a second registry.
5. **Versioned shared roots first:** the external shared Library parent gets local Git history before Workflow/Skill content is imported.


## M0 — Reconnaissance & TODO Alignment

这是 Stage 1 的第一个 Gate：先盘点，先回报 TODO，先对齐，再移动。

原则：**先盘点，先回报 TODO，先对齐，再移动。**

本地 Agent 比网页端更接近真实文件系统、Runtime、历史副本和人工摩擦，因此 M0 不要求它们只执行既定脚本，而要求它们主动发现问题并回报建议任务。

### M0 outputs

每个参与 Agent 必须形成：

```text
1. LOCAL FACT INVENTORY
2. FRICTION / AMBIGUITY LIST
3. PROPOSED MIGRATION TODO
4. DO-NOT-TOUCH / NEEDS-DECISION list
```

所有 proposed TODO 在主线裁决前都是 proposal，不得因为 Agent 自己认为合理就直接大规模移动、归档、删除或改 canonical。

### M0 Gate

只有以下内容对齐后才能进入 M1–M4：

- canonical Workflow / Skill roots 已确认；
- active Projects 已确认；
- active / standby Agents 已确认；
- 主要 legacy / duplicate / stale paths 已列出；
- s027 / s029 的 TODO proposal 已汇总；
- Coordinator 当前 TODO 与本轮迁移任务不冲突；
- Human / web lead 已给出 reconciled Master Migration TODO。

---

## M0.5 — Transition Safety Readback

Packet A 后、第一批 mutation 前，必须补齐：

- transition-day entry authority；
- single activation owner map；
- dirty/untracked canonical-claim inventory；
- explicit primary registry target；
- versioned external Library root rollback。

M0.5 不做 path-changing mutation。它只决定第一批 mutation 是否安全。

---

## M1 — Workflow Library Reconstruction

目标不是建立一个“最小 Seed”，而是建立一个覆盖主要工作生命周期和高频工作类型的完整 V1.1 baseline。

### Coverage baseline

#### Employee lifecycle

- `wf-normal-agent-work-cycle`
- `wf-work-intake-and-planning`
- `wf-handoff-and-resume`
- `wf-work-review-and-closeout`

#### Delivery

- `wf-engineering-change`
- `wf-research-to-decision`
- `wf-product-definition`
- `wf-document-revision`

#### Quality

- `wf-independent-review`
- `wf-evidence-and-acceptance`

#### Workspace / learning

- `wf-project-material-ingest`
- `wf-lesson-to-library-promotion`

这 12 个是 baseline candidate set，不是强行锁死的最终目录。M0 如果发现已有高频工作类别明显缺失，可提出增补；若某条实际上应属于 Guide / Skill，也应在 M0/M1 纠正。

### Workflow contract

每个 Workflow 统一包含：

```text
Outcome
Use When
Do Not Use When
Inputs
Outputs
Preconditions
Flow
Gates
Collaboration
Skills
Evidence
Stop / Escalate
Closeout
```

### Workflow baseline quality

- 不依赖某个 Runtime / native session；
- 不复制 Project 专有背景；
- 不写成超长 Prompt；
- 不固定模型内部思考；
- 能让新 Runtime 只靠 Catalog + Workflow 执行；
- Output / Gate / Evidence 明确；
- 相似 Workflow 不互相竞争。

### Guides baseline

- `guide-agent-operating-principles`
- `guide-evidence-and-truth-sources`
- `guide-collaboration-and-escalation`
- `guide-project-file-placement`
- `guide-workflow-authoring`
- `guide-library-versioning-and-promotion`

### Templates baseline

- `tpl-work-brief`
- `tpl-review-report`
- `tpl-research-evidence-card`
- `tpl-decision-brief`
- `tpl-handoff-summary`
- `tpl-project-cleanup-report`

---

## M2 — Skill Library Reconstruction

Skill 不按数量建设，而按现有真实资产建设。

流程：

```text
inventory all current skills
→ identify duplicate / overlapping / project-specific skills
→ identify giant skills that should be split
→ normalize stable id + directory + SKILL.md
→ remove Project/Runtime assumptions
→ rebuild Catalog
→ connect Workflow references
→ preserve usage events
```

M2 完成标准不是“有多少 Skill”，而是：

- 所有当前有效 Skill 有唯一稳定身份；
- duplicate / obsolete / project-specific copies 有明确处理；
- Workflow 引用 stable Skill ID；
- Catalog 可重建；
- usage / usefulness 仍可继续积累；
- Skill 不承担 Workflow orchestration。

---

## M3 — Active Project Vault Cleanup

所有 active Project 都进入本轮；历史已关闭 Project 不要求全面重构。

基础布局：

```text
<Project>/
├─ Inbox/
├─ Materials/
├─ Works/
├─ Decisions/
├─ Workstations/
└─ Archive/
```

允许 Materials 在真实需要下使用：

```text
Materials/
├─ Inputs/
├─ Meetings/
├─ Research/
└─ References/
```

但不为填目录而建空分类。

### Cleanup objective

重点不是“看起来整齐”，而是消除 competing current truth：

```text
final.md
final2.md
final-new.md
reviewed.md
最新版.md
```

必须明确：

- canonical current result 是哪一个；
- 其他是 Archive、历史证据、材料还是可删除生成物；
- 以后 Agent 应从哪里读 current truth。

### Project migration map

每个 active Project 必须先生成映射表，再执行移动：

```text
source path
current meaning
target canonical path
action: retain | move | archive | merge | generated-delete-candidate
reason
source of truth after action
risk
owner
reviewer
```

默认优先 archive，不批量删除历史文件。

---

## M4 — Agent Workstation / Role Migration

长期 Agent 迁移到 role-first，而不是 Runtime-first。

当前建议：

```text
3002-s027  Implementation / Integration Engineer
3002-s029  Independent Reviewer / QA
3002-s031  Runtime Reliability Specialist
Coordinator Project Lead
3002-s020  current-scope inactive / standby unless real role appears
```

每个 active Agent 自己迁移自己的工位。主执行者不得替 Reviewer / Specialist 改其长期 ENTRY/TODO。

### ENTRY keeps stable facts

- stable role；
- default responsibilities；
- default non-responsibilities；
- default workflows；
- Workflow / Skill roots；
- Project / workstation navigation；
- live context entry。

ENTRY 不保存当前 Work / Cycle / Runtime / native session。

### TODO keeps current execution state

- current Work / current responsibility；
- stage；
- result-oriented progress；
- real blocker；
- next action；
- bounded task list。

没有任务时 `standby` 是合法状态，不制造永久维护 Work。

---

## M5 — Baseline Integration & Acceptance

### Library Gate

- Workflow / Skill Catalog 均可重建；
- duplicate stable ID = 0；
- Workflow / Guide / Skill 边界无明显竞争；
- active baseline 覆盖主要 Work 生命周期；
- 没有 Runtime / Project leakage。

### Project Gate

- 所有 active Project 使用标准 Vault；
- current canonical result 唯一；
- stale / duplicate / legacy 内容有明确归宿；
- Project 不复制共享 Workflow / Skill。

### Workstation Gate

- 所有 active Agent 有固定 Workstation；
- ENTRY role 清楚；
- TODO 当前；
- roots 正确；
- mailbox 可用；
- 旧入口不参与 daily navigation。

### Cold-start Gate

给 fresh Runtime 只提供：

```text
ENTRY
TODO
Workflow / Skill Catalog
live context access
```

它必须能独立回答：

- 我是谁；
- 当前在做什么；
- 去哪里找材料；
- 该选什么 Workflow；
- 何时找同事 / Coordinator / Human；
- 成果写到哪里；
- 结束时更新什么；
- 无任务时如何 standby。

---

# Stage 2 — Cutover / Legacy Retirement

Stage 1 Gate 通过后才执行。

1. Freeze canonical Workflow/Skill/Project/Workstation baseline。
2. active Projects 正式切换到 canonical paths。
3. legacy daily entry 退出导航，但保留必要历史证据。
4. existing Agent / Coordinator prompt 或 entry 不再引用 old paths。
5. 对 s027 / s029 / s031 做 fresh-Runtime cold restart。
6. 检查没有 silent dual-current source。

---

# Stage 3 — Flywheel

Stage 3 开始后，默认一个真实摩擦对应一个 bounded change。

重点观察：

- Human 重复解释次数；
- Coordinator 替 Worker 做个人行政次数；
- Agent 找不到材料次数；
- Agent 走错事实源次数；
- handoff 后重新理解项目成本；
- Runtime 更换后的恢复成本；
- Work 被退回的原因；
- Workflow / Skill 被真实消费与评分的情况。

只有真实 Run 证明某条规则、Workflow、Skill 或目录需要改时再改。

---

# Roles in this migration

## s027 — main migration executor

- local filesystem / real runtime inventory；
- migration mapping；
- approved batch execution；
- Catalog rebuild；
- own workstation migration；
- evidence collection。

## s029 — independent migration reviewer

- independent inventory；
- challenge duplicate truth / hidden legacy paths；
- review proposed TODO；
- review each migration batch；
- cold-start review；
- no default implementation on behalf of s027。

## s031 — specialist / self-migration

- inventory Runtime-specific friction that only local specialist sees；
- migrate its own workstation；
- later perform fresh-Runtime cold-start check；
- no broad migration unless explicitly assigned。

## Coordinator

- maintain Master Migration TODO；
- reconcile local reports；
- assign bounded migration batches；
- accept / return batches；
- keep Human attention on actual canonical decisions。

## Web lead

- decide architecture / canonical policy；
- reconcile s027/s029 local evidence；
- approve Master Migration TODO before destructive movement；
- decide GitHub/docs/code changes；
- decide Stage 1/2 Gates。

---

# Immediate next action

Do **M0 only**.

No large-scale move, archive, delete, rename, or canonical rewrite is authorized before M0 reports are reconciled.

s027 and s029 should independently return their local inventory + proposed TODOs. The next web-side action is to merge those into one Master Migration TODO, resolve conflicts, and then open the first executable M1/M2/M3/M4 batches.