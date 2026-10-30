# Personal Agent OS v0.1 仓库边界与迁移映射

## 1. 仓库身份

建议远程：

`xiangscream/personal-agent-os`

建议可见性：

`private`

建议本地：

`C:\Users\remo\Desktop\agent学习计划\personal-agent-os`

2026-07-31 经 GitHub 连接核验并发布 Planning Seed：该仓库为 private、未归档，`main` 已包含根 README、G0 设计、实施任务包、前向审查与建设队列。当前没有 Dashboard、Memory Pipeline、真实数据或运行代码。

## 2. 为什么 v0.1 保留旧目录名

当前 Dashboard、启动脚本和浏览器静态路径依赖两个目录互为兄弟：

```text
attention-dashboard-v1-static
attention-memory-pipeline-v0
```

第一次迁移同时重命名会迫使 Agent 修改：

- 前端 `DATA_BASE`；
- 前端 `SOURCE_BASE`；
- 本地服务根目录；
- 启动脚本；
- 测试数据路径；
- README 和排错入口。

这会把“建立仓库边界”和“重构路径”混为一个 Gate。因此 v0.1 原样保留，后续若确有价值，再用独立 ADR 和测试完成重命名。

## 3. 迁移映射

### Dashboard

来源：

`C:\Users\remo\Desktop\agent学习计划\.lab\prototypes\attention-dashboard-v1-static`

目标：

`C:\Users\remo\Desktop\agent学习计划\personal-agent-os\attention-dashboard-v1-static`

纳入：

- `index.html`
- `app.mjs`
- `model.mjs`
- `styles.css`
- `local_server.py`
- `start-dashboard.ps1`
- `start-dashboard-v1.ps1`
- `START-HERE.md`
- `README.md`
- `FRONTEND-DESIGN-v1.2.md`
- `tests/dashboard-v1.test.mjs`
- `tests/test_local_server.py`

排除：

- `__pycache__/`
- `tests/__pycache__/`
- 运行日志；
- 浏览器 `localStorage`；
- 临时端口与 PID 文件。

### Markdown 记忆管道

来源：

`C:\Users\remo\Desktop\agent学习计划\.lab\prototypes\attention-memory-pipeline-v0`

目标：

`C:\Users\remo\Desktop\agent学习计划\personal-agent-os\attention-memory-pipeline-v0`

纳入：

- `scan_vault.py`
- `dashboard_adapter.py`
- `schema/attention-state.schema.json`
- `synthetic-vault/`
- `tests/test_scan_vault.py`
- `tests/test_dashboard_adapter.py`
- `README.md`
- `DASHBOARD-CONTRACT.md`

默认排除：

- `build/attention-state.json`
- `build/dashboard-data.json`
- `build/source-manifest.json`
- `build/scan-report.md`
- `__pycache__/`
- `tests/__pycache__/`

理由：`build/` 是派生数据，应由 `scan_vault.py` 和 `dashboard_adapter.py` 重建。

`synthetic-vault/` 不是无条件递归复制。Dry Run 必须先展开逐文件清单并完成敏感信息检查；只有未命中真实业务、真实 Inbox、Key、内部 URL 或个人资料时才纳入。

### 学习文档

从：

`C:\Users\remo\Desktop\agent学习计划\08-Agent研究实验室`

选择性复制到：

`docs/learning/`

第一版只纳入：

- `10-系统组成与分层排错-v1.md`
- `11-Tips收件箱闭环与排错-v1.1.md`
- `12-从三条主线到交付闭环-v1.2.md`
- `13-前端开发设计书与模型分层执行协议-v1.md`

其他学习资料不批量迁入。

### agent-co

不复制任何源码和运行数据。

只在 ADR 中引用：

