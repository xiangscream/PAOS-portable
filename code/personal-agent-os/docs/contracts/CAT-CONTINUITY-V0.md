# PAOS ↔ CAT Continuity V0

状态：M3 canonical contract。

双仓基线：

- PAOS `main@2c69cb97fe9e36bbba8a99e3d62b8fc7c8728cc7`
- CAT `master@f2d5d71f33d741c54521602a4a74d3074948339d`

## 1. 一句话

**PAOS durable Agent 换 native Runtime 时，CAT Room membership 不换；新 Runtime 用同一个既有 participant_id 重新绑定自己的 Runtime locator。**

M3 不把 CAT 变成 PAOS 生命周期的同步依赖。

## 2. 稳定事实与可替换事实

PAOS 保存两个 Project 级稳定事实：

```json
{
  "cat_room_id": "room-0123456789ab",
  "cat_participants": {
    "3002-s028": "p-3002-s028",
    "3002-s031": "reviewer-A"
  }
}
```

规则：

- `cat_room_id`：这个 Project 的一个逻辑 CAT Room；只接受 CAT 当前创建流程真实生成的 `room-<12 hex>`；
- **一个 CAT Room 只属于一个 PAOS Project，禁止跨 Project 复用同一 Room 作为有效协作空间；**
- CAT Room 自身 `paos_binding.project_id` 是 Room 归属的外部权威事实；PAOS 本地 `cat_room_id` 只是引用，不得覆盖或夺取 CAT Room 的 Project 归属；
- `cat_participants[agent_id]`：该 durable PAOS Agent 在 Room 中**实际已有**的 participant ID；
- participant ID 不要求等于 PAOS Agent ID，且不得是 `.` / `..`；
- 不从 `sNNN`、Identity、label、最近 Room 或旧命名规则推导 participant ID；
- Room 与 participant map 由 Human manual Project PUT 同次替换，Agent/Runtime 只读。

可替换 Runtime locator 不进入上述稳定 binding：

```text
runtime_id / runtime
native session_id
source_path
model_id
```

PAOS 继续按 Cycle 保存自己的 Runtime history；CAT Participant 只维护当前协作 Runtime locator。

## 3. Human binding 写入口

不新增 M3 专用 write endpoint。复用已有 Human manual Project PUT：

```text
PUT /api/projects/{project_id}?revision=<current>
```

```json
{
  "schema": "paos-project-manual-update/v1",
  "project_patch": {
    "cat_room_id": "room-0123456789ab",
    "cat_participants": {
      "3002-s028": "p-3002-s028"
    }
  }
}
```

`cat_room_id` 与 `cat_participants` 必须同一次提交；清除绑定也必须同次提交 `""` 与 `{}`。现有 revision guard / backup / Project validation 不变。

PAOS manual PUT 不跨仓查询 CAT，也不把本地引用当成 Room ownership 证明。若 Human 配置了属于别的 Project 或未绑定 Project 的 Room，Runtime self-rebind 必须 fail closed；Human 再修正本地 binding。这样不会把 CAT 网络可用性变成 PAOS Project mutation 的提交条件。

V0 不做真实 private-data migration；旧 Project 缺这两个字段就是 `unbound`。

## 4. Continue / Ack / CAT 的顺序

普通 takeover：

```text
PAOS Continue
→ 新 Cycle + Context Pack（Agent ID / Work / Mailbox / stable CAT binding 不变）
→ 新 Runtime Ack，并把自己的 PAOS Runtime locator 写入当前 Cycle
→ Runtime 执行 CAT existing-participant self-rebind
→ 读 CAT Inbox
→ 按 Runtime 需要配置 Hook
```

CAT self-rebind 发生在 Runtime 侧，不在 PAOS Store mutation / pre-commit hook 内。

因此：

- CAT offline 不阻止 Continue；
- CAT offline 不阻止 Ack；
- CAT rebind 失败不回滚 Cycle；
- 恢复后只重试 CAT rebind / inbox / hook，不再 Continue、不再开第二 Cycle。

## 5. Context Pack

每个新 Pack 都投影 `cat_binding`：

- `unbound`：没有 CAT 指令，PAOS 正常工作；
- `bound`：给出 exact Room / Participant / CAT local base 与 existing-only rebind 步骤；
- `incomplete` / `invalid`：明确要求停 CAT 并让 Human 修 binding，禁止猜值。

Pack 中 CAT binding 是 PAOS 已知的 stable collaboration reference；Runtime locator 以当前 Runtime 自己 Ack 后的事实为准。旧 Pack 中的 native locator 不是下一 Runtime 的 binding 来源。

