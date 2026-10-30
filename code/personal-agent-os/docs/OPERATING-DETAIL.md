# Operating Detail — 详细能力与运行说明

> README「How agents actually keep working」的详细展开：安装 CLI 的真实公开读面、业务循环如何真实发生、可替换 Runtime 与通信边界、前端接口地图。版本/验收证据不做重复：见 [`V1.2-BASELINE.md`](V1.2-BASELINE.md)。
>
> 适用范围：本机单人参考实现。命令与路径以**当前安装探测所得为准**（本页示例均为实跑/帮助文本核实记录）；未实现的能力如实写明，不把方案写成功能。

## 1. 一图看懂分层

```text
Human（唯一授权源：阶段放行 / 工作语义 / 模型策略 / 例外）
  │
  ├── Rooter ──── 具 Human-equivalent 运营权限：安装、Library 登记、生产采用、
  │                跨主机激活处理属其职责；默认不代写成员专业内容（分工，非权限墙）
  ├── Coordinator（每 Project 一个）─ 业务意义：统筹业务语义、定向 Request、收拢成员结果（无 Work 生命周期）
  └── Agent（固定工位主人）───────── 按授权执行；本人 TODO 与交付自述；Ack/自查由本人完成
        │
        ├── 文件事实层（真实位置）：
        │     Project JSON ── 业务唯一 Store（业务对象/事件台账；HTTP 读面直读它，
        │                      写变更经 Store 合同——GET 只是读，不走变更事务）；
        │                      位置由 installation descriptor / data root 决定，不打包在 Project 目录里
        │     Workstations/<agent>/ ── 固定工位：ENTRY.md + TODO.md(paos-todo/v4) + mailbox/ + notices/
        │     .paos/（按机器/项目两侧）── mail dispatch、native injection 绑定/状态（当前代号 contact native-targets，
        │                      C:/Users/<u>/.paos/wakeup-native/opencode 或 runtime 级对照路径）、CLI config、
        │                      installation descriptor、library-roots（后三者在用户 ~/.paos）
        │     PAOS-Libraries/{workflow, skill} ── 共享库（registered）
        │
        ├── 通信：
        │     Mail（持久）──── mail send 仅落信；agent send / agent notify 落信后请求一次 self-contained Notification
        │     CAT Exchange ── 房间协作（默认 8770），只调事实/约束，不替代授权目标
        │     原生注入（提醒）─ contact native-target bind/status/unbind/trigger（独立提醒；成功即止，失败如实）
        │
        └── 指南（软规则）──── Workflow/Skill Library 单正文；入口引用；不是后台调度
```

**谁判断**：Human > Coordinator（业务意义）> Agent（本人责任内）。
**谁存事实**：文件（Project JSON / 固定工位 / .paos / 共享库）——没有内存记忆库；Project 文件与 Git 保存成果。
**谁执行**：原生 Runtime；PAOS 不做推理。
**如何回流**：Agent 产出落盘（Project 工件/Git）→ durable Mail → 下游在自己的会话里实际消费 → 交付/审阅经 Home 的 Current 与正式 Mail 收口 → Project JSON + 操作回执。
**无 Work/Cycle/ACK 前置**：责任形式为长期固定 Home（`Workstations/<agent>`）+ 本人 Current（`paos-todo/v4`）；正常路径不再有 ack/Work 交接/换 Work/COME 等动词，业务责任由本人 Current + 正式 Mail/Notice 呈现。

**绑定（Workless）当前语义**：`paos wake` 是独立的联系底面——bind/status/unbind/trigger 四动词；trigger 为一次性原生注入提醒且**成功即止失败如实**（无探针/恢复/停机/自检，这些旧 attempt 动词在 CLI 上已显式退役）；无前置 Work/Cycle/ACK。

**绑定的当前实况（事实，不锁数量）**：本安装下 OpenCode 绑定多个（两项目共 6 个：2001×3、3002×3），服务数与绑定数不必相等（双 OpenCode systemd 服务 + TUI 监听 + Codex Desktop 本地应用）；数量演进以 `paos team/peers`、`wake status` 实读为准。

