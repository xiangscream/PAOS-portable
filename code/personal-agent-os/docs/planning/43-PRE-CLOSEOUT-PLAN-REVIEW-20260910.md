# 43 · 4/5 收口前规划审查（只读）

> 作者：3002-s027（implementer · opencode）· 2026-09-10
> 委托：3002-s010（CAT Exchange x-6515d9ea3089 / 预检后续指示 x-d81cd048cf94）
> 范围：基于当前 main@32860da 与真实使用记录的只读规划审查，不改代码、不扩数据模型。
> 工作区事实核对：`git diff --ignore-cr-at-eol` 显示 71 个 modified 文件中仅 5 个有实质改动（project-attention-ui.mjs、project-session-ui.mjs、project.html、session.html、session.mjs，均为 Human 授权的 UI 窄修，未提交）；其余 66 个文件为纯行尾（CRLF）漂移噪声。

## A. 三飞轮如何以最小 onboarding 进入日常工作

### 已实现（证据路径）
- Workflow 飞轮雏形：Context Pack 自动编译 + 执行任期 + Runtime 接管。`attention-dashboard-v1-static/agent_continuity_workflow.py`、`context_compiler.py`、合同 `docs/contracts/AGENT-CONTINUITY-V0.md`。真实使用证据：s027 已完成 3 次 Cycle 接管（含 2026-09-10 DSH→opencode 跨 Runtime 真实接管，PAOS delta rev 418）。
- Memory 飞轮：Agent Working Memory（M1B）。`working_memory_hooks.py`、`working_memory_projection.py`、`working_memory_context_safety.py`、合同 `AGENT-WORKING-MEMORY-V0.md`；bounded 注入已生效（当前 Pack 只注入 8/61 delta）。窄接口：`artifact_add type=agent_working_memory`。
- 责任投递：Agent Mailbox（M2）。`mailbox_projection.py`、`mailbox_hooks.py`、合同 `AGENT-MAILBOX-V0.md`。Mailbox 只投影 canonical Request/Assignment/Work 责任，**天然没有广播通道**——伪造广播在当前数据模型下无法发生，除非伪造 canonical 事实（受 Store/权限约束）。
- 协作通道：CAT Room/Participant 稳定绑定（M3，`cat_binding.py`、合同 `CAT-CONTINUITY-V0.md`）+ Runtime 自助 rebind/inbox/hook-setup。
- 成果沉淀：Artifact 版本谱系（M5A）与类型化 subject/source/evidence 引用（M5B，合同 `ARTIFACT-LINEAGE-V0.md`、`ARTIFACT-EVIDENCE-REFERENCES-V0.md`）。

### 未实现 / 缺口
1. Learning 飞轮无正式落点：Human correction、成功经验、失败路径目前只能留在 CAT 讨论、Session Update 与摩擦记录里，没有 Skill/Eval/Lesson 类对象；`CAT_RUNTIME_ADAPTERS.md` 里「三飞轮」只是 adapter 文档中的背景愿景。
2. Onboarding 仍有两处 Human 手工粘合：开新 Agent 需 Human 手动 open session + 手动粘贴接班 Prompt；Context Pack 的「本次必读资料」字段靠人填，没有按 Work 自动挑选材料。
3. Mailbox 的真实消费证据不足：至今 Inbox 责任多走 CAT Exchange 即时协作，经 Mailbox 投影被 Agent「读取→处理→闭合」的完整链路 dogfood 记录还很少。
4. g015（Room 筛选/显式结论提升）、g008（带沟通目的 Agent→Agent 关系边）未实现，跨 Agent 结论沉淀依赖人工转述。

### 最小下一阶段
1. 不建新对象，继续真实使用：让 2–3 条真实 Work 全程走「Human open → Agent ack(claim+binding) → Mailbox 领责 → CAT 协作 → Update 回写 → Artifact 登记」，收集「Mailbox 消费是否降低 Human 重复解释」的证据。
2. Coordinator Request 增加「必读材料」显式字段用法（现有 payload 内已有入口），让 Pack 必读从人工填写转向按 Request 自动携带。
3. Learning 沉淀先复用现有对象：摩擦记录 → Work suggestion；经验 → Decision/Artifact；等教训积累后再决定是否需要正式 Learning 合同。

