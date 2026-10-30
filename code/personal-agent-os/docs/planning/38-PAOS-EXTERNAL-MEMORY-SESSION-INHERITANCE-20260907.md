# 需求文档：PAOS 作为外置记忆体的 Session 转生/继承

> **M0 状态说明（2026-09-08）**：本文保留为最初问题定义、外部调研与需求来源，不再作为普通接班实现合同。唯一有效的接班合同是 `docs/contracts/AGENT-CONTINUITY-V0.md`；执行顺序见 `docs/planning/39-AGENT-CONTINUITY-MAILBOX-SUPERVISED-DELIVERY-20260908.md`。
>
> 与后续合同冲突时按以下修订解释：
> - “新 Session `continues_session_id = 旧 Session`”不再是普通夺舍主路径。产品语义中的 Agent 就是现有 `sNNN`；新的 native GPT/Codex/DS-H 会话通过**同一个 Agent 新 Cycle**接管，Agent 编号、Work、Coordinator 岗位、Mailbox 与 Room membership 不迁移。
> - 既有 `continues_session_id` 链只保留历史可读；M1A 不继续用它创建普通 successor Agent，也不批量重写历史证据。
> - “旧 Participant retire、新 Participant 接续 Room”被取代。普通夺舍继续使用 Agent 已经绑定的**现有 CAT participant_id**；participant ID 不是从 PAOS Agent ID 重新推导，新 Runtime 自行 rebind native/runtime binding。
> - 当前 Artifact 只有 `type/purpose/replaces/status=current` 等骨架，**尚未实现正式版本冻结/审阅治理**；本文中“版本化、可冻结、可溯源”属于目标能力，不得写成现状事实。
> - Working Memory 是工作连续性记忆，不复制 Work/Request/Decision/Authority 等实时项目事实；冲突时 PAOS current fact 优先。
> - Working Memory V0 使用 `agent_working_memory` 受管 Artifact；M1A 先做 Runtime handover，M1B 再做记忆与 bounded context。
> - “<2k tokens”只作为产品目标，工程用字符/条目预算约束；不引 tokenizer 来追求伪精确。
> - 删除“每个 Session <40%”“转生零丢失”等保证。M5 记录同类任务实际初始注入、后续读取、重复读取与工具回合；T244 只证明重新生成已审内容会失真，不单独证明 auto-compaction 是唯一根因。

> 问题：超长会话（如 LRC101 的 251+65 turn Codex 会话）消耗快、易触发压缩丢失；开新会话又冷启动失忆。
> 方案方向：把会话的长期记忆**外置到 PAOS**（受治理的项目记忆），新 Session 通过 PAOS 继承状态而非背负全量对话历史。
> 作者：DSH · 3002-s028 · 2026-09-07。配套调研见文末。

---

## 1. 问题定义

两种坏情况，用户都真实遇到：

1. **超长会话烧额度且不可靠**：Codex 5 小时窗口用到 96%；长会话反复粘贴报告、读 CAT/PAOS、高推理任务——额度快速消耗，且 auto-compaction 会丢上下文（T244 事件证明重新生成会偷换冻结内容）。
2. **新会话冷启动失忆**：开新 Codex task 不继承长对话，但给它的 handoff 太短就「理解错任务」、太长就又成了超长会话。

**本质矛盾**：上下文即消耗，但工作又依赖上下文。解法是**让上下文的主体不再住在会话里，而住在 PAOS**——会话变成「按需读取外置记忆的执行体」，而不是「携带全部历史的容器」。

## 2. 参考方案调研（三族）

