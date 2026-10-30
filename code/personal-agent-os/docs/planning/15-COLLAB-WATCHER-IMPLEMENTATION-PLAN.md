# PAOS Collaboration Watcher 实施方案 v2（审查后修订）

> 状态：有条件通过，待实施
> 关联：3002-w010 · Project Coordinator v0 之后的多 Agent 自唤醒协作
> 修订原因：采纳审查意见，修复 5 个 P1（重复唤醒 / 并发启动 / 失败重试 / Run 级锁 / 准则冲突）并重排为三个实施包。

## 1. 架构与命名

```text
PAOS Coordinator / Request（已有状态源）
        ↓
PAOS Collaboration Watcher（Sidecar，决定“该不该唤醒”）
        ↓
Runtime Adapter（决定“怎么唤醒”，每个 Runtime 一个配置）
        ↓
Codex / Claude / DPHS / WorkBuddy 原生会话
```

Watcher 在协作 Run 期间作为独立进程运行；不进入 PAOS 常驻服务主进程。它不理解业务任务，不代替 Agent 领取 Work。

**授权边界（与开发准则同步后的版本）：**
PAOS 主服务不自动启动 Agent。人类显式创建并启动、限定 Session、有效期与任务数的临时 Collaboration Run，可以在其生命周期内调用已配置的 Runtime Adapter。

## 2. 目录与数据结构

### 2.1 协作 Run 目录（git-ignored 数据区）

```text
private-data/collab/<run_id>/
├─ run.json          # 一次协作的全部配置
├─ STOP             # 放置即触发停止
├─ WATCHER.lock     # Run 级生命周期锁，阻止第二个 Watcher 进程
├─ events.jsonl     # 追加式事件：seen/wake/failure/stop...
└─ state.json       # watcher 幂等状态
```

删除上一版 `locks/<session_id>`：同步轮询 v0 没有可靠的跨进程作用，真正需要的是整个 Run 只有一个 Watcher。

### 2.2 run.json（v0 schema）

```json
{
  "schema": "paos-collab-run/v0",
  "run_id": "run-20260820-001",
  "project_id": "2001",
  "paos_base_url": "http://127.0.0.1:8766",
  "created_at": "2026-08-20T10:00:00Z",
  "expires_at": "2026-08-20T11:00:00Z",
  "poll_seconds": 15,
  "wake_prompt_template": "去 PAOS 领取新周期。",
  "sessions": {
    "2001-s010": {
      "role": "coordinator",
      "adapter": "manual",
      "adapter_config": {}
    },
    "2001-s011": {
      "role": "worker",
      "adapter": "command",
      "adapter_config": {
        "runtime": "claude",
        "command_template": ["<path-to-claude>", "--resume", "{native_session_id}", "-p", "{wake_prompt}"],
        "cwd": "C:\\Users\\remo\\Desktop\\agent学习计划",
        "native_session_id": "<Agent 自行填入>",
        "env": {"PATH": "<覆盖/附加，默认为继承>"}
      }
    }
  },
  "limits": {
    "max_tasks_per_run": 1,
    "max_concurrency_per_session": 1,
    "wake_once_per_request": true
  }
}
```

字段说明：
- `paos_base_url` 必须显式写。Windows 与 WSL 不一定共用 `127.0.0.1:8766`；
- `expires_at` 是硬截止：到期即视为 STOP；
- `adapter` 只允许四种值：`manual`、`mock`、`command`、`self`；
- `command_template` 是参数列表，永远 `shell=False`；占位符只允许 `{native_session_id}` 与 `{wake_prompt}`；
- `env` 语义是覆盖/追加到当前进程环境（`os.environ` 基础上 update），不是新环境；
- Agent 只允许改 `native_session_id`、`cwd`、`env`、`command_template`；其余字段由人类/Coordinator 冻结；
- `max_tasks_per_run` 统计的是成功进入 `woken` 的 Request 数量；最小实验默认 `1`。

### 2.3 state.json（Watcher 私有）

```json
{
  "schema": "paos-collab-watcher-state/v0",
  "run_id": "run-20260820-001",
  "requests": {
    "2001-r002": {
      "state": "triggering",
      "session_id": "2001-s011",
      "updated_at": "..."
    }
  },
  "tasks_woken": 1,
  "updated_at": "..."
}
```

状态机（每个 Request 一条，at-most-once）：

```text
triggering → woken → resolved
                  ↘ failed
                  ↘ uncertain（Watcher 重启时才可能产生）
```

- `triggering`：先原子写 state，再调用 Adapter。若写 state 前进程被启动、写盘前崩溃，就产生对外副作用；因此顺序必须是 state 先行。
- `woken`：Adapter 返回成功。
- `failed`：Adapter 失败或不确定时落此状态；一次 Request 自动尝试一次，不自动重试。人类检查后显式删除该条或执行 retry。
- `uncertain`：Watcher 重启时发现 `triggering`（上次在 state 后、Adapter 结果前崩溃），改写为 `uncertain`，不自动重试，交由人类判断。
- `resolved`：从 Project 的 `requests` 事实中确认该 Request status 已不为 open。
- state.json 读取失败/损坏 → Watcher 立即退出并报错，**不得当作空状态重建**。
- 每次写 state 用临时文件 + `os.replace`；先写 state，后 Popen。

