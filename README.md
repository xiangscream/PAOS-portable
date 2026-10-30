# PAOS Portable

**以项目事实为核心的轻量硬基座，配合可复用方法库和可替换的 Agent 运行环境。**

这个仓库发布的是**代码与共享方法资产**，不是某台电脑的已运行安装。克隆不会带来原机的项目、工位、登记数据、登录状态或已启动的接收器。

## 仓库里有什么

| 路径 | 内容 | 是否随 Git 发布 |
|---|---|---|
| `code/personal-agent-os/` | CLI、服务模块、Runtime 适配代码及保留的测试 | 是；常用工位、输入与 Library 入口已改为文件直连 |
| `libraries/` | Workflow、Skill、参考范例、Tool Catalog | 是；Catalog 是索引，不是原文替代品 |
| `config/*.example.json` | 安装定位模板 | 是；占位模板不能直接作为有效安装使用 |
| `config/local/` | 本机生成的安装描述与 Library 定位 | 否；换电脑重新生成 |
| `data/`、Rooter 工位、项目库 | 私有安装事实与业务资料 | 否；按需要单独迁移 |

首次接续采用**一个安装级 Rooter + 每个迁入项目一个现任 Coordinator**。其他工位不默认恢复运行，但不删除原工位与业务历史。具体边界只有一份：[架构与资产边界](ARCHITECTURE.md)。

## 从新克隆开始

在仓库根目录，使用 Python 3.10 或更高版本：

```text
python portable.py plan
python portable.py init
python portable.py doctor
```

`plan` 只显示按当前仓库位置展开的两个配置；`init` 生成 `config/local/` 中的配置对，并创建空的数据根与 Library 元数据目录。它不覆盖已有配置，不导入项目，不创建工位，不修改 Runtime、不启动服务。遇到已有安装、损坏配置或旧路径，明确报错，不猜测修复。

`doctor` 是**只读定位检查**：即使 `configuration_ok: true`，也不代表 CLI、项目接续或唤醒已经通过测试。输出分别保留 `cli_verified`、`business_verified`、`runtime_verified` 为 `false`。

选用本机生成的配置后，再核查 CLI。以下入口已用完整源码、隔离项目与真实文件调用验证；不是生产工位采用记录：

```powershell
$env:PAOS_INSTALLATION_FILE = (Resolve-Path .\config\local\installation.json).Path
$env:PAOS_LIBRARY_ROOTS_CONFIG = (Resolve-Path .\config\local\library-roots.json).Path
$env:PYTHONIOENCODING = "utf-8"
python .\code\personal-agent-os\scripts\paos.py --help
python .\code\personal-agent-os\scripts\paos.py health
```

Linux 对应设置：

```sh
export PAOS_INSTALLATION_FILE="$PWD/config/local/installation.json"
export PAOS_LIBRARY_ROOTS_CONFIG="$PWD/config/local/library-roots.json"
export PYTHONIOENCODING=utf-8
python code/personal-agent-os/scripts/paos.py --help
python code/personal-agent-os/scripts/paos.py health
```

已有 Rooter 或编号登记文件时，首次 `init` 可以用 `--rooter-home <绝对目录>` 与 `--agent-numbers-config <绝对文件>` 显式绑定；没有提供时保持未绑定，不伪造身份，也不重置编号。之后的安装变更继续使用核心已有的配置入口，而不是反复运行初始化来覆盖。

## 换电脑与最小接续

[迁移说明](MIGRATION-NOTES.md) 区分三件事：重新取得代码和库、迁入选定的耐久业务资料、在目标机器重新建立运行绑定。项目 `root_path` 不会因为安装路径更新而自动变化；不要直接搜索替换 Project JSON。

公开 Git 仓库不等于完整备份。尤其 `.paos/usage-events/` 中的使用事件不是可重建缓存，Rooter/Coordinator 引用的 Works、决策与消息也不能按目录名整批丢弃。

## Agent 工作底座：已收敛的调用链

```text
CLI → 本地项目登记 → 工位 TODO / Mail / Notice
CLI → 登记的 Workflow / Skill / Tool 文件
显式 remind / cat → 对应外部 Runtime / CAT（不作为本地读写前置）
```

`orient`、`inbox`、`status`、`attention`、`agent send`、`mail`、`peers/team`、
`wake` 的项目定位和 `library search/tools` 不再查询旧 Core。
`project show` 只回登记与成员；项目最新口径按原文维护，不填 human/generated。
旧 Session 管理、项目进度填报、Dashboard/Workbench 和旧 Tips HTTP 代理已从 CLI 退出。
命令用途见[共享接口参考](libraries/workflow/Guides/guide-paos-interface-reference.md)。

对话、日会和 Tips 增量整理复用[已有工作流](libraries/workflow/Workflows/wf-meeting-audio-package.md)：
保留原件，按需更新唯一口径、TODO 或方法；不是新增状态服务，也没有自动启动采集任务。

## 验证

```text
python code/personal-agent-os/scripts/verify.py
```

当前验证器检查初始化与真实文件接续、接收器/安装合同、保留的扫描管道及 Python 语法；
不再依赖已剥离的 Node/Dashboard。原无效 Core 测试按退出接口退役，仍有用的数据根/备份
断言已迁到 `test_installation_files.py`。范围和未完成项见[代码健康说明](CODE-HEALTH-NOTES.md)。

本包尚未自动迁入真实项目，也未重写 TODO v3 为原生 Markdown 任务列表。
初次项目登记写入口、生产 Windows/WSL 原生接续、旧非入口模块的后续裁减仍是剩余工作。
这是草稿候选，不是生产安装已切换。
