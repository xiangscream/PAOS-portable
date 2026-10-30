# PAOS Agent 连续性、外置记忆体与主管式交付：执行计划

状态：M0 修订版。M1A 及以后实现的唯一接班合同入口是 `docs/contracts/AGENT-CONTINUITY-V0.md`；本文件负责开发顺序、包边界和验收计划，不重复制造第二套接班语义。

基线：PAOS `main@e4f2cdd74df9f5f11198cfd5154986b631656143`。CAT 每个涉及它的包启动前重新记录实际 HEAD。

来源：37 号 Coordinator 编排需求、38 号外置记忆需求、2026-09-08 产品讨论、M0 设计审查，以及当前 Session/Cycle、Context Compiler、Artifact、Coordinator Authority 和 CAT Participant/Exchange 实现。

---

## 1. 产品模型

### 1.1 Agent 复用现有 `sessions[]`

Project 下继续保持扁平关系：

```text
Project
├─ Work A
├─ Work B
├─ Work C
├─ Agent s028
├─ Agent s031
└─ Coordinator s001

Work ↔ Agent
```

V0 不新增 `agents[]`、`agent_id` 或 permanent identity 层。历史代码/字段仍可能叫 Session，但产品语义中的 `sNNN` 就是 Agent 编号。

### 1.2 native Runtime 是可替换执行实例

稳定事实：Agent ID、Project/Work 关系、Coordinator 岗位、PAOS Mailbox、外置记忆、CAT Room/Participant binding。

可替换事实：GPT/Codex/DS-H 原生 Session、Runtime 类型、模型和 native session 定位。

普通“夺舍/接班”只替换当前执行实例；不创建新的 PAOS Agent。

### 1.3 Create Agent 与 Continue Agent 分开

- `Create Agent`：Human-only 重动作；组织结构真正增加一个 Agent；继续使用现有 Session Open。
- `Continue Agent`：同一个 `sNNN` 更换 native Runtime；普通路径在同 Agent 下开启新 Cycle。

Coordinator 不自动 Create Agent，也不自动启动任意外部 Runtime。

### 1.4 Cycle 不是“一次 native Session”的同义词

Cycle 表示一次 PAOS 执行周期。Switch Work、Reactivate、Runtime Handover 都可能创建 Cycle；native Runtime 是否变化由该 Cycle 的 runtime 记录决定。

普通 Runtime 接班不再用 `continues_session_id` 创建 successor Agent。既有 continuation chain 只保留历史可读，不作为新功能主流程。

### 1.5 Mailbox 在 PAOS，CAT 是 transport

PAOS Mailbox 表达“哪些正式工作责任要求这个 Agent 行动”，优先投影 Request、Assignment、Review/返工责任等 canonical facts；不另存第二套聊天。

CAT 继续负责 Room、Participant、Exchange、wake 和 Runtime binding。Participant ID 是现有 binding 事实，不强制等于 PAOS Agent ID，也不在 M3 做字符串格式迁移。

### 1.6 外置记忆体不是长期人格大脑

Working Memory 服务工作连续性：保存当前理解、执行位置、理由、未决和关键入口。Project/Work/Request/Decision/Authority 等实时事实每次从 PAOS 读取；冲突时实时事实优先。

---

## 2. 总体交付顺序

```text
M0 合同冻结
→ M1A Continue Agent / Runtime Handover
→ M1B 外置记忆体 / bounded context
→ M2 PAOS Agent Mailbox
→ M3 CAT 自续步
→ M4 Coordinator 主管循环
→ M5 Exact Artifact / Review / Assembly
→ M6 文档优化 Reference Workflow
→ M7 经验飞轮
```

每包独立分支、独立 PR、可独立合并。核心 schema/lifecycle/authority/context 变更跑完整 verifier；文档和低影响局部改动按 `SUPERVISED-DELIVERY` 做比例化验证。

---

# 3. M0：合同冻结

## 唯一有效接班合同

`docs/contracts/AGENT-CONTINUITY-V0.md`

37/38 仍保存原始需求背景，但与该合同冲突的 successor Session、CAT retire/new participant 等普通接班设计全部被取代。

## M0 必须冻结的边界

