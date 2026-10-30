# T-MA-01 · Codex 稳定 Stop-hook 适配器（一次性安装，Run 不再改配置）

解决方案：把「Hook 配置加载」和「Run 激活」分开。每个 Run 只 `activate/deactivate`，不再反复改 `hooks.json`、不再反复 Review/Trust。

## 一次性安装（每台 Codex Desktop 只做一次）

1. 稳定适配器定点路径：

```text
{{adapter_path}}
```

2. 写入 `~/.codex/hooks.json`（只写一次；如已有 hooks，把 `Stop` 条目合并进去）：

```json
{{stable_hooks_json}}
```

3. 在 Codex 的 `/hooks` 中 Review、Trust 并**刷新**。本机 2026-08-25 已实测：刷新后当前进程即加载新配置，无需重启；若刷新后仍未生效，再重启一次作为兜底。此后不再改这份配置。

## 每次 Run（不再重启）

```text
python collab_run.py create <RUN_DIR> --session-id S --request-id R
python collab_run.py activate <RUN_DIR>     # 写 active-run 指针
# ... Worker 进入、写 marker，稳定 hook 在每次 Stop 边界检查并续步 ...
python collab_run.py stop <RUN_DIR>         # 需要时人工停止
python collab_run.py deactivate             # 撤销指针（hook 变空操作）
python collab_run.py cleanup <RUN_DIR> --yes
```

稳定适配器每次 Stop 都运行，但：

- 无 active-run 指针 → 立即 `exit 0`，空操作；
- 有指针 → 检查 `STOP` / `expires_at` / `max_steps` → 到界即放行；
- 首次看到本 Run → 写 `hook_seen` 探针事件；
- 有合法 marker 且未到界 → 原子抢占、校验身份后消费，block 一次（stdout JSON + `exit 0`）。

## 与临时实验模式的关系

- 临时模式（`codex/hooks.json` + `codex/stop_hook.ps1`）：用于隔离实验；每 Run 一份，路径变化会重建配置。
- 稳定模式（本文件）：生产默认；首次安装/信任/刷新一次，之后每 Run 只 `activate/deactivate`。

## 边界

- 稳定 Hook 只是 Runtime 适配器，不理解业务；业务判断仍由 Worker 与 PAOS Request 完成。
- PAOS 不启动 Codex；本工具只管理本地执行信封。