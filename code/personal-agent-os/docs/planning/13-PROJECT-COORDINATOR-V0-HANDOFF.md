# Project Coordinator v0 开发 Handoff（供审查）

> 生成时间：2026-08-20
> 来源 Session：3002-s013（integrator / managed）
> 关联 Work：3002-w010 · 设计总维护 Agent 的分级 PAOS 授权
> 审查目的：请另一 Agent 审计本轮开发过程、代码变更与验证证据，找出我未发现的问题

## 0. 一句话状态

Project 2001（LRC101）需要"总控 Agent 通过 PAOS 直接向子 Agent 发任务"的能力。本轮在 Project 3002（PAOS 自身）实现了 Project Coordinator v0：
人类授权 Coordinator → Coordinator 创建正式 Work + 定向 Request → 子 Agent 被唤醒后自查 `office?session_id=` → `switch_work` 带 `coordination_request_id` 原子领取并 resolve Request → 新周期 Ack。
后端 Step 1/2/4 和项目页按钮已完成，测试 329/329 通过，等待真实 LRC101 场景做 Step 5 验收。

## 1. 背景与范围收敛

最初方案是完整的 Level 0/1/2 权限平台，被用户否决后收敛为具名能力 Project Coordinator。最终范围：

做：
- 人类授权 / 撤销一个 Session 为 Project Coordinator（同项目互斥、绑定 granted_cycle、Close 失效）
- Coordinator 创建正式 Work（来源标记 `created_by=coordinator` + `source_session_id`）
- Coordinator 创建定向 Request（必填 `target_session_id` + `target_work_item_id`；拒绝不可领取组合）
- 子 Agent 通过 Office/Context Pack 看到指向自己的 open Request
- `switch_work` 携带 `coordination_request_id` 在同一 canonical mutation 中 resolve Request 并创建新周期
- 项目页 Session 卡片显示 Coordinator 状态与授权/撤销按钮

不做：
- `assign_work`（总控强制切换子 Session）
- Level 2 / PAOS root
- 通用 `/api/maintenance` 端点
- 旧窄写接口下线
- 总控 review_work 委托
- `generated/lists` 的 Coordinator 维护端点（放 v0.1）

## 2. 代码变更清单

### 后端

| 文件 | 变更 |
|---|---|
| `attention-dashboard-v1-static/errors.py` | 新增 `ForbiddenError`（403） |
| `attention-dashboard-v1-static/project_store.py` | 新增 `_coordinator_failure_reason` / `_is_active_coordinator` / `_check_coordinator`，三函数共享同一判断源 |
| `attention-dashboard-v1-static/session_contracts.py` | 新增 `GRANT_COORDINATOR_SCHEMA` / `REVOKE_COORDINATOR_SCHEMA` 及验证器；`normalize_requests` 支持 `target_session_id` / `target_work_item_id`；`normalize_session_switch_work_payload` 支持可选 `coordination_request_id` |
| `attention-dashboard-v1-static/workflow_service.py` | 新增 `grant_coordinator` / `revoke_coordinator`（幂等重放冻结专用 receipt）；新增 `create_work_coordinator`（`_create_work_impl` 共享实现，权限检查在 mutate_v2.apply 内）；新增 `create_request_coordinator`（定向 Request + 不可领取校验 + 冻结 receipt）；`_start_new_cycle` 支持 `coordination_request_id` 并原子 resolve Request，touched_paths 覆盖 Request 三个字段，event_details 记录 `resolved_request_id` |
| `attention-dashboard-v1-static/local_server.py` | 新增路由/handler：`grant-coordinator` `revoke-coordinator` `coordinator/work-items` `coordinator/requests`；`ForbiddenError`→403；`get_office` 解析 `?session_id=` 并传给 projection |
| `attention-dashboard-v1-static/office_projection.py` | `office(project, session_id="")` 增加 `pending_requests` 投影 |
| `attention-dashboard-v1-static/context_compiler.py` | `pending_requests` 进入基础 Context Pack（Brief 可见）；`build_prompt_markdown` 渲染"待处理的协调请求"并含 Request ID / 目标 Work / `coordination_request_id` 指引；Context Pack 内 office URL 带 `?session_id=` |

### 前端

| 文件 | 变更 |
|---|---|
| `attention-dashboard-v1-static/project-model.mjs` | `isActiveCoordinatorSession` / `coordinatorStatusText` / `isGrantableCoordinatorSession` / `buildGrantCoordinatorPayload` / `buildRevokeCoordinatorPayload` |
| `attention-dashboard-v1-static/project.mjs` | Session 卡片：Coordinator 状态行 + 授权/撤销按钮 + `grantCoordinator` / `revokeCoordinator` 函数 + 事件委托绑定 |

