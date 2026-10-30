# PAOS Workflow Library 运行与建库指南

> Workflow Library 不是 Prompt 仓库，也不是“每类工作一套 SOP”的方法库。它只保存长期 Agent / Coordinator 跨 Project 都必须遵守的工作管理协议。

本指南定义 V1.1 canonical Workflow Layer 的内容与使用规范。V1.1 已明确采用“两层方法架构”：Workflow Kernel 管业务运行与 TODO 主动性；Skill Library 管具体任务经验与能力。具体决策见 `docs/planning/v11-baseline-reconstruction/TWO-LAYER-WORKFLOW-SKILL-ARCHITECTURE.md`。

## 1. 两层方法架构与 Project 边界

```text
Project Vault
= 某个 Project 的事实、材料、Work、Decision、Artifact

Workflow Layer
= 员工/Coordinator 如何管理 Work
= 责任、TODO、协作、证据、验收、交接、standby

Skill Library
= 如何更好地执行具体工作
= 开发、研究、PRD、写作、Review、迁移等经验
```

判断规则：

- “这个 Project 里发生了什么 / 当前真相是什么？” → Project Vault。
- “员工现在应如何管理自己的责任和 TODO？” → Workflow Layer。
- “这类任务具体怎样做得更好？” → Skill Library。
- 一次 Run 的日志/报告先作为证据；只有重复有效的方法才提升。
- Workflow 可以调用 Skill，但不固化 Skill 的具体执行方法。

## 2. Workflow Layer 目标目录

物理目录仍沿用 A3a 的结构，但 V1.1 不追求填满它：

```text
<Workflow Library>/
├─ README.md
├─ Workflows/
│  ├─ wf-agent-work-cycle.md
│  └─ wf-coordinator-governance-cycle.md
├─ Guides/
│  ├─ guide-todo-and-self-management.md
│  ├─ guide-truth-collaboration-and-escalation.md
│  ├─ guide-evidence-review-and-acceptance.md
│  └─ guide-workflow-and-skill-boundary.md
├─ Templates/
│  ├─ tpl-work-brief.md
│  └─ tpl-handoff-summary.md
├─ CATALOG.md
└─ .paos/
   └─ catalog.json
```

这是 baseline hypothesis，不是数量 KPI。没有真实需要的 Guide/Template 可以不创建。

命名：

```text
Guide     guide-<topic>
Workflow  wf-<task-class>
Template  tpl-<artifact>
```

文件名应与稳定 ID 一致。ID 不因为标题、模型、Runtime 或版本变化而改名。

## 2.1 Canonical root and registry rules

V1.1 shared Library roots are Project-independent and are registered explicitly.

Target baseline:

```text
C:\Users\remo\Desktop\agent学习计划\PAOS-Libraries\workflow
C:\Users\remo\Desktop\agent学习计划\PAOS-Libraries\skill
```

The parent `PAOS-Libraries` is initialized as a standalone local Git repository before Workflow/Skill content migration. This provides the Stage-1 rollback/version history; no remote is required initially.

Important execution rule:

> `library roots set/show` resolves the default registry relative to the repo that runs the CLI.

Therefore a clean migration runner **must not** use the default when configuring the real installation. It must pass:

```text
--config C:\Users\remo\Desktop\agent学习计划\personal-agent-os\private-data\environment\library-roots.json
```

and verify the runner's own default registry remains absent/unregistered.

Repo `docs/workflows` is source/documentation material, not the shared canonical Library root.

## 3. Frontmatter

继续使用现有 `paos-workflow/v1`：

```markdown
---
schema: paos-workflow/v1
id: wf-agent-work-cycle
title: Agent Work Cycle
description: Universal long-lived Agent loop for responsibility, TODO, collaboration, evidence and closeout.
tags: agent, work, todo, governance
status: active
version: 1
---
```

状态只使用：

```text
candidate   新方法，可真实试用但还不是默认
active      已验证，可作为正常工作方法
deprecated  不再推荐，为旧引用保留
```

不要出现 `final`、`latest`、`v2-final`、`active-new`。版本变化用同一文件的 `version` 和 Git 历史表达。

## 4. Workflow / Guide / Template 的职责

### Workflow

Workflow 只回答：

> 一个长期 Agent / Coordinator 应怎样管理 Work，而不替它决定专业执行方法。

标准内容：

```text
Outcome
Role / Authority
Resume / Intake
TODO discipline
Execution boundary
Collaboration / Escalation
Evidence / Review
Closeout / Handoff / Standby
```

它不包含“怎样写 PRD”“怎样开发软件”“怎样研究市场”这种任务范式。

### Guide

Guide 是 Workflow Layer 的支持规则，回答跨多个 Work 都稳定成立的判断问题，例如：

