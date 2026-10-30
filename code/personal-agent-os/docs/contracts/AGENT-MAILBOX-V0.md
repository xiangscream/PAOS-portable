# PAOS Agent Mailbox V0

状态：M2 第一包 canonical contract。

基线：PAOS `main@7110a46aa3f794907158313a353686ee30eb9553`（M0 + M1A + M1B）。

## V1.1 命名说明

V1.1 另外增加了 Project Workstation 内的持久 Markdown **Workstation Mail**（见 `WORKSTATION-MAIL-V11.md`）。

本文件定义的 Mailbox 仍然只是 canonical Request / Assignment 的正式责任投影。二者不得混成一个状态源：Workstation Mail 负责持久通信，Request/Assignment Mailbox 负责正式责任。

## 1. 一句话定义

**Mailbox 是 durable PAOS Agent（现有 `sessions[]` / sNNN）的正式工作责任投影，不是聊天记录、消息数据库或第二套任务状态机。**

PAOS 继续以 Project / Work / Request / Decision / Session 等 canonical facts 为真相。Mailbox 只回答：

- 现在有什么责任明确交给我？
- 我发出了什么责任、还在等别人处理？
- 与我直接相关的哪些责任刚刚闭合？

普通 Runtime Continue 不迁移 Mailbox，因为 Agent ID 不变。

## 2. 不新增 `mailbox[]`

M2 V0 不在 Project schema 中新增 Mailbox 持久化对象，也不复制 CAT Exchange。

来源仍是现有 canonical Request：

```text
Project.requests[]
  ├─ information
  ├─ artifact
  ├─ review
  ├─ decision
  ├─ coordination
  ├─ resource
  ├─ clarification
  ├─ assignment
  └─ integration
```

Request 状态继续只有现有 `open / resolved / cancelled`。Assignment Ack、Coordination Switch Work、Request update 等状态变化继续走各自现有 workflow；Mailbox 本身不提供独立 resolve/ack 状态。

## 3. Agent Inbox 的显式绑定规则

一个 Request 只有满足至少一个**明确 canonical 绑定**，才属于具体 Agent 的 Inbox：

1. `request.target_session_id == agent_id`；
2. 当 Request 没有 concrete `target_session_id` 时，`request.id` 明确存在于该 Agent 的 `session.request_ids[]`；
3. 当 Request 没有 concrete `target_session_id` 时，`request_type == assignment`，且 Request ID 明确存在于该 Agent 当前或历史 Cycle 的 `entry.assignment_request_id`（或顶层当前 entry）。

**Concrete target 优先。** 只要 Request 已存在非空 `target_session_id`，该字段就是具体 Agent 归属的最高优先级事实；其它 Agent 的旧 `session.request_ids[]` 或 Assignment entry 不得覆盖它、不得把同一责任再次投递给别的 Agent。

第三条用于支持：Coordinator 先按 Identity 建立 Assignment，Human 随后 Open 一个具体 Agent 并通过 `assignment_request_id` 明确接单。

**禁止按 Identity 相似性推断具体 Agent。** 多个 Agent 可以拥有相同 `identity_id`；仅有 `target_identity_id=implementer` 的 Assignment 在尚未绑定到 sNNN 前属于 staffing/unassigned 责任，不自动进入任何一个 implementer Agent 的 Inbox。

## 4. 三个视图

### Inbox

`status=open` 且按第 3 节明确绑定到本 Agent。

若同一 Request 同时由本 Agent 发出又指向本 Agent，只在 Inbox 出现一次，`direction=self`，不再重复进入 Waiting。

### Waiting

`status=open`、`source_session_id == agent_id`，并且该 Request 不属于本 Agent Inbox。

含义是“本 Agent 已把正式责任发出，目前仍等待其 canonical Request 闭合”。

### Recent

`status in {resolved, cancelled}` 且本 Agent是明确 incoming owner 或 `source_session_id == agent_id`。

Recent 是轻量闭环历史，不替代 Ledger。

## 5. Review / Rework 边界

`request_type=review` 可以像其它 Request 一样进入 Mailbox。

当前 Human `work.review.reject` 只把 Work 从 `review` 退回 `doing`，并没有指定哪个 Agent 负责返工。因此：

> **Work 被 reject 本身不构成某个 Agent 的 Mailbox responsibility。**

需要返工时，必须由现有责任工作流形成明确指向具体 sNNN 的 Request / Assignment，之后才进入该 Agent Mailbox。V0 不从 `review_source_session_id`、最近执行者、Identity 或时间顺序猜测返工责任。

## 6. Human Needs Me 边界

`Needs Me` 继续表示“没有 Human 介入就无法正确继续”的项目级 Human gate。

Mailbox 表示 Agent responsibility。二者可以指向同一 canonical Request，但不是同一投影：

- 明确 target 到 Agent 且 `requires_human=true`：仍可出现在该 Agent Inbox，并保留 `requires_human` 标记；
- 同一 Request 也可由 Needs Me 提醒 Human；
- Mailbox 不因为 Human gate 就自行隐藏正式 Agent 责任。

## 7. Restore 语义

Mailbox 是**当前业务真相的 live projection**，不是 Working Memory 或 execution-tenure history。

因此 Restore 如果把 `requests[]` 的当前业务状态回退，Mailbox 必须跟随恢复后的当前 Project 投影。M2 **不扫描 append-only Ledger 来复活被 Restore 隐藏的未来 Request 状态**。

这与 M1A/M1B 的例外不同：

