# 多 Agent 协作自动化模式设计（29，v0.2 修订）

> 状态：修订稿 v0.2，**供再次审核**。
> 目标一句话：以 **PAOS 为唯一业务与协调事实源**；**人手动确认进入**协作模式；Worker 完成第一步后，如确有必要，**由 Worker 写下一次性续步标记**，由 **hook 在同一原生会话补一次续步**，然后停止。连续维持是待验证项，不是本版承诺。
> 本版按评审意见修订：收窄 hook 能力口径、修正 Request 边界、移除 WorkBuddy、信封不复用 T-CW-01、冻结五项决策。

---

## 0. 修订记录（v0.1 → v0.2）

1. **删除“持续自治”承诺**：v0.1 把「一次续步」写大成了「持续工作直到目标完成」。v0.2 的顶部承诺固定为：**一次人工进入 → Worker 完成第一步 → 可选一次续步 → 停止**。
2. **PAOS 与本地信封的关系收紧**：PAOS 是唯一业务/协调事实源；本地信封只是临时执行控制状态。`marker / 预算 / 本地状态` 不得判定 Work 完成、Request resolved 或交付通过。
3. **marker 结构化且由 Worker 决定**：marker 不是空文件；Worker 在回合末判断「是否确实需要续步」，原子写入结构化 JSON；hook 只查 STOP/过期/loop-guard、原子消费 marker、唤醒一次。
4. **历史只追加的对象限定**：PAOS Ledger / receipt / `events.jsonl` → 追加；`state.json` → 允许原子覆盖；`marker` → 一次性消费；`STOP` → 运行控制信号。
5. **删除 WorkBuddy 全部内容**。
6. **信封不复用 T-CW-01 状态 schema**（原 133–147 行意见）。
7. **Request 边界修正**：Worker 被禁止的是「给自己派 coordination 任务 / 冒领他人 coordination 任务 / 直接唤醒他人」；普通 Request（information/artifact/clarification…）不在禁止之列，按其既有协议处理。
8. **冻结五项决策**（见 §8）。

---

## 1. 信息汇总（已确认事实）

### 1.1 Runtime hook 真值（修正后口径）

| 能力 | 证据 | 结论 |
|---|---|---|
| DS-H 原生 idle-hook → `agent.followup()` 同一 Session 单次续步 | `23` + 外部运行时 `/home/remo/work/deepseek-harness/examples/dsh-turn-hook` | **单次续步 L4 已证** |
| Codex `Stop` hook → `decision:block` 同一 Thread 单次续步 | `25/26` | **单次续步 L4 已证** |
| Codex `Stop` hook **连续多步接棒**（纯机制） | `30` §7 | **纯机制 L4 已证** |
| Worker 基于 PAOS 剩余工作重发 marker（业务真闭环） | `32` §7 | **L4 已证（2026-08-25）** |
| `stop_hook_active` 语义 | 官方：表示当前 turn 是否已被 Stop 续过；**未说 true 后拒绝下一次 block** | 循环观测信号，**不是硬停止条件** |

修正上一轮的重要表述：**“Codex 只能靠 Stop hook 续一次”目前没有被证明**。

### 1.2 PAOS 已有能力（复用，不重造）

- Project / Session / Work / Request 生命周期：Open → Ack → Update → Close、Review/Cancel。
- **Coordinator v0**：人类授权、同 Project 互斥、`granted_cycle` 绑定；创建 Work + 定向 Request。
- **Office 投影**：`office?session_id=<sid>` 只返回指向该 Session 的 open Request。
- **原子领取**：`switch_work + coordination_request_id` 在一次 `mutate_v2` 中 resolve Request；`resolved_request_id / Ack / Update / Close` 全进 Ledger。
- 可靠性内核：`mutate_v2`（revision 乐观锁、幂等、Ledger、receipt、备份、原子写）。
- 访问事实：读 PowerShell `Invoke-RestMethod`；含中文写回 Windows 原生 Python `urllib` UTF-8；WSL 不直连 `127.0.0.1:8766`。

### 1.3 硬约束（不变）

1. 不 CLI 唤醒任何 GUI；保留人在回路。
2. 未经授权：不创建 Automation/Hook/Schedule/计划任务、不写真实 PAOS 对象。
3. 真实 `private-data/` 只读；PAOS 历史证据只追加不重写。
4. 未达证据等级不宣称。

---

## 2. 设计原则

