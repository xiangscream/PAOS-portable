# PAOS v0.4 可用闭环总体设计与实施任务

> 状态：设计收敛稿 v1
> 日期：2026-08-09
> 代码基线：`388f5ad`（`agent/v04-drop-v1`）
> 事实输入：`C:\Users\remo\Desktop\agent学习计划\06-资料库\PAOS现状快照-v0.4-给Codex设计输入.md`
> 实施对象：Codex 负责总体设计和验收；DeepSeek V4 Flash 等实施 Agent 按任务包顺序完成

本文是 v0.4 的实施唯一来源。现状快照负责记录事实，本文负责回答“做什么、为什么、做到什么程度”。旧的 `09-V02-SESSION-LOOP-FRAMEWORK-DESIGN.md` 保留为历史设计，不再用它决定 v0.4 的实施范围。

---

## 0. 当前结论

PAOS v0.4 的目标不是继续增加抽象层，而是把已经具备的写入能力收成一个能日常使用的 Agent 协作闭环。

一句话定义：

> PAOS 是一个本机 Agent 协作记录台：用户把一件可完成的工作交给 Agent，Agent 复述理解、完成工作并登记结果，PAOS 保存上下文和证据，再把下一步清楚地交还给用户。

产品力主线：

```text
少重复解释
  → Agent 先复述目标和边界
  → 工作过程只在必要时报告
  → Close 一次登记成果、产物与剩余事项
  → PAOS 把结果投影成可继续、可评审、可归档的下一步
```

v0.4 的三个关键词：

- **单一路径**：日常只保留一个 Work → Session 启动入口。
- **完整投影**：凡是已经写入的关键数据，用户都能看见并使用。
- **渐进揭示**：日常界面隐藏协议；开发/学习区域再展示 revision、Ledger、回执和原始合同。

---

## 1. 基线与真实问题

### 1.1 已经成立的能力

- 项目 JSON 原子写、备份与恢复；
- revision 乐观锁；
- operation ID + request hash 幂等；
- Ledger 与 operation receipt 证据记录；
- Session 的 Open → Ack → Update → Close 状态机；
- Context Pack 与 Prompt 生成；
- Windows 开机自启动已安装并端到端验证；
- v1 项目 schema 已删除，当前只有 `paos-project/v2`。

这些能力不需要推倒重做。v0.4 只修正边界并让它们真正服务日常行为。

### 1.2 真实使用暴露的问题

1. 只有一次完整真实 Session；测试通过不等于使用顺畅。
2. 两条 Session 入口并存，完整生命周期与顺畅创建 Work 没在同一条路径上。
3. Close 已保存剩余工作和交接说明，但页面只显示一句摘要。
4. Context Pack 页面只有 ID，正文永远停在“等待加载……”。
5. Request 和 Decision 可以产生，但日常界面缺少处理出口。
6. `source_path` 和 Artifact 路径存在，但没有日常直达与失效反馈。
7. Agent 第一次真实调用时仍会写错字段形状和状态值，错误虽然可见，但不够指导下一步。
8. `session_service.py` 直接读写 Context Pack，违反“Store 是唯一持久状态写者”的分层约束。
9. UI、README、测试套件名称仍暴露 v0.2/v2 等历史代号。
10. `progress` 是 Agent 自述，不是系统验证过的客观事实；当前界面没有表达这一区别。

### 1.3 三条闭环不变量

后续设计和审查统一使用下面三条，而不是不断追加零散规则：

1. **写入一份数据，就必须有对应的读取投影。**
2. **用户触发一个动作，就必须看到真实结果或明确失败。**
3. **日常界面出现一个对象，就必须有下一步或结束动作。**

Context Pack 空白、Close 数据不可见和自启动静默失败，本质上都违反了其中一条。

---

## 2. v0.4 的目标体验

### 2.1 一条主流程

