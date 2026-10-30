# Codex Stop-hook 连续续步 Gating 实验（30）

> 状态：**已执行并 PASS（2026-08-25）**。纯机制实验（不接 PAOS）通过 → 结论见文末「实验结论」与 `29` §5.3。
> 性质：临时、可回滚、做完即清理；不落全局配置。

---

## 0. 通过标准（先写死）

```text
一次人工输入
→ 初始回复
→ 自动续步 1
→ 自动续步 2
→ 自动续步 3
→ 自动停止（不得出现第 4 次）
```

且全过程在**同一个可见 Codex Task**，中间没有任何人工「继续」。

---

## 1. 前置

1. Codex Desktop 打开一个目标 Thread，准备跑纯机制实验。
2. 备份/记录当前 hooks 配置（如 `~/.codex/hooks.json`：若存在则备份原文，若无则记住「原本没有」）；实验后还原。
3. 建一个本地 run 目录（示例 `%TEMP%\codex-cont-run\`），作为一次性执行状态。

---

## 2. 一次性 Stop hook 逻辑（硬上限 = 3）

hook 外部命令内部维护一个 `state.json`（`max_steps=3`、`step=0`、`expires_at=now+10min`）与一个只追加的 `events.txt`。

hook 每次被 `Stop` 触发时，顺序执行：

1. **硬停止检查**：`STOP` 文件存在，或 `now > expires_at` → 放行（不 block）。
2. **读 state 并原子扣减**：`step = step + 1`；
   - 若 `step > max_steps` → 放行（不再续）。
3. **记录**（只记录，不用作停止依据）：
   - 当前 `turn_id`、`stop_hook_active`（从 hook stdin payload 里取；取不到就写 `unknown`）、`step`、时间戳。
4. 若仍允许续步 → 输出 block 决策：
   - 按 Codex hook 协议写 stdout：`{"decision":"block","reason":"continue-one-step"}`，并 **`exit 0`**（当前协议：block 用 stdout JSON + 退出码 0；**不要 `exit 2`**，否则 Desktop 判为 hook 错误——本次实验已踩坑）。
   - **先扣减 step，再返回 block。**

关键约束：**不要把 `stop_hook_active==true` 当作停止条件**，它只是观测信号；真正的硬停是 `STOP + expires_at + max_steps`。

### 最小 PowerShell 参考实现（可让 Codex 按此适配）

```powershell
$run = "$env:TEMP\codex-cont-run"
$stateFile = Join-Path $run "state.json"
$events = Join-Path $run "events.txt"
$payload = $input | Out-String        # hook stdin（含 turn_id / stop_hook_active 等；字段名以实际为准）

# 1) STOP / 过期 → 放行
if ((Test-Path (Join-Path $run "STOP")) -or
    [DateTime]::UtcNow -gt [DateTime]::Parse((Get-Content $stateFile -Raw | ConvertFrom-Json).expires_at)) {
  exit 0
}

# 2) 原子扣减（单文件、供实验用；更高要求可用临时文件+Move 原子替换）
$s = Get-Content $stateFile -Raw | ConvertFrom-Json
$s.step = [int]$s.step + 1
$s | ConvertTo-Json | Set-Content $stateFile -Encoding utf8

# 3) 记录（观测）
$rec = "{0} step={1} payload={2}" -f [DateTime]::UtcNow.ToString("o"), $s.step, $payload.Replace("`n"," ")
Add-Content $events $rec -Encoding utf8

# 4) 超限放行
if ($s.step -gt $s.max_steps) { exit 0 }

# 5) 否则续一步
'{"decision":"block","reason":"continue-one-step"}'
exit 0
```

---

## 3. 执行步骤

1. 放好临时 `hooks.json`（只含一个 `Stop` command hook，指向上面的脚本）。
2. 初始化 `state.json`：

```json
{ "max_steps": 3, "step": 0, "expires_at": "<now UTC + 10min RFC3339>" }
```

3. 确认 `events.txt` 为空、`STOP` 不存在。
4. 人类**只发一条启动消息**（例如 `CONTINUATION_START`）。
5. 观察并记录：
   - 每条回复是否在同一个可见 Codex **Task**；
   - 每条回复对应的 `turn_id`（hook stdin 里取）；
   - 每条回复的 `stop_hook_active`；
   - 当前 `step`、时间。
6. 期望序列：初始回复 → 续步1 → 续步2 → 续步3 → 自动停；无人工「继续」。
7. 实验结束立即：删除临时 `hooks.json`、run 目录、marker、日志；还原原 hook 配置。

---

## 4. 证据回报模板（发回 DS-H）

```text
实验：Codex Stop-hook 连续续步（纯机制）
task_id: <同一个 Codex Task id>
sequence:
  初始回复 step=0 turn_id=... stop_hook_active=false time=...
  续步1   step=1 turn_id=... stop_hook_active=... time=...
  续步2   step=2 turn_id=... stop_hook_active=... time=...
  续步3   step=3 turn_id=... stop_hook_active=... time=...
  自动停止：未出现第 4 步
cleanup: 临时 hook/state/events/STOP 已删除，原配置已还原
verdict: PASS / FAIL
```

---

## 5. 判定与去向

- **PASS（连续 3 步 + 自动停 + 同 Task）** → 进入 §5.2（接 PAOS 真闭环：人类启动一次 → Agent 按剩余工作决定是否重发 marker）。
- **FAIL / 只能续 1 次 / 出现第 4 次 / 换新 Task** → 按 `29` §5.3：**Codex 回退 Heartbeat**，或暂时退出自动协作范围；不为 hook 建主链。
- 无论结果，如实回填 `29` §5 的实验结论与 `30` 本文的证据段。

---

## 6. 附：§5.2 接 PAOS 真闭环（通过后再做，概要）

通过后把 run 目录换成「PAOS run 信封 v2」（`29` §4.5），让 Codex：

1. 读 PAOS Request（指向自己的 open Request）。
2. 完成步骤 A → Update。
3. **自己判断**是否还有明确后续步骤：
   - 有 → 写结构化 `marker.json`（含 `reason`）；
   - 无 / done / STOP → 不写。
4. `Stop` hook 只消费 marker 并续一步。
5. ...直到 Update/Close，不再留 marker → 自动停。

这里验证的不仅是「能连续触发」，更是「**连续性来自 Agent 判断，hook 只执行续步**」。

---

## 7. 实验结论（已回填，2026-08-25：PASS ✅）

```text
一次人工输入
→ 初始回复
→ 自动续步 1
→ 自动续步 2
→ 自动续步 3
→ 自动停止（未出现第 5 次续步）
```

- 同一 Task：`019fa820-4cd7-77c2-9e0d-50600edc2300`
- 同一 `turn_id`：`01a036d4-52ad-7b61-a61f-5d2752587425`
- `stop_hook_active`：`false → true → true → true`
- 最终 `step=4 / max_steps=3`：第 4 次只放行，无第 5 次
- 临时 hooks.json / 状态文件 / 事件日志已清理

**根因修复**：原脚本同时用 stdout JSON + `exit 2`，Desktop 判为 hook 错误；改为 stdout JSON + **`exit 0`** 即符合当前协议。修复已同步回 `stop_hook.ps1`（`exit 0`，BOM+CRLF）与本文件 §2 参考实现。

**判定**：`Stop` hook 连续续步成立 → 可进入 `29 §5.2`（接 PAOS 真闭环）。Codex hook 主链可行，不走「回退 Heartbeat」分支。