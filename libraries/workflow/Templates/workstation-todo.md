---
schema: paos-workflow/v1
id: template-workstation-todo
title: TODO v4：Obsidian 原生工位
status: active
version: 10
description: 一份可由 Obsidian 阅读和编辑、由 Agent 有界读写的 Pinned + Current + Tasks 工位原件。
tags: template, todo, current, obsidian
---

# 工位 TODO v4

复制下面的正文到已登记 Home 的 `TODO.md`，并改为本人的真实身份与工作。
Rooter 的 `home_kind` 用 `rooter`，`project_id` 用空字符串。

```markdown
---
schema: "paos-todo/v4"
home_kind: "project_agent"
home_id: "3002-s010"
project_id: "3002"
---

# Pinned

- 项目最新口径：[[INDEX]] 所指向的唯一当前正文。
- 本次 Human 要求：直接引用准确消息或原始记录，必要时在此简记。

# Current

- **Objective:** 更新项目口径并处理未完成输入
- **Next action:** 阅读新增日会并核对原文
- **Waiting:**
- **Inflight:**
- **Context refs:**
  - [[Materials/日会记录]]
- **Result refs:**

# Tasks

- [/] **T-001** · 从日会提取影响下一步的结论
  - **Source refs:**
    - [[Materials/日会记录]]
  - **Artifact:** [[Works/日会整理]]
```

## 原则

- `Pinned` 是任意正常 Markdown，可写长原话、引用、二级标题；不是另一套项目概览。
- `Current` 只记录当前目标、下一步、等待、真实在途和需要的引用。只需 `Objective`、`Next action` 两个必填字段；不要添加旧 `stage`、`generated` 等重复状态。
- `Tasks` 直接用 Markdown checkbox 表达任务状态：`[ ]` todo、`[/]` doing、`[?]` waiting、`[x]` done、`[-]` cancelled。**不再维护第二行 `state`**。Obsidian 原生识别任务列表；非标准字符的特殊视觉样式依赖主题/插件，但不影响文件解析。
- 任务 ID 稳定，显示为 `- [/] **T-001** · 描述`；可选 `Waiting`、`Result`、`Artifact`、`Source refs`、`Acceptance refs`、`Notify after` 以缩进子列表记录。不要把长成果全文塞进 TODO。
- 修改 `Current` 用 `attention todo-update` 或 `rooter-todo-update`，只写管理区，保留 `Pinned` 和 `Tasks` 原始字节及其换行。修改 Pinned、任务标题、勾选框和任务引用用完整 `todo-write`；CLI 读完后使用 `--expected-fingerprint` 防止过期覆盖。
- `todo-write` 会验证身份、状态与引用，拒绝旧 v3；历史业务原件不自动修改。旧工位需要一次明确的离线转写、引用校核，再用合法完整写入替换，不在运行时兼容两套合同。
- 短期任务进展留在 TODO，跨工位的长久项目共识归 OB 项目唯一最新口径，原始输入归档保留精确来源。
