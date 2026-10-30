---
schema: attention-note/v0
id: workflow-pattern-prompt-canary
object_type: workflow_pattern
domain: agent_ops
project: Agent-Memory-Lab
thread: prompt-review
scope: evolution
status: active
review_state: candidate
sensitivity: personal
updated: 2026-07-29T08:45:00+08:00
dedupe_key: weak-model-canary
---

# 弱模型 Prompt 歧义探针候选

## 摘要

让弱模型固定复述目标、输入、允许动作、禁止动作、完成标准、停止恢复和未知项。

## 上下文

- 自动补写最多三轮
- 三轮后用户介入
- 只证明指令是否容易被误解

