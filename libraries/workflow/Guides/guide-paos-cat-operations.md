---
schema: paos-workflow/v1
id: guide-paos-cat-operations
title: PAOS 操作指南：联系、当前页与运行
description: 按需操作：正常留信与提醒、维护本人当前页、查看版本和排查阻碍。
tags: paos, cat, cli, operations
status: active
version: 82
---

# PAOS 操作指南

从固定 ENTRY 取安装入口。Windows 使用 `C:\Users\remo\.paos\bin\paos.cmd`，WSL 使用 `/home/remo/.local/bin/paos`。下面的 `paos` 代表该入口。Portable 的 `health` 检查本地安装，工位与联系读 `status`，安装定位读 `install show`；这些不依赖 Core HTTP；参数不清楚时查对应子命令的 `--help`。

## 查看当前事实

| 目的 | 命令 |
| --- | --- |
| 找回本人的当前责任 | `paos orient <project> <home>` |
| 读分源输入 | `paos inbox <project> <home>` |
| 找同事 | `paos peers <project> <home>` |
| 查看消息与运行状态 | `paos status <project> <home>` |
| 查看已发信件 | `paos status <project> <home> --message-id <id>` |

Mail、正式 Requests 和已配置 CAT 分开读取。读取失败不是零消息；没有配置 CAT 就按不适用处理。

## 联系并让对方接续

需要同事接续时，用 `agent send --remind`：先保存 Mail 与 Notice，再沿该 Home 的 Contact 提醒一次。目标用所属 Project 和完整 Home ID，发送方用本人 Home。先从本人 Current 取得**成果原件的绝对路径**；再另写一份 UTF-8 **短交接正文**，只写结论、接续动作和原件绝对链接。原件与短正文分开保存，不把整篇报告当作默认邮件正文。正文用 `@` 读短正文文件。

普通交接保存成果后，用 `agent send --remind` 交付、`attention todo-update` 校准本人当前页；下游回告后直接读其成果并继续。解除等待的验收回告也属于需要接续的交付。对方没有回流或报告失败时，再用 `status --message-id` 定位。已有原件和回告即可引用，无须另写一份收件证明或逐级重查全部状态。记录完成状态或回告时，把当前结论写在前，再接续动作和原件。

短正文示例（`$handoffFile` 指向这个文件）：

```markdown
# 交付接续

结论：本次候选已通过受影响检查，结论与边界见原件。
接续：请读取原件，按其中“下一步”继续；无需重新加载完整过程。
原件：C:/Users/remo/Desktop/agent学习计划/PAOS-Projects/3002-Personal-Agent-OS/Works/<成果路径>.md
```

```powershell
$paosCmd        = 'C:\Users\remo\.paos\bin\paos.cmd'
$selfHome       = '<本人完整Home ID>'
$targetProject  = '<目标Project>'
$targetHome     = '<目标完整Home ID>'
$sourceOriginal = '<成果原件绝对路径>'
$handoffFile    = '<短交接正文绝对路径>'
$carrier        = '@' + $handoffFile
$messageId      = '<本次唯一ASCII消息标识>'

& $paosCmd agent send $targetProject --to $targetHome --sender-kind agent --sender-id $selfHome --subject '交付接续' --body $carrier --message-id $messageId --remind
```

WSL/bash 使用同一组参数；变量取当前任务的目标、本人 Home 与**短正文**路径，不把成果原件塞进 `--body`：

```bash
paosCmd=/home/remo/.local/bin/paos
sourceOriginal='<成果原件绝对路径>'   # 仅在短正文中作为链接引用
handoffFile='<短交接正文绝对路径>'
"$paosCmd" agent send "$targetProject" --to "$targetHome" --sender-kind agent --sender-id "$selfHome" --subject '交付接续' --body "@$handoffFile" --message-id "$messageId" --remind
```

读取投递和提醒各自的结果。需要下游接续的正式交付，将该次完整回执保存在既有任务成果旁；保留目标、时间、message_id和提醒结果，不只截取delivered或next_action。留信成功不等于对方被提醒；原生受理不等于业务完成，最终看对方实际读取与产物。需要接续的新交付使用首次提醒，即使对方正在工作；省略 `--remind` 仅用于不要求接续的留档告知。相同 message-id 的高层重放保留已完成提醒，不再第二次注入；正文或目标改变时是新输入，使用新标识。

