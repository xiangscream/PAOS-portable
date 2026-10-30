# 需求文档：Coordinator 编排的项目工作流高度自动化

> **M0 状态说明（2026-09-08）**：本文保留为最初业务需求与 LRC101 实录提炼，不再作为 Agent 接班、CAT 身份、阶段审阅或冻结语义的实现合同。唯一有效的普通接班合同是 `docs/contracts/AGENT-CONTINUITY-V0.md`；开发顺序见 `docs/planning/39-AGENT-CONTINUITY-MAILBOX-SUPERVISED-DELIVERY-20260908.md`。
>
> 与后续合同冲突时按以下修订解释：
> - F3.1“分派给并行 Agent”只表示向**已经由 Human 创建/接入的现有 Agent**分工，不授权 Coordinator 自动 Create Agent 或自动启动 Runtime。
> - F4“每个阶段都进入 Human Gate”降级为历史范式；V0 采用 **Coordinator technical acceptance + selective Human Gate**，只有产品方向、用户承诺、关键分歧、最终批准等需要 Human Authority 的节点才强制进 Needs Me。
> - F4.3“通过 = 冻结”被取代：`snapshot/frozen`、`technical acceptance`、`human approval` 是三个独立维度，不能互相冒充。
> - F5 的装配目标保留，但仅靠可变路径 + 哈希不算已固定证据；M5 使用 exact Git commit+path 或不可覆盖 snapshot，并要求 provenance 覆盖正文来源。
> - §3 第 2 条“阶段通过/版本冻结全部只能人类”不再是通用规则；Coordinator 可以做普通技术验收，但不能代办 Human-only 决策/最终批准。
> - §4 的“并行 ≥2 Agent / 每阶段 1 Gate”等只作为能力测试场景，不要求真实任务强行并行、制造返工或人工 Gate。

> 依据：LRC101 协作实录（251-turn 主会话 + 65-turn 续会话）中已被真实使用验证的工作流。
> 目标：把「理解项目 → 详细计划 → 实施 → 阶段人工审核 → 汇总成果 → 沉淀经验」这条流程，用 PAOS（Coordinator 编排）做成可重复、可验收、低人工成本的自动化流程。
> 作者：DSH · 3002-s028（specialist · 功能开发，agent 优先）· 2026-09-07

---

## 0. 现状：这条流程已经「半自动」，卡在四个点

LRC101 实录证明流程本身成立，但每一环都靠用户人肉粘合：

| 环节 | 实录中的样子 | 卡点 |
|---|---|---|
| 理解项目 | 用户把会议记录/前序 Session 上下文/最新文档喂给 GPT | 理解靠用户手动聚合材料，没有统一入口 |
| 详细计划 | GPT 出 Research Pack A–E + 阶段计划 | 计划是一次性 prompt，不是可追踪对象；阶段间靠用户手动推进 |
| 实施 | 多 Agent 并行调研 + GPT 成稿 | 并行 Agent 靠用户手动搬运结果；结果汇总靠 GPT 单线程 |
| 阶段人工审核 | 用户逐节过闸、复述校验、结构纠正 | 审核点无形式化，靠用户记住「该审了」；审核结论散落对话里 |
| 汇总成果 | GPT 装配版本（S6 Canonical） | 装配被 GPT 偷换成重新生成（T244 事故）；版本信任靠用户人肉核验 |
| 沉淀经验 | 工作法变成禁令/规则 | 经验沉淀在对话里，没有变成可复用的流程资产 |

**核心判断：这条流程的「形状」已经被验证有效，缺的不是方法，而是把它从「人肉粘合的对话」变成「Coordinator 编排的正式流程」。**

## 1. 需求总目标

让 Coordinator 能够编排一条**阶段门（Stage-Gate）项目工作流**：理解→计划→实施→审→汇总→沉淀，其中——

- **Coordinator 负责**：阶段推进、任务分派（并行 Agent）、结果聚合、版本装配、经验沉淀提示；
- **Agent（执行体）负责**：材料通读、并行调研、结构化产出、QA 清洗；
- **人类负责**：只在**形式化的决策门**出现——批准计划、阶段审阅、冻结版本、裁决分歧。

量化目标（来自实录的人工成本估算）：
- 阶段间推进的人工消息数：从「每阶段 5–15 条手动指令」降到「每阶段 1 次确认」；
- 并行 Agent 结果的汇总：从用户手动搬运到 Coordinator 自动聚合+冲突标注；
- 版本装配：从「可能被重新生成」到「可溯源装配 + 哈希核验」。

## 2. 功能需求（按阶段）

### F1. 理解项目（Intake）

- **F1.1** Coordinator 能从三类入口理解项目：会议记录（Artifact）、前序 Session 上下文（session continuation）、最新版本文档（当前事实）。**现状**：PAOS 已有（Artifact + session cycles + needs-me）。
- **F1.2** 新增：Coordinator Intake 视图——把「当前承诺 / 最新版本 / 未关闭缺口 / 待处理 Request」聚成一个只读开工面（复用 stewardship 投影，不加对象）。

### F2. 详细计划（Plan）