1. Agent = 当前 `sessions[]` 产品语义；普通接班 ID 不变。
2. Continue Agent 新建同 Agent Cycle，不新建 successor Agent。
3. Agent 级职责连续，但 Agent-initiated write 必须归属于具体 Cycle/Context Pack。
4. old Runtime 在新 Cycle 建立后不能把 Update/Close/Artifact/Coordinator write 串入新任期。
5. Continue 状态矩阵区分 active、closed、pending_ack、historical。
6. pending_ack 下“查看/复制 Prompt”是只读动作，不能重复造 Cycle。
7. Runtime 历史每 Cycle 保存 runtime 类型、model 和 native session 定位；顶层只表示当前 binding。
8. Coordinator pointer 连续不等于 pending_ack 期间可写；现有 active+acked 门禁继续生效。
9. Mailbox 属于 PAOS；CAT participant ID 使用现有 binding，不重新推导。
10. Create Agent 继续 Human-only；PAOS 不自动启动 Runtime。

## M0 验收

新执行者只读 canonical contract 即可回答：

- 什么是 Agent、Cycle、native Runtime；
- 什么时候 Create Agent，什么时候 Continue Agent；
- 旧 Runtime 为什么不能在新任期继续写；
- closed Cycle 为什么不能被 Continue 改写；
- pending_ack 为什么复制 Prompt 不会新增 Cycle；
- Coordinator 接班期间何时有、何时没有执行资格；
- PAOS Mailbox 与 CAT 的边界。

---

# 4. M1A：Continue Agent / Runtime Handover

## 用户收益

一个全新的 GPT/Codex/DS-H 原生会话可以接管同一个 `sNNN`，而旧任期证据不变、旧执行者不会把报告串进新任期。

## 4.1 新增 Human-only Continue Agent 动作

建议路由：

```text
POST /api/projects/{project_id}/sessions/{session_id}/continue
```

请求至少包含：

```json
{
  "schema": "paos-session-continue/v1",
  "operation_id": "op-...",
  "revision": 123,
  "reason": "native context too long",
  "mission": {
    "objective": "...",
    "done_when": ["..."]
  }
}
```

Continue 只创建新任期；查看/复制当前 Prompt 走现有 Session Detail / 当前 Context Pack 只读路径。

## 4.2 Continue 状态矩阵

| 当前状态 | 行为 |
|---|---|
| `active` | 快照当前 runtime；以 `runtime_handover` 结束尚未结束的 current Cycle；追加新 Cycle。 |
| `completed` / `partial` / `blocked` / `abandoned` | 不修改旧 Cycle 的 `end_kind/ended_at/close_result`；直接追加新 Cycle，前提是当前 Work 仍可启动。 |
| `pending_ack` | Continue mutation 默认拒绝；UI 只允许重新查看/复制当前 Cycle Prompt，不新增 Cycle。 |
| `historical` | 普通 Continue 拒绝。 |

`runtime_handover` 只能作用于尚未结束的 active Cycle。

## 4.3 Runtime 记录

每个新 Cycle 保存：

```json
{
  "runtime_id": "",
  "model_id": "",
  "runtime_session": {
    "environment": "",
    "title": "",
    "session_id": "",
    "source_path": ""
  }
}
```

规则：

- active → Continue 前先把旧顶层 binding 同步到旧 Cycle；
- 新 Cycle 初始化为未绑定；顶层当前 binding 同时清空；
- Ack 一次性上报新的 `runtime_id/model_id/runtime_session`，并同步顶层和当前 Cycle；
- 历史 Cycle 缺 binding 就显示未知，不拿当前值补造历史；
- 任何现存 manual runtime correction 路径若保留，必须同步当前 Cycle，不能只改顶层。

## 4.4 Cycle execution claim

M1A 给 Agent-initiated mutation 加最小任期归属：

```text
execution_cycle
context_pack_id
```

服务端核对它们必须等于 Agent 当前 Cycle 与当前 Context Pack。

至少覆盖：

- Acknowledge；
- Update；
- Close；
- Artifact Add；
- worker 自发 switch-work；
- Coordinator narrow actions；
- 其它会把 Agent 自身报告/主管动作写入 Project 的 Agent-initiated mutation。

Human-only 管理动作不需要伪装 Agent Cycle。

这不是 secret lease，也不是恶意认证系统；它只保证正常旧 Runtime 按旧 Prompt/旧 Context Pack 继续工作时不会污染新任期。

## 4.5 Coordinator continuity

Continue 不改变 `organization.coordinator_session_id`。

流程：

```text
pointer 保留
→ Continue 后 Agent pending_ack
→ Coordinator narrow actions 因 active+acked 门禁不可用
→ 新 Runtime Ack
→ 同一 pointer 自动恢复主管执行资格
```

