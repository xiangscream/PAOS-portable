---
schema: attention-note/v0
id: tip-weak-model-canary
object_type: tip
domain: agent_ops
project: unassigned
thread: inbox
status: active
review_state: candidate
sensitivity: personal
updated: 2026-07-29T08:42:00+08:00
dedupe_key: weak-model-canary
---

# 把弱模型作为 Prompt 歧义探针

## 摘要

如果弱模型无法稳定复述目标、输入、允许动作和停止条件，就继续补写 Prompt，最多三轮。

## 为什么值得记

弱模型的误解可以暴露边界条件缺口，但不能证明任务方案正确。

## 上下文

- 三轮后仍不一致，由用户介入
- 只进入候选区
- 不自动创建实施任务

