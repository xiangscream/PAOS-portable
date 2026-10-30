> **历史设计稿**：本文为早期设计原稿（三态 Work 等旧口径），仅用于解释历史设计思路；**现行对象/状态以 [`V1.2-BASELINE.md`](V1.2-BASELINE.md) 与本项目合同为准**。历史正文保持原样。

# Area → Project → Work Item 模型

当前模型只解决一件事：把分散在多个 Vault、目录和 Agent 会话中的材料，组织成能继续推进的项目视图。

```text
Area（长期责任域）
  └─ Project（有限或持续的项目）
       └─ Work Item（一次可结束的成果）
            └─ Session（证据，不是新的管理层）
```

## 固定 Area 与编号

| 编号段 | Area | 示例 |
|---|---|---|
| `1xxx` | 程序性工作 | `1001` 周报、`1002` 调研 |
| `2xxx` | 工作 | `2001` LRC101 |
| `3xxx` | 项目 | `3001` obs-agent、`3002` Personal Agent OS |

`project_id` 只有这一套四位数字字符串，不保留英文别名。编号关闭后封存，不复用。Area 变化意味着项目身份变化，不能只改下拉框。

## Work Item

Work Item 必须描述一个能结束的成果，而不是宽泛话题。例如：

- 好：`2001-w001 收敛 LRC101 产品主线`
- 差：`聊 LRC101`

编号使用 `<project_id>-wNNN`。状态只有 `todo / doing / done`。

## Session 关联

- Session 保留 Agent 的原始标题，不重命名。
- 每条 Session 关联必须给出 `work_item_id` 和 `reason`。
- 同一 Session 可以服务多个项目；每个项目分别记录关联原因。
- 工作目录、关键词或最近活跃时间只产生候选，不自动成为项目成员。
- 无法明确归属的会话继续留在 Session 目录中，不制造虚假的整齐。

## 数据所有权

- `human`：原始要求、当前承诺、DDL、确认时间；只接受用户明确修改。
- `generated`：阶段、进展与成果、最近变化、当前缺口；可由 Agent 增量更新。
- `work_items` 与 `sessions`：系统先生成，用户可纠正。

真实数据位于 `private-data/project-registry/`，被 Git 永久忽略；仓库只保留合成样例和校验逻辑。
