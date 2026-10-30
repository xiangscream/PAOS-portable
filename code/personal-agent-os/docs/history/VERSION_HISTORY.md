# 版本历史

## v0.5 最小 Work/Session 闭环（2026-08-13）

**Work 跨 Session 接力，Session 按周期复用；当前实现已收口，PR #5 仍为 Draft。**

- Work 可持续跨多个 Session 推进；Session 支持 Reactivate、Switch Work，并追加周期历史
- Close 结果、Context Pack、Session Detail、Timeline 和下一步交接统一按当前周期投影
- `current_work_item_id` 是唯一当前可写 Work；`work_item_ids` 只保留历史关联
- `ProjectStore.mutate_v2()` 继续作为唯一原子写入入口，Pack 写入失败不提交项目状态
- Restore 保留 Ledger 与 `operation_receipts` 作为证据，并追加 `state.corrected`
- Restore 后旧 operation 失去重放资格，统一返回 409；不增加 revision、不追加 Ledger、不改变项目状态
- 提交 `8dd56f6`：补齐 Ack/Update/Close/Reactivate/Switch 的 Restore 后重放边界测试
- 当前验证：10 个套件、276/276 通过；未对真实 `private-data` 做写入冒烟

## v0.4 (2026-08-06) — 删除 v1，只留一种 schema

**迁移完成后不再维护双 schema 分支**（开发准则第 1 条）。

- 8 个真实项目全部迁移到 `paos-project/v2`（迁移前独立快照 + SHA256 + 守恒验证）
- 删除后端 v1 路径：`validate_project` / `update_project`（整份 PUT）/ `is_v2` / `migrate_v1_to_v2_file` / v1 handshake 主体 / `_handshake_receipt` / `migrate_v1_to_v2`
- `project_store.py` 1775 → 1497 行；`project_store_v2.py` 383 → 231 行
- `empty_project` 直接产出 v2 骨架，成为唯一骨架定义点；`empty_v2_project` 降为别名
- 删除前端 13 处 `schema === "paos-project/v2"` 判断、v1 Session 卡片、v1 编辑器分支，以及 `buildSavedHuman` / `humanFieldsChanged` / `nextWorkItemId`
- `PUT /api/projects/<id>` 只接受 `paos-project-manual-update/v1`，整份覆盖返回 422
- revision 守卫下移到 store（唯一写者）：`update_v2_manual` 缺少 revision 直接 `ValidationError`，任何调用方都绕不过乐观锁
- 迁移脚本 `scripts/migrate_project_v1_to_v2.py` 退役（送回收站）；v1 fixture 换成真实 v2 形态
- 新增 `docs/DEVELOPMENT-PRINCIPLES.md`：9 条开发准则、安全边界五条保留项与推迟清单、Agent 直接编辑非框架文件的设计前提
- 九套件共 216 项测试（Pipeline 25 + API 35 + Store 46 + v2 Store 17 + Session 生命周期 20 + T-101 24 + 旧 Dashboard 10 + Project Board 31 + Session Model 8）

## v0.4 可用闭环 (2026-08-09) — 把写入能力收成日常闭环

**目标：单一路径、完整投影、渐进揭示。** 不增加抽象层，把已有写入能力收成能日常使用的 Agent 协作闭环（设计书 docs/planning/10-V04-USABLE-CLOSURE-DESIGN.md）。

- T-V04-01：Session 页完整投影 Close 结果（result/summary/remaining_work/建议下一步/交接说明）；progress 改"Agent 最近一次报告"；Ack 展示风险
- T-V04-02：Context Pack 移入 Store（原子写 + operation 元数据）；Pack 写失败项目不提交（pre_commit_hook）；不同 operation 不覆盖
- T-V04-03：Session Detail 只读投影（project_revision/session/context_pack/timeline/artifacts/requests）；missing/invalid Pack 显示可读状态
- T-V04-04：errors.py 领域异常 + error_code/hint/details；标准库 logging → private-data/logs/paos.log；覆写 http.server 请求日志
- T-V04-05：Open 原子创建新 Work（new_work 与 work_item_ids 二选一）；done/cancelled Work 拒绝新 Session
- T-V04-06：唯一日常 Launcher（选 Work / 新建 Work；高级设置折叠；创建后直达 Session）
- T-V04-07：删除旧 handshake 接入路径（端点 / adapter / Prompt / AGENTS/CLAUDE 规则 / 协议文档改写为窄写入）
- T-V04-08：项目页/Session 页日常化（Session 倒序 + 最近 10 条折叠 + 下一步提示 + 关闭后继续/后续/评审预填；Office 中文卡片）
- T-V04-09：Request 交接（以此请求启动 Session）+ 关闭后追加归档 Artifact 窄合同 + 归档 Prompt
- T-V04-10：后端可读性重构（project_store_v2 → project_schema；V2_* 领域名；_apply_bundle 五段；POST/PUT 路由表；无 >100 行函数）
- T-V04-11：前端与文档收口（ui-common.mjs 唯一一份 helper；README/ARCHITECTURE 与实现一致）
- T-V04-12：发布验收与真实使用起点
- 最终收口：归档 Prompt 使用当前 revision；Request 交接状态用后清空；Artifact 幂等重试返回原始 ID；Context Pack 读取判断完全收回 Store

