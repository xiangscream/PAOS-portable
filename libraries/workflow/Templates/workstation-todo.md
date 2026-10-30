---
schema: paos-workflow/v1
id: template-workstation-todo
title: TODO v3 模板
description: 本人当前目标、下一步、等待与成果；八个默认字段，按需补在途信息。
tags: template, todo, current
status: active
version: 9
---

# 复制下方正文

```markdown
---
schema: "paos-todo/v3"
home_kind: "project_agent"
home_id: "<home-id>"
project_id: "<project-id>"
---

# Current
objective: "<当前目标>"
approved_scope: "<已获准范围>"
stage: "<当前阶段>"
next_action: "<下一项可执行动作>"
waiting: "<谁提供什么、结果位置和回流方式；没有则写无>"
result_refs: ["<当前成果路径或引用>"]
input_version: "<本轮实际输入版本或原消息>"
history_ref: "<长过程与已完成任务的历史入口>"

# Tasks

### T-001
schema: "paos-todo-task/v1"
title: "<任务标题>"
state: "doing"
waiting: ""
result: ""
artifact_ref: "<成果位置>"
notify_after: []
```

Current 默认用这八项说明当前任务，长期岗位职责留在本人角色规则，历史过程沿 `history_ref` 阅读。只有 `objective` 和 `next_action` 是解析必需项，其余按实际需要填写。元数据填写本人 `home_kind`、`home_id`；Project Agent 还需 `project_id`。元数据和正文字段中的字符串值保持双引号，包括数字形式的 Project ID；列表仍用 JSON 数组。已有解析器支持的其他字段仍可使用，不必为套模板添加空字段。

真实在途外部写入需要接续时，再加 `inflight`，写清目标、控制人、查看与停止入口。历史输入和重复状态缓存留在原成果中，Current 引用原件。

## 任务状态

每个任务使用独立 ID，字段值写成单行。按实际进展使用以下状态：

| state | 示例 |
| --- | --- |
| todo | 已登记任务，下一步开始执行 |
| doing | 正在修改正文或处理输入 |
| waiting | 等同事给原件；waiting 写明负责人、结果位置和回流方式 |
| done | 成果已保存，result 与 artifact_ref 指向实际结果 |
| cancelled | 目标被明确取消；result 写明取消依据 |

需要完成后回告的来源放 `notify_after`，没有则保留空列表。消息已发但下游尚未接续时，保留真实等待；个人任务 done 不代替项目验收。长过程放原报告或历史页，不复制进 Current。

目标、成果、下一步或等待有实质变化时更新本人 TODO。具体写入、回读与异常定位只按[共享 OPS](../Guides/guide-paos-cat-operations.md#当前页与输入)。
