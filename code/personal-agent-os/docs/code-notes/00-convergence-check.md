# PAOS 收敛检查

检查对象：`Source/personal-agent-os`，HEAD `49cc445`，工作区干净。
方式：只读 + 批注。没有改动任何功能代码、配置和状态文件。

## 结论

分三块看，结论不一样：

- **代码主干：收敛。** 分层被代码强制，写入只有一条路，边界有明确防线。
- **文档：不收敛。** 实现地图滞后于代码，版本口径有两套说法，启动脚本有三个。
- **仓库外壳：不收敛。** 遗留分支、历史源码副本、原型残留都还在原地。

一句话：PAOS 的**内部**是收敛的，**外部**（别人理解它的路径）没跟上。

---

## 一、代码主干：收敛

### 分层是硬的，不是口号

`AttentionDashboardHandler` 只做 HTTP：解析请求、查路由表、映射错误、伺服静态文件。它不碰磁盘，不写业务规则。

写入唯一入口是 `ProjectStore.mutate_v2`（`attention-dashboard-v1-static/project_store.py:701`）。它的 docstring 把锁内顺序写死了（同文件 719-733 行）：幂等检查 → 读取校验 → touched-path 冲突检查 → execution-claim 校验 → 深拷贝 apply → 校验 → event+receipt → 备份 → pre_commit_hook → 原子替换。任一步失败都不写盘。

`WorkflowService` 是薄 facade，自身几乎没有逻辑，行为都在 mixin 里（`attention-dashboard-v1-static/workflow_service.py:36-48`）。

### 两处值得学的设计

**静态目录白名单是唯一防线。** `local_server.py:85-91` 的注释写得很直白：白名单是唯一防线，以后新增静态目录要显式加进来，而不是从黑名单里减。这条注释本身就在防"以后有人图省事改成黑名单"。

**路由用 fullmatch，所以顺序无关。** `local_server.py:120-124` 解释了为什么：正则整串匹配且 `[^/]+` 不跨斜杠，各条互不重叠。注释还预判了退化路径——改成 `re.match` 前缀匹配就会引入顺序依赖。

### 服务端的依赖不只在自己目录里

`local_server.py:20-22` 把 `scripts/` 插进 `sys.path`，因为 `paos_attention_service`、`paos_installation` 这些模块在 `scripts/` 下。`workflow_service.py:89-97` 也在方法内部动态 import `scripts/paos_contact`。

服务端和 CLI 共用 `scripts/` 下的模块。这一点 `CODE-MAP` 没写，读代码时容易以为 `attention-dashboard-v1-static/` 是自包含的。

---

## 二、文档：不收敛

### 1. 目录名和实质完全不符

`attention-dashboard-v1-static/` 这个名字像"静态页面目录"，实际上**整个后端都在里面**：`local_server.py`（1890 行）、`project_store.py`（1557 行）、`context_compiler.py`、`workflow_service.py` 以及 11 个 projection 模块，共 90 个文件。前端也在这里。

而 `docs/CODE-MAP.md:10-31` 的架构图按"顶层 `local_server.py` → `workflow_service.py` → `project_store.py`"描述。顶层根本没有这些文件——顶层只有 `scripts/`、`tools/`、`runtime_adapters/`、`docs/`、`private-data/` 和两个历史目录。

后果：第一次读代码的人按 CODE-MAP 找模块，会全找不到。

### 2. CODE-MAP 覆盖面滞后

| CODE-MAP 写的 | 实际 |
|---|---|
| 4 个 workflow mixin + `workflow_support.py`（`CODE-MAP.md:14`） | `WorkflowService` 组合 11 个 mixin（`workflow_service.py:36-48`）；`workflow_support.py` 是共享 helper 库不是 mixin（该文件第 1 行自称 "Shared workflow helpers"） |
| 5 个 projection 模块 | 实际 11 个 `*projection*.py`，多出 `mailbox_projection`、`portfolio_projection`、`reference_projection`、`stewardship_projection`、`artifact_revision_projection`、`working_memory_projection` |

### 3. 版本口径有两套说法

- `README.md:11`：V1.3 已部署并接受，`V1.2-BASELINE.md` 是历史证据。
- `docs/START-HERE.md:5`：已安装 V1.2 的长期工作入口、验收结果与已知缺陷见 V1.2 基线。
- `docs/SUPPORT-MATRIX.md:3`：当前安装已验证的环境……统一见 V1.2 基线。

`docs/V1.2-BASELINE.md:3` 自己写明了"本页不是实时安装版本表"——它没说错，是引用它的两个页面没跟上。按 README 走的人得到 V1.3，按 START-HERE 走的人被导向 V1.2。