```text
进入项目
  → 选择未完成 Work，或直接新建 Work
  → 创建 Session 并复制 Prompt
  → Agent Ack：复述目标、边界、首步和风险
  → Agent 工作；只有真实阶段变化或阻塞时才 Update
  → Agent Close：结果、产物、剩余事项、建议下一步
  → 用户查看完整结果
  → 继续当前 Work / 创建后续 Work / 发起评审 / 归档会话
```

正常使用不需要命令行、curl、手写 JSON 或理解 revision。协议仍然存在，但只在高级区域和 Agent Prompt 中出现。

### 2.2 Work 与 Session 的关系

- Work 是一个可完成成果，可以跨多个 Session。
- Session 是一次具体 Agent 协作。
- 未完成 Work 可以继续开新 Session。
- `done` Work 不静默重新打开；如果出现新目标，创建一个预填上下文的后续 Work。
- 新建 Work 与 Open Session 必须在同一次原子 mutation 中完成，不能先写半个 Work 再尝试开 Session。

### 2.3 Update 的定位

Update 是可选的，不是日报制度。只在以下时刻使用：

- 形成可复用阶段成果；
- 工作方向发生变化；
- 出现阻塞或需要人的输入；
- 长任务需要留下可接续状态。

页面统一使用“Agent 最近一次报告”，不把 `progress` 写成“项目真实进度”。

### 2.4 Close 与归档的区别

- **Close**：结束 PAOS 中的 Session 生命周期，登记结果与剩余工作。
- **归档**：把原生对话或总结保存为可长期打开的文件，并登记为 Artifact。

归档不重新打开已关闭 Session。v0.4 增加一个窄的“追加 Session Artifact”合同，允许关闭后补充会话归档，但不能修改 Close 结果和历史证据。

### 2.5 日常区与开发/学习区

不建立复杂的全局模式系统，先用渐进展开实现：

**日常区默认展示：**

- 本轮目标；
- Agent 对目标的理解；
- Agent 最近一次报告；
- 最终结果、剩余工作和下一步；
- Artifact、Request 和会话记录入口。

**高级区域折叠展示：**

- Identity / Mode / Context Level / Runtime / Model；
- revision、Ledger、operation receipt；
- Context Pack 原文；
- Manual Writeback envelope；
- 高级纠错入口。

---

## 3. 功能取舍

### 3.1 v0.4 核心功能

没有这些功能，主流程不成立：

1. Close 完整结果投影；
2. Context Pack 可靠存储与真实加载；
3. 单一 Work + Session 启动入口；
4. Session 状态驱动的下一步；
5. Session 最近活动排序与历史折叠；
6. Artifact、会话记录和归档可访问；
7. Request 到后续 Session 的最小交接；
8. 错误、日志与正式回执可见。

### 3.2 关键支撑

- Store 成为 Context Pack 的唯一持久化入口；
- 标准库 logging；
- 独立领域错误模块；
- 清晰的 Session Detail 读投影；
- 一条真实旅程测试与手工浏览器验收；
- README 和架构说明与当前实现一致。

### 3.3 保留但退出日常主路径

- `quick` / `collaborative`：后端暂时保留，Launcher 默认只展示 `managed`；高级区域可实验。下一轮按真实使用决定删除或正式化。
- 六个 Identity：默认使用 `implementer`；`reviewer`、`integrator` 只在评审和交接动作中出现；其余身份不占据日常入口。
- `brief / standard / deep`：由系统按职责给默认值，用户可在高级区域修改。
- Decision Proposal：保留数据和高级只读展示，本版不新增接受/拒绝合同；日常 Project Office 不再突出一个没有出口的对象。
- 旧 Tips Dashboard：保留为独立原型入口，不把它混入项目与 Session 主流程。

### 3.4 v0.4 明确不做

