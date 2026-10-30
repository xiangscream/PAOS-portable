# Personal Agent OS｜私有数据迁移政策 v0.1

状态：初始个人资料迁移完成；尚未进入索引或模型处理  
更新时间：2026-07-31

## 1. 用户授权范围

用户允许 Personal Agent OS 在后续 Gate 使用和迁移以下类别：

- 真实 Obsidian Vault 与备份 Vault；
- 真实 Tips Inbox；
- 数据库、Agent raw logs 与工具调用记录；
- `agent-co` 源码与历史材料；
- 模型与 NAS 配置；
- 个人资料和项目材料；
- API Key、Token 与公司内网配置。

授权改变的是“可纳入系统”的数据范围，不改变 Git、凭据和公司数据的安全边界。

### Secret Store（独立于资料归档）

用户指定的敏感信息根目录为：

```text
C:\\Users\\remo\\Desktop\\secrest
```

它是 **Secret Store**，而不是 Personal Agent OS 的资料目录：

- 不放入仓库，也不放入 `private-data/`；
- 不参与自动扫描、索引、夜间整理、归档复制或 Agent 日志；
- Agent 只能引用逻辑名称（如 `company-llm`、`nas-smb`），不得在 Markdown、Prompt、截图或 Git 历史中记录真实值；
- 只有某个已批准的功能确实需要凭据时，才设计一个最小适配器读取对应条目；仓库只保留 `.env.example`、字段说明或连接配置 schema，绝不保留 `.env` 与真实密钥；
- 公司 API Key、内网地址和工作账号仍受公司政策约束，不能因为个人仓库为 private 而自动获得复制或上传授权。

## 1.1 已完成的初始本机归档

2026-07-31 已以复制、逐文件 SHA-256 校验的方式迁入本机 `private-data/`：

| 来源 | 纳入文件 | 体积 | 结果 |
|---|---:|---:|---|
| Obsidian Vault | 853 | 63.89 MiB | 已校验 |
| Obsidian Vault Backup | 216 | 3.06 MiB | 已校验 |
| obs-agent | 29 | 0.66 MiB | 已排除 Git、依赖与 `.venv*` |
| OBSBOT first-month workspace | 254 | 18.04 MiB | 已校验 |
| agent-co 历史档案 | 451 | 303.91 MiB | private Git clone，固定在 `3cfaf15c` |

普通资料合计为 1,352 个文件、85.65 MiB；`agent-co` 保留其历史 Git 元数据。来源没有被移动或删除。迁移清单只保存在 Git 忽略的 `private-data/_migration-meta/`。

疑似凭据文件、`.env*`、私钥格式文件、`.git`（除 agent-co 历史档案）和可重建依赖环境没有进入普通副本。它们不是丢失，而是等待 Secret Store 或独立归档流程。

## 2. 四层存储

| 层级 | 典型内容 | GitHub | 默认位置 | 目的 |
|---|---|---:|---|---|
| Code & Planning | 代码、Skill、设计、任务包、脱敏样例 | 跟踪 | 仓库工作区 | 可协作、可审查、可恢复 |
| Private Data Root | Vault 副本、Inbox、DB、raw logs、个人资料、真实配置 | 忽略 | `private-data/` 或受控外部路径 | 让系统可用真实信息 |
| Derived Data | 索引、摘要候选、缓存、报告 | 默认忽略 | `runtime/`、`build/` | 可删除并重建 |
| Secret Store | Key、Token、密码、公司连接凭据 | 永不跟踪 | 环境变量、系统密钥存储或受控本地文件 | 仅在运行时注入 |

`private-data/` 与 `runtime/` 不等于“无保护目录”：它们仍需本地备份、权限控制、来源清单和恢复路径，只是不进入 Git 历史。

本系统当前的受控本地 Secret Store 路径为 `C:\\Users\\remo\\Desktop\\secrest`。系统只保存逻辑引用名和配置 schema，不自动读取其中内容。

## 3. 分类迁移规则

### Vault、Inbox、数据库与 raw logs

允许复制到 Private Data Root，但每一次迁移必须先完成：

1. Dry Run：文件数、大小、来源、目标、排除项；
2. 来源哈希与时间戳；
3. 只复制，不移动、不删除来源；
4. 忽略规则验证，确保没有进入 Git 候选列表；
5. 可恢复说明和删除申请流程。

第一轮只允许用户选定的一条低敏任务切片，不扫描整个 Vault。

### agent-co

源码可作为只读历史档案迁移，但不作为 Personal Agent OS runtime 的依赖。SQLite、raw logs 与含用户会话的材料进入 Private Data Root；代码先经过敏感扫描后才可纳入 Git。

### 模型与 NAS 配置

配置分为两部分：

- 可公开的结构与字段模板：允许放入 Git；
- 真实名称、路径、IP、账号、挂载凭据与 Token：进入 Private Data Root 或 Secret Store。

模型权重不复制进 Git；只保存安装说明、版本、量化方式和可重建清单。

### Key、Token 与公司内网配置

永不明文提交到 GitHub，即使仓库 private。个人 Key 可在本地 Secret Store 使用；公司 Key、内网 URL、会议与业务数据是否能复制到个人设备或个人仓库，需要遵守公司制度。这个限制不由 Agent 或用户个人授权单独解除。

## 4. G1 的唯一目标

验证一条用户手选、可撤回的真实任务切片能否以只读方式进入 Dashboard，同时满足：

- 原文仍然是事实源；
- 来源、哈希与导入时间可追溯；
- 删除 Private Data Root 后系统降级到合成数据；
- 不向模型发送该切片；
- 不产生 Git 跟踪的真实内容；
- 用户能在 30 分钟内理解它如何进入、如何被索引、如何撤回。

## 5. 停止条件

- Dry Run 影响超过 20 个文件而未获批准；
- 需要移动、删除或覆盖来源；
- 真实内容出现在 Git 候选清单、PR 或日志；
- 需要把 Key、Token、密码或内部 URL 写入 Markdown；
- 无法解释数据来源、所有权或恢复方法；
- 公司规则对复制个人存储存在疑问；
- 同一导入失败三次。

## 6. 下一步

先完成 T-001 的 Dry Run。之后由设计 Agent 基于实际文件分布，为 G1 生成单独的 `T-010` 任务包；在用户批准前不复制任何真实资料。