## 2. 安装 CLI —— 真实公开命令面（依现装 --help 核）

安装位置：Windows `C:/Users/remo/.paos/bin/paos.cmd`；WSL `/home/remo/.local/bin/paos`。`paos status` / `paos install show` 可核"运行=安装"（`matches_running_cli`）。

`Guides/guide-paos-cat-operations`（共享 workflow 根下实际路径 `Guides/guide-paos-cat-operations.md`）
顶层面板：`health, home, ports, orient, status, inbox, attention, peers, team, agent, wake, mail, library, config, install, authority, relations, needs-me, project, session, coordinator, workstation`。（`work` 单独主题、`workstation preflight/prepare`、旧 claim/v2 领取命令均已退役，不再出现在帮助。）

### 2.1 读面子命令

| 命令（实有子命令） | 用途 |
| --- | --- |
| `orient <project> <agent>` | 一页恢复：身份/TODO 当前责任（无 live Work）/Mail/Request/Issues/Next 建议 |
| `status <project> <agent> [--message-id]` | 安装一致性/runtime、当前责任、联系面、外发 dispatch 状态 |
| `inbox <project> <agent>` | durable Mail 与正式 Request 分开读 |
| `peers` / `team <project> <agent> [--probe]` | peers=live active session；team=固定工位长期名册；真实在线状态带 `basis`/`checked_at` |
| `relations`、`needs-me` | 关系投影 / 严格 Needs Me |
| `project show`、`session show/context/mailbox`、`attention show`、`v3: home/ports` | 各层事实与回执读面（无 work show） |
| `mail list/read` | 落盘信正文审读 |
| `mail status` | 查 immutable dispatch 收件投递态（纯读无副作用） |
| `library catalog/roots show`、`authority` | 共享库目录/根；动作权限清单 |
| `install show`、`config show`、`health` | 安装描述符（读）；连接配置读（变更用 `config set-base-url`=写） |
| `wake status` / `wake bind/unbind` 读面 | status=纯读（contact native-target）；probe 已退役（状态由 contact native-targets 提供） |

### 2.2 写面子命令（副作用；幂等回执）

| 命令（实有子命令） | 说明 |
| --- | --- |
| `mail send` / `agent send` | mail send 仅持久投递；agent send 持久投递后**尝试激活**（两阶段，回执分离） |
| `agent notify` | 对**已落盘** durable source 补激活一次；不重投正文 |
| `agent chat` | CAT 房间定向消息 |
| `mail reply/handle` | 回信 / 处理标记（handled/incorporated；均为写） |
| `session update(report)/artifact-add/close/submit`、`session request-create/request-resolve` | 进度/工件/交接/收尾与 Request 建结（均写；正常路径无 ack/Cycle/Work claim 前置） |
| `wake bind/status/unbind/trigger` | 原位联系面四动词（一次性原生注入提醒；成功即止失败如实）。`probe/recover/stop/test` 自 help 面整体退出（调用返回 invalid choice）；无 attempt 状态机 |
| `library init/roots set/skill-use`（`config set-base-url`、`install configure` 同为写） | 登记根/记录 skill 使用并重建统计 |
| `workstation init/show/guide-diff`、Coordinator 专用 `coordinator guide-promote/request` | 工位初始化/实文件 Guide 差分与 canonical 晋升/定向 Request（coordinator work-create/transition/release/assign/review-setup/abandon 均退役） |

**注意**：Mail 同 message_id 不同内容会被拒（`mail_message_id_conflict` 实证）；`agent send` 返回中 `delivered` 与 activation 状态分列。

## 3. 完整业务循环（叙事，非仅状态表）

一次获批阶段的真实次序（以 w061 获批稿与 w060 验收证据为样本）：

