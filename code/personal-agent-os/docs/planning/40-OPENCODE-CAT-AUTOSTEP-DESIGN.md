# 40 · opencode 适配 CAT 配置自动续步（设计研究）

> 目标：研究 opencode 如何以优雅、最小侵入的方式，复用 CAT 既有的「自动续步」契约
> （durable inbox + marker + STOP + TTL），让一个 opencode 会话在收到 CAT 新消息时
> 自动唤醒并连续续步，而不依赖人工每轮回车。
> 状态：研究结论 + 推荐方案（未实现）。

## 1. 结论（TL;DR）

推荐方案：**一个外部 sidecar 适配器 `opencode_cat_adapter`**，而不是给 opencode
写 in-process 插件或 Stop hook。

- 它直接读取 CAT 已经写好的 **`scope.json`**（即「CAT 配置」）——里面含
  `room_id` / `participant_id` / `marker_file` / `stop_file` / `expires_at`。
- 它监听 CAT 的 **`marker.json`**（一次性唤醒桥），在被唤醒时通过 opencode 自带的
  **HTTP Server API `POST /session/:id/message`** 给正在运行的 opencode 会话
  注入一条「处理 CAT inbox」的提示。
- 续步（continuation）由适配器自身的**消息循环**完成：上一轮结束后再查 inbox，
  还有消息就再发一条。activation 与 continuation 在同一个循环里，无需两种机制。
- CAT 侧、opencode 核心**都不用改**；适配器是「Agent 自决」的运行时组件，与现有
  Codex Event Bridge / DSH 插件属于同一适配器家族。

为什么比「in-process hook」优雅：opencode 已有官方、稳定的「以编程方式驱动会话」
的通道（这正是一体化 TUI/IDE 插件所用的同一架构），sidecar 只是换了个客户端；
不需要深入 opencode 内部 hook 协议，也不需要在每次 opencode 升级时复测 hook 层。

## 2. CAT 的「自动续步」契约（opencode 要适配的配置）

CAT 不向任何 GUI 注入伪输入，只负责：持久 inbox、marker、STOP、TTL。唤醒与续步
完全由 Runtime Adapter 在自己原生生命周期里完成。

- `scope.json`（`co-agent-hook-scope/v1`）—— 每个 room+participant 一份，是适配器的
  唯一配置来源：
  ```json
  {
    "schema": "co-agent-hook-scope/v1",
    "room_id": "room-xxxx",
    "participant_id": "p-3002-sXXX",
    "native_session_id": "",
    "marker_file": "<runtime>/<participant>/marker.json",
    "stop_file": "<room>/STOP",
    "expires_at": ""
  }
  ```
- `marker.json`（`co-agent-marker/v1`）—— CAT 在有新 exchange 给该 participant 时
  **原子写入**的一次性桥；只含 `exchange_id` 引用，不含业务正文。适配器读后 claim 并
  转去查 inbox HTTP 接口。
- `STOP` 文件 + `expires_at` —— Room 停止 / 过期的 TTL 信号，适配器见到即退出。

现有 Runtime 如何实现两层语义（activation=唤醒空闲会话 / continuation=回合边界续步）：

| Runtime | activation（空闲唤醒） | continuation（续步） |
|---|---|---|
| Codex Desktop | Event Bridge sidecar 监听 marker 文件事件 → 同 thread 新回合 | Stop hook（`codex_stop_router.py`）读到 marker 输出 `decision:block` |
| DS-H | 原生 `dsh-cat-inbox` poller 按 `pollIntervalMs` 轮询 | `agent.followup()` 即排一个新回合 |
| **opencode（本方案）** | **sidecar 监听 marker → `POST /session/:id/message`** | **sidecar 消息循环：上一轮后复查 inbox 再发一条** |

关键事实：Codex 的 Stop hook **无法**从完全空闲状态唤醒会话；opencode 用 sidecar
直接打 Server API，天然同时覆盖激活与续步两层，机制更少。

## 3. opencode 侧可用原生能力（已核实，opencode 1.18.18）

- `opencode serve [--port 4096]`：无头 HTTP Server，暴露 OpenAPI 3.1（`/doc`）。
  这是「以编程方式驱动 opencode」的官方通道（IDE 插件同理）。
- 相关端点（来自 `/doc`）：
  - `POST /session/:id/message` —— 发消息并**等待响应**返回。
  - `POST /session/:id/prompt_async` —— 异步投递（不等待），返回 204。
  - `POST /session/:id/abort` —— 中止运行中会话。
  - `GET /session` / `POST /session` —— 列出 / 新建会话；`POST /session/:id/fork`。
  - `GET /event` —— SSE 事件流（可用来判断会话何时回到 idle，作为续步触发点）。
  - `POST /tui/submit-prompt` 等 TUI 控制端点（若以 TUI 方式运行）。
