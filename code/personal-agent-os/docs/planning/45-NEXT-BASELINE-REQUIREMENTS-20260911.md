# PAOS 下一轮开发需求：独立安装、完整工作流与 Agent 易用性

> 版本：v0.2 · 2026-09-11 · **范围已批准，执行中**。冻结施工顺序与退出 Gate 见 [46 · 飞轮前最终基座收口](46-FLYWHEEL-READY-BASELINE-EXECUTION-PLAN-20260911.md)。
> 负责人：3002-s010 · PAOS 开发总管。执行与初审优先通过 CAT 交给 OpenCode / DS-H；主管负责取舍、独立复核和阶段放行。
> 目标：为下周开始的独立安装试用提供可靠基线，随后用真实工作验证 Workflow、Memory、Learning 三个飞轮。
> 关系：[44 号登记表](44-PAOS-REQUIREMENT-DEVELOPMENT-REGISTER.md)继续回答“做到了哪一步”；本文定义下一轮怎样做、怎样验收，不另建需求数据库。

## 1. 产品定义与本轮判断

PAOS 让人的长期工作脱离某一个 AI 会话：人提出目标，Agent 在原生环境执行，PAOS 保存可以继续、检查和交接的工作事实。

当前缺口主要不是底层对象不够，而是已经存在的能力尚未连成顺手、可分发的产品：两仓交付不同步，网页与指南仍带旧语义，Agent 常需自行拼接协议和唤醒配置，项目资料与需求状态也不够好找。

本轮应是**交付与使用闭环收口**，不是再扩建一轮平台。保留可靠性内核和现有数据模型，优先补入口、薄适配、清晰反馈与真实流程验证；局部代码结构确实妨碍实现时才做边界型重构。

### 已确认的用户与场景

- 新用户各自在自己的电脑安装，数据、Runtime 和模型由本人管理；不是多人共用这台 PAOS 服务器。
- Human 使用网页和自然语言，不使用 PAOS CLI。CLI 的用户是 Agent / Runtime。
- 第一任务：从空白安装开始，带一个真实目标进入 PAOS，让一个 Agent 完成小任务、留下成果，再由新原生会话接续同一个 Agent。
- 进阶任务：授权 Coordinator 后，让它组织工作、调用执行者、汇总已审成果，只把真正需要人的判断交给 Human。
- 沿用本地单机、泛用、灵活、轻量的方向。智能和主动性属于 Agent；PAOS 提供事实、权限、状态与可靠写入，CAT 提供临时交流，Runtime 负责执行和唤醒。

### 范围与非目标

下周试用入口先按 Windows 桌面网页规划；其他操作系统列入支持矩阵，未经实测不宣称支持。接入一种已验证 Runtime 即可完成首次使用，CAT 自动协作是可选安装项，但凡对外声明可用的自动模式必须经过冷启动验证。

本轮不做多租户、远程共享服务、权限平台换代、数据库迁移、全 Vault 搜索/RAG、知识图谱、证据评分、自动摘要入库、通用工作流引擎。也不因“每人一台电脑”而引入统一云端控制面。

## 2. 当前基线与已核对的问题

以下是 2026-09-11 本机快照，不继承旧汇报中的通过数字；远端 PR 最新状态另在实施前核对。
> 更新（2026-09-11 开工冻结）：远端基线确认为 PAOS `main@cf8a691`、CAT `master@7fcb4e8`；E04–E11 保留原核对，新增 E12–E16 作为本轮 Must 摩擦。

