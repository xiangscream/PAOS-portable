# 05 唤醒：控制器、驱动与 attempt

唤醒（Wake）解决的是一件事：PAOS 有事要交给某个 Agent，但那个 Agent 的原生会话不在手上——怎么把 prompt 送进去。

## 定位先说清楚

`scripts/paos_wakeup.py` 开头的 docstring 定死了边界：

> Wake is an operational connectivity layer. It does not own Project/Work facts, Workstation Mail content, CAT exchanges, or task completion state.

唤醒层**只管连接**。项目的对不对、Work 完没完成、Mail 里写的什么、CAT 房间里的业务内容，都不归它管。

## 三层结构

| 层 | 位置 | 职责 |
|---|---|---|
| 控制器 | `scripts/paos_wakeup.py`（810 行） | 绑定管理、attempt 生命周期、状态快照 |
| 驱动 | `scripts/wakeup_drivers/` | 各 Runtime 的连接机制，一个 Runtime 一个驱动 |
| 原生侧 | `scripts/wakeup_native/` | 跑在 Runtime 里的 worker 与扩展 |

驱动共 6 个：`base`（契约）、`codex`、`manual`、`mock`、`opencode`、`workbuddy`。

## 驱动契约

`wakeup_drivers/base.py` 定义 `WakeDriver`，`WAKE_DRIVER_API = "paos-wake-driver/v1"`。类 docstring 同样划了线：

> Drivers own Runtime connectivity mechanics only. They must not read or mutate PAOS Project governance facts, Workstation Mail bodies, or CAT business content.

方法：

| 方法 | 语义 |
|---|---|
| `validate_config` | 配置结构性校验 |
| `setup(binding)` | 准备绑定，必须可重试且快速返回 |
| `probe(binding)` | 检查 Runtime 可达性，**不产生 model turn** |
| `wake(...)` | 请求一次 Runtime 续接 |
| `recover(binding)` | 修复连接，**不产生 model turn** |
| `stop(binding)` | 停掉驱动自己的 sidecar |
| `test(binding)` | 自检，默认等同 probe |

驱动用三个类属性声明自己：`name`、`runtime_ids`、`supports_external_wake`。`workbuddy.py:20-23` 声明 `supports_external_wake = True`。

## wake 的硬约束

`base.py` 里 `wake` 的 docstring 说了两件事：

1. 控制器在进入 `wake` **之前**，已经把 attempt 以 `state=triggering` 持久化了；
2. driver **不得**以会产生重复 model turn 的方式内部重试，除非把这个行为报告出来。

第一条对应控制器 docstring 的另一句：

> A crash after the external side effect but before result persistence therefore leaves an explicit uncertain attempt instead of silently retrying a model turn.

翻译：副作用已经发出、结果还没写下来时进程崩了，系统留下的是一个**显式标记为 uncertain 的 attempt**，而不是悄悄再发一次 prompt。宁可留一个"不知道成没成"的记录，也不冒"让模型跑两遍"的风险。

代码里能看到这条：`_mark_triggering_uncertain`（`paos_wakeup.py:658`）在控制器恢复时，把仍处于 `triggering` 的 attempt 标成 uncertain（`661-670` 行），`triggering_means_external_result_unknown_after_process_loss: True`（455 行）。

## attempt 是什么

`WAKE_ATTEMPT_SCHEMA = "paos-wake-attempt/v1"`（`paos_wakeup.py:31`）。

一次 attempt 是一条**持久化的回执**，不是一次函数调用。它有 `state`（`triggering` → 结果态）、`attempt_id`、`source_kind`、`source_id`、`prompt_sha256`。

**attempt 被接受 ≠ 任务已完成。** 这条在实战里最容易踩：attempt `state=accepted` 只说明 prompt 被 Runtime 接走了，模型有没有真的跑完是另一回事。判断完成要看别的事实（`completed`、bridge 返回值、原生侧状态），不能拿 accepted 当完成。

## WorkBuddy 驱动怎么工作

`wakeup_drivers/workbuddy.py`：

- `_runtime(binding)`（37 行）读运行时文件，拿到本地 endpoint；
- `_call(runtime, path, payload)`（52 行）走本地 HTTP；
- `wake`（75 行）支持传 `model_id`；
- `probe`（62 行）、`stop`（102 行）、`recover`（109 行）各自实现。

配套的原生侧在 `scripts/wakeup_native/workbuddy_extension/`：`extension.json`、`distribution.json`、`server/`、`send.cjs`、`test.cjs`。扩展只申请一个权限 `conversations.sendPrompt`，监听 127.0.0.1，用一个随机 token 做本地鉴权，token 不进日志也不进 SDK 参数。

## 相关文件

- `scripts/wakeup_native/` 下还有 `codex_worker.py`、`opencode_worker.py`、`workbuddy_notice_worker.py`、`room_seam_status.py`——各 Runtime 的常驻消费端。
- `scripts/collab_adapters/` 是协作适配器（`base`/`command`/`manual`/`mock`/`self`）。
- `scripts/collab_watcher.py`（637 行）是协作监视器。
