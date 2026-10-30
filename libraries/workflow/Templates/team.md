---
schema: paos-workflow/v1
id: template-team
title: TEAM 模板
description: 当前人工成员目录，稳定联系与历史入口。
tags: template, team, peers
status: active
version: 4
---

# TEAM 正文模板

```markdown
# Team

## 当前成员

### <stable-agent-id>
- 成员状态：在队
- 职责/专长：<由 Coordinator 确认职责，本人补充专长>
- Harness：<本人使用偏好>
- 工位：Workstations/<agent-id>/ENTRY.md
- 当前动作：Workstations/<agent-id>/TODO.md
- 联系：PAOS <agent-id>；已有 CAT 讨论沿原线程回复
<!-- 单处维护：岗位简介/联系元数据只在本文件维护；API 与网页读同一投影，不再各抄一份 -->

## 历史与变化
- 历史成员与交接：<已有历史入口>
- 版本变化：本文件 Git 历史
```

Coordinator 维护成员归属/职责，本人局部维护介绍、Harness、工位和稳定联系方式。不手抄当前责任、原生会话 ID、generation、端口或在线状态。读最新文件后只更新负责的小节；冲突不整表覆盖。TEAM 不是授权文件，在队不等于在线。

同事状态读面从正式绑定和实际 Harness 派生当前在线/忙碌/离线/未知、服务端口、会话与检查时间，提供可复制的打开/attach命令，并链接成员 TODO。当前任务、下一步和阻塞从该 TODO 派生，不维护第二份进度。修改时间仅表明文件更新；不据此断言 Agent 正在执行。离线时单独展示已知的手动服务启动方法，不自动启动 Harness。
