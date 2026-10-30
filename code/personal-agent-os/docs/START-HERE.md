# Start Here — 先跑通一个真实 Project

PAOS 最容易通过一次真实工作理解。第一次使用只需要关注 Project、Agent 与 Session。Agent 是长期成员，可在不重新分配身份的前提下更换 Runtime。方法在共享 Workflow，入口见本页「日常入口（执行方法）」；其它能力按需打开。

## 当前安装

- **现行安装版本**：以 `paos health` 实读为准；已接受的发布快照见 [V1.3 发布事实](V1.3-RELEASE-FACTS.md) 与 release manifest。
- 历史材料仅供追溯，不作为当前说明或重新入场指令。

## 日常入口（执行方法）

日常工作方法读共享 Workflow，不在本页复制。按目的取用：

- 恢复、执行、收口：[Agent 工作循环] — `<workflow_root>/Workflows/wf-agent-work-cycle.md`；
- 方法导航：[工作入口 GUIDE] — `<workflow_root>/Guides/guide-work-method.md`；
- 按目的找命令：[操作入口 OPS] — `<workflow_root>/Guides/ops-entry.md`。

`<workflow_root>` 由 `paos library roots show` 读取。Library 未登记时，先注册 Library roots 再打开以上正文；本页只给入口，不手抄正文。

## 1. 启动 PAOS

Windows 在仓库根目录运行：

```powershell
.\scripts\start.ps1
```

启动链：`scripts/start.ps1` → `attention-dashboard-v1-static/paos_server.py`（薄壳，`import local_server` 并挂 `X-PAOS-Runtime-Fingerprint` 响应头）→ 核心 `attention-dashboard-v1-static/local_server.py`。

浏览器打开（真实界面，读真实项目数据）：

```text
http://127.0.0.1:8766/attention-dashboard-v1-static/projects.html
```

注意：旧原型界面 `index.html` + `app.mjs`（读合成数据）已退役；唯一活界面是 `projects.html`（项目总览，走 /api/*）；`project.html`/`session.html` 为静态退役提示页（不读数据，改用固定工位 Current/Mail/Notice 与同版 CLI）。定位代码先读 [`CODE-MAP`](CODE-MAP.md)。

如果 Agent 运行在 WSL2，参见 [`WSL-ACCESS.md`](WSL-ACCESS.md)。CLI 安装描述符及 Windows/WSL 共用入口示例见 [`contracts/CLI-INSTALLATION-LOCATOR-V1.md`](contracts/CLI-INSTALLATION-LOCATOR-V1.md)。

## 2. 创建一个真实 Project

选一个你之后还会继续回来的真实项目。第一次只需要写清：

- 项目名称；
- 当前最重要的要求或承诺；
- 所属 Area。

现行 CLI 没有创建 Project 的子命令（`paos project` 只提供 `show` / `inspect`）。真实入口是核心 HTTP 路由 **`POST /api/projects`**，请求体是**完整的 current-schema 项目态**（`paos-project/v3`，经 `validate_project` 校验），不是只给名称/承诺/Area 就自动补全。骨架可由 `project_domain.empty_project(id, name, area)` 生成：`id` 必须与 `area` 的编号段一致（`AREA_PREFIXES`）。创建 Project **不**创建员工工位。完整字段与示例见 `attention-dashboard-v1-static/project_schema.py` 与 `project_domain.py`。

不用先把未来所有事项建出来。

## 3. 为一位 Agent 开一个 Session（新 Project / 新员工登记）

项目建好后，现行 CLI 没有 `session open`（`paos session` 现有子命令见 `--help`）。真实入口是 **`POST /api/projects/{id}/sessions`**：会话创建即登记该员工并初始化固定工位（`ensure_fixed_workstation` 写入 ENTRY/TODO/mailbox/notices），随后在 `paos orient` 可见。Open 返回的 `prompt_markdown` 就是交给 Agent 的入场说明，其中已经带好项目事实、边界、接口与写入合同。

Open 需要写明的是：这次要达成的目标（`mission.objective`）、完成定义（`done_when`）、以及执行者身份（`identity_id`）。`session ack` 仅保留为可选作证件。

**已有员工换 Runtime（不重新分配身份）**：工位与身份不变，不重新登记员工、不再开新身份。换的是**原生联系目标**，不是 Session 元数据：`session update` 只写状态/摘要/交接，**没有** Runtime / 原生会话 / 联系参数。真实写链是联系登记 —— `paos wake bind <project> <Agent> --driver <codex|opencode|workbuddy> --native-session-id <原生会话ID> --driver-config <JSON文件路径>`：`--native-session-id` 是**必填**的原生会话 ID（`execute_wake` 在读 driver-config 之前先校验它，不能只放进 JSON）；`--driver-config` 传 **UTF-8 JSON 文件路径**（文件含 `base_url` 等；不是内联 JSON）。调用保存原 target，并按本人 receiver 准备（见 Rooter 原入口恢复说明）。联系目标未换绑前，不要当作已切换。

Session 是执行记录，不是任务清单：一个 Session 记录一位 Agent 在这一段执行里的目标、进展、产物与请求。项目级的责任与承诺仍然写在 Project 上。

## 4. 交给 Agent

把 Open 返回的 `prompt_markdown` 粘贴到你实际使用的 Agent Runtime 中。手动复制粘贴是正式主路径，不需要 CAT、hook 或特定 Runtime 集成。

## 5. 让 Agent 正常工作

Agent 应该：

- 首次入场即开始工作（Workless 正常路径无 ACK 前置；需要郑重作证时才用可选 `session ack`）；原生联系目标由 Contact 登记（`paos wake bind`），`session update` 本身不含 Runtime/联系字段；更换原生会话不重复办理入场；
- 使用自己的工具和判断完成专业工作；
- 在产生有意义的进展、结果或交接时更新 PAOS。

不要为了证明 Agent 还活着而制造无意义的 Update。

日常执行与 Coordinator 工作方法统一使用共享 Workflow，入口见本页「日常入口（执行方法）」。日常委托只传目标、输入和完成标准，不复制指南全文。

## 6. 回到 PAOS

Project 页面首先回答这些问题：

- 当前项目状态是什么？
- 哪位 Agent 正在推进，当前目标是什么？
- 什么事情真的需要我？
- 当前结果是否已经可以评审或继续？

原生 Runtime 的一次 Session 结束，不等于责任完成。是否完成以人类对实际结果的验收为准。

## 7. 继续同一个 Agent

新原生会话从本人工位 ENTRY、TODO 当前区与 `paos orient` 继续已有责任。接班原则以 [产品哲学](PRODUCT-AND-DESIGN-PHILOSOPHY.md) 为准，具体操作读共享 Workflow；旧的 Cycle 接班手续不再是正常路径。

## 8. 有真实需要时再打开高级能力

- **需要我处理**：只有没有人类判断就无法正确继续的事项；
- **项目负责人 / Coordinator**：Project 级规划、分工与责任收口；
- **CAT（系统级圆桌）**：跨 Project 的同事协作与公开讨论；入口见共享 OPS 的「CAT 圆桌」；
- **资料与记录**：历史 Agent、历史 Session、Decision、文件等；
- **高级 / 管理**：原始状态维护、修正、Project Restore 与诊断。

如果这些能力还没有解决你的真实摩擦，就先不用配置。