- [agent-co PR #1](https://github.com/xiangscream/agent-co/pull/1)
- evidence-first；
- raw source 与 derived index 分离；
- human-in-the-loop；
- incremental validation。

## 4. 根目录新增文件

### `README.md`

必须说明：

- 项目唯一目标；
- 当前版本与状态；
- 两个子系统；
- 一键启动；
- 一键验证；
- 数据边界；
- 当前非目标；
- `agent-co` 的关系；
- 下一 Gate。

### `.gitignore`

至少覆盖：

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/

**/build/
runtime/
logs/
*.log
*.pid

.env
.env.*
!.env.example

*.sqlite
*.sqlite3
*.db

00-Agent-Inbox/
private-data/
user-sandbox/

proxy/logs/
raw-logs/
```

### `SECURITY-BOUNDARIES.md`

必须说明：

- 不提交 Key；
- 不提交公司内部 URL；
- 不提交真实工作录音或会议纪要；
- 不提交完整 Vault；
- 不提交 raw Agent logs 或 SQLite；
- 合成数据必须明确标识；
- 真实数据实验必须位于被忽略目录。

### `RECOVERY.md`

必须说明：

- 如何从干净目录恢复；
- 如何重建 `build/`；
- 如何运行测试；
- 如何检查页面和健康接口；
- 如何恢复正式 Tips Inbox；
- 哪些目录绝不能通过脚本删除；
- 回退只恢复对应文件，不整体覆盖工作区。

### `VERSION_HISTORY.md`

初始版本：

```text
v0.1.0
- 建立 Personal Agent OS 独立仓库边界
- 原样导入 Attention Dashboard v1.2
- 原样导入 Markdown Memory Pipeline v0
- 32 项测试基线
- 不连接真实数据、模型或 agent-co runtime
```

### `docs/adr/ADR-0001-repository-boundary.md`

记录：

- 为什么不继续扩展 `agent-co`；
- 为什么新建 monorepo；
- 为什么 v0.1 保留目录名；
- 为什么先 lift-and-shift 再重构；
- 替代方案与否决理由。

### `docs/adr/ADR-0002-source-of-truth.md`

记录：

- raw source；
- derived index；
- candidate；
- human decision；
- skill artifact；
- 每一层的写入权和恢复方式。

### `docs/architecture/README.md` 与 `docs/runbooks/README.md`

用于解释两个目录的职责、当前内容边界和后续进入条件，避免用 `.gitkeep` 保存没有语义的空目录。

## 5. 统一脚本契约

### `scripts/verify.ps1`

按顺序：

1. 进入记忆管道；
2. 记录并检查 Python、Node 与 PowerShell 版本和必要前置条件；
3. 从 `synthetic-vault` 重建 `build/attention-state.json`；
4. 生成 `build/dashboard-data.json`；
5. 运行 Python 管道测试；
6. 检查 `app.mjs` 与 `model.mjs` 语法；
7. 运行 Dashboard Node 测试；
8. 运行本地服务 Python 测试；
9. 输出 17 + 10 + 5 的汇总；
10. 任一步失败立即非零退出。

### `scripts/start.ps1`

职责：

- 调用统一验证或至少重建数据；
- 启动只绑定 `127.0.0.1` 的本机服务；
- 明确打印页面、健康接口和 Tips API 地址；
- 记录固定参数、工作目录、端口占用检查与服务停止方式；
- 不后台静默启动多个重复服务；
- 不创建公网监听。

## 6. 首次 Git 边界

本任务只允许 `git init` 和只读状态/候选清单检查；禁止 `git add`、`git commit`、添加 remote、push 和 PR。

首次提交授权前：

- 输出将跟踪文件清单；
- 输出被忽略文件清单；
- 逐文件回核 Dry Run 的相对路径、大小与 SHA-256；源文件在 Phase A 后发生变化时停止；
- 搜索 Key、Token、密码、内部 URL、`.sqlite`、raw logs；
- 验证没有 `D:\Obsidian-Vault` 内容；
- 验证没有 `agent-co` runtime；
- 验证没有 Tips Inbox；
- 验证 `build/` 可由脚本重建；
- 运行完整测试。

远程仓库已经创建；添加 remote、首次 push 和 PR 仍属于第二授权阶段。

