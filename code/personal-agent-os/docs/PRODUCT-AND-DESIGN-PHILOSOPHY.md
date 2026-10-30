# PAOS / CAT 产品与设计哲学

> PAOS / CAT 不只是一个项目管理工具和一个多 Agent 聊天插件。它们是一场关于“需求能否被持续编译成个人软件”的长期实验。

V1.2 围绕长期 Agent 的责任与协作运行。原生对话和执行实例可以更换，成员身份、项目责任与已接受的成果继续存在。本文定义产品原则；已接受版本、实际采用、已知缺陷与历史方案的边界见 [V1.2 长期基线](V1.2-BASELINE.md)。操作参数以同版 CLI 与已安装共享指南为准。

## 1. 从旧版 PAOS 得出的开发哲学

回看旧版 PAOS，我认为它真正建立起来的不是一套页面或 API，而是一组越来越清楚的开发判断：

> **状态先于调度，语义先于自动化，证据先于叙述，边界先于能力，真实使用先于架构。**

### 1.1 状态先于调度

旧版最早容易把“Agent 正在做什么”当成系统中心，后来才逐渐确认：真正需要长期保存的是人的工作状态，以及长期 Agent 的身份和责任，而不是某段原生对话的运行状态。

```text
Work    = 人的长期工作事实与验收对象
Agent   = 可持续承担责任的团队成员
Runtime = Agent 当前思考、使用工具和写入的执行实例
原生会话 / 旧 Cycle = 可追溯的执行经历，不是续任许可
```

因此：

```text
Runtime ended != Agent left the team
Work completed != Agent employment ended
Agent reported done != Work accepted
```

一个 Work 可以暂时没有 Agent 接手，仍然保持 `doing`；一个 Agent 也可以在队待机而没有当前 Work。系统应显示这些事实，不能借“自动整理”之名替人改变工作的含义，也不能为了维持成员身份而制造占位 Work。

### 1.2 语义先于自动化

自动化不是越多越好。只有当动作的语义已经稳定，自动化才会减少成本；语义不稳时，自动化只会更快地产生错误状态。

旧版 PAOS 的真实教训是：Session Close 曾经会推动 Work 状态，Agent 自报曾经容易被误当成人类承诺，Coordinator 的权限也曾经比职责说明更早出现。这些都不是技术能力不足，而是动作含义没有先说清楚。

所以 PAOS 的开发顺序应该是：

```text
人的原始意图
  → 领域语义
  → invariant
  → 可执行合同
  → 状态变更
  → 自动化
```

不能倒过来从“Agent 能调用什么”推导“Agent 应该替人决定什么”。

### 1.3 证据先于叙述

Agent 很擅长总结，但总结不是事实本身。PAOS 必须区分：

- 当前事实：Project、Agent、Work、Decision 与当前执行绑定的现状；
- 提案与推断：Agent 认为下一步应该怎样；
- 历史证据：Ledger、receipt、Close 结果和 Artifact；
- 原生过程：Agent 自己的完整 Session 日志。

项目摘要可以重写，提案可以被拒绝，当前状态可以迁移；但“某时某刻发生过什么”不能被事后叙述覆盖。

这也是为什么个人本机软件仍然需要 revision、operation_id、receipt、append-only Ledger 和 Restore：它们不是为了模仿企业系统，而是为了让 Agent 的高执行力不会冲掉人的真实历史。

### 1.4 边界先于能力

PAOS、CAT 与 Runtime 的分离不是代码洁癖，而是产品语义：

```text
PAOS    = durable truth / governance kernel
CAT     = transient collaboration transport
Runtime = reasoning / tools / execution
```

PAOS 回答“这件事现在是什么状态”；CAT 回答“这些 Human / Agent 如何交流”；Runtime 负责真正干活。

Room 可以关闭，Participant 可以退出，Codex 或 DS-H 可以离线，但 Project、Work、Decision、Evidence 与 Authority 仍应存在。CAT 因而必须是插件，而不是逐渐长成 PAOS 内部的第二套工作系统；Runtime Adapter 也只是驱动，不应变成新的事实源。

