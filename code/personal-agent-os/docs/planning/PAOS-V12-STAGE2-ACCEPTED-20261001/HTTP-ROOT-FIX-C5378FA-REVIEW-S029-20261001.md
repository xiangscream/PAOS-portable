# 独立复核 — HTTP 根接线修复 `c5378fa` — s029

- Reviewer：`3002-s029`。Work：`3002-w060`（沿用）。
- 依 s027 `msg-3002-w060-http-root-fix-s027-20261001`（响应 Rooter `V12-9A10E32-INTEGRATION-FAILURE-20261001` 的三缺口）。
- **候选**：`c5378fadbe073f352f731c6263b7560d113c8142`（parent `9a10e32`；**已 push FF → PR #114 head**——远端读回确认）；readback §8 已更新。
- 模式：只读 + 候选 worktree 复跑 + **Rooter 真实输入复现**（live 服务 GET 快照 + canonical 工位目录端到端）。未改生产/候选。

## 1. 三缺口逐一判定（对照 Rooter 失败报告）

### 1.1 HTTP team.agents=[] 真因修复（根接线） — **PASS**
- 新 `ProjectStore.project_root_path(project_id)`：Project vault `root_path` 的**唯一推断点**（"服务层不得自行猜目录"——与 Rooter 的架构结论一致：路径推断必须留在既有 project_store 唯一推断点）。
- `workflow_service.team_contact` 改走 `self.store.project_root_path()` → `build_team_rows(project, Path(root_path))`——**不再传 `self.store.root`（登记数据目录）**。
- **root_path 未登记时**：返回 `unavailable_reason=project_root_path_not_registered`——诚实显示；**此前「缺工位即诚实降级」的错误定性已撤回**（Rooter 明示该正常路径错误不可称"诚实降级"）。
- **架构检查**：`check_architecture.py` 9 条通过（s027 报告；该检查由 Rooter 失败报告引入的机械边界——workflow_service.py:98 猜目录——现由唯一推断点满足）。

### 1.2 本人 TODO 直接入口 — **PASS**
- team 卡片 TODO 行附工作台 `TODO.md` 直接路径（可复制）——实测 build_team_rows 真实数据输出中 workstation_todo.path 均为 canonical 绝对路径。

### 1.3 Codex 手动入口（manual_open） — **PASS**
- `derive_attach` 对 codex 附 `manual_open`：`native_thread`（binding native session）+ `co_agent_root`（binding 配置）+ `manual_open` 配置键**原文优先**；**不编造命令、不自动启动**；"未配置=not configured"如实。
- 本人实测（真实数据端到端）：s010 行 manual_open = `native_thread=01a042ee-4ac4-7613-8619-3782fc03554f`、co_agent_root 自 binding、note 明示人工打开语义与不自动启动——**CLI+页面同示**（build_team_rows 单一事实源）。

## 2. Rooter 同一真实输入复现（关键验证）

- 用 **live 服务 GET 快照**（`/api/projects/3002`，root_path=canonical vault）+ 候选 `build_team_rows`（仓库 `c5378fa`）+ **实际工位目录**：
  - **5 行 fixed-workstation**：`3002-s010/s027/s029/s031/s032`——Rooter 失败时的「CLI 5 行 vs HTTP 0 行」分裂，在修复后同输入下两侧一致（HTTP 层经 project_root_path 拿到同一 root → 同一构建器 → 5 行）。
  - s029 行：`trusted=true`、next 正确、attach 正确派生；s010 行 manual_open 如实。
- 聚焦：`tests.test_contact_surface_s2` **21/21 OK**（含 Rooter 失败回归两例：`test_dashboard_team_contact_uses_project_root_path`（store 根≠Project root_path 真因果）、`without_root_path_is_honest` / `root_path_missing_is_honest_not_empty_ok`（unavailable_reason 契约）+ `test_team_json_hides_no_unavailable_facts`）。
- 整套 python：s027 报告 817（FAIL 仅 1=预存在 WSL codex interop）；Windows verifier 待 Rooter 在含 `c5378fa` 的最终候选跑（不替宣称）。
- `git diff --check` clean；push FF 已核；范围 5 文件（store/workflow/contact/UI+测试）；未动生产/binding/锁/Harness/attempt。

## 3. 结论

**总判：`c5378fa` — PASS（三缺口修复成立：唯一推断点 + manual_open + TODO 入口；Rooter 真实输入上 HTTP/CLI 两侧一致 5 行复现已证）。联系面"HTTP→页面数据流"的最终复验由 Rooter 在最终候选跑（含真实服务进程的 GET /team → 页面渲染）——待其跑完前不宣称整体完成。**

---
审查人：3002-s029。证据：diff 审读（5 文件）、live 服务 GET 快照 + canonical 工位端到端复现（5 行 / trusted / manual_open 实测）、聚焦 21/21 复跑、`git diff --check`、push FF 读回。未改生产。
