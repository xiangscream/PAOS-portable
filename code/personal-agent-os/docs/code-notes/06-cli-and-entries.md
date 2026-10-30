# 06 CLI 与启动入口

## CLI 不直接读文件

`scripts/paos.py`（5072 行）是 Agent 用的命令行入口。开头 docstring：

> Agent-first PAOS localhost REST CLI. **Durable state is accessed only through HTTP.** The CLI intentionally exposes Agent/Runtime actions and supported Coordinator governance commands. Human-only governance remains on its approved Human surface.

也就是说 CLI 和服务端是**同一个后端、两个入口**：CLI 走 HTTP 打 8766（`DEFAULT_BASE_URL`，`paos.py:116`），网页也走 HTTP 打 8766。CLI 不会绕过 workflow 直接改 JSON。

这条避免了"两套读法不一致"的问题——也是为什么 `workflow_service.py:85-97` 要特意注释"复用 scripts/paos_contact 同一读面，无第二套解析"。

## 23 个子命令

```text
health  home  orient  status  inbox  attention  peers  team  agent  wake
mail  library  config  install  authority  relations  needs-me
project  work  session  coordinator  workstation
```

几个容易混的：

- `inbox` —— 读工位 Mail，**与** PAOS 正式 Request 分开。
- `agent` —— Agent 激活走持久通信，Runtime 留在 Wake binding 后面（不直接碰 Runtime）。
- `wake` —— Runtime 唤醒连接：bind / status / probe / trigger / recover / stop。
- `attention` —— V1.3 Home 的 TODO/NOTICE/source 服务，注释明确"never submits native turns inline"。
- `install` —— 查看或配置**本机** PAOS 安装定位器。

## 两个使用上的坑

**`orient` 和 `status` 必须带 project_id 和 agent_id。** 直接跑 `paos orient` 会报缺少位置参数。正确写法：

```text
paos orient 3002 3002-s035
```

**文本值有四种写法。** `--help` 里写了：字面文本、`@FILE`（读文件，`@` 后要跟绝对路径）、`-`（UTF-8 stdin）、`@@...`（字面量以 `@` 开头时的转义）。

## 启动与停止

```text
启动PAOS.cmd  →  scripts\start.ps1  →  attention-dashboard-v1-static\paos_server.py  (端口 8766)
停止PAOS.cmd  →  scripts\stop.ps1
```

`start.ps1` 做了几件事：检测 Python（可用 `PAOS_PYTHON` 环境变量指定）、调 `release_identity.py` 拿本机 build identity 来判断"跑着的服务和当前 checkout 是不是同一份代码"、未起则后台起服务、默认开 `projects.html`（`start.ps1:8` 的 `-Entry` 参数可改）。

开机自启用 `scripts/autostart/paos-autostart.vbs`，配 `-NoBrowser` 只起服务不开浏览器。

另有两条**不走主入口**的脚本 `attention-dashboard-v1-static/start-dashboard.ps1` 和 `start-dashboard-v1.ps1`，起的是 `local_server.py`，还会先跑一遍 `attention-memory-pipeline-v0` 扫描。两个文件内容等价，只有中英文文案差别。用主入口就行。

## 排障与自检

- `scripts/doctor.ps1` —— `README.md:90` 建议在"启动或版本身份不清楚时"从你要用的那份 checkout 跑它。
- `scripts/verify.py` —— 七道闸：Architecture、Python tests、Derived data、Node UTC、Node Asia/Shanghai、Python compileall、JS `node --check`。

`AGENTS.md:41` 对跑测试的尺度有明确要求：按改动范围选。只读工作和纯文档改动不必先跑全套；核心状态转换、共享合同、集成和发布才需要全套。同一代码版本和相同环境已有可信记录时，审阅那份证据并确认关键差异即可，不必重跑。

注意 `verify.py` 的 Derived data 那道闸会**生成派生数据**，跑之前确认你能接受工作区出现这些文件。

## 安装位置

CLI 装在 `~/.paos/bin/paos.cmd`，不是从仓库里跑。装的是哪份源码由 `~/.paos/installation.json` 的 `source_root` 决定。

库根在另一处：`~/.paos/library-roots.json` 的 `workflow_root` / `skill_root`，指向 `PAOS-Libraries/` 下的共享 Workflow 与 Skill 库。PAOS 源码、库、Rooter（`PAOS-Rooter/rooter-001`）是三个分开的目录。
