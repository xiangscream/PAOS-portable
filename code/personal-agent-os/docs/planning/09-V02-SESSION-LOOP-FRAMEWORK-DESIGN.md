# Personal Agent OS v0.2：Session 工作与组织回写闭环设计书

版本：v0.2 设计冻结候选

日期：2026-08-05

基线分支：`agent/t-100-project-skeleton`

基线提交：`76f50d5`

实施方式：本文件负责冻结框架与验收；具体编码交给实施 Agent

---

## 0. 一句话目标

Personal Agent OS v0.2 要跑通：

```text
用户从项目中开启 Session
→ PAOS 自动编译这次需要的项目上下文与工作合同
→ 用户把 Prompt 手动粘贴给任意 Agent
→ Agent 完成专业工作，同时一次性回写进度、产物、请求和后续信息
→ 下一 Session 直接读取最新状态与 Delta，不再由用户重新讲一遍
```

它不是 Agent Runtime，不自动启动 Agent，不做实时多 Agent 聊天，也不接管人的最终决定。

v0.2 的价值不是增加一批对象名，而是减少四种真实成本：

1. 反复向新 Session 解释项目背景；
2. 人工把一个 Agent 的结果转述给另一个 Agent；
3. 工作结束后手动维护进度、资料和下一步；
4. 多个 Session 同时工作时互相覆盖或产生不同版本的“项目现状”。

---

## 1. 对用户思考的产品翻译

每个受管 Session 有双重职责：

```text
专业职责：完成调研、编码、设计、写作、审查等本职工作

组织职责：让 PAOS 中的项目状态比 Session 开始前更完整
```

组织职责并不等于写一篇长 Handoff。Agent 应通过一个结构化 Bundle 顺带提交：

- 本次进度与结论；
- 关联 Work Item 的状态；
- 新增或修改的重要产物；
- 阻塞和开放请求；
- 待人确认的决定候选；
- 剩余事项；
- 推荐的下一种职责；
- 对下一 Session 有用的短信息。

类比人类组织：员工不仅完成专业工作，还会发起评审、资料、协调或资源请求。但 PAOS 只登记和展示这些请求，不自动执行外部流程。

---

## 2. 当前基线与必须保留的资产

当前实现已经具备：

- 三个 Area：`routine`、`work`、`personal`；UI 分别显示“程序性工作”“工作”“项目”；
- 四位 Project ID：`1xxx / 2xxx / 3xxx`；
- Work Item ID：`<project_id>-wNNN`；
- `paos-project/v1` 项目 JSON；
- Work Item 与 Session 关联；
- 项目 `revision`、保存前备份、原子替换、恢复时 revision 单调递增；
- `handshake_id` 幂等握手；
- 人工授权的要求更新和项目列表更新；
- 本地 `127.0.0.1:8766` HTTP 服务、同源写保护与请求大小限制；
- 静态 HTML/CSS/原生 JavaScript 前端；
- 当前 137 项验证基线。

v0.2 必须复用这些资产，禁止为了“架构更漂亮”先重写。

### 2.1 本设计明确拒绝的无价值迁移

- 不把 Project ID 改成 `PRJ-2001`；
- 不把 Work Item ID 改成 `WORK-031`；
- 不立刻把内部 `personal` 改名为 `project`，UI 继续显示“项目”即可；
- 不把当前扁平目录一次性重排成 `backend/routes/services/storage/domain`；
- 不引入 React、Vue、数据库、消息队列、Docker 或第三方包；
- 不把现有握手、要求更新和列表更新接口直接删除。

这些改动不能直接减少用户的协作行政成本，因此不进入本阶段。

---

## 3. v0.2 第一阶段边界

### 3.1 本轮必须完成

```text
Open
→ Context Pack + Prompt
→ Acknowledge
→ Update Bundle（可选，可多次）
→ Close Bundle
→ Project Office + Delta
→ 下一 Session 接续
```

具体能力：

1. 六个稳定 Identity；
2. Quick / Managed / Collaborative 三种 Session mode；
3. Session 生命周期；
4. Brief / Standard / Deep Context Pack；
5. Agent 一次提交一个 Update Bundle；
6. Artifact、Request、Decision Proposal 和 Work 更新；
7. 逻辑 Append-only Ledger；
8. operation 幂等；
9. revision 与 touched-path 冲突判断；
10. Project Office 最小投影；
11. 项目页 Session Launcher；
12. 只读 Session 页面；
13. v1 项目安全迁移与旧接口兼容；
14. 完整生命周期、幂等、并发和恢复测试；
15. Agent 无法访问 localhost 时的手动回贴通道。

### 3.2 明确暂缓

- 自动调用或启动 Codex、Claude、OpenCode、WorkBuddy；
- CLI 适配器和中央调度器；
- Agent 实时聊天室；
- 自动扫描所有 Session 日志；
- 本地小模型摘要；
- 全量 Vault 读取、RAG、向量库和知识图谱；
- 模型自动评分与自动路由；
- 自动修改 Skill；
- NAS、云同步和远程控制；
- 多人账号与权限系统；
- 任意项目树和动态 Area；
- 自动登记所有文件；
- 强制每个 Session 写长 Handoff。

这些内容保留为技术储备，不得成为当前实现的依赖。

---

## 4. 冻结的概念关系

```text
Area
└─ Project：长期上下文与正式状态容器
   ├─ Work Item：一个可完成的成果
   ├─ Session：一次岗位任职，可关联多个 Work Item
   ├─ Artifact：重要资料或产物的引用
   ├─ Request：跨 Session 的信息、评审、协调或资源请求
   ├─ Decision Proposal：Agent 建议，尚不是人的正式决定
   └─ Ledger Event：已经发生的组织状态变化
```

