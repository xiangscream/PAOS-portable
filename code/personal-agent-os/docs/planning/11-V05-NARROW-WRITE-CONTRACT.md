# v0.5 窄写入合同：两个 Agent 适配器接回 mutate_v2

> 前置：`10-V04-USABLE-CLOSURE-DESIGN.md`（v0.4 可用闭环）
> 触发：2026-08-10 真实使用摩擦 —— 复制出来的 Prompt 因 revision 推进而永久失效
> 范围：`update_human_from_agent()` 与 `update_project_lists_from_agent()` 两个适配器

先把合同定下来再改代码。这两个函数写的是真实项目数据，"改对了没有"不能靠读代码判断，
只能靠先写清楚期望行为、再用测试钉住。

---

## 0. 为什么要改

两个适配器绕开了 `mutate_v2`，自己算 revision、自己 append Ledger、自己构造 receipt：

| 位置 | 现状 |
|---|---|
| `project_store.py:487` | `if current.get("revision") != request["expected_revision"]: raise ConflictError(...)` |
| `project_store.py:576` | 同上 |

后果是 `mutate_v2` 里已经实现好的三件事全部拿不到：

1. **幂等**：同 `operation_id` + 同 `request_hash` 返回原 receipt（`:735-743`）
2. **自动 rebase**：`expected_revision < current_revision` 且 touched-path 不重叠时基于最新状态应用（`:747-758`）
3. **结构化 409**：`RevisionConflictError` 带 `current_revision` / `conflicting_paths` / `delta_since_base`

真实后果（2026-08-10 实际发生）：Prompt 里写死 `expected_revision`，复制出来放一会儿，
revision 被别的操作推进（24→25），Prompt 就永久失效，只能回项目页重新复制。而这次推进
动的是 `/next_items`、失效的 Prompt 想改的是 `/human` —— 两者根本不冲突，本该自动 rebase。

---

## 1. 合同条款

### 1.1 幂等优先于"无变化"

**先查 `operation_receipts[operation_id]`，命中且 `request_hash` 相同就原样返回；
只有未命中时才判断有无变化。**

为什么这条要写进合同：两条规则会对同一请求给出相反答案。

> 同一个 `update_id` 第一次提交产生了变化（revision 24→25）。重试时因为已经写进去了，
> 提交内容与当前状态**相同** → 若先判"无变化"，返回 `changed: false`；
> 但按幂等语义应该返回首次 receipt（`changed: true`）。

幂等优先，否则"这是重试"和"这次真的没变化"永远分不开 —— 这正是窄 PUT 缺幂等键那个
老缺口的根因。顺序固定为：

```
1. 校验请求格式
2. 匹配授权 Session（见 1.3）
3. 查 operation_receipts[operation_id]
   ├─ 命中 + hash 相同 → 原样返回首次 receipt（不推进 revision，不写 Ledger）
   └─ 命中 + hash 不同 → ConflictError("operation_conflict")
4. 计算 changed / changed_fields
   └─ 无变化 → 返回 changed=false 回执（不推进 revision，不写 Ledger，不写 receipt）
5. 有变化 → 交给 mutate_v2
```

### 1.2 "无变化"语义必须保留

相同列表 / 相同 human 内容 **不推进 revision、不产生 Ledger 事件**，回执 `changed: false`。

风险点：`mutate_v2` 本身不判断"有无变化"，它假定调用方已经决定要写。
如果把无变化请求也丢给它，会白写一次事件并推进 revision。所以这个判断必须留在适配器里，
在调用 `mutate_v2` **之前**完成。需要专门测试钉住。

### 1.3 Session 匹配不能只看 ID

`_match_managed_session()` 生产调用方只有两个，正是这两个适配器
（`project_store.py:493` 与 `:582`），不波及 Open/Update/Close 主生命周期。
影响范围可控，可以直接改判定规则。

统一为：

```
status 属于 {pending_ack, active}     # 即"没有被终结"
```

**履责不需要任何领取手续。** Acknowledge 只把 PAOS Session 与真实原生 Runtime 的关联
写成证据，它不是开工许可，也不参与这里的判定；否则人类刚开出的 Session 在本人
Acknowledge 之前一律写不进项目数据，正常路径就断在领取上了。

`pending_ack` 仍留在可写入集合里，是因为它是"Acknowledge 是干活许可"时代留下的历史
事实，读旧数据时不能把它当成已终结；新流程不再产生这个状态。

**已终结的 Session（historical / completed / partial / blocked / abandoned）不能授权写入。**
这些状态背后没有活着的责任，重新激活后才回到可写入集合。

**`mode` 不参与判断。** 真实数据里 10 个 Session 的 mode 全是 `managed`，加上它不筛掉
任何东西，反而会让人误以为有在把关。若将来协议明确只允许 managed，再单独加。

