# PAOS V1.2 Stage 1 — Domain / continuity design (s027)

状态：Stage 1 设计提案（分支 `feat/v12-domain-continuity`，base `main@9a7f2bec`）。实现流 1「Domain / continuity / conversion」的 Owner 为 s027。本文件先固定**最小 enter / current-instance write-owner 接口**供 s031 对齐，再落实现。Stage 1 只产出隔离候选与转换演练，不 cutover。

## 1. 目标与问题

V1.1 把「同一 Agent 接班」与「新 Cycle/Context Pack/claim」绑在一起：新原生会话接管同一责任时，必须先造业务 Cycle、再 Ack、再携带 `execution_cycle`+`context_pack_id` 才能写。真实摩擦（STAGE1-TODO 失败样本 2）是：新 Runtime 已从固定工位恢复同一 `w060`，却被旧 Cycle/claim 挡写。

V1.2 要把四件事分离：

```text
durable Agent identity        （长期，稳定）
Team / Coordinator 关系        （长期）
Work 责任                      （业务对象，可验收）
当前 Runtime 实例              （易变，可被替换）
```

同责任接续只替换「当前实例」，不新增 Assignment / Coordinator grant / Human-only Continue / 业务 Cycle / 人工复制 claim。但保留**最小当前实例写入栅栏**：新实例可写，旧实例被挡；revision、原子写、幂等与 receipt 不变。

## 2. 领域对象

- **Agent（durable）**：`sessions/<id>`，身份与责任绑定；`write_owner` 为当前实例投影（见 §3）。
- **Instance（当前 Runtime 实例）**：由原生会话自报的稳定标识，非 PAOS 新建对象；同时进入 `write_owner` 与（可选）CAT participant generation 核验。
- **Work**：业务责任；`doing/review/accepted/cancelled` 等状态由业务动作驱动，与执行关闭解耦。
- **Cycle / Context Pack / execution claim**：降级为**历史只读证据**，不再是正常接班的行政前提；不再要求普通续写携带。

## 3. 最小 current-instance write-owner 接口（s010 已裁决，见 Mail msg-3002-v12-s027-write-owner-decision-20260928）

### 3.1 Store durable 记录（s027）

```text
session.write_owner = {
  "owner_id":   "<PAOS 生成的实例级 opaque ID>",
  "generation": <int, 新实例接管时 +1>,
  "runtime_id": "<codex|opencode|...>",
  "model_id":   "...",
  "runtime_session": { environment, title, session_id, source_path },
  "bound_at":   "<ISO8601>"
}
```

- `owner_id` 是**当前 Runtime 实例级**的 PAOS opaque ID，**不直接等于 native session_id**（同一原生会话可能被多个本地进程/窗口打开，直接复用会合并两个真实实例、失去 fencing）。native session/thread id 只保留在 `runtime_session` 元数据。
- 幂等：同一实例带**其现有 owner 凭据**重复 `enter` → 复用同一 owner，不递增 generation；新实例（无凭据/凭据不符）`enter` → 发放新 owner 并 generation+1。
- 追加只读历史事件 `session.write_owner.bound`（含 previous owner_id/generation 的安全摘要），用于审计与证明旧实例已被栅栏。
- durable owner 放在**稳定 Agent 身份槽位**，不跟业务 Work/Cycle 走。未进入 V1.2 的 legacy Agent 无 `write_owner`；首次 `enter` 惰性建立，不做批量迁移。

### 3.2 写入栅栏（s027，在 ProjectStore 的 mutation lock 内校验）

- 普通 Agent 写操作携带 `write_owner_id`（+ generation）；`owner_id` 视为实例一致性凭据，**非 auth/secret/lease**。
- 若 durable `write_owner` 已存在：carry 缺失或不匹配 → `ConflictError`，错误码 `enter_required`，附**安全的当前 owner 摘要**（generation/runtime_id/bound_at，不含其他实例凭据）；返回可操作提示：执行 `enter` 重新接管。
- **缺 owner 语义（s010 裁决）**：V1.2 正常路径里，已建立 write-owner 的 Agent 在无/错 owner 时**必须**报 `enter_required`，不得退回「旧 Cycle/claim 才能继续写」的长期 fallback。旧 Cycle/claim 仅作只读历史（转换器可读取还原历史输入）。
- 接管：新实例 `enter` 在**同一次** `mutate_v2` 中写入新 `write_owner` 并 generation+1；旧实例下一次写入即被挡。
- `scoped_request_hash` 把 owner 绑定纳入 hash（等价于现在的 runtime_binding），保证同 operation_id 不能跨实例重放。
- revision / 原子写 / 幂等 / receipt 语义不变；Cycle/claim 强制校验仅保留在「从未建立 write_owner 的 legacy 路径」，作为迁移过渡，不作为新契约。

