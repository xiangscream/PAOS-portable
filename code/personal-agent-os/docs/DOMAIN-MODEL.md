# Domain model — Workless 现行语义

> 现行口径（2026-10 Workless 收敛后）：Project 文件与 Git 保存成果；长期固定 Home 承接责任；Current 由本人维护；输入经 durable Mail/Notice；原生 runtime 是唯一推理者；**无 Work/无 Cycle/无 ACK 前置**。旧三态 Work 口径是历史设计稿，仅解释 `VERSION_HISTORY.md` 与已归档材料；不在 README/操作指南里充作现行语义。

## 对象

| 对象 | 含义 | 在哪 |
| --- | --- | --- |
| Project | 一条业务主线（唯一 Store 上下文） | `private-data/project-registry/projects/<id>.json`（Store 合同） |
| Agent Home（长期固定工位） | 一个有稳定身份与固定工位的成员责任 | `Workstations/<agent>/`（ENTRY.md + TODO.md(paos-todo/v3) + mailbox/ + notices/） |
| Current | 本责任区实时行动表（objective/approved_scope/stage/next_action/waiting/results/inflight/delivery 等） | 所属 Home TODO.md 的 Current 区 |
| Session | 一个原生 Runtime 会话/执行容器（可重建、可代换） | Project Store 资料（历史可读），不承载 Home 责任 |
| Mail | 发出即不可变的定向消息 | `Workstations/<agent>/mailbox/<message_id>.md` |
| Notice | Home 对一件输入/激活意图的 durable 处理事实 | `Workstations/<agent>/notices/<notice_id>.md` |
| CAT Room | 可选跨 Runtime 协作（另一仓） | CAT 仓；非 PAOS Store |
| Workflow / Skill Library | 共享方法论与技能单正文 | `PAOS-Libraries/{workflow,skill}`（必须 install configure 登记） |

## 语义规则

- **责任存于 Home**：无 Work 对象、无 claim/ack 与交接动词；Home 的 Current 就是本人的责任底面。
- **成果存于文件与 Git**：Project JSON 记业务事实；产物/工件进项目路径或仓库，不复制多份"状态真相"。
- **Mail 不可变**：同 message_id 不同内容被拒（`mail_message_id_conflict`）；投递状态以 mailbox 文件+dispatch JSON 为证。
- **激活是一次性原生注入**：agent send/notifyMail 落信后请求一次 self-contained injection（成功即止，失败如实）；不引 Helper Runtime 流程代理。
- **休眠 Runtime 不假装在线**：contact native-target/`paos team` 状态如实 unknown。

## 历史边界

- 旧 Work / Cycle / ACK / coordinator work-items 路由退役；相关历史数据在 Store 以惰性归档保留（可读，不参与执行）。
- 旧 resume 链（`continues_session_id`）仅历史概念；现行恢复打法 = 固定工位 ENTRY/TODO + `paos orient`。