- TODO 如何保持当前而不是变成历史日志；
- 哪些事实源优先；
- 什么时候找同事、Coordinator、Human；
- evidence 与 acceptance 的边界；
- 什么应该成为 Skill，什么不该升级进共享库。

Guide 不是第三层方法系统。

### Template

Template 只提供少量稳定的业务交接形状，例如 Work brief / handoff summary。不要为每类任务创建模板。

## 5. V1.1 Workflow Kernel

### `wf-agent-work-cycle`

```text
Resume / Wake
→ locate fixed Workstation
→ read current TODO + Mailbox + relevant live context
→ confirm current responsibility / authority
→ reconcile TODO and choose next meaningful action
→ execute with model judgment + Skills as needed
→ collaborate directly with relevant Agents
→ escalate only governance / priority / resource / decision issues
→ produce reviewable evidence / Artifact
→ update own TODO before reporting
→ continue / handoff / close / standby
```

核心要求：

- TODO 是执行事实，不是历史堆积；
- Agent 自己做个人行政，不靠 Coordinator 催；
- Runtime chat 不是长期真相；
- 被唤醒 ≠ 已读 ≠ 已完成 ≠ 已验收；
- 专业执行方式交给模型与 Skill。

### `wf-coordinator-governance-cycle`

```text
Read thin Project / Agent state
→ identify unresolved responsibility / review / decision
→ assign or clarify bounded Work
→ let Agents collaborate directly
→ receive meaningful result / blocker
→ request independent review where warranted
→ accept / return / integrate
→ close before spawning unnecessary new branches
→ surface only real judgment points to Human
```

Coordinator 不成为：

- 所有工作内容的中转站；
- 所有 Agent 的 TODO 维护者；
- 每次 Runtime 更换后的人工背景注入器。

## 6. Workflow Layer 支持文件

V1.1 baseline 不强制创建任何 Guide / Template。

原则：

- 能清楚放进两个 Workflow 的规则，不拆文件；
- Workflow/Skill 边界写进 Library README；
- authority / lifecycle 只引用 PAOS 权威，不复制；
- Work brief / handoff 的最小字段可以直接写进对应 Workflow；
- 只有真实 Run 反复证明“内联规则难以维护/发现”时才新增 Guide / Template。

空目录是合法 baseline。

## 7. Task-specific 方法全部进入 Skill 评估

下列旧候选不再作为 Workflow baseline：

```text
engineering-change
research-to-decision
product-definition
document-revision
independent-review
project-material-ingest
migration-planning
clean-writing
```

它们如果值得共享，应作为 Skill candidate 评估。

第一批只冻结两个已被大量工程 Run 证明的 Skill：

```text
skill-engineering-change
skill-independent-review
```

其中 `skill-engineering-change` 吸收 exact-head / focused/full verify / diff hygiene / risk-based real-machine smoke；`skill-independent-review` 吸收独立审查技法，但不拥有 acceptance authority。

其他候选继续保留，不为了“完整”而一次性建全。Skill 可以更具体、更有观点，也允许快速演进；Workflow Kernel 则保持少而稳定。

## 8. Library 准入与升级

一个新条目进入共享 Library，至少应满足一项：

- 同类任务重复出现；
- 一次重大事故暴露了可复用系统规则；
- 一个方法明显减少重复解释或返工；
- 它是长期 Agent 正常工作的基础协议。

否则先留在 Project。

Workflow Kernel Candidate → Active 建议满足：

1. 它描述的是跨任务稳定的业务运行规则，而不是专业执行方法；
2. 至少一次真实 Run 证明它解决了组织摩擦；
3. 有独立 Reviewer；
4. 不依赖具体 Runtime / Session / Project；
5. 没有和 Skill 重复拥有执行方法；
6. 改动后 fresh Runtime 能更容易继续 Work。

具体任务经验默认先成为 Skill candidate，而不是 Workflow candidate。

修改已有 Workflow：保持 ID、修改同一文件、`version +1`、重建 Catalog；不要创建 `-v2.md` / `-new.md`。

废弃先标 `deprecated` 并指出替代 Workflow ID。

## 9. Agent 如何消费 Library

Agent 每次醒来不要全文读取 Library。

正确路径：

```text
ENTRY
→ TODO / Mailbox / live context
→ 执行 wf-agent-work-cycle
→ 判断当前任务是否需要 Skill
→ 只加载相关 Skill
```

Coordinator 使用自己的 governance cycle。Workflow Kernel 应小到可以稳定掌握；Skill 才通过 Catalog 按需发现。

## 10. Workflow 与 Skill

```text
Workflow = business operating protocol
Skill    = execution experience / capability
```

例如“更新 TODO、何时升级 blocker、怎样完成 handoff”属于 Workflow；“如何写干净文档、如何做代码 Review、如何组织 PRD”属于 Skill。

## 11. Workflow 与 Project Vault