- SQLite 或其他数据库迁移；
- FastAPI、Pydantic、ORM、前端框架；
- 全局全文搜索、RAG、向量库；
- 自动启动或调度外部 Agent；
- 多用户、局域网、远程访问和新安全体系；
- Agent 直接编辑 PAOS 非框架文件；
- 完整跨项目晨间页；
- 为未发生的异常输入继续增加攻击测试；
- 大目录迁移或为了“像大项目”而拆十几个空模块。

上述方向只能由真实使用或部署范围变化重新触发。

---

## 4. 目标代码边界

v0.4 不重写技术栈，也不做大包结构迁移。目标关系是：

```text
Browser
  ↓ HTTP / JSON
local_server.py        传输、路由、错误映射、静态文件
  ↓
session_service.py     Session 状态机和业务编排；不碰磁盘路径
  ↓
project_store.py       项目 JSON、Context Pack、备份、Ledger、回执的持久化入口

纯模块：
session_contracts.py   请求归一化和校验
project_schema.py      当前项目 schema 校验（由 project_store_v2.py 更名）
session_projection.py  Session Detail 只读投影
context_compiler.py    Context Pack 与 Prompt 编译
office_projection.py   Project Office 只读投影
errors.py              领域错误和稳定错误码
```

允许的磁盘写入例外只有运行日志。日志是运维记录，不是项目事实状态；由标准库 logging handler 负责，不经过 ProjectStore。

### 4.1 Store 的 Context Pack 合同

Store 至少提供：

```python
context_pack_path(project_id, pack_id) -> Path
read_context_pack(project_id, pack_id) -> dict
write_context_pack_atomic(project_id, pack_id, payload, *, operation_id, request_hash) -> Path
```

约束：

- Service 不读取 `store.root`，不自行拼目录；
- Pack 使用临时文件、flush、fsync、重读校验和 `os.replace`；
- 不覆盖不同 operation 产生的既有 Pack；
- Pack 写失败时项目状态不得提交；
- 项目提交失败最多留下无项目引用的完整孤立 Pack，不能留下指向损坏/半写 Pack 的正式 Session；
- 同一 operation 重试可以复用内容一致的孤立 Pack；
- 旧 Pack 缺少新增元数据时仍可读取，不改写历史快照。

### 4.2 Session Detail 读投影

`GET /api/projects/{project_id}/sessions/{session_id}` 返回：

```json
{
  "ok": true,
  "project_revision": 42,
  "session": {},
  "context_pack": {
    "status": "available",
    "content": {},
    "path": "..."
  },
  "timeline": [],
  "artifacts": [],
  "requests": []
}
```

`context_pack.status` 为 `available / missing / invalid`。缺失或损坏必须显示为可读状态，不能让整个 Session 页面 500，也不能静默重建一份冒充原快照。

Timeline 只取 `ledger[].session_id == 当前 Session` 的事件，按 revision 升序展示。

`project_revision` 是页面生成后续窄写入 Prompt 时使用的当前 revision；不能回退使用 Session Open 时写入 `entry` 的历史 revision。

### 4.3 Open 时原子创建 Work

`paos-session-open/v1` 增加可选字段：

```json
{
  "work_item_ids": [],
  "new_work": {
    "title": "一次可完成成果",
    "objective": "为什么做",
    "done_when": ["完成条件"],
    "depends_on": []
  }
}
```

合同要求：

- `work_item_ids` 非空与 `new_work` 二选一；
- 既有 Work 必须存在且不是 `done/cancelled`；
- 新 Work 与 Session 在同一次 mutation 中分配 ID、追加 Ledger 和 receipt；
- 幂等重试不重复创建 Work 或 Session；
- 前端日常只允许选择一个既有 Work，但 API 保留关联多个 Work 的已有能力。

### 4.4 关闭后追加归档 Artifact

新增窄合同：

```text
POST /api/projects/{project_id}/sessions/{session_id}/artifacts
schema = paos-session-artifact-add/v1
```

只允许：