禁止为了“不中断 Authority”放开 pending_ack 写入。

## 4.6 Prompt 语义

新 Continue Prompt 必须写成：

```text
你正在继续 PAOS Agent 3002-s028。
当前是 Cycle 4。
新的 native Runtime 正在接管该 Agent。
Agent 的 Project / Work / Coordinator 岗位 / 历史责任没有因 native Session 更换而重置。
```

不能继续写成“创建 successor Session”或“这是一个新的工作身份”。

Prompt 同时携带本周期 `execution_cycle/context_pack_id`，后续 Agent 写入不得自行替换为其它 Cycle claim。

## 4.7 M1A 修改范围

后端：

- `session_contracts.py`：Continue contract + execution claim；Ack 支持 runtime/model 自报；
- `session_lifecycle.py`：`runtime_handover`、per-cycle runtime、历史不改写 helper；
- `session_workflow.py`：`continue_agent()`，复用现有 new-cycle/context-pack/receipt 基础；
- `project_schema.py`：校验新 end_kind、per-cycle runtime；
- `coordination_contracts.py` / coordinator workflow：复用 current-cycle claim；
- `workflow_support.py`：如能明显减少重复，可放一个窄的 current-cycle claim 校验 helper，不建新租约框架；
- `local_server.py`：Continue endpoint；
- `authority_manifest.py`：Human-only `session.continue`；
- `scripts/paos.py`：`session continue`。

前端：

- `project-model.mjs`：payload/claim builder；
- `project-session-ui.mjs`：Continue Agent 走同 Agent Cycle；pending_ack 只复制现有 Prompt；Create New Agent 仍独立。

测试：

- lifecycle/state matrix；
- old-cycle write rejection；
- runtime history；
- idempotency；
- Coordinator pointer/eligibility；
- UI payload/pending copy path；
- Authority surface。

## 4.8 M1A 明确不碰

- CAT；
- Working Memory / Artifact lineage；
- PAOS Mailbox；
- Artifact freeze/review；
- Coordinator 自动 staffing；
- `mutate_v2` 内核；
- 真实 private-data 迁移。

## 4.9 M1A Done When

1. Continue 不改变 Agent ID 和当前 Work。
2. active → Continue 时旧 Cycle 以 `runtime_handover` 结束且旧进度/记忆/runtime 保留。
3. closed → Continue 时旧结束原因、时间和 Close evidence 不变。
4. pending_ack 反复复制 Prompt 不新增 Cycle。
5. historical 拒绝普通 Continue。
6. 新 Cycle 创建后当前 runtime 显示未绑定；Ack 后同步新 Runtime 到顶层和当前 Cycle。
7. 旧 Cycle runtime 不被新 Ack 覆盖。
8. 旧 Runtime 用旧 Cycle/Pack claim 提交 Agent write 被拒绝，即使 revision 是新的。
9. 同 operation 幂等重放不产生第二 Cycle。
10. Coordinator pointer 保留；pending_ack 不能执行；新 Ack 后恢复且无需 re-grant。
11. Continue Prompt 使用 Agent/Cycle 语义。
12. 全 verifier 通过。

完成后再进入 M1B，不把 Working Memory 与任期归属同时塞进一个高爆炸半径 PR。

---

# 5. M1B：外置记忆体 / Working Memory V0

## 用户收益

新 Runtime 不读旧聊天全文，也能理解 Agent 当前主线、关键取舍、未决问题与下一步。

## 设计

复用 Artifact，类型：

```text
agent_working_memory
```

最小内容：任务目标及理由、执行位置、已确认取舍及来源、Agent 当前判断、未决问题、关键材料入口、下一步、等待关系。

只对该受管类型建立最小 lineage 规则：predecessor 存在、同 Project、同 source Agent、同 type、无 self/cycle；多个无替代关系候选时投影明确 conflict，不按时间静默猜。

新增只读 `working_memory_projection.py`。Compiler 只引用索引/路径，不读取正文、不调用模型总结。

## Context 缩减

- standard/deep 不再默认注入全部历史 Artifact；
- bounded artifact index；
- Working Memory Head 单独提升；
- delta 只按明确实体引用做机械筛选；
- 条目/字符预算，不引 tokenizer；
- 必需项超预算明确暴露，不静默截断关键约束。

## 验收

