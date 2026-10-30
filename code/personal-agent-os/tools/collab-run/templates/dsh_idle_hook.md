# T-MA-01 · DS-H 侧接入说明

本 Run 的本地续步由 DS-H 原生 idle-hook 完成。它已经示例化为：

```text
/home/remo/work/deepseek-harness/examples/dsh-turn-hook
```

## 路径约定（重点）

- 本工具运行在 **Windows**，`run_dir` = `{{run_dir}}`。
- DS-H 原生插件运行在 **WSL**，读文件的路径形态不同，因此本 Run 的 DS-H marker 用 **WSL 路径**：

```text
wsl_run_dir = {{wsl_run_dir}}
```

## 用法（目标 DS-H 会话加载该插件后）

1. 用环境变量把该 hook 的一次性 marker 指向本 Run（WSL 形态）：

```text
DSH_TURN_HOOK_MARKER = {{wsl_run_dir}}/dsh_marker.json
```

2. Worker（DS-H 会话）在“决定续步”时，在 **Windows run 目录**维护业务 `marker.json`（供 `collab_run status` 观测），同时写好 DS-H 插件的 prompt marker：

```json
{
  "sessionId": "<DS-H 原生 Session id，例如 session-46af412b-...>",
  "prompt": "[collab-run {{run_id}}] 继续下一步：step_no=N，reason=..."
}
```

3. hook 在 `agent/status==idle` 时读该文件、先删除（一次即废）、再 `agent.followup(prompt)`。

## 与 Codex 的区别

- Codex：hook 消费本 Run 的 `marker.json`（业务结构，含身份校验），自己不算步数。
- DS-H：现有插件只认识 `{sessionId, prompt}`，所以 Worker 额外写一个 `dsh_marker.json`；业务上的 `marker.json`（含 step_no/reason）仍按 Run 规范维护。

## Run 参数（本文件由 materialize 生成）

- run_id: {{run_id}}
- session_id: {{session_id}}
- request_id: {{request_id}}
- max_steps: {{max_steps}}
- expires_at: {{expires_at}}

## 停止口径（诚实区分）

- **Codex：工具级硬限制**——稳定/临时 hook 内置检查 `STOP / expires_at / max_steps`，违规直接不续步。
- **DS-H：Agent 配合下的有界运行**——当前外部 idle-hook 只读 `dsh_marker.json`，不检查 Run 的 `STOP / TTL / max_steps`，因此这些边界由 **Worker 按 WORKER_PROMPT 自律执行**：
  - `{{wsl_run_dir}}/STOP`（或 Windows 侧 `{{run_dir}}\STOP`）存在，Worker 不得再写 marker；
  - 超过 `{{expires_at}}` 不得再写 marker；
  - 自动续步累计到 `{{max_steps}}` 后不得再写 marker。

> 若未来要求 DS-H 也做到“工具级硬停”，需再加一个薄适配器去读 `run.json/STOP/events.jsonl`；本版不扩代码，只如实标注口径。