### 不做项
Mailbox 广播/通知对象、知识图谱、证据评分、自动 Learning 抽取管线、任何 PAOS 数据模型扩展。

## B. Coordinator 主入口的轻量闭环（检查→拆解→派发→跟进→验收→沉淀）

### 已实现（证据）
- Coordinator 动作面（API 齐全，29 actions）：`coordination_workflow.py:303 create_work_coordinator / :373 create_assignment / :460 transition_work / :711 create_request_coordinator`；`coordinator_continuity_guard.py`；decision.review、session.abandon（Coordinator 通道）。
- 只读投影：`needs_me`、`stewardship`、`lifecycle_findings`、`relations`、`portfolio`（workflow_service.py:62-90）。
- 权限事实：work.create / work.review / work.cancel 为 Human-only；Coordinator 只能创建 Work/派发/推进，不能代办 Human 决策（authority_manifest.py:140-340）。

### 未实现
1. **上述 Coordinator 动作全部没有 UI 入口**：所有 `.mjs` 均未调用 `coordinator/requests`、`coordinator/assignments`、`coordinator/work-items`；Coordinator 面板当前只有 Choose Agent / Continue Coordinator / Agent history（`project-attention-ui.mjs:103`）。
2. 六步闭环目前靠 s010 人肉执行，无引导面、无 checklist 投影。
3. M4 Coordinator Supervisor Contract 仍是 Draft PR #25，不视为已交付。

### 最小下一阶段
1. Coordinator 面板加一块**只读开工清单**：数据全部复用 needs-me/stewardship/office 投影（待领 Request、待推进 Work、Needs Me、最近闭合），零新 API。
2. 给 request.create / assignment.create / transition 各加一个最小表单按钮，直调既有端点；表单字段与 API payload 一一对应，不加新对象。
3. 验收标准：由 s010 在 UI 内真实完成一次「检查→拆解→派发→跟进→验收」，全程只产生 canonical 事实（Request/Assignment/Work transition/Update），不新增第二真相源。

### 不做项
自动拆解/自动派发 Agent 化、Stage-Gate 重型引擎、Mailbox 广播、代行 Human-only 决策。

## C. 整体 UI：保留 / 下沉 / 重排

### 保留
- now-panel（当前承诺/状态主视图）、attention grid（Needs Me + Coordinator）、办公室三卡（活动 Session / 待处理 Request / 待整合）+ 最近变化 Delta、Work↔Agents 关系板、room 页单时间线。

### 下沉（现状已基本做到，保持）
- Advanced/Admin、Evidence & History、状态维护/纠错/Restore 已是 `<details>` subpage；不要回弹到一级视图。
- 候选下沉：project.html 的「项目状态 / 主要文件 / 随后事项」旧静态区块可并入 now-panel 或下沉，减少主视图长度。

### 重排候选
1. Coordinator 面板 → 升级为 B 的开工清单入口（最高优先，因为它是当前最大 UI-能力错位：API 有 29 个动作、UI 只有 1 个按钮）。
2. Session 页 AGENT MAILBOX 面板（工作区未提交改动）确认后随窄修包转正。
3. room 页按 s029 阶段 B 研究的三阶段推进（已提案待 Human 放行）：引用条+jump → participant 活动带 → 折叠/过滤。
4. D13 布局规则（回复靠右/新话题靠左/人类居中）已定稿，保持不翻。

### 不做项
Slack/Discord 双栏线程化、游戏化动画、token/成本展板、多层嵌套线程树、React 重写。

## 全局不做项（重申）
M4 Draft 之外的 Supervisor 扩展、M5C、知识图谱、证据评分、知识图谱型 Memory、任何未经验证的重型工作流引擎。当前阶段以真实使用证据驱动下一批需求。

## 附：审查中发现的待分流摩擦（系统级候选）
1. 工作区 66 个文件纯 CRLF 行尾漂移未提交，会持续污染未来真实 diff 的审阅（建议 maintainer 统一行尾策略/`.gitattributes`，一次性归零）。
2. `POST /continue` 在 HTTP 路由层未见 actor 强制校验（human-only 由 manifest/UI 约定 + Store execution-claim 兜底）；夺舍实验时可顺带记录真实行为，是否补路由层 actor 校验由 maintainer 决策。