- **F2.1** Coordinator 把理解转成**阶段计划**：阶段列表 + 每阶段目标/Done-When/验收门。计划作为 Artifact 落盘（不是一次性 prompt）。
- **F2.2** 阶段计划支持**并行任务包**（Research Pack 模式）：每个包有独立目标、方法约束、产出形态、验收标准——对应实录的 Pack A–E。

### F3. 实施（Execute）

- **F3.1** Coordinator 把任务包**分派给并行 Agent**（assignment with purpose），多 Agent 同时执行——对应实录的多 Agent 并行调研。
- **F3.2** 各 Agent 的产出回执为 Artifact（带证据分级 A/B/C）。
- **F3.3** Coordinator **自动聚合**并行产出：合并、冲突标注（哪两处结论矛盾、证据强度对比）、去重——对应实录中 GPT 手动「对过并行结果」的动作。**这是当前最大的自动化缺口。**

### F4. 阶段人工审核（Gate）

- **F4.1** 每个阶段结束进入一个**形式化决策门**：Coordinator 把「本阶段产出 + 建议（通过/修改/驳回）」放进 Needs Me，人类一键裁决（对应实录的「进入阶段 X / ok 了 / 就这样吧」）。
- **F4.2** 决策门有**显式验收标准**（该阶段的 Done-When），不是「感觉不成熟」式的自由发挥——但允许人类附加自由批注（实录证明这种直觉纠偏有价值）。
- **F4.3** 冻结语义：通过 = 该阶段 Artifact 冻结，不可被后续阶段改写（对应 T221 冻结纪律 + T244 教训）。

### F5. 汇总成果（Assemble）

- **F5.1** Coordinator **按已冻结的各阶段 Artifact 装配**最终成果——**绝不重新生成**（T244 的硬教训）。
- **F5.2** 装配可溯源：每段内容标注来源（哪个阶段 Artifact / 哪个 turn），成品带哈希，可被独立核验。
- **F5.3** 装配后进入**最终验收门**（创始人视角找茬 + 硬伤门禁），人类批准才算完成。

### F6. 沉淀经验（Sediment）

- **F6.1** 流程结束后，Coordinator 提示「这次有哪些工作法值得沉淀为规则」：禁用语清单、证据分级、冻结纪律、Gate 清单——变成**可复用的流程资产**（下次同类流程直接复用）。
- **F6.2** 沉淀入口：作为 Suggestion（ Coordinator 提炼 → 人类确认 → 进公共能力索引），对应 §1.6 摩擦驱动的知识复用。

## 3. 关键不变式（不可违反）

1. **冻结即冻结**：已冻结的 Artifact 永不被后续改写；装配只做拼接，不做重新生成。
2. **决策门必须人类**：阶段通过、版本冻结、最终验收、分歧裁决——只能人类（Coordinator 只能提出，不能代办）。
3. **Coordinator 编排但不替代**：它不替代 Agent 执行、不替代人类裁决；它是流程的推进器与聚合器。
4. **纯投影，不加对象**：Intake 视图、Gate 视图、聚合视图都从现有 Artifact/Request/Needs-me 投影，不新建 durable 对象（除非确实需要「阶段计划」作为一种 Artifact）。

## 4. 验收标准

| # | 场景 | 验收 |
|---|---|---|
| A | 一个真实项目（如 LRC101 第三章重构类）走完整条流程，阶段间推进只需人类每阶段 1 次确认 | 阶段数 ≥3，每阶段 1 Gate 裁决 |
| B | 并行 ≥2 Agent 调研，Coordinator 自动聚合产出冲突标注 | 聚合报告含冲突项 |
| C | 装配可溯源：成品每段可指回阶段 Artifact；哈希可验 | 抽检 ≥3 段命中 |
| D | 全程 Coordinator 无越权（未代办人类裁决、未重新生成冻结内容） | 审计日志 |
| E | 沉淀 ≥1 条流程资产进公共能力索引 | 有 Suggestion 记录 |

## 5. 与既有系统的关系（不重复建设）

- 复用：Coordinator 授权（已有）、Authority Matrix（已有）、Stewardship 投影（已有）、Artifact/Request/Decision/Needs-me（已有）、CAT Room 多 Participant（已有）。
- 新增（最小增量）：阶段计划 Artifact 类型、并行产出聚合器（纯计算）、阶段门视图（纯投影）、装配溯源+哈希。
- 明确不做：多 Agent 编排框架、自动 scheduler、跨系统隐式级联、新建 durable workflow 对象（除非 F2.1 证明必要）。

## 6. 风险与开放问题

1. **阶段计划要不要成为 durable 对象？** 倾向：作为 Artifact（版本化、可冻结），不是新领域对象——但需 Grill 确认。
2. **并行 Agent 聚合的冲突标注质量**：机械 diff vs 语义冲突——先做机械标注，语义判断留给人类 Gate。
3. **冻结纪律的强制度**：装配器如何机械保证「不重新生成」？候选：装配只接受冻结 Artifact 的内容引用，不允许自由文本输入。

---

*本文档由 LRC101 协作实录（251+65 turn）提炼，供 Coordinator 编排工作流的建设立项；2026-09-08 起由 M0 canonical contract 与 39 号执行计划约束实现。*