| 编号 | 实际观察 | 本轮处置 |
|---|---|---|
| E01 | 当前远端 PAOS `main@cf8a691`；其父提交 `ce0f54e` 为 PR #31 UI/文档基线，`cf8a691` 继续对账 44/45 状态。开发包为该主干的干净源码快照 | REQ-BASE-01 增加运行实例 build identity 与 Support Matrix；最终发布以 immutable tag 而不是“某个 main”作为锚点 |
| E02 | 已收口：CAT `master@7fcb4e8`（PR #17 merge，携带 origin/master@6da7dae 的 existing Participant self-rebind）；OpenCode adapter/指南/测试与 Hook setup/Reply 修复已合并；工作区仅 `.opencode-cat-logs` 未跟踪 | 双仓交付已对齐；M3 CAT 侧仍需独立安全验证与冷启动/夺舍验证后才宣称一般安全能力 |
| E03 | 44 表 R-05/R-08/R-12 已按合并后实况更新（本次登记；R-08 已合并、R-05 待独立验证）；Project 3002 摘要字段中 M3 的交付表述仍待修正 | REQ-BASE-01 执行时由 Coordinator/Human 修正 Project 摘要与交付说明；历史汇报保留 |
| E04 | `START-HERE.md` 第 7 节仍写 Continue 创建带 `continues_session_id` 的新 Session | 改为 M1A 的同一 sNNN 换 Runtime / 新 Cycle；指南不能教旧产品 |
| E05 | 真实新建 Agent 面板仍要求填写 Runtime，展示“H1 将改为 Runtime 自报”；还有禁用的 Continue existing agent 下拉 | 去掉实现计划文案与失效控件；核对 Open/Ack 合同后减少 Human 填写 |
| E06 | Project 3002 已有 Work↔Agent 连线和弹出式新建入口；但大量 ignored/accepted 建议仍在主页面展开渲染，Coordinator 卡有断行，多个 Continue 入口含义难区分 | 不再立项“添加连线/把新建表单折叠”；改做层级、语义和长内容布局 |
| E07 | Agent 详情已有本地 Mailbox 面板，但 Inbox 为空时总数仍为 1（来自 Recent）；active Agent 页面同时展示未标明旧 Cycle 的 Close 结果和历史 Ack 约束 | 分开当前职责、历史报告、待处理数；历史不能冒充当前执行指令 |
| E08 | CAT 浏览器中 Reply 会自动带目标，Clear reply 可移除预览；复制/折叠/多选已有。当前 s027/s029 使用相同绿色，旧消息标题仍是旧定位 | 已修部分进入发布验收；补色彩辨识及当前身份/历史身份说明，不重做整套聊天功能 |
| E09 | CLI 已有 Ack/Update/Close、Coordinator 派发等；`session show` 已能取得含 Mailbox 的详情，但尚无紧凑开工入口、独立 Artifact Add / Switch Work 命令 | 补 Agent 主链，不把“没有 mailbox 命令”写成“后端没有 Mailbox” |
| E10 | 真实 Project 文件表指向 CAT 根目录 `README.md`，本机该文件不存在；项目材料仍主要是纯路径清单 | 项目文档入口需要校验和维护；不能只堆更多链接 |
| E11 | OpenCode 指南明确 adapter 依赖 `fcntl`、只支持 WSL/Linux且无自启；`USER-AND-ARCHITECTURE-GUIDE.md` 仍含作者路径和旧 Focus 流程 | 支持矩阵必须按组件区分；不能把 Python 标准库依赖少写成“零安装” |
| E12 | 真实 Continue/夺舍曾观察到旧 Runtime/CAT activation 未完全退场，新旧 consumer 可能争抢 marker/消息 | B1 明确旧 execution 退场语义；C1 验证 CAT 单消费者 ownership，不以“给旧 Runtime 发退出消息”代替 binding 约束 |
| E13 | 更新代码后仍可能继续复用旧 PAOS 进程/资源，造成“新代码已改、浏览器仍表现旧行为”的误判 | A1 增加运行实例 build identity；B4 upgrade 必须验证服务与当前 checkout/release 一致 |
| E14 | Windows/WSL scope 路径与 CAT base 地址可能失配，人工修整 scope 容易形成环境依赖 | C1/B4 增加 scope/address 校验与恢复；优先从 PAOS 当前 projection 重建，不教用户手写完整 scope |
| E15 | Agent 在 WSL 等环境需要反复提供 PAOS base URL | B3 固化 `--base-url > 环境变量 > 本地配置 > 127.0.0.1` 的解析顺序；桥地址只作为配置值 |
| E16 | Continue 的 human-only 目前主要依赖 UI/authority 约定与 execution claim 兜底，Agent-facing 表面仍需明确禁止 | B1 保证 Agent CLI 不提供 Continue；B4 Gate 前验证 worker path 必须失败并裁决是否需要最小 route-level 保护，不扩成认证平台 |