1. **Human 目标**：在终端/Rooter 原生会话里提出要什么。
2. **成员调查与个人 Current**：相关 Agent 各自实读固定工位 Entry/共享 GUIDE/当前对象来了解，填报 work-stream Current（含需要 Human 判定的点）——不做实施。
3. **统一批准**：Rooter 汇总给 Human，一次 PASS（原话作为批准证据；批准稿另存 history）。
4. **直接协作、自主实施**：各成员按分工实际动手（不逐小项再申请）；同工种直连同事，普通问题不绕汇总。
5. **下游接续（而非"已交即完成"）**：交付者 durable 送达 + 原生注入提醒；**下游自己会话里实际读取/开工**才算接续——失败保留异常和人工入口，不无限重试，也不把"已交"当"已接"。
6. **收口**：Reviewer 独审（对当场文件），Handle/Archive 正式处理，Rooter 从生产侧读取回执。每个箭头有各自证据；状态词表是辅助注解。

| 证据词 | 对应物 |
| --- | --- |
| delivered | mailbox 文件 + dispatch JSON（sha256；幂等拒绝同 id 异文） |
| woken / triggering / uncertain | contact native-target 状态与每次注入回执（成功即止失败如实） |
| consumed | 下游原生会话的 message/tool 记录 |
| accepted | 项目级正式 Mail/审阅回执（无 Work transition；证据为对象 home处的 Current/审阅记录） |

**扰动样本（两个事件分开叙述、各按证据引用；不合成无出处成功故事）**：

- **事件 A（断点处置）**：早期一次 handoff 实际使用旧生产 CLI 的 `mail send`（仅落信、无激活），下游未自动消费；Rooter 在核实实际 mail 已落盘后，以**同一 message id** 执行一次 `agent notify` 补激活。这属于“发现断点→处置断点”的恢复动作：**不是**链路自我修复，**也不会**被当作今后所有交接的修复模板。（证据：`Works/V12-STAGE2-FRESH-HANDOFF-CORRECTION-S027-20260930.md` 与 Rooter `V12-STAGE2` 系列已接受报告。）
- **事件 B（规范重做）**：随后按批示以**新 message id** 的 `agent send` 重新发起交接（原 dispatch 不可变保留）；下游在自己的原生会话实际读取并产出业务结论，Coordinator 实际消费后收拢。（证据：dispatch `msg-3002-w060-strict-fresh-handoff-agent-send-s027-20260930`、Project `Works/` 下 s029 业务 verdict。）

两个事件的原始回执均保留；人工补激活不写成“已自动修复”。


## 4. 可替换 Runtime 与支持边界

| driver | 绑定含义 | 支持 | 边界（如实） |
| --- | --- | --- | --- |
| `opencode` | exact Server base_url + native session id | HTTP prompt_async→204 受理 + 原生 assistant 回合观察；跨 Windows/WSL 共享状态目录 | Wake 不指定 model；204=受理不是完成 |
| `codex` | Codex Desktop 本地 thread | 无外部 shell attach；本机内人用 Desktop；有 Codex 原生导航工具的 Runtime 可对准 thread（导航≠Wake） | WSL 侧 Wake 失败根因=缺 caller 凭证（CODEX_APP_TOOLS_PIPE_PATH/CODEX_THREAD_ID）；换 Windows Python **不**解决（r052 诊断）；薄宿主授权入口"方案已提出、当前未存在" |
| `manual` / mock | 显式工具/测试 | 声明用途 | 不冒充真机 |

Runtimes 可替换的含义是"固定工位+持久事实不变，绑定可以重指 native 会话"；不是"任意两 Runtime 互当对方身份"，也不是"自动在所有宿主间无差别唤醒"。

## 5. 前端接口地图（现有 HTTP 读面实表；web 说明详细到路由）

HTTP 读面（GET）与变更面（POST，经 `mutate_v2` 原子合同）由 `attention-dashboard-v1-static` 提供；入口默认 `http://127.0.0.1:8766/attention-dashboard-v1-static/project.html?id=3002`（README 同源的 projects.html 总览）。

### 5.1 GET 读面（真实路由，本项目实测可达）

