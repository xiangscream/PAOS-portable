# 优化批注：这份可迁移单元做了什么、为什么

2026-10-29，S040。对照原体系，逐条说明本副本的结构优化与理由，以及实操中踩到的坑（供下次迁移避免）。原系统未被改动。

## 一、结构优化的八条，及各自理由

### 1. 目录按"代码 / 数据 / 资产 / 业务 / 配置"五分

**改动**：建 `code/`、`data/`、`libraries/`、`business/`、`config/` 五个顶层目录。
**理由**：原体系里代码、数据、业务、资产混在 `Source/` 与项目根下，看一眼分不清角色。五分之后，每一块的迁移方式天然明确——代码 clone、数据打包、资产带走、业务按需、配置改路径。这是"易懂"最基础的一步。

### 2. data_root 从代码里抽离（解耦核心）

**改动**：原 `Source/private-data` 抽为独立的 `data/`。
**理由**：代码和数据物理嵌套带来三个实际问题——代码更新会碰数据、出现两个同名 private-data 并存（连审查都判错）、无法"只带数据不带代码"。抽离后，代码目录只放代码，数据目录只放数据。**这是整个解耦里收益最直接的一步。**

### 3. 剔除 `project-registry/backups/`（4.67 GB）

**改动**：不随包迁移历史备份。
**理由**：实测 backups 占数据根的 **99.6%**（4.67 GB），而当前状态 `projects/` 只有 8.1 MB。迁移要恢复的是"当前责任"，不是"全部历史快照"。历史备份留在原机，需要时可单独取。**这一条把数据根从 4.7 GB 降到 23 MB。**

### 4. 剔除可重建的依赖与缓存

**改动**：排除 `node_modules`、`.git`、`.gitnexus`、`__pycache__`、构建产物。
**理由**：这些都能由 `npm install` / `git clone` / 运行时再生成，搬它们只会把迁移包撑大且毫无意义。代码本体因此从约 600 MB 降到 226 MB。

### 5. 不带 `Works/` 工作现场，只带 `Materials/` 经验

**改动**：Works（约 4 GB）不迁，Materials/TIPS.md 等经验保留。
**理由**：Works 是"工作现场"（中间产物、工作树、过程稿），不是资产。真正值得带走的是沉淀的经验与方法（TIPS、指南）。这正对应你说的"范例复利"——**带的是可复用的，不是全部过程**。

### 6. Rooter 只带工位，排除历史快照

**改动**：Rooter 排除 candidate / reports / restore-points / private-data，从 5.4 GB 降到 2.3 MB。
**理由**：Rooter 是安装级维护角色，要的是它的工位（当前职责、联系、脚本），不是它多年来累积的安装快照。

### 7. 业务资料独立成 `business/`

**改动**：工位 Workstations、Materials、Rooter 工位统一放 `business/`，与系统本体（code/data/libraries）分开。
**理由**：采用你那个更干净的分类——**PAOS 本体是机制，工位是它跑出来的业务资料**。分开之后，"迁移系统"和"迁移业务"变成两个可以独立进行的动作，不再互相牵扯。

### 8. 配置集中且只改路径

**改动**：`installation.json`、`library-roots.json` 放 `config/`，8 个路径全部指向本目录。
**理由**：原 resolver 已经把路径集中到这 8 个字段，直接复用，不另起一套。迁移时只改路径，不动配置结构。

## 二、实操中踩到的三个坑（重要，下次必看）

### 坑 1：工位路径不由 installation.json 决定

一开始我只改了 `installation.json` 的 8 个路径，结果 `attention show` 读到的仍是**原机工位**。
查代码才发现：**工位位置由 `data/project-registry/projects/<pid>.json` 的 `root_path` 决定**（`paos_home.py:52,66` → `root_path + /Workstations/<agent>`），安装配置里没有这一项。

**所以迁移要改的是两层路径**：安装配置（8 个）+ 每个 Project 的 `root_path`。这正是 S010 资料里提醒的"项目内部绝对定位不会随安装定位自动迁移"。

### 坑 2：PowerShell 写 JSON 会带 BOM，直接把文件写坏

我用 `Set-Content -Encoding UTF8` 改 3002.json 后，解析报 `Unexpected UTF-8 BOM`。
**原因**：PowerShell 的 UTF8 默认带 BOM，而 `json.loads` 不接受。
**正确做法**：改 JSON 用 Python（`json.load` 用 `utf-8-sig` 读、`utf-8` 无 BOM 写）或专用编辑器。**不要再用 PowerShell Set-Content 写 JSON。**

### 坑 3：Windows 控制台 GBK 编码

`paos attention show` 输出含中文/特殊字符时直接 `UnicodeEncodeError: 'gbk'`。
**解决**：设 `PYTHONIOENCODING=utf-8` 再跑。这条已写进 README 的运行步骤。

## 三、验证记录（这份副本确实能跑，不是复制对了就算）

- `paos health` → `ok:true`，build `a48fe60`。
- `resolve_home_by_registry('3002-s035')` → `D:\paos-portable\business\Workstations\3002-s035`（确认读的是副本，不是原机）。
- `paos attention show 3002 3002-s035` → 工位 schema / Current / TODO 正文正常返回。

## 四、还没做、也不该由这次顺带做的

- **没拆 `paos.py`（5947 行巨型 CLI 入口）**。它是"易懂"的反例，但拆它牵动 import 与测试，属于独立的重构任务，不该和迁移混在一起。已单列为后续候选。
- **没删 v2 历史链**。它承载内部兼容，只做"标注为历史"的处理，未剥离。要剥离须先验证正常路径对它零依赖。
- **没动 Store 的不变量**（revision / receipt / Ledger / atomic / Restore）。那是承重墙，不为风格重构。
- **只迁了 3002 这一块**。3003 / 3004 未纳入，按需按同法补。

## 五、一句话总结这次优化

原体系的问题是"认知结构乱"，不是"代码烂"。这次没改一行代码逻辑，只做了**分层、抽离、剔除历史与可重建物、集中配置**——把 12 GB 收敛成 274 MB 的、每一块都讲得清角色的自包含单元，并验证了它真能跑。

## 后续调整（同日，按 Human 进一步明确）

Human 澄清：**只需迁移优化系统，不必整理业务文件，工位不用迁**。据此把 `business/`（工位、材料、Rooter 工位）**整体移出系统包**，单独存放。系统包最终纯化为 **code + data + libraries + config**（约 256 MB），只含"机制 + 流程资产 + 安装事实"。业务工作区是独立的 Markdown，人与 Agent 直接编辑，不属系统本体——这比第 7 条更进一步：业务不只"分层"，而是**完全不进系统包**。架构图见 `ARCHITECTURE.md`。
