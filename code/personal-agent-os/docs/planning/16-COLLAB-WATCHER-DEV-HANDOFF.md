# PAOS Collaboration Watcher 开发交接

> 生成日期：2026-08-21
>
> 用途：交给下一位实施 Agent。本文描述当前工作树的真实状态，不代表已经提交、推送或完成真实 Runtime 验收。

## 1. 当前任务与总边界

项目：3002 · Personal Agent OS

当前方向：在已有 Project Coordinator v0 之上，增加一次性、可停止、可审计的多 Agent 唤醒协作。

关联设计：[`15-COLLAB-WATCHER-IMPLEMENTATION-PLAN.md`](15-COLLAB-WATCHER-IMPLEMENTATION-PLAN.md)

关联开发 Handoff：[`14-SESSION-3002-S013-DEV-HANDOFF.md`](14-SESSION-3002-S013-DEV-HANDOFF.md)

总体架构：

```text
PAOS Project / Work / Request / Session
                ↓
Collaboration Watcher（按需 Sidecar，不进入 PAOS 主服务）
                ↓
Runtime Adapter 或 Agent 自己的 GUI Automation
                ↓
Codex / Claude / DPHS / WorkBuddy 原生会话
```

PAOS 仍然只负责组织事实、Request、Work 领取、Session 状态、revision 和 receipt。不要把 Runtime 专用命令、GUI 控制或调度循环塞进 `local_server.py`、`workflow_service.py` 或 `project_store.py`。

## 2. 已有背景

Coordinator v0 已完成：

- 人类授权/撤销 Coordinator；
- Coordinator 创建正式 Work；
- Coordinator 创建带 `target_session_id` 与 `target_work_item_id` 的定向 Request；
- 子 Agent 通过 `office?session_id=` 看到 Request；
- `switch_work + coordination_request_id` 原子领取并 resolve Request；
- Context Pack / Prompt 投影待处理 Request。

Coordinator v0 的真实 LRC101 Step 5 仍未完成。Watcher 的真实 Runtime 验收也未完成。

## 3. 当前工作树中已经存在的 T-CW-01 实现

以下文件目前存在于工作树，但不能据此声称已提交：

- `scripts/collab_watcher.py`
- `scripts/collab_adapters/base.py`
- `scripts/collab_adapters/mock.py`
- `scripts/collab_adapters/manual.py`
- `scripts/collab_adapters/command.py`
- `scripts/collab_adapters/self.py`
- `attention-dashboard-v1-static/tests/test_collab_watcher.py`
- `scripts/verify.ps1` 中已加入该测试套件
- `docs/planning/15-COLLAB-WATCHER-IMPLEMENTATION-PLAN.md`
- `docs/DEVELOPMENT-PRINCIPLES.md` 中已把“主服务不调度”与“人类显式启动的临时 Collaboration Run”区分开

T-CW-01 当前实现范围：

- `--once` 单次运行；
- 读取 `private-data/collab/<run_id>/run.json`；
- 校验 `paos_base_url`、Project、Session、Adapter 和任务上限；
- 读取 Project 的 `requests` 事实；
- 读取 `office?session_id=` 的 `pending_requests`；
- `WATCHER.lock` Run 级生命周期锁；
- `STOP`、`expires_at`、`max_tasks_per_run`；
- `state.json` 原子写；
- Request 状态 `triggering / woken / failed / uncertain / cancelled / resolved`；
- `triggering` 先落盘，再调用外部 Adapter；
- Watcher 重启时不自动重放 `woken / failed / uncertain`；
- `mock`、`manual`、`command`、`self` 四种通用触发类型。

其中：

- `external`：Watcher 负责调用 Adapter；
- `self`：Watcher 不唤醒，Agent 自己配置 GUI automation 或其他轮询；
- `manual`：只记录需要人工唤醒；
- `mock`：只用于测试。

`self` 不是 WorkBuddy 专用适配器。WorkBuddy 只是目前第一个准备验证的 `self` 实例。

## 4. 当前验证证据

审查修复后已实际执行：

```text
Windows Python：test_collab_watcher.py 27/27 通过
Coordinator 专项：42/42 通过
临时 Project 端到端：grant → create Work → directed Request → switch+resolve → Ack 通过
scripts/verify.ps1：11 个套件，360/360 通过
```

本轮新增覆盖：stale lock 接管、uncertain 停止、严格单任务上限、状态语义校验、达上限前终态对账、EOF 残行修复、中间坏行拒绝、manual/self 去重、Command Adapter 确定失败、triggering 先行落盘、STOP/过期紧邻外部启动复查。

T-CW-02 真实 Runtime 仍未执行；不得把本地 mock/临时 Project 验证表述为已完成真实 Agent 唤醒。

T-CW-01 没有做以下事情：

- 没有调用真实 Codex / Claude / DPHS / WorkBuddy；
- 没有启动真实原生 Agent；
- 没有向真实 Project 写入 Work、Request 或 Session；
- 没有证明任何 GUI Automation 能恢复原生 Session；
- 没有完成 Worker → Coordinator 的返程唤醒。

## 5. 最重要的设计决策

### 5.1 Agent 自己选择唤醒方式

Agent 可以根据自己的 Runtime 选择：

- GUI automation；
- 原生 hook；
- command/CLI resume；
- manual。

但它不能自行决定 Project 权限、目标 Work、Coordinator 授权、STOP、有效期或最终 Review。

Agent 配置完成后，应报告：

