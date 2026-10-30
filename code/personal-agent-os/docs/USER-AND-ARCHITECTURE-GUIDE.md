# Personal Agent OS：使用与架构教学手册

> **Historical / superseded for onboarding.** 本文保留 v0.3 的架构与使用背景，不再作为当前首次使用指南。当前入口请使用 [`START-HERE.md`](START-HERE.md)，实际支持范围以 [`SUPPORT-MATRIX.md`](SUPPORT-MATRIX.md) 为准；Agent Continuity、Mailbox、Artifact Lineage 与 CAT 行为以 `docs/contracts/` 当前合同为准。

版本：v0.3 · 2026-08-04
适用对象：这个系统的主人，以及需要理解、维护或协作开发它的本地 Agent。

## 0. 先建立正确心智模型

这不是“自动替你管理人生”的系统，也不是全量 Obsidian 搜索、Agent 调度平台或聊天记录查看器。

它也不会直接启动 Codex、Claude、OpenCode 或 WorkBuddy。项目页只生成完整握手 Prompt，由你选择目标 Agent 并手动粘贴；这是保留人工授权、避免 CLI 适配复杂度的正式设计。

当前可稳定使用的核心，是一个**本机项目控制面**：你手动确认什么值得成为项目、什么是可结束的工作项；新 Agent 通过标准握手把自己关联到 Work Item，系统再把项目、工作项、Session 以低摩擦方式展示、保存、备份和恢复。

它回答的是：

> 我现在有哪些项目？每个项目的当前承诺是什么？要交付的成果卡在哪？哪些历史对话和文件能让我快速找回上下文？

当前明确不做：真实 Vault 自动扫描、遍历抓取所有历史 Agent Session、模型自动更新、NAS 同步、知识图谱、ZIP 打包上下文、自动打开 Session。

这不是缺功能，而是当前版本的边界。先让人工维护的主线真的降低切换成本，再用实际摩擦决定下一项自动化。

## 1. 三层结构

```text
Area（长期责任域，不结束）
  └─ Project（项目，可有限或持续）
       └─ Work Item（一次可完成的成果）
            └─ Session（历史证据，不额外成为管理层）
```

| 层级 | 你该用它回答的问题 | 示例 |
|---|---|---|
| Area | 这件事属于哪类长期责任？ | 程序性工作 / 工作 / 项目 |
| Project | 我持续要维护或阶段性完成什么？ | `2001` LRC101、`3001` obs-agent |
| Work Item | 这一次具体要形成什么成果？ | `2001-w001` 收敛 LRC101 产品主线 |
| Session | 我为什么认为它与这个成果有关？ | 某个 Codex、WorkBuddy、OpenCode 原生对话 |

### 四位编号

| 编号段 | Area | 当前例子 |
|---|---|---|
| `1xxx` | 程序性工作 | `1001` 周报、`1002` 调研 |
| `2xxx` | 工作 | `2001` LRC101 |
| `3xxx` | 项目 | `3001` obs-agent、`3002` Personal Agent OS |

编号只用于关联和消歧，不要求你重命名原来的 Vault、文件夹或 Agent 标题。编号关闭后封存，不复用。

Work Item 编号固定为 `<项目号>-wNNN`，例如 `3002-w004`。它必须代表**一个能结束的成果**，不要用“继续研究 Agent”“聊 LRC101”这种无限话题。

## 2. 五分钟上手

在仓库根目录打开 PowerShell：

```powershell
cd "C:\path\to\personal-agent-os"
.\scripts\start.ps1
```

脚本会：

1. 找到 Python；
2. 检查 `8766` 端口；
3. 若已经是 PAOS 服务，直接打开页面；
4. 若未启动，则启动本地服务、等待健康检查成功后打开浏览器。

默认页面是项目看板：

```text
http://127.0.0.1:8766/attention-dashboard-v1-static/projects.html
```

如果机器仍阻止 PowerShell 脚本，可只对这一次启动绕过：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

### 你应当先看什么

