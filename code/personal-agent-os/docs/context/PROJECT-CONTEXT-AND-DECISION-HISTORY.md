# Personal Agent OS｜项目上下文与决策史

状态：面向新 Agent 的必读上下文  
最后整理：2026-07-31  
范围：本工作线程中已经形成、且会影响后续实现或审查的结论  
不包含：聊天逐字稿、真实 Vault 内容、Key、公司内部 URL、个人原始录音与业务细节

## 0. 如何使用这份文件

新 Agent 先阅读本文件，再阅读当前 GitHub Issue 和对应任务包。这里是“为什么这样做、哪些约束不能忘”的压缩上下文；Issue 和设计书才是当前任务的可执行规格。

如果本文件与更晚的 Issue、PR、设计书冲突，以更晚的可审查文档为准，并在交付中指出冲突，而不是自行猜测。

## 0.1 2026-07-31 流程降重决定

WorkBuddy 对首版计划的批评被接受：一次可回退的 32 文件代码迁移被配置了过重的设计、Dry Run、三阶段批准和多 Agent 审查，元工作已经接近超过实现价值。

后续以以下规则覆盖本文中较早的流程描述：

- T-002 的快速预检、复制、测试和 Draft PR 在同一轮完成；不再单独等待 Phase A / B 批准；
- Git 分支内可回退的代码与 Agent 生成文件属于 L1，默认直接实现、测试、PR；
- Dry Run 主要用于真实用户资料、不可重建文件、新外部写入或破坏性动作；
- 三天真实使用先于完整记忆治理；Skill、模型、NAS 和 Runtime 由真实问题触发，不预建；
- 成功标准包含系统交互时间下降：早晨确认不超过 3 分钟，日终不超过 5 分钟，每日可见候选不超过 3 条。
## 1. 一句话定义

Personal Agent OS 不是自动化一切的 Agent 平台，也不是聊天记录仓库。它是一个 **个人注意力与工作记忆控制面**：帮助一个同时处理产品、技术、市场、设计、沟通和项目的人，持续回答：

```text
今天最该推进什么？
哪件紧急事正在侵蚀主线？
这些信息最终改变了哪个决策？
什么应当保留为事实、候选、决策或可复用流程？
```

项目的长期目标是持续改善真实工作中的注意力、上下文恢复与交付闭环；它不以一次汇报或展示为完成条件。

## 2. 用户工作方式：系统为什么需要存在

用户是机器人/硬件背景的产品经理，能跨技术、市场、设计和产品机会建立复杂关联；当前并行工作包括正式产品任务、短期沟通/汇报、学习、长期 `obs-agent` 和个人 Agent 系统。

已反复验证的困难不是资料不足，而是：

- 多线程切换消耗大，紧急事务会挤压重要但不紧急的长期项目；
- 调研与信息收集很强，但容易在最终表达前失去“唯一因果主线”；
- 倾向保留信息熵，不愿过早砍掉可能性；
- 复杂系统本身可能成为新的研究黑洞；
- 需要保留人的顶层判断权，系统不能把“收集更多”误当成“完成更多”。

因此首页不以待办数量为目标，而是默认突出三条活跃主线；每条必须能说清：**当前唯一问题、阶段交付物、完成定义**。

## 3. 已冻结的产品原则

### 3.1 注意力是入口，记忆是长期价值

旧 `agent-co` 仍是 Agent 执行观察与协作经验的历史档案，不是新系统的 runtime 核心。Attention Dashboard 先解决“今天看什么”，但它相对纸笔的长期增量来自可追溯记忆，而不是更复杂的界面。

当前顺序改为：可运行基线 → 三天真实使用 → 一周记忆价值验证。Skill、模型、NAS、Runtime Bridge 和多 Agent 聊天室都留在候选池，只有被真实使用问题拉动时才进入。

### 3.2 记忆不是一个全局桶

系统区分：Session、Thread、Project、Domain、Operator、Evolution 六层。项目私有事实默认不跨项目召回；跨项目应优先复用方法与模式，而不是人物、会议、承诺或业务细节。

原始事件是事实源；派生索引可重建；规则或模型生成的内容只能是 candidate；Human Decision 不可被静默覆盖；Skill 必须先经过评测才进入正式工作流。

### 3.3 模型与审查按杠杆使用

- 强模型：架构、复杂取舍和真正需要发散收敛的任务；
- 中低成本模型：冻结规格下的实现、测试、分类和候选生成；
- 用户：顶层决策、优先级、信息范围与最终取舍。

低能力模型作为“边界是否足够清楚”的探针仍然有价值，但不再默认加入每个小任务。只在数据所有权、权限、破坏性操作、冻结规格或连续失败等高杠杆点使用。

### 3.4 设计书不是所有任务的门票

设计先行适用于跨组件、不可逆或会改变数据所有权的任务。隔离分支内、一天以内、验收明确的可回退实现，直接按短任务包完成测试和 Draft PR。规格不清时才回到高推理设计，而不是先制造一整套文档。

