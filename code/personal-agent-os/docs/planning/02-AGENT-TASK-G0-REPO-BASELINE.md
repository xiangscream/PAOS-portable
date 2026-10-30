# Agent 任务包｜G0 Personal Agent OS 仓库基线

> 状态：已被 T-002 取代，请勿继续执行。
>
> 原因：本任务假设原型可以零代码迁入，但路径审查发现 Tips 默认 Inbox 会随目录层级漂移。当前入口为 [G0 v0.2 设计](07-G0-REPOSITORY-BASELINE-DESIGN-v0.2.md) 与 [T-002 任务包](08-AGENT-TASK-T002-G0-BASELINE-IMPLEMENTATION.md)。本文仅保留为历史计划证据。

## 给执行 Agent 的指令

你正在执行 Personal Agent OS 的 Gate 0。当前任务不是开发新功能，而是建立独立、可重建、可恢复的新仓库基线。

## 1. 唯一目标

在已经检出规划种子的 `xiangscream/personal-agent-os` 工作区中，把两个现有原型以**复制、零代码改动、行为不变**的方式迁入。推荐本机工作区：

`C:\Users\remo\Desktop\agent学习计划\personal-agent-os`

并建立根目录启动、验证、安全、版本与恢复文档。

## 2. 必读设计

先完整阅读：

1. 仓库内的 `docs/planning/00-MASTER-BUILD-PLAN-v0.1.md`；
2. 仓库内的 `docs/planning/01-REPO-BOUNDARY-AND-MIGRATION-MAP.md`；
3. 仓库内的 `docs/reviews/03-G0-FORWARD-TEST-2026-07-31.md`；
4. 本机 Dashboard 来源目录中的 `FRONTEND-DESIGN-v1.2.md`。

先用不超过 12 条复述目标、非目标、允许来源、排除内容、测试和停止条件。不能准确复述时不要开始复制。

## 3. 来源与目标

只读来源：

```text
C:\Users\remo\Desktop\agent学习计划\.lab\prototypes\attention-dashboard-v1-static
C:\Users\remo\Desktop\agent学习计划\.lab\prototypes\attention-memory-pipeline-v0
C:\Users\remo\Desktop\agent学习计划\08-Agent研究实验室
```

目标工作区：

```text
C:\Users\remo\Desktop\agent学习计划\personal-agent-os
```

禁止把来源目录移动、重命名、清空或覆盖。

远程仓库已经包含规划种子。执行 Agent 可以位于其他本地 worktree，但必须能只读访问上述三处来源；无法访问时立即停止，不得用猜测内容或远程旧副本代替。

### WSL 执行说明（仅适用于 Phase A）

如果实施 Agent 在 WSL 中运行，Windows 来源目录等价于：

```text
C:\Users\remo\Desktop\agent学习计划\.lab\prototypes\attention-dashboard-v1-static
→ /mnt/c/Users/remo/Desktop/agent学习计划/.lab/prototypes/attention-dashboard-v1-static

C:\Users\remo\Desktop\agent学习计划\.lab\prototypes\attention-memory-pipeline-v0
→ /mnt/c/Users/remo/Desktop/agent学习计划/.lab/prototypes/attention-memory-pipeline-v0

C:\Users\remo\Desktop\agent学习计划\08-Agent研究实验室
→ /mnt/c/Users/remo/Desktop/agent学习计划/08-Agent研究实验室
```

WSL Agent 的第一项只读检查必须验证三个挂载目录均可读。Phase A 可以在 WSL 工作区中完成；Phase B 的 PowerShell 启动脚本、本机端口和浏览器验证仍需在 Windows 上单独确认，不能假定 WSL 运行结果等价。

## 4. 必须先执行的 Phase A：Dry Run

本次会影响超过 20 个文件，因此先只做 dry run。

Dry run 必须输出：

- 计划创建的目录树；
- 计划复制的每个来源和目标；
- 文件总数；
- 每个拟纳入文件的目标相对路径、大小、修改时间和 SHA-256；
- 计划新增的根目录文档与脚本；
- 明确排除的文件；
- 发现的缓存、生成物、数据库、日志和疑似敏感文件；
- 预计需要修改的现有代码文件数量，必须为 0；
- 预计 Git 跟踪文件清单；
- 回退方式。

Phase A 不得：

- 创建或重新初始化目标仓库；
- 复制文件；
- 初始化 Git；
- 修改来源；
- 创建 GitHub 仓库；
- commit、push 或开 PR。

输出 Dry Run 后停止，等待用户明确批准 Phase B。

## 5. 用户批准后的 Phase B

### 允许动作

- 在已检出的规划仓库工作区中新增目标目录；
- 按迁移映射复制文件；
- 创建根目录文档、ADR 和脚本；
- 只读检查现有 Git 状态和候选文件清单；
- 运行构建、测试和本机服务验证；
- 创建本地首次提交前候选变更。

