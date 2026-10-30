# T-MA-01 · Collab Run（有界协作 Run 信封工具）

一个只管理**本地执行信封**的最小 CLI，不碰 PAOS 核心。把实验转成可重复使用的「一个 Worker + 一个 Request + 3 次续步 + 30 分钟」协作 Run。

## 边界（严格遵守）

- 不新增 PAOS API；不改 Project/Session 数据模型。
- 不做后台常驻调度器；不自动启动 Agent。
- 不做多 Worker 并发；不做无人值守。
- Runtime hook 仍由**目标 Agent 按生成材料自行配置**。
- PAOS 只保存业务事实；本工具只管理 `run.json / STOP / marker.json / events.jsonl / active-run 指针`。

## 目录结构（本包）

```text
collab-run/
  README.md
  collab_run.py
  codex_stop_adapter.ps1   # 稳定 Codex Stop-hook（生产默认：一次安装，Run 只 activate）
  templates/
    codex_stop_hook.ps1    # 临时 Codex 续步 hook（隔离实验用；hooks.json 由 collab_run.py 序列化生成）
    stable_setup.md        # 稳定适配器一次性安装说明
    dsh_idle_hook.md       # DS-H idle-hook 接入说明（WSL 路径）
    worker_prompt.md       # Worker 进入 Prompt 模板
```

一个 Run 实例落在任意 run 目录：

```text
<run-dir>/
  run.json
  STOP              # 创建时不存在；status/stop 可观察
  marker.json       # Worker 决定续步时原子写入；hook 校验身份后原子消费
  events.jsonl      # 追加审计（hook_seen / continue / marker_invalid / ...）
  codex/hooks.json  # materialize 生成（JSON 序列化，反斜杠已转义）
  codex/stop_hook.ps1
  dsh/README.md
  STABLE_SETUP.md
  WORKER_PROMPT.md
```

## run.json（不可变身份 + 有界参数）

```json
{
  "schema": "collab-run/v1",
  "run_id": "run-<uuid>",
  "project_id": "<PAOS Project id，从 session/request 推导或显式指定>",
  "session_id": "<PAOS Worker Session id>",
  "request_id": "<指向该 Worker 的 open Request id>",
  "max_steps": 3,
  "ttl_minutes": 30,
  "created_at": "<UTC RFC3339>",
  "expires_at": "<UTC RFC3339>"
}
```

## marker.json（Worker 写、hook 消费，一次即废）

```json
{
  "run_id": "run-<uuid>",
  "request_id": "<request_id>",
  "session_id": "<session_id>",
  "step_no": 1,
  "expires_at": "<run.expires_at>",
  "reason": "还有一个已确定的后续步骤：……"
}
```

身份必须与本 Run 的 `run_id/session_id/request_id` 一致；hook 只消费合法 marker，解析失败或身份不符会放行并记 `marker_invalid/marker_identity_mismatch`。

## CLI

```text
python collab_run.py create   <RUN_DIR> --session-id S --request-id R [--project-id P] [--max-steps 3] [--ttl-minutes 30]
python collab_run.py materialize <RUN_DIR> [--runtime codex|dsh|all]
python collab_run.py status   <RUN_DIR>
python collab_run.py stop     <RUN_DIR>
python collab_run.py activate <RUN_DIR> [--force]   # 稳定模式：写 active-run 指针
python collab_run.py deactivate                      # 稳定模式：撤销指针
python collab_run.py cleanup  <RUN_DIR> --yes
```

- `create`：拒绝已存在目录；`max_steps/ttl_minutes` 必须 >= 1；session/request 必须同项目（不再写死 3002）。
- `materialize`：生成 Worker 进入 Prompt、临时/稳定两种 Codex hook 材料、DS-H 说明；`hooks.json` 用 JSON 序列化生成（正确转义反斜杠）。**不写 PAOS**。
- `status`：run 参数、STOP/marker、过期（含 `expiry_parse_error`）、已续步步数、active 指针、`hook_seen`。
- `activate`：已有其它激活 Run 时拒绝，除非 `--force`。
- `cleanup`：若 active 指针指向本 Run，先撤销再删目录（需 `--yes`）。

## 一次真实协作的顺序（生产默认：稳定适配器）

1. 人预建 Work + Worker Session + 定向 Request（PAOS 各自现有能力）。
2. `create` 建 Run 信封。
3. `materialize` 生成 Worker Prompt 与 `STABLE_SETUP.md`（首次安装稳定 hook；之后 Run 不再改 hook 配置）。
4. `activate` 写 active-run 指针。
5. 人类对 Worker 说「进入」；Worker 按 `WORKER_PROMPT.md` 领取 Request，每步按剩余工作写 `marker.json`；稳定 hook 在 Stop 边界校验并续步（最多 `max_steps` 次）。
6. Run 结束（空 / done / STOP / 过期 / 达上限）→ `stop`（如需）→ `deactivate` → `cleanup --yes`；人在 PAOS Review。

隔离实验仍可用临时模式：`materialize --runtime codex` 生成 `codex/hooks.json` + `codex/stop_hook.ps1`，该 Run 独立使用，不改全局 hook。