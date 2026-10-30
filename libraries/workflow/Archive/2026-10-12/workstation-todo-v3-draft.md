---
schema: paos-workflow/v1
id: template-workstation-todo-v3
title: WS TODO v3 模板（已退役并入 v5）
description: 已退役（并兼并出当 template-workstation-todo v5 v3 合同语义）：生产 Home 已 v3 采用（13 Home 全部转换），此 candidate 版保留作为字段来源过程记录（scripts/paos_todo_v3.py PR126）。
tags: template, workstation, todo, v3, candidate
status: historical
version: 1
---

# TODO v3 模板（已退役并入；历史过程记录保留）

> **已并入当前采用面 `template-workstation-todo` v5**（paos-todo/v3 同一合同模板，双源收敛至一处）；本文件不再用于当前生成，保留为字段来源过程记录与早期收窄依据；candidate-source 本家历史字段类别在 PR126 中。

字段来源（唯一）：`candidate-source/scripts/paos_todo_v3.py`（normalize_task / render_todo_v3）。以下模板如实反映其合同；两处必填=objective / next_action；project_agent 必带 project_id。

```markdown
---
schema: paos-todo/v3
home_kind: project_agent
home_id: <Home 精确地址·如 3002-s032>
project_id: <project_agent 必填>
---

# Current

objective: <本次目标（必填）>
approved_scope: <已批准范围/授权口径>
current_work: <正式 Work 引用；短动作可不带 Work>
stage: <阶段>
next_action: <下一个动作（必填）>
waiting: <等谁/等什么/解除后做什么>
results: <成果落点说明>
result_refs: <结果引用 list>
context_refs: <上下文引用 list>
legacy_source_ref: <迁移来源引用（V1.3 转换件必填）>
inflight: <在途外部动作句柄>
alignment_ref: <对齐依据（本文件/Work/上级安排）>
input_version: <输入/候选版本>
delivery: <交付路径>
dependencies: <依赖>
continuation_to: <接续对象>

# Tasks

### <task-id>
schema: ["paos-todo-task/v1"]
title: <一句话目标>
state: <todo|doing|waiting|done|cancelled>
waiting: <等待说明（state=waiting 时用）>
result: <结果一句话>
artifact_ref: <成果 locator>
notify_after: [{"to": "<收件 Home>", "when": "<解除条件/何时", "source_ref": "<结果 source 引用>"}]
```

## 维护口径（对照 P5 交付）

- **状态枚举唯一**：`todo / doing / waiting / done / cancelled`（TASK_STATES）；不引入第二处理状态库。
- `notify_after` 是任务内回告要求（to/when/source_ref）；正文做完≠已回告——未兑现回告不随处理状态消失。
- 同 ID 异正文拒绝覆盖；原子按条更新由统一工具承担（本模板只管内容形态）。
- **本模板在 V1.3 采用前仅用于 candidate-library 与转换演练；生产工位不得改写为 v3。**