关键不变量：

- Session 不是 Work Item 的第四级子任务；它是一次工作实例和证据来源；
- Work Item 与 Session 是多对多；
- 一条 Session 可分别登记到多个 Project，但每个 Project 保存自己的关联理由；
- Project 保存正式状态，不保存完整聊天正文；
- Artifact 默认只保存路径、用途和来源，不复制原文件内容；
- Decision Proposal 只有经人确认后才能成为正式决定；
- Agent 不得通过 Update Bundle 修改 `human` 字段、项目名、Area、优先级或安全边界。

---

## 5. Identity、Model、Runtime、Session 必须分离

```text
Identity：这次承担什么职责
Model：这次使用什么能力底座
Runtime：在哪个 Agent 产品或执行环境工作
Session：这次实际工作实例
```

第一版只提供六个 Identity：

| ID | 中文名 | 主要职责 | 默认 Context |
|---|---|---|---|
| `project-framer` | 项目开启者 | 理解、发散、边界、第一版计划 | Deep |
| `implementer` | 实施者 | 在明确边界内交付、验证和回写 | Standard |
| `specialist` | 专项专家 | 图像、文档、硬件、数据等特殊能力 | Standard |
| `reviewer` | 审查者 | 按完成定义独立验收、发现遗漏 | Deep |
| `integrator` | 整合者 | 汇总多 Session、消解冲突、阶段收口 | Deep |
| `steward` | 维护者 | 低频修复状态漂移和遗留记录 | Standard |

Identity 是工作合同，不是安全身份，也不与模型品牌绑定。

第一阶段不实现 Model Registry 和自动推荐。Session 只保存用户填写的：

```json
{
  "runtime_id": "codex-desktop",
  "model_id": "gpt-5.x",
  "agent_label": "Codex"
}
```

`model_id` 允许为空；模型和 Runtime 的选择权始终在用户。

---

## 6. 总体架构

```text
┌─────────────────────────────────────────────┐
│ Human UI                                    │
│ Projects / Project / Session                │
└──────────────────────┬──────────────────────┘
                       │ 创建并复制 Prompt
┌──────────────────────▼──────────────────────┐
│ Session Gateway                             │
│ Open / Ack / Update / Close / Get           │
└──────────────┬──────────────────┬───────────┘
               │                  │
┌──────────────▼──────────┐ ┌────▼────────────┐
│ Context Compiler        │ │ Identity Registry│
│ Brief/Standard/Deep     │ │ 六个静态合同      │
└──────────────┬──────────┘ └────┬────────────┘
               │                  │
┌──────────────▼──────────────────▼────────────┐
│ Project Store v2                             │
│ Project / Work / Session / Artifact / Request│
│ Decision / Ledger / Operation Receipt        │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│ Projection                                 │
│ Project View / Office / Delta / Session View │
└─────────────────────────────────────────────┘

外围接入：人工复制 Prompt + 本地 HTTP API
```

---

## 7. 存储裁决：先保证原子，再追求物理分层

外部技术草案建议立即使用：

```text
state.json + ledger.ndjson + operations.ndjson + context-packs/
```

该布局在长期是合理的，但第一阶段会引入多文件事务问题：状态写成功而 Ledger 或 Receipt 写失败时，重试和恢复会变复杂。

因此 v0.2 第一阶段采用：

```text
private-data/project-registry/
├─ projects/<project_id>.json
├─ backups/projects/<project_id>/...
├─ context-packs/<project_id>/<context_pack_id>.json
└─ focus.json
```

其中 `<project_id>.json` 同时保存：

- Canonical State；
- 逻辑 Append-only Ledger；
- operation receipt。

这样一次 Update Bundle 的状态变化、事件和幂等回执可以在同一个临时文件中构造，然后沿用现有 `_atomic_write()` 一次替换。

Context Pack 是只读快照，可在状态提交前用确定性 ID 写入；即使主状态写入失败，最多留下一个可安全清理的孤立快照，不会污染正式状态。

### 7.1 何时再拆 NDJSON

满足任一条件时再设计物理 Ledger：

- 单项目 Ledger 超过 1000 条；
- 项目 JSON 超过 5 MB；
- 真实并发使整文件写入成为可测瓶颈；
- 已经有可靠的事务恢复和重建工具。

在此之前，独立 NDJSON 不是 v0.2 成立条件。

---

## 8. `paos-project/v2` 数据结构

继续使用当前 `projects/<四位项目号>.json`，不改路径和 ID。

