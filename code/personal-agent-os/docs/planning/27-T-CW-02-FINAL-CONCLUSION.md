# T-CW-02 / 多 Agent 自动化协作 — 最终结论与架构定稿（27，v2）

> 状态：**定稿**。取代 v1；T-CW-02 收口。
> 日期：2026-08-25。
> 一句话：**以 PAOS 为唯一中转站；人进入一次 + 专用 Coordinator 派发 + Worker 按剩余工作写 marker + 原生 hook 续步，三重硬停；已在 DS-H 与 Codex 双 Runtime 实测 L4。**

---

## 0. 文档定位

本文件把 `17~26` 的调查、`29/30/31` 的设计与审查、`32` 的真闭环实测，压缩成一份可交接的最终结论。**F/G 业务真闭环有 PAOS Ledger/receipt；A–E 的 Runtime 能力分别由原生会话日志、hook 事件与对应实验文档支撑。** 所有「待做」都明确标注，不假装完成。

---

## 1. 一句话结论（最终口径）

T-CW-02 目标已达成：**「已存在的原生 Agent Session/Thread 在没有普通人类消息时，由原生 hook 在同一 Session/Thread 内自动续步，完成一个有界任务，到点自动停止，权限随 Run 授予与撤销。」** 连续性来自 **Agent 对 PAOS 剩余工作的判断**，hook 只执行续步。

---

## 2. 证据总表

| # | 能力 | 证据 | 等级 |
|---|---|---|---|
| A | DS-H `schedule` 同 Session 自动领取 | `23` | L4 ✅ |
| B | DS-H 原生 idle-hook `followup()` 造回合 | `32 §8` + DS-H 原生会话日志（示例在外部运行时：`/home/remo/work/deepseek-harness/examples/dsh-turn-hook`） | L4 ✅ |
| C | Codex `Heartbeat` 同 Thread 自动领取 + 自删 | `24` | L4 ✅ |
| D | Codex `Stop` hook 单次续步（同 Thread） | `25/26` | L4 ✅ |
| E | Codex `Stop` hook 连续续步（纯机制） | `30 §7` | 纯机制 L4 ✅ |
| F | Codex Worker 按 PAOS 剩余工作重发 marker（业务真闭环） | `32 §7` | L4 ✅ |
| G | DS-H Worker 按 PAOS 剩余工作重发 marker（业务真闭环，idle-hook） | `32 §8` | L4 ✅ |
| H | verify 基线 | `17/27` | 360/360 ✅ |

两条真闭环都验证：同一 Task/Session、无人工「继续」、Request 单次领取、marker 由 Worker 重发、≤3 次自动续步、PAOS 与本地 `events.jsonl` 对账、结束无残留。

---

## 3. 架构定稿

### 3.1 参与角色

| 角色 | 谁 | 职责 | 禁止 |
|---|---|---|---|
| 操作方/人 | 用户 | 确认进入、叫停、Review、按 Run 授权 | — |
| 专用 Coordinator | 每 Run 新建/复用的**专用 Session**（本次 `3002-s018`，identity `integrator`） | 建 Work + 定向 Request | 替人 Review；直接唤醒 Worker；永久权限 |
| Worker | DS-H / Codex 原生 Session | 首次 Ack 写映射 → 读 office → `switch_work` 领取 → Ack 新周期 → 干事 → 判断续步 → Update/Close | 自派 coordination；冒领他人；直接唤醒他人 |
| 本地信封 | 每 Run 一个本地目录 | 执行控制：STOP/过期/步数/marker | 判定业务结论 |

> 职责与证据边界：Coordinator「创建 Work + 定向 Request」是既定职责；**本轮 F/G 真闭环只真实验证了「Coordinator 创建定向 Request」，「Work 由人预建（`created_by=human`）」**。Coordinator 创建 Work 的能力由测试覆盖，不并入 F/G 的 L4 证据。

### 3.2 执行链（已实测，正确的 Claim/Ack 顺序）

```text
人确认进入 + 按 Run 授权专用 Coordinator
→ Coordinator 建 Work + 定向 Request
→ 人进入 Worker 原生会话
→ Worker 首次 Ack（active + 写 runtime_session 映射）
→ 读 office?session_id=自己
→ switch_work + coordination_request_id
     （Request 原子 resolved；Session 进入新周期 pending_ack）
→ Ack 新周期
→ 完成步骤 → Update
→ Worker 判断剩余工作：
     有 → 写一次性 marker（reason/step_no/expires_at）
     无 / done / STOP / 过期 / max_steps → 不写，Close
→ hook：查 STOP/过期/上限 → 原子消费 marker → 唤醒一次同一会话
→ 循环直到 Update/Close 自动停
→ Run 结束撤销 Coordinator → 人 Review
```

**协议要点（踩坑后写死）：**
- `switch_work` 会创建新周期，必须在其后重新 `Acknowledge`。
- `close` body **不能**手写 `work_updates.status`；状态由 `result=completed` 自动投影（`review`），否则 422。
- 含中文写回走 Windows 原生 Python `urllib` UTF-8。
- block 决策：**stdout JSON + `exit 0`**（`exit 2` 会被判为 hook 错误）。

### 3.3 本地信封 v2