1. 顶部“当前焦点”：最多三项，只放今天确实需要维持注意力的项目或工作项。
2. 三个 Area 标签：程序性工作、工作、项目。
3. 卡片上的“承诺”和“阶段”：这是当前项目的最短状态摘要。
4. 点“进入”：项目页先给出“启动一个受管 Session”，随后是进度、当前要求与 DDL、相关 Session 和 Work Item。

## 3. 日常使用流程

### 3.1 新建一个项目

1. 先切换到对应 Area。
2. 点击“新建项目”。
3. 接受系统给出的下一可用四位编号，或输入同编号段的其他未用编号。
4. 输入项目名称后，会直接进入项目页。
5. 先填写“当前唯一承诺”，再填写 DDL（若存在）；不要一开始把所有待办都塞进去。
6. 新建第一个 Work Item，定义这次的可完成成果。

例如临时要准备一次产品小组分享，不必新建第四个 Area；可在 `1003 汇报准备` 下建一个 Work Item：“形成周四产品小组分享”。

### 3.2 更新一个项目

项目页点击“编辑项目”。字段分为两类：

| 字段区 | 内容 | 谁应决定 |
|---|---|---|
| `human` | 飞书原始要求、当前唯一承诺、DDL、确认时间 | 默认由你；明确授权的 Agent 只能更新这三项要求 |
| `generated` | 当前阶段、进展与成果、最近变化、当前缺口 | 你审过后手动粘贴 Agent 总结 |

当前页面仍允许你手动编辑全部字段；“人类字段不可被 Agent 默认改写”是默认工作流边界。若你在项目页主动选择已握手 Session 并复制“更新 OS 要求” Prompt，则 Agent 只可通过专用窄接口写回 `original_requirement`、`current_commitment`、`ddl`，其他字段仍不可写。Agent 无法访问本机端点时，直接手动填写就是备用手段。

保存一次项目时，系统会：

```text
读取当前 revision
  → 备份当前 JSON
  → 写入新 JSON
  → revision + 1
```

所以保存失败且提示 revision 冲突时，不要在两个页面里反复硬点保存；刷新项目页，先看另一处已经保存了什么，再合并你的修改。

### 3.3 使用 Work Item

- Work Item 是项目页里的“当前工作项”。
- 状态只有：`todo`、`doing`、`done`。
- 一个 Work Item 可以挂多个 Session。
- 删除 Work Item 前，必须先将其 Session 改挂到别的 Work Item 或删除 Session 关联；系统会阻止悬空引用。

推荐命名公式：

```text
动词 + 成果对象 + 必要时的边界
```

例如：

- `形成 LRC101 产品主线`：好；它有判断产物。
- `调研轮腿机器人`：偏宽；可改为“形成轮腿竞品判断”。
- `继续 obs-agent`：不好；没有完成定义。

### 3.4 关联 Session

日常不要再手填 Agent、环境、标题、Session ID 等一串字段。使用项目页顶部的“启动一个受管 Session”：

1. 选择已有 Work，或选择 `AUTO` 并给新 Work 起一个可结束的名称；
2. 写清这个 Session 的具体要求；
3. 填写相关文件、Obsidian 笔记或 URL（每行一项）；
4. 点击“一键复制握手 Prompt”；
5. 把 Prompt 粘贴到新开的 Codex、Claude、OpenCode 或 WorkBuddy Session；
6. Agent 在实质工作前调用本机握手端点，并返回 PAOS 的规范回执；
7. 回到项目页点“刷新登记结果”，即可看到受管 Session 与握手编号。

成功回执必须以 `PAOS_HANDSHAKE_COMPLETED` 开头，并报告规范项目名、Work Item、`handshake_id`、revision 和真实 Session 信息。若 Agent 无法访问本机端点，必须回复 `PAOS_HANDSHAKE_NOT_COMPLETED`，此时它仍是“野 Session”。

Agent 不知道原生标题、Session ID 或记录路径时必须留空，不能编造。唯一 `handshake_id` 负责重试去重，所以缺少 Session ID 也不会造成重复记录。

项目编辑页仍保留“高级纠错：手动修复 Session 记录”，只用于迁移旧 Session、纠正错误关联或补历史数据，不作为日常入口。

一个 Session 可以同时属于两个项目。例如一轮 Beni 调研既服务 `1002 调研`，也服务 `2001 LRC101`；两个项目各自保存关联理由即可。

