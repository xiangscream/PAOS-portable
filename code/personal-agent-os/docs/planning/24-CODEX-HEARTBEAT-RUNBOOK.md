# Codex Heartbeat 同 Thread 最小实测 Runbook（24）

> 状态：PAOS 跑道已就绪；**等待用户在 Codex Desktop（Windows）里显式开始**。
> 上游：`21` §3.3、`22` §2.2、`23`（DS-H 侧已 L4 通过）。
> 性质：执行手册。未达 L4 不写“已验证同 Thread 自动唤醒”。

---

## 0. 当前证据等级（诚实口径，先读）

已复核到的本地证据（来自 `~/.codex` 与会话 JSONL 里的真实 tool declaration）：

- Codex Desktop `26.818.3698.0` 暴露 `codex_app__automation_update`：create / update / view / delete 四类 action。
- 支持 `kind: "heartbeat"` + `targetThreadId`（绑定当前本地线程）；`status: ACTIVE / PAUSED`。
- RRULE 允许分钟级（协议示例 `FREQ=MINUTELY;INTERVAL=30`），**无 WorkBuddy 式 60 分钟硬下限**。
- 协议明确：“Heartbeat automations are proactive follow-ups attached to the current local thread and are the default for recurring requests.”
- 现有 `~/.codex/automations/automation/automation.toml` 是 **weekly cron + projectless**（周五 16:00 每周回顾），**不是** thread heartbeat，不能当同 Thread 领取链证据。

仍待实测（四项）：实际最小间隔、后台唤醒延迟、同一可见 GUI Thread、`mode="delete"` 是否真自删。

---

## 1. 已建 PAOS 跑道（Project 3002，2026-08-24）

| 对象 | ID | 说明 |
|---|---|---|
| 被测 Session | `3002-s015` | `runtime_id=codex`、`identity=implementer`、`agent_label=Codex-Heartbeat-TCW`；当前 `pending_ack`（**故意留给 Codex 自己 Ack**，以回填真 thread id） |
| 停靠 Work | `3002-w014` | 当前 Work（Open 时挂靠） |
| 领取目标 Work | `3002-w015` | `todo`；被 Request 指向 |
| 定向 Request | `3002-r003` | `open`；`target_session=3002-s015`、`target_work=3002-w015`（由协调 Session `3002-s013` 创建，随后已撤销授权） |

- 创建后基线 revision = `127`。
- `3002-s015.runtime_session` 暂为空；**由 Codex 在 Acknowledge 时写回**它自己的原生 thread id 与 rollout JSONL 路径。

---

## 2. 在 Codex Desktop 内执行（请先把本文件给到那个 Codex 会话）

### Step 0 — 取自己（Codex）的原生 Thread ID 与日志路径

- 确认你现在就在目标 Codex Desktop Thread；数据来源可选：当前 rollout JSONL 路径（形如 `C:\Users\remo\.codex\sessions\…\rollout-<date>-<threadId>.jsonl`）或 Codex 应用暴露的当前 thread id。
- 记录两项：`native_thread_id`、`rollout_path`。

### Step 1 — Acknowledge PAOS Session（写回 native 映射）

1. 读当前 revision：`GET http://127.0.0.1:8766/api/projects/3002`（只读可用 PowerShell `Invoke-RestMethod`）。
2. POST：

```text
POST http://127.0.0.1:8766/api/projects/3002/sessions/3002-s015/acknowledge
```

```json
{
  "schema": "paos-session-ack/v1",
  "operation_id": "op-codex-heartbeat-ack-<唯一ID>",
  "base_revision": <读到的最新 revision>,
  "session_id": "3002-s015",
  "runtime_session": {
    "environment": "codex-desktop",
    "title": "Codex Heartbeat TCW",
    "session_id": "<native_thread_id>",
    "source_path": "<rollout_path>"
  },
  "understood_objective": "在保持原 Codex Thread 不变的前提下，用 Thread-bound Heartbeat 自动醒来并领取一次指向本 Session 的 open Request。",
  "understood_boundaries": ["同一 Request 只领取一次", "未达 L4 不宣称成功", "完成后 automation_update(mode=delete)"],
  "proposed_first_steps": ["Acknowledge 并回写 native 映射", "创建 Thread-bound Heartbeat", "等待醒来领取一次"],
  "detected_risks": ["最小间隔与后台唤醒延迟未实测", "若醒来不是同一 Thread 则记 unverified"]
}
```

含中文写回必须走 **Windows 原生 Python `urllib`**（`ensure_ascii=False`、UTF-8 字节、`Content-Type: application/json; charset=utf-8`），不要用 PowerShell 5.1 发中文。