```text
<run-root>/
  run.json      # {run_id, session_id, request_id, created_at, expires_at}
  STOP          # 存在即停
  marker.json   # Worker 原子写、hook 原子消费；{run_id, request_id, session_id, step_no, expires_at, reason}
  events.jsonl  # 追加审计
```

### 3.4 双 Runtime 的 hook 适配

| Worker | 续步机制 |
|---|---|
| DS-H | 原生 idle-hook：`agent/status==idle` → 读 marker → `agent.followup()`（示例位于外部运行时 `/home/remo/work/deepseek-harness/examples/dsh-turn-hook`） |
| Codex | `Stop` hook：读 marker → `{"decision":"block","reason":"..."}` + `exit 0` |

### 3.5 硬停（防失控）

- 硬停 = `STOP` + `expires_at`（30 分钟 v0.2 口径）+ `max_steps`（3 次自动续步，**不含人类初始回合**）+ marker 消费。
- `stop_hook_active` 是**观测信号**，不是硬停条件。
- marker 一次即废；有界 Run 内由 Agent 按剩余工作重发下一枚。

---

## 4. 已冻结决策（评审通过）

1. PAOS 唯一事实源；本地信封只是执行控制。
2. Worker 不自派、不自协调、不直接唤醒；普通 Request 不被禁止。
3. 专用 Coordinator Session（按 Run 临时授予、结束撤销）；不与 Worker 混用。
4. v0.2 进入粒度 = 1 Worker + 1 Project + 1 Request + 1 Run。
5. v0.2 hook 口径 = `max_steps=3` 自动续步 / `expires_at=30min` / 单 Request；正式生产值跑完再调（`max_steps=1` 不用）。
6. 信封默认不登记 Artifact；失败/重要 Run 只留结果摘要。
7. 旧自协调跑道 `s016/s017/r004/r005` 废弃：`s016/s017` 已 `abandoned`；`r004/r005`（含 `r001`）已通过现有 `request_updates` 置 `cancelled`。

---

## 5. 两条真闭环实测记录

### Codex（`32 §7`）

- Task `019fa820-…`；`s019 completed`；`r006 resolved/target_session_accepted`；`w022 review`
- 目标 Work `w022` 由**人**预建（`created_by=human`）；`r006` 在 revision 152 由 Coordinator 创建。
- **Worker 自动执行段**（revision 154→161，不含 Work/Session/Request 建立）：`grant(154) → ack(155) → switch(156) → ack(157) → update A(158) → update B(159) → close C(160) → revoke(161)`

### DS-H（`32 §8`）

- Session `session-46af…`；`s020 completed`；`r007 resolved/target_session_accepted`；`w024 review`
- 目标 Work `w024` 由**人**预建（`created_by=human`，revision 162/163）。
- 执行段含 Open/grant/Request/领取/关闭：`opened(164) → grant(165) → request.created(166) → ack(167) → switch(168) → ack(169) → update A(170) → update B(171) → close C(172) → revoke(173)`

---

## 6. PAOS 现状与遗留清单（Project 3002，`revision=182`）

**已闭合（本轮已清账，非删除、非 Restore）：**
- `r006/r007` → `resolved / target_session_accepted`
- `r001/r004/r005` → **`cancelled`**（经 source Session `3002-s013` 的 `request_updates`，理由注明）
- 停靠桩 `w012/w014/w016~w019/w021/w023` → **`cancelled`**
- `s016/s017` → `abandoned`；`s019/s020` → `completed`
- `s018` Coordinator capability 已撤销，但 **Session 保持 `active`、`w020` 保持占用**（作为以后复用的专用 Coordinator + 停靠 Work）

**待人类 Review 归档（不代劳）：**
- `w013/w015/w022/w024`（均 `review`）

**备注（非 backlog）：**
- Request 取消**不需要新后端端点**：现有 `request_updates` 已支持 `status=cancelled`。唯一缺口是“项目页人工取消入口”的 UI 摩擦，留作日后有需要时补按钮，不立项。
- `stop_hook_active` 已在 `30 §7` 观测到 `false→true→true→true`；`32` 业务真闭环那次 Desktop 未传 stdin，仅在该文件作观测说明，**不再列入 backlog**。

---

## 7. 状态与后置（期计划）

- **已验证**：期 1（单 Worker 闭环）、期 2（两 Worker 分别完成同版本真闭环）。
- **后置**：
  - 期 3：PAOS **中转交接**（A Close → Coordinator 建 B 的 Request → 人进入 B），人仍负责进入下一个 Worker。
  - 严格“双 Worker 同一时刻并发、互不误领”未做并发压测（现有 F/G 已证明各自只领自己的 Request）。
  - WorkBuddy 维持 manual/self，不自动化。
  - Codex 更短 Heartbeat 最小间隔（可选）。

---

## 8. 建议下一步（按优先级）

1. 人类 Review 归档 `w013/w015/w022/w024`（停靠桩与旧请求已清账，无需再动）。
2. 需要自动化交接时再跑期 3；需要无人值守时再评估 schedule/heartbeat。
3. 不做新 `request-cancel` 端点；如日后人工取消摩擦明显，再补「项目页 Cancel 按钮」（纯 UI）。
4. 文档 `27/29/30/31/32` 建议做一次**独立 docs commit**；是否 push 由用户定。