## v0.3 (2026-08-04) — Session 握手纳管

**把“新开一个 Agent 对话”变成有正式请求与回执的接入流程。**

- 新增 `PAOS Session Handshake Protocol v1`，明确请求、回执、失败语义与权限边界
- 项目页新增“启动一个受管 Session”：选择已有 Work 或 `AUTO` 新建，填写要求与资料，一键复制 Prompt
- 新增窄写接口 `POST /api/agent/handshake`，只能创建/关联一个 Work Item 与 Session，不能覆盖项目人工字段
- `handshake_id` 作为幂等键；重试不重复创建、不新增备份、不增加 revision
- Agent 必须使用真实原生元数据；未知标题、Session ID 或记录路径留空，禁止编造
- 新增 `AGENTS.md` 与 `CLAUDE.md`，共同引用一份规范协议，避免规则分叉
- 手动 Session 表单降级为“高级纠错”，保留历史迁移与修复能力
- 握手纳管阶段基线为 126 项测试：Pipeline 17 + API 31 + Store 41 + 旧 Dashboard 10 + Project Board 27
- 协议冻结“核心严格、扩展宽容”：未知字段忽略且不落盘；已定义核心字段错误时写入整体中止
- WSL Bash 调用 `verify.ps1` 的正确路径与 `WSLENV` 传参方式已实测并写入手册
- 冻结交互边界：PAOS 只生成握手 Prompt 并接收回执，不直接启动、调用或调度 Agent；用户手动粘贴是正式授权步骤
- 项目页新增“手动填写 / 修正”备用入口，以及独立的“更新 OS 要求”授权 Prompt
- 新增窄写接口 `POST /api/agent/project-requirement-update`：仅允许已握手 Session 更新三个 `human` 要求字段，带 Session 引用、revision、备份和标准回执
- 新增 `PAOS Project Requirement Update Protocol v1`，与握手协议分离；不引入 CLI 调度或 Agent 自动启动
- 五套件共 137 项测试：Pipeline 17 + API 35 + Store 46 + 旧 Dashboard 10 + Project Board 29
- 项目页重排为“项目摘要 → Work Items / Requirements 下属页”；主要文件与随后事项也提供独立下属页、手动编辑和受限 Agent 更新
- 新增 `POST /api/agent/project-list-update`，一次只允许 Agent 更新 `key_files` 或 `next_items` 其中一类
- v0.2 Session Update 的 `progress` 语义收敛：省略保留、显式 `null` 重置、非法拒绝（此前省略会返回 500，非法结构可原样落盘）
- v2 Session 可在项目页直接授权要求/列表回写：窄写入口按 PAOS Session ID 识别，回执 `session` 摘要 v1/v2 统一填充
- `verify.ps1` 干净检出可直接运行：Dashboard 套件前自动生成缺失派生数据，已存在的 `build/` 一律不覆盖
- 九套件共 222 项测试

## v0.2 (2026-08-03) — 项目骨架（T-100，Draft PR 待审）

**新增本地项目看板**，不引入框架与第三方依赖。

- 三个 Area：程序性工作、工作、项目
- 项目编号统一为四位字符串：`1xxx / 2xxx / 3xxx`，Area 与首位强校验
- 项目页增加 Work Item 层；Session 必须关联已有 Work Item，可跨项目复用
- 最多三项手动焦点（label 为空代表整个项目）
- 项目页首屏保留进度、要求与 DDL、相关 Session，并可展开 Work Item
- 项目创建、编辑、安全保存（原子写入）、恢复上一版
- revision 冲突返回 409，不静默覆盖
- "复制给本地 Agent"按钮，Prompt 浏览器本地生成
- `start.ps1` 默认打开 `projects.html`；旧 Dashboard 保留 `index.html` 入口
- 真实本地注册表初始包含 7 个项目；68 个 Session 只挂入明确相关部分，其余保留灰色空间
- 新增和扩展 Store、API、Dashboard 模型与页面测试
- `verify.ps1` 修复：清空退出状态、启动失败算失败、动态统计测试数

## v0.1 (2026-07-31)

**基线建立**：将 Attention Dashboard v1.2 与 Markdown Memory Pipeline v0 迁入独立仓库。

- 32 个来源文件白名单复制
- Inbox 优先级修复：`--inbox > PERSONAL_AGENT_OS_INBOX > <repo>/private-data/inbox/tips`
- 一键启动/验证/诊断
- 完整恢复与安全文档
- 35 项测试通过（Pipeline 17 + Tips Server 8 + Dashboard 10；原型基线 32 项）

## 原型阶段（2026-07-29 至 2026-07-30）

### v1.2 — 执行契约
- 三条主线卡片显示执行契约（当前唯一问题、阶段交付物、完成定义）
- Dashboard 自动测试 10 项
- 五层故障诊断

### v1.1 — Tips 显式提交
- Tips 从浏览器 localStorage 转为 Markdown Inbox
- 幂等重试
- Tips Server 测试 8 项（含 3 项 Inbox 优先级，T-002 新增）

### v1.0 — 初始原型
- 合成 Markdown → 扫描 → 三条主线 → Dashboard
- Pipeline 测试 17 项（原型基线）
- 夜间候选审核