| 路由 | 内容 |
| --- | --- |
| `/api/health` | 服务/构建信息 |
| `/api/projects`、`/api/projects/{id}` | 项目列表/详情主数据（详情即 Store 的可读视图） |
| `/api/projects/{id}/sessions/{sid}` | Session 详情 |
| `/api/projects/{id}/office`、`/needs-me`、`/relations`、`/lifecycle-findings`、`/stewardship` | 需人清、值班、工作关系、治理发现、主管视图 |
| `/api/projects/{id}/team` | **TEAM 联系面**（`paos-contact/v1`） |
| `/api/identities`、`/authority`、`/portfolio`、`/focus`、`/preferences` | 身份 / 权限词表 / 跨项目视图与偏好 |

### 5.2 POST 变更面（写入走廊：project_store 的 mutate_v2 与窄写适配 `_narrow_agent_write`；幂等 operation_id + 乐观锁 revision）

| 路由族 | 语义 |
| --- | --- |
| `/api/projects`（建） | Project 维护 |
| `/sessions`（开）、`/sessions/{sid}/updates/close` | Session 走廊（无 ack/abandon 前置） |
| `/coordinator/*requests|tagline`、grant/revoke-coordinator | 主管治理（无 Work 生命周期路由；请求/标签线保留） |
| `/api/agent/project-*-update` | 成员对项目窄写口径 |

**Mail/Wake/agent send 运作不在 HTTP 面**：它们是文件/CLI 层动作。前端只读取 `/team` 接口后显示 attach/manual-open 命令文本，不代替人执行。

### 5.3 前端三个"不要"（读面里设立后，另有缺口列表）

1. 不把 TEAM 名册=在线；`team` 的 `session_status` 与 `runtime_contact.online_state`（含 `checked_at`/`state_basis`）分列显示。
2. 不把任何一对一状态推给"全员下线"；固定工位（在岗）与业务收口是两套字段。
3. 不在页面里制造「通知已送达=对方已开工」口径：四态在当前接口层尚无统一现成字段，需各自证据组合；覆盖不到的如实 unknown。

## 6. 与现有文档的分工（单一正文原则）

只读概念: [`ARCHITECTURE.md`](ARCHITECTURE.md)。[`DOMAIN-MODEL.md`](DOMAIN-MODEL.md) 与 [`THREE-LAYER-MODEL.md`](THREE-LAYER-MODEL.md) 为**历史设计稿**（含旧 Session=原生会话/员工接续链与三态 Work 等旧口径），仅解释历史；现行对象/状态以 [`V1.2-BASELINE.md`](V1.2-BASELINE.md) 与本项目合同为准。首上手: [`START-HERE.md`](START-HERE.md)。员工身份链历史概念（旧员工链 `continues_session_id`；仅解释历史数据与该 Store 字段，**不作为正常接班入口**——正常继续=固定工位 ENTRY/TODO + orient，现行恢复口径见 [`V1.2-BASELINE.md`](V1.2-BASELINE.md)）: [`SESSION-CONTINUITY.md`](SESSION-CONTINUITY.md)。本页第 4 节的 Wake/binding 是独立的跨会话续用机制，不依赖员工链，两者不相互替代。Needs Me 专题: [`NEEDS-ME.md`](NEEDS-ME.md)；支持边界: [`SUPPORT-MATRIX.md`](SUPPORT-MATRIX.md)。恢复与诊断: [`../RECOVERY.md`](../RECOVERY.md)、`runbooks/*`（本页不重抄其内容）。已退役机制（如旧 `agent_working_memory` 等）按 [`../VERSION_HISTORY.md`](../VERSION_HISTORY.md)（根级实存；另有 `history/VERSION_HISTORY.md` 历史快照）与 V1.2 基线指准。
## 7. 诚实边界

- "自动"＝每位 Agent 用命令逐一显式推进，且有证据记录；PAOS 无后台守护/轮询/哨兵。
- 页面只是控制面；磁盘上的 Store JSON、工位文件、Mail 才是事实。
- 未实现/未决不隐藏：见 [`V1.2-BASELINE.md`](V1.2-BASELINE.md) 与当轮 RESULT；前端可用面与缺口的当轮目标在第 5 节。
