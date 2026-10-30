# Session Continuity

## 概念

员工身份 = Session Continuity Chain：

```text
s011 → s027 → s041
```

字段：`Session.continues_session_id`。`employee_id` = 链根 Session ID，仅用于投影，不持久化。

## 规则

1. 前序 Session 必须属于同一 Project，且必须存在。
2. 不能 continue 自己。
3. 一个前序 Session 最多一个后继 Session（不许分叉）；需要分叉就另起新的员工链。
4. 链条不能成环。
5. 接续已结束（completed/partial/blocked/abandoned/historical）的前序 Session 时，不改变其 Close 结果。
6. 接续 active/pending_ack 前序 Session 时，旧 Session 当前 Cycle 记录：
   - `ended_at`
   - `end_kind = "session_continuation"`
   - `end_reason = "Continued by <new_session_id>"`
   旧 Session 状态置为 `historical`，不产生真实 Close 证据。

## 投影

纯函数：
- `session_predecessor(project, session_id)`
- `session_successor(project, session_id)`
- `session_root_id(project, session_id)`
- `session_chain(project, session_id)`
- `current_session_for_chain(project, session_id)`

它们不写盘、不发 HTTP。

## Prompt

接续 Session 的握手 Prompt 会包含“你正在接续前序 Session”，列出前序 Mission / note_for_next_session，并要求在 Acknowledge 中说明：
1. 当前目标理解
2. 先做什么
3. 继承风险或冲突

## Cycle 与 Close

- Session.result = 员工这次工作的结果。
- Work.status = 项目对整项工作的正式判断。
- 两者解耦。Cycle.end_kind 允许：agent_close / human_switch / session_continuation。
