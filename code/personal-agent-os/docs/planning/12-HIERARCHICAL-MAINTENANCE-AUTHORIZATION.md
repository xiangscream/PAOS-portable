# Project Coordinator v0 设计

状态：实施规格 · 2026-08-19
关联 Work：3002-w010 · 设计总维护 Agent 的分级 PAOS 授权
关联 Session：3002-s013（integrator / managed）
依赖 Decision：3002-d006、3002-d007（建议 accept）；3002-d008（建议改为有限范围后 accept）

## 0. 设计目标

让经人类显式授权的总控 Agent（Coordinator）能在一个 Project 内创建正式 Work 和定向 Request，子 Agent 被唤醒后能自行发现并领取任务。人类从"手动采纳 Suggestion + 切换 Work + 复制长 Prompt"缩减为"分别唤醒 Agent 说继续"。

**这不是一个通用权限平台。** 它是一个由 LRC101 真实场景驱动的具名能力。Level 2 / PAOS root / 通用 `/api/maintenance` / 跨 Session 强制切换 / 旧接口下线均不进入 v0。

## 1. 真实场景：LRC101 三 Agent 协作

2026-08-19，LRC101 项目发生了一次真实协作：

```
总控 Agent（s009，integrator）
  ├── 分析任务、拆解、分配
  ├── 创建 Work Suggestion（g005/g006/g007）
  ├── 创建 Coordination Request（r001→s012, r002→s011, r003→s013）
  │
  └── ❌ 人类必须手动：
       1. 采纳 Suggestion → 生成正式 Work
       2. 切换每个 Session 的 Work
       3. 复制任务 Prompt 给每个 Agent

子 Agent（s012/s011/s013）
  └── ❌ 不知道总控已分配任务，直到人类手动操作
```

**摩擦点：** 总控已完成所有协调工作，但无法直接把任务写入 PAOS 并让子 Agent 看到。人类被夹在中间做纯行政转交。

## 2. Coordinator v0 目标流程

```
人类授权总控 Session 为 Coordinator
  ↓
总控 Agent（Coordinator）
  ├── 创建正式 Work（w011/w012/w013）
  ├── 创建定向 Request（r001→s012/w011, r002→s011/w012, r003→s013/w013）
  └── 每个 Request 含 target_session_id + target_work_item_id + 任务书路径

子 Agent 被人类唤醒（"继续"）
  ├── GET /api/projects/{id}/office → 发现指向自己的 open Request
  ├── 调用 switch_work（带 coordination_request_id）
  │   └── 同一次 mutation：校验 Request 目标 → 创建新 cycle → Request resolved
  └── Ack 新周期，开始工作

人类
  └── 从"九次点击 + 三次复制"缩减为"分别唤醒三个 Agent"
```

**明确边界：** 总控写入 PAOS ≠ 子 Agent 自动醒来。Codex、Claude、WorkBuddy 的原生对话不会因 PAOS 状态变化自动运行。没有 Harness 主动投递时，人类仍需唤醒子 Agent。

## 3. 数据结构变更

### 3.1 Session 增加 coordinator 字段

```json
{
  "id": "3002-s013",
  "coordinator": {
    "level": "coordinator",
    "project_id": "3002",
    "granted_cycle": 1,
    "granted_at": "2026-08-19T...",
    "granted_by": "human",
    "revoked_at": null
  }
}
```

权限检查同时要求：
- `coordinator.level == "coordinator"`
- `coordinator.revoked_at == null`
- `session.status == "active"` 且 `acknowledgement != null`
- `session.current_cycle == coordinator.granted_cycle`

这样 Close 后再 Reactivate 产生新周期，旧授权自然失效，不需要额外规则。

### 3.2 Request 增加 target_session_id 和 target_work_item_id

当前 Request 结构（`session_contracts.py:384`）只有 `request_type`、`target_identity_id`、`description`。Coordinator 创建的定向 Request 必须增加：

```json
{
  "id": "2001-r001",
  "request_type": "coordination",
  "target_identity_id": "implementer",
  "target_session_id": "2001-s012",
  "target_work_item_id": "2001-w011",
  "description": "任务书路径：LRC101-三Agent产品定义任务分发-v0.2.md",
  "status": "open"
}
```

`target_session_id` 和 `target_work_item_id` 为可选字段——普通 Request 不需要它们，但 Coordinator 创建的定向 Request 必须填写。

### 3.3 switch_work 接受可选的 coordination_request_id