不能确定历史 Session 归属时，不要硬挂。保留在你自己的 Session 归档目录中，等将来出现明确使用场景再关联。新 Session 则应在开始时通过握手明确归属。

### 3.5 焦点最多三项

看板卡片右下角“加入焦点”可把项目加入顶部焦点区。可填写一个可选 label：

- 留空：表示整个项目；
- 填写文字：表示今天聚焦的某项内容。

当前 label 是轻量文本，不会强制指向一个 Work Item。这是有意保留的低成本入口；当你实际觉得它经常不同步时，才值得把它升级为正式 `work_item_id` 关联。

### 3.6 与 Agent 协作

项目页现在有两种 Prompt，作用不同：

| 按钮 | 用途 |
|---|---|
| 启动新 Session / 一键复制握手 Prompt | 先完成 API 握手，把新 Session 纳入某个 Work Item，再开始工作 |
| 手动填写 / 修正 | 你直接补齐或修正项目要求，Agent 无法访问端点时的备用入口 |
| 复制“更新 OS 要求” Prompt | 你明确授权一个已握手 Session，只让它写回三个 human 要求字段 |
| 主要文件 / 随后事项下属页 | 手动编辑对应列表，或要求已握手 Agent 只更新其中一类列表 |
| 复制项目上下文 | 给已经受管的 Agent 补充项目全貌，或让 Agent做阶段性总结 |

握手 Prompt 是正式协议，会带唯一编号、目标 Project/Work、本轮要求、资料、锁定边界、API 端点和标准回执。完整协议见 [`AGENT-HANDSHAKE-PROTOCOL.md`](AGENT-HANDSHAKE-PROTOCOL.md)。

“复制项目上下文”会带上：项目编号、承诺、DDL、阶段、已有进展、主要文件、Work Item 和相关 Session。它要求 Agent 最终只输出：

1. 进展与成果；
2. 最近变化；
3. 当前缺口；
4. 建议的下一事项。

它还明确禁止 Agent 改写飞书原始要求、当前唯一承诺、DDL 与优先级。你审核后将合适的内容粘回 `generated` 区。

“更新 OS 要求”是例外但也是受限例外：Prompt 会带当前 revision 和 Session 引用。Agent 必须只提交本轮用户明确改变的要求；服务端校验该 Session 确实已经纳管、revision 没有变化，并自动备份。成功后 Agent 应返回 `PAOS_REQUIREMENT_UPDATED`、变化字段和新 revision；没有新变化或调用失败必须使用对应的明确标记。

项目页的“主要文件”和“随后事项”不再把操作堆在项目页顶部，而是在对应卡片里展开下属页。下属页的 Agent Prompt 一次只允许提交一个完整数组：`key_files` 或 `next_items`；手动编辑按钮仍会打开项目编辑器并直接定位到对应字段。

### 3.7 Tips 的位置

项目看板不承担碎片 Tip 捕获。旧 Attention Dashboard（`index.html`+`app.mjs`）已于 2026-10-10 按真实依赖闭合退役；Tips 收件箱路径不变，仍由 API 显式提交：

显式提交的 Tip 写入：

```text
private-data/inbox/tips/
优先级为：`--inbox` 参数 > `PERSONAL_AGENT_OS_INBOX` 环境变量 > 上述默认目录。

## 4. 这套系统究竟如何运行

```mermaid
flowchart TD
  U[你在浏览器操作] --> B[projects.html / project.html]
  B --> JS[projects.mjs / project.mjs]
  JS -->|fetch 本机 API| S[local_server.py : 127.0.0.1:8766]
  U -->|复制握手 Prompt| A[新 Agent Session]
  A -->|POST agent handshake| S
  S -->|canonical receipt| A
  S --> PS[project_store.py]
  PS --> D[(private-data/project-registry)]
  PS --> BK[(backups/ 历史备份)]

  U -->|显式 Tip 提交（API）| S
  S --> I[(private-data/inbox/tips)]

  M[合成 Markdown Vault] --> P[scan_vault.py]
  P --> BD[(build/dashboard-data.json)]
  BD --> O[Attention-memory-pipeline build 数据（运维工具消费）]

  G[GitHub] -.只保存代码、文档、合成样例.-> C[仓库工作区]
  D -.被 .gitignore 排除.-> G
  I -.被 .gitignore 排除.-> G
