# V1.1 Baseline Reconstruction — Local Agent TODO Report Template

> 本模板用于 M0 盘点与后续每个迁移 Batch。它不是额外治理 Store；正式当前任务仍维护在各 Agent 自己的 `TODO.md`。本报告用于跨 Agent / web lead 对齐迁移事实与 proposed changes。

## 1. Identity

```text
Agent:
Role:
Project:
Runtime:
Local workspace root:
Report time:
Baseline SHA / version:
```

Runtime 只用于描述本次观察环境，不定义 Agent 身份。

## 2. Current local facts

只写实际看到的事实：

```text
- path / object:
  observed:
  currently used by:
  confidence:
```

不要把推断写成事实。

## 3. Friction / ambiguity

```text
F-001
Observed friction:
Where it happens:
How often / evidence:
Impact:
Possible cause:
Needs canonical decision: yes | no
```

重点记录网页端无法直接观察的本地摩擦。

## 4. Proposed migration TODO

每项使用：

```text
ID: M1-001
Workstream: M0 | M1 | M2 | M3 | M4 | M5
Object / path:
Observed fact:
Proposed action:
Why:
Mutation class:
Risk: low | medium | high
Dependencies:
Done When:
Evidence to return:
Owner:
Reviewer:
Rollback / recovery:
Decision needed:
Status: proposed
```

Mutation class：

```text
read-only
create
edit
move
archive
merge
generated-delete-candidate
retire-reference
```

## 5. Do-not-touch / decision list

列出本地 Agent 不应自行处理的对象：

```text
D-001
Object:
Why ambiguous / risky:
Possible options:
Evidence:
Who should decide:
```

## 6. Suggested ordering

只写依赖，不把自己的偏好伪装成全局计划：

```text
M1-001 before M1-004 because ...
M3-002 blocks M4-001 because ...
```

## 7. Current personal TODO alignment

把自己工位 `TODO.md` 中与本次迁移相关的当前状态压缩列出：

```text
Current stage:
Current accepted tasks:
Current blocker:
Next safe action:
Waiting for:
```

如果本地 `TODO.md` 与收到的 migration assignment 冲突，必须先报告，不直接覆盖。

## 8. Proposed P1 / P2

```text
P1:
- ...

P2:
- ...
```

P1 是会破坏 canonical truth、丢失 active data、制造双入口、导致 active Run 错误或阻断迁移的事项。

P2 是不阻塞当前 baseline、但应跟踪的清理债务。

## 9. Summary for reconciliation

最多回答五件事：

```text
1. 我实际发现了什么？
2. 哪些地方和原计划不一样？
3. 我建议新增 / 修改哪些 TODO？
4. 哪些动作现在不安全？
5. 我下一步在不改变 canonical policy 的前提下还能安全做什么？
```

---

# Batch completion addendum

执行获批 TODO 后追加：

```text
Completed TODO IDs:
Actual changes:
Exact paths:
Catalog / index rebuild:
Verification:
Unexpected friction:
New TODO proposals:
P1:
P2:
Current TODO after closeout:
Next safe action:
```

不要只汇报“已完成”。必须能让 reviewer 与 web lead 判断：实际事实是否与预期 canonical result 一致。