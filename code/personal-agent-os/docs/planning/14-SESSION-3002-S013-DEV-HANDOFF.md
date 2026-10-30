# Session 3002-s013 完整开发 Handoff（供审查）

> 生成时间：2026-08-20
> Session：3002-s013 · integrator · managed
> Project：3002 Personal Agent OS
> Work：3002-w010 · 设计总维护 Agent 的分级 PAOS 授权
> PAOS revision：65（打开时）→ 98（本文登记前）
> 审查目的：请另一 Agent 审查本 Session 全部开发过程、代码变更、验证证据与历史失误，重点找我没发现的问题。

## 1. 本 Session 发生了什么（按时间顺序）

1. **环境恢复**：PAOS 服务未运行，先在 WSL 起了测试服务完成 Acknowledge。
2. **设计收敛**：从"三级权限平台（Level 0/1/2）"开始，经用户三轮纠偏，最终收敛为"Project Coordinator v0"具名能力。过程经历了：
   - 第一版：Level 0/1/2 + 统一 `/api/maintenance` + assign_work；
   - 第二版：保留 Coordinator，删除 assign_work、leave_instruction；
   - 第三版：把旧设计全部删除，只保留 Coordinator v0 实施规格；
   - 最终范围：授权/撤销 + Coordinator 创建 Work + 定向 Request + 子 Agent 自取 + 投影。
3. **后端 Step 1**：Coordinator 授权/撤销端点 + `_coordinator_failure_reason` 统一判断源 + 16?（实际 12 项）测试。期间修复两个 P1：失效授权阻塞新授权；幂等重放返回后来状态。
4. **后端 Step 2**：Coordinator 创建 Work / 定向 Request；`switch_work` 带 `coordination_request_id` 原子领取并 resolve Request；拒绝不可领取的 Request。期间修复两个 P1：权限检查在事务外、Request 重放返回 null；再修 touched_paths 与来源标记。
5. **Step 4 投影**：Office 支持 `?session_id=`；Context Pack 基础区新增 `pending_requests`；Prompt Markdown 渲染"待处理的协调请求"；Brief 级别也必须可见。
6. **前端项目页按钮**：Session 卡片显示 Coordinator 状态 + 授权/撤销按钮。第一次编辑因 CRLF/LF 失配静默失败，被用户抓出；第二次补齐并 grep 复核。
7. **restart.ps1 修复**：闪退 → WMI CommandLine 空误拒 → WSL 启动的服务桌面无法停止 → v4 简化版（health 确认 + 尝试停止 + 调 start.ps1，失败给人工指引）。
8. **回写编码修复**：PowerShell 5.1 `Invoke-RestMethod` Latin-1 发送导致 rev 91-95 中文乱码；改用 Windows 原生 Python urllib UTF-8 字节 POST。
9. **文档**：Coordinator 分发/领取作战提示；本 handoff。

## 2. 最终实现范围

做：
- 人类授权/撤销 Session 为 Project Coordinator（同项目互斥，授权绑定 granted_cycle，Close 失效）
- Coordinator 创建正式 Work（`created_by=coordinator` + `source_session_id`）
- Coordinator 创建定向 Request（必填 `target_session_id` + `target_work_item_id`；拒绝 historical 目标、目标 Work == 当前 Work、Work 终态）
- 子 Agent 通过 Office/Context Pack 看到指向自己的 open Request
- `switch_work` 携带 `coordination_request_id`：同一 canonical mutation 中校验并 resolve Request、创建新周期
- 项目页 Session 卡片显示 Coordinator 状态与授权/撤销按钮

不做：
- `assign_work`（总控强制切换子 Session）
- Level 2 / PAOS root
- 通用 `/api/maintenance`
- 旧窄写接口下线
- 总控 review_work 委托
- Coordinator 维护 generated/lists 端点（v0.1）

## 3. 代码变更文件

后端：
- `attention-dashboard-v1-static/errors.py`
- `attention-dashboard-v1-static/project_store.py`
- `attention-dashboard-v1-static/session_contracts.py`
- `attention-dashboard-v1-static/workflow_service.py`
- `attention-dashboard-v1-static/local_server.py`
- `attention-dashboard-v1-static/office_projection.py`
- `attention-dashboard-v1-static/context_compiler.py`

前端：
- `attention-dashboard-v1-static/project-model.mjs`
- `attention-dashboard-v1-static/project.mjs`

脚本：
- `scripts/restart.ps1`

测试：
- `attention-dashboard-v1-static/tests/test_v2_sessions.py`（新增 `CoordinatorGrantRevokeTests` 12 项、`CoordinatorDispatchTests` 10 项）
- `attention-dashboard-v1-static/tests/project-dashboard.test.mjs`（新增 2 项 coordinator 纯函数测试）

