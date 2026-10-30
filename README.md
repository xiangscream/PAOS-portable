# PAOS 可迁移单元

这是从本机 PAOS 体系中**抽离、收敛后的一份自包含副本**，目标是：一眼看懂每块是什么、换电脑能直接恢复。

**只读自原系统，未改动原系统任何文件。** 全部内容约 274 MB（原体系约 12 GB，已剔除可重建依赖与历史堆积）。

## 目录结构

```
paos-portable/
├─ code/personal-agent-os/     核心代码（PAOS 本体，v3 正常路径 + 历史兼容链）
├─ data/                       安装事实（data_root，已从代码里抽离）
├─ libraries/                  共享资产（workflow 流程库 / skill 技能库 / 工具目录）
└─ config/                     安装配置（路径已指向本目录）
    ├─ installation.json
    ├─ library-roots.json
    └─ AGENT-NUMBERS.json
```

**这是纯系统包**：只含"机制 + 流程资产 + 安装事实"，**不含工位等业务文件**。

**分层原则**：代码可重建（clone）、数据必须带走（data）、流程资产可复用（libraries）、配置集中（config）。**业务工作区（各 Agent 工位 TODO、项目文件）是独立的 Markdown，不属于本系统包**——它们由人或 Agent 直接编辑，按需另行处理。架构与分层理由见 `ARCHITECTURE.md`，逐条优化批注见 `MIGRATION-NOTES.md`。

## 3002 完整闭环

本系统包与**项目库**组合，构成 Project 3002 的完整闭环：

| 部分 | 位置 | 角色 | 大小 |
| --- | --- | --- | --- |
| 硬侧代码 | `code/personal-agent-os` | PAOS 本体（可 clone） | 226 MB |
| PAOS 库（软侧） | `libraries/` | 流程库 / 技能库 / 工具目录 / Rooter 工位 | ~9 MB |
| 运行状态 | `data/` + `config/` | 安装事实 + 配置 | ~23 MB |
| **项目库** | `D:\paos-business` | **全部 10 个工位** + Materials | ~16 MB |

项目库是独立的 Obsidian 库，含 `Workstations/`（s010…s037 全部 10 个工位）与 `Materials/`。**工位属项目业务，不进系统包**，但闭环通过 `data/project-registry/projects/3002.json` 的 `root_path` 指向它。

**闭环验证**（已实测）：

- `paos health` → `ok:true`（build `a48fe60`）
- 工位解析 → `D:\paos-business\Workstations\3002-s035`（确认指向项目库）
- `attention show 3002 3002-s035` → 工位正文可读
- 流程库 `workflow/CATALOG.md`、`skill/CATALOG.md` 均在

## 在本机/新机跑起来

```powershell
# 1. 指向本单元的安装配置
$env:PAOS_INSTALLATION_FILE = "D:\paos-portable\config\installation.json"
$env:PYTHONIOENCODING = "utf-8"   # Windows 控制台必须，否则中文/特殊字符报 GBK 错

# 2. 进入代码目录运行
cd D:\paos-portable\code\personal-agent-os
python scripts\paos.py health

# 3. 系统本体自检（工位业务数据不在本包内，见下方说明）
```

已实测通过：`health` 返回 `ok:true`（build `a48fe60`），系统本体可独立运行。工位等业务文件不在本系统包内——它们是独立的 Markdown 工作区，由人或 Agent 直接编辑，按需指向或另行迁移。

## 换电脑怎么做

1. **整目录拷到新机**（放哪都行，不必是 D 盘）。
2. **若路径变了，改三处**（就这三处，没有第四处）：
   - `config/installation.json` 的 5 个路径（source_root / data_root / library_roots_config / rooter_home / agent_numbers_config）
   - `config/library-roots.json` 的 3 个路径（workflow_root / skill_root / tool_catalog）
   - `data/project-registry/projects/3002.json` 的 `root_path`（指向新的业务工作区位置）
3. **装 Runtime**（Codex / OpenCode）并登录——这些不随包迁移。
4. **设 `PAOS_INSTALLATION_FILE`** 指向新位置的 `config/installation.json`。
5. **逐工位重建 Contact / wake binding**：原生会话 ID、接收器、端口都是新机重新建立，不沿用旧值。
6. 用 `paos health` + 各工位 `attention show` 验收——**恢复的是工位与 Current，不是聊天历史**。

## 这份副本没包含什么（有意不带）

- `project-registry/backups/`（4.67 GB 历史快照，留原机，需要时可取）
- `node_modules`、`.git`、`.gitnexus`、缓存、构建产物（可重建）
- **工位等业务文件**（Workstations、Materials、Rooter 工位）——已单独移出系统包，不属系统本体
- `Works/` 工作现场（约 4 GB，非资产）
- Rooter 的 candidate / reports / restore-points（历史快照）
- Runtime 软件、登录凭据、原生会话 ID、接收器进程、PID / 命名管道

## 注意

- 本系统包**不含工位业务文件**。各 Agent 工位 TODO、项目材料属业务资料，由人或 Agent 直接编辑，按需另行处理（原机仍在，副本暂存 `D:\paos-business`）。registry 里的 `root_path` 指向业务工作区位置，新机按需指向已有或新建的工作区。
- 代码里仍含 v2 历史 HTTP 链（内部兼容用）。**业务入口是 v3 CLI**，Core 8766 属历史链，迁移时不需要拉起它也能用 CLI。
- 这是一份**副本快照**（2026-10-29），原系统后续变更不会自动同步。