浏览器范围：实际 Home、Project 3002、s010 详情、CAT Room；约 1265×712 视口。只打开面板和回复预览，没有发送测试消息、创建/关闭业务对象或执行 Continue。Clear reply 本次验证的是清预览与自动目标展示，不替代带正文、手动目标恢复、失败重试等完整验收。身份卡在 PAOS 数据加载后能显示正确定位，不能把加载初期的旧标签误判为永久失效。

## 3. 成功标准与关键工作流

### 成功指标

下表是建议验收目标，不是已有成绩。安装耗时、Token 与 Human 干预次数尚无可信基线，先在试用中记录，不承诺固定降幅。

| 目标 | 验收方式 | 建议通过标准 |
|---|---|---|
| 新人能独立开始 | 非开发者在干净用户目录/电脑按指南操作 | 无作者口头补步骤、不改源码、不填作者路径或固定 ID，完成首次任务与成果查看；运行实例可机械确认就是目标版本 |
| 工作可继续 | 同一任务换新原生会话 | sNNN、Work、Mailbox、文档入口保持连续；新 Runtime 不靠完整旧聊天完成下一小步 |
| 自动协作真可用 | 每种宣称支持的 Runtime 单独验证 | 正常空闲来消息、服务重启、Runtime 重连、主动停用后行为与文案一致；无消息时不创建模型回合 |
| Agent 协作更省事 | 对比同一任务的旧用法与新 CLI | 主链不手写 HTTP/schema，不全量拉取历史；报告请求次数、输出体积及人工转述次数 |
| 三飞轮被消费 | 同类真实 Workflow 连续使用两次 | Run2 显式复用 Run1 ≥1 个流程产物 + ≥1 条 Lesson；实际发生 Working Memory 接班；接班输入规模可测且小于对应旧聊天全文；本轮已关闭 E04–E16 / Must 摩擦复现数=0 |

### 关键工作流

1. **首次使用**：安装/启动 → 创建 Project 与一项 Work → 复制入场 Prompt → Agent Ack/工作/登记成果 → Human 看结果。
2. **主管委托**：Human 向 Coordinator 说明目标 → Coordinator 读当前事实、形成并保存执行方案 → 在授权内派发 → 执行者报告 → 主管验收 → 原文成果装配 → Human 处理保留的裁决。
3. **短会话接班**：保存当前 Working Memory → Human Continue → 新 Runtime Ack → 读取实时事实与当前 Memory → 可选 CAT rebind → 接续；CAT 失败不重做 Continue。
4. **资料进入项目**：指定材料 → Agent 判断用途与归档建议 → 在已授权目录内整理 → 登记 Artifact/修改摘要 → 项目页和下一任 Agent 都能定位当前文档。

## 4. 需求总表

优先级不是缺陷等级：**Must** 为首批独立试用及本轮承诺所需；**Should** 为本轮重要优化，不阻塞基础使用；**Later** 留待试用证据。对于可选 CAT 自动模式，相关 Must 是该模式的发布门槛，不要求每位新人先安装 CAT。

| ID | 能力 | 优先级 | 对应登记项 | 模块归属 |
|---|---|---|---|---|
| REQ-BASE-01 | 两仓发行与项目状态对账 | Must | R-05/08/12 | 发布、项目维护 |
| REQ-BASE-02 | 独立安装、升级与首次使用指南 | Must | R-09，新人交付 | 启动器、文档 |
| REQ-UX-01 | Project 主路径与视觉统一 | Must：主流程；Should：视觉细磨 | R-01/06/11 | PAOS/CAT 前端 |
| REQ-UX-02 | 新建、继续、结束 Agent 的语义闭合 | Must | R-02/04/09 | 前端、Context |
| REQ-AGENT-01 | Agent-first CLI 与紧凑开工信息 | Must | R-04/09/15 | CLI、读投影、Prompt |
| REQ-RUNTIME-01 | 一次配置、可恢复且可撤销的自动接入 | Must：声明支持的自动模式 | R-05/07/08 | Runtime adapter、CAT |
| REQ-CAT-01 | 回复、引用与长消息交互收口 | Must：已修交付；Should：筛选与引用增强 | R-11、g015 | CAT 前端 |
| REQ-DOCS-01 | Project 文档入口与当前版本导航 | Must：入口与定位；Should：资料整理辅助 | R-14、R-05a/b | PAOS 读投影、Agent |
| REQ-LOOP-01 | 主管式交付与三飞轮最小实用验证 | Must：示范闭环；Should：更多场景 | R-03/06/10、M4 | Coordinator 指南、试用 |

