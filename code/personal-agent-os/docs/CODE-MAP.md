# PAOS Code Map

约 100 行的“改哪里”地图。给第一次进入仓库的 Agent 定位用；详细设计见 [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) 与 [`docs/DEVELOPMENT-PRINCIPLES.md`](DEVELOPMENT-PRINCIPLES.md)。安装侧可能另有一份基于某历史 HEAD 写成的本地学习批注（不随仓库分发；发现对不上时以代码为准）。

**模块位置**：除非注明 `scripts/…`，本页提到的 `.py` / `.mjs` 服务端与前端文件都在 `attention-dashboard-v1-static/` 下。CLI 与服务端共享的模块在 `scripts/`（`paos.py`、`paos_attention_service.py`、`paos_installation.py`、`paos_contact.py` 等）。`local_server.py` 会在导入时把 `scripts/` 插入 `sys.path`，`workflow_service.py` 部分方法内动态 import `scripts/paos_contact`——`attention-dashboard-v1-static/` 不是自包含目录。

主启动路径是 `scripts/start.ps1` → `attention-dashboard-v1-static/paos_server.py`（薄壳：`import local_server`，只负责响应头 `X-PAOS-Runtime-Fingerprint`）；`local_server.py` 是核心实现。

## 一张图

```text
浏览器 / Agent
  ↓ HTTP JSON
attention-dashboard-v1-static/local_server.py    路由表 GET/POST/PUT、错误映射、静态 fallback
  ↓
attention-dashboard-v1-static/workflow_service.py  薄 facade：请求分发到 WorkflowService mixins（见下）
  ↓
工作流 mixins（权威清单 = workflow_service.py:36 `class WorkflowService(...)` 组合声明，随代码演进读源码，不在本页复制）：
  主组合 SessionWorkflowMixin / CoordinationWorkflowMixin
  + AgentContinuityWorkflowMixin / DecisionWorkflowMixin
  + hooks：TypedReferenceHooks / CoordinatorContinuityGuard / AgentContinuityHooks / ArtifactRevisionHooks / WorkingMemoryHooks
  workflow_support.py 只是 mixins 共用 helper，不是 mixin；session_lifecycle.py 经 session_workflow.py import 参与语义
  ↓
contracts (session/work/coordination/project) + project_schema.py
  ↓
attention-dashboard-v1-static/project_store.py   项目 JSON 唯一写入者：mutate_v2 + revision + Ledger + receipt
  ↓
项目 JSON 落盘：`local_server.py` 的 `DEFAULT_PROJECT_REGISTRY_ROOT = REPO_ROOT / "private-data" / "project-registry"`
即仓库根 `private-data/project-registry/projects/<id>.json`（仓库默认值；实际安装以启动参数/配置为准）

只读投影（均为 attention-dashboard-v1-static/ 下）：
context_compiler.py                Context Pack 与握手 Prompt
session_projection.py              Session Detail
office_projection.py               Office / Delta
relations_projection.py            Session/Cycle ↔ Agent 关系事实
lifecycle_projection.py            生命周期治理 findings（只读）
session_lifecycle.py               Session 终结语义：Close / Submit / Abandon（V1.3 后周期=Session；无 Cycle 结束手续）
needs_me_projection.py             严格 Human-attention 投影
plugin_registry.py                 插件清单/禁用/入口 URL
```

前端为原生 JS（两套，别读错）：

```text
真实界面：attention-dashboard-v1-static/projects.html + projects.mjs   走 /api/* 读真实项目总览
project.html / session.html：静态退役提示页（不读 /api/*，仅提示改用工位 Current/Mail/Notice 与同版 CLI；旧 Work/Cycle 接单页面已退出）
旧原型（已退役 2026-10-10）：index.html + app.mjs 原读合成数据；目录按真实依赖闭合退回（UI 入口删除）
```

## 常见改动路径

### GET

