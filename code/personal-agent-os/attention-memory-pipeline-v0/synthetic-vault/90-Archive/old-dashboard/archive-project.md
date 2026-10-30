---
schema: attention-note/v0
id: archive-old-dashboard
object_type: archive_project
domain: personal
project: old-agent-dashboard
thread: archive
scope: project
status: archived
review_state: reviewed
sensitivity: personal
updated: 2026-07-29T08:20:00+08:00
---

# 旧版 Agent Dashboard / Proxy 实验

## 摘要

试图打通 Dashboard、Proxy、模型与多 Agent，但同时改变过多组件，最终无法判断故障位置。

## 项目墓志铭

信息墙的产品动机仍然成立，工程实现因缺少最小链路和分层调试而停摆。

## 为什么停

前端、代理、构建和模型路线反复切换；遇到错误后继续加功能。

## 留下什么

- Dashboard 与 Agent API 的基础结构
- 日志、Console、Network、最小请求的调试顺序
- 不能同时修改太多组件的失败证据

## 值得重启的条件

能够先冻结一个 API 契约，并只恢复单 Agent 最短链路。

## 第一小时

找到最后可运行快照，只启动前端与一个最小请求，记录第一个失败层。