## 5. 详细需求

### REQ-BASE-01 · 对齐主干、运行版本与交付状态

- **触发/输入**：开始本轮开发与每次发布前，读取两仓真实 HEAD、候选分支、未提交改动和运行方式。
- **行为**：把每项差距明确分为已有能力、已有待发布候选、确实缺失、只有历史说法。M3 CAT 优先查找既有候选；M4 先对比当前 main，再决定复用哪些 Supervisor 合同，不能机械合并旧分支。
- **反馈与保存**：44 表保留实现/验证/使用验收，并把交付描述拆清“是否合并”和“运行来自主干还是本地补丁”。发布说明记录双仓版本、支持的 Runtime、未交付项和恢复入口，不再只写一串总测试数。
- **边界**：修正当前生成摘要和现行说明；原始需求、历史 Ledger/receipt、旧报告原文不改。架构意见和旧建议不自动升级为新实现要求。
- **验收标准**：新电脑取得同一发布组合能复现声明的功能；发布包不依赖 untracked adapter；R-05 等与当前发布状态一致；没有“本机有，下载没有”的必要功能。

### REQ-BASE-02 · 从别人的电脑顺利开始

- **触发**：首次安装、重复启动、升级现有安装。
- **行为**：提供一份中文主指南：依赖检查 → 启动 → 打开页面 → 第一个任务 → 成果验收 → Continue → 可选 CAT。Human 不运行 PAOS 业务 CLI；必要安装命令可由其 Agent 执行。
- **默认值**：沿用现有本机服务默认端口；安装目录、数据目录、PAOS/CAT 地址由本机实际配置产生，不嵌入 `remo`、项目 3002、固定原生会话 ID 或旧 WSL IP。单实例启动失败说明占用者/下一步，不按端口盲杀进程。
- **恢复**：缺 Python/选配 Node、端口被占、CAT 不在线时给出明确行动；已有数据不得被演示数据覆盖。升级有备份和回退说明，不能以清空业务历史换“干净基线”。
- **按需排障**：遇到 Windows 保留端口/WSL 地址变化时才检查相应事实；不能让每个新用户默认运行改系统端口或网络配置的修复脚本。Python、Runtime 与所选适配器依赖分别说明。
- **文档**：首次使用只解释目标、工作、Agent、成果；Cycle/claim/receipt 留给 Agent 指南与排障。支持矩阵区分 PAOS 基础、CAT 消息、运行期续步、重启后恢复，不能以某一列通过代表全适配。
- **验收标准**：至少一次非作者用户的全新安装试用；中文/空格目录可运行；没有 CAT 也能完成第一个 Work；升级演练保留 Project、Artifact、历史和本机自定义设置。按已声明平台验收，不临时扩展全部系统。

### REQ-UX-01 · 以人的任务组织页面

- **触发**：回到 Home/Project、查看工作关系、委托 Coordinator。
- **行为**：Home 可迅速找到近期/Pin 项目；Project 优先回答“现在在做什么、谁在负责、什么需要我、下一步怎么办”。Coordinator 主动作应是委托/继续沟通，不能只剩 Change 与历史入口，也不把全部后端动作平铺成表单墙。
- **入口**：复用既有 Room 的定向交流或复制语义 Prompt；没有已运行 Runtime 时如实提示进入方式，不把点击 Continue 当作发消息。明确人工动作仍可从页面完成，但已授权的例行动作由 Coordinator 自主执行。
- **显示**：保留现有 Work↔Agent 关系板；多 Agent 同 Work 时，Continue 必须指明目标 Agent。开放建议默认简短摘要；ignored/accepted 建议进入可展开历史，不占主流程。当前状态和历史原文分层。
- **视觉**：沿用低饱和深色工业/粗野主义方向，统一颜色、间距、字阶、表单、按钮和焦点状态；中文职责名不压坏卡片。主要动作有明确区分，不能仅用很暗的线条表示可点击。
- **验收标准**：真实长标题/长建议和合成空项目两组数据；1440×900、1280×720、390px 窄视口无页面级横向溢出和按钮遮挡；Work 与 Agent 的关系不依赖 SVG 也可读；键盘可到达/关闭弹窗；Current/History/Needs Me 不互相冒充。