- CLI 续跑：`opencode run -c -s <session_id> "<prompt>"` 可在无 Server 时续跑指定
  会话；配合 `--port` 固定 Server 端口最稳。
- 插件：`opencode plugin` / `.opencode/plugins/` 可加 custom tools、hooks、集成。
  本方案**不依赖**插件机制，保持 sidecar 外部化。

客户端可直接用官方 SDK（`@opencode-ai/sdk`）或裸 HTTP 调上述端点。

## 4. 推荐设计：`opencode_cat_adapter`（sidecar）

### 4.1 生命周期
```
加入 Room → 读 scope.json（CAT 配置） → 启动 sidecar（单实例互斥）
        → inotify/轮询 marker.json
        → 命中且非 STOP/未过期 → POST /session/:id/message "处理 CAT inbox <room>/<participant>"
        → 等待响应（或监听 /event idle）→ 复查 inbox → 有则再发（续步循环）
        → 直到 inbox 空 / 收到 STOP / 过期 → 退出；CAT 侧无需清理
```

### 4.2 绑定与单实例
- 绑定身份 = `scope.json` 里的 `participant_id`（与 Codex/DSH 一致，per
  room+participant，避免并行 Room 唤醒错会话）。
- 同 participant 只允许一个 sidecar；复用 Windows named mutex / PID 文件保证单实例，
  退出自动释放（对齐 Codex Event Bridge 的实现约定）。
- 冷恢复：`start` 前清掉 stale runtime 记录与残留 STOP 文件；`status` 报告
  `running` / `stale` / `not_running`，参考 `codex_event_bridge_control.py`。

### 4.3 续步循环（统一 activation + continuation）
- 不依赖 opencode 的 Stop hook。sidecar 在「收到响应」或「`/event` 回到 idle」后
  主动再查 CAT inbox；有未 ack 消息就再 `POST /message` 一条。这样：
  - 空闲会话被 marker 唤醒 = activation；
  - 同一会话连续多步 = continuation；
  - 二者同一段代码，无第二种机制。

### 4.4 与 CAT 的交互（沿用现有协议，零改造）
- 唤醒：`marker.json` 出现 → 适配器 claim → `GET /api/rooms/<room>/inbox?participant_id=`
  → 处理 → `POST /api/rooms/<room>/acknowledge`（与 `cat_polling_agent.py` 同款）。
- 停止：检测到 `<room>/STOP` 或 `expires_at` 已过 → sidecar 自行退出。
- 适配器**不读取/不修改** CAT 或 PAOS 业务正文，只做唤醒与 inbox 拉取/ack。

## 5. 备选方案（不推荐，记录取舍）

- **B. in-process 插件 + Stop hook**：用 opencode plugin 注册 hook，在回合边界输出
  continue 指令。缺点：需深入 opencode hook 协议，升级需复测 hook 层；且 hook 难以
  从完全空闲状态唤醒（与 Codex 同一坑）。sidecar 已覆盖两层，更省事。
- **C. 纯 `opencode run -c -s` 轮询脚本**：无 Server 时可用，但每次起进程较重、
  难做 idle 精确触发；仅作无 Server 环境的降级方案。

## 6. 待验证 / 下一步（建议立项后再做）

1. 起 `opencode serve --port 4096`，用 SDK 发一条 `POST /session/:id/message`，
   确认响应结构与 idle 事件（`/event`）可作为续步触发点。
2. 用 `cat_polling_agent.py` 的 inbox/ack 逻辑，写最小 `opencode_cat_adapter.py`
   原型，绑定一个真实 `scope.json` 做端到端唤醒+续步。
3. 验证单实例互斥、STOP/TTL 退出、冷恢复（重启后重绑 `participant_id`）。
4. 对齐 Codex Event Bridge 的「Runtime Truth 投影」约定（last_successful_wake_at
   等只作运行时证据，不进 CAT/PAOS 事实）。

## 7. 与现有 Work 的关系

- 本方案是 3002-w027「汇总摩擦，规划 PAOS 更新及审查代码」在「opencode 接入 CAT
  自动续步」方向上的具体设计产出。
- 复用 CAT 既有契约，不涉及 g008（Agent-Agent 关系边）/ g015（Room 筛选）等缺口。
- 实施前建议先以独立 Work 立项（见 PAOS Session Update 的 work_suggestion）。
