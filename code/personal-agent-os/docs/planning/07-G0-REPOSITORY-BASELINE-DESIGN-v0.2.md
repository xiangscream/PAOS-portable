# Personal Agent OS｜G0 仓库可运行基线设计书 v0.2

状态：设计冻结，等待实施  
更新时间：2026-07-31  
适用仓库：`xiangscream/personal-agent-os`

## 1. 本阶段只解决什么

把当前已经验证的两个隔离原型迁入独立仓库，并形成一个可启动、可测试、可恢复的 Personal Agent OS v0.1：

```text
合成 Markdown
  → 只读扫描与来源哈希
  → attention-state/v0
  → Dashboard 数据适配
  → attention-dashboard-data/v0
  → 本机 HTTP 服务
  → 当前三条主线 / Tips / 候选审核 / 来源检查
```

G0 不增加新的产品能力。它解决的是“当前原型能否成为一个可靠工程基线”，而不是“系统最终能做多少事”。

## 2. 为什么现在先做仓库基线

当前功能已经足以验证核心产品判断：

- 首页默认显示三条活跃主线；
- 每条主线具备“当前唯一问题—阶段交付物—完成定义”；
- 紧急任务完成后，长期项目可以补位；
- Tips 可以显式提交到 Agent 可读 Markdown；
- 夜间整理只形成候选，不自动升级为事实；
- 所有可视任务可以返回来源和哈希；
- 数据请求、来源请求和 Tips 写入失败都有可见故障层。

继续扩展真实 Vault、模型或多 Agent，只会让“原型是否能在新目录恢复”更难判断。因此 G0 的产品价值不是增加功能，而是冻结一条可信的最小链路。

## 3. 当前证据

2026-07-31 在来源原型上验证：

| 验证项 | 结果 |
|---|---:|
| Markdown 管道测试 | 17/17 通过 |
| 本地 Tips 服务测试 | 5/5 通过 |
| Dashboard JavaScript 测试 | 10/10 通过 |
| 合计 | 32/32 通过 |
| 当前服务端口 | 8766 |
| 当前运行服务 | 未启动 |

拟迁入的有效来源文件：

| 来源 | 文件数 | 排除 |
|---|---:|---|
| `attention-dashboard-v1-static` | 12 | `__pycache__`、`.pyc` |
| `attention-memory-pipeline-v0` | 20 | `build/`、`__pycache__`、`.pyc` |
| 合计 | 32 | 所有生成物与缓存 |

这 32 个是“来源文件”，不是“32 项测试”；两者数量恰好相同，实施时不得混淆。

## 4. 发现的关键路径缺陷

原型中的 `local_server.py` 通过目录层级推算工作区：

```text
原位置：
agent学习计划/.lab/prototypes/attention-dashboard-v1-static
```

迁到仓库根目录后：

```text
agent学习计划/personal-agent-os/attention-dashboard-v1-static
```

相同的 `parents[2]` 会指向不同目录，导致默认 Tips Inbox 漂移。原 G0 计划中的“迁入代码零修改”因此不再成立。

### 冻结修复

只允许修改：

1. `attention-dashboard-v1-static/local_server.py`
2. `attention-dashboard-v1-static/tests/test_local_server.py`

新的路径规则：

```text
显式 --inbox 参数
  > PERSONAL_AGENT_OS_INBOX 环境变量
  > 仓库内 private-data/inbox/tips
```

默认路径必须位于仓库内被 Git 忽略的 `private-data/`。G0 不迁移旧 Tips；真实 Inbox 接入属于 G1。

禁止根据任意父目录层数猜测工作区，也禁止把真实绝对路径写进 Git。

## 5. 仓库结构

```text
personal-agent-os/
├─ attention-dashboard-v1-static/
├─ attention-memory-pipeline-v0/
├─ docs/
│  ├─ architecture/
│  ├─ adr/
│  ├─ planning/
│  ├─ reviews/
│  └─ runbooks/
├─ scripts/
│  ├─ doctor.ps1
│  ├─ start.ps1
│  └─ verify.ps1
├─ private-data/                 # 本机存在，Git 永久忽略
├─ .gitignore
├─ README.md
├─ SECURITY-BOUNDARIES.md
├─ RECOVERY.md
└─ VERSION_HISTORY.md
```

v0.1 保留两个原型目录名，不引入 React、npm 包、Docker、数据库或 monorepo 工具。

## 6. 前端设计边界