### 4. 同一件事有三份启动脚本、两个入口

- 主入口 `scripts/start.ps1:148` 起 `attention-dashboard-v1-static/paos_server.py`。这是一个 56 行的薄入口，只负责往响应头加 build identity，核心实现仍在 `local_server.py`（`paos_server.py:1-8` 的 docstring 说明了这个分工）。
- `attention-dashboard-v1-static/start-dashboard.ps1` 与 `start-dashboard-v1.ps1` 起的是 `local_server.py`，并且启动前先跑 `attention-memory-pipeline-v0` 的扫描。两个文件内容等价，只有中英文文案不同。

三条脚本，两个不同的服务端入口文件。

---

## 三、仓库外壳：不收敛

### 分支与工作树

28 个未合并分支；35 个 worktree，其中 17 个是 prunable（多为 WSL 侧 `/tmp/opencode/*` 残留）。

仍有人在用的（有活 worktree 且近期有提交）：`feat/s034-workbuddy-wake-20261002`、`fix/r076-opencode-consumer-breakpoints`、`feat/t091-ports-slice`、`docs/v13-business-accepted-20261006`（在 `~/.paos/recovery/` 下的恢复点，应保留）。

其余集中在 2026-09-27 至 10-03 的 v1.2 收尾期，属于历史分支。

### 五份独立旧版本源码仓库

`Source-v12-integrated-release`、`Source-v12-rooter-handoff`、`Source-v12-s031-cli-communication-install`、`Source-v12-s031-codex-cross-host-handoff`、`Source-v12-s031-model-inherit`——五个目录**各自带独立的 `.git`**，是 v1.2 各阶段的源码快照。

当前唯一源是 `Source/personal-agent-os`，由 `~/.paos/installation.json` 的 `source_root` 指明。这五份不参与运行，但占据目录列表，且路径都带 `Source` 前缀。

### 原型残留仍连着主链路

`attention-memory-pipeline-v0` 最后实质改动是 2026-09-11（只改了换行策略），但它没有死：

- `attention-dashboard-v1-static/app.mjs:12-14` 读它的 `build/` 和 `synthetic-vault/`；
- `local_server.py:89-90` 把这两个目录放进静态白名单；
- 多个测试依赖它（`test_local_server.py:747-748`、`test_s6_release_check.py:29`）。

它服务的是**旧原型面** `index.html` + `app.mjs`（读合成数据）。真实主界面是 `projects.html` + `projects.mjs`，`scripts/start.ps1:8` 的默认 `Entry` 就是 `projects.html`。

两套界面共存，旧的那套还能被两条脚本启动。

### 一次性转换脚本仍在仓库

`scripts/paos_v12_convert.py`、`scripts/paos_v13_conversion_service.py`（对应 `paos_v13_convert.py`）、`scripts/ensure_build_data.py` 都还在，并被测试引用（`test_v12_converter.py:15`、`test_v13_conversion_service.py:36`）。

其中 `scripts/render_authority_matrix.py` 是**活的**——`authority_manifest.py:609-610` 和 `docs/AUTHORITY-MATRIX.md:72-73` 都指向它，用来生成/校验权限表。它不属于"可清理的残留"。

### 状态数据不在版本控制内

`private-data/` 4.4 GB，被 `.gitignore` 排除。项目 JSON、备份、日志都在这里。备份积累是它体积的主因。

---

## 未验证项

以下没有本次证据，不要当作结论：

- **当前 HEAD 是否全绿**：本次没有跑 `verify.py`。它会生成派生数据，与"只读"冲突。
- `docs/V1.3-RELEASE-FACTS.md` 里的 "87 passed and 7 subtests" 是 `8f06f9b` 当时的快照，不代表 `49cc445`。
- `tools/`（最后提交 2026-09-11）是否仍被使用，未逐项核实。

---

## 待你拍板（我没有动）

按影响排序：

1. **目录名改不改。** `attention-dashboard-v1-static` 改成能反映"后端 + 前端"的名字，或在 `CODE-MAP.md` 开头加一句指明后端落点。前者动路径，牵扯启动脚本、白名单和一堆测试；后者只改一行。
2. **启动脚本收不收敛。** 三份合成一份，统一到 `paos_server.py` 入口。
3. **版本口径对齐。** START-HERE、SUPPORT-MATRIX 指向 V1.3，或明确 V1.2 基线只作历史归档入口。
4. **清不清理。** 17 个 prunable worktree、5 份 `Source-v12-*` 副本、旧原型面（index.html + app.mjs + attention-memory-pipeline-v0）。清理前需要确认旧原型面确实不再使用——它目前仍被测试和白名单引用。