- 追加 Artifact；
- Artifact 归属当前 Session；
- 保留 operation ID、revision、Ledger 和 receipt；
- Session 已关闭或仍 active 均可使用；
- 不修改 status、progress、Close Result、human 字段或既有 Artifact。

它用于“补充会话归档”，不是第二套通用更新接口。

### 4.5 错误响应

保留现有 `error` 字符串以减少一次性改动，同时增加：

```json
{
  "ok": false,
  "error": "可读中文原因",
  "error_code": "revision_conflict",
  "hint": "刷新项目后重新复制 Prompt；未保存的输入仍保留",
  "details": {}
}
```

前端优先展示 `error + hint`。日志记录堆栈，HTTP 响应不暴露堆栈。

---

## 5. 实施顺序

任务必须顺序实施，不并行修改共享文件：

```text
T-V04-01 Close 投影
  → T-V04-02 Pack 存储边界
  → T-V04-03 Session Detail 完整投影
  → T-V04-04 日志与错误基础
  → T-V04-05 Open 原子创建 Work
  → T-V04-06 单一 Launcher
  → T-V04-07 删除旧入口
  → T-V04-08 日常导航与下一步
  → T-V04-09 Request 交接与归档
  → T-V04-10 后端可读性重构
  → T-V04-11 前端与文档收口
  → T-V04-12 发布验收
```

前三包先兑现已有数据和正确边界；中间六包完成用户闭环；最后三包把成品整理成学习样本。

---

## 6. 所有实施 Agent 的共同合同

每个任务 Prompt 都必须带上以下约束；任务包内不再重复全部背景：

1. 先读 `AGENTS.md`、`docs/DEVELOPMENT-PRINCIPLES.md` 和本文。
2. 只做当前任务，不顺手处理下一任务或无关风格问题。
3. 不读取、扫描、写入真实 `private-data/`；测试使用 fixture 或 `TemporaryDirectory`。
4. 不修改用户现有未提交文件 `attention-dashboard-v1-static/FRONTEND-DESIGN-v1.2.md`。
5. `.py/.mjs/.md` 保持 LF；`.ps1` 保持 BOM + CRLF。
6. 先跑目标测试，再跑 `scripts/verify.ps1`；如失败，停下并说明，不修补无关代码。
7. 只为正常路径、静默状态损坏、核心公共合同增加阻塞测试；不追求测试数量。
8. 每包一个独立提交；不 push、不开 PR、不合并，除非用户或集成 Agent 明确授权。
9. 交付必须报告：改了什么、用户现在能多做什么、目标测试、全量测试、未完成项、工作区状态。
10. 重构包必须做到“只搬职责，不改行为”；行为变化只能出现在功能包中。

---

## 7. 任务包

### T-V04-01｜把 Close 结果完整还给用户

**用户结果：** 打开已关闭 Session，立即看见已有的完整结果与下一步，不再丢掉 6 条 `remaining_work` 和交接说明。

**范围：**

- `session-model.mjs` 增加纯 `sessionOutcomeView()`；
- `session.html/session.mjs` 展示 result、result summary、remaining work、recommended next identity、note for next session；
- Ack 同时展示 `detected_risks`；
- `progress` 标题改为“Agent 最近一次报告”；
- 空值使用明确空态，不显示 `undefined/null`。

**不做：** 不改 API、Store、schema、Context Pack、Session 状态机。

**目标文件：**

- `attention-dashboard-v1-static/session-model.mjs`
- `attention-dashboard-v1-static/session.mjs`
- `attention-dashboard-v1-static/session.html`
- `attention-dashboard-v1-static/tests/session-model.test.mjs`

**验收：**

- 一个含 6 条 remaining work 和长交接说明的 fixture 能完整投影；
- 一个没有 Close Result 的 active Session 显示正常空态；
- 新增测试不超过 2 个；
- 浏览器手工确认真实 `3002-s009` 的既有内容可见，手工确认只读，不写项目数据。

