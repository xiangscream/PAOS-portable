# 04 Context Pack 与握手 Prompt

Session 开成功后，PAOS 要生成一份给 Agent 的入场材料，这就是 Context Pack，外加一份可直接粘贴的握手 Prompt。

## 两个文件，两层职责

| 文件 | 职责 |
|---|---|
| `context_compiler.py`（732 行） | 基础编译器：`build_context_pack`（95 行）+ `build_prompt_markdown`（713 行） |
| `context_pack_composition.py`（113 行） | 组装管道：`compile_context_pack`（34 行），把各 bounded 数据段按顺序拼好 |

`WorkflowService._compile_context_pack`（`workflow_service.py:61-70`）只有一个实现，注释写着 "Single explicit Context Pack entry owned by WorkflowService"。调的是 `context_pack_composition.compile_context_pack`，不是 `context_compiler` 直接暴露的函数。

## 组装管道讲了什么

`context_pack_composition.py` 的 docstring 说明了它为什么存在：

> One named pipeline replaces the previous implicit `super()._compile_context_pack` MRO chain.

以前靠 mixin 的 MRO 链隐式调用（`super()._compile_context_pack`），现在换成一条**具名的、可见顺序的**管道：读已读好的 Project 快照 + Session，按顺序构建每个 bounded 数据段，**base Prompt 只渲染一次**，然后再依次套用各 feature section injector。

顺带记下它划的边界（同一段 docstring）：这个模块**不读 Store、不写项目数据、不调 HTTP/CAT、不读 Artifact 正文**。

还有一个容易忽略的细节：Mailbox 用**真实**项目事实构建，而 base compiler 及其下游的 Working-Memory / Artifact / CAT 各阶段拿到的是 **Context-only 的 Project 视图**，其中 legacy 的宽 Request 列表被屏蔽掉了。

## 纯投影，不写盘

`context_compiler.py` 开头就写了：

> Builds Brief / Standard / Deep Context Packs and the handoff prompt markdown for a newly opened Session. Pure projection over project state; no writes. **Materials are references only — never file content.**

最后一句是硬约束：Pack 里给的是材料的**引用**（路径、ID），不是文件内容。想看内容自己去读。

三档：Brief / Standard / Deep。

## Prompt 是一段段拼出来的

`build_prompt_markdown`（713 行）由一系列 `_append_prompt_*` 函数拼装，每个负责一段：

- `_append_prompt_header`（266）
- `_append_prompt_work`（293）
- `_append_prompt_continuation`（309）—— 接班说明
- `_append_prompt_work_boundary`（340）
- `_append_prompt_friction_duty`（351）
- `_append_prompt_assignment`（386）
- `_append_prompt_authority`（399）—— 权限
- `_append_prompt_materials`（415）
- `_append_prompt_delta`（461）
- `_append_prompt_protocol`（533）
- `_append_prompt_examples`（572）

改握手 Prompt 的措辞，找对应的 `_append_prompt_*`，不要在 `build_prompt_markdown` 里塞内容。

## 落盘有独立的保护

`ProjectStore.write_context_pack_atomic`（`project_store.py:914`）负责写，而且它比普通写入更挑剔：

- 文件已存在且**没有 `meta`** → 视为历史快照，**拒绝覆盖**；
- 已存在且 `meta.operation_id` 不同 → 拒绝覆盖（不同 operation 不互相覆盖）；
- operation 相同但 `request_hash` 不同 → 拒绝覆盖；
- 写失败就抛错，项目提交不会发生。

写盘时带上 `meta`（`operation_id`、`request_hash`、`written_at`），所以每个 Pack 都能追溯到哪次操作产生的。

## Pack 和项目状态同进退

Pack 的写入挂在 `mutate_v2` 的 `pre_commit_hook` 上，位置在备份之后、项目写盘之前（`project_store.py:890-893`）。

含义：Pack 写失败 → 项目状态也不提交；反之项目写盘成功，Pack 一定已经落盘。不会出现"Session 开了但入场材料没生成"的孤儿状态。

## 回写标记

`context_compiler.py:26-27` 定义了两个常量：

```python
ACK_MARKER = "PAOS_SESSION_ACKNOWLEDGED"
UPDATE_MARKER = "PAOS_SESSION_UPDATED"
```

Agent 完成任务回写时靠这两个标记被识别。它们出现在生成的 Prompt 里，Agent 按协议原样回填。