```json
{
  "schema": "paos-project/v2",
  "id": "3002",
  "name": "Personal Agent OS",
  "area": "personal",
  "project_type": "continuous",
  "status": "active",
  "priority": 1,
  "root_path": "...",

  "human": {
    "original_requirement": "...",
    "current_commitment": "跑通单 Session 工作与组织回写闭环",
    "ddl": "",
    "confirmed_at": "..."
  },

  "generated": {
    "stage": "v0.2 单 Session 闭环",
    "progress_and_results": "...",
    "recent_change": "...",
    "current_gap": "..."
  },

  "next_items": [],
  "key_files": [],

  "work_items": [
    {
      "id": "3002-w005",
      "title": "建立 Session Update Bundle",
      "objective": "让 Agent 一次提交专业结果和组织更新",
      "done_when": ["原子应用", "幂等重试", "冲突可读"],
      "status": "doing",
      "priority": 1,
      "depends_on": [],
      "note": "",
      "created_at": "...",
      "updated_at": "...",
      "last_updated_by_session": ""
    }
  ],

  "sessions": [
    {
      "id": "3002-s001",
      "handshake_id": "",
      "mode": "managed",
      "identity_id": "implementer",
      "model_id": "",
      "runtime_id": "codex-desktop",
      "agent_label": "Codex",
      "work_item_ids": ["3002-w005"],
      "request_ids": [],
      "mission": {
        "objective": "实现 Update Bundle",
        "done_when": ["完整生命周期测试通过"]
      },
      "entry": {
        "project_revision": 12,
        "context_pack_id": "3002-cp001",
        "context_level": "standard"
      },
      "runtime_session": {
        "environment": "Windows",
        "title": "",
        "session_id": "",
        "source_path": ""
      },
      "acknowledgement": null,
      "progress": {
        "status": "not_started",
        "summary": "",
        "percent": null,
        "blockers": [],
        "next_actions": []
      },
      "status": "pending_ack",
      "started_at": "...",
      "last_active_at": "...",
      "closed_at": null,
      "close_result": null
    }
  ],

  "artifacts": [],
  "requests": [],
  "decisions": [],
  "ledger": [],
  "operation_receipts": {},

  "revision": 13,
  "updated_at": "..."
}
```

### 8.1 状态枚举

Work Item：

```text
todo / doing / blocked / review / done / cancelled
```

Session：

```text
pending_ack / active / completed / partial / blocked / abandoned / historical
```

Request：

```text
open / resolved / cancelled
```

Decision：

```text
proposed / accepted / rejected / superseded
```

### 8.2 数据所有权

Agent Update Bundle 允许修改或追加：

- 当前 Session 的 `progress`、`runtime_session`、`status` 和关闭结果；
- 当前 Session 已关联 Work Item 的 `status` 与 `note`；
- `generated.stage / progress_and_results / recent_change / current_gap`；
- Artifact；
- Request；
- Decision Proposal；
- Project Framer / Integrator 创建的新 Work Item；
- Ledger Event 与 operation receipt（服务端自动生成）。

Agent Update Bundle 禁止修改：

- `human`；
- Project `id / name / area / project_type / priority / root_path`；
- 已确认决定；
- 其他 Session 的数据；
- 与当前 Session 无关联的 Work Item；
- `key_files` 和 `next_items` 的整表替换。

人工字段仍使用现有“更新 OS 要求”授权链路。重要文件通过 Artifact 登记；`key_files` 是否升级由人或后续 Integrator 流程处理。

### 8.3 人工编辑不能覆盖系统状态

当前 v1 编辑器会重建整份 `work_items` 和 `sessions` 数组。进入 v2 后，这会丢失 Identity、Mission、Context、Progress、Ledger 等系统字段，因此禁止继续用整份 Project PUT 覆盖 v2 状态。

v2 继续复用现有 URL：

```http
PUT /api/projects/{project_id}?revision=N
```

但正文改为窄的人工更新契约：

```json
{
  "schema": "paos-project-manual-update/v1",
  "project_patch": {
    "name": "...",
    "status": "active",
    "priority": 1,
    "root_path": "..."
  },
  "human_patch": {},
  "generated_patch": {},
  "key_files": [],
  "next_items": [],
  "work_items": [],
  "session_corrections": []
}
```

服务端在当前 v2 State 上合并这些人工字段，始终保留：

- Session 的 Identity、Mission、Context、Progress、状态和关闭结果；
- Artifact、Request、Decision；
- Ledger 与 operation receipt；
- 所有服务端生成的 ID 和时间戳。

`session_corrections` 仅允许按 PAOS Session ID 修正 Agent 原生标题、原生 Session ID、环境、source path、关联理由；不得修改生命周期状态和组织回写内容。

v1 Project 仍接受原有完整 `paos-project/v1` PUT，确保尚未迁移的项目继续可用。

---

## 9. Session 生命周期

### 9.1 Quick

```text
Open → active → Close
```

- 跳过 Acknowledge；
- 可以完全不调用中间 Update；
- 一次 Close Bundle 完成本职结果与组织回写；
- 不要求长 Handoff。

### 9.2 Managed

```text
Open → pending_ack → Acknowledge → active
     → Update（0..N）→ Close
```

- 必须确认理解目标与边界；
- 可以多次更新；
- Close 必须给出结果摘要和剩余事项。

### 9.3 Collaborative

第一版允许创建并按 Managed 运行，同时在 Context Pack 中额外显示其他 Active Session 与开放 Request。

本阶段不实现自动 Work Claim、自动派发或自动 Integrator。UI 必须标注“协同信息可见，仍由用户手动粘贴 Prompt”。

### 9.4 关闭后的规则

- 普通 Update 只允许 `active` Session；
- `pending_ack` 只能 Acknowledge 或 Abandon；
- 关闭后不能继续普通 Update；
- 继续工作应创建新 Session；
- `reopen` 暂不做，防止历史状态模糊；
- v1 迁移的旧 Session 使用 `historical`，不出现在 Active Session。

---

## 10. API 合同

所有新写接口继续执行现有：

- 只允许 localhost 同源；
- `Content-Type: application/json`；
- 独立请求体大小限制；
- 路径参数与正文 ID 必须一致；
- 写入前完整校验；
- 失败不得创建 backup、revision 或部分对象。

核心字段采用严格校验；未知顶层字段默认忽略但不保存。未来需要扩展时必须提升 schema 版本，或使用明确的 `extensions` 容器，不能让任意字段悄悄进入正式状态。

`operation_id` 统一使用：

```text
^op-[A-Za-z0-9._:-]{4,120}$
```

### 10.1 Identity

```http
GET /api/identities
GET /api/identities/{identity_id}
```

