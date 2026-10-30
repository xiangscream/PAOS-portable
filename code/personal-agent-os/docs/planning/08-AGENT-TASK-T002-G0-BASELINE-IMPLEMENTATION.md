# Agent 任务包｜T-002 可运行仓库基线

状态：Ready  
远程仓库：`xiangscream/personal-agent-os`  
分支：`agent/t-002-g0-runnable-baseline`

## 1. 唯一目标

把 Attention Dashboard v1.2 与 Markdown Memory Pipeline v0 迁入本仓库，修复 Tips 默认 Inbox 路径，完成验证并创建 Draft PR。

这是一项隔离分支内、Git 可回退的 L1 任务。快速预检、实施和 Draft PR 在同一轮完成；正常情况下不等待中间批准。

## 2. 开始前只读两份文件

1. `docs/context/PROJECT-CONTEXT-AND-DECISION-HISTORY.md`
2. 本任务包

如需理解旧决策，可再查 `07-G0-REPOSITORY-BASELINE-DESIGN-v0.2.md`，但它不是执行前置。

先用不超过 8 条复述目标、允许改动、验证和停止条件。复述准确后直接实施。

## 3. 工作区与来源

在 WSL 文件系统中的全新 clone 或隔离 worktree 工作。不要在含真实 `private-data/` 的 Windows 归档副本中开发。

只读来源：

```text
/mnt/c/Users/remo/Desktop/agent学习计划/.lab/prototypes/attention-dashboard-v1-static
/mnt/c/Users/remo/Desktop/agent学习计划/.lab/prototypes/attention-memory-pipeline-v0
```

永不读取：

```text
C:\Users\remo\Desktop\secrest
```

## 4. 同一轮执行

### A. 快速预检

只确认：

- 工作区是隔离 clone/worktree，分支正确；
- 两个来源可读；
- 排除 `build/`、`__pycache__/`、`.pyc` 后，来源为 12 个 Dashboard 文件和 20 个 Pipeline 文件；
- 来源中没有 `.env*`、数据库、日志、真实 Tips、`private-data/` 或明显公司/Secret 内容；
- 来源原型测试基线仍为 32 项。

结果正常就继续，不输出独立 Dry Run，不等待批准。文件哈希可用于源/目标自动比对，但不需要生成逐文件 Markdown 报告。

### B. 复制与最小修复

只复制预检中的 32 个文件，保持两个目录名不变。

允许修改的既有文件只有：

1. `attention-dashboard-v1-static/local_server.py`
2. `attention-dashboard-v1-static/tests/test_local_server.py`

Inbox 选择优先级固定为：

```text
--inbox
  > PERSONAL_AGENT_OS_INBOX
  > <repo>/private-data/inbox/tips
```

不得修改 UI、排序算法、数据 schema、扫描规则或产品功能。

### C. 最小工程说明

只添加让新目录能启动、验证和恢复所必需的内容。允许：

- `scripts/doctor.ps1`
- `scripts/start.ps1`
- `scripts/verify.ps1`
- `SECURITY-BOUNDARIES.md`
- `RECOVERY.md`
- `VERSION_HISTORY.md`
- 一篇启动与排错说明

不要为了“文档齐全”继续创建 ADR、架构册、流程图或新的规划文档。已有 README 能承载的内容直接改 README。

脚本不得自动安装软件、修改 PATH、杀进程、开放局域网、创建后台服务或删除用户文件。

### D. 验证

必须验证：

- Pipeline Python：17 项；
- Tips Server Python：5 项；
- Dashboard Node：10 项；
- 总计：32 项全部通过；
- `/api/health` 返回 `ok: true`；
- 页面入口 HTTP 200；
- 默认数据含三条主线；
- 默认 Inbox 为 `<repo>/private-data/inbox/tips`；
- `--inbox` 和 `PERSONAL_AGENT_OS_INBOX` 覆盖分别通过测试；
- Tips 重试保持幂等；
- 服务只绑定 `127.0.0.1:8766`；
- `private-data/`、`build/`、Secret 和真实资料不出现在 staged diff。

如果缺少 Python 或 Node，只报告明确缺失与可复现命令；不得自动改系统环境。

### E. 交付

验证通过后：

1. 对待提交差异做敏感扫描，只返回路径和风险类型，不回显疑似值；
2. 只暂存任务范围文件；
3. commit 并 push 当前分支；
4. 创建 Draft PR；
5. 不合并。

PR 只需写清：变更、两处既有代码差异、32 项测试、HTTP/Inbox 证据、敏感扫描、恢复方式和剩余问题。

## 5. 立即停止

- 文件数不是 12 + 20，或来源测试基线已变化；
- 发现真实资料、Secret、公司内部 URL 或凭据；
- 需要修改两个允许文件之外的既有产品逻辑；
- 需要移动、删除或覆盖来源；
- 需要安装软件、改权限、杀进程或开放网络；
- 测试只能靠跳过安全检查才能通过；
- 同一故障连续三轮仍无法形成最小复现；
- 准备直接合并 `main`。

## 6. 返回格式

```text
结论：
变更：
测试：
HTTP 与 Inbox：
敏感扫描：
恢复：
Draft PR：
停止条件或剩余问题：
```