前端实现继续以原型内的 `FRONTEND-DESIGN-v1.2.md` 为冻结设计：

- 不重做视觉；
- 不改变三条主线排序算法；
- 不在前端猜测执行闭环字段；
- 不允许页面直接改写来源 Markdown；
- 不增加聊天室和多 Agent 调度；
- 不把 Dashboard 变成新的事实源。

G0 只允许修复因仓库迁移直接产生的路径、启动与诊断问题。

## 7. 运行时设计

### 启动依赖

- Python 3.11 或更高：运行扫描器、本机服务和 Python 测试；
- Node.js 20 或更高：只用于 JavaScript 测试，页面运行本身不依赖 npm；
- PowerShell 7 或 Windows PowerShell 5.1：Windows 一键入口。

根脚本不得假设 `python` 和 `node` 一定在 PATH。探测顺序：

```text
PAOS_PYTHON / PAOS_NODE 显式路径
  → py / python / python3 或 node
  → 清晰报错并停止
```

脚本不得自动安装软件、修改系统 PATH 或注册后台服务。

### 固定端口

- 默认绑定：`127.0.0.1`
- 默认端口：`8766`
- 不绑定 `0.0.0.0`
- 端口占用时显示占用错误，不自动杀进程或换端口

## 8. 数据所有权

| 数据 | 权威来源 | G0 是否进入 Git | 是否可重建 |
|---|---|---:|---:|
| 合成 Markdown | 仓库 `synthetic-vault/` | 是 | 是 |
| 扫描状态与 Dashboard JSON | `build/` | 否 | 是 |
| 浏览器排序、完成和草稿 | 浏览器 `localStorage` | 否 | 可重置 |
| 显式提交的 Tips | `private-data/inbox/tips` | 否 | 否 |
| Key、Token、密码 | `C:\Users\remo\Desktop\secrest` | 永不 | 否 |
| 真实 Vault 与历史资料 | 本机 `private-data/` 或外部事实源 | 否 | 取决于来源 |

G0 的启动、测试和截图必须使用合成数据。不得读取 `secrest` 或真实 Vault。

## 9. 实施方式

执行 Agent 使用 WSL 中的全新 clone 或 worktree，不在包含真实 `private-data/` 的 Windows 归档副本内开发。

```text
Phase A：只读 Dry Run
  → 精确列出 32 个来源文件及哈希
  → 用户批准

Phase B：独立分支实施
  → 白名单复制
  → 仅修复冻结的 Inbox 配置边界
  → 新增根脚本与恢复文档
  → 32 项测试 + HTTP 验证

Phase C：远程交付
  → 敏感扫描
  → Draft PR
  → 不合并
```

## 10. 完成定义

- [ ] Dry Run 与实际纳入文件逐项一致；
- [ ] 两个来源原型未被移动、删除或修改；
- [ ] 只有两处既有源文件允许发生功能性修改；
- [ ] 32 项测试全部通过；
- [ ] 删除 `build/` 后可重新生成；
- [ ] `/api/health` 返回 `ok: true`；
- [ ] 页面入口返回 HTTP 200；
- [ ] 默认 Inbox 位于仓库 `private-data/inbox/tips`；
- [ ] `--inbox` 与 `PERSONAL_AGENT_OS_INBOX` 可以覆盖默认路径；
- [ ] `private-data/`、`build/`、日志、缓存、数据库和 Secret 未进入 Git；
- [ ] 新 Agent 能按 README 在新 clone 中完成诊断、验证和启动；
- [ ] 创建 Draft PR，用户决定是否合并；
- [ ] Obsidian 中有本阶段 Run Card 和恢复点。

## 11. 停止条件

出现以下任一情况立即停止：

- 需要修改除 `local_server.py` 与对应测试外的既有产品逻辑；
- 来源文件数或哈希在 Dry Run 后变化；
- 需要移动、删除或覆盖来源；
- 真实资料、Key、Token、内部 URL 或旧 Tips 出现在 Git 候选清单；
- 需要安装系统软件、修改 PATH 或开放局域网端口；
- 任何测试需要被跳过才能通过；
- 同一故障连续处理三轮仍未定位；
- `private-data/` 出现在 `git status`；
- 实施 Agent准备直接合并到 `main`。

## 12. 下一 Gate

只有 G0 Draft PR 经用户审查、合并并形成 v0.1 快照后，才进入 G1：

> 从本机 Private Data Root 中由用户手选一条低敏真实任务切片，以只读、可撤回、可追溯的方式进入 Dashboard。