### REQ-UX-02 · Agent 身份和生命周期说人话

- **触发**：创建 Agent、继续既有 Agent、查看详情、退出协作。
- **行为**：新建只要求人提供真正缺少的工作意图；继承 Work 的 Mission/Done When。Runtime/self-position 由 Agent 在已有合同允许的阶段自报；若当前 Open 必须要 Runtime，先做最小合同调整，不往后端写假值。移除禁用 successor 选择器和“H1 将……”文案。
- **继续**：明确“为 sNNN 生成接班 Prompt”，与“给当前 Runtime 发消息”分开。普通 pending_ack 只复制现有入场材料，Restore recovery 继续沿用现有 M1A 规则；不由 UI 代取新 claim 给旧 Runtime。
- **详情**：首屏给 Mission、Current Work、当前进展、Mailbox 待处理、当前 Memory/成果入口。Recent 数量不能伪装成未读数；历史 Close/Ack 标注所属 Cycle，默认下钻，不让旧边界覆盖现有权限。
- **退出**：沿用显式“结束 Agent 并退出当前 Room”的跨系统步骤，展示哪步成功、哪步待重试；不因退出失败再次 Close，不隐式关闭 Work或删除历史消息。
- **验收标准**：新建/active/普通 pending_ack/closed/Restore-rewound 均使用现有领域路径；当前 active Agent 不被页面误报已关闭；只剩历史责任时待处理数为 0；身份在 PAOS 与 CAT 都以稳定 sNNN 优先辨识。

### REQ-AGENT-01 · CLI 完成 Agent 主链

- **触发**：Agent 首次入场、领取新责任、阶段写回、登记成果与交接。
- **行为**：提供一个可发现的紧凑开工入口，复用现有 live Session/Mailbox/Authority/Memory/Artifact 投影。默认只输出相关当前事实、可用动作和按需入口；显式请求才展开全项目/历史。省下输出，不用静默截断隐瞒责任。
- **主链**：读当前责任 → 已授权领取/切 Work → 必要时 Ack → Update → dedicated Artifact Add → 按类型处理 Request → Close。优先补 Switch Work、Artifact Add、紧凑 Context/Mailbox 及已有 Request 更新路径；复用已有命令，不另造业务逻辑。
- **权限**：Coordinator 有独立治理命令；Human Continue/Reactivate、Decision 裁决、Coordinator 授权不因 CLI 可调用就变成 Worker 自主权。确需这些动作时返回明确人工入口，或由持有明确委托的 actor 走现行合同。不能让通用 `work create` 绕过应使用的 Coordinator 路径。
- **错误/重试**：成功返回对象 ID、operation、revision 与 receipt；失败有稳定机器可读错误、operation 和可恢复入口。中文/多行正文支持文件与 stdin；请求结果不确定时复用同一 operation，不能自动换 ID 重做。409 先分清 revision 与任期冲突，不自动刷新 execution claim。
- **边界**：CLI 只薄包装 PAOS canonical REST；不直接写项目 JSON，不调用 CAT，不承担模型思考或流程调度。`PAOS_BASE_URL` 已有，不重复立项。
- **验收标准**：新 Agent 只读紧凑入场材料与 CLI 帮助即完成一条真实主链，无手写 HTTP/schema；旧 Runtime 的 claim 仍被拒绝；失败/重试不重复创建；记录相同任务的输出体积与调用数，不用测试数量替代效率证据。

### REQ-RUNTIME-01 · 安装一次，重启可恢复，接管不抢单

