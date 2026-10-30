# Project Coordinator

面向实际项目负责人的运行方法见 [`COORDINATOR-OPERATING-GUIDE.md`](COORDINATOR-OPERATING-GUIDE.md)。本文件继续只描述 Coordinator 的数据模型、权限与状态转换合同。

## 模型

Coordinator 是 Project 级长期职责，不是某个 Cycle 的临时令牌。

存储：

```json
{
  "organization": {
    "coordinator_session_id": "3002-s020"
  }
}
```

只有一个字段：`coordinator_session_id`。

## 读取

`project_coordinator_session_id(project)`：
1. 优先 `project.organization.coordinator_session_id`；
2. 旧项目没有 organization 时回退扫描 legacy `session.coordinator`；
3. 都没有则返回 `None`。

保留旧数据只读兼容，不批量迁移真实项目。

## Grant / Revoke

- Grant 写入 `project.organization.coordinator_session_id`。
- 已有不同 Coordinator 时 grant 返回 409，必须先显式 revoke。
- 同一 Session 的重复 grant 仍由 operation receipt 幂等保证。
- Revoke 将 `coordinator_session_id` 清为 `null`。
- Coordinator 授权默认长期有效，不因 Cycle 推进失效；只有 Human 显式 revoke 或授权他人时失效；Reactivate 后角色保持。`granted_cycle` 仅作历史记录。
- 接续 Coordinator Session 时，`organization.coordinator_session_id` 自动指向新 Session。

## 权限

Coordinator 权限不再手写维护。唯一产品事实源是：

- `attention-dashboard-v1-static/authority_manifest.py`
- 生成文档：`docs/AUTHORITY-MATRIX.md`
- 只读 API：`GET /api/authority?actor=coordinator`

Coordinator Prompt 的能力段也从同一 manifest 生成。这样 Route、Workflow、Prompt、文档与未来 CLI 使用同一 action vocabulary。

关键边界：

- Coordinator 的治理动作是四个：创建 Assignment Request、创建定向 Request、维护项目一句话描述（`generated.tagline`）、治理性 Abandon worker Session。
- Decision accept/reject 是 Human-only。
- Restore 是 Human-only。
- Coordinator 不能启动外部 Runtime；PAOS `Session Open` 也不等于 Runtime activation。
- Coordinator 仍是一个 Agent Session，因此保留自身 Acknowledge / Update / Close；Close 只记录本 Session 的 Agent 交班证词，正式责任的验收由 Human 决定。
- Coordinator 不是通用项目编辑器：除 `generated.tagline` 外不写 Project 级字段。