共享 Workflow 不承载 Project 内容。Project 特殊流程先留在 Project 中；只有脱离项目专有背景、已经重复可用后才提升到共享 Library。

推荐提升路径：

```text
Project / Run practice
→ repeated evidence
→ if universal Work-management rule: Workflow Kernel change
→ if execution method: Skill candidate
→ if Project-only: keep local
```

# Part II — 长期 Agent 工位重新编排

## 12. 从“某 Runtime 的 Agent”变成“某岗位的 Agent”

V1.1 以后稳定身份应该是岗位 / 责任，而不是 Runtime。

错误：

```text
s027 = OpenCode Agent
s031 = Codex Agent
```

正确模型：

```text
stable Agent role
+ current Runtime binding
```

### 3002-s027 — Implementation / Integration Engineer

长期职责：主要实现、本机真实环境执行、端到端 smoke、落地已批准方案、维护自己的 TODO / evidence / Artifact。

默认 Workflow：`wf-agent-work-cycle`。具体工程方法按需加载相关 Skills。

### 3002-s029 — Independent Reviewer / QA

长期职责：独立语义复核、focused regression、隐藏假设和边界、P1/P2/historical 区分；不默认替主执行者改代码。

默认 Workflow：`wf-agent-work-cycle`。Review 方法按需加载相关 Skills。

### 3002-s031 — Runtime Reliability Specialist

长期职责：native Runtime / Desktop / thread / wake 行为验证。当前主要经验在 Codex，但 Codex 不是身份本体。没有 Runtime 专项时正常 standby。

### 3002-s020

DSH 已退出 V1.1 主线。若当前没有新的稳定岗位，不为了保持 Agent 数量制造职责；保留历史工位，进入 standby / current-scope inactive。

### Coordinator

保持项目负责人身份，不与 Builder / Reviewer 合并。负责开 Work、定责任、组织 Review、接住结果、合并收口和 Human 判断点。

## 13. 工位继续保持最小

```text
Workstations/<agent-id>/
├─ ENTRY.md
├─ TODO.md
└─ mailbox/
```

本轮不要新增 `memory/`、`context/`、`knowledge/`、`outputs/`、`history/`。正式成果继续写到 `<Project>/Works/` 或明确的项目文件位置。

## 14. ENTRY 增加稳定岗位段落

现有 ENTRY 可人工增加：

```markdown
## 岗位

- Role：Implementation / Integration Engineer
- Default Responsibilities：
  - 实现明确边界的工程变化
  - 真实环境验证
  - 维护自己的 TODO 和交付证据
- Default Non-Responsibilities：
  - 不做最终产品方向裁决
  - 不替 Reviewer 做独立验收
- Default Workflows：
  - wf-agent-work-cycle
- Default Skills：
  - 按当前 Work 需要发现，不固化进岗位身份
```

只写长期稳定职责；不写当前 Work / Cycle / Runtime，不写完整 Prompt，不复制 Project 背景。

当前代码不会覆盖已有 ENTRY，所以现有工位迁移必须显式 review。先在 2–3 个长期 Agent 上验证价值，再决定是否固化到 generator。

## 15. TODO 只保存当前执行状态

迁移时不要把历史任务塞回 TODO。

无当前任务时允许：

```text
阶段：standby
进展：工位与 Library 已就绪
阻塞：无
下一步：等待新的 Mail / CAT / Work
```

不要制造“长期维护任务”来让 Agent 看起来 active。

## 16. 冷启动验收

模拟 Runtime 全换、新 Session 第一次进入这个 Agent，只给它 `ENTRY.md`。

合格标准：

1. 知道自己的稳定岗位；
2. 能找到 TODO；
3. 能找到 Mailbox；
4. 能找到 Workflow / Skill roots；
5. 能通过 live context 获取治理事实；
6. 能从 Catalog 找到适用 Workflow；
7. 不需要 Coordinator 再解释“你是谁、该干什么”；
8. 不依赖具体 Runtime 才能理解工作；
9. 知道正式结果写回 Project Vault；
10. 无任务时知道 standby。

# Part III — 迁移执行入口

Workflow / Skill 基线的实际迁移不再由本指南自带一套独立执行计划。

当前 authoritative execution source：

```text
docs/planning/v11-baseline-reconstruction/MASTER-MIGRATION-TODO.md
docs/planning/v11-baseline-reconstruction/PACKET-C1-WORKFLOW-SOURCE-MAPPING.md
```

原因：迁移阶段需要结合本地 dirty facts、Agent TODO、Project 状态和 reviewer evidence；这些状态会持续变化，不应该复制进长期 Operating Guide。

本指南只定义长期稳定的两层边界：

```text
Workflow Kernel
→ 管 Work / TODO / 协作 / 验收 / handoff

Skill Library
→ 管具体执行经验
```

Stage 1 完成后，本指南继续作为长期 Library 规则存在，而 migration packet 会退出日常入口。