Identity 来自仓库内静态配置，不写入 `private-data`。

### 10.2 Open Session

```http
POST /api/projects/{project_id}/sessions
```

```json
{
  "schema": "paos-session-open/v1",
  "operation_id": "op-open-...",
  "base_revision": 12,
  "work_item_ids": ["3002-w005"],
  "request_ids": [],
  "mode": "managed",
  "identity_id": "implementer",
  "model_id": "",
  "runtime_id": "codex-desktop",
  "agent_label": "Codex",
  "context_level": "standard",
  "mission": {
    "objective": "实现 Update Bundle",
    "done_when": ["完整生命周期测试通过"]
  },
  "extra_materials": []
}
```

返回：

```json
{
  "ok": true,
  "session": {},
  "context_pack": {},
  "prompt_markdown": "...",
  "receipt": {
    "operation_id": "op-open-...",
    "project_revision": 13
  }
}
```

Open 在用户点击“创建并复制 Prompt”时发生。它先在 PAOS 中创建 Session，再把 Prompt 复制给用户；即使用户没有粘贴，项目页也能看到一个待接入 Session，并允许人工标记 abandoned。

### 10.3 Acknowledge

```http
POST /api/projects/{project_id}/sessions/{session_id}/acknowledge
```

```json
{
  "schema": "paos-session-ack/v1",
  "operation_id": "op-ack-...",
  "base_revision": 13,
  "session_id": "3002-s001",
  "runtime_session": {
    "environment": "Windows",
    "title": "Agent 原生标题",
    "session_id": "Agent 原生 Session ID；未知留空",
    "source_path": "未知留空"
  },
  "understood_objective": "...",
  "understood_boundaries": [],
  "proposed_first_steps": [],
  "detected_risks": []
}
```

成功后 Session 进入 `active`。

### 10.4 Update Bundle

```http
POST /api/projects/{project_id}/sessions/{session_id}/updates
```

```json
{
  "schema": "paos-session-update/v1",
  "operation_id": "op-update-...",
  "base_revision": 14,
  "session_id": "3002-s001",

  "progress": {
    "status": "working",
    "summary": "完成数据校验，正在补冲突测试",
    "percent": null,
    "blockers": [],
    "next_actions": ["补生命周期测试"]
  },

  "generated_patch": {
    "stage": "v0.2 实施",
    "progress_and_results": "Session API 主流程完成",
    "recent_change": "新增 Update Bundle",
    "current_gap": "缺并发测试"
  },

  "work_updates": [
    {
      "work_item_id": "3002-w005",
      "status": "doing",
      "note": "主流程完成，等待验证"
    }
  ],

  "work_creations": [],

  "artifacts": [
    {
      "path": "attention-dashboard-v1-static/session_service.py",
      "type": "code",
      "purpose": "Session 生命周期与原子 Bundle",
      "work_item_ids": ["3002-w005"],
      "replaces": null
    }
  ],

  "requests": [
    {
      "request_type": "review",
      "target_identity_id": "reviewer",
      "description": "审查幂等与 revision 冲突"
    }
  ],

  "request_updates": [],

  "decision_proposals": [],
  "note_for_next_session": "重点复查重试是否重复创建 Artifact"
}
```

除 `schema / operation_id / base_revision / session_id` 外，其余字段可空或省略。

`progress` 的三种情形必须区分：

- 键不存在（省略）：保留 Session 已有 progress，不视为清空；
- 显式 `null`：重置为初始 `not_started`；
- 出现且非法（status 不在枚举内、字段类型不对）：整体拒绝，返回 422 ValidationError，不落盘。

服务端必须自动生成：

- Artifact / Request / Decision / Work Item ID；
- 时间戳；
- touched paths；
- Ledger Event；
- request hash；
- 新 revision；
- receipt。

Agent 不填写能由服务端确定的行政字段。

### 10.5 Close Bundle

```http
POST /api/projects/{project_id}/sessions/{session_id}/close
```

Close 请求复用 Update Bundle 的可选字段，额外增加：

```json
{
  "schema": "paos-session-close/v1",
  "operation_id": "op-close-...",
  "base_revision": 15,
  "session_id": "3002-s001",
  "result": "completed",
  "result_summary": "Update Bundle 已实现并验证",
  "remaining_work": [],
  "recommended_next_identity_id": "reviewer"
}
```

`result` 允许：

```text
completed / partial / blocked / abandoned
```

Quick Session 可以在 Close 中携带全部 progress、work_updates、artifacts、requests 和 decision_proposals。

### 10.6 查询与投影

```http
GET /api/projects/{project_id}/sessions/{session_id}
GET /api/projects/{project_id}/office
GET /api/projects/{project_id}/delta?since_revision=12
```

Project Office 返回：

```json
{
  "active_sessions": [],
  "open_requests": [],
  "pending_decisions": [],
  "pending_integration": [],
  "recent_delta": [],
  "blocked_work_items": []
}
```

Office 是投影，不另存一份状态。

---

## 11. Update Bundle 的权限与行为

### 11.1 Work 更新

- Session 只能更新自己 `work_item_ids` 中的 Work；
- `work_creations` 只允许 `project-framer` 或 `integrator`；
- 新 Work ID 由服务端按当前最大后缀生成；
- 删除 Work 不在 Agent Bundle 中支持；
- Work 进入 `done` 时，必须有非空 `note` 或 Close `result_summary`。

### 11.2 Artifact

只登记重要产物，不扫描全部文件。

必须包含：

- path；
- type；
- purpose。

服务端补充：

- artifact ID；
- project ID；
- source session ID；
- work item IDs；
- created_at；
- status=`current`。

### 11.3 Request

