# 03 写入契约：mutate_v2

PAOS 所有项目状态变更走同一个函数：`ProjectStore.mutate_v2`（`attention-dashboard-v1-static/project_store.py:701`）。

理解这一个函数，就理解了 PAOS 为什么敢把状态全放在 JSON 文件里。

## 锁内九步

docstring（`project_store.py:719-733`）把顺序写死了：

```text
幂等检查 → 读取校验 → touched-path 冲突检查 → execution-claim 校验
  → 深拷贝 apply → 校验 → event+receipt → 备份 → pre_commit_hook → 原子替换
```

任一步失败都不写盘（备份除外），不产生 revision。

##  revision 的三种关系

调用方传 `expected_revision`（我基于哪个版本改的），store 拿它和 `current_revision` 比：

| 情况 | 处理 |
|---|---|
| `expected > current` | 直接冲突，报错（753-756 行）。你基于一个还不存在的版本在改。 |
| `expected == current` | 正常路径。 |
| `expected < current` | 你落后了。检查 `touched_paths` 在落后期间有没有被别人动过：没冲突就**基于最新状态自动 rebase 再应用**，有冲突才 409（786-795 行）。 |

第三条是关键：它不是"落后就拒绝"，而是"落后但没碰同一块就可以自动前进"。这让并发的独立改动不会互相打架。

`require_exact_revision=True` 是例外开关（779-782 行）：项目根目录迁移这类一次性危险操作，要求精确基线。

## 幂等靠 operation_id + request_hash

同一个 `operation_id` 再来一次：

- `request_hash` 相同 → **返回原 receipt**，不重复写（763-770 行）。网络重试、脚本重跑都安全。
- `request_hash` 不同 → 409 冲突。同一个 ID 请求内容变了，说明有地方搞错了。

还有一层：`_state_was_corrected_after` 检查。如果期间发生过人工 Restore，旧 receipt 虽然永久保留作证据，但不再允许重放（758-769 行的注释解释了理由：它不能再证明当前投影仍包含那次操作的效果）。

## Ledger 和 receipt 同文件提交

一次 mutation 会产生两样东西：

- **Ledger event**（835-852 行）：`event_id`、`event_type`、`base_revision`、`revision`、`touched_paths`、`allocated_ids`、`summary`。追加到 `project["ledger"]`。
- **operation receipt**（874-888 行）：同一次操作的回执，存在 `operation_receipts[operation_id]`。

两者都写在**同一个项目 JSON 里**，和状态变更一起原子提交。不会出现在"状态改了但 ledger 没记"的中间态。

## 备份 → hook → 写盘，顺序有讲究

```python
self._atomic_write(self._backup_project_path(project_id), current)   # 890：先备份旧状态
if pre_commit_hook is not None:
    pre_commit_hook(updated, self)                                    # 892：外部写入
self._atomic_write(path, updated)                                     # 893：最后写新状态
```

`pre_commit_hook` 存在的理由写在 docstring（730-732 行）：给"必须与项目提交同进退"的外部写入用，典型是 Context Pack。hook 抛错则项目**不写盘**，满足"Pack 写失败时项目状态不得提交"。

注意顺序：备份在 hook 之前。所以 hook 失败时，磁盘上仍然是旧状态，备份文件里也是旧状态，没有半截状态。

## execution claim：防绕过

`enforce_store_execution_claim`（801-806 行）在**真实锁内、业务 apply 之前**执行。docstring（725-728 行）说明了原因：如果放在 workflow 预检，就会留下"预检通过 → 并发 handover → 再写 store"的窗口。放在锁内，这个窗口不存在。

受保护事件即使在 `runtime_handover` 后绕过 scope 直写 store，同样会被拒。

## allocated_ids 高水位

apply 期间新分配的对象 ID（Session ID、Event ID 等）会被记进 ledger（830-832 行）。注释给了理由：这样 `restore` 之后 `allocate_id` 仍能看到它们，**不复用已审计的编号**。

## 原子写本身

`_atomic_write`（149 行）是静态方法，写临时文件再替换。配合上面的顺序，构成"要么全成，要么完全没动"。

## 分层禁止

这几条在 `docs/CODE-MAP.md:89-95` 写了，代码里也是这么落：

- `local_server.py` 不写磁盘、不调 `_atomic_write`；
- contracts 不 import `ProjectStore` / `WorkflowService` / `local_server`；
- `project_store.py` 不 import workflow 模块。

`docs/CODE-MAP.md:95` 还额外冻结了一条：`mutate_v2` / Ledger / receipt / backup / Restore / 原子写默认不重构，除非发现真实 bug。改这块之前先读 `AGENTS.md:25`。