```text
PAOS_ACTIVATION_READY
- Session：
- Mode：self / external / manual
- Runtime：
- Automation 或 Adapter ID：
- 周期：
- 原生 Session ID：
- 是否已在原 GUI Session 实测：
- 停止方式：
```

### 5.2 WorkBuddy GUI 路径

用户明确不希望使用 CLI 唤醒，而希望 GUI 中的原生 Session 正常交互。因此 WorkBuddy 只能先走 `self`：

```text
GUI Automation 每隔一段时间：
  检查 STOP
  GET Project / Session / office?session_id=
  没有 Request：静默结束本轮
  有 Request：switch_work + coordination_request_id
             → Acknowledge
             → 执行任务
             → Update / Close
```

不要让 automation 在没有 Request 时每轮向 GUI 写“暂无任务”，否则会污染对话记录。

STOP 文件只能保证不再领取新任务；它不一定能删除或禁用 Runtime 自己的 Automation。创建 Automation 时必须同时记录实际的停止方式；如果 Runtime 不支持自禁用，就由人类在 GUI 中关闭。

### 5.3 Watcher 不判断 Runtime

Watcher 只认识触发模式和统一结果，不增加 `CodexAdapter`、`ClaudeAdapter`、`WorkBuddyAdapter` 等专用类。

如果新的 Runtime 有 CLI，复用 `command`；如果 Runtime 能在 GUI 内部自行轮询，使用 `self`；无法自动化则使用 `manual`。

## 6. 下一位 Agent 的工作顺序

### 第一步：先审 T-CW-01，不要直接扩循环

先读：

1. `AGENTS.md`
2. `docs/DEVELOPMENT-PRINCIPLES.md`
3. `docs/planning/14-SESSION-3002-S013-DEV-HANDOFF.md`
4. `docs/planning/15-COLLAB-WATCHER-IMPLEMENTATION-PLAN.md`
5. 本文件

然后检查当前工作树，不能把已有用户修改、Coordinator 修改和 Watcher 修改混在一次提交。

### 第二步：T-CW-01 已完成本地验证

已确认：

- 27 项 Watcher 测试通过；
- `scripts/verify.ps1` 11 套件 360/360 通过；
- 活 PID 锁拒绝第二实例，死亡 PID stale lock 可接管；
- `triggering` 在 Adapter 调用前已原子写入磁盘；
- STOP 与 expires_at 在真正调用 Adapter 前紧邻复查；
- `triggering` 重启后变为 `uncertain` 并停止本轮，不会继续唤醒第二 Request；
- `failed / uncertain / cancelled / resolved / manual_notified / delegated` 不会被误当作新 Request；
- 达到任务上限、STOP 或过期时仍会先根据 Project 权威事实对账 `resolved/cancelled`；
- `events.jsonl` 的完整行可读，EOF 残行会在追加前截断，中间坏行会报错；
- Command Adapter 的入口/cwd/Popen 确定失败进入 `failed`，不会伪装成 `uncertain`。

### 第三步：只做一个真实 Runtime 实验

从 Codex、Claude、DPHS、WorkBuddy 中选择一个最容易验证的 Runtime。先不要扩展三 Agent 接力。

实验链：

```text
人类启动一个 Collaboration Run
→ 一个 Work + 一个定向 Request
→ 一次真实唤醒
→ 目标 Agent GET PAOS
→ switch_work + Ack
→ 做一个极小任务
→ Update / Close
→ 人类检查后 STOP
```

必须记录：

- 原生 Session 是否真的被恢复，而不是新开 Session；
- GUI 是否仍可见、可继续交互；
- Adapter 返回的 PID 是否代表真实任务；
- Windows/WSL 是否都能访问 `paos_base_url`；
- 重复调度是否会产生重复消息或并发运行。

未经实测的 Runtime 必须标记 `unverified`，不能写入“已支持”。

### 第四步：最后才做 T-CW-03

只有 T-CW-02 证明至少一个 Runtime 能稳定恢复后，才实现：

- 多 Request 循环；
- 子进程退出跟踪；
- Session busy 生命周期；
- STOP 与 expires_at 的持续生效；
- Worker 完成后如何唤醒 Coordinator；
- 实施 → 审计的多 Agent 接力。

## 7. 不要做的事

- 不要把 Watcher 接入 PAOS 常驻服务；
- 不要把 Runtime 命令写死在 PAOS 后端；
- 不要把 Watcher 脚本路径写入 `runtime_session.source_path`；
- 不要把项目目录、Vault 路径或 Automation 配置冒充原生会话日志路径；
- 不要因为测试方便而创建真实 Project、Session、Work 或 Request；
- 不要自动修改全局 Runtime 配置，除非用户明确授权；
- 不要在没有真实 Runtime 证据时宣称“多 Agent 已自动协作”；
- 不要为了这项实验引入 SQLite、第三方调度器或常驻服务。

## 8. 提交与工作区纪律

当前工作树有大量既有修改和未跟踪设计文件。提交前必须：

1. 明确本次只提交 T-CW-01 文件；
2. 不暂存 Coordinator 后端、前端和用户既有文档；
3. 保留各文件原有换行格式；
4. 运行 `git diff --ignore-space-at-eol` 与 `git ls-files --eol`；
5. 运行目标测试和全量 `verify.ps1`；
6. 报告真实测试数量、Git 状态、未触碰文件；
7. 未经用户授权不 push、不合并、不创建真实自动任务。

当前最安全的交付点是：

```text
T-CW-01 单次 Watcher + mock 测试已验证
T-CW-02 一个 Runtime 的真实唤醒已验证
```

在这两个事实成立前，不要继续扩展“自动实施 → 自动审计 → 自动返工”。