- **触发**：用户选择启用自动模式、重启本机/服务、Runtime 改端口或被新 Runtime 接管。
- **行为**：统一语义要求，分别给 Codex、DS-H、OpenCode 指向其真实适配指南；让目标 Agent 自行选择本机合适机制。一次授权后保留配置，下次从固定入口恢复，不让人每次重贴长 Prompt。需要自启时属于明确选配，不能由本需求自动注册系统服务。
- **配置来源**：scope 来自 Room/Participant 的正式投影；缺失时修复该投影或给出明确诊断，不教新人手造带固定地址的 scope。Runtime 模型、身份与路径在本机验证，不依赖作者的模型别名或私人配置。
- **归属**：Room/Participant 保持稳定；原生 locator、连接和消费权由 adapter/Runtime 管理。接管后旧消费者必须停用或被识别为不再有效；不能靠向同一 Participant inbox 发“旧 Runtime 请退出”来解决双消费者抢收。
- **M3 前置**：self-rebind 先验证 Room project ownership、existing participant 和 same-ID 更新；不存在/跨项目不创建替代 Participant。PAOS Continue/Ack 成功而 CAT 失败时仅重试 CAT 部分。
- **恢复与反馈**：分别显示已配置、adapter 最近观测、待消息、已投递、已 ack、失败原因和时间。连接失败不能自动 ack 或把 marker 丢掉；无消息时不唤醒模型；Room 长期存在不等于 Runtime 永远在线。STOP/暂停/解绑优先于重连恢复。
- **验收标准**：按 Runtime 支持矩阵各跑空闲消息、服务重启、Runtime 重启/换端口、同一 Agent 接管、重复投递、主动停用六组场景；接管时同一消息不由新旧 Runtime 各处理一遍。Windows 不反复弹终端，不依靠模型每次轮询耗 Token；故障由一次可理解操作恢复或清楚标出不支持项。

### REQ-CAT-01 · 整理消息，而不是再造聊天系统

- **触发**：回复、清除引用、阅读长对话、多选整理、寻找相关上下文。
- **行为**：先发布并验收已有 Clear reply / auto-target 修复；Clear 取消 reply 关系但保留用户正文，自动目标和手动目标按已定状态恢复；回复布局靠右、新话题靠左，由 `reply_to` 而非发送者身份决定。
- **辨识**：发送方→接收方文本一直可见；同 Room 常用参与者避免颜色碰撞，颜色不足时配合稳定 ID/标记，不靠颜色唯一识别。历史消息可保留历史定位，但明确其 sNNN 当前对应谁，不改写消息证据。
- **增强**：单条复制、多选引用和折叠复用现有功能；补引用来源跳转、基本参与者/文本过滤。Work/行动类型只在有显式引用/字段时过滤；没有结构化来源就标未关联，不靠关键词猜关系。
- **结论交接**：选择消息后可把原文引用与目的定向交给 Coordinator；是否登记 Suggestion/Decision/Artifact 由 Agent 按权限判断，CAT 不自动“提升事实”。
- **验收标准**：Reply→编辑→Clear、Reply→调整目标→发送、多选引用→复制、部分发送失败→重试均可恢复；真实长消息和 500+ 消息 Room 不遮挡 compose；筛选可恢复全部；历史消息/ack 不被 UI 整理改变。状态机测试外必须有浏览器点击验证。

### REQ-DOCS-01 · 每个项目有可靠的资料入口

- **触发**：建立项目工作区、加入新材料、修改已有成果、Agent 接班。
- **行为**：项目页显示文档工作区入口、当前关键成果与待整理材料入口。优先使用现有 key_files / Artifact heads / source refs；确实缺少机器可读根目录时才加最小项目字段，不另建目录数据库。
- **默认/边界**：根目录由本机用户指定；待整理目录可空，不默认监控全 Downloads 或 Vault。Obsidian 是一种好用的文件组织方式，不成为安装依赖。飞书可继续承担对外主稿，PAOS 要说明材料角色，而不是要求全部复制回本地。
- **整理**：Agent 在指定范围理解、命名、建立链接；已授权的普通整理无需每个文件再请示，范围外移动、覆盖和删除保持原有批准要求。修改已有登记成果后复用 M5A replaces/change_summary，外部版本坐标可选，不增加 digest/正文归档要求。
- **反馈/恢复**：网页提供打开受支持 URI 或复制路径的明确动作；浏览器无法直接打开本机目录时不能假成功。失效路径可指出并修正，多个 lineage head 显示待择，不按 mtime 猜最新。
- **验收标准**：用 LRC101 现有文件体系作为样本而非模板，另用一个新空项目验证：指定材料→整理→登记→修改→接班检索。新 Agent 能找出当前文档、修改摘要和原始来源，不必遍搜 Downloads；不额外创建第四套“当前真相”。