### T-V04-02｜让 Store 真正拥有 Context Pack

**用户结果：** Context Pack 不会半写损坏；Open 失败时不会留下正式 Session 指向坏文件。

**范围：**

- 在 `ProjectStore` 增加 Pack 路径、读取和原子写方法；
- `session_service.py` 删除 `Path`、`read_text/write_text` 和 `store.root` 路径推断；
- Pack 写入带 operation ID/request hash 元数据；
- 明确 Pack 与项目提交的先后关系及孤立 Pack 重试规则。

**不做：** 不改 Session 页面和 HTTP 返回形状，不重建或改写既有 Pack。

**目标文件：**

- `project_store.py`
- `session_service.py`
- `tests/test_project_store.py`
- `tests/test_v2_sessions.py`

**验收：**

- 强制 Pack 写失败：revision、Session、Ledger、receipt 全部不变；
- Pack 文件始终是可重新读取的完整 JSON；
- 不同 operation 不覆盖 Pack；相同 operation 重试可恢复；
- `session_service.py` 不再出现 `.root`、`Path`、`read_text`、`write_text`。

### T-V04-03｜完成 Session Detail 只读投影

**用户结果：** Context Pack 正文、Session 时间线、Artifact 和 Request 真正出现在页面；缺文件时页面告诉用户发生了什么。

**范围：**

- 增加纯 `session_projection.py`；
- 扩展现有 Session Detail GET 响应；
- Session 页面使用 Detail 响应，不再拉整个 Project 后自行筛选；
- 替换写死的“等待加载……”；
- Timeline 展示 Open/Ack/Update/Close 事件；
- Pack missing/invalid 显示可恢复提示，不自动重建。

**不做：** 不增加写接口，不改变 Ledger，不做全项目时间线。

**目标文件：**

- `session_projection.py`（新增）
- `session_service.py`
- `local_server.py`
- `session-model.mjs`
- `session.mjs`
- 对应 Python/Node 测试

**验收：**

- API 返回真实 Pack content；
- 页面正文不再保留“等待加载……”字面量；
- missing/invalid Pack 均返回 200 + 状态对象，页面明确显示；
- 测试必须断言正文内容，不得只断言 HTML ID 存在。

### T-V04-04｜让错误和运行状态可见

**用户结果：** 自启动运行后有可查日志；写入失败能说明对象、原因和下一步。

**范围：**

- 新增 `errors.py`，承接领域异常与稳定错误码；
- 消除 `session_contracts.py`、`office_projection.py` 对 Store 错误/常量的横向依赖；
- 标准库 `logging` + `RotatingFileHandler` 写入 `private-data/logs/paos.log`；
- 记录服务启停、写操作结果和未处理异常；
- 覆写 `http.server` 默认请求日志；
- 错误响应增加 `error_code/hint/details`，保留旧 `error` 字符串。

**不做：** 不记录请求正文、Prompt、项目内容和 Secret；不重构路由表。

**验收：**

- 原有 404/409/422 映射与状态码不变；
- 一次成功写入和一次模拟异常都能在临时日志中定位；
- revision 冲突提示当前 revision 和刷新建议；
- 真实日志目录仍被 Git 忽略。

### T-V04-05｜Open 原子创建新 Work

**用户结果：** 没有未完成 Work 时，用户可以直接创建 Work 并启动完整生命周期 Session。

**范围：**

- `normalize_open_payload` 支持 `new_work`；
- `open_session` 在同一次 mutation 中创建 Work、Session、Pack、Ledger 和 receipt；
- 既有 Work 与新 Work 二选一；
- 既有 `done/cancelled` Work 拒绝新开 Session；
- 新 Work 的 `depends_on` 可用于“后续 Work”。

**不做：** 不改前端，不删除旧 handshake，不增加独立 Work 创建 API。

**验收：**