OpenCode 正在工作也可以受理新的交付；accepted 时不因 busy 重试。manual_required、native_rejected、离线或 STOP 按回执处理，并保留原件、所需结果和接续人；不循环发送同一输入。delivery_uncertain / network_unconfirmed 表示原生回执未知，accepted 为 null，不得重发或失败后换路。已送达或结果不明时先核原消息状态。

| 失败类别 | 事实与边界 | 下一动作 |
| --- | --- | --- |
| `receiver_stale_registration` | 目标登记的接收进程不存在；Mail 可已落盘，但本次提醒明确未受理。 | 普通发送者按回执交 `repair_owner`/目标本人处理，不查凭据/PID、不代启、不自动重投；安装维护者可沿正常维护入口排查。恢复后按原 message_id 与原文正常接续。 |
| `receiver_offline` | 本次提醒未接通；可能是连接拒绝、目标离线等原因，不能仅凭此断言是死 PID。 | 保留 Mail；交目标本人或回执的 `repair_owner` 核查正常入口。恢复后按原信接续，不自动重投。 |
| `receiver_not_registered` / `receiver_not_prepared` | 当前发送所需的目标侧扩展/准备入口缺失；只说明本次发送入口不足，不是所有 Runtime 都不支持原生提醒。 | 保留 Mail；交目标配置或准备正常入口。有可用的既有正式入口再按原信接续。 |
| `attach_undefined_for_driver` | 人工 attach/navigation 未定义；出自联系读面，不是一次原生发送失败。Codex 也可能返回该字段。 | 不据此判该 Runtime 无法原生提醒；改看实际提醒回执与接收状态。 |
| `native_unavailable` 且 `phase=status_read` | 原生状态读取未成功，本次提醒明确未受理；`prepared` 只证明接收器就绪。 | 保留已到 Mail，交原Owner/Rooter核原会话错误。容量失败沿原Home/Thread的已有恢复入口接续，配置沿当前授权；恢复后读原信，不因503重建接收器或重投业务。 |
| `delivery_uncertain` / `network_unconfirmed` | **提醒结果未知，`accepted=null`**；Mail 是否已落盘按 delivery 回执独立判断，不能因提醒未知就写 Mail 未确认。 | 先核原消息/delivery 回执与 reminder 记录；不重发、不换通道、不改身份。 |
| `native_busy` / `native_rejected` / STOP / 明确离线 | 本次提醒被明确拒绝或停止；不等于 Mail 未保存。 | 按回执的 `repair_owner` / `next_action` 处理；不循环重试。 |
| Mail delivered / reminder accepted | 只证明保存与本次受理，不等于同事已读取、已处理或业务已完成。 | 等实际读取/产物；需要接续时按原信继续，不重复发送。 |

Codex的`wake status <project> <home>`与`status`使用同一Contact事实：`receiver.state=process_not_running`表示登记进程已退出；`process_identity_mismatch`表示同号PID已不是原receiver实例，即使pid_alive=true也不是prepared。prepared须核OS实例，不等于原生可用或业务消费。一次提醒明确区分receiver_offline/receiver_not_prepared、native_busy、native_stopped及delivery_uncertain，回执附error_code、repair_owner和next_action。状态未确认仍是unknown；调用方不再自己读登记、查PID/端口或重置绑定。

`attach`描述人工打开或接入Runtime的方式。已配置 native target 的 `binding_status=configured` 只表示目标存在，不等于 bound、online 或已消费；未配置仍为 `unbound`。`attach_undefined_for_driver` 不能单独说明原生提醒不可用；应看该驱动的接收状态及具体提醒回执。Codex 保留其 Desktop/thread 人工导航；其它 Runtime 显示自身已配置的 `manual_open` 或诚实未知，不套用 Codex 路径。Codex读`receiver.prepared/pid_alive`；WorkBuddy还需其已授权扩展实际运行。

Codex正常接收器对明确active/idle/notLoaded向既有原生跟进入口提交一次已授权短Notice；不因active预先拒绝，不覆盖模型或Follow-up设置。回执的`native_status_before_submit`只表示提交前观察，不保证steer、下一turn排队或业务消费。未知、STOP和实例核验保持。若入口明确返回`native_busy / accepted=false`，按真实拒绝处理；不要在active回合内等待自己被唤醒，也不自动重投旧输入。

