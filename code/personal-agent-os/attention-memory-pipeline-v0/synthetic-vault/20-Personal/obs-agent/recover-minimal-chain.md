---
schema: attention-note/v0
id: task-obs-agent-recovery
object_type: thread_state
domain: personal
project: obs-agent
thread: recover-minimal-chain
scope: thread
status: active
review_state: reviewed
sensitivity: personal
updated: 2026-07-19T19:00:00+08:00
attention: true
long_term: true
last_progress_at: 2026-07-19T19:00:00+08:00
weekly_target: 2
weekly_progress: 0
---

# 推进 obs-agent：恢复最小可运行链路

## 摘要

先验证上一个可运行版本，再恢复 Dashboard 到 Agent API 的最短链路。

## 当前唯一问题

怎样先恢复上一个可运行版本，并证明 Dashboard 到 Agent API 的最短链路仍然成立？

## 阶段交付物

一条可重复执行的最小链路，以及日志、Console、Network、最小请求四类定位证据。

## 完成定义

新机器按文档能重新部署；故障时能恢复到上一个可运行版本；最小请求能独立通过。

## 上下文

- 已超过一周没有推进
- 本周目标是至少推进两次
- 固定调试顺序是日志、Console、Network、最小请求