| 族 | 代表 | 机制 | 与 PAOS 的关系 |
|---|---|---|---|
| **压缩族** | Claude Code auto-compaction、session-vitals | 会话内自动压缩/挑选保留 | 治标：仍在会话内，压缩会丢（T244 证明不可靠） |
| **交接族** | [claude-code-session-handoff](https://github.com/IRDcode/claude-code-session-handoff)、[Codex Session Bridge #24810](https://github.com/openai/codex/issues/24810) | 老会话交接给新会话，新会话读父级 | 方向对，但交接的是「对话历史」而非「受治理的项目状态」 |
| **外置记忆族** | [Letta](https://github.com/joanmarcriera/Home-office-automations/blob/main/docs/tools/agents/letta.md)、[Cloudflare Agent Memory](https://www.infoq.cn/article/TPqCEvSNCh9jzivioLs8)、[Redis LTMA](https://redis.io/blog/long-term-memory-architectures-ai-agents/)、[synapto](https://pypi.org/project/synapto/0.4.0/) | 持久记忆库，Agent 读写 | 方向最对，但它们是**通用记忆库**，没有 PAOS 的治理（revision/receipt/Coordinator/冻结） |

**PAOS 的独特位置**：外置记忆族的方向 + 受治理的项目事实。新 Session 继承的不是「记住了什么」，而是「项目当前的可验证状态」——这比裸记忆可靠得多，因为它有 revision、receipt、冻结语义、Coordinator 治理。

## 3. PAOS 现状能力盘点（已有什么）

| 机制 | 现状 | 差距 |
|---|---|---|
| Session Continuity Chain | `continues_session_id` 链（s011→s027→s041），链式员工身份，前序 Mission + `note_for_next_session` 进握手 | 只传「一句话备注」，不传丰富上下文 |
| Context Pack | 握手时给 Mission/边界/当前事实 | 是一次性打包，不是按需读取的活的记忆 |
| Artifacts | 版本化、可冻结、可溯源 | 已经是最好的「外置记忆载体」——但没有「Session 工作记忆」的专门形态 |
| note_for_next_session | 小文本字段 | 太小，承载不了长会话的状态 |
| Office/Stewardship 端点 | Agent 可读自己的状态 | 是「现在」的快照，不是「工作过程」的记忆 |

## 4. 需求：Session 转生/继承的完整设计

核心思想：**会话的工作记忆分层外置，新 Session 通过三层继承**。

### L1. 身份继承（已有，保持）
Session Continuity Chain：新 Session `continues_session_id = 旧 Session`。继承 Mission、定位、职责边界。**这一层已可用。**

### L2. 状态继承（新增核心：外置工作记忆）
旧 Session 在工作过程中，把**关键状态**持续写成 PAOS 的**受治理记忆对象**：

- **当前理解**：对项目/任务的当前判断（不是对话，是结论）
- **已确认事实**：已验收的决策、已冻结的版本、已关闭的问题
- **开放问题**：未关闭的疑问、待验证的假设
- **证据锚点**：关键 Artifact 的指针（不是内容，是引用 + 哈希）

形态建议：一种新的 Artifact 类型 `session_working_memory`（版本化、可冻结、可溯源），或复用 generated 块。**倾向：Artifact（版本化 + 冻结语义天然契合）**——但需 Grill 确认。

### L3. 过程继承（按需读取，不预载）
新 Session **不预载**全部历史。它继承 L1+L2 后，通过**按需读取**获取过程细节：
- 需要某段历史时，读对应 Artifact（不是全量拉取）；
- 需要某次会议/某条证据时，读源文件（不是粘贴进会话）；
- CAT Room 的后续消息继续流向新 Session（CAT binding 换绑到 successor）。

**关键纪律**：新 Session 的初始上下文 = L1（身份）+ L2（受治理状态摘要，<2k tokens）+ 一个「记忆索引」（哪些 Artifact 可查），**不含** L3 的过程历史。过程只在需要时读。

## 5. 量化目标

| 指标 | 现状（LRC101 会话） | 目标 |
|---|---|---|
| 新 Session 初始上下文 | 全量历史或短 handoff | L1+L2 摘要 < 2k tokens + 记忆索引 |
| 继承保真度 | 短 note 或人工复述 | 关键状态 100% 来自受治理 Artifact（非对话记忆） |
| 超长会话额度消耗 | 5h 窗口 96% | 同类工作分摊到多个短 Session，单个 < 40% |
| 重新生成风险 | T244 式偷换 | 状态只来自冻结 Artifact，装配可溯源 |

## 6. 功能需求

| # | 需求 | 说明 |
|---|---|---|
| M1 | **Session Working Memory Artifact** | 旧 Session 持续写「当前理解/已确认事实/开放问题/证据锚点」到受治理 Artifact；版本化、可冻结 |
| M2 | **继承握手增强** | 新 Session 的 Context Pack 在 L1 基础上注入 L2 摘要 + 记忆索引（哪些 Artifact 可查） |
| M3 | **CAT 换绑** | 旧 Participant retire（治理式，保留历史），新 Participant 接续 Room；CAT 的后续消息流向新 Session |
| M4 | **记忆索引视图** | 新 Session 看到一个只读索引：有哪些 Artifact、各自类型/时间/一句话内容——决定「要不要读」而不是「被迫全读」 |
| M5 | **按需读取纪律** | Prompt 明确：过程历史只在需要时读对应 Artifact，不预载、不粘贴全量历史进会话 |
| M6 | **转生验收** | 新 Session 在 Acknowledge 时报告：从 L2 继承了什么、有哪些开放问题、计划先做什么——验证继承保真度 |

## 7. 与超长会话的关系（正确使用方式）

这条需求**不是**要消灭长会话，而是让长会话**可以随时转生**：

```
长会话（烧额度中）
  ↓ 用户决定转生（或额度预警）
旧 Session 把 L2 工作记忆写入 Artifact（冻结）
  ↓
新 Session 开（短上下文），continues_session_id = 旧 Session
  ↓ L1 身份 + L2 状态摘要 + 记忆索引
新 Session 继续工作，过程细节按需读
  ↓ CAT binding 换绑，消息流向新 Session
```

额度消耗从「一个无限长的会话」变成「一串各自有限长的会话」，每段都 <40% 窗口，且因为状态在 PAOS 而非对话里，转生零丢失。

## 8. 与既有系统的关系

- 复用：Session Continuity（L1 已有）、Artifacts（L2 载体）、CAT retire/接续（M3 基础）、Context Pack（M2 通道）。
- 新增（最小增量）：working-memory Artifact 类型、继承握手注入 L2+索引、CAT 换绑流程、记忆索引视图。
- 不做：通用记忆库（Letta 式）、向量检索记忆（synapto 式）、自动压缩（压缩族——PAOS 的记忆是受治理的，不需要压缩）。

## 9. 风险与开放问题（Grill）

1. **Working Memory 是新 Artifact 类型还是复用 generated？** 倾向 Artifact（冻结+溯源），待 Grill。
2. **L2 摘要谁写**：旧 Session 自己写（它最懂）还是 Coordinator 提炼？倾向旧 Session 写、Coordinator 审。
3. **CAT 换绑的原子性**：旧 retire + 新加入是两步，中间窗口消息去哪？（Saga 语义，分步可见）
4. **记忆索引的粒度**：Artifact 级还是段落级？先 Artifact 级。

---

*配套调研：§2 三族外部方案；内部：PAOS SESSION-CONTINUITY.md、T244 版本信任教训、Codex 超长会话额度实录（5h 窗口 96%）。本文自 2026-09-08 起作为历史需求输入保留；实现以 M0 canonical contract 与 39 号计划为准。*