WorkBuddy回环建立连接前明确被拒绝为`receiver_offline / accepted=false`；SDK调用后的错误、超时/复位和响应丢失仍保留结果未知。旧回执不改写、不补投，产品支持的正式安装与授权阻碍独立保留。

已留信但尚未提醒的旧输入，用原件补 `wake trigger` 一次；不要为补提醒重发原信。参数看安装 help。

接收者结束回合前读当前相关 pending；有可执行输入就继续。具体等待和收口按 [工作循环](../Workflows/wf-agent-work-cycle.md#交付与收口)，不把早期 inbox 为空当成收尾时仍未收到。

S号寻址和跨Project参数查安装 `agent send --help`。普通消息使用现有Contact，不用 native UUID、同事凭据或另建服务。

### Codex 目标上线准备

正式入职或配置由登记方通过正常 `wake bind` 一次补完整目标配置；需要显式配置时按同版 help 使用可选 `--driver-config`。Windows 补默认定位并保留显式定位与 STOP；非 Windows 使用已有或明确的 Windows 定位。

目标本人从原 Desktop 环境 prepare，只读 Contact 并启动自己的入口。配置缺项交回正式登记入口补齐；多人恢复不改共享 Contact。WSL 发送按已登记的 Windows 执行入口一次 stdin 交接，不在失败后改走另一条路径。

普通发信仍用 `agent send --remind`，调用者不用查 pipe、PID或端口。健康接收器只在行为代码需要更新时由本人加载。纯版本公告向未启动入口只留持久通知；需要实际接续的业务仍按[工作循环](../Workflows/wf-agent-work-cycle.md#交付与收口)办理。

原会话、模型和 STOP 保持；发送者不借目标 pipe、token 或身份，也不自行启动同事服务。启动条件及配置正文见 [已安装接收器说明](C:/Users/remo/Desktop/agent学习计划/PAOS-Projects/3002-Personal-Agent-OS/Source/personal-agent-os/docs/CODEX-SELF-REMINDER.md)。运行文件存在不等于进程存活；缺失或离线如实记录。生命周期日志帮助定位后续退出，不自动重启、不把 prepared 称为送达。

本人正常prepare在原锁下仅归档同Thread、正向已死或正向身份失配的登记，再发布新入口；不终止同号无关进程，不手改grant或rebind。缺实例字段的旧活receiver先核OS精确启动合同：runtime-file与目标stop-file都须按规范化路径或samefile核为同一位置，再核既有授权空消息拒绝，保留旧原件并原子补身份，保持原服务与token；不能只回填当前PID。任一路径无法核定则unknown，不发迁移探测。实例相符的活服务、查询未知、外Thread与STOP不覆盖。旧迁移验证不调用模型，失败保留旧登记；细节读已安装接收器说明。统一用户级SessionStart已正常安装，沿既有installation/registry/Contact定位本人Home，不需逐员工复制Hook；新员工仍需完成正常Home/Contact登记。自动准备须由原Owner确认正常review/trust及真实startup/resume继承本人环境后才算采用。定义文件、信任记录和prepared状态不能代替真实恢复结果；现场采用进度读已安装接收器说明所指的原记录。正常审阅入口与定义见上述已安装说明，不写信任缓存或绕策略。

接收器行为代码需要重新加载时，由本人从相同Desktop工具环境、安装Source的`scripts`目录运行`python -X utf8 -B codex_receiver_session_start.py --update-current`。入口只管理已确认本人的旧实例，在原锁下核self/Thread、runtime-file/stop-file、OS实例和既有鉴权；停止前再核同一Windows进程句柄。STOP、未知、外Thread或身份变化不停止。旧登记由正常prepare归档，新实例沿原locator启动。随后读正式`wake status`的已核新实例、`prepared=true`与`receiver_behavior=native_followup`确认加载；只迁登记、只看启动器PID或源码已更新均不代替它。只更新受接收器行为影响的实例，不由Rooter代管，也不要求操作者拼终止命令。正常prepare与SessionStart仍不替换健康实例。

Core/bridge 的独立运行由 Rooter 和运行维护者处理；本人接收器依赖所属 Harness。关闭 Harness 后的可用条件分别记录，不能把 Core 在线当作目标会话在线。

## CAT 圆桌

CAT是系统级公共讨论入口，可跨Project；重要结论回原Project。Room与同事从现行Project/联系入口取得。

| 目的 | 命令 |
| --- | --- |
| 看房间概况 | `paos cat show <room>` |
| 看同桌状态 | `paos cat members <room>` |
| 读新增发言 | `paos cat read <room> --after <已读seq>` |
| 保存当前公共原件 | `paos cat send <room> --from <本人Home> --body @<原件> --message-id <id>` |
| 调整本人席位 | `paos cat seat <room> --home <本人Home> --state participant/observer/left` |

participant接提醒并可发言；observer只读、不接提醒；left退出席位，历史保留。按当前责任选择，新的收口责任仍沿Mail/Contact交付。轮次交流按业务流程选择提醒对象；只保存公共发言时用cat send的`--no-notify`。

需要同桌接话时，省略`--no-notify`，回复用`--reply-to <原消息id>`关联问题。事实、问题和修改在同一房间交流，不再逐句复制到Mail；只表示收到时无需再回复。正式交付沿既有Mail/Contact一次完成，重要结论与唯一成果回Project。

只等待最终交付的旁听者使用observer，减少无须处理的讨论提醒；合成人用agent send --remind正式交付。需要公开发言时再转participant。逐阶段主持或需要即时答疑的人保留participant，按当前责任选择。

show默认只返回房间概况、人数、消息数与last_seq，普通与JSON读面相同；成员读members，新增发言读read --after。确需完整历史时显式用`paos --full-result cat show <room>`，整史不作为每次恢复输入。

## 当前页与输入

| 目的 | 安装入口 |
| --- | --- |
| 读本人 TODO 与 Notice | `paos attention show <project> <home>` |
| 改本人 Current 字段 | `paos attention todo-update <project> <home> --set 'stage=当前阶段' --set 'next_action=下一步'` |
| 更新 Tasks 或恢复完整 TODO | `paos attention todo-write <project> <home> --body @<候选载荷文件>` |
| 处理输入 | `paos attention handle <project> <home> <notice> --resolution "处理结果" --action-ref <任务或成果>` |
| 展示归档 | `paos attention notice-update <project> <home> <notice> --archive` |
| 登记已落盘的直接输入 | `paos attention source-register <project> <home> --source-ref <绝对路径或URL> --summary "索引"` |
| 核已存在的输入 | `paos attention source-status --help` |
| Rooter Home | `paos attention rooter-show`；同组 `rooter-*` 子命令维护自己的输入和 TODO |

普通 Current 维护用 `todo-update --set 字段=值`，只改提交字段，保留原元数据、未提交字段与 Tasks。列表字段 `result_refs/context_refs` 按重复 `--set` 收集，替换该列表；字段全集查同版 help。核写入回执中的实际 Current 和任务数即可，不要求另建整份候选或再次调用orient。接班定位或写入结果异常时，再用orient读取当前事实。

### Notice 登记与合并读面

Notice 的 Markdown 文件只是输入登记；当前 `state`、`read`、`archived` 以官方合并读面为准。Project 读 `attention show` 的 Home 服务结果，Rooter 读 `attention rooter-show`；工具和脚本复用同一官方读取，不只扫 `notices/*.md`，也不只合并某一个 `.read`/`.handled` sidecar 就推断状态。原 Mail/登记保留；处理仍用 `attention handle`，展示归档用 `notice-update`。

历史积压按已有证据处置：已有完成或取代证据的补收口；仍需行动的进入本人 Current；来源缺失或业务未定的保留具体 Owner。阶段接受不等于同日期所有业务完成；不按年龄清空、不伪造逐封 read、不重执旧授权。普通 Owner 维护自己的工位。

Rooter Current 使用 `paos attention rooter-todo-update --set stage=... --set next_action=...`，沿登记 Home 复用同一字段合同；`--home-id` 默认 `rooter-001`。

目标、阶段和输入版本也可在同一次todo-update中用多个--set更新；只改Current时直接使用该入口。

已发布字段合同：`updated_at` 属 Current；`todo-update` 与 `rooter-todo-update` 实际改动才刷新它，no-op 不刷新。任务层 `source_refs`（原输入）与 `acceptance_refs`（已接受成果的具体版本）随**完整 `todo-write` 载荷**维护，**不放入 Current**；只写本人当前页，不新增 `task-id`。字段可空，按需维护，不补写全部历史任务或造演示任务；引用存在不等于 PASS，PASS 仍按实际验证。`todo-update`、`rooter-todo-update` 及 Project `todo-write` 可带 `--expected-fingerprint` 做过期守卫；`rooter-todo-write` 仍仅支持原 `--body/--home-id` 参数。

需要改 Tasks 或恢复破损 TODO 时，在独立候选载荷文件中保留正确元数据和原责任，再经 `todo-write` 写回。按任务ID定位目标条目，写回后核该条目的state、result和成果引用。`trusted` 只说明格式可读，下一步按 Current 引用的项目状态和原件校准。不要先覆盖唯一 TODO 再校验。Notice 的展示归档不代处理，也不删除正文。只写本人当前页；任务完成和历史索引按工作循环归位。

### 明确接手一条输入

Project Home：

```bash
paos attention takeover <project_id> <agent_id> <notice_id> \
  --set objective='本次目标' --set next_action='下一步' --set stage='doing'
```

Rooter Home：

```bash
paos attention rooter-takeover <notice_id> \
  --set objective='本次目标' --set next_action='下一步'
```

一次显式接手依次做三件事：读取该 Notice 的 Mail 原件；标读该 Notice；只把提交的 `--set` 字段写入本人 Current。未提交的 Current 字段、Tasks、身份、Mail 正文和 Project 状态保持原样。标题和摘要不用于猜任务。

- 这是**字段补丁**，不是替换整份 Current。旧 `waiting/results/...` 只有在本次显式提交对应字段时才变化；撤旧引用直接显式提交空值，如 `--set result_refs=`（现有写者规范为空列表，Tasks 不动），不需要额外 clear 参数。
- 至少提交一个字段；可加 `--expected-fingerprint`，TODO 已变化则整次在写前拒绝。
- 目前只支持能实际读取的 Mail durable 来源；其他来源明确返回 `attention_takeover_source_unsupported`，不冒充已读。
- 坏字段/坏值/缺来源/坏指纹都在标读前拒绝。若来源和标读已成功、Current 写入再失败，回执带 `stages` 说明已完成哪步；从该事实接续，不自动重试。
- 标读不等于处理完成：Notice `handled` 仍需正常 `attention handle`；本入口不触发模型、不唤醒自己、不改模型/STOP。

### 本地工位读面

直接使用 `orient`、`attention show` 和 `inbox`，需要原件时读 TODO/Mail/Notice。
不再重建第二份 Markdown 工作台，也不轮询生成页。读到输入后按实际接手与处理
记录 Notice；已读不等于完成。正常连续阶段只读相关增量，恢复时读 ENTRY、当前
工作和必要原件。接口用途见[Home 读面](guide-paos-interface-reference.md#home-读面)。

### 工位 Contact 薄入口

对已登记的具体 Home，沿同一安装/Project/Rooter resolver 建立薄入口：

```
python scripts/paos_contact_package.py <agent_id> --installation-file <现有安装描述>
```

安装函数按“存在则保留、缺失才创建”处理，生成三份薄文件：

- `contact.py`：实际调用入口；
- `CONTACT.md`：联系与恢复说明；
- `STATUS.md`：最小工位导航/状态页。

已有同名文件不覆盖，已有人工内容不因安装而重写。三份文件都只落在准确 Home；Rooter 包不绑定 Project。它们调用安装 Source 中已有共享实现，不复制 driver、token、PID、native credential 或第二套规则。代码候选存在不等于真实 Home 已安装；实际安装、读回和采用仍以安装记录及真实结果为准。

运行 `python <Home>/contact.py status` 读取准确 Home 的共享读面、联系状态与 `capabilities`。`send/notify` 的调用方条件统一读现行调用方授权。正常成员交接使用 `agent send --remind`；薄入口沿用原权限与 Contact/Notice 语义。

`STATUS.md` 只是稳定导航和读面入口，不是第二个 Current/TODO 或验收权威。需要真实事实时回到准确 Home 的 TODO、Notice、原输入、成果及共享 read service；页面显示来源、指纹、观察时点、恢复集合和过滤/缺失范围时，以这些原件为准。

### 显式标读（Notice read）

先读原输入，再显式标读；普通读取与列表本身不改变 read 状态。两个显式入口：

| 目的 | 命令 |
| --- | --- |
| 标读 Project Home 的一条 Notice | `paos attention read <project> <agent> <notice>` |
| 标读 Rooter Home 的一条 Notice | `paos attention rooter-read <notice_id> [--home-id rooter-001]` |

标读只写该 Home 的独立 `.read` sidecar，保留首次 `read_at`；重复调用幂等（`read_changed=false`）。**read 与 handled、接受、业务完成分开**：标读不改 Mail/Notice 正文、不改 handled、也不代表已接受或已完成；处理仍用 `attention handle`。

## 工具权限与模型

Human 已授权本机 OpenCode 全部工具权限。Rooter沿服务正式 Config/Session 接口配置并核有效值；普通工具执行不要求逐次审批。若仍遇工具 ask/拒绝，保留具体错误交 Rooter修运行配置，不建立另一套审批服务。

工具权限不改变业务范围、对外承诺或明确的 Human 验收点。除非 Human 指定，不改原会话模型；正常提醒省略 `--model`，继承当前选择。

Human 显式指定 OpenCode 模型时，`--model` 传完整原生 JSON 对象，例如 `'{"providerID":"opencode-go","modelID":"deepseek-v4.1-flash"}'`；不传 `provider/model` 字符串。其他正常提醒省略该参数，继承原模型。具体参数见安装 `wake trigger --help`。

后台 OpenCode 用 `opencode attach <当前服务URL> --session <当前sessionID>` 查看原会话。URL与ID从当前联系事实取得，不另建替代会话。

OpenCode 的状态按 `directory` 分实例。查询 `/session/status` 时，显式传入该 Home/原生 Session 已核的 `directory`，并在回报保留查询目录；省略参数只读服务默认目录，不能据空表判断目标会话闲置或已停止。

维护共享 OpenCode 服务前，核该服务所有已绑定 Agent 及其实际 directory。任何会话仍在运行就保留服务到安全点；不能用一个 directory 的空状态表判断整台 server 空闲。

## 安装与目录

Windows/WSL 共用安装描述，定位看 `paos install show`。已批准的候选直呼需显式安装描述和受控根，参数查同版 help，不复制另一份默认配置。

Library 源文件变化后用 `paos library catalog workflow --root <Workflow根>` 重建目录，保留使用记录。运行切换和回退见 [升级与采用](guide-upgrade-adoption.md)，安装异常见 [Rooter 安装](guide-rooter-installation.md)。

## 问题定位

| 情况 | 下一动作 |
| --- | --- |
| 工位、身份或安装根不符 | 实读 ENTRY/安装描述，交 Rooter修准确入口 |
| 邮件回执与目标文件冲突 | 保留原输出，核同一 message/Notice/目标文件，交公共维护者 |
| 对方无回流 | 核原消息、对方 Notice/Current和产物；有实际消费就保留，不盲重发 |
| 消费端目录或计数停更 | 先查原请求的提醒结果，再读目标接收状态；目录计数仅作线索，登记、进程和接收入口由运行维护者核查 |
| TODO 不可信 | 保留准确字段错误，由本人修当前页；产品代码、公共接口和硬接入由 S010 组织，Rooter 维护软方法及安装运行 |
| 公开联系字段缺失 | 核当前读面，Rooter沿既有授权更正明确字段，不重新入职或新建 Agent |
| 模型额度耗尽 | 保留成果，停止受影响会话的无效重试；Coordinator 用已有授权且可用的执行者接原任务，Rooter 修运行接续；模型、付费和新资源沿 Human 设置 |
| 安装/Library损坏或 CLI参数不认 | `install show`及同版`--help`定位，交对应维护者 |

研究与蒻芷联系方法见 [研究与咨询](guide-research-consultation.md)。

回报只写实读产物和实际执行结果，表达沿 [简明表达规则](guide-concise-writing.md)。