第一版类型：

```text
information / artifact / review / decision / coordination / resource / clarification
```

Request 只登记需求，不自动启动下一 Agent。用户从 Project Office 看到它，再手动启动对应 Identity。

Open Session 可携带 `request_ids`，表示本 Session 接受处理哪些开放请求。Update / Close 中的 `request_updates` 只能修改这些请求：

```json
{
  "request_id": "3002-r001",
  "status": "resolved",
  "resolution": "已完成独立审查，结论见 3002-a004"
}
```

Project Office 的 Request 卡提供“以此请求启动 Session”，只是预填 `request_ids`、推荐 Identity 和 Mission，仍由用户复制 Prompt 并手动粘贴。

### 11.4 Decision Proposal

Agent 只能创建 `proposed` Decision。接受、拒绝和变成 Project 正式边界必须由人工操作；第一阶段前端只展示 pending，不自动确认。

### 11.5 `generated_patch`

允许 Agent 增量更新四个 generated 字段，但不能静默删除已有信息。

第一版采用字段级替换，并要求请求中给出完整新文本。Prompt 必须提醒 Agent：先读取当前字段，再保留仍有效内容并写出更新后的完整值。

如果真实使用发现长文本经常冲突，再设计更细粒度的结构，不在第一轮预埋。

---

## 12. Context Pack

### 12.1 固定组成

```text
OS 通用协议
+ Project 当前状态
+ 关联 Work Item
+ Identity 工作合同
+ 最近 Delta
+ 活动 Session
+ 开放 Request
+ Artifact / key_files 引用
+ 本次组织回写合同
```

### 12.2 Brief

- 当前唯一承诺与 DDL；
- 本次 Work、目标和 Done When；
- 必需资料；
- Open 时的 project revision；
- Ack / Close 接口；
- Agent 不得修改的边界。

适合 Quick Session。

### 12.3 Standard

在 Brief 基础上增加：

- Project generated 状态；
- 项目原始要求；
- 相关 Work 的已有 Artifact；
- 最近 Delta；
- Active Session；
- Open Request。

适合一般实施。

### 12.4 Deep

在 Standard 基础上增加：

- 全部未关闭 Work；
- 已确认决定；
- 相关历史 Session 的关闭摘要；
- pending Decision；
- pending integration；
- 更完整的资料索引。

适合 Framer、Reviewer 和 Integrator。

### 12.5 材料只提供引用

Context Pack 默认不读取或复制外部文件内容，只保存：

```json
{
  "path": "...",
  "reason": "为什么与本次任务相关",
  "required": true
}
```

Agent 拥有本机文件访问能力时按需读取；网页 Agent 由用户另行上传 ZIP。Context Compiler 不成为 RAG。

### 12.6 可复查性

Open 时保存：

```text
context-packs/<project_id>/<context_pack_id>.json
```

文件包含结构化 Context 与当时实际复制的 `prompt_markdown`，从而回答“这个 Agent 当时实际看到了什么”。不保存外部文件正文。

---

## 13. 接入 Prompt：真正的跨 Agent API 合同

Prompt 必须明确告诉新 Session：

1. PAOS 是本次工作的组织事实源；
2. 本次 Project、Work、Identity、Mission 和 Done When；
3. 必读材料及其理由；
4. 禁止修改的人工字段和边界；
5. Managed Session 先 Acknowledge，再开始实质工作；
6. 简单任务可以不做中间 Update，直接 Close；
7. Update / Close 时顺带登记进度、重要产物、请求和下一步；
8. 不编造原生 Session ID、标题或路径；未知必须留空；
9. 每次调用使用唯一 operation ID；
10. revision 冲突时读取返回 Delta，合并后用新 operation ID 重提；
11. 最终向用户报告规范回执和新 revision；
12. 无法访问本机 API 时明确返回未完成标记，并给出可手动粘贴的 JSON，不得假装写入成功。

### 13.1 两种 Transport，共用同一合同

```text
local_http
Agent 直接 POST 本机 API，读取正式 receipt

manual_paste
Agent 不能访问 localhost，输出结构化 envelope；用户粘贴回 Session 页面，由浏览器代为 POST
```

手动回贴格式：

```text
PAOS_MANUAL_WRITEBACK_V1
{
  "action": "acknowledge",
  "payload": {
    "schema": "paos-session-ack/v1",
    "operation_id": "op-ack-...",
    "base_revision": 13,
    "session_id": "3002-s001"
  }
}
```

`action` 只允许 `acknowledge / update / close`。Session 页面从当前 URL 确定 Project 和 Session，不接受 Agent 提供任意请求 URL。浏览器仍调用相同后端合同，所以校验、幂等、revision、备份和权限完全一致。

这个通道是 ChatGPT 网页端等无法访问本机服务的正式兼容方式，不是第二套数据模型。

### 13.2 成功标记

```text
PAOS_SESSION_ACKNOWLEDGED
PAOS_SESSION_UPDATED
PAOS_SESSION_CLOSED
PAOS_SESSION_WRITEBACK_NOT_COMPLETED
```

HTTP 直接成功时使用前三种完成标记。仅生成了 manual-paste envelope 时，必须明确说“尚未写入 PAOS”，直到用户在 Session 页面粘贴并看到服务端 receipt。

### 13.3 “行政工作”必须保持轻量

- Quick Session：最多一次 Close 调用；
- Managed Session：只有状态真实变化时才 Update；
- 进度百分比可空；
- 没有 Request、Artifact 或 Proposal 时传空数组；
- 完成任务不再额外写长 Handoff；
- partial / blocked / collaborative 才要求明确剩余工作和下一 Identity。

---