- 正常路径只增加一次 revision；
- receipt/ledger 的 `allocated_ids` 同时含 Work 和 Session；
- 幂等重试不产生重复 Work/Session/Pack；
- 任一步失败不写半个 Work；
- 现有 `work_item_ids` Open 仍正常。

### T-V04-06｜建立唯一的日常 Launcher

**用户结果：** 项目页只有一个明确入口；既能选 Work，也能新建 Work，并复制完整 Session Prompt。

**范围：**

- 当前完整生命周期 Launcher 成为唯一主入口；
- Work 选择增加“新建 Work”模式；
- 默认 `implementer + managed + 自动 context`；
- Mode、Identity、Context、Runtime/Model 收进高级设置；
- 创建成功后显示 Session ID、正式 receipt、查看 Session 按钮和复制成功状态；
- 没有可用 Work 时默认进入新建，不显示终止性的“无可用 Work”。

**不做：** 本包只移除旧入口的 UI，不删除后端旧 handshake 代码。

**验收：**

- 选择既有 Work 和新建 Work 两条正常路径均可用；
- 用户无需手工刷新即可进入新 Session；
- 项目页不再同时展示两个 Launcher；
- 日常区域不出现 v0.2/v2 字样。

### T-V04-07｜删除旧 Session 接入路径

**用户结果：** 产品和代码只有一条 Session 接入语义，未来阅读不再需要推理两套流程。

**范围：**

- 删除 `/api/agent/handshake` 及其 Store adapter、Prompt 生成和专属测试；
- 从 `AGENTS.md` 删除旧 Session Handshake 触发规则；
- 保留 requirement/list 两个窄写入协议；
- 更新协议文档，只描述仍存在的入口；
- 历史 Session 的 `handshake_id` 作为可读旧数据保留，不迁移、不清空。

**不做：** 不删除历史 Session，不改 Ledger/receipt，不借机重写 requirement/list 合同。

**验收：**

- `rg` 找不到旧 handshake endpoint 和 Prompt tag 的运行时代码；
- 当前 Launcher Open/Ack/Update/Close 完整通过；
- 测试总数允许下降，报告删除的是哪类旧路径测试，不以数量下降为失败。

### T-V04-08｜把项目页和 Session 页变成日常入口

**用户结果：** 用户先看到当前要处理什么，再按需展开历史和协议细节。

**范围：**

- Session 按 `last_active_at` 倒序；
- 默认显示最近 10 条，其余放入“更早 Session”折叠区；
- active/pending_ack/blocked 状态有明确下一步提示；
- 已关闭 Session 提供“继续 Work”“创建后续 Work”“发起评审”预填入口；
- Session 页展示 `runtime_session.source_path`、Artifact 路径和存在/缺失状态；
- 先提供可靠的复制路径；平台打开动作只有在可稳定验证时才加入；
- Project Office 改成中文动作语言，空对象不占据大卡片；
- 协议字段移入高级折叠区。

**不做：** 不做全局搜索、跨项目晨间页和路径全文索引。

**验收：**

- 11 条以上 Session 时首屏恰好 10 条且顺序正确；
- 更早历史可展开且数据未删；
- broken source path 可见但不阻塞页面；
- “继续/后续/评审”只预填 Launcher，不自动启动 Agent。

### T-V04-09｜补上 Request 交接与会话归档

**用户结果：** 开放 Request 可以自然交给下一个 Session；关闭后的原生对话可以作为 Artifact 补充归档。

**范围：**

- Request 卡增加“以此请求启动 Session”；
- 预填 `request_ids`、目标 Identity、Mission 和来源 Session；
- 新 Session 可通过既有 `request_updates` 完成 Request；
- 增加关闭后追加 Artifact 的窄合同、服务方法和 receipt；
- Session 页生成“归档会话 Prompt”；
- 归档 Agent 保存 Markdown 后登记 `type=session_archive` Artifact；
- Decision Proposal 移入高级只读区，本版不提供假动作。

