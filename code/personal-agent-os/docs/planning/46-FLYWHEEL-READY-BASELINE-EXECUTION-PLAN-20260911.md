# 46 · PAOS 飞轮前最终基座收口

> 状态：**范围已批准，执行中** · 2026-09-11
> 当前开工基线：PAOS `main@cf8a691755c695b815b906ef46c5d7318977f42e`；CAT `master@7fcb4e8e001715051ceac30ecba41098616b4e02`。
> 需求边界仍以 [45](45-NEXT-BASELINE-REQUIREMENTS-20260911.md) 为准；[44](44-PAOS-REQUIREMENT-DEVELOPMENT-REGISTER.md) 记录实际完成状态。本文冻结本轮施工顺序与退出 Gate。

## 1. 目标

本轮不扩建平台。完成后，PAOS 的核心链路应没有 E04–E16 / Must 范围内的已知阻塞摩擦，并具备独立安装、Agent 主链、真实接班、可选自动协作、数据恢复与正式发布锚点。

之后默认开发方式转为：

```text
real work
→ friction
→ Practice / Skill first
→ repeated evidence
→ only then evolve Language / Physics
```

## 2. 不重新设计的地基

- M1A Agent Continuity / Runtime Tenure
- M1B Working Memory
- M2 Agent Mailbox
- M3 PAOS ↔ CAT Durable Binding
- M5A Artifact Revision Registration
- M5B Typed Evidence References

PAOS 保存 durable work facts；CAT 保存 transient collaboration；Runtime 负责实际执行。工作方法优先留在 Practice / Skill，不下沉为 Supervisor policy engine。

旧 M4 PR #25 只作为素材库。D1 前必须把 reuse/discard 清单登记进 44；不得直接把旧分支合入当前 main。

## 3. 最终 Gate

### G1 · Runtime Truth

代码、运行实例、浏览器静态资源、指南和 44 表必须可以机械对齐。运行实例报告 build identity；Doctor 能发现“当前 checkout ≠ 正在运行的旧进程/旧资源”。

### G2 · Independent First Use

非开发者在新的 Windows 用户环境中完成安装 → Project → Work → Agent → Artifact，过程中不依赖作者口头补步骤、作者绝对路径或固定 Project/Agent ID。

### G3 · Agent Golden Path

新 Agent 只依赖 Entry/Continue Prompt 与 `paos --help` 完成 inspect → Ack → Update → Artifact → responsibility → Close/Memory。主链 0 次手写 HTTP、0 次手拼 schema、0 次 Human 告知 endpoint；以 CLI transcript、operation receipts 与独立复核为证据。

### G4 · Real Continuity

旧 Runtime 仍在场时执行 Continue：同一 sNNN 开新 Cycle，新 Runtime 读取实时事实 + Working Memory 后完成下一步；旧 Cycle 无法污染 PAOS，新旧 Runtime 也不能同时成为 CAT 自动消费者。

### G5 · Declared Collaboration Support

每一种最终写为 Supported 的自动 Runtime 独立通过 cold start、idle message、CAT restart、Runtime reconnect、takeover、duplicate prevention、STOP 和 scope/address recovery。未经验证只能标 Experimental / Not claimed。

### G6 · Flywheel Consumption

Run 2 必须显式复用 Run 1 至少一个 Workflow/流程产物、至少一条 Lesson/Practice 改进，并实际发生一次 Working Memory 接班。接班输入规模必须可测且小于对应旧聊天全文；本轮已声明关闭的 E04–E16 / Must 摩擦复现数必须为 0。

其他效率指标允许没有全部改善；真实变差时记录并考虑裁剪能力。

### G7 · Release & Recovery

最终交付必须有 immutable release tag、release notes、Support Matrix、44 登记和机械检查过的发布包。至少完成一次真实 backup → destructive/upgrade test environment → restore 演练，确认 Project、Artifact、Ledger/history 和持久化用户配置按合同恢复。

## 4. 冻结摩擦 E04–E16

| ID | 摩擦 | 归属 |
|---|---|---|
| E04 | START-HERE 仍教 successor Session | B1 |
| E05 | Create Agent 仍有未来计划文案和失效 selector | B1 |
| E06 | Project 主页面历史/建议抢占主路径 | B2 |
| E07 | Mailbox 当前责任与历史信息仍需继续分层 | B1 |
| E08 | CAT 身份辨识与 Reply 剩余组合摩擦 | C2 |
| E09 | Agent CLI 主链残缺 | B3 |
| E10 | Project 文件入口可能指向不存在路径 | C3 |
| E11 | 作者路径、旧指南和平台支持声明不准确 | A1/B4/C1 |
| E12 | Continue 后旧 Runtime/CAT activation 可能继续抢消息 | B1/C1 |
| E13 | 旧 PAOS 进程/静态资产可能被误当作新代码 | A1/B4 |
| E14 | Windows/WSL scope 与 CAT base 地址容易失配 | C1/B4 |
| E15 | WSL Agent 需要反复填写 PAOS base URL | B3 |
| E16 | Continue human-only 在 Agent/route 表面的边界不够硬 | B1/B4 Gate |