## 14. Ledger、幂等、revision 与冲突

### 14.1 Operation 幂等

每个写请求必须带 `operation_id`。

服务端计算规范 JSON 的 SHA-256：

```text
相同 operation_id + 相同 hash
→ 返回原 receipt，不增加 revision，不重复创建对象

相同 operation_id + 不同 hash
→ 409 operation_conflict
```

receipt 与状态在同一项目 JSON 中原子写入。

### 14.2 Ledger Event

每次成功写操作只追加一条逻辑事件：

```json
{
  "event_id": "3002-e014",
  "event_type": "session.update.applied",
  "project_id": "3002",
  "session_id": "3002-s001",
  "operation_id": "op-update-...",
  "base_revision": 14,
  "revision": 15,
  "timestamp": "...",
  "touched_paths": [
    "/sessions/3002-s001/progress",
    "/work_items/3002-w005/status",
    "/artifacts/3002-a001"
  ],
  "summary": "完成主流程并登记一个代码产物"
}
```

Ledger 不保存聊天全文和完整 diff。

### 14.3 touched-path 冲突

如果 `base_revision == current_revision`，正常应用。

如果 `base_revision < current_revision`：

1. 计算本次 Bundle 的 touched paths；
2. 收集 Ledger 中 revision 大于 base 的 touched paths；
3. 两组路径没有冲突时，自动基于最新状态应用；
4. 精确相同或一方为另一方父路径时，返回 409。

例如：

```text
Session A：/work_items/3002-w005/status
Session B：/work_items/3002-w006/status
→ 不冲突

Session A：/work_items/3002-w005/status
Session B：/work_items/3002-w005/status
→ 冲突
```

409 响应必须包含：

```json
{
  "error": "revision_conflict",
  "current_revision": 18,
  "conflicting_paths": [],
  "delta_since_base": []
}
```

### 14.4 原子应用顺序

在一个 ProjectStore 锁内：

```text
校验请求
→ 检查 operation receipt
→ 读取和校验项目
→ 校验 Session 状态与权限
→ 计算 touched paths / 冲突
→ 深拷贝当前状态
→ 在副本应用完整 Bundle
→ 校验完整 v2 状态
→ 生成 event + receipt
→ 在副本追加 event + receipt
→ 备份当前文件
→ _atomic_write 一次替换项目文件
→ 返回 receipt
```

任一步失败都不得写盘。

### 14.5 恢复

继续复用当前备份机制：

- 每次成功 mutation 前备份；
- restore 也先备份当前版本；
- 恢复后 revision=current+1；
- 恢复追加 `state.corrected` 事件；
- 旧 operation receipt 不能因为恢复而被再次执行。

---

## 15. v1 → v2 迁移（已完成，v0.4 起 v1 不再存在）

### 15.1 执行记录

2026-08-06，全部 8 个真实项目已迁移到 `paos-project/v2`：

| 项目 | revision | 项目 | revision |
|---|---|---|---|
| 1001 | 1 → 2 | 2001 | 2 → 3 |
| 1002 | 1 → 2 | 2002 | 4 → 5 |
| 1003 | 3 → 4 | 3001 | 1 → 2 |
| 1004 | 1 → 2 | 3002 | 10 → 11 |

迁移前在 `private-data/project-registry/pre-v2-snapshot-20260806-095423/` 留了独立快照并记录 SHA256；迁移后逐个验证通过 `validate_project_v2`，且 `name` / `human` / Work Item 数 / Session 数全部守恒。

### 15.2 v0.4 的清理

按开发准则第 1 条（不以维护向后兼容性为目标），迁移完成后已删除：

- `scripts/migrate_project_v1_to_v2.py`
- `project_store.validate_project` / `update_project`（v1 整份 PUT）/ `is_v2` / `migrate_v1_to_v2_file` / v1 handshake 主体 / `_handshake_receipt`
- `project_store_v2.migrate_v1_to_v2`、常量 `PROJECT_SCHEMA`（v1）
- 前端 13 处 `schema === "paos-project/v2"` 判断、v1 Session 卡片、v1 编辑器分支、v1 整份 PUT payload 构造、`buildSavedHuman` / `humanFieldsChanged`
- 全部 v1 测试用例与 v1 fixture（fixture 已换成 v2 形态）

`empty_project` 现在直接产出 v2 骨架，是唯一的项目骨架定义点；`empty_v2_project` 只是它的别名。

**如果将来还需要读一个 v1 文件**：从上面那份快照恢复，或从 Git 历史 `fff243d` 取回迁移函数——不要在当前代码里重建 v1 分支。

---

## 16. 三个旧写入接口（保留，但只作用于 v2）

保留这三个接口，因为它们是 Agent 侧已经在用的窄写入协议，与 project schema 无关：

```text
POST /api/agent/handshake
POST /api/agent/project-requirement-update
POST /api/agent/project-list-update
```

行为：

- 旧 handshake 映射为一次 Quick Session Open + runtime metadata 登记，仍返回 `paos-agent-handshake-receipt/v1` 回执（Agent 侧合同不变）；
- 要求更新只允许三个 human 字段，追加 `source_adapter=legacy_requirement_update` 的 Ledger Event；
- 列表更新只允许一类列表（`key_files` 或 `next_items`），追加 `source_adapter=legacy_project_list_update`；
- 两个更新接口的 `session_ref` 按 PAOS Session ID / handshake_id / runtime 原生 session_id 匹配。Session 的 `handshake_id` 是空字符串，不得因此判为未受管；
- 回执中的 `session` 摘要用 `id` / `identity_id` / `runtime_id` / `agent_label` 填充，不得留空——Prompt 要求 Agent 逐字报告它。