### 1.5 真实使用先于架构

旧版 PAOS 很多有价值的设计都不是预先规划出来的，而是从真实摩擦里长出来的：

- Work 与 Session 解耦，来自“Agent 做完不等于工作完成”；
- Coordinator，来自人类被夹在多 Agent 之间做行政转交；
- CAT，来自 Agent 之间需要交流、纠错和达成结论；
- source_path，来自总控需要查看另一个 Agent 的工作细节；
- Agent 身份合同，来自多个 Participant 都叫 Manual；
- Event Bridge，来自 Stop hook 无法唤醒完全空闲的 Codex；
- obsolete test 分类，来自“通过的测试也可能在保护已经死掉的产品约束”。

因此 PAOS 不应靠想象一次性建成“完整 Agent 平台”。每一层都必须回答：它解决了哪一个已经出现的真实摩擦？完成后用户具体少做了什么、多看见了什么？

### 1.6 Agent 的摩擦也是需求来源

真实使用不只是人类的使用。Agent 在 PAOS/CAT 里工作时撞到的摩擦——合同歧义、字段名记错、端口不通、醒不来、看不见自己的状态——同样是需求信号，而且往往比人类的更早、更密。

因此：

- Agent 发现自己反复绕路、重复踩坑、或用「看起来成功但其实失败」的方式掩盖问题时，**应当主动记录**到当前工作页、协作讨论或项目摩擦记录，而不是默默绕行；
- 记录不是立即可做清单：先攒着，阶段性由人类或 Coordinator 评审——值不值得改、什么时候改，由治理节奏决定；
- 判断标准不变：它解决了哪一个已经出现的真实摩擦？谁的负担因此变小？

这条把「摩擦驱动」从单向（人→系统）补成双向（人 + Agent→系统）。

## 2. PAOS 不是任务管理器，而是个人工作的状态内核

PAOS 最核心的业务关系可以保持克制：

```text
Project → Team / Agent ↔ Work → Evidence / Receipt
                    ↘ 当前执行实例（运行绑定）
```

当前执行实例只说明谁此刻代表这个 Agent 写入，不续签 Agent 的身份、岗位和 Work。PAOS 不把人的生活变成更多行政对象，而是让长期工作不再寄生于任何一条聊天记录、某个模型或某次运行。

核心原则是：

> **Agent 可以执行和维护事实，PAOS 保存可追溯状态，人拥有最终工作语义。**

“OS”的含义正在这里：它提供一个稳定状态空间，使 Agent 可以更换、暂停、接力、协作和失败，而人的工作仍能继续。

### 2.1 Project 是 Agent 可以长期进入的工作世界

一个 Project 不只是一条数据库记录。它同时应有一块人和 Agent 都能直接阅读、编辑和带走的文件工作区，例如 Obsidian Vault、Markdown 文档、参考资料、Guide、Skill 与外部工具配置。

PAOS 与文件工作区各自保存不同的东西：

```text
PAOS Store        = 长期身份、正式责任、状态、裁决与可审计历史
Project Workspace = 当前工位、团队目录、正文资料、方法与交付成果
```

文件工作区不能成为第二套 Work 状态；PAOS 也不应吞入所有文档正文。二者通过路径、Artifact、版本登记和 Workstation 相互定位。

Agent 加入 Project，不只是获得一个 Session ID，而是进入一个工位：它能从稳定的 ENTRY 找到自己，从 TODO 找到个人下一步，从 PAOS 找到正式责任，从 TEAM 找到同事，按需找到共享 Workflow 与 Skill。Runtime 可以更换，工位和长期 Agent 身份仍然连续。当前责任不手抄进多份文件；工具应合成各处事实，并在冲突时展示来源。

### 2.2 Human、Coordinator 与 Worker 的组织分工

PAOS 的目标组织关系是：

```text
Human 不做日常行政
  → Coordinator 组织项目行政
      → Worker 自己闭环个人行政与专业交付
```