- 大量无关 Artifact 不让初始 Continue Context 线性增长；
- live Work/Decision 与旧 Memory 冲突时 live fact 优先；
- 新 Runtime 仅凭短 Prompt 能指出当前任务、已确认路线、未决和第一步；
- 不要求读取旧 native chat 全文。

---

# 6. M2：PAOS Agent Mailbox V0

Mailbox 优先是 projection，不建第二套 Message 数据库。

至少聚合：open directed Request、Assignment、明确指向 Agent 的 review/coordination/integration 责任，以及真实存在的 blocking responsibility。

建议 API 继续沿用当前底层命名：

```text
GET /api/projects/{project_id}/sessions/{session_id}/mailbox
```

UI 文案显示 Agent Mailbox。

验收：Continue 前后 mailbox 完全相同；source fact resolve 后对应 item 消失；不复制 CAT Exchange；无责任时返回空列表。

---

# 7. M3：Project Room + CAT 自续步

每个 Project 绑定一个逻辑 Room；Agent 保存/投影自己实际已有的 CAT participant binding。

**不规定 `participant_id == PAOS Agent ID`。** 已存在 `p-3002-s028` 就继续使用它。

普通 Continue：

```text
PAOS Agent / Work / Mailbox / Room membership 不变
→ 新 Runtime Ack
→ 新 Runtime 自己根据 Prompt 配置 CAT
→ rebind 既有 participant 的 native binding
→ 发送/接收真实测试 Exchange
```

CAT 不可用时 PAOS Continue 仍成立；恢复后只重试 CAT 未完成步骤，不开第二 Cycle。

---

# 8. M4：Coordinator 主管式协作循环

Coordinator 在现有 Agent 足够时能够：

```text
Observe
→ Plan
→ Assign Existing Agents
→ Notify
→ Monitor
→ Technical Review
→ Rework
→ Escalate Human
→ Integrate
```

不自动 Create Agent，不自动启动 Runtime，不代办 Human-only Decision / final approval。

普通技术验收与 Human approval 分离；无合适 Agent 时产生 Human-facing staffing need。

---

# 9. M5：Exact Artifact / Review / Freeze / Assembly

保持三个维度独立：

```text
snapshot/frozen
≠ technical acceptance
≠ human approval
```

Git 文件使用 exact commit + path；非 Git Markdown 使用不可覆盖 snapshot。Review 绑定精确版本、reviewer、scope、outcome。Replacement 不撤销历史 review。

Assembly manifest 只接受允许的精确 source，正文机械读取源文件，不由模型重写；输出 provenance map 覆盖全部正文来源。

Restore 后历史 review/freeze evidence 仍可解析到旧 snapshot；不修改 `mutate_v2` 核心算法。

---

# 10. M6：文档优化 Reference Workflow

这是第一个 Organization Playbook，不是 Workflow Engine。

真实流程：

```text
Source document + meeting records
→ Coordinator Intake
→ Improvement Brief
→ Human direction gate
→ Work plan
→ Existing Agent assignment
→ Room collaboration
→ Worker artifacts
→ Coordinator technical review / 必要时 rework
→ selective Human gates
→ exact assembly
→ final QA
→ final Human approval
```

真实任务不为验收强行制造并行或返工：适合串行就串行，没有实质问题就直接通过。

并行 ≥2 Agent、返工路径、冲突处理等应作为**独立能力测试场景**覆盖；Agent 夺舍应至少在一次真实或受控任务中验证。最终 exact-source assembly 是硬要求。

---

# 11. M7：经验飞轮

只在 M6 真正跑通后进入。

沉淀 Project playbook lessons、Agent 工作经验、用户纠偏、常见返工原因和可复用检查表；不自动把所有聊天写入长期记忆。

---

# 12. 每包工程纪律

1. 每包开始记录实际 PAOS/CAT HEAD，主干前移先核相关 diff。
2. 短分支 → Draft PR → 同版本测试证据 → supervisor review → merge。
3. 核心合同变更跑完整 `python scripts/verify.py`；低影响改动做比例化验证。
4. 不编辑真实 `private-data/`，除非明确授权迁移。
5. Ledger / receipt / Close evidence append-only。
6. 跨 PAOS/CAT 只报告真实分步状态，不伪装原子成功。
7. 同 operation 幂等重试不得产生第二 Cycle/Artifact/Assignment。
8. 每个包必须回答“完成后用户多得到什么”，不能只交基础设施。