### REQ-LOOP-01 · 用真实工作验收三个飞轮

- **触发**：上述主链可用后，选择一项会重复做的真实任务。
- **Workflow**：核对 M4 候选是否仍符合当前合同；采用紧凑任务包、阶段产物、主管验收、原文装配。计划可随证据调整，不增加固定阶段对象/后台调度器；例行阶段由主管放行，只有明确 Human gate 才要求人逐次确认。
- **Memory**：每次交班保存当前工作状态、已定/未定、失败路径和下一步入口；下任先读 live facts，再按需读 Memory。不要把哲学全文、全部日志或所有 Skills 塞进每轮 Prompt。
- **Learning**：挑一条真实纠正，形成有触发条件的小 Lesson/Skill/测试，并在下一次任务实际使用。先复用既有文档和 Artifact；不新建 Learning 数据库。
- **验收标准**：同一类任务做两次；保留第一轮经审阅的文件，第二轮明确引用并复用，不凭长聊天重新生成。记录 Human 转述/催办/裁决次数、接班输入规模、耗时和重复错误；如第二轮没有更省，给出具体原因并删减无效步骤。所有正式结论仍带实际来源，不按自报宣称通过。

## 6. 串行实施与阶段验收

| 阶段 | 输入与任务 | 交付物 | 放行标准 |
|---|---|---|---|
| A · 事实与发行盘点 | 双仓 HEAD/dirty、M3/M4 候选、44 表 | 逐项复用/补齐清单、发布组合、旧文案修正范围 | 主管确认无重复建设，无未解释的必要本地补丁 |
| B · 一人一 Agent 主链 | A 的确定基线；REQ-BASE-02、UX-01/02、AGENT-01 | 独立安装入口、主页面、CLI 主链、中文首次使用指南 | 空项目真实首次任务与接班通过；不要求 Human 学协议 |
| C · 多 Agent 与资料 | 已验收 B；REQ-RUNTIME-01、CAT-01、DOCS-01 | Runtime 支持矩阵、CAT 收口、项目资料入口 | 一种受支持 Runtime 的冷恢复与 takeover 通过；资料接班可用 |
| D · 整体打磨与试用发行 | 已审 B/C 文件；REQ-LOOP-01 | 真实浏览器 QA、两次工作记录、发行说明和用户指南 | 外部用户完成首任务；实际安装代码与审过的版本一致 |

阶段之间串行放行。同阶段只有不同仓/文件且没有语义依赖的任务才并行；不让多个 Agent 同时改同一前端文件。每个执行任务指定输入版本、路径、完成标准和不能碰的区域；初审与主管验收分开。

短期分支 → 聚焦测试/必要全量 → 独立审查 → PR 合并 → 本机运行验证 → 更新 44 表。发布时一次检查最终代码组合；没有变化且环境一致的可信测试不反复重跑。最终交付装配已验收文件，不再生成一份“类似的最终版”。

时间不足时，下周先交 **B 阶段基础试用版**，明确 CAT 自动模式的支持状态；不能把未验收的 C 当默认能力。完整本轮完成点仍包含 C/D，而不是通过改名称把欠项消失。具体实施排期由阶段 A 的候选差异量决定，不先承诺固定开发天数。

## 7. 验证、异常与发布要求

