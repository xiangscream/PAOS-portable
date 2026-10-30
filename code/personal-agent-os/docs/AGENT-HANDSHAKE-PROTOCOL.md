# PAOS Agent 窄写入协议

本协议描述本地 Agent 通过用户明确授权对 PAOS 项目状态进行的窄写入。PAOS 不负责调用、启动或调度 Agent；Session 由项目页 Launcher 的 Open 流程创建，Agent 通过 Open 生成的 Prompt 完成接入。以下两个协议是独立的、由用户主动复制的窄写入口，不授予任何通用写权限。

手动粘贴承担目标 Agent 选择和最终授权，是正式交互设计，不是临时降级方案。

## 1. 用户主动授权的要求维护

项目页提供 `PAOS Project Requirement Update Protocol v1`。它解决的是：项目要求已经随工作推进发生变化，但用户不希望手动把内容逐字抄回项目页。

这不是 Open 流程的隐含权限。只有用户在项目页选择一个受管 Session，并主动点击“授权 Agent 维护当前要求”后，Agent 才能按该 Prompt 发起：

```text
POST http://127.0.0.1:8766/api/agent/project-requirement-update
Content-Type: application/json
```

一次点击的授权含义是：**Agent 可以主动检查并维护三个 human 要求字段**，不需要用户逐字给出新值。项目页的“本次补充说明”是可选的额外指导，留空不影响授权。

### 依据分层：为什么不能统称“已确认事实”

Prompt 携带的材料并非同一性质，因此分成两层：

| 层 | 内容 | 作用 |
|---|---|---|
| A. 承诺依据 | 现有 `human` 字段、用户本次补充说明、正式 Work 的目标/Done When、accepted Decision | 人类侧事实；只有这一层可以支撑新的或实质改变的承诺 |
| B. 辅助记录 | `generated`、acknowledgement、progress、交接说明、Ledger summary | 含 Agent 自报与系统记录；只能判断旧表述是否过期、补充阶段背景 |

分层的原因是防止自我强化。`progress` 只能证明“Agent 最近一次这样报告”，不能证明事情确实如此；`acknowledgement` 是 Agent 自己的复述；`generated` 通常也由 Agent 汇总。如果把它们统称“已确认事实”，就会出现：

```text
Agent 自报某结论
→ Prompt 把自报当成已确认事实
→ 下一个 Agent 据此改写人类当前承诺
```

这与 PAOS 的边界相反——`human` 字段代表人对项目的最终判断，不能由 Agent 的自我报告改写。`proposed` 状态的 Decision 只是 Agent 提案，人类尚未裁决，因此不属于 A 层。

**锚定规则：`current_commitment` 的新增或实质改变必须锚定至少一条 A 层承诺依据。** 只有 B 层、没有任何 A 层依据时，应保持原值或返回 `PAOS_REQUIREMENT_UPDATE_NOT_NEEDED`，必要时在回复中请用户确认，而不是替他决定。

请求最小结构：

```json
{
  "schema": "paos-agent-requirement-update/v1",
  "update_id": "up-唯一编号",
  "project_id": "3002",
  "expected_revision": 10,
  "session_ref": {
    "handshake_id": "历史握手编号（旧数据，可空）",
    "session_id": "受管 Session 的 PAOS ID"
  },
  "human_patch": {
    "current_commitment": "维护后确实需要变更时才填写",
    "ddl": "存在明确时间依据且需要变更时才填写"
  },
  "reason": "用户显式授权当前 Session 维护 OS 中的要求"
}
```

规则：

- `expected_revision` 必须匹配当前项目版本；冲突返回 `409`，不会写盘。
- `session_ref` 必须匹配当前项目的受管 Session（按 PAOS Session ID / handshake_id / 原生 session_id 匹配）；未匹配返回 `404`。
- `human_patch` 只认识 `original_requirement`、`current_commitment`、`ddl` 三个字段；维护后没有差异的字段省略，空字符串可以表示明确清空。
- 项目名称、Area、priority、状态、Work Item、Session、`generated`、主要文件和随后事项都不能通过该端点修改。
- 变化会刷新 `human.confirmed_at`，写入前自动备份并把 revision 加一；没有实际变化时返回 `changed=false`，不增加 revision。
- 未知额外字段按“核心严格、扩展宽容”处理：忽略且不落盘，但核心字段缺失或无效时先返回 `422`，不产生任何副作用。

### 字段维护边界

三个字段的依据要求不同，不能一律按“综合当前事实”处理：

