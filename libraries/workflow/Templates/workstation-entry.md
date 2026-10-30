---
schema: paos-workflow/v1
id: template-workstation-entry
title: Workstation ENTRY 模板
description: 身份与稳定入口；当前动作在TODO、原生连接在Contact、版本在成果。
tags: template, workstation, entry
status: active
version: 9
---

# ENTRY 正文模板

生成时将路径占位符填写为当前安装的真实绝对路径，并核对链接；本人规则指工位 AGENTS，未单设时指 Project AGENTS。不要把以下占位符原样写入工位。

- 长期 Agent：<agent-id>
- Project：<project-id>；根：<absolute-project-root>
- 固定工位：<absolute-workstation-root>
- 当前执行页：[TODO](TODO.md)
- Project 规则：[Project AGENTS](<absolute-project-root>/AGENTS.md)
- 本人规则：[AGENTS](<role-rules-path>)
- 当前同事：[TEAM](<absolute-project-root>/TEAM.md)
- 持久消息：mailbox/
- 安装入口：<stable-installed-cli-entry>
- 恢复正文：[Agent 工作循环](<workflow-root>/Workflows/wf-agent-work-cycle.md#恢复)
- 方法导航：[GUIDE](<workflow-root>/Guides/guide-work-method.md)
- 操作入口：[OPS](<workflow-root>/Guides/ops-entry.md)
- Workflow 目录：[Catalog](<workflow-root>/CATALOG.md)
- Skill 目录：[Catalog](<skill-root>/CATALOG.md)
- Tool 目录：[Tool Index](<tool-index-path>)
- 表达规范：[简明表达指南](<workflow-root>/Guides/guide-concise-writing.md)

新会话、压缩恢复和职责纠偏直接按恢复正文继续。工位只保留稳定入口，恢复步骤与通用业务规则链接共享正文。

本页记录身份与稳定入口；当前动作在TODO、原生连接在Contact、版本在成果。Rooter继续使用Rooter Home管理入口，角色沿正式岗位事实。

新Codex工位或换Runtime的入口准备按[Rooter原入口恢复说明](<workflow-root>/Guides/guide-rooter-installation.md#原入口恢复)。