Human 主要保留方向、品味、价值判断和最终责任。Coordinator 理解局势、拆分 Work、组织 Agent、推动 Review、汇总成果并把真正需要人的问题送入 Needs Me。Worker 读取工位和 Mailbox，自行找资料、工作、验证、沟通、登记成果和留下交接，而不是把个人行政重新倾倒给 Coordinator。

Coordinator 的自主性来自 Agent 的泛化智能，而不是把每种业务过程写成硬编码工作流。普通派工、成员安排、复核、验收与取消由 Coordinator 承担；Human 保留方向、偏好、资源、对外承诺及明确保留的验收。Rooter 管安装和跨项目运行秩序，不代替 Coordinator 决定项目内容。底层保留业务权限、revision 冲突、幂等、原子提交与恢复规则；正常写入不依赖 Runtime owner、instance ID、mandatory enter 或 Cycle claim。

具体动作沿当前业务接口执行；Rooter 复用 Human operational authority，职责分工不构成新的权限租约。Rooter 的长期身份、Home 与治理边界见 [Rooter 原则](ROOTER-PHILOSOPHY.md)。

### 2.3 CAT 是自然协作空间，不是正式事实库

CAT 的价值不只是传递任务状态。Agent 可以在 Room 中讨论、质疑、求助、改变理解和形成临时协作，让有价值的发散自然出现。

但 CAT 中的讨论、猜测和共识不会自动成为 Project 的正式事实。形成 Work、Decision、Artifact、Lesson 或 Guide 改进后，应由 Agent 或 Coordinator 显式登记回 PAOS。可以把这条边界概括为：

> **CAT 可以自由，PAOS 必须清楚。**

### 2.4 三个飞轮共用同一个真实工作过程

PAOS 不应另造“飞轮任务”。一次真实工作同时产生三类可能的复利：

```text
Workflow   = 同类工作下次更自然地推进
Continuity = 下一任从工位、正式事实和成果接上主线
Learning   = 纠正与经验被提升为 Lesson、Guide、Skill 或 Eval
```

Continuity 不依赖独立的 Working Memory 机制。正式责任由 PAOS 保存，个人当前页留在 TODO，长期知识进入普通项目文件，个人提醒可以按需写 NOTES。只有下一次真实工作实际消费了这些内容或共享方法，飞轮才成立；保存文件、增加字段或生成总结，都不等于产生复利。

### 2.5 长期 Agent 轻接入，原生会话由人创建

Human 在 Codex、OpenCode 等 Harness 中手动打开原生会话，并提供长期 Agent ID、Project 和固定工位入口。Agent 读 ENTRY、TODO 与 orient 后直接继续已有责任；同一会话压缩上下文使用同一恢复路径。换对话本身不创建 Work、Assignment、业务 Cycle，也不重授 Coordinator 岗位。

正常路径已删除写入 owner、instance ID、必做 enter 与 Cycle claim，不在工具背后恢复 lease 或 ticket。换会话时停止旧执行及相关消费者；revision 冲突检查不能替代停止旧 Runtime。稳定 Agent ID 表达业务身份，Wake binding 只表达联系地址，消费者内部去重不成为员工写入资格。PAOS 不接管 Harness 的原生会话创建。

### 2.6 一个信息只维护一次

正式责任和验收在 PAOS，当前团队与稳定联系方式在项目根的 TEAM，个人下一步与在途动作在本人工位 TODO，项目知识在普通文件，当前连接由工具维护，历史由 Git、交付物和必要日志保留。CLI 负责把这些事实拼成 Agent 能读懂的工作视图，不再生成另一份需要人工维护的总 Memory。

工位 ENTRY 保持稳定、狭窄；TODO 的当前区必须与旧记录分离。个人待办勾完不等于 Work 验收，Work 完成也不等于成员离队。文档与工具出现分歧时，应明确显示来源和待修位置，不能给出看似正常的假当前状态。

### 2.7 协作与收尾属于正常工作

Agent 应能直接找到同事、提出疑问、沿已有消息回复，不让 Coordinator 成为所有交流的转发站。持久工位 Mail、正式 Request 和 CAT 临时讨论各有用途；送达、可达、实际消费与业务验收是不同事实。绿色连接状态不能替代本人回执或真实工作。