## 4. 已有资产与唯一来源

| 资产 | 定位 | 默认动作 |
|---|---|---|
| `C:\Users\remo\Desktop\skill库` | 个人 Skill 的唯一可编辑来源 | 默认只读；Skill 迭代时才修改 |
| `C:\Users\remo\Desktop\agent学习计划` | 研究实验室、计划、隔离原型 | 可读写 |
| `D:\Obsidian-Vault` | 长期认知、决策与阶段存档 | 写摘要和 Run Card |
| `D:\Obsidian-Vault-Backup` | 历史证据 | 只读 |
| `C:\Users\remo\Desktop\obs-agent` | 视觉/屏幕证据项目 | 默认只读，另开开发任务 |
| `xiangscream/agent-co` | 历史多 Agent 协作实验 | 归档参考，不作 runtime 依赖 |
| `xiangscream/personal-agent-os` | 新系统的代码、设计与可执行协作面 | 当前主仓库 |

早期盘点发现跨目录 Markdown 重复和过期信息问题，因此“复制更多资料”不是默认解法；必须明确来源、作用域、状态和可恢复路径。

## 5. 当前可运行原型：已证实，不要重造

### 注意力与记忆闭环 v1.2

原型位于：

```text
C:\Users\remo\Desktop\agent学习计划\.lab\prototypes\attention-dashboard-v1-static
C:\Users\remo\Desktop\agent学习计划\.lab\prototypes\attention-memory-pipeline-v0
```

它已证明以下链路：

```text
合成 Markdown
  → 只读扫描
  → attention-state/v0
  → Dashboard 数据适配
  → 本机 HTTP 服务（127.0.0.1:8766）
  → 浏览器 Dashboard
```

已具备：默认三条主线、长期项目补位、三段执行契约、来源路径/哈希/片段、候选审核、归档与复活卡、五层故障诊断、Tips 草稿与显式提交。

已验证：Pipeline 17 项 + Tips 服务 5 项 + Dashboard 10 项 = **32 项测试通过**。`build/` 是可删除重建的派生数据。

Tips 的经验尤其重要：浏览器 `localStorage` 只能保存草稿，不等于 Agent 已收到。只有用户显式提交后，Tip 才进入本机 Markdown Inbox；失败时草稿必须保留，重试必须幂等。

## 6. G0 为什么从“零代码迁移”改为最小修复

最初计划是把两个原型原样复制进新仓库。但检查发现 `local_server.py` 用父目录层数推导默认 Inbox。原型迁到仓库根目录后，该推导会漂移到错误位置。

因此当前 G0 只允许对既有逻辑做一项修复：

```text
--inbox 参数
  > PERSONAL_AGENT_OS_INBOX 环境变量
  > <repo>/private-data/inbox/tips
```

允许修改的既有文件仅为：

1. `attention-dashboard-v1-static/local_server.py`
2. `attention-dashboard-v1-static/tests/test_local_server.py`

除该边界外，不改 UI、排序算法、schema、扫描规则或产品功能。

## 7. 隐私、数据与操作安全

### 四层数据

| 层 | 进入 GitHub？ | 说明 |
|---|---:|---|
| Code & Planning | 是 | 代码、设计、脱敏样例、任务包 |
| Private Data Root | 否 | Vault 副本、真实 Inbox、DB、raw logs、个人资料 |
| Derived Data | 否 | 索引、缓存、扫描报告、构建产物 |
| Secret Store | 永不 | Key、Token、密码、公司凭据 |

Secret Store 根目录固定为：

```text
C:\Users\remo\Desktop\secrest
```

该目录不扫描、不索引、不上传、不记录到 Prompt/Markdown/日志。系统只能保存逻辑引用名和 schema；有首个获批消费者时再设计最小读取适配器。

### 其他硬约束

- 超过 20 个用户既有、不可重建或难以回退的文件先 Dry Run；有 Git 保护的仓库代码不机械套用该阈值；
- 默认只复制，不移动、不删除来源；
- 真实资料进入索引、模型、外部服务前单独开 Gate；
- 公司业务资料和凭据仍受公司政策约束，private GitHub 不是授权替代；
- 不自动安装系统软件、改 PATH、杀进程、开放局域网端口或部署后台采集；
- 失败三轮且无法定位时停下，把证据交回用户。

## 8. 用户环境与部署假设

- Windows 是日常交互环境；外部 Agent 主要在 WSL 中运行；
- WSL 已登录 GitHub CLI，账号为 `xiangscream`，可创建分支/PR；
- Windows 和默认 WSL PATH 未必已有 Python/Node；脚本必须先探测显式 `PAOS_PYTHON` / `PAOS_NODE`，不能暗中安装；
- Dashboard 只绑定 `127.0.0.1:8766`；端口冲突时停止报告，不自动杀进程或换端口；
- 长期可用设备包括一台 RTX 4070 SUPER 主机、NAS 与个人笔记本，但 NAS、局域网部署、本地模型均是后续选项，不是当前依赖。