1. **PAOS 是唯一事实源与唯一中转站**：Agent 之间不直接通信、不直接唤醒；任务/状态/证据只经 PAOS。
2. **Worker 不自派、不自协调、不直接唤醒**：
   - 禁止：给自己建 coordination Request；冒领他人 Request；直接唤醒其它 Worker。
   - 允许：领取指向自己的 Request；按既有协议发起**普通 Request**（information/artifact/clarification 等）。
3. **进入靠人，维持靠 hook，连续靠“Worker 判断 + 有界 hook”**：
   - v0 承诺：人进入 → Worker 完成第一步 → 至多补一次续步 → 停。
   - 后续目标：Worker 按「是否还有已确定工作」主动决定是否重发下一枚一次性 marker；hook 只执行续步。→ 必须通过 §5 连续实验。
4. **hook 只执行“是否继续”的动作，不做业务判断**：Worker 负责写 marker 的 `reason`；hook 不直连 PAOS、不改状态。
5. **每步有退出边界**：空任务 / done / STOP / 过期 / max_steps 即停。

---

## 3. 目标与非目标（v0）

### 目标

- 人确认进入后，Worker 在**同一原生 Session/Thread** 完成“第一步”，若确有必要，hook 补**一次**续步，然后可靠停止。
- 多 Worker 在同一 Project 内**互不误领**：每人只认领 `target_session_id == 自己` 的 Request。

### 非目标（v0）

- **持续自治**（待 §5 连续实验）。
- 无人值守冷启动（schedule/heartbeat 是后续可选）。
- 全自动交接（v0 只做“PAOS 中转交接”，下一个 Worker 仍由人进入）。
- Worker 之间直接调用 / 自我派发。

---

## 4. 功能实现方案（v0）

### 4.1 总架构

```text
                    人 / 操作方（确认进入 + 随时叫停 + 最终 Review）
                             │ 授权 Coordinator（按 Run 临时）
        ┌────────────────────▼─────────────────────────────┐
        │            PAOS：唯一业务/协调事实源               │
        │ Coordinator 建 Work + 定向 Request                │
        │ office?session_id= 投影；switch_work 原子领取      │
        └──────────┬──────────────────────────┬─────────────┘
              DS-H Worker                 Codex Worker
        （idle-hook 单次续步）        （Stop-hook 单次续步；连续待测）
                   │                          │
          本地信封 v2：run.json / STOP / marker.json / events.jsonl
```

### 4.2 参与者与职责（v0）

| 角色 | 谁 | 职责 | 禁止 |
|---|---|---|---|
| 操作方/人 | 用户 | 确认进入、叫停、Review、按 Run 授权 Coordinator | — |
| Coordinator | 专用 Session（**角色固定**），**权限仅按本次 Collaboration Run 临时授予**，Run 结束撤销 | 建 Work、建定向 Request | 替人 Review/Cancel；直接唤醒 Worker；永久后台权力 |
| Worker | DS-H / Codex 的某原生 Session | 首次 Ack 写映射（active）→ 读 office → `switch_work` 领取 + **Ack 新周期** → 干事 → Update/Close → 必要时写一次性 marker | 给自己派 coordination 任务；冒领他人；直接唤醒他人 |
| 本地信封 v2 | 每 Run 一个本地目录 | STOP / 过期 / 步数 / marker（纯执行控制） | 判定业务结论 |

### 4.3 v0 状态机

```text
idle
  └─(人确认 + 按 Run 临时授权 Coordinator)→ preparing：Coordinator 建 Work/Request、写信封
  └─(人对 Worker 说「进入」)→ worker_first_step：
        Worker 读信封/office → switch_work 领取 → Ack → 做第一步 → Update
  └─(Worker 判断是否确需续步)
        ├─ 不需要 / STOP / 过期 / 到步数 → stop：
        │     Worker Close；hook 放行；Run 结束撤销 Coordinator；人 Review
        └─ 确需 → Worker 写一次性 marker（结构化）→ hook 补一次续步 →
              worker_second_step → （如再需，重发新 marker；否则停）
```

### 4.4 中转协议

1. Coordinator（专用 Session、按 Run 临时授权）：
   - `POST /api/projects/<pid>/coordinator/work-items`
   - `POST /api/projects/<pid>/coordinator/requests`
2. Worker（进入时先首次 `acknowledge` 使 Session active，并写 `runtime_session.session_id / source_path`）：
   - `GET .../office?session_id=<自己>`（只认领自己的）
   - `POST .../switch-work`（带 `coordination_request_id`）→ Request 原子 `resolved`，Session 进入**新周期 `pending_ack`**
   - `POST .../acknowledge`（Ack 这个**新周期**）→ 开始工作
   - `POST .../updates` / `close`