交付时顺手更新当前页、成果入口和必要历史。跨回合仍会修改外部目标的进程，必须留下目标、控制人、结果查看和停止方法，并确认完成、停止或明确接手；原生回合结束不代表它启动的外部写入已经停止。短任务不强制写 Memory、Handoff 与重复总结。

### 2.8 升级以完整业务闭环交付

版本完成的单位是一条可用路径：新 Runtime 从固定入口恢复身份与责任，能正式写入、联系同事、交付成果、完成复核，并让下一任继续工作。代码合并、安装成功和成员实际采用分别举证。V1.2 先让 2001 与 3002 两个活跃 Project 完整采用；其他旧 Project 保留可读历史并退出日常运行，不为旧机制维持第二条正常路径。

内部开发可以并行，发布采用同一集成候选和一次切换。Coordinator 对当前团队发持久公告，成员自行更新个人工位与联系入口并回报，Rooter处理安装例外。验收看真实接班和业务动作，不看公告发出了多少或配置亮了多少绿灯。

## 3. 复杂度应花在语义正确，而不是基础设施豪华

PAOS 是本机单用户软件，因此可以长期使用很轻的工程结构：

```text
localhost
JSON / files
append-only Ledger
Python standard library
browser UI
several local ports
```

它不需要为了显得专业而引入多租户、微服务、容器编排、分布式数据库或复杂权限树。

但“基础设施简单”不能变成“状态语义随便”。以下问题必须严格：

```text
谁改了什么？
这个 Agent 是否被授权？
重复请求会不会重复写入？
失败后状态能否重放或恢复？
Runtime 结束是否影响 Work？
Decision 究竟由谁裁决？
```

可以不严谨地追求基础设施规模，不能不严谨地处理人的工作含义。

> **个人软件可以工程结构很轻，但不能认知结构很乱。**

## 4. 需求编译式个人软件

PAOS / CAT 暴露出一种新的软件生产方式：

> **当 Agent 大幅降低软件开发的边际成本，软件可以从“为一类用户制造标准产品”，变成“把一个人的工作方式编译成运行环境”。**

可以把它称为：

> **Requirement-Compiled Personal Software**  
> **需求编译式个人软件**

传统软件需要把开发成本摊给大量用户，因此必须抽象共同需求。Agent 时代，一些过去经济上不值得开发、又比脚本复杂得多的软件开始成立：它可能只有一个用户、一台电脑、几条工作流，却仍然拥有 UI、状态、自动化、API、权限、日志、升级、测试和插件。

这类软件可以称为：

> **Personal Microsoftware**  
> **个人微软件**

它的价值不来自用户规模，而来自它与一个人的真实工作方式有多贴合。

## 5. Agent 是需求编译器，而不只是代码生成器

未来的软件使用过程可能从：

```text
下载软件 → 学习配置 → 改变自己去适应软件
```

转为：

```text
个人工作方式
+ 本机环境
+ 已有文件与工具
+ 习惯与约束
        ↓
      Agent
        ↓
工作流中间表示
        ↓
组件 / 配置 / glue code
        ↓
验证 / 安装 / dogfood
        ↓
Personal Software
```

自然语言需求是 Source Language，领域 invariant 是 Intermediate Representation，schema、API 和状态机是合同，代码与配置是编译产物，测试和运行证据则是类型检查与运行时证明。

例如：

```text
Requirement:
  Agent 更换原生会话后继续同一份责任。

Invariant:
  Work、成员身份与个人当前页不因 Runtime 更换而改变；换会话时必须先明确停止旧执行（含相关消费者），不再依赖写入收据判断谁在场。

Contract:
  新会话走固定工位（ENTRY/TODO）+ orient 恢复原责任并正常写入；写入资格不依赖 Runtime owner、instance ID、必做 enter 或 Cycle claim。

Implementation:
  运行绑定 + 写入合同（revision/幂等/原子提交/回执）+ 恢复 CLI + 数据转换。

Verification:
  Work/Agent 身份保持；停止旧执行后从固定工位恢复成功；过期 revision 失败且不部分提交；同一合法操作重试复用原回执；revision 冲突不是 Runtime fencing，只拦截并发写乱序。
```