### 2.4 events.jsonl（追加式）

行格式：

```json
{"ts": "2026-08-20T10:00:01Z", "event": "watcher.pass", "run_id": "...", "detail": "seen=2"}
{"ts": "2026-08-20T10:00:16Z", "event": "request.triggering", "request_id": "2001-r002", "session_id": "2001-s011", "adapter": "command"}
{"ts": "2026-08-20T10:00:16Z", "event": "wake.success", "request_id": "2001-r002", "session_id": "2001-s011", "detail": "pid=... command=..."}
{"ts": "2026-08-20T10:15:00Z", "event": "stop.seen", "detail": "STOP exists"}
```

事件语义：`完整行均可解析；读取时若末尾有残行（进程崩溃半行）允许忽略最后一条`。不得对中间完整行报错。

## 3. Component 设计

### 3.1 Watcher（`scripts/collab_watcher.py`，下划线便于测试导入）

单次模式（`--once`）为 v0 默认运行方式，也为测试入口。

循环逻辑：

```text
启动：
  1. 解析 --run-id；读 run.json（无则退出）
  2. 用 O_CREAT|O_EXCL 创建 WATCHER.lock 并持有到退出；
     已存在则检查 PID 是否存活：存活 → 拒绝启动第二个实例；不存活 → 移除重建
  3. 读 state.json（缺失 → 新建空；损坏 → 立即退出报错）
  4. 检查 STOP / expires_at / max_tasks_per_run 是否已达上限

每轮：
  1. 开头检查 STOP / expires_at / 上限；任一成立 → 停止
  2. GET project 当前 revision → 读项目 requests 事实
  3. GET office?session_id= 每个目标 Session
  4. 对每个 open pending_request：
     - state.requests 已存在 → skip（已 woken/resolved/failed/uncertain 都不重放）
     - T-CW-01 单次版：tasks_woken >= max_tasks_per_run → skip
     - 先原子写 state=triggering
     - 再检查一次 STOP（写 state 后、Popen 前；缩小已喊停仍启动的窗口）
     - 调用 Adapter
     - 成功 → state=woken；失败 → state=failed（不自动重试）
  5. 对 state 中 woken 的 Request：
     - 当 project.requests 显示该 Request 已 resolved，
       且（T-CW-03）Adapter 报告启动的子进程已退出 → state=resolved
     - T-CW-01/02 未实现进程跟踪时：每个 Session 每个 Run 最多唤醒一次，
       不因 Request resolved 释放 busy
  6. sleep poll_seconds；--once 则结束
```

要点：
- `Request resolved` 不等于 Worker 空闲。`switch_work` 在领取时立即 resolve；真实释放条件必须是 **子进程退出**。未实现进程跟踪前，busy 的释放条件就是"本 Run 不再对该 Session 自动唤醒"。
- 可以从 `pending_requests` 消失推知可能 resolved，但结论必须用 `project.requests` 事实核验。

### 3.2 Runtime Adapter（`scripts/collab_adapters/`）

接口：

```python
class BaseAdapter:
    name = "base"

    def can_wake(self) -> tuple[bool, str]:
        """(是否确定能唤醒, 原因)。不能确定时必须返回 False。"""

    def wake(self, *, target_session_id, native_session_id, wake_prompt, run_ctx) -> dict:
        """返回快、非阻塞。{"ok": bool, "pid": int|None, "detail": str}"""
```

首批实现：
- `manual`：`can_wake` 永远 False，事件记 `wake.needs_manual`；
- `mock`：只记 events，返回 ok=True、pid=None；
- `command`：按 `command_template` 参数列表 `subprocess.Popen(..., shell=False)`；`env` 用 `os.environ` 为基再 update；`can_wake` 校验模板路径与占位符。

`command` Adapter 对已启动的进程不追踪状态。若将来需要，T-CW-03 增加 `poll()` 报告进程是否退出。若 Runtime 启动后脱离父进程，Adapter 文档必须标 `unverified` 并说明"pid 不代表真实任务"。

### 3.2.1 通用 `self` Adapter（WorkBuddy 是第一个实例）

WorkBuddy 实测有内置 CLI（`D:\work\WorkBuddy\resources\app.asar.unpacked\cli\bin\codebuddy`，v2.115.0，`-p` 非交互可运行）。但用户明确：不用 CLI 唤醒，要 GUI 正常交互。

因此 Watcher 不做 runtime 判断，只认三种触发模式：
- `external`：由外部 Watcher 调命令；
- `self`：Agent 自己轮询 PAOS / 自己配置 automation；
- `manual`：只能人工唤醒。

`adapter="self"` 与 `adapter="manual"` 是通用类型，不是 WorkBuddy 专属。WorkBuddy 只是 `self` 的第一个实例。

WorkBuddy GUI automation 的固定 prompt 模板（人类在 GUI 里创建，Watcher 代码不包含它）：