“原样迁入”指迁移映射选中的原型文件内容与目录名保持不变，不是递归复制整个来源目录。Phase B 不得修改任何已复制的原型代码；若启动或测试不兼容，停止并报告。

### 禁止动作

- 不使用剪切；
- 不删除任何来源或目标文件；
- 不复制 `build/`、缓存、日志、数据库和真实 Inbox；
- 不修改真实 Obsidian Vault；
- 不读取或复制 `D:\Obsidian-Vault-Backup`；
- 不复制 `agent-co` 代码或 raw logs；
- 不连接模型；
- 不导入 Key；
- 不接真实业务资料；
- 不重命名两个原型目录；
- 不改变 Dashboard 功能或视觉；
- 不添加 GitHub remote；
- 不执行 `git add` 或 `git commit`；
- 不 push。

## 6. 目标目录

```text
personal-agent-os/
├─ attention-dashboard-v1-static/
├─ attention-memory-pipeline-v0/
├─ docs/
│  ├─ architecture/
│  ├─ adr/
│  ├─ runbooks/
│  └─ learning/
├─ scripts/
│  ├─ start.ps1
│  └─ verify.ps1
├─ .gitignore
├─ README.md
├─ SECURITY-BOUNDARIES.md
├─ RECOVERY.md
└─ VERSION_HISTORY.md
```

## 7. 需要创建的文档

- 根 README；
- `SECURITY-BOUNDARIES.md`；
- `RECOVERY.md`；
- `VERSION_HISTORY.md`；
- `docs/adr/ADR-0001-repository-boundary.md`；
- `docs/adr/ADR-0002-source-of-truth.md`；
- `docs/architecture/README.md`；
- `docs/runbooks/README.md`；
- 复制指定的四篇学习文档；
- 保留 Dashboard 的 `FRONTEND-DESIGN-v1.2.md`。

文档必须解释“为什么”，不能只列命令。

## 8. 验证

在目标目录中重新生成数据后运行：

```text
管道测试：17 项
Dashboard 测试：10 项
本地服务测试：5 项
总计：32 项
```

还要验证：

- 记录 Python、Node、PowerShell 版本、固定参数、工作目录与端口要求；
- 页面返回 HTTP 200；
- `/api/health` 返回 `ok: true`；
- LRC101 三个执行闭环字段可从 HTTP 数据读取；
- 来源 URL 安全测试仍通过；
- Tips Inbox 不在 Git 跟踪范围；
- 删除目标 `build/` 后能够重建。

## 9. 敏感信息检查

复制 `synthetic-vault/` 前，以及首次提交授权前，搜索并报告但不要回显真实值：

- API Key、Token、Bearer；
- `.env`；
- 密码和连接串；
- 内部模型 URL；
- `*.sqlite`、`*.db`；
- raw logs；
- 工作会议录音与纪要；
- 真实 Obsidian 路径内容；
- Tips Inbox 内容。

如果发现疑似敏感内容，停止并只报告文件路径和风险类型。

## 10. 停止条件

出现任一情况立即停止：

- 工作区在执行前已经包含 `attention-dashboard-v1-static/`、`attention-memory-pipeline-v0/` 或计划外产品代码；
- 工作区除 `.git/`、根 README 与 `docs/planning/`、`docs/reviews/` 外还存在无法解释的文件；
- dry run 与实际文件数不一致；
- Phase B 的来源文件大小或 SHA-256 与 Dry Run 不一致；
- 需要修改来源文件；
- 需要修改任何已复制的原型代码；
- 需要删除或移动文件；
- 需要重命名两个原型目录；
- 现有启动依赖无法在保留结构下工作；
- 测试失败需要改变产品逻辑；
- 检测到真实 Key、数据库或 raw logs；
- 需要执行 `git add`、`git commit`、添加 remote 或 push；
- 同一问题连续三轮失败。

## 11. 最终交付格式

Phase A 返回：

```text
Dry Run 结论
计划文件数
纳入内容
排除内容
预计修改
风险
回退
是否可以进入 Phase B
```

Phase B 返回：

```text
完成的目录与文件
与来源的差异
测试结果
HTTP 验证
敏感信息检查
Git 状态
未解决问题
是否触发停止条件
下一步需要用户批准的外部动作
```

## 12. 外部动作

private `xiangscream/personal-agent-os` 已于 2026-07-31 由用户创建，并先接收规划种子。本任务的 Phase A 与 Phase B 都不得改变远程仓库。

只有用户另行明确批准后，另开任务处理：

- 添加 remote；
- commit / push；
- 创建初始 PR 或发布标签。

不要把这些动作包含在 G0 本地基线任务中。