3. 交接 = **PAOS 中转交接**：A 只 Update/Close；Coordinator 读 A 的 receipt/artifact 后建指向 B 的 Request；**人进入 B**。B 不由 A、也不由 hook 唤醒。

### 4.5 本地信封 v2（最小、不复用 T-CW-01 state schema）

```text
<run-root>/
  run.json      # {run_id, session_id, request_id, expires_at, created_at}
  STOP          # 运行控制信号（存在 = 停）
  marker.json   # 一次性、结构化；由 Worker 原子写入，hook 原子消费
  events.jsonl  # 追加审计（wake/continue/stop/claim/error）
```

`marker.json` 结构（Worker 在回合末、确有后续步骤时才写）：

```json
{
  "run_id": "run-...",
  "request_id": "3002-r...",
  "session_id": "3002-s...",
  "step_no": 1,
  "expires_at": "RFC3339",
  "reason": "还有一个已确定的后续步骤：……"
}
```

hook 逻辑（唯一职责）：

1. 检查 `STOP` / 过期 / max_steps（硬停止）；
2. 记录 loop-guard（`stop_hook_active`，仅观测）；
3. 原子消费 `marker.json`；
4. 唤醒**一次**同一会话。

业务上的「为什么继续」写进 marker 的 `reason`，由 **Worker** 决定；hook 不理解业务。

### 4.6 Runtime hook 适配器（v0）

- **DS-H**：原生 idle-hook（外部运行时 `/home/remo/work/deepseek-harness/examples/dsh-turn-hook`）——单次续步与「基于 PAOS 剩余工作重发 marker 的业务真闭环」均已 L4 验证（`32 §8`）。
- **Codex**：`Stop` hook `decision:block`——单次已证；**连续接棒 L4 已证**（`30` §7，注意 stdout JSON + `exit 0`）。
- ~~WorkBuddy~~（本版删除）。

### 4.7 停止与防失控

- 硬停止 = `STOP` + `expires_at` + `max_steps` + marker 消费。
- `stop_hook_active` 只作为**循环观测信号**记录，不作为「true 即停」的硬条件。
- `max_steps` 定义：**只统计自动 continuation 次数，不含人类最初启动的回合**。`max_steps=3` = 初始人工回合 + 最多 3 次自动续步。
- 默认：有界 Run 用 `max_steps + expires_at + STOP` 做硬停；v0.2 真闭环采用 `3 次 / 30 分钟 / 单 Request`（实验口径，跑完再调；`max_steps=1` 不采用）。
- 每步 prompt 强制退出条件；空 office 静默退。
- 临时 hook / 信封随 Run 结束清理；不落全局常驻。

### 4.8 PAOS 侧改动（倾向零核心变更）

- 业务与协调状态一律留在 PAOS（Request/Session/Work）。
- 本地信封是机器相关的临时控制文件，**默认不登记为 Artifact**；失败或重要 Run 可登记一份**结果摘要**。
- 不新增 Runtime 调度框架。

---

## 5. Gating 实验：Codex 连续续步（先纯机制，后接 PAOS）

> 目的：验证「一次人工进入 → 多次自动续步 → 自动停」是否成立。通过前不进入双 Worker 与自动交接。

### 5.1 第一轮（纯机制，不接 PAOS）

1. 人类只发一条启动消息。
2. 临时 `Stop` hook 最多允许连续续步 **3 次**。
3. **不以** `stop_hook_active==true` 作为停止条件，只记录它。
4. 每步记录：同一个 **Codex Task ID**、`turn_id`、`stop_hook_active`、当前步数、时间。
5. 第 3 次后必须自动放行，不得出现第 4 次。
6. 同时设：`STOP` 文件、10 分钟过期、`max_steps=3`；**状态先原子扣减，再返回 `decision:block`**。
7. 实验完成立即删除临时 hook、marker、日志。

通过标准：

```text
一次人工输入
→ 初始回复
→ 自动续步 1
→ 自动续步 2
→ 自动续步 3
→ 自动停止
```

且全过程在**同一个可见 Codex Task**，中间没有任何人工「继续」。

### 5.2 第二轮（接 PAOS 真闭环）— **已执行并 PASS（`32 §7`）**