## 9. Agent 协作协议

用户负责产品方向、Gate、信息范围、是否合并。设计 Agent 维护架构和任务包。实施 Agent 只做已解锁范围。审查 Agent 只读挑错，不取代决策。

实施 Agent 的默认交付格式必须包含：

```text
阶段 / 结论 / 文件清单 / 差异 / 测试 / HTTP 证据
数据或 Inbox 路径 / 敏感扫描 / Git 状态 / 停止条件 / 恢复 / PR
```

外部 Agent 不应在 Windows 归档副本 `C:\Users\remo\Desktop\agent学习计划\personal-agent-os` 开发，因为其中存在 Git 忽略的真实 `private-data/`。使用 WSL 文件系统中的新 clone 或 worktree。

## 10. 当前状态与唯一下一步

当前仓库：`xiangscream/personal-agent-os`（private）。

- T-001 已关闭；
- T-002 是唯一可领取任务；
- WorkBuddy 提到的 Phase A 报告没有进入 GitHub、当前项目目录、分支或 PR，因此没有可审查的独立 Phase A 成果；
- 更重要的修正是：T-002 不再要求独立 Phase A。实施 Agent 在同一轮做快速预检、白名单复制、最小 Inbox 修复、32 项测试、HTTP 验证与 Draft PR；
- T-002 合并后先进行三天真实使用，而不是立即建设完整 G1/G2/G3 架构。

当前任务入口：

- GitHub Issue #2：`[T-002][G0] 建立 Attention Dashboard 可运行仓库基线`
- `docs/planning/08-AGENT-TASK-T002-G0-BASELINE-IMPLEMENTATION.md`
## 11. 历史时间线：保留原因，不重复执行

| 阶段 | 已获得的结论 | 不应回退的原因 |
|---|---|---|
| 长期系统基线 | 系统应围绕真实工作持续演进，而非追求工具数量 | 已有真实项目、Skill、记忆和协作证据 |
| Skill 治理 | Skill 必须有触发/不触发边界与前向评测 | 已观察到过度触发与规则膨胀风险 |
| 分层模型协议 | 高推理设计，低成本实现/审计 | 降低 Token 成本，同时保留架构审查 |
| Dashboard v0 | 三条主线、手动排序、推进债务、Tip 捕获有产品价值 | 解决注意力切换，而非展示技术 |
| Memory Pipeline v0 | 来源、哈希、候选与事实必须分离 | 防止规则/模型把推断升级为事实 |
| Dashboard v1.1 | Tips 必须显式提交到可审查 Inbox | localStorage 不是长期记忆 |
| Dashboard v1.2 | 每条主线需要执行契约 | 排序本身不能保证交付 |
| 私有资料初始归档 | 真实资料可留在本机 Private Data Root | GitHub 不能成为个人资料仓库 |
| G0 v0.2 | 迁移前先修正路径所有权 | “零代码复制”会把 Tips 写错位置 |

## 12. 新 Agent 的第一轮检查清单

1. 阅读本文件和当前任务包；
2. 用不超过 8 条复述目标、允许改动、验证和停止条件；
3. 确认工作区是隔离分支，不读取 `private-data/`、`secrest` 或真实 Vault；
4. L1 任务直接实施、测试并创建 Draft PR；
5. 只有真实资料、不可重建文件、Secret、权限或破坏性动作才升级为 Dry Run / 明确批准；
6. 若同一问题三轮仍失败，返回最小复现，不继续加功能。
## 13. 参考入口

| 资源 | 用途 |
|---|---|
| `docs/planning/00-MASTER-BUILD-PLAN-v0.1.md` | v0.2 阶段顺序、风险分级与使用指标 |
| `docs/planning/04-AGENT-HANDOFF-AND-BUILD-QUEUE.md` | 当前任务队列与角色协议 |
| `docs/planning/06-PRIVATE-DATA-MIGRATION-POLICY.md` | 私有资料与 Secret 边界 |
| `docs/planning/07-G0-REPOSITORY-BASELINE-DESIGN-v0.2.md` | 当前 G0 设计冻结 |
| `docs/planning/08-AGENT-TASK-T002-G0-BASELINE-IMPLEMENTATION.md` | 当前实施 Agent 指令 |
| `D:\Obsidian-Vault\10-Projects\Agent协作体系` | 阶段 Run Card、决策与复盘 |
| `C:\Users\remo\Desktop\agent学习计划\08-Agent研究实验室` | 原型、教程和实验记录 |

---

本文件由历史对话和已落盘的阶段材料压缩而成。它应在每个 Gate 后只增补已验证的决策、证据和废弃假设；不把临时聊天、未验证想法或敏感原文混入长期上下文。