现有 `switch_work`（`workflow_service.py:1107`）不接受 `coordination_request_id`。需要扩展：

```json
{
  "schema": "paos-session-switch-work/v1",
  "operation_id": "op-switch-...",
  "base_revision": 69,
  "session_id": "2001-s012",
  "new_work_item_id": "2001-w011",
  "coordination_request_id": "2001-r001",
  "reason": "按总控分发切换到 Agent A 双模式闭环"
}
```

当 `coordination_request_id` 存在时，同一次 mutation 中：
1. 校验 Request 存在且 status == "open"
2. 校验 `target_session_id` == 当前 Session
3. 校验 `target_work_item_id` == `new_work_item_id`
4. 创建新 Session cycle + Context Pack
5. 将 Request status 改为 "resolved"
6. 记录 resolution：`"resolved_by": "target_session_accepted"`

如果校验失败（Request 不存在/状态不对/目标不匹配），整个操作失败，不产生任何副作用。

**为什么不在 switch_work 之外单独 resolve：** 现有权限只允许 Request 创建者或 `session.request_ids` 中的拥有者更新 Request（`workflow_service.py:691`），目标 Session 默认没有这个权限。放到 switch_work 同一次 mutation 中，既避免了额外权限问题，又保证了"领取任务"和"切换 Work"的原子性。

## 4. 端点设计

### 4.1 人类授权/撤销 Coordinator

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/projects/{id}/sessions/{sid}/grant-coordinator` | POST | 人类授权。同 Project 已有 Coordinator 时返回 409。写入 Ledger `coordinator.granted` |
| `/api/projects/{id}/sessions/{sid}/revoke-coordinator` | POST | 人类撤销。写入 Ledger `coordinator.revoked`。Session Close 也自动失效 |

### 4.2 Coordinator 专用端点

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/projects/{id}/coordinator/work-items` | POST | 创建正式 Work。经过 `_check_coordinator` |
| `/api/projects/{id}/coordinator/requests` | POST | 创建定向 Request。必须含 `target_session_id` + `target_work_item_id` |

权限检查集中在 `_check_coordinator(session, project_id)` 领域函数中。路由分散，逻辑不分散。

### 4.3 子 Agent 领取任务（扩展已有端点）

| 端点 | 方法 | 变更 |
|---|---|---|
| `/api/projects/{id}/sessions/{sid}/switch-work` | POST | 新增可选 `coordination_request_id` 字段 |

### 4.4 投影增强

| 端点 | 变更 |
|---|---|
| `GET /api/projects/{id}/office` | 增加"指向本 Session 的 open Request"列表 |
| Context Pack 编译 | 增加"待处理 Request"section |

## 5. 不进入 v0 的内容

| 内容 | 原因 |
|---|---|
| `coordinator/generated` 端点 | 已有单次窄写 Prompt，不阻塞主流程，放 v0.1 |
| `coordinator/lists` 端点 | 同上 |
| `assign_work`（跨 Session 强制切换） | 子 Agent 自行 switch_work 先验证；如果经常漏掉再增加。届时必须校验 `expected_current_work_item_id` + `expected_cycle`，创建完整新 cycle，使用 `coordinator_switch` 而非 `human_switch` |
| Level 2 / PAOS root | 完全没有真实需求 |
| 通用 `/api/maintenance` | 不做 |
| 旧窄写接口下线 | 保留。它们是"单次、低信任授权"模式，Coordinator grant 是"持续、较高信任授权"。两种粒度各有真实用途 |
| `leave_instruction` | `note_for_next_session` 是 Session 自己的交接字段，switch_work 会清空。总控指令统一用定向 Request |
| 总控 review_work | 最终 Review 仍由人类决定。总控可留下评估，现有 Close 结果或 Decision proposal 已能承载 |

## 6. 权限检查

```python
def _check_coordinator(session: dict[str, Any], project_id: str) -> None:
    """验证 Session 是否为当前 Project 的有效 Coordinator。"""
    coordinator = session.get("coordinator") or {}
    if coordinator.get("level") != "coordinator":
        raise ForbiddenError("当前 Session 未被授权为 Coordinator。")
    if coordinator.get("revoked_at"):
        raise ForbiddenError("Coordinator 授权已被撤销。")
    if coordinator.get("project_id") != project_id:
        raise ForbiddenError(
            f"Coordinator 授权仅限于项目 {coordinator.get('project_id')}。"
        )
    if session.get("status") != "active":
        raise ForbiddenError("Coordinator Session 必须处于 active 状态。")
    if session.get("acknowledgement") is None:
        raise ForbiddenError("Coordinator Session 必须先 Acknowledge。")
    if session.get("current_cycle") != coordinator.get("granted_cycle"):
        raise ForbiddenError(
            "Coordinator 授权绑定于授权时的周期，当前周期已变化。"
        )
```

