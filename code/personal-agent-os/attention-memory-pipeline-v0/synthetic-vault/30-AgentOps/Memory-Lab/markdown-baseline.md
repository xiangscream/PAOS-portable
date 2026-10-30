---
schema: attention-note/v0
id: task-memory-markdown-baseline
object_type: thread_state
domain: agent_ops
project: Agent-Memory-Lab
thread: markdown-baseline
scope: thread
status: active
review_state: reviewed
sensitivity: personal
updated: 2026-07-21T21:00:00+08:00
attention: true
long_term: true
last_progress_at: 2026-07-21T21:00:00+08:00
weekly_target: 2
weekly_progress: 1
---

# Agent 记忆系统：完成 Markdown 合成数据基线

## 摘要

验证文件变化、来源索引、候选降级和跨域边界，不连接真实资料。

## 当前唯一问题

纯 Markdown 是否足以保留来源、变化和候选边界，并稳定生成可审查记忆对象？

## 阶段交付物

一套合成数据基线：状态文件、来源索引、变化报告和候选清单。

## 完成定义

每个对象可追溯到相对路径和哈希；模型推断留在候选；扫描不改写来源。

## 上下文

- 所有模型推断只能进入候选
- 每个对象必须能返回相对路径与哈希
- 先验证纯 Markdown 上限