`PUT /api/projects/<id>` 只接受 `paos-project-manual-update/v1` 窄合同，整份 PUT 覆盖已被移除（422 拒绝）。

现有 API 测试必须继续全部通过。

---

## 17. 前端设计

### 17.1 不重做首页

本阶段不重构 Projects 首页。先在一个真实项目中证明 Session 闭环。

首页以后可增加 Active Sessions / Open Requests / Needs Integration，但不作为 v0.2 第一轮阻塞项。

### 17.2 项目页

保留现有十秒信息：

1. 项目进度；
2. 当前要求与 DDL；
3. 相关 Session；
4. 当前 Work Item。

新增一个紧凑的 Project Office 区域：

```text
Active Sessions
Open Requests
Pending Decisions
Needs Integration
Recent Delta
```

默认只显示计数和前三项，详细内容折叠，不能重新占满项目页顶部。

第一版 Pending Integration 只使用四条确定规则：

- Session 以 `partial` 或 `blocked` 关闭；
- Session 推荐下一 Identity 为 `integrator`；
- Reviewer 已关闭，但关联 Work 仍为 `review`；
- 存在尚未由人处理的 Decision Proposal。

### 17.3 Session Launcher

升级现有“启动一个受管 Session”下属页：

```text
选择 Work
→ 选择 Identity
→ 选择 Quick / Managed / Collaborative
→ 填 Runtime；Model 可空
→ Context Level 默认跟随 Identity，可人工改
→ 填 Mission / Done When
→ 创建 Session 并复制 Prompt
```

第一步是选择职责，不是模型品牌。

旧握手 Prompt 入口可折叠为“兼容模式”，不再是默认入口。

### 17.4 Session Card

至少显示：

- PAOS Session ID；
- Agent 原生标题，未知时降级显示；
- Identity；
- Runtime / Model；
- 关联 Work；
- 状态；
- 一句话进度；
- 最后活动时间；
- “查看 Session”入口。

### 17.5 Session 页面

新增：

```text
attention-dashboard-v1-static/session.html
attention-dashboard-v1-static/session.mjs
attention-dashboard-v1-static/session-model.mjs
```

只读展示：

- Assignment；
- Mission / Done When；
- Context Pack；
- 当前状态与 acknowledgement；
- Update 历史；
- Artifact；
- Request；
- Close Result；
- “复制接续 Prompt”。

同时提供一个默认折叠的“手动回贴”下属页：粘贴 `PAOS_MANUAL_WRITEBACK_V1` envelope，页面校验 action 与当前 Session 后调用相同 Ack/Update/Close API，并显示正式 receipt。

第一版不在 Session 页面直接启动 Agent，也不提供通用 JSON 编辑器。

---

## 18. 推荐代码接缝

不做大目录迁移，在现有 `attention-dashboard-v1-static/` 内增加：

```text
identity_registry.py
session_contracts.py
session_service.py
context_compiler.py
office_projection.py
config/identities.json
session.html
session.mjs
session-model.mjs
```

现有文件职责：

| 文件 | v0.2 改动 |
|---|---|
| `project_store.py` | v2 校验、迁移纯函数、统一 atomic mutation、Ledger/receipt |
| `local_server.py` | 只接路由、解析请求、映射错误；不塞业务逻辑 |
| `project.html` | Session Launcher 与紧凑 Project Office |
| `project.mjs` | 调用 Open/Office，渲染 Session 卡；保留人工编辑 |
| `project-model.mjs` | 纯 view-model；不重复后端校验 |
| `scripts/verify.ps1` | 纳入新增 Python/Node 测试套件，动态计数 |

后端依赖方向：

```text
local_server
→ session_service / context_compiler / office_projection
→ session_contracts / identity_registry
→ project_store
```

禁止 `project_store.py` 依赖 HTTP 或前端。

---

## 19. 测试与验收

### 19.1 Store / Contract

- v1 fixture dry-run 迁移不写盘；
- apply 迁移前有备份，字段映射正确；
- v2 完整校验；
- Session/Work/Artifact/Request 引用不悬空；
- 原子写入无临时文件残留；
- restore revision 单调并留下 correction event；
- 真实 private-data 未被测试触碰。

### 19.2 生命周期

```text
Open → Ack → Update → Close → 下一 Session Open
```

断言：

- 新 Session 得到最新 Context 与 revision；
- Update 原子修改 progress、Work、Artifact、Request；
- Close 后不能普通 Update；
- 下一 Session 的 Delta 能看到上一 Session 的结果；
- Quick Session 可以 Open 后直接 Close；
- Managed Session 未 Ack 前不能 Update；
- historical Session 不进入 Active。

### 19.3 幂等

- 同 operation ID + 同请求返回原 receipt；
- revision 不增加；
- Artifact、Request、Work 不重复；
- 同 operation ID + 不同请求返回 409。

### 19.4 并发

- 两个 Session 更新不同 Work，旧 revision 自动 rebase 后都成功；
- 两个 Session 更新同一 Work 状态，后者 409；
- Update 与 restore 竞争不能静默覆盖成功结果；
- 同一 Session 的 Close 与 Update 竞争只能有一个符合状态机。

### 19.5 权限

- Implementer 不能创建 Work；
- Session 不能更新未关联 Work；
- Bundle 不能改 human/name/area/priority；
- Agent 只能 proposed Decision；
- 恶意 Origin、非 JSON、超大正文失败且无副作用。

### 19.6 前端