### Step 2 — 创建同 Thread Heartbeat

用当前 Codex 会话可见的 `codex_app__automation_update` 工具（**让工具自己生成 RRULE，不要手写 automation 指令**）：

- `kind: "heartbeat"`
- `targetThreadId`: 当前 Thread 的 ID
- 节奏建议：`FREQ=MINUTELY;INTERVAL=15`（或与用户确认后取 `INTERVAL=5`）
- `prompt`: 使用下方 §3 全文
- 创建后记录：automation id、创建时间、RRULE、targetThreadId

### Step 3 — 等待自动醒来，观察

- 不发新人类消息；观察是否仍在**同一个可见 GUI Thread** 醒来。

### Step 4 — 醒来后执行领取链（§3 的 prompt 会展开这一步）

预期链路：`office 读到 r003` → `switch_work(3002-w015, coordination_request_id=3002-r003)` → `Acknowledge` → 极小 `Update` → `Close`。

### Step 5 — 完成后自删 Heartbeat

- 调用 `codex_app__automation_update`（`mode="delete"`），删除本 Heartbeat 并记录删除时间。

---

## 3. Heartbeat prompt 全文（写进 automation 的 prompt）

```text
[Codex Heartbeat 同 Thread 自动领取最小实测]
先判停止件：若已见 Work done / STOP / 截止时间 → 只做 automation_update(mode=delete) 并说明原因，不领取。
正常流程（只执行一次）：
1) 确认当前仍在这个 Codex Thread（Thread ID 未变、GUI 可见、无新 standalone 任务）。
2) GET http://127.0.0.1:8766/api/projects/3002/office?session_id=3002-s015
3) pending_requests 为空 → 静默结束本轮。
4) 存在 open 的 3002-r003：POST
   http://127.0.0.1:8766/api/projects/3002/sessions/3002-s015/switch-work
   body: schema=paos-session-switch-work/v1, target 用 work_item_id=3002-w015,
   coordination_request_id=3002-r003（只此一次）。
5) 成功后 Acknowledge → 做一次极小 Update → Close。
6) 完成后 automation_update(mode=delete) 删除本 Heartbeat 并记录删除时间。
纪律：含中文写回走 Windows 原生 Python urllib UTF-8；同一 Request 只领取一次。
```

---

## 4. 停止 / 回滚

- 主停止件 = `automation_update(mode="delete")`（并记录是否真的自删）。
- 失败兜底：在 Codex 里手动删除该 automation；`3002-r003` 未领取可留 open 或由人类取消。
- 不重写任何 Ledger/receipt；`3002-w014/w015` 留作真实历史。

---

## 5. L4 验收（限定 Codex 同 Thread）

- [ ] 同一 Thread 醒来（Thread ID 未变、GUI 可见、无新 standalone 任务）
- [ ] 未由普通人类消息触发（触发源是 Heartbeat）
- [ ] `3002-r003` `resolved / target_session_accepted`，且只领取一次
- [ ] PAOS Ledger：`session.work.switched → session.acknowledged → session.update.applied → session.closed`
- [ ] `automation_update(mode=delete)` 自删生效并被记录
- 未达 L4 一律写 `unverified`。

---

## 6. 实测结果（2026-08-24，Codex 侧 L4 达成 ✅）

（由用户回报 + DS-H 侧独立复核 PAOS 与本地配置）

| 验收项 | 证据 |
|---|---|
| 同一 Thread 醒来 | ✅ 原生 Thread `019fa820-4cd7-77c2-9e0d-50600edc2300`（`3002-s015.runtime_session.session_id` 已回填该值） |
| 未由普通人类消息触发 | ✅ 触发源是 Thread-bound Heartbeat |
| Request 只领取一次 | ✅ `3002-r003` `resolved / target_session_accepted` |
| Ledger 完整 | ✅ `session.acknowledged(rev128) → session.work.switched(129) → session.acknowledged(130) → session.update.applied(131) → session.closed(132)` |
| Heartbeat 自删 | ✅ `mode=delete` 生效；`~/.codex/automations/automation/automation.toml` 只剩下原每周 `cron`，无残留 heartbeat |
| 最小间隔 | ⚠️ 计划 15 分钟，实际约 14 分 31 秒唤醒；**更短最小间隔仍未测** |

PAOS 最终：`revision=132`、`3002-s015 status=completed`、`current_work_item_id=3002-w015`、`3002-w015 status=review`。

结论：**Codex Desktop Thread-bound Heartbeat 同 Thread 自动唤醒 + 定向领取链达到 L4**（更短最小间隔另行实测）。