```

### 两条数据链一定要区分

| 链路 | 当前用途 | 数据是否真实 |
|---|---|---|
| Project Board | 项目、Work Item、Session、焦点、项目状态 | 是，人工决策 + Agent 窄接口握手 |
| Markdown Pipeline + 旧 Dashboard | 验证扫描、候选与三条主线的原型逻辑 | 目前主要是合成 Vault |

因此，项目看板能展示你现在建立的七个真实项目；旧 Dashboard 能演示 Tips 和 Markdown 管线，但**还没有读取你的全部真实 Obsidian Vault**。

## 5. 模块地图：从入口一路读到数据

建议按此顺序阅读代码，而不是一上来读全部：

| 顺序 | 文件 | 作用 | C++ 类比 |
|---:|---|---|---|
| 1 | `README.md` | 系统入口、边界、命令 | 项目总览 |
| 2 | `scripts/start.ps1` | 找 Python、查端口、起服务、开浏览器 | 启动器 / main 前的环境检查 |
| 3 | `attention-dashboard-v1-static/local_server.py` | 静态文件服务和 API 路由 | 轻量 Controller + HTTP Server |
| 4 | `attention-dashboard-v1-static/project_store.py` | JSON 校验、读写、备份、恢复、revision | Repository / 数据访问层 |
| 5 | `attention-dashboard-v1-static/project-model.mjs` | 无 DOM 的格式化、排序、Prompt 纯函数 | 可单测的 domain utility |
| 6 | `attention-dashboard-v1-static/projects.mjs` | Area 看板、焦点、新建项目 | 看板页面控制器 |
| 7 | `attention-dashboard-v1-static/project.mjs` | 单项目展示、编辑、Work Item、Session | 详情页控制器 |
| 8 | `attention-dashboard-v1-static/*.html`、`styles.css` | 页面骨架和视觉样式 | View |
| 9 | `attention-memory-pipeline-v0/` | 旧 Markdown 扫描实验 | 独立原型模块 |
| 10 | `tests/` | 回归保护 | 单元 / 集成测试 |

### `project_store.py` 是最值得吃透的后端文件

它没有数据库；每个项目就是一个 JSON 文件：

```text
private-data/project-registry/
├─ projects/2001.json
├─ projects/3002.json
├─ focus.json
└─ backups/projects/3002/<时间戳>.json
```

它承担四件事：

1. **校验不变量**：项目号必须四位且和 Area 对应；Work Item 必须属于本项目；Session 必须指向已有 Work Item；握手编号不能重复。
2. **原子写入**：先在同目录写临时文件、重新读回确认，再用 `os.replace` 替换正式文件。中途崩溃不会留下半个 JSON。
3. **乐观并发控制**：每个项目带 `revision`。页面保存时说明“我基于第 N 版修改”，若磁盘已经不是第 N 版，返回 `409`，拒绝盲覆盖。
4. **可恢复历史**：每次覆盖先复制旧版本到 `backups/`；恢复旧版本也会先备份当前版本。
5. **幂等握手追加**：Agent 只能原子新建/关联一个 Work 与 Session；重复 `handshake_id` 原样返回回执，不增加 revision。

这相当于一个极小的“文件型数据库”。它不追求多人高并发，而是优先保证你和多个本地 Agent 不会悄悄覆盖彼此的状态。

### `local_server.py` 的角色

它使用 Python 标准库 `ThreadingHTTPServer`，只监听 `127.0.0.1`，因此同一局域网其他设备默认访问不到。

它做两件事：

| 类型 | 例子 |
|---|---|
| 静态文件 | HTML、JS、CSS、旧 Dashboard 构建产物 |
| JSON API | `/api/projects`、`/api/focus`、`/api/agent/handshake`、`/api/agent/project-requirement-update`、`/api/tips`、`/api/health` |

写入项目、焦点和握手时，它检查同源请求与 JSON Content-Type；项目与握手请求最多 256KB，以允许保留较长要求和资料。Tips 仍使用较小的独立限制。握手是窄写接口，不接受整份项目 JSON，因此不能覆盖人工字段。

### 前端的分工

- `projects.html`：三个 Area 标签、焦点区、项目卡片。
- `projects.mjs`：请求 `/api/projects` 和 `/api/focus`，渲染卡片，创建项目，加入焦点。
- `project.html`：单项目详情、握手面板、要求更新授权面板和编辑表单。
- `project.mjs`：读取一个项目、生成握手/要求更新 Prompt、把表单转成 JSON、保存/恢复。
- `project-model.mjs`：不碰浏览器 DOM 和网络，负责两种 Prompt 与格式化纯函数，因此可以直接由 Node 测试。

这种拆法的意义是：视觉问题优先看 HTML/CSS，页面交互问题看 `*.mjs`，数据错误看 `project_store.py`，端口/API 问题看 `local_server.py`。排错不必在所有文件里盲找。

## 6. 保存一次项目时，数据如何流动

以你在 `3002` 项目页修改“进展与成果”为例：

```text
点击保存
  → project.mjs 收集表单内容
  → PUT /api/projects/3002?revision=当前版本
  → local_server.py 校验同源、Content-Type、请求体大小
  → project_store.py 校验 JSON 结构和编号关系
  → 备份旧版
  → 临时文件写入 + 回读验证
  → 原子替换 3002.json
  → revision + 1
  → 浏览器拿到新版 JSON 并重绘页面
```

如果中途失败：

- 校验失败：`422`，原文件不动；
- 有人刚保存过：`409`，原文件不动；
- 跨站写入：`403`，原文件不动；
- JSON 文件损坏：API 明确报错，不会假装“项目不存在”。

### 新 Session 握手时的数据流

```text
项目页生成 handshake_id 和 Prompt
  → 新 Agent 填写真实 Session 元数据
  → POST /api/agent/handshake
  → Store 在锁内读取当前项目
  → 若 AUTO：分配下一个 <project>-wNNN
  → 追加 Session（不接收整份项目）
  → 校验、备份、原子写入、revision + 1
  → 返回 canonical receipt
  → 相同 handshake_id 重试：直接返回同一归属，不再写盘
```

### 用户授权要求更新时的数据流

```text
项目页选择已握手 Session
  → 用户点击复制“更新 OS 要求” Prompt
  → 手动粘贴给原 Session
  → Agent 根据本轮明确变化提交 human_patch
  → local_server.py 校验同源、JSON、项目、Session、revision
  → project_store.py 只改三个 human 要求字段
  → 备份旧版 + 原子写入 + revision + 1
  → 返回 changed_fields 与 canonical receipt
```

## 7. 验证与排错

### 一键验证

```powershell
.\scripts\verify.ps1
```

当前会运行 5 个套件，共 **137 项测试**：

| 套件 | 数量 | 保护什么 |
|---|---:|---|
| Pipeline Python | 17 | 合成 Markdown 扫描与 Dashboard 数据契约 |
| Tips + Project API | 35 | Inbox、HTTP API、同源、revision、握手、要求与列表更新回执、未知字段隔离 |
| Project Store | 46 | JSON 校验、备份、恢复、并发、幂等握手、Session 关联与受限列表/human patch |
| 旧 Dashboard Node | 10 | 旧 Dashboard 的浏览器数据逻辑 |
| Project Board Node | 29 | 编号、排序、上下文/握手/要求/列表更新 Prompt、Work Item 与下属页面结构 |

如果 PowerShell 找不到 Node，可临时指定实际位置：

```powershell
$env:PAOS_NODE = "C:\\path\\to\\node.exe"
.\scripts\verify.ps1
```

从 WSL Bash 调用 Windows 版验证脚本时，不要直接把 `/mnt/c/...` 当作 `-File` 参数，也不要把五套件手工拆开。使用混合路径并让 WSL 转换 Node 路径：

```bash
cd /mnt/c/path/to/personal-agent-os
export PAOS_NODE=/mnt/c/path/to/node.exe
export WSLENV="${WSLENV:+$WSLENV:}PAOS_NODE/p"
powershell.exe -NoProfile -ExecutionPolicy Bypass \
  -File "$(wslpath -m ./scripts/verify.ps1)"
```

该方式已从 Ubuntu 26.04 WSL 实测跑通完整五套件。Windows PowerShell 5.1 的中文输出在 WSL 终端里可能显示乱码，但不影响测试执行和退出码。

### 诊断顺序

```powershell
.\scripts\doctor.ps1
```

按以下顺序定位：

1. Python 是否可用；
2. `8766` 端口是否是 PAOS；
3. `/api/health` 是否返回 `ok: true`；
4. 页面是否 HTTP 200；
5. 旧 Dashboard 的构建数据是否可读。

常见情形：

| 现象 | 先做什么 |
|---|---|
| `禁止运行脚本` | 用本手册第 2 节的单次 Bypass 命令，或修正当前用户的 Execution Policy |
| `端口 8766 被占用` | 不要直接杀进程；先访问 `/api/health` 判断是否已是 PAOS |
| 看板空白 | 运行 `doctor.ps1`；再检查 `private-data/project-registry/projects/` 是否仍有 JSON |
| 保存提示 409 | 刷新页面，比较最新内容后再保存 |
| 保存提示 422 | Work Item 或 Session 结构不符合规则；确认 Session 已选择 Work Item |
| 项目页打不开 | 确认 URL 带 `?id=四位编号`，例如 `project.html?id=3002` |
| Agent 返回 `PAOS_HANDSHAKE_NOT_COMPLETED` | 先确认 PAOS 服务已启动，再让 Agent重试同一个 `handshake_id`；不要重新复制生成另一份 Prompt |
| 握手返回 404 | Project 或所选 Work Item 已不存在；刷新项目页后重新生成 Prompt |
| 握手成功但页面没出现 Session | 点击“刷新登记结果”；核对回执中的 project_id 是否为当前项目 |
| 旧 Dashboard 数据报错 | 它依赖 `attention-memory-pipeline-v0/build/`；删掉旧 build 后重新跑扫描管线 |

## 8. 恢复与 Git 的边界

项目 JSON 不进 Git，但每次正常保存都会先备份。优先使用项目页的“恢复上一版”；不要先手改 JSON 文件。

代码和文档则受 Git 保护：

```powershell
git log --oneline -10
git status
.\scripts\verify.ps1
```

恢复一个代码版本前先确认当前工作区有没有你未提交的变更。不要用强制重置来“图快”。项目数据的单独备份位置是：

```text
private-data/project-registry/backups/
```

更完整的恢复说明见 [RECOVERY.md](../RECOVERY.md)。

## 9. 建议你用 45 分钟吃透架构

| 时间 | 做什么 | 目标 |
|---:|---|---|
| 0–5 分钟 | 启动看板，浏览三个 Area | 理解系统的用户入口 |
| 5–15 分钟 | 进入 `3002`，查看 Work Item 和 Session | 理解三层如何落到真实数据 |
| 15–25 分钟 | 只读打开 `private-data/project-registry/projects/3002.json` | 将页面字段和 JSON 一一对应 |
| 25–35 分钟 | 从 `scripts/start.ps1` 跟到 `local_server.py`、`project_store.py` | 理解启动和保存链路 |
| 35–45 分钟 | 运行 `verify.ps1`，打开一个测试文件 | 理解每层怎样被保护 |

第一轮只读即可。第二轮再试一次低风险编辑：为 `3002` 添加一个临时 Work Item，保存后观察 revision 增加与 backup 文件出现，再点“恢复上一版”。这样你会真正理解文件型存储、revision 和回滚，而不是只记住概念。

## 10. 当前阶段的下一步，不要提前做

你下一次应该先获得两类真实反馈：

1. 打开项目页时，是否真的能在十秒内找回“进度、承诺/DDL、Session”；
2. 手动把 Agent 输出粘回项目状态时，哪里最别扭。

只有当这些反馈明确出现，才选择下一项小扩展：例如 Session 路径一键打开、焦点正式绑定 Work Item、从项目目录候选关联 Markdown，或将项目状态卡同步写回指定 Vault。模型自动归档、NAS、全局 RAG 和多 Agent 调度目前都不应抢在这一步之前。