E07 已有 `badge = Inbox + Waiting`、Recent 不计 pending 的修复，本轮以回归验证和历史/当前信息分层为主，不重做 Mailbox。

## 5. 开发顺序

### Stage A · Release truth

**A1**：build identity、Support Matrix、旧文档/作者路径清理、当前发布事实对账。
**A2**：EOL hygiene 独立包；先预演 `.gitattributes only` 与 renormalize diff，默认避免 mega-diff。

Gate A：代码/运行实例/文档/支持声明一致；过时 39 文档不再可被误当实施依据；EOL 不再污染业务 PR。

### Stage B · 一人 + 一个 Agent

**B1**：Create / Continue / History / Mailbox / E12 / E16。
**B2**：Project Golden Path 与 Human→Coordinator 顺手入口。
**B3**：Agent-first CLI，base URL 优先级为 `--base-url > 环境变量 > 本地配置 > 127.0.0.1`；补 compact start、mailbox、switch-work、Artifact Add 与结构化错误。
**B4**：clean install、Doctor、upgrade、真实 backup/restore、Dogfood #0。首次真实任务使用真实可用材料，不只使用 synthetic fixture。

Gate B：完整 First Use + Artifact + Memory + Continue + 下一步成功；旧 Runtime 无法污染新 Cycle；主链无手写 HTTP；E04/E05/E07/E09/E13/E15/E16 不复现。

### C Scope Gate

B4 后重新区分 C 的 Must / Should。真实工作未触发且不影响首发 claim 的 Should 可以降级 Later，禁止为了完成计划硬做功能。

### Stage C · Collaboration & Documents

**C1**：existing-only rebind 安全审查、单消费者、cold start/reconnect/STOP/scope recovery。
**C2**：只收真实存在的 CAT UI 摩擦。
**C3**：Project 文件入口与 Artifact head 导航；复用 key_files / Artifact lineage，不建 RAG 或新的 document truth store。

Gate C：所有 Supported runtime claim 有独立证据；CAT 单消费者成立；scope 可恢复；文件入口不说谎；关闭 CAT 仍可完成 PAOS 基础 Golden Path。

### Stage D · Flywheel proof

**D0**：预注册指标定义、数据来源、统计窗口和观察者；执行 Agent 不自评通过。
**D1**：从当前 main 重新吸收 M4 中仍成立的 factual projection / Practice Guide。
**D2**：真实 Workflow Run 1，中途强制一次 Working Memory Continue，形成真实 Lesson。
**D3**：同类 Run 2，显式消费 Run 1 的流程产物和 Lesson，测量重复解释、读取量、CLI 调用、接班输入、返工和摩擦复现。
**D4**：非作者 External User Acceptance。

## 6. 每包纪律

```text
fresh main/master
→ exact input HEAD
→ short branch
→ focused implementation
→ focused tests
→ full verifier when appropriate
→ Draft PR
→ independent review
→ approval
→ exact-head merge
→ runtime/browser verification
→ update 44
```

验证证明无需改代码时，Acceptance evidence + status/docs update 是合法交付；不得为了“应该有 PR”制造无意义代码。

如果一个包明显超过冻结范围，先砍 Should，保 Must，不无声扩 scope。

## 7. 不做

本轮不新增 Agent identity 层、Memory/Evidence/Relation 数据库、Promote API、Workflow engine、自动创建 Agent、通用 Runtime orchestration、全 Vault RAG、知识图谱、证据评分、Blob archive、数据库迁移、多租户、云端控制面或完整认证/RBAC 平台。

## 8. 退出条件

Human 不懂内部协议也能交真实任务；Agent 只凭 Prompt + CLI 能正确执行与回写；新 Runtime 不读完整旧聊天即可接续；自动模式只有当前有效消费者处理消息；数据能从真实备份恢复；Run 2 真正复用了 Run 1 的流程、Lesson 与 Working Memory；外部用户安装的是有 tag、有支持边界、无私人数据的正式 release。

全部成立后，本轮关闭，PAOS 标记 **Flywheel-ready**。
