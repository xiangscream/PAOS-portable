# 01 仓库真实布局

读 PAOS 代码第一件要理清的事：**目录名会骗人**。

## 先记住一条

后端和前端**全在 `attention-dashboard-v1-static/` 里**。

这个目录名字听起来像"放静态页面的地方"，实际上它是整个 PAOS 服务的主体：`local_server.py`（1890 行 HTTP 层）、`project_store.py`（1557 行唯一写盘者）、`workflow_service.py`（facade）、11 个 projection 模块、以及所有前端 `.mjs` 和 `.html`。共 90 个文件。

顶层目录里**没有** `local_server.py`，也没有 `project_store.py`。如果你按 `docs/CODE-MAP.md` 的架构图去找，会一无所获。

## 目录分工

| 目录 | 实际职责 |
|---|---|
| `attention-dashboard-v1-static/` | PAOS 本体：HTTP 服务、workflow、store、投影、前端 |
| `scripts/` | CLI（`paos.py`，5072 行）与各类独立脚本；**服务端也依赖这里的模块** |
| `private-data/` | 项目 JSON、备份、日志（4.4 GB，被 gitignore，不进版本控制） |
| `docs/` | 文档。`code-notes/` 是本批注所在目录 |
| `runtime_adapters/` | Windows/WSL 桥接 |
| `attention-memory-pipeline-v0/` | v0 时代的原型数据源，只服务旧原型界面 |
| `tools/` | 最后提交 2026-09-11，使用情况未核实 |

## 一个容易踩的依赖方向

`attention-dashboard-v1-static/` **不是自包含的**。它会往 `scripts/` 取模块：

- `local_server.py:20-22` 在导入阶段就把 `scripts/` 插进 `sys.path`，用来拿 `paos_attention_service`、`paos_installation`；
- `workflow_service.py:89-97` 在 `team_contact` 方法内部动态 import `scripts/paos_contact`。

所以 `scripts/` 里不是只有 CLI。CLI 和服务端共用一部分逻辑（联系面就是一个例子，注释明确写了"复用 scripts/paos_contact 同一读面，无第二套解析"）。

## 前端有两套，别读错

- **真实界面**：`projects.html` + `projects.mjs`，走 `/api/*` 读真实项目数据。`scripts/start.ps1:8` 的默认入口就是 `projects.html`。
- **旧原型界面**：`index.html` + `app.mjs`，读 `attention-memory-pipeline-v0/build/dashboard-data.json` 这份**合成数据**（`app.mjs:12-14`）。

如果你改了后端逻辑却在旧原型界面上看效果，看到的是假数据。

## 两个服务端入口文件

- `local_server.py` — 核心实现，1890 行。
- `paos_server.py` — 56 行薄壳，`import local_server`，只做一件事：往响应头挂 `X-PAOS-Runtime-Fingerprint`（build identity）。

主启动路径走 `paos_server.py`（`scripts/start.ps1:148`）。之所以不把 identity 直接写进 `local_server.py`，`paos_server.py:1-8` 的 docstring 给了理由：不让 release 相关的关注点混进 workflow/store 实现。

另两条脚本 `start-dashboard.ps1` 和 `start-dashboard-v1.ps1` 起的是 `local_server.py`（少了 identity 头），而且启动前会先跑一遍 `attention-memory-pipeline-v0` 的扫描。这两个文件内容等价，只有中英文文案差别。

## 五份历史源码副本

`Source-v12-integrated-release`、`Source-v12-rooter-handoff`、`Source-v12-s031-cli-communication-install`、`Source-v12-s031-codex-cross-host-handoff`、`Source-v12-s031-model-inherit` 位于上级 `PAOS-Projects/3002-Personal-Agent-OS/` 目录，**各自带独立 `.git`**，是 v1.2 各阶段的快照。

当前唯一源由 `~/.paos/installation.json` 的 `source_root` 指明，指向 `Source/personal-agent-os`。拿不准"我该改哪份"时，读这个字段，不要靠目录名猜。