- execution tenure 不能被 Restore 复活旧 Runtime；
- Working Memory logical head 不能因 Restore 丢失连续性；
- Mailbox 则必须反映当前被恢复的 business projection。

## 8. 顺序与去重

- Inbox / Waiting 按 canonical `requests[]` append 顺序输出，旧责任优先，避免新责任长期遮住旧责任；
- Recent 使用相同 canonical 顺序后反转，最近追加的闭环责任优先；
- 同一个 Request ID 在同一 section 只出现一次；
- 不按“最近时间”“同 Work”“同 Identity”推断责任归属。

## 9. Context Pack 边界

Agent Detail 的 Mailbox 是读取当下 Project 后生成的 **live projection**；写入某个 Context Pack 的 Mailbox 则是该 Cycle 创建时的 **bounded snapshot**。运行期间如果需要确认最新责任，Runtime 必须读取当前 Agent/Session Detail；当前 PAOS fact 覆盖旧 Pack snapshot。

M2 生成的新 Context Pack 以 `mailbox` 作为 Agent-facing responsibility view。**Legacy Request 输入必须在基础 Prompt renderer 运行前被屏蔽**：用于 Context 编译的 Project view 保留相同 revision、Work、Ledger、Artifact、Session 等事实，但不给下层 compiler 暴露全量 `requests[]`。Mailbox 本身始终从真实 Project Request facts 计算，持久化 Project 不被修改。

因此最终 Prompt 与最终 Pack 均不得再暴露旧的全项目 `open_requests` dump 或旧的 `pending_requests` coordination 列表。不得通过“Prompt 已经渲染后再字符串裁剪”的方式修复；最终 renderer 的输入本身必须已经不包含这两条 legacy responsibility 路径。

这同时意味着：同一 directed Request 不得既出现在 `Mailbox Inbox`，又重复出现在“待处理的协调请求”。M2 之后 Agent-facing responsibility 的唯一 Context 入口是 bounded Mailbox。

V0 Context 限额：

- Inbox：最多 12 项 / 4000 serialized chars；
- Waiting：最多 8 项 / 2400 serialized chars；
- Recent：最多 8 项 / 1600 serialized chars；
- 单项 description 超过 1200 chars：正文省略并显式 `description_omitted=true`，不静默截断；
- Recent resolution 超过 600 chars：显式省略；
- 超长 target Identity 同样显式省略。

Context Pack 只放责任索引，不复制 CAT 对话或 Ledger 证据 body。

Prompt 必须明确：

```text
Mailbox in Context Pack = bounded entry snapshot
Current Agent Detail mailbox = live responsibility projection
PAOS current fact > old Pack snapshot / inherited memory
同 Identity != 同 Agent
状态变化继续走 canonical workflow
```

## 10. V0 读入口

M2 第一包不增加新的 HTTP write route，也不增加平行 Mailbox 数据 API。

现有 Agent/Session Detail：

```text
GET /api/projects/{project_id}/sessions/{agent_id}
```

新增 `mailbox` 字段，返回完整 live projection。

每次新 Context Pack（Open / Continue / Switch / Reactivate 等已有编译路径）新增 bounded `mailbox` 字段和 Prompt 摘要。Pack 内现有 `api.session` 就是刷新 live Mailbox 的读入口。

`WorkflowService.mailbox(project_id, agent_id)` 作为内部只读 facade，便于测试和后续 UI/CLI 复用。

## 11. 明确不在 M2 V0 第一包

- 不复制 CAT Room / Exchange；
- 不做 CAT wake / runtime rebind（M3）；
- 不新增 `mailbox[]`、message ID 或 unread/read 状态；
- 不按 Identity 自动领取 Assignment；
- 不从 Work reject 自动猜返工 Agent；
- 不新增通用 Request 状态机；
- 不做通知推送、定时轮询、自动启动 Agent；
- 不修改真实 `private-data/`。

## 12. 阻塞验收

1. 明确 `target_session_id` 的 open Request 只进入该 concrete target Inbox；其它 Agent 的旧 `request_ids` 不得覆盖 concrete target。
2. target 为空时，`session.request_ids[]` 明确绑定的 Request 进入 Inbox。
3. Identity-only Assignment 不进入任一同 Identity Agent；一旦 Session/Cycle entry 显式绑定 assignment_request_id，则进入该 Agent Inbox。
4. Agent 发出的未闭合 Request 进入 Waiting；self-target 不重复。
5. resolved/cancelled 的直接责任进入 Recent。
6. Work review reject 若没有明确 Request/Assignment，不制造 rework Mailbox 项。
7. `requires_human` 的明确 Agent Request 保留在 Inbox 并标记，同时不改变 Needs Me 语义。
8. Restore 后 Mailbox只服从当前 `requests[]`，不从 Ledger 复活未来状态。
9. Agent Detail 返回完整 live Mailbox；新 Context Pack 返回 bounded snapshot；legacy Request 输入在基础 Prompt 渲染前被屏蔽，最终 Pack/Prompt 不含 `open_requests/pending_requests`，Prompt 指向 `api.session` 作为刷新入口。
10. 最终 Prompt 不得泄漏 identity-only Assignment 或其它 Agent 的 Request；同一 Agent-owned directed Request 只通过 Mailbox 展示一次，不得再出现“待处理的协调请求”重复段。
11. M1A tenure 与 M1B Working Memory 行为不回归；`python scripts/verify.py` 全绿后才可合并。