> 结果：同 Codex Task `019fa820…`；`r006` 单次 `resolved/target_session_accepted`；Ledger `Ack→switch→Ack→Update A→Update B→Close→Coordinator撤销`；`s019 completed`、`w022 review`。运行逻辑如下：

```text
人类启动 Codex Worker 一次
→ 读取 PAOS Request → 完成步骤 A → 主动留下 marker（原因明确）
→ Stop hook 自动继续 → 完成步骤 B → 如仍有明确工作，重发新 marker，否则不写
→ ... → Update/Close → 不再留 marker → 自动停止
```

重点验证 **Agent 会按剩余任务主动决定**：
- 还有明确工作 → 重新签发下一枚一次性 marker；
- PAOS 已无任务 / Work 完成 / STOP 存在 → 不写 marker。

即：**每枚 marker 一次即废，但有界 Run 内由 Agent 按实际工作重发下一枚**。连续性来自 Agent 判断，hook 只执行续步。

### 5.3 判定（已回填：PASS，2026-08-25）

- ✅ 纯机制第一轮已 PASS，证据与根因见 `30` §7：同 Task、同 `turn_id`、`stop_hook_active: false→true→true→true`、`step=4/max_steps=3` 且第 4 次只放行。
- 结论：`Stop` hook **连续续步成立** → 可成为「人进入一次、Agent 持续完成一个有界任务」的主链。
- 修复同步：block 必须用 **stdout JSON + `exit 0`**（不能用 `exit 2`，Desktop 判为 hook 错误）；已回写 `stop_hook.ps1` 与 `30` §2。
- 官方建议这类编排明确设置次数、重试与停止边界 → 生产默认：`max_steps`、`expires_at`、`STOP` 三重硬停。

---

## 6. 阶段计划（修订）

- **Gating（完成）**：`30 §7` Codex 连续续步纯机制 **PASS**。
- **期 1（完成）**：单 Worker 同 Session/Thread 自动续步闭环——Codex `32 §7`、DS-H `32 §8`。
- **期 2（完成）**：两 Worker 分别完成同版本真闭环（不要求互醒）。
- **期 3（后置）**：PAOS **中转交接**；人进入下一个 Worker。
- **期 4（后置）**：仅当真实使用证明“人工再次进入”是主要摩擦，才引入 schedule/Heartbeat。

清账（已执行，`revision=182`）：`s016/s017→abandoned`；`r001/r004/r005→cancelled`；停靠桩 `w012/w014/w016~w019/w021/w023→cancelled`；`s018/w020` 保留为可复用的专用 Coordinator + 停靠 Work。

---

## 7. 验收标准

1. Worker 只领取指向自己的 Request；两条 Request 互不误领。
2. 每条 Request 恰好 `resolved / target_session_accepted` 一次；Ledger 四段链完整。
3. 单次续步：同一 Session/Thread，且 STOP/过期/步数后可靠停。
4. 连续续步：**L4 已证**（`30` §7）；有界 Run 用 `max_steps + expires_at + STOP` 三重硬停。
5. Agent 间无直接调用/唤醒证据；交接只发生在 PAOS。
6. 临时 hook/信封/日志可清理；PAOS 历史只追加；中文写回无乱码。

---

## 8. 风险与已冻结决策

### 冻结五项（按评审建议直接采用）

| 事项 | 冻结结论 |
|---|---|
| Coordinator | 每 Project 用**专用 Coordinator Session**；授权**按 Collaboration Run 临时授予**，Run 结束即撤销 |
| 信封是否登记 Artifact | 默认**不登记**；失败/重要 Run 只登记一份结果摘要 |
| 进入粒度 | v0 = **一个 Worker + 一个 Project + 一个 Request + 一个 Run** |
| hook 续步上限 | **v0.2 实验口径**：`max_steps=3` 次**自动续步**（不含初始人工回合）+ `TTL 30 分钟` + 单 Request；正式生产值跑完一个真实闭环后再调。DS-H 与 Codex 同一口径 |
| Worker 能力 | 只做 human-in-the-loop 领取链；不伪装自动 |

### 风险

- hook 无界续命：由 `STOP + expires_at + max_steps + marker` 兜底，不看 `stop_hook_active` 当硬停。
- marker 空文件：已改为结构化 JSON；消费后即失效。
- 信封替代业务事实：已明确 PAOS 是唯一事实源，信封只做控制。
- 连续实验**已通过**：Codex hook 进主链；若未来出现回归，才回退 Heartbeat（§5.3 的失败分支保留为预案）。