`local_server.do_GET` → `GET_ROUTES` 路由表 → 具体 `get_*` handler → `ProjectStore` / 投影模块 → JSON 响应。

### Mutation

以 `POST /api/projects/<id>/sessions` 为例：

```text
local_server.py handle_session_open
  → workflow_service.WorkflowService.open_session
  → session_workflow.py SessionWorkflowMixin.open_session
  → session_contracts.normalize_open_payload
  → project_store.ProjectStore.mutate_v2
  → project_schema.validate_project_v2
  → Ledger + operation_receipt + 备份 + 原子替换
```

### Context Pack

```text
Open Session 成功后
  → context_compiler.build_context_pack
  → project_store.write_context_pack_atomic（原子写快照）
  → context_compiler.build_prompt_markdown（生成握手 Prompt）
```

### 需要改什么？

除注明 `scripts/…` 外，下表文件均在 `attention-dashboard-v1-static/` 下。

| 你关心 | 去这里 |
|---|---|
| 新 API 路由 / 状态码 / JSON 响应 | `local_server.py` |
| CLI 子命令（安装/唤醒/mail/todo 等） | `scripts/paos.py` 及 `scripts/paos_*.py` |
| Session Open/Ack/Update/Close/Abandon 语义 | `session_workflow.py` + `session_lifecycle.py` |
| ~~Work 创建/Review/Cancel/评价~~ | 已退役：Work 不是系统对象，`work_workflow.py` 已删除 |
| Coordinator 授权/撤销/定向 Request | `coordination_workflow.py` |
| Authority Matrix / actor capability vocabulary | `authority_manifest.py` + `docs/AUTHORITY-MATRIX.md` |
| 请求 body 归一化与错误文案 | `session_contracts.py` / `coordination_contracts.py` / `project_contracts.py` |
| 项目 JSON 结构与校验 | `project_schema.py` |
| 文件落盘/备份/恢复/revision | `project_store.py` |
| 握手 Prompt 文本 | `context_compiler.py` |
| 生命周期治理信号 | `lifecycle_projection.py` |
| Human/Coordinator Abandon Session | `session_workflow.py` / `coordination_workflow.py` / `session_lifecycle.py` |
| 项目总览页 DOM（唯一活界面） | `projects.mjs`（+ `projects-model.mjs` 纯逻辑；`project.html`/`session.html` 为静态退役提示页，无对应 .mjs） |
| 旧原型 DOM（已退役：UI 入口删除，仅存派生数据供运维/测试） | —（原 `app.mjs`；`project.mjs`/`session.mjs` 已随 b63b87a 删除） |
| 前端纯逻辑/格式化 | `ui-common.mjs` / `ux-polish.mjs`（`model.mjs`/`project-model.mjs`/`session-model.mjs` 已随原型退役） |
| 测试入口 | `scripts/verify.py` |

## 分层禁止

- `local_server.py`：不写磁盘、不调 `_atomic_write`、不夹带业务逻辑。
- Contracts：不 import `ProjectStore` / `WorkflowService` / `local_server`。
- `project_store.py`：不 import workflow 模块，不 import `local_server`。
- `context_compiler.py`：不 import HTTP 层，不引用 `private-data` 路径。
- `mutate_v2` / Ledger / receipt / backup / Restore / 原子写：默认不重构，除非发现真实 bug。

## 插件边界

- `plugin_registry.py` 只读插件清单与 Manifest，路由只做 URL 白名单。
- 插件不会直接改写项目数据；写路径必须像内置逻辑一样通过 workflow → store。
- 相关动态：`GET /api/plugins` 与项目页内插件动作渲染。

## CAT 边界

- CAT 是独立仓库 `co-agent-2`；PAOS 本仓库**不包含 CAT 代码**。
- PAOS 与 CAT 之间只通过 CAT 的 HTTP API 互操作。
- 不要把 CAT 的 runtime adapter、inbox/marker/STOP 行为搬进 PAOS 后端。