`bound` 只代表 PAOS 本地 binding 结构完整，不代表已经跨仓验证 CAT ownership。Runtime 必须 GET Room 并确认 `room.paos_binding.project_id == current PAOS project_id`；为空或不同都停止 CAT 步骤并报告，禁止把别的 Project Room 当成本 Project Room 使用。

## 6. CAT existing-only rebind

CAT 当前已有同-ID participant upsert。M3 CAT 第一包不改 Service/Store，而是增加 Agent-side adapter：

`runtime_adapters/cat_self_rebind.py`

adapter 必须：

1. GET Room；
2. Room 必须是 open；
3. Room `paos_binding.project_id` 必须存在且等于当前 PAOS Project；未绑定或属于另一 Project 时 fail closed；
4. exact Participant 必须已存在；
5. existing `paos_session_id` 必须为空或等于当前 durable PAOS Agent；
6. 已经是目标 Runtime state 时直接成功，不 POST；
7. 否则以**相同 participant_id**调用现有 participant upsert；
8. POST 后再次验证 Room Project ownership、participant count、participant ID 与 Runtime locator。

Participant 不存在、Agent binding 冲突、Room 未绑定 Project 或跨 Project Room 引用都 fail closed；普通 takeover 不得创建替代 Participant，也不得认领未绑定 Room。

这条边界解决的是“有效使用权”而不是在 PAOS 内建立第二份全局 Room registry。即使 Restore 或人工误配让两个 PAOS Project 暂时都写着同一个 `cat_room_id`，只有与 CAT Room 自身 `paos_binding.project_id` 一致的 Project 能完成 self-rebind；另一方必须失败并由 Human 修正。

## 7. Mailbox / CAT Exchange 边界

```text
PAOS Mailbox = formal responsibility projection
CAT Exchange = realtime collaboration transport
```

M3 不把 Exchange 复制到 Mailbox，也不把 CAT ack 当 PAOS Request resolve。

需要持久化的长期事实、Artifact、Review、Request 等继续走各自 PAOS canonical workflow。

## 8. Restore

Restore 回滚 PAOS business projection 时，`cat_room_id/cat_participants` 与其它 Project business fields 一样跟随被恢复的 Project snapshot。

M3 不从 Ledger 复活“未来 CAT binding”。如果 Restore 后本地 `cat_room_id` 已经指向另一个 Project 的 Room，CAT self-rebind 会按 Room 自身 `paos_binding.project_id` fail closed；Human 使用现有 manual PUT 修正绑定。

这和 M1A execution tenure / M1B Working Memory 的不可回退历史语义不同。

## 9. V0 明确不做

- 不自动 Create Agent；
- 不自动启动 GPT/Codex/DS-H；
- 不要求 `participant_id == sNNN`；
- 不迁移/复制 CAT Exchange；
- 不把 CAT health 变成 PAOS Continue/Ack commit gate；
- 不在 PAOS 内 import CAT；
- 不建立第二份 PAOS 全局 CAT Room ownership registry；
- 不新增通用 integration framework；
- 不修改 CAT Service/Store membership 内核，除非审查证明 Agent-side existing-only guard 不够。

## 10. 阻塞验收

1. Human manual PUT 可以原子绑定一个真实 CAT `room-<12 hex>` 与多 Agent exact participant IDs。
2. participant ID 不被 PAOS 自动推导或改名，且 `.` / `..` 不可成为新 continuity binding。
3. Continue 前后 stable CAT binding 完全相同。
4. 新 Context Pack 对 bound Agent 给出同一 Room/Participant，并明确要求校验 `paos_binding.project_id`；unbound Agent 不收到伪造 CAT 指令。
5. incomplete/invalid binding fail visible，不猜值。
6. CAT 不可用不阻塞 PAOS Continue/Ack。
7. CAT adapter 对 missing participant / PAOS Agent mismatch 在 POST 前失败。
8. CAT adapter 对未绑定 Project 的 Room / 跨 Project Room 引用在 POST 前失败。
9. successful rebind participant count 和 ID 不变，只更新 Runtime locator，并保持 Room Project ownership 不变。
10. exact target state 重试不重复 POST。
11. Mailbox/Working Memory/M1A tenure 不回归；PAOS 与 CAT 各自 verifier 全绿后才合并。

P2 Project ownership 收紧改变了双仓 exact head；之前的全量 PASS 不继承。当前 head 必须重新通过 focused ownership review 与双仓既有完整 verifier 后才能合并。
