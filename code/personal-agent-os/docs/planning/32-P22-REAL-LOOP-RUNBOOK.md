# P2.2 真闭环执行卡（32）

> 状态：**已完成（PASS，见 §7/§8）**。§1–§6 是执行前快照（`revision=154`）；真闭环结果见 §7（Codex）与 §8（DS-H）。
> 这是 `29 §5.2` 的真闭环首跑：验证「连续性来自 Agent 按 PAOS 剩余工作重发 marker」。

---

## 1. 本轮 PAOS 对象（执行前快照，`revision=154`；Project 3002）

| 对象 | ID | 说明 |
|---|---|---|
| 专用 Coordinator Session | `3002-s018` | `identity=integrator`，`agent_label=P2.2-Coordinator-TCW`；**当前保持 Coordinator 授权**，Worker Close 后再撤销 |
| Coordinator 停靠 Work | `3002-w020` | 仅作 Coordinator 挂靠 |
| Codex Worker Session | `3002-s019` | `identity=implementer`，`agent_label=P2.2-Codex-Worker`；`pending_ack`，**由 Codex 首次 Ack 回写 native 映射** |
| Worker 停靠 Work | `3002-w021` | 仅作 Open 挂靠 |
| 目标 Work | `3002-w022` | 真闭环最小工作 A/B/C，`todo` |
| 定向 Request | `3002-r006` | `open` → `target=3002-s019 + 3002-w022`（由**专用 Coordinator `3002-s018`** 创建） |

---

## 2. Codex Worker 执行步骤（人类只进入一次）

### Step 0 — 人类进入

在 Codex Desktop 当前 Thread 只说一句：

```text
进入 P2.2 真闭环，按 docs/planning/32-P22-REAL-LOOP-RUNBOOK.md 执行。
```

### Step 1 — 首次 Ack（写映射，进入 active）

Codex 读当前 revision（`GET /api/projects/3002`），POST：

```text
POST http://127.0.0.1:8766/api/projects/3002/sessions/3002-s019/acknowledge
```

```json
{
  "schema": "paos-session-ack/v1",
  "operation_id": "op-p22-codex-ack0-<唯一ID>",
  "base_revision": <读到的最新 revision>,
  "session_id": "3002-s019",
  "runtime_session": {
    "environment": "codex-desktop",
    "title": "P2.2 real loop Worker",
    "session_id": "<当前 Codex native Thread id>",
    "source_path": "<当前 rollout JSONL 路径>"
  },
  "understood_objective": "同一原生 Thread 内领取指向自己的 open Request，并按剩余工作决定是否重发一次性 marker。",
  "understood_boundaries": ["同一 Request 只领取一次", "每次 marker 必须基于明确剩余工作", "无剩余工作不写 marker"],
  "proposed_first_steps": ["office 读 Request", "switch_work 领取", "Ack 新周期"],
  "detected_risks": ["hook 续步最多 3 次（不含初始回合）"]
}
```

含中文写回走 Windows 原生 Python `urllib`（UTF-8，`ensure_ascii=False`）。

### Step 2 — 领取

```text
GET http://127.0.0.1:8766/api/projects/3002/office?session_id=3002-s019
→ 应出现 open 的 3002-r006
POST http://127.0.0.1:8766/api/projects/3002/sessions/3002-s019/switch-work
body: schema=paos-session-switch-work/v1, work_item_id=3002-w022, coordination_request_id=3002-r006（只此一次）
→ r006 原子 resolved，Session 进入新周期 pending_ack
POST .../sessions/3002-s019/acknowledge   # Ack 这个新周期
```

### Step 3 — 完成步骤并决定续步

- 完成**步骤 A** → `POST .../updates`（progress/note 记录 A 已完成）。
- 完成 A 后，判断是否有明确剩余工作（B/C）：
  - 有 → 写一次性 `marker.json`（见 §3）；
  - 无 / done / STOP → 不写，直接 Close。

### Step 4 — hook 续步（最多 3 次自动续步）

- 回合将停时，`Stop` hook 见 §4：消费 `marker.json` → 续一步。
- 每次续步后 Codex 重复 Step 3：完成 B → 写下一枚 marker（若还有 C）→ … → C 完成后**不再写 marker** → Close。

### Step 5 — Close

```text
POST .../sessions/3002-s019/close
result=completed, result_summary=<A/B/C 已完成 + 证据>
```

---

## 3. 本地信封 v2（`%TEMP%\codex-p22-run\`）

```text
run.json     # {"run_id":"run-p22-...", "session_id":"3002-s019", "request_id":"3002-r006", "created_at":"...", "expires_at":"<now+30min RFC3339>"}
STOP         # 存在即停（人/Coordinator 放）
marker.json  # Worker 决定续步时原子写入；hook 消费一次
events.jsonl # 追加：ack/switch/update/marker/continue/close
```

`marker.json`（结构化，一次即废）：

```json
{
  "run_id": "run-p22-...",
  "request_id": "3002-r006",
  "session_id": "3002-s019",
  "step_no": 1,
  "expires_at": "<run.expires_at>",
  "reason": "还有一个已确定的后续步骤：完成步骤 B"
}
```

续步纪律：`max_steps=3` **只统计自动 continuation，不含人类最初启动回合**；每个 marker 由 Worker 按「仍有明确工作」重发；无剩余工作不得写 marker。

---

## 4. Stop hook（真闭环版：消费 marker，不再自减步）

逻辑：