## 7. 实施步骤

### Step 1：Session schema + 授权/撤销端点

- `coordinator` 字段加入 Session schema
- `grant-coordinator` / `revoke-coordinator` 端点
- 同 Project 互斥检查
- Ledger 事件：`coordinator.granted` / `coordinator.revoked`
- 测试：授权 → 撤销 → 403；Close → Reactivate → 旧授权不恢复

### Step 2：Request schema 扩展 + Coordinator 创建端点

- `target_session_id` / `target_work_item_id` 加入 Request schema
- `POST /api/projects/{id}/coordinator/work-items`
- `POST /api/projects/{id}/coordinator/requests`
- 测试：Coordinator 创建 Work + Request；非 Coordinator 403

### Step 3：switch_work 扩展（coordination_request_id）

- `switch_work` 接受可选 `coordination_request_id`
- 同一次 mutation：校验 Request → 创建新 cycle → Request resolved
- 测试：正常领取；Request 状态不对 → 失败；目标不匹配 → 失败

### Step 4：Office / Context Pack 投影

- Office 投影增加"指向本 Session 的 open Request"
- Context Pack 编译增加"待处理 Request"section
- 测试：子 Agent GET office 能看到指向自己的 Request

### Step 5：端到端验证

用一个真实 LRC101 三 Agent 分发验证：

```text
人类授权总控
→ 总控创建 Work + 定向 Request
→ 人类对目标 Agent 说"继续"
→ 子 Agent 查到 Request
→ 领取并切换 Work
→ Request 自动 resolved
→ Ack 新周期
→ 撤销后总控再写返回 403
```

## 8. 与现有代码的关系

| 现有代码 | v0 处理方式 |
|---|---|
| `_narrow_agent_write` (project_store.py:713) | 保留不动——历史操作分支（幂等预检查先于 no-op 判断）必须保留（T-052-01） |
| `_match_managed_session` (project_store.py:1465) | 复用 |
| `_is_authorizable_session` (project_store.py:1419) | 复用 |
| 三个旧窄写端点 | 保留，不标记 deprecated |
| `workflow_service.create_work` (1144) | Coordinator 端点复用其逻辑 |
| `workflow_service.switch_work` (1107) | 扩展：接受可选 `coordination_request_id` |
| `context_compiler.build_context_pack` | 增强：增加"待处理 Request"section |
| `office_projection.office` | 增强：增加"指向本 Session 的 open Request" |
| `mutate_v2` (project_store.py:905) | 不变——所有 Coordinator 操作的最终写入路径 |

## 9. 未来储备（不进入 v0）

### 9.1 Coordinator 维护 generated / lists（v0.1）

当 Coordinator 需要主动维护项目进度摘要或文件列表时，增加 `coordinator/generated` 和 `coordinator/lists` 端点。当前已有单次窄写 Prompt 可用，不阻塞主流程。

### 9.2 assign_work（v1）

如果事实证明"让子 Agent 自己 switch 仍然经常漏掉"，增加 Coordinator 跨 Session 强制切换。届时必须：
- 校验 `expected_current_work_item_id` 和 `expected_cycle`
- 创建完整的新 Session cycle 和 Context Pack
- 将状态置为 `pending_ack`
- 保留旧周期
- 使用 `coordinator_switch`，不是 `human_switch`

### 9.3 Level 2 / PAOS root

完全没有真实需求。留在设计储备区，等出现跨 Project 维护或 human 字段委托的真实场景后再设计。

## 10. 依赖的 Decision 状态

| Decision | 当前状态 | 建议 |
|---|---|---|
| 3002-d006（权限范围与可靠性内核分离） | proposed | 建议 accept——Coordinator 扩大权限但不放弃 mutate_v2 |
| 3002-d007（不用 Identity 自动推导 root 权限） | proposed | 建议 accept——Coordinator 是显式授权，不由 integrator identity 自动获得 |
| 3002-d008（显式授权 = 事实维护委托） | proposed | 建议改为有限范围后 accept——Coordinator 授权是"在本 Project 内创建 Work 和定向 Request"，不是 blanket authority |