Agent 真正困难的任务不是写出 Python，而是把模糊需求收敛成可以执行、验证、升级、回滚和再次编译的个人工作系统。

## 6. 可再编译性比代码生成更重要

“每天让 AI vibe coding 几个小工具”不会自然产生个人软件生态，只会很快形成无人理解、无人敢升级的个人技术债垃圾场。

需求编译式软件必须保留完整链条：

```text
Requirement
  → Invariant
  → Contract
  → Implementation
  → Verification
  → Runtime Evidence
```

其中源码不一定是最上游资产。更值得长期保存的是：

- 为什么需要它；
- 哪些工作语义不可破坏；
- Agent 和人的权限边界；
- 外部组件怎样接入；
- 什么行为才算通过；
- 真实运行曾经证明过什么。

当这些仍然存在时，代码可以迁移、重构甚至重建。真正的能力不是永远不丢实现，而是能从可信规格重新编译出可信系统。

## 7. Software Genome：真正可携带的是个人软件规格

未来用户保存的可能不是一组安装包，而是一份个人软件基因：

```text
personal-software-spec/
  requirements
  preferences
  workflows
  invariants
  authority
  connectors
  ui_preferences
  local_data_contract
  acceptance_tests
  package_lock
  runtime_evidence
```

换电脑时不再逐个重装和重新配置 37 个 App，而是让 Agent 根据这份规格重新编译工作环境。

这与 Arch Linux 的精神相似：系统由组件组合成适合自己的形状。不同之处是，Agent 有机会把过去只有专家才能承担的配置与维护成本降下来，使“高度定制”不再自动等于“高技术门槛”。

## 8. PAOS / CAT 在这套编译体系中的位置

```text
PAOS Core          = Personal Work Kernel
CAT                = Collaboration Package
Runtime Adapter    = Driver
Authority          = Capability / Permission Model
Context Compiler   = Execution Context Linker
Tests              = Type System / Conformance Suite
Receipt + Ledger   = Runtime Proof
Agent              = Compiler + Maintainer + Installer + Migration Engineer
```

PAOS / CAT 不必成为面向百万用户的标准 SaaS。它们更重要的价值，是作为一个具体原型证明：高度定制、可追溯、可升级的小规模软件能够服务一个真实的人，并随着使用持续重新编译。

## 9. 对后续开发的判断准则

任何 Human 或 Agent 在新增功能、修复摩擦或重构架构前，应先回答：

1. 这项变化保护的是哪一个人的工作语义？
2. 输入属于事实、推断、提案还是历史证据？
3. 它应该进入 PAOS Core、CAT、Runtime Adapter，还是只留在原生 Session？
4. 失败会污染长期事实，还是只影响一个局部页面？
5. 当前最小、可读、可验证的实现是什么？
6. 哪条验收行为能证明它真的减少了真实摩擦？
7. 新合同落地后，哪些旧代码、旧字段和旧测试必须删除？
8. 如果实现代码丢失，现有 Requirement / Invariant / Contract / Test 是否足以把它重新编译出来？

两条边界尤其重要：

> **当人类仍在机械执行 Agent 已经可以可靠完成的行政动作时，系统存在协作摩擦。**

> **当 Agent 能在没有明确依据和授权时改变人的工作语义时，系统已经越界。**

PAOS 的长期方向，就是不断缩小第一种摩擦，同时永远守住第二条边界。

## 10. 最终愿景

PAOS / CAT 的意义不只是给现有软件增加 AI，也不只是让多个 Agent 相互发送消息。

它们指向另一种可能：

> **人的需求、习惯、约束和真实工作证据，可以成为软件最上游的源代码；Agent 则把它持续编译成适合这个人的软件环境。**

过去的软件工业不断追求“一套产品服务越来越多人”。Agent 可能同时开启另一条支流：

> **越来越多的软件，只服务一个人。**

PAOS / CAT 是这条支流上一个很早、很具体，也已经经历真实 dogfood 的原型。