1. `STOP` 存在 / 超过 `run.json.expires_at` → 放行（`exit 0`）。
2. `marker.json` 不存在 → 放行。
3. `marker.json` 存在 → **原子删除 marker** → 记一行 `events.jsonl` → 输出 block：

```text
stdout: {"decision":"block","reason":"continue-one-step"}
exit 0     ← 注意：是 0，不是 2（exit 2 会被 Desktop 判为 hook 错误）
```

PowerShell 参考：

```powershell
$run = Join-Path $env:TEMP 'codex-p22-run'
$runJson = Join-Path $run 'run.json'
$marker  = Join-Path $run 'marker.json'
$events  = Join-Path $run 'events.jsonl'
if ((Test-Path (Join-Path $run 'STOP')) -or
    [DateTime]::UtcNow -gt [DateTime]::Parse((Get-Content $runJson -Raw | ConvertFrom-Json).expires_at)) { exit 0 }
if (-not (Test-Path $marker)) { exit 0 }
Remove-Item $marker -Force
Add-Content $events ("[{0}] continue" -f [DateTime]::UtcNow.ToString('o')) -Encoding utf8
'{"decision":"block","reason":"continue-one-step"}'
exit 0
```

临时 `hooks.json` 指向它；跑完删除 run 目录与临时 hooks，还原原配置。

---

## 5. 验收（逐条，全部通过才算真闭环 PASS）

1. 同一个 Codex Task；中间没有人工「继续」。
2. `3002-r006` 只领取一次：`resolved / target_session_accepted`。
3. 每次 marker 都由 Worker **基于明确剩余工作**重新签发。
4. 自动续步 ≤ 3 次（不含初始回合）。
5. PAOS `Update/Close` 与本地 `events.jsonl` 对得上。
6. Run 结束后：无 marker、无临时 hook、`3002-s018` Coordinator 已撤销。
7. 中文写回无乱码；历史只追加。

---

## 6. Codex 完成后我（DS-H）会做

1. 撤销 `3002-s018` Coordinator（Run 结束即撤销）。
2. 复核 PAOS：`r006` resolution、`s019` status、`w022` status、Ledger 链、revision。
3. 对照 `events.jsonl` 逐条验收。
4. 回填 `29 §5.2` 结论与 `31` 证据清单，宣告真闭环 PASS/FAIL。

---

## 7. 实测结果（已回填，2026-08-25：真闭环 PASS ✅）

- 同一 Codex Desktop Task：`019fa820-4cd7-77c2-9e0d-50600edc2300`
- Worker `3002-s019`、Work `3002-w022`、Request `3002-r006`

Codex **Worker 自动执行段**（revision 154→161；不含 Work/Session/Request 建立。`r006` 创建于 rev152；目标 Work `3002-w022` 由人预建）：

```text
coordinator.granted(154) → session.acknowledged(155)
→ session.work.switched(156) → session.acknowledged(157)
→ session.update.applied(158 = 步骤 A)
→ session.update.applied(159 = 步骤 B，续步后)
→ session.closed(160 = 步骤 C)
→ coordinator.revoked(161)
```

最终状态：

- `3002-r006` → `resolved / target_session_accepted`（只领取一次）
- `3002-s019` → `completed`；`current_work_item_id=3002-w022`
- `3002-w022` → `review`
- `3002-s018` → Coordinator 已撤销（`revokedAt=2026-08-25T03:55:33Z`）
- 临时 hooks.json / marker / 运行状态 / 辅助脚本已清理

两个观测记录（不影响结论）：

1. **Close 422 细节**：示例若在 `close` body 里直接带 `work_updates.status` 会被协议拒绝（422）；去掉该字段后成功——Close 的 Work 状态由 `result=completed` 自动投影为 `review`，不允许手写 `status`。
2. **`stop_hook_active` 本轮未观测**：Desktop 未把该字段传入 hook stdin；但 marker 消费与同 Thread 续步链路已实际验证。该字段的“观测值”已在 `30 §7` 记录为 `false→true→true→true`，不影响硬停，无需再补实验。

---

## 8. DS-H 侧同版本真闭环（已回填，2026-08-25：PASS ✅）

用**专用 Coordinator `3002-s018`** 建的 DS-H 跑道，由 DS-H 原生 idle-hook 跑同版本 A/B/C：

- Worker `3002-s020`（`deepseek harness`）、目标 Work `3002-w024`、Request `3002-r007`
- 目标 Work `3002-w023/w024` 由**人预建**（`created_by=human`，rev162/163）
- 续步机制：`dsh-turn-hook` 一次性 marker（`/tmp/dsh-turn-hook-marker.json`）→ `idle` 时 `agent.followup()` 续步

执行段（含 Open/grant/Request/领取/关闭，revision 164→173）：

```text
session.opened(164) → coordinator.granted(165) → coordinator.request.created(166)
→ session.acknowledged(167) → session.work.switched(168) → session.acknowledged(169)
→ session.update.applied(170 = 步骤 A)
→ session.update.applied(171 = 步骤 B)
→ session.closed(172 = 步骤 C)
→ coordinator.revoked(173)
```

最终：`r007` → `resolved/target_session_accepted`；`s020` → `completed`；`w024` → `review`；`s018` Coordinator 已撤销。

**结论：同一套「专用 Coordinator + PAOS 中转 + Worker 判断 marker + 原生 hook 续步」在 DS-H 与 Codex 两侧都跑通。**