**不做：** 不自动调用 Agent，不自动接受 Decision，不引入新 Archive 实体。

**验收：**

- Request → 新 Session → resolved 的真实临时 registry 旅程通过；
- closed Session 可追加一个 Archive Artifact，但 close_result 字节不变；
- 幂等重试不重复 Artifact；
- 日常界面不再突出无出口的 Pending Decision 卡。

### T-V04-10｜后端可读性重构

**用户结果：** 无直接界面变化；代码边界足够清楚，可作为后端分层学习样本。

**范围：**

- `do_POST/do_PUT` 改为与 GET 一致的路由表；
- `_apply_bundle` 拆成 progress、Work、Artifact、Request/Decision、Close 五段明确函数；
- `project_store_v2.py` 更名为 `project_schema.py`，`V2_*` 运行时代号改为当前领域名；
- 保持 `ProjectStore` facade，不做大目录迁移；
- 删除已无调用的 helper、import 和历史注释。

**不做：** 不改 URL、状态码、JSON 字段、状态机和用户文案。

**验收：**

- 路由等价性覆盖当前全部 API；
- 重构前后临时 registry 的响应体一致；
- `session_service.py` 没有 >100 行函数；
- 失败时回滚本包，不通过修改业务行为“修测试”。

### T-V04-11｜前端与文档成为学习入口

**用户结果：** README 能独立带用户跑通系统；代码中不再残留误导性的版本语言和重复基础函数。

**范围：**

- 提取共用 `ui-common.mjs`：`api`、HTML 转义、错误展示、剪贴板反馈；
- 纯 view model 承担状态判断，DOM 文件只渲染和接事件；
- 清理 UI、注释和 verify 套件中的 v0.2/v2 历史标签；
- 更新 README：五分钟启动、一个完整 Session、日志位置、失败恢复；
- 新增 `docs/ARCHITECTURE.md`：模块图、写路径、读投影、三类数据语义；
- 更新 `VERSION_HISTORY.md`，不在长期文档硬编码易过时的行数。

**不做：** 不引入 UI 框架、构建工具、Ruff/ESLint 或新的运行依赖。

**验收：**

- 新用户只按 README 能启动并理解一次完整流程；
- 前端基础 helper 只有一份；
- schema/protocol 内部版本字符串保留，日常用户界面不显示历史开发代号；
- Markdown 无冲突标记、代码围栏成对、链接存在。

### T-V04-12｜发布验收与真实使用起点

**用户结果：** v0.4 从“测试项目”变成可开始一周真实使用的版本。

**范围：**

1. 运行目标测试与 `scripts/verify.ps1`；
2. 临时 registry 完成完整旅程；
3. 手工打开三个静态入口；
4. 由用户明确授权后，才在真实项目完成一次新 Work → Open → Ack → Close；
5. 检查日志、Context Pack、Timeline、Close 投影、Archive Artifact 和下一步；
6. 形成一页发布证据和一周观察清单。

**不做：** 实施 Agent 不自行写真实 `private-data/`，不 push/merge，不以测试总数作为发布结论。

**发布必须演示：**

```text
Windows 登录后服务可用
  → 打开 Projects
  → 新建 Work 并创建 Session
  → Prompt 交给一个真实 Agent
  → Ack 后工作
  → 可选 Update
  → Close
  → 页面看见完整结果与时间线
  → 创建后续 Work 或登记会话归档
```

---

## 8. 测试策略

### 8.1 不再用测试总数代表成熟度

每个核心合同只保留：

- 一个真实正常路径；
- 一个最关键失败路径。

已删除功能对应的测试同步删除。只有普通正常路径曾失败、可能静默损坏状态、核心公共合同易复发时才新增永久阻塞测试。

### 8.2 三类测试

**Store 不变量：**

- 原子写；
- revision/幂等；
- Pack 与项目提交关系；
- 证据 append-only。

**业务旅程：**