文档：
- `docs/planning/12-HIERARCHICAL-MAINTENANCE-AUTHORIZATION.md`（Coordinator v0 设计/实施规格）
- `docs/planning/13-PROJECT-COORDINATOR-V0-HANDOFF.md`（Coordinator 专项 handoff，本文件的子集）
- `docs/runbooks/COORDINATOR-TASK-DISPATCH-PROMPT.md`（给 Agent 粘贴的作战提示）

## 4. 验证数据（2026-08-20 行尾修复后实跑）

| 套件 | 数量 |
|---|---|
| Dashboard Python | 236 |
| Pipeline Python | 25 |
| project-dashboard JS | 45 |
| session-model JS | 13 |
| dashboard-v1 JS | 10 |
| **合计** | **329** |

全部通过。`git diff --ignore-space-at-eol` 显示未编辑文档无内容差异。

## 5. 需要审查的重点

权限与事务：
1. `create_work_coordinator` 的权限检查必须落在 `mutate_v2.apply` 内；幂等重放先于权限判断。
2. grant/revoke/request 三条写路径的幂等重放必须返回首次冻结的专用 receipt，不是重建当前状态。
3. `switch_work` 带 `coordination_request_id` 时，touched_paths 必须覆盖 `/requests/{id}/status|resolution|updated_at`，event_details 要有 `resolved_request_id`。

契约与来源：
4. 定向 Request 创建时必须拒绝：目标 Session historical、目标 Work 为当前 Work、目标 Work 为 review/done/cancelled。
5. Coordinator 创建的 Work 必须写 `created_by=coordinator` + `source_session_id`；普通 `create_work` 仍写 `created_by=human`。
6. Coordinator grant/revoke 授权与撤销都进 Ledger；撤销后接口必须 403；Close 后旧授权不得复活。

前端：
7. `project.mjs` 的导入块、sessionCard 渲染、session-list 事件委托三处必须齐全且无重复。
8. Session 卡片按钮只在 active + acknowledged 且未持有有效 Coordinator 时显示"授权"；已持有显示"撤销"。

编码与提交卫生：
9. 所有文件 `git ls-files --eol` 与 HEAD 一致；`git diff --ignore-space-at-eol` 只包含真实改动。
10. 以后 PAOS 回写禁止用 PowerShell 5.1 `Invoke-RestMethod` 发中文；用 Windows 原生 Python UTF-8 字节 POST（或等效 UTF-8 通道）。

## 6. 历史失误清单（如实记录，供审查复核）

1. 前端按钮第一次声称"已添加"但三处关键代码（导入、卡片、事件）因 CRLF 失配未落盘；用户抓出后才补齐。教训：改完必须 grep 每处预期标记 + node --check + 实测。
2. PAOS Ledger rev 91-95 中文乱码：PowerShell `Invoke-RestMethod` 默认 Latin-1 发送。未能提前发现编码风险。
3. rev 96 `test` summary：编码测试误用真实 Session 发了一个测试更新。已保持证据不变并在 rev 97 追加修正说明。
4. restart.ps1 多次返工：裸 `exit` 闪退；WMI CommandLine 空误拒；Stop-Process 跨会话拒绝访问。最终 v4 简化收敛，但过程说明我在环境差异下缺少一次到位的前置验证。
5. 行尾翻转：除真正编辑的文件外，`docs/planning/00/04/07/08` 与 `docs/runbooks/START-AND-DIAGNOSE.md` 一度被发现 i/lf w/crlf（未编辑却被翻），已恢复。审查者请确认仓库再无可疑翻转。
6. WSL 启动的服务导致桌面会话无法停止；最终由桌面启动解决。教训：测试服务和应用服务不能混会话。

## 7. 未完成事项

- Step 5：真实 LRC101 单 Agent 一条线验收（人类授权 → Coordinator 创建 1 Work + 1 定向 Request → 人类唤醒 → 子 Agent 自查领取 → Request resolved → Ack 新周期）。
- `assign_work`：仅当实践证明子 Agent 自行 switch 经常漏掉时再做，需 `expected_current_work_item_id` + `expected_cycle` + `coordinator_switch`。
- Coordinator 维护 generated/lists 端点（v0.1）。
- P2 日志轮转问题要在 Windows 原生服务下复测确认是否仍存在。

## 8. 给审查 Agent 的快速校验命令

```bash
cd /mnt/c/Users/remo/Desktop/agent学习计划/personal-agent-os
git diff --ignore-space-at-eol --stat
git ls-files --eol | grep -E "w/(lf|crlf)" | awk '$1 != $2'   # 找出所有行尾不一致
python -m unittest discover -s attention-dashboard-v1-static/tests -p "test_*.py" -q
cd attention-memory-pipeline-v0 && python -m unittest discover -s tests -p "test_*.py" -q
node --test attention-dashboard-v1-static/tests/project-dashboard.test.mjs
node --test attention-dashboard-v1-static/tests/session-model.test.mjs
node --test attention-dashboard-v1-static/tests/dashboard-v1.test.mjs
```
