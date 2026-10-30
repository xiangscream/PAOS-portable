# 44 · PAOS 需求开发登记表（单一工作索引）

> 定位：PAOS/CAT 的「需求是否已实现、验证、投入使用、被 Human 验收」的工作索引。正文以 Work / Artifact / PR / receipt / 真实使用为证据源，本表不替代 canonical 事实。
> 维护人：3002-s027（受 3002-s010 委托）· 最后核对：2026-09-10（基于 PAOS main@32860da、CAT master@f2d5d71，逐条经 Git/PAOS 证据核对，不凭记忆）

> 2026-09-11 开工核对：下一轮范围已批准并开始执行。需求边界见 [45 · 独立安装与工作流基线](45-NEXT-BASELINE-REQUIREMENTS-20260911.md)，冻结施工与 Gate 见 [46 · 飞轮前最终基座收口](46-FLYWHEEL-READY-BASELINE-EXECUTION-PLAN-20260911.md)。当前远端基线：PAOS `main@cf8a691`、CAT `master@7fcb4e8`。39 号旧实施计划保留原始历史证据，由 45/46 明确替代，不再作为当前开工依据。

## 更新规则
1. 需求提出时即登记一行，状态从「未开始」起步。
2. 状态四轴独立推进，分开更新，不合并成一个 Done：
   - **实现**：未开始 / 进行中 / 已实现
   - **验证**：未验证 / 测试通过 / 真实链路通过
   - **使用验收**：待试用 / 有摩擦 / Human 接受
   - **主干运行**：写清未合并 / 已合并，以及实际运行来自哪一 commit、是否包含本地补丁；「本机运行」不是高于「已合并」的完成状态，未提交功能也可能正在本机运行。
3. 每完成实现/测试/合并/本机运行/Human 验收任一状态变化，即时更新对应列并补 exact evidence（PR/commit/receipt/Artifact/真实使用记录）。
4. 阶段审查后立刻登记 exact evidence，不写记忆性描述。
5. 需求被替代时保留原行并标 `superseded → 新 ID`，不删历史。

## 状态例读
每行写法：实现 / 验证 / 使用验收 / 主干运行；末列为该行最后核对日期。

---

## 已完成大能力回填

| ID | 需求 | 层 | 实现状态 | 证据 | 剩余缺口 / 下一动作 | 负责人 | 最后核对 |
|----|------|----|---------|------|---------------------|--------|
| R-01 | Coordinator v0 核心 API + 任务领取 | PAOS | 已实现 / 测试通过 / 有摩擦 / 已合并 | main coordination_workflow.py（create work/request/assignment、transition；领取防重复 session_workflow.py:1030）；test_v2_sessions.py:3123 起（Work+定向 Request+子 Session 领取、不可领取组合 422） | 主 UI 无 canonical 操作入口（29 动作 vs 1 按钮）；下一动作见 R-06 | s010 | 2026-09-10 |
| R-02 | M1A Runtime handover / execution tenure | PAOS | 已实现 / 真实链路通过 / 待试用 / 已合并 | commit 906c41c；合同 AGENT-CONTINUITY-V0.md；真实证据：s027 Cycle 2→3 跨 Runtime 接管（Delta rev 417-419），旧 claim 409（op-evidence-stale-claim-c2、op-evidence-noclaim-write）、新 claim rev 423 成功 | 跨整系统重启的自动恢复未做（sidecar/自启级）；继续真实使用 | s010 | 2026-09-10 |
| R-03 | Agent Working Memory（M1B） | PAOS | 已实现 / 测试通过 / 待试用 / 已合并 | commit 7110a46；合同 AGENT-WORKING-MEMORY-V0.md；tests test_working_memory_m1b*.py；本机 bounded 注入生效（Pack 仅注入 8/61 delta） | 真实接班消费 Working Memory 的 dogfood 证据不足 | s010 | 2026-09-10 |
| R-04 | Agent Mailbox（M2） | PAOS | 已实现 / 测试通过 / 待试用 / 已合并 | commit 2c69cb9；合同 AGENT-MAILBOX-V0.md；tests test_agent_mailbox_m2*；canonical-only 投影（无广播通道） | 「领责→处理→闭合」全程经 Mailbox 的 dogfood 不足；Session 页 Mailbox 面板未提交（本机运行） | s010 | 2026-09-10 |
| R-05 | Project Room / CAT participant 稳定绑定（M3） | PAOS+CAT | **拆分**：PAOS 侧已实现 / 测试通过 / 已合并（commit cd4a622；合同 CAT-CONTINUITY-V0.md；tests test_cat_binding_m3.py）；CAT 侧 existing-only rebind adapter **已实现 / 测试通过（远端自带 tests/test_m3_runtime_rebind.py）/ 未独立验证 / 已合并**（master@7fcb4e8，PR #17 合并链携带 origin/master@6da7dae 的 existing Participant self-rebind） | 双仓发布不同步：s027 本次 rebind 仅记「身份结果已观察」，不宣称一般安全能力（s010 裁决 x-0d44eeee771e/x-5e5233749f16） | 独立安全审查 existing-only/paos_project_id guard + 冷启动/夺舍验证；验证通过前不宣称一般安全能力；s027 本次 rebind 仍只记「身份结果已观察」 | maintainer | 2026-09-10 |
| R-05a | Artifact 版本谱系（M5A） | PAOS | 已实现 / 测试通过 / 有真实登记使用，待 Human 验收 / 已合并 | commit 86cd532；test_artifact_revision_m5a.py；真实使用：3002-a047→a048-a053→a054 版本演进登记 | 同 path 更新必须 replaces+change_summary（已写进 Habit 规则） | s010 | 2026-09-10 |
| R-05b | Artifact 类型化 subject/source/evidence 引用（M5B） | PAOS | 已实现 / 测试通过 / 待试用 / 已合并 | PR#30 squash（main@32860da）；focused 16/16、verify.py 7/7（Python 514、Node 140 双时区）；本机 Session typed-reference projection 运行正常 | 语义纪律靠使用维持（subject≠source≠evidence） | s010 | 2026-09-10 |