| 字段 | 是否允许主动综合 | 依据要求 |
|---|---|---|
| `current_commitment` | 允许，但必须锚定 A 层 | 现有 `human`、用户本次补充说明、正式 Work 的目标/Done When、accepted Decision。字段为空或明显仍在描述已完成/过期阶段时应维护；仍准确时不改动。仅凭 B 层辅助记录不得改写。 |
| `ddl` | 不允许推测 | 只有明确日期依据（用户说明、accepted Decision、Work 完成定义中的时间、已确认周期）时才填写；否则留空。Agent 自报的进度或计划不是日期依据。 |
| `original_requirement` | 只允许转录 | 必须是用户原文或已有权威原始引用。不得把 Agent 的总结、复述或推断写成原始要求。 |

成功回执的第一行必须是：

```text
PAOS_REQUIREMENT_UPDATED
```

`PAOS_REQUIREMENT_UPDATE_NOT_NEEDED` 只用于两种情况：按 A 层维护后三个字段都没有差异；或缺少 A 层承诺依据（只有 B 层辅助记录）。**“用户本轮没有逐字提供新值”不是返回 NOT_NEEDED 的理由；“只有 Agent 自报进度”则是。** 调用失败、Session 不匹配或 revision 冲突时使用：`PAOS_REQUIREMENT_UPDATE_NOT_COMPLETED`。

用户仍可直接在项目页点“手动填写 / 修正”。这是备用入口，也是 Agent 无法访问本机端点时的恢复手段。

## 2. 用户主动授权的项目列表更新

项目页的“主要文件”和“随后事项”也有独立下属页。用户选择受管 Session 后，可以复制对应的 `PAOS_PROJECT_LIST_UPDATE_V1` Prompt。

端点：

```text
POST http://127.0.0.1:8766/api/agent/project-list-update
Content-Type: application/json
```

该端点的 `list_patch` 必须且只能包含一个字段：`key_files` 或 `next_items`。它们都是完整的新文本数组；不能同时改两类列表，也不能改项目的其他字段。请求同样必须带 `expected_revision`、受管 `session_ref` 和用户明确的 `reason`。

成功回执使用 `PAOS_PROJECT_LIST_UPDATED`；没有明确变化使用 `PAOS_PROJECT_LIST_UPDATE_NOT_NEEDED`；失败使用 `PAOS_PROJECT_LIST_UPDATE_NOT_COMPLETED`。写入前自动备份，列表无实际变化时不增加 revision。

手动编辑仍通过项目编辑器完成；Agent 更新入口只在下属页中出现，不会让项目主页再次堆叠大型操作面板。

## 3. 用户主动授权的项目进度维护

项目进度卡片提供独立的 `PAOS Project Progress Update Protocol v1`。它维护的是 Project 当前摘要，不是某个 Session 的 progress；Agent 不得用 Session Update 代替该接口。

```text
POST http://127.0.0.1:8766/api/agent/project-progress-update
Content-Type: application/json
```

请求使用 schema `paos-agent-project-progress-update/v1`，并携带 `update_id`、`project_id`、`expected_revision`、受管 `session_ref`、`generated_patch` 与 `reason`。`generated_patch` 只允许 `stage`、`progress_and_results`、`recent_change`、`current_gap`，至少包含一个字段；省略表示不改，空字符串表示明确清空。

该写入走与其他 Agent 窄合同相同的 canonical mutation：Session 必须 active 且已 Acknowledge；exact replay 返回首次 receipt；Restore 后旧 replay 返回 409；写入有 Ledger、operation receipt、备份和原子替换。无变化时不写 Ledger/receipt，也不消耗 update_id，之后可以用同一个 update_id 携带真实变化。

项目摘要可以综合当前 Work、Session 报告、最近 Ledger、accepted Decision 和 Request，但必须保留来源强度：Agent progress 只证明“Agent 最近一次这样报告”，不能自动写成客观完成；`progress_and_results` 中的确定结果应有 Artifact、测试、receipt、accepted Decision 或明确状态支持；proposed Decision 只能标记为待确认。

成功使用 `PAOS_PROJECT_PROGRESS_UPDATED`；无变化使用 `PAOS_PROJECT_PROGRESS_UPDATE_NOT_NEEDED`；失败使用 `PAOS_PROJECT_PROGRESS_UPDATE_NOT_COMPLETED`。

## 4. 典型流程

```text
项目页选定受管 Session
        ↓
用户主动复制“维护要求”“维护项目进度”或“更新列表” Prompt
        ↓
手动粘贴回原 Session
        ↓
Agent 只提交授权字段的 patch
        ↓
PAOS 校验 Session + revision，备份并原子写入
        ↓
Agent 返回 changed_fields 与新 revision
```