- Identity 默认 Context 正确；
- Launcher 先 Identity 后 Runtime/Model；
- Prompt 包含 Project/Work/Mission/边界/回写端点；
- Project Office 空状态和有数据状态；
- Session Card 与 Session 页面；
- manual-paste 只接受三个已知 action，并始终使用当前页面的 Project/Session；
- 无效 envelope 不发请求，成功必须显示服务端 receipt；
- 现有页面 ID 不重复；
- 原有握手、要求、列表 Prompt 测试继续通过。

### 19.7 完成定义

使用合成或临时项目完整跑通：

```text
1. 用户已有一个 Work Item。
2. 页面选择 Implementer，创建 Managed Session 并复制 Prompt。
3. Agent Acknowledge，留下真实 Runtime Session 信息。
4. Agent 完成任务，通过 Close Bundle 一次登记成果、Artifact 和 Review Request。
5. 项目页自动显示 Session 已完成、Work 状态、Artifact、Request 和 Delta。
6. 用户创建 Reviewer Session。
7. Reviewer 的 Context 自动包含上一 Session 的结果和 Artifact 引用。
8. 全过程除首次粘贴 Prompt 外，不要求用户重新讲背景或手抄进度。
9. 同一 Close Bundle 通过 local HTTP 和 manual-paste 两种 transport 均能得到相同正式状态。
```

只有这条链路通过，才称为 v0.2 骨架成立。

---

## 20. 实施顺序

### Commit 1：合同、v2 Store 与迁移

实现：

- Identity 静态配置；
- v2 schema/validator；
- v1→v2 pure migration + dry-run；
- operation receipt、Ledger Event、touched paths；
- atomic mutation 基础；
- Store 单元测试。

此提交不改真实 private-data，不做前端。

### Commit 2：Session Gateway 与 Context

实现：

- Open / Ack / Update / Close；
- Context Compiler；
- Project Office / Delta；
- API 路由与错误映射；
- 生命周期、幂等、冲突与 HTTP 测试；
- 旧接口兼容测试。

### Commit 3：最小前端闭环

实现：

- Session Launcher；
- Project Office；
- Session Card / Session 页面；
- Prompt 复制；
- 前端测试；
- 使用与排错文档更新。

不要求死守三个提交，但提交必须保持可独立审查，不能把无关格式化混入。

---

## 21. 实施 Agent 的硬边界

1. 不重写技术栈；
2. 不增加第三方依赖；
3. 不改 Project 和 Work Item 编号；
4. 不自动调用外部 Agent；
5. 不读取、迁移或测试真实 `private-data`；
6. 不改 Tips 与 Attention Pipeline 的产品逻辑；
7. 不把 Session 变成第四层任务；
8. 不让 Agent Update Bundle 获得通用项目写权限；
9. 不为未来模型、小模型、MCP、RAG 预埋复杂抽象；
10. 不把已有 137 项测试删掉或降低口径；
11. 不把当前工作区中与任务无关的 CRLF/换行变化纳入提交；
12. 如果必须改写超过 20 个非本任务文件，先停止并报告。

---

## 22. 可直接交给实施 Agent 的任务入口

```text
你正在实现 Personal Agent OS v0.2 的第一条纵向闭环。

仓库：xiangscream/personal-agent-os
基线分支：agent/t-100-project-skeleton
基线提交：76f50d5
主设计书：docs/planning/09-V02-SESSION-LOOP-FRAMEWORK-DESIGN.md

开始前必须完整阅读：
1. 主设计书；
2. AGENTS.md；
3. CLAUDE.md；
4. docs/AGENT-HANDSHAKE-PROTOCOL.md；
5. docs/THREE-LAYER-MODEL.md；
6. attention-dashboard-v1-static/project_store.py；
7. attention-dashboard-v1-static/local_server.py；
8. 现有 Project Store / API / Board 测试。

目标：
在不重写现有 Python + JSON + 静态前端的前提下，按设计书完成
Open → Context → Ack → Update/Close → Office/Delta → 下一 Session 接续。

执行顺序：
Commit 1 合同与 Store；Commit 2 Gateway/Context/API；Commit 3 最小前端。

实现约束：
- 只使用标准库；
- 保留所有旧接口与测试；
- 真实 private-data 只读且不得迁移；
- 所有写测试使用 TemporaryDirectory / fixtures；
- 单个 Bundle 的状态、Ledger、operation receipt 必须同文件原子提交；
- 未实现功能不得在 UI 或文档中宣称可用；
- 当前工作区存在若干仅换行符变化的未提交文件，禁止纳入提交。

每个 Commit 后运行相关小测试；全部完成后运行 scripts/verify.ps1。

最终只返回：
1. 变更摘要；
2. 文件清单；
3. 生命周期实测证据；
4. 测试套件与真实数量；
5. 兼容性结果；
6. 未实现项；
7. 恢复方式；
8. 分支/提交/PR 状态。

不要合并 main。若设计与现有代码发生实质冲突，先报告冲突和最小修正建议，不自行扩展架构。
```

---

## 23. 远期技术储备（不进入当前任务）

当 v0.2 被真实使用后，可再评估：

- 从各 Runtime 原始日志提取 Session 证据；
- 用脚本或本地小模型生成 Work/Session 摘要候选；
- 外置 NDJSON Ledger 与确定性重建；
- MCP Adapter；
- 模型能力与成本注册表；
- 根据真实首次通过率推荐 Identity/Model/Runtime；
- 自动 Artifact 候选；
- 自动 Handoff 编译；
- Steward 周期检查；
- 跨项目 Portfolio Session；
- 稳定流程沉淀为 Skill 候选。

这些能力都必须继续服从同一个判断：

> 是否直接减少重复解释、人工转述、状态更新和资料归档成本？

如果不能，暂不进入主线。