- Existing Work → Session；
- New Work → Session；
- Ack → optional Update → Close；
- Request → follow-up Session；
- closed Session → Archive Artifact。

**前端投影：**

- 输入完整 Session 数据，断言用户最终能看到的 view model；
- 不再把“HTML 中存在一个 ID”当作内容已展示；
- 中文、空字段、长文本、Windows/WSL 路径使用脱敏真实形态 fixture。

### 8.3 每包验证顺序

```text
目标纯函数/模块测试
  → 目标 API/Store 测试
  → scripts/verify.ps1
  → 受影响页面手工 smoke
  → git diff --check
```

静态文件兜底仍需手工确认：

```text
GET /attention-dashboard-v1-static/projects.html
GET /attention-dashboard-v1-static/project.html?id=3002
GET /attention-dashboard-v1-static/session.html?id=3002&session=3002-s009
```

---

## 9. v0.4 完成定义

只有全部满足，才能称为 v0.4：

### 用户闭环

- 项目页只有一个日常 Session 入口；
- 新建 Work 与启动 Session 一次完成；
- 不用命令行可走完 Open → Ack → Close；
- Session 页展示全部关键 Ack、报告、Close、Artifact、Request 和 Timeline；
- Context Pack 正文真实可读，损坏/缺失明确可见；
- Close 后有继续、后续 Work、评审和归档动作；
- 最近 10 个 Session 顺序正确，历史可展开；
- 所有日常可见对象都有下一步或结束动作。

### 可靠性与架构

- ProjectStore 是项目状态和 Context Pack 的持久化入口；
- Session Service 不猜磁盘布局；
- Pack 不会半写，失败不产生正式坏引用；
- Ledger、receipt、close_result 不被迁移或恢复覆盖；
- 错误有中文原因、稳定 code、恢复 hint 和日志；
- 自启动后服务状态可确认。

### 学习样本

- README 可独立上手；
- 架构文档与代码边界一致；
- 路由、服务、Store、合同、投影职责清楚；
- 长函数按业务职责拆分，而不是机械切段；
- 日常 UI 隐藏协议，高级区域可查看完整证据；
- 测试说明行为，不用历史工单名和数量制造成熟感。

---

## 10. v0.4 之后的触发条件

### SQLite

只有出现以下任一真实需求才讨论：

- 跨项目组合查询开始产生大量手写扫描逻辑；
- Session/Artifact/Ledger 数量使页面扫描出现可感知延迟；
- 需要全文搜索；
- 需要真正的多对象事务。

在此之前 JSON 仍是事实源。若先需要搜索，优先考虑“JSON 事实源 + 可重建 SQLite 读索引”，不立即迁移全部写路径。

### FastAPI/Pydantic

只有当手写传输、路由和校验代码持续压过业务代码，或者用户明确进入现代后端框架学习阶段时再评估。框架迁移不得和功能闭环在同一版本进行。

### 自动 Agent、RAG、直接文件编辑

只有一周真实使用证明“复制 Prompt、寻找资料或登记 Artifact”已经成为主要摩擦时，再从最小动作设计；不预埋调度器、索引框架或权限体系。

### 未验证 Identity/Mode

一周真实使用后统计选择次数与实际行为差异：

- 没有独特行为的项删除；
- 有清晰场景但入口太深的项再正式化；
- 不以“以后可能有用”作为永久保留理由。

---

## 11. 一周使用只观察五件事

v0.4 发布后不立刻开发 v0.5，只记录：

1. 哪一步仍需要用户解释协议或打开终端；
2. 哪类 Close 结果最常被继续使用；
3. 用户是否真的创建 Request、评审 Session 或归档 Artifact；
4. `source_path`、Artifact 和 Timeline 是否足够找回上下文；
5. 哪种跨项目查询第一次让 JSON 扫描显得不够用。

这些记录决定 SQLite、晨间页、搜索、自动 Agent 和直接文件编辑的真实优先级。