前后端必须同一语义，否则会出现"页面允许选择、后端却拒绝"或反过来。前端对应实现是
`project-model.mjs` 的 `isAuthorizableSession()`，两处的判定条件必须逐字对应。

### 1.4 专用回执在首次提交时保存，幂等重试原样返回

**不得在幂等重试时从"当前项目状态"重建专用回执。**

`mutate_v2` 存的 canonical receipt（`project_store.py:799-813`）只有通用字段：
`operation_id` / `project_id` / `session_id` / `event_type` / `base_revision` /
`revision` / `request_hash` / `touched_paths` / `allocated_ids` / `event_id` / `created_at`。

**没有** `field` / `items` / `changed` / `changed_fields` / `human`。

所以如果重试时从当前项目状态重建这些字段，返回的 `items` 会是**后来的**列表，而不是那
一次写入的结果 —— 同一个 `update_id` 返回不同内容，幂等就是假的。

做法：首次提交时把专用结果作为一个子对象随 canonical receipt 一起存入
`operation_receipts[operation_id]`，幂等重试时原样取出返回。

### 1.5 适配器只做三件事

请求校验、描述 touched paths、生成业务结果。**不得**手工修改 revision、append Ledger、
写 operation receipts、调 `_atomic_write`。这些全部交给 `mutate_v2`。

`touched_paths` 取值：
- 要求更新 → `["/human"]`
- 列表更新 → `["/key_files"]` 或 `["/next_items"]`（按实际字段，不要两个都写）

---

## 2. 待定：expected_revision 比服务器还新

`mutate_v2:729` 对 `expected_revision > current_revision` 抛的是普通 `ConflictError`，
不是结构化的。这是"客户端 revision 比服务器新"的情况，通常意味着项目被 restore 回滚过。

接进来之后这条路径会漏出非结构化 409，和 1.4 要修的是同一类问题（错误信息不可执行）。

**本次不改，明确记录。** 理由：restore 回滚是低频动作，且真实使用中尚未发生过一次；
按"爆炸半径"分级（准则 §7），它不值得和事务语义一起改。若试用周内真实撞到，再处理。

---

## 3. 最小验证集（6 组）

只保留有真实区分力的场景，对应开发准则的测试止损三类判据
（用户正常路径曾跑不通 / 可能静默损坏真实状态 / 核心公共合同易复发）：

| # | 场景 | 期望 |
|---|---|---|
| 1 | 同 `update_id`、同请求 | 返回原回执，revision 不变，Ledger 不增长 |
| 2 | 同 `update_id`、不同请求 | 409 `operation_conflict`，状态完全不变 |
| 3 | 过期 revision，期间改的是**无关**字段 | 自动 rebase 成功，基于最新状态写入 |
| 4 | 过期 revision，期间改的是**同一**字段 | 结构化 409，带 `current_revision` + `conflicting_paths` |
| 5 | Session 授权边界 | active+ack 成功；historical / completed / 未 Ack 全部拒绝 |
| 6 | 无变化请求 | `changed: false`，revision 不推进，Ledger 不增长（可与 1 参数化合并） |

第 4 组还要断言 `conflicting_paths` 的**内容**，不只是字段存在 —— 否则又是一个
"测试绿了但信息没用"的空壳（参照 v0.4 那个只断言 `id="context-pack-id"` 在 HTML 里的测试）。

**全部使用临时 registry。测试不得触碰真实 `3002.json`。**

---

## 4. 真实数据验证时机

备份**不是**写代码前的仪式，而是第一次用新代码对真实 `3002` 做冒烟验证之前的动作：

1. 全套九套件在临时 registry 上通过
2. 复制真实 `3002.json` 到独立副本，记录 SHA-256
3. 只执行**一条**明确授权的请求
4. 逐字段 diff：只有目标字段 + `ledger` + `operation_receipts` + `revision` + `updated_at`
   变化，协议禁改字段逐字节未动

---

## 5. 架构检查（scripts/check_architecture.py）

零依赖、范围很窄，只守机械边界。**不检查**命名风格、函数长度、注释格式 —— 那些制造仪式感
而不防回归。事务语义 Ruff/ESLint 也查不出来，所以自己写这几条：

1. `local_server.py`、`workflow_service.py` 禁止直接写项目文件
   （`write_text` / `mkdir` / `os.replace` / `open(..., "w")`）
2. 适配器中禁止手工 `["revision"] =`、`ledger.append`、写 `operation_receipts`
3. 两个 Agent 窄写适配器必须出现 `mutate_v2` 调用
4. 服务层禁止 `store.root` 猜目录、禁止 `write_text()` 写 Context Pack

检查通过后再进入现有九套件。