```text
每 5 分钟检查一次以下内容，就在当前 GUI 会话内运行，不要用 CLI：
1. 若 private-data/collab/<run_id>/STOP 存在：停止本次轮询并说明已停止。
2. 否则 GET http://127.0.0.1:8766/api/projects/<pid>/office?session_id=<WorkBuddy 的 PAOS Session ID>
3. pending_requests 为空：回复“本轮暂无任务，等待下一次轮询”。
4. 有 pending_requests：按 PAOS 流程领取：读 Project/Session → switch_work 带 coordination_request_id → Acknowledge → 执行任务 → Update/Close。
同一 Request ID 只处理一次。
```

Agent 自己配置 hook/automation 时必须遵守：
- 未经用户明确要求，不修改全局 `~/.codebuddy/settings.json`；
- 优先使用会话级/本地配置；
- 创建后向用户报告名称、周期、怎样停止。

### 3.3 Run 级锁（WATCHER.lock）

- 创建与持有：Watcher 启动时独占创建，整个生命周期持有；
- 拒绝：已有锁且 PID 存活 → 立即退出；
- stale 恢复：PID 不存活 → 移除后重建；
- 不再实现 Session 级锁文件，避免"看起来有用其实挡不住两个 Watcher"的机制。

## 4. 实施包重排

### T-CW-01：单次 Watcher（已完成本地实现与审查修复）

- `--once`：读 run.json → 先对账已有状态 → 检查 STOP/过期/上限 → 拉取 office → 对最先满足条件的一个 Request 走 triggering/woken/failed → 退出
- mock adapter 只返回结构化结果；`events.jsonl` 由 Watcher 单点写入
- Run 级锁：活 PID 拒绝第二实例，死亡 PID 的 stale lock 可安全接管
- state.json 状态机：triggering/woken/failed/uncertain/cancelled/resolved/manual_notified/delegated
- 发现崩溃遗留 triggering 时转 uncertain 并停止本轮，不再自动唤醒其他 Request
- T-CW-01 严格要求 max_tasks_per_run=1、max_concurrency_per_session=1、wake_once_per_request=true
- STOP / expires_at 在真正启动外部进程前紧邻复查
- events.jsonl 允许忽略并截断 EOF 残行；中间坏行必须报错
- 不实现多任务循环、不实现 session_busy、不实现真实 Runtime
- 本地验收：Watcher 27 项、全套 11 套件 360/360 通过；尚未完成 T-CW-02 真实 Runtime 验证

### T-CW-02：一个真实 Runtime（只挑一个验证）

- 从 Codex / Claude / DPHS 中挑最容易实测的一个
- 验证：resume 指定原生 session、进程退出行为、是否会开新 session、Windows/WSL 对 `paos_base_url` 的可达性
- 跑通一次真实链：Work → Request → Wake → switch_work → Ack
- 未验证的 Runtime 一律 `manual` / `unverified`

### T-CW-03：临时循环

- 多 Request、轮询循环、STOP、expires_at、max_tasks_per_run
- session_busy 生命周期与子进程退出跟踪（按 Adapter 真实能力设计）
- Worker 完成如何唤醒 Coordinator（返程）
- 只有 T-CW-02 证明某个 Runtime 能稳定恢复原会话后才开始

## 5. 最小实验与验收

### T-CW-01 验收

1. 一个 Request 只写一条 `woken`；
2. 没有 open Request 时不调用任何 Adapter；
3. Watcher 重启后对 `woken/failed/uncertain` 不重放；
4. state 先于 Popen：崩溃在 Popen 前不会产生进程；崩溃在 Popen 后重启进入 `uncertain`；
5. STOP 在轮询开头与 Popen 前都检查；
6. 两个 Watcher 同时启动时，后启动者被 WATCHER.lock 拒绝。

### 三个包累计验收（T-CW-02/03 完成后）

1. 一个 Request 只唤醒一次；
2. 无 Request 不启动进程；
3. switch_work 与 Ack 正常；
4. Watcher 重启不重放；
5. STOP 一个轮询周期内生效；
6. PAOS Ledger / Work / Session / Request 与实际一致；
7. events.jsonl 完整行可解析，末尾残行可忽略。

## 6. 测试策略

- `test_collab_watcher.py`（Python，只测纯逻辑）：
  - run.json 合法性（schema、adapter 枚举、占位符、paos_base_url、max_tasks=1）
  - WATCHER.lock 有效/stale
  - state 状态机：triggering→woken/failed、重启 triggering→uncertain、损坏时退出
  - state 原子写与先写后启动顺序
  - STOP/expires/上限判定
- 回归：Watcher 不在主服务，现有 329 项不受影响。

## 7. 开发准则同步

`docs/DEVELOPMENT-PRINCIPLES.md` 中"不自动启动或调度外部 Agent"改为：

```text
PAOS 主服务不自动启动或调度外部 Agent。
人类显式创建并启动的临时 Collaboration Run，可以在限定 Session、有效期与任务数内，通过 Runtime Adapter 调用已配置的唤醒入口。
```