- **行为优先**：领域不变量继续由现有 Store/合同测试保护；前端点击、键盘、失败重试与冷启动必须实测。不得再用字符串源码断言或 HTTP 200 代替交互验收。
- **失联可恢复**：PAOS 无响应时禁止新的业务写入并保留草稿；CAT 无响应不影响 PAOS 已成功写入。恢复后按 receipt/operation 对账，不重复创建对象。
- **版本可追踪**：每份验证写明 exact commit、是否含未提交补丁、环境和实际场景。开发/初审/独立验收/已发布/真实使用分别陈述。
- **数据分离**：发行只带空数据或可撤销的合成示例，不带当前 3002/2001、Runtime binding、日志和个人配置。旧用户数据原地保留，通过既有 API 整理当前投影，不抹历史。
- **结构维护**：只统一确有重复的 UI 组件、错误呈现和 adapter 接口。EOL 用独立机械提交处理，不混业务逻辑；不能根据旧“66 文件”汇报清理当前 5 个真实改动。
- **用户指南成果**：一份人用快速开始；一份 Agent 入场与动作入口；按 Runtime 分开的适配页；一份常见失败恢复。页面、指南、发行文件名与实际功能同步，不强迫新人阅读开发史。

## 8. 依赖、风险与开放问题

| 问题 | 当前假设 / 风险处理 | 关闭责任与时点 |
|---|---|---|
| 新用户的系统和 Runtime 尚未逐人确认 | 首批 Windows；基础手动接入与至少一种完整验证的自动模式分级。Mac/Linux 不借 Python 可运行就宣称完整支持 | s010 在阶段 A 排期前确认；不阻塞本需求评审 |
| M3 CAT 与 M4 候选的当前远端状态 | 本文只确认本机缺口；实施前读取实际候选树，决定复用，不从旧汇报猜 merge 状态 | 执行 Agent 核对，s010 验收 A |
| 当前 CAT 委托是否被正确 Runtime 消费 | 本轮已收到 p027 初审，但单次回报不能证明冷恢复/旧消费者退出。旧/新 Runtime 共享 inbox 的抢收是待解决输入 | Runtime 维护者在 C 验证 |
| 新人价值和易用性尚未验证 | 让非作者完成真实任务，观察其是否愿意第二次继续；不能以页面更漂亮代替这一点 | 首批试用者与 s010，D 阶段 |
| 工期/维护成本 | 先复用已完成能力与候选，按 A→D 收口；不建立需要持续人工维护的新索引体系 | s010 按每阶段结果调整，保留删减权 |

Agent↔Agent 带目的连线保留为 Later：目前执行连线已存在，交流先用显式定向消息/Request 完成；积累真实使用后再决定是否需要图上建边。复杂筛选、跨项目知识检索和全面跨平台安装器也不挤占首次使用主链。

## 9. 证据与接续入口

- 需求状态：[44 号登记表](44-PAOS-REQUIREMENT-DEVELOPMENT-REGISTER.md)、[43 号收口审查](43-PRE-CLOSEOUT-PLAN-REVIEW-20260910.md)。
- 当前哲学：[产品与设计哲学](../PRODUCT-AND-DESIGN-PHILOSOPHY.md)、[开发准则](../DEVELOPMENT-PRINCIPLES.md)。哲学是待真实证据检验的判断，不是禁止改进的僵硬清单。
- 当前指南：[START-HERE](../START-HERE.md)、[README](../../README.md)、[权限矩阵](../AUTHORITY-MATRIX.md)。本文 E04 已指出首次使用中的过时语义。
- CLI：`scripts/paos.py` 的命令注册、`test_paos_cli.py` / `test_paos_cli_tenure.py`；没有在本轮重新跑完整测试。
- 本机页面：[Home](http://127.0.0.1:8766/attention-dashboard-v1-static/projects.html)、[Project 3002](http://127.0.0.1:8766/attention-dashboard-v1-static/project.html?id=3002)、[s010](http://127.0.0.1:8766/attention-dashboard-v1-static/session.html?id=3002&session=3002-s010)、[CAT Room](http://127.0.0.1:8770/room.html?id=room-e7f0cfaa5c5f)。
- CAT 只读核查任务：`x-7e50ccb74f7f`；p027 报告 `x-20cef8140ac9` 已收到并由 s010 复核。采纳 CLI、dirty/M3、个人路径、重启和平台限制；不采纳“零安装”“PAOS 没有首次使用步骤”“新电脑大概率重踩端口”等过度结论。以上是初审和静态事实，不是新版本通过证明。

本稿已进入批准实施状态；完成与发布状态只按 44 号登记表、exact PR/commit、运行验收和最终 release 证据更新。
