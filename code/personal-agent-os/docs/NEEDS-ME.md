# Needs Me Projection

## 定义

Needs Me = “没有人类介入，当前工作就无法正确继续的事项”。它是纯投影，不落盘、不新增可编辑字段。

API：`GET /api/projects/{project_id}/needs-me`

## 分类

| 类别 | 规则 |
|---|---|
| `decision` | `Decision.status == proposed` |
| `integration` | `request_type == "integration"` 且 `requires_human == true` |
| `request` | 其余 `open` 且 `requires_human == true` 的 Request |
| ~~`blocker`~~ | 已退役：Work 不是系统对象，不再产生该类别；`counts.blockers` 恒为 0 |

## 旧数据推断

旧 Request 没有 `requires_human` 时只读推断：
- `target_session_id` 存在 → `false`
- `target_identity_id` 存在且 != `human` → `false`
- `target_identity_id == human` → `true`
- 没有 Agent target → `true`

不批量迁移旧数据。

## 输出

```json
{
  "total": 7,
  "counts": {
    "decisions": 2,
    "blockers": 0,
    "requests": 3,
    "integration": 1
  },
  "items": []
}
```

旧 Office 保留，等 UI 迁移完成后再降级。