### 3.3 CLI / Runtime（s031）

- 用**独立 enter 动作/路由**，不扩展 `acknowledge`：`enter` 绑定当前实例并返回 live responsibility readback（复用 orient 组合）；**不创建** native session / Assignment / Cycle / Context Pack。`acknowledge` 仍只表示对消息/交付的确认。
- `paos enter` 与只读 `orient/inbox/peers` 明确分开；写入通过 s031 冻结的 `report/submit` 或普通治理动作；底层 `session update/ack` 是否保留为内部/诊断入口由 s031 判断。
- **实例凭据只属于该 Runtime context**：必须由 `enter` 返回给进入的实例、并在该实例本地持久化；**不得**从全局「latest owner」文件、`orient` 或 `inbox` 读回新 token。相同实例可跨 CLI 子进程复用其凭据；新实例必须显式 `enter` 接管。本地文件位置/自动传递方式由 s031 的 install/CLI 设计冻结；**不新增全局 credential store**。
- `orient`/`inbox` 只读，永不绑定实例。

### 3.4 与 CAT 的关系

CAT `ownership_generation` 与 PAOS write-owner generation 是**两套独立栅栏**：只核对绑定一致性，不互相替代；PAOS 本轮不重写 CAT scope/Room，CAT 侧由 Rooter 单线处理。

## 4. Work 验收 / 成员任职 / 执行关闭 分离

- Work 状态由业务动作驱动：`accepted` 不因迟到历史交接回退为 active；`cancelled/accepted` 终态不可被写入复活。
- 执行关闭（Cycle/instance 结束）不再改写 Work 验收；历史 Cycle 关闭只作为交接证据。
- Coordinator 可无当前 Work 待机；不造占位 Work。
- 普通 Coordinator 治理（派 Work、安排成员、Review/accept/cancel）收敛为**一次明确业务动作 + receipt**，不要求 Human-only 双提交或同责任重复授权；Human 保留方向、对外承诺、明确 Human 验收项。`authority_manifest` 如实反映该边界。

## 5. Working Memory 退役（域内）

- `agent_working_memory` 退出正常机制（PR #111 @ `065b73f` 已实现写拒绝与 Context 退出）。
- 转换器把历史 Memory 正文转普通 Project 文件或可选 Agent notes，**不丢正文**，也不把 Memory head/replace/Restore 特例带入新路径。
- Session Detail 的历史 `working_memory` 投影保留只读，不作正常恢复状态。

## 6. 一次性 V1.1→V1.2 转换器

- 输入：正式只读快照（2001 / 3002 / Rooter Home 三类）；输出：隔离副本 + 转换报告 + 回退说明。
- 保留稳定 ID、真实责任、验收成果、外部引用（Feishu 等）、回退依据。
- 移除旧 Cycle/claim/Context Pack 对正常续写的约束：生成 `write_owner` 基线、把 Work 责任与实际验收对齐、把历史 Cycle 标为只读。
- 不迁移、不修改生产 Store/Runtime/CAT/Wake/private-data；不部署、不 cutover、不归档。
- 随 Source 候选版本冻结；演练结果交 s010，Stage 2 独立复核。

## 7. #111 已知缺口（域内修复）

1. Library registry 缺失/损坏区分（`orient` 已给显式提示，需安装配置流不依赖 `__file__`）。
2. 不可验证的 Source locator 不得合成：`_orient_source_root` 回退拼接的路径需改为「无法验证则留空 + 提示」。
3. TODO Work ID 精确匹配 / `## 当前` 区解析（现为子串包含匹配，易误判）。
4. Working Memory 退役后不再作为正常恢复状态（延续 #111）。
5. 失败样本 5：外部在途长写必须在 TODO/交接里标注未决外部副作用与接手人，不把文本保存当外部写入停止。

## 8. 依赖顺序

`s027/s031 先对齐 §3 接口` → 域实现（§3.2/§4/§5/§7）与 CLI 面（s031）并行 → 接口稳定后完成 §6 转换器与隔离演练 → 合入集成分支并冻结 manifest → s029 对完整 exact candidate 独立审查。
