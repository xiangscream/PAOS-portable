# PAOS Portable：首轮收敛与代码健康复核

审查基线：`e00f31b2bedb6b40d8924a74636b26dd633f6fe2`（初始仓库提交）。本轮只改 Portable 仓库候选，不改原生产系统、不迁移真实业务、不启动服务。

S040 的拆分与剥离记录原文保留在 [历史代码健康记录](docs/history/CODE-HEALTH-NOTES-S040-20261030.md)。下表是对当前仓库的核实，不把历史回报自动升级为本轮实测。

## 一、查明的问题与本轮处理

| 问题 | 基线证据 | 本轮处理 |
|---|---|---|
| README 将本机副本和 Git 包混写 | 仓库没有 data/、真实 installation.json、Rooter 或项目工位；README 却列其尺寸和闭环实测 | README 改成真实发布边界，分开配置/CLI/业务/唤醒验证 |
| 配置模板不能直接启动 | `config/*.example.json` 使用占位符；`paos_installation.py` 要求绝对定位 | 新增只做定位的 `portable.py`，从仓库位置展开模板，使用原 v1 schema |
| Library 元数据目录不会随 clone 出现 | 根 `.gitignore` 忽略 `.paos/`；`paos_library.py` 的注册校验要求该目录及 usage-events/ | init 只补空目录；明确不恢复使用事件，不伪造统计 |
| 硬/软边界过度按文件格式划分 | 旧 ARCHITECTURE 声称系统不约束内容；开发准则实际要求 Home/Project 专属写者 | 统一架构说明；可读 Markdown 不等于可绕过状态合同 |
| 工位迁移范围重复、过时 | README 要求全部十个工位，历史文档又说工位都不迁 | 采用本轮用户确定的 Rooter + 每项目现任 Coordinator；不删除历史 |
| Works 与 `.paos` 被笼统当成可丢内容 | 旧迁移记录将 Works 全视作现场；Library 代码将 usage-events 作为原始事实 | 按引用/证据筛选，保留范例、正式成果及所需历史事件 |
| 文档重复维护结构定义 | README、ARCHITECTURE、COMPOSITION 分别给出不同结构 | ARCHITECTURE 为唯一边界说明，COMPOSITION 仅保留入口，历史报告归档 |

## 二、必须保留为未完成的硬基座缺口

**1. 旧 verifier 与当前包不闭合。**

`scripts/verify.py` 仍对 `attention-dashboard-v1-static` 执行 unittest、Node 测试、编译检查；该目录已不在当前包。它也没有在现有 `python_tests()` 中发现根 `tests/` 的三份 pytest 测试。因此“只缺 pytest，其他六门已过”不能作为此 Git 包的可复现结论。保留旧报告原文，但不沿用其通过口径。

**2. UI 剥离不等于后端依赖剥离完成。**

`AGENTS.md` 和开发准则仍把 ProjectStore 放在已剥离的目录中。`tests/test_d32_data_root.py` 导入 `install_homes`，并把 scripts 与旧服务目录加入搜索路径；本轮读取 `scripts/install_homes.py` 返回 404。需要恢复必要后端模块或有证据地移除对应能力，并同步测试，不能仅凭 health/orient 两条成功就断言全 CLI 无依赖。

**3. CLI 入口仍混合新旧语义。**

`scripts/paos.py` 的模块说明仍称所有耐久状态只走 HTTP，同时文件实际导入 v3 Home/Mail/Notice 等模块。下一切片应先列清命令到模块的真实依赖，再按域裁减或拆分；不再以减少主文件行数作为完成指标。

**4. 项目恢复与运行绑定未验证。**

本仓库没有真实项目数据。未核实实际 Coordinator、未完成输入和原件可达性；也未测试 Windows/WSL、CAT、Receiver 或新机唤醒。任何配置级结果都不能填补这些证据空白。

## 三、新增入口的设计取舍

`plan`、`doctor` 只读。`init` 的显式写入范围仅为 config/local 配置对、空 data_root 以及库所需的空元数据目录。配置对先在同一文件系统暂存，写完后一次重命名发布；不提供 force 覆盖，不写 Project、TODO、Mail、Notice、Contact、凭据或 Runtime 配置。

旧配置不匹配、已存在另一安装描述、损坏 JSON、未知模板字段、文件占目录、路径越界均可见失败。已有 Rooter 和编号文件只能显式绑定，默认保持未绑定。代码旁注解释了这些约束的原因。

这是首次配置入口，不是完整安装器、迁移引擎、通用配置数据库或自动重试器。它没有替代任何业务写者。

## 四、实际验证与限制

在本轮 Linux 执行容器运行 `python -m unittest discover -s tests -v`：**37 tests，全部通过**。测试使用合成的最小包，覆盖路径含空格/中文、工作目录独立、只读检查、重复初始化、旧配置保护、绑定不覆盖、编号内容保留、损坏输入、路径/链接边界、写入/发布失败清理、移动后旧路径诊断与退出码。

这是新增助手的合同测试，**不是完整仓库集成测试**。直接 git clone 失败，实际错误为 `Could not resolve host: github.com`；仓库原文通过已连接 GitHub 工具读取，新增文件在容器中测试。未在此容器取得整库检出，未运行核心完整测试，未通过 Windows/WSL 或真实业务闭环验收。

下一项最有价值的硬基座工作是**让当前 CLI 依赖和保留测试形成可复现的闭合包**，而不是扩大 Agent 数量或继续删除目录。本轮不声称 PAOS Portable 已全部完成。
