# Personal Agent OS｜WSL 实施 Agent 说明

状态：适用于 G0 Phase A  
更新时间：2026-07-31

## 已就绪环境

- WSL：`gh 2.97.0` 已通过官方 apt 源安装；
- GitHub：已登录 `xiangscream`，Token 有 `repo` 与 `workflow` 范围；
- Git HTTPS：凭据助手已经委托给 `gh auth git-credential`；
- Windows：另有一个当前用户范围的 `gh`，但实施协作以 WSL 为主。

## 工作区与来源

建议在 WSL Linux 文件系统内检出规划仓库，例如：

```bash
gh repo clone xiangscream/personal-agent-os ~/workspace/personal-agent-os
```

原型来源保留在 Windows 磁盘，通过 `/mnt/c` 只读访问。G0 Phase A 需要先检查：

```bash
test -r /mnt/c/Users/remo/Desktop/agent学习计划/.lab/prototypes/attention-dashboard-v1-static
test -r /mnt/c/Users/remo/Desktop/agent学习计划/.lab/prototypes/attention-memory-pipeline-v0
test -r /mnt/c/Users/remo/Desktop/agent学习计划/08-Agent研究实验室
```

任一失败即停止并报告，不得用远程旧副本代替。

## 当前边界

Phase A 只读取 GitHub 规划文档与 `/mnt/c` 中指定来源，输出 Dry Run 后停止。

不得：

- 在 Windows 来源目录中写入、移动、删除或重命名；
- 创建产品目录、复制产品文件、`git add`、commit、push 或 PR；
- 读取真实 Vault、备份 Vault、Key、公司内网配置、raw logs 或真实 Inbox；
- 因为 WSL 中能运行某个命令，就认定 Windows PowerShell 脚本或本机浏览器验证也已通过。

## Phase B 的环境判定

Phase B 尚未解锁。Dry Run 必须记录哪些验证可在 WSL 执行，哪些依赖 Windows PowerShell、浏览器或 `127.0.0.1` 服务。之后由用户决定：

1. 在 Windows 工作区实施并以 WSL 仅做 Git 协作；或
2. 用 WSL 实施跨平台部分，并对 Windows 专属验证另设子 Gate。

在这个决定前，不修改脚本来“兼容 WSL”。

