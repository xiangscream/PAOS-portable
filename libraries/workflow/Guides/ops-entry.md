---
schema: paos-workflow/v1
id: ops-entry
title: 操作入口：按目的找命令
description: 本地工位、持久输入、方法库与显式运行通道。
tags: ops, operations, entry
status: active
version: 29
---

# 操作入口

先选当前任务需要的入口，不加载全套状态或历史。命令查同版 `--help`。

| 目的 | 入口 |
| --- | --- |
| 恢复本人工作 | `orient` / `attention show`，再读 ENTRY、当前输入与必要原件 |
| 输入与交接 | `inbox` / `mail` / `agent send --remind` |
| 接手与更新 | `attention takeover` / `todo-update` / `todo-write` / `handle` |
| 找同事与联系状态 | `peers` / `team` / `status` / `wake status` |
| 方法复用与工具 | `library search` / `library tools` |
| 本项目经验 | `project experience`；正文按文件/Git维护 |
| 安装定位 | `install show` / `install configure` / `health` |
| 对话、日会、Tips 归位 | [日常输入整理](../Workflows/wf-meeting-audio-package.md) |

命令用途与已退出入口见[接口参考](guide-paos-interface-reference.md)。
投递和提醒语义见[操作指南](guide-paos-cat-operations.md)；日常职责按[工作循环](../Workflows/wf-agent-work-cycle.md)。