### 文档

| 文件 | 说明 |
|---|---|
| `docs/planning/12-HIERARCHICAL-MAINTENANCE-AUTHORIZATION.md` | Coordinator v0 设计（后经用户多次收窄，旧 Level 0/1/2 内容已删除） |
| `docs/runbooks/COORDINATOR-TASK-DISPATCH-PROMPT.md` | 可粘贴给任何 Agent 的分发/领取作战提示 |
| 本文件 | Handoff |

### 脚本

`scripts/restart.ps1` 经历多次修复，最后 v4 简化：
- 只做 health 确认 PAOS → 尝试 Stop-Process → 调用 start.ps1
- 删除 Win32_Process CommandLine 校验（WMI 读空时会误拒）
- Stop-Process 拒绝访问时给人工指引（WSL 启动的服务桌面会话停不掉）
- 全逻辑 try/catch + `Exit-WithPause`（双击不停留的问题）

## 3. 验证数据（2026-08-20 实跑）

| 套件 | 数量 | 结果 |
|---|---|---|
| Dashboard Python（`attention-dashboard-v1-static/tests/test_*.py`） | 236 | 通过 |
| Pipeline Python（`attention-memory-pipeline-v0/tests/test_*.py`） | 25 | 通过 |
| `project-dashboard.test.mjs` | 45 | 通过 |
| `session-model.test.mjs` | 13 | 通过 |
| `dashboard-v1.test.mjs` | 10 | 通过 |
| **合计** | **329** | **通过** |

新增测试集中在 `test_v2_sessions.py`（CoordinatorGrantRevokeTests 12 项 + CoordinatorDispatchTests 10 项）与 `project-dashboard.test.mjs`（2 项 coordinator 纯函数）。

## 4. 需要审查的重点

1. **权限位置**：`create_work_coordinator` 的 `_check_coordinator` 是否真的在 mutate_v2.apply 内执行；幂等重放是否先于权限判断。
2. **幂等响应冻结**：grant/revoke/request 三条写路径的重放是否返回首次冻结结果（`coordinator_receipt`），不是重建当前状态。
3. **touched_paths 完整性**：switch_work 携带 coordination_request_id 时，是否覆盖 `/requests/{id}/status|resolution|updated_at`；event_details 是否有 `resolved_request_id`。
4. **不可领取 Request**：创建时是否拒绝 historical Session、目标 Work == 当前 Work、Work 为终态。
5. **来源语义**：Coordinator 创建的 Work 应写 `created_by=coordinator` + `source_session_id`；普通 `create_work` 仍写 `created_by=human`。
6. **前端**：project.mjs 的导入块、sessionCard、事件委托三处是否齐全（本轮曾发生编辑脚本 CRLF 失配导致静默失败，后已补）。
7. **行尾**：git ls-files --eol 是否与 HEAD 一致（本仓库 project.mjs 是 CRLF；project-model.mjs 是 LF）。

## 5. 已知问题与历史失误（如实记录）

1. PAOS Ledger rev 91-95 的中文 summary 是乱码。原因：Windows PowerShell `Invoke-RestMethod` 默认 Latin-1 发送。已改用 Windows 原生 Python `urllib` UTF-8 字节 POST。
2. PAOS Ledger rev 96 有一条 `test` summary。原因：编码测试误用真实 Session 发了测试更新。已按证据不可重写原则保留，并在 rev 97 追加修正说明。
3. 前端按钮第一次宣称"已添加"但实际未落盘三处关键代码。原因：编辑脚本用 LF 匹配 CRLF 文件且未做 grep 复查。已补齐并通过 node --check + JS 测试。
4. restart.ps1 反复出错：闪退（裸 exit）→ WMI CommandLine 空误拒 → 跨会话进程 Stop-Process 拒绝访问。已收敛为 v4 简化版。
5. PAOS 服务一次被 WSL 启动，导致桌面会话无法重启；解决办法是用户桌面双击 start.ps1 启动服务，让服务与桌面同会话。

## 6. 未完成 / 下一步

- Step 5：真实 LRC101 单 Agent 一条线验收（人类授权 Coordinator → Coordinator 创建 1 Work + 1 定向 Request → 人类唤醒目标 Agent → 子 Agent 自查并领取 → Request resolved → Ack 新周期）
- 若 Step 5 发现子 Agent 自己 switch 经常漏，再实现 `assign_work`（届时需 `expected_current_work_item_id` + `expected_cycle` + `coordinator_switch`）
- Coordinator 维护 generated/lists 端点放 v0.1
