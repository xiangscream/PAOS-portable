# DS-H Schedule 同 Session 最小实测 Runbook（23）

> 状态：PAOS 侧已就绪（对象已创建）；**等待用户在本 Web GUI 外部执行 overlay 重启**，然后在本会话继续。
> 上游：`21` §1/§3、`22` §2.1、`19` §3（设计 B）。
> 性质：执行手册。每步都先判停止件；未达 L4 不写“已验证原 GUI 同 Session 自动唤醒”。

---

## 1. 已创建的 PAOS 对象（Project 3002，2026-08-24）

| 对象 | ID | 说明 |
|---|---|---|
| 被测 Session | `3002-s014` | `runtime_id=deepseek harness`、`identity=implementer`、`agent_label=DSH-Schedule-TCW`；已 Ack；`runtime_session.session_id=session-46af412b-8e6b-41ca-91c6-7760e62406d0`、`source_path=/home/remo/.dsh/sessions/--home-remo-paos--/session-46af412b-8e6b-41ca-91c6-7760e62406d0/session.jsonl.zstd` |
| 停靠 Work | `3002-w012` | 当前 Work（Ack 后 session 挂在它上面） |
| 领取目标 Work | `3002-w013` | `todo`；被 Request 指向 |
| 定向 Request | `3002-r002` | `open`；`target_session=3002-s014`、`target_work=3002-w013`、`source=3002-s014`（临时 Coordinator 创建后已撤销） |

- 创建时基线 revision 依次推进到 `117`。
- 临时 Coordinator 已撤销：`3002-s014` 恢复 plain Worker；`r002` 创建于撤销前，保持 open。
- 本轮未创建 Automation/计划任务；未 CLI 唤醒 GUI；未改 WorkBuddy 二进制。

---

## 2. 第一步：用户在 GUI 外部重启（带 schedule overlay）

当前 web 服务进程（命令与 cwd 已核实）：

```text
PID 518, cwd=/home/remo/work/deepseek-harness
node --import tsx/esm apps/cli/src/bin.ts web --host 127.0.0.1 --port 3080
```

停止并重启（**在 WSL 终端执行**，会短暂中断本 GUI，属预期）：

```bash
kill 518
cd /home/remo/work/deepseek-harness
/home/remo/.nvm/versions/node/v24.18.0/bin/node --import tsx/esm apps/cli/src/bin.ts web --host 127.0.0.1 --port 3080 --patch examples/web-schedule/cordis.yml
```

> 若 `kill 518` 找不到（PID 变化），用 `ps -eo pid,cmd | grep "apps/cli/src/bin.ts web"` 找到当前 pid 再 kill。

重启后回到本会话（cold resume 同一 Session），先核对 `schedule_*` 工具可见：

```text
tools_catalog 查询 schedule  → 应出现 schedule_create / schedule_list / schedule_delete
```

---

## 3. 第二步：记录基线（执行前）

- DS-H 原生 Session ID：`session-46af412b-8e6b-41ca-91c6-7760e62406d0`（应不变）
- PAOS Project 3002 `revision`、`3002-r002` 状态（应 open）、`3002-w013` 状态（应 todo）
- `schedule_list` 起始应为空

---

## 4. 第三步：schedule_create（一次性，不用 every_seconds 防止重复）

建议值：一次性 `after_seconds` 或 `at`（`now + 6~8 分钟`，留观察窗）。prompt 全文：

```text
[DS-H Schedule 同 Session 最小实测]
先判停止件：若已见 Work done / STOP / 截止时间，则结束本轮且不领取。
否则只做：
1) 确认仍在当前 DS-H Session（Session ID 未变，未新开会话）。
2) GET http://127.0.0.1:8766/api/projects/3002/office?session_id=3002-s014
   （读走 Windows PowerShell Invoke-RestMethod 或等效只读通道）。
3) pending_requests 为空 → 静默结束本轮，不写“暂无任务”。
4) 存在 3002-r002（open）：读取 description/target_work_item_id；用
   POST /api/projects/3002/sessions/3002-s014/switch-work
   schema=paos-session-switch-work/v1，带 target_work_item_id=3002-w013
   与 coordination_request_id=3002-r002（仅一次）。
5) 成功后 Acknowledge → 做一次极小回写 → Update/Close；
   Request 只领取一次；resolved_request_id / Ack / Update / Close 全进 Ledger。
6) 完成后 schedule_delete 删除本轮提醒并记录删除时间。

任何含中文写回走 Windows 原生 Python urllib（UTF-8, ensure_ascii=False）。
```

---

## 5. 第四步：等待到期并观察

- 保持本 Web GUI 打开、live 且 idle；不发普通人类消息。
- 观察是否仍为**同一 Session**；Session log 应落 `schedule/change create → dispatch`。

---

## 6. 第五步：验收（strict L4，限定 DS-H 同 Session）

- [ ] Session ID 未变、GUI 可见、无新 Session
- [ ] `schedule/change` 有 create → dispatch
- [ ] 未由普通人类消息触发
- [ ] `3002-r002` 恰好 `status=resolved` 且 `resolution=target_session_accepted`，只领取一次
- [ ] PAOS Ledger：`session.work.switched`(含 resolved_request_id) → `session.acknowledged` → `session.update.applied` → `session.closed`

---

## 7. 停止 / 回滚

- 主停止件 = `schedule_delete`（删除本次提醒并记录时间）。
- 若 schedule 到期但提示已 overdue：回到本 Session 重新打开会投递 overdue；仍用 `schedule_delete` 清理。
- 回滚：不重写任何 Ledger/receipt；`3002-r002` 若未领取可留 open 或由 human 决定取消；Work `3002-w012/w013` 作为真实历史保留，不删。
- 未达 L4 一律写 `unverified`，不修补掩盖。

---

## 8. 实测结果（2026-08-24 自动回合，L4 达成 ✅）

触发：`schedule-1`，`occurrence_at=2026-08-24T07:48:56.595Z`（Session-local；本回合由提醒排队产生，非新人类消息）。

| 验收项 | 结果 |
|---|---|
| 原生 Session 未变 | ✅ `session-46af412b-8e6b-41ca-91c6-7760e62406d0` |
| 同一 GUI 会话可见 | ✅ 本回合出现在原会话 |
| 未由普通人类消息触发 | ✅ 触发源 `[SCHEDULE REMINDER] schedule-1` |
| Request 只领取一次 | ✅ `3002-r002` `resolved / target_session_accepted` |
| STOP 生效 | ✅ 一次性提醒触发后自动消费：`schedule_delete → schedule_not_found`，无残留定时器 |
| Ledger 链路 | ✅ `session.work.switched(rev118)→session.acknowledged(119)→session.update.applied(120)→session.closed(121)` |

PAOS 最终状态：`rev=121`；`3002-s014 status=completed`、`current_work_item_id=3002-w013`；`3002-w013 status=review`（进入人类 Review，符合生命周期）。

结论：**DS-H Schedule 同一原生 Session 自动唤醒 + 定向领取链达到 L4**（限定 DS-H 自身；已知边界：`session-local` 仅在本 Session live+idle 时触发，GUI 关闭只变 overdue）。

后续：人类对 `3002-w013` Review 归档；多 Worker 并行进入 P2。