## 当前未收口项

| ID | 需求 | 层 | 实现状态 | 证据 | 剩余缺口 / 下一动作 | 负责人 | 最后核对 |
|----|------|----|---------|------|---------------------|--------|
| R-06 | Coordinator 主入口与委托闭环 | PAOS | 未开始 / 未验证 / 待试用 / 未合并 | a054 B 节是候选方案；2026-09-11 浏览器确认 Coordinator 卡主要为 Change/Continue/History，尚缺顺手的委托与跟进入口 | 按45的 REQ-UX-01/REQ-LOOP-01收敛：Human 自然语言委托，Coordinator 复用事实投影与正式动作；不以“29动作全部做表单”验收。真实完成委托→拆解→派发→跟进→验收，Human-only裁决仍留给Human | s027 | 2026-09-11 |
| R-07 | s027 OpenCode 转生验收 | Runtime | 已实现（身份连续）/ 测试通过+A 收口 PASS；B 运行期自动续步 PASS；C CLI 通过 / Human 待终验 / **本机运行（adapter 已入 master，sidecar pid 93146 切新代码）** | ACK rev 419（DSH→opencode binding）、409 双实锤、CAT rebind、x-98d9822543fc 证据表；s010 验收 x-5e5233749f16：A PASS、B 运行期可用、C 通过 | 跨系统重启自动恢复未实现（sidecar 需手动重启）；TUI 端口变化需 rebind；CAT 段停用直至 R-05收口 | s027 | 2026-09-10 |
| R-08 | OpenCode 自动续步 adapter 合并 CAT 库 | CAT | 已实现 / 测试通过+运行期真实链路通过（14 黑盒+6 并发；s027 多次真实唤醒→模型回合一→inbox ack）/ 有摩擦（跨重启自恢复未实现、冷启动未验证）/ 已合并（PR #17 → master@7fcb4e8） | 合并后门禁：Python discovery 92 pass/0 fail(skip3)、Node 58/0；canonical 唤醒路径统一为 POST /session/:id/prompt_async（代码/help/两份指南一致）；本机切 master 版运行（OpenCode sidecar pid 93146） | 归入 45 REQ-RUNTIME-01 做冷启动/重连/停用验证；不宣称开箱自启 | s010 | 2026-09-11 |
| R-09 | Agent onboarding / Context 减负 | PAOS | 进行中 / 未验证 / 有摩擦 / 已合并（合同部分） | Context Pack 自动编译运转正常（真实接管使用它）；a054 A 节：开新 Agent 需 Human 手动 open+粘 pack；必读资料靠人填；Mailbox 消费 dogfood 不足 | 继续真实使用收集「减少 Human 重复解释」证据；Request 带必读材料字段试用 | s010 | 2026-09-10 |
| R-10 | Coordination Learning 飞轮 | PAOS+Skill | 未开始（决策：先复用摩擦记录/Work Suggestion，不新建对象）/ 不适用 / 待试用 / — | a054 A 节；教训当前沉淀在 Session Update/摩擦记录/Work suggestion | 教训积累后评审是否立项正式 Learning 合同 | s010 | 2026-09-10 |
| R-11 | CAT Room UI（回复引用/布局/过滤） | CAT | 已实现部分 / 既有测试报告 node 58；2026-09-11 浏览器局部通过 / Human 尚待完整使用验收 / 本机补丁未合并 | s010 实际点击 Reply 显示自动目标，Clear reply 清除预览，无冗余 reply 按钮；未发送消息，未验收全部正文/手动目标恢复组合。复制/折叠/多选已有；同Room s027/s029颜色碰撞仍可见 | 已修功能进入发布验收，不重新立项 Clear；按45 REQ-CAT-01完成剩余颜色/历史身份/引用筛选及行为回归。R-05仍是自动协作前置 | s010 | 2026-09-11 |
| R-12 | 工作区 EOL 漂移维护包 | 维护 | 未开始（结构性修复）/ 不适用 / 不适用 / 未合并 | 2026-09-11 合并后两仓工作区均已干净：PAOS 64 个纯 CRLF-only 文件已按 HEAD 字节还原（--ignore-cr-at-eol 复核零实质差异）；CAT 仅 .opencode-cat-logs 未跟踪。.gitattributes/统一行尾策略仍未做，编辑器重写可能再次产生噪声 | 独立维护包：统一行尾策略一次性归零；与业务改动分开提交 | maintainer | 2026-09-11 |
| R-13 | Continue human-only 的 route 层 authority 假设 | PAOS | 未开始（架构假设审视，不实现）/ 不适用 / 待试用 / 已合并（现状即假设） | 证据：local_server.py:713 handle_session_continue 无 actor 校验；human-only 由 authority_manifest + UI 约定 + Store execution-claim 兜底（claim fail-closed 已实测：409 双实锤） | 独立审视项：是否补路由层 actor 校验由 maintainer 决策，不混入其它改动 | maintainer | 2026-09-10 |
| R-14 | Project 文档工作区 / Obsidian Vault 资料整理 | PAOS | 未开始 / 未验证 / 待试用 / 未合并 | 用户真实摩擦：Downloads 材料堆积。现有 key_files、Artifact版本谱系/来源引用可复用，缺少清晰工作区与待整理入口；2026-09-11还发现Project文件表的CAT README路径不存在 | 按45 REQ-DOCS-01：先复用现有字段/投影，确有需要才加document_root和可选intake；不全Vault扫描、不另建文档数据库、不默认复制飞书主稿。LRC101是现状样本而非规定模板。Agent在已授权范围整理，修改成果复用replaces/change_summary；越界移动/覆盖/删除保持原批准要求 | s010 | 2026-09-11 |
| R-15 | Agent-first PAOS CLI 协作入口 | PAOS | 部分实现 / 既有聚焦测试16/16，本轮静态核对 / 待完整真实试用 / 基础已合并 | scripts/paos.py；e9dddcc基础CLI、906c41c tenure。已有health/authority/relations/needs-me/project/work/session/coordinator；session show已含Mailbox。CLI专给Agent/Runtime，不做Human终端产品；现有PAOS_BASE_URL不重复开发 | 按45 REQ-AGENT-01补紧凑context/mailbox、switch-work、dedicated Artifact Add及已有Request处理。主链inspect→领责/切Work→Ack→Update→Artifact→处理责任→Close无需手写HTTP。Human-only Continue/Reactivate/Decision review不得误列为Worker自主能力；需要时给人工入口或现行明确委托路径。补stdin/结构化错误/重试operation；只包装canonical REST，不复制业务规则、不访问CAT、不自动获取最新execution claim | s010 | 2026-09-11 |
| R-16 | Release truth / build identity / Support Matrix（REQ-BASE-01 A1） | PAOS+Release | **进行中** / focused + full verifier 已通过（候选分支）/ 待 clean-install 与运行实例验收 / 未合并 | 候选 `feat/a1-release-truth-build-identity`：canonical `paos_server.py` 为 `/api/health` 增加 `paos-build-identity/v1`；start/doctor 比对当前 checkout 与运行 runtime/static fingerprint；新增 `docs/SUPPORT-MATRIX.md`；v0.3 onboarding 已明确 Historical，39 号旧实施计划由当前 44/45/46 明确 supersede 且保留原始历史；本地候选完整 `python scripts/verify.py` 7/7（Python 519、Node 140 双时区），HTTP 黑盒确认 health 与真实静态响应的 fingerprint 一致 | 独立 review；Windows 实机 start/doctor stale-process 反例与 clean-install 在 B4 验收；最终发行再增加 immutable tag/release package lint。当前测试证据只属于候选 HEAD，未宣称 main 已交付 | s010 | 2026-09-11 |

## 说明
- R-01 的「Coordinator v0 核心 API」指 main 上的 coordination_workflow.py（create work/request/assignment、transition；领取）。四份 Coordinator Supervisor Loop（M4）commit（30bed57/c9b39e7/0edf301/d6c5c19）在 remotes/origin/feat/m4-coordinator-supervisor-loop，**未进入 main**（Draft PR #25），不记已交付。
- 本表登记为 Artifact 后，同路径更新必须用 M5A `replaces` 指向当时 head 并写 change_summary。
- 4/5 收口审查（3002-a054）与 takeover precheck 两份材料是证据输入；precheck 未登记 Artifact，不作为正式证据。
