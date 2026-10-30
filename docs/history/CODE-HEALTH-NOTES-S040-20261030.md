# 硬基座优化批注：拆分与前端剥离

2026-10-30，S040。在 `paos-portable` 副本上做，**未动原系统**。目标：让硬基座更轻、更懂、更易迁移。所有改动都做了功能验证。

## 一、paos.py 巨型入口的拆分

**问题**：`paos.py` 原 5948 行，一个文件装着 95 个函数，而且**同时包含 v2 HTTP 客户端逻辑和 v3 文件操作逻辑**——两套挤在一起，是"易懂"最大的反例。

**方法**：先 AST 做依赖分析，找**自包含或域内自包含**的函数组，按域提取（不是按行乱切），每拆一块立即验证。

### 拆出的三个模块

| 模块 | 内容 | 行数 | 对外依赖 |
| --- | --- | --- | --- |
| `paos_render.py` | 5 个 `render_*` 展示函数 | 121 | 仅 typing，纯 `result.get` 拼字符串 |
| `paos_orient.py` | orient 导览域 7 个函数 | 224 | paos_library / paos_installation / paos_workstation |
| `paos_compact.py` | compact 摘要域 5 函数 + 3 常量 | 103 | 仅 typing 与域内常量 |

`paos.py`：**5948 → 5577 行**，三处改为 `from paos_xxx import ...`，调用处不变（函数名仍在命名空间）。

**关键依据**：ORIENT 域经 AST 验证**域外依赖为空**（可整体独立）；COMPACT 域只多带 3 个 `*_MAX_CHARS` 常量（一并带走）。render 系是纯展示，最先拆。

### 验证（每拆必验）

- `py_compile` 三个新模块 + paos.py 全过
- `import paos_orient / paos_compact` 正常
- `paos health` → `ok:true`
- `paos orient 3002 3002-s035` → 完整输出（Who / Project / Mail / Source 全正常）——这一步同时覆盖了 orient 域与 compact 域的真实调用

## 二、前端完全剥离

**改动**：把 `attention-dashboard-v1-static/`（v2 HTTP 服务 + 旧前端 UI，**195 个 py**）从代码包移到 `D:\paos-frontend-legacy`。

**理由**：按你的判断——**现在的"前端"未来是 Obsidian 库中的汇总页**，这套历史前端服务+UI 不该留在硬基座里。剥离后，硬基座只剩 **CLI + v3 核心模块**，未来前端在本地收敛完成后重做。

**验证**：剥离后 `health`、`orient` 均正常。前端本就"承载内部兼容、非业务入口"，CLI 正常路径不依赖它；`local_server.py` 是"前端依赖 scripts"，不是反过来。

**保留**：`attention-memory-pipeline-v0/`（仅 1MB）——它被 `ensure_build_data.py`、`release_check.py`、`verify.py` 引用，是构建/派生数据的来源，剥了会让 verify 的派生数据步失败。**只剥大前端服务+UI，不碰这个被构建工具引用的小管道。**

## 三、verify 的 Python tests FAIL 是环境问题，不是拆分引入

跑 `verify.py` 时 `[2/7] Python tests FAIL`，一度需要查清是不是拆分破坏。
核实：**本机几个 Python 都没装 pytest**（`No module named pytest`），所以那项直接失败。
**这与拆分无关**——拆分已用 compile / import / health / orient 做了实证。其余六道门（Architecture / Derived data / Node UTC / Node 上海 / compileall / JS check）全 PASS。

## 四、剩余路线（未做，按优先级）

1. **v2 客户端函数剥离**：paos.py 里的 `RestClient`、session/project/coordinator 的 HTTP 调用属 v2 历史链，前端剥离后它们没有服务端可连。可整体提取为 `paos_v2_legacy.py`，让 paos.py 只剩 v3 正常路径 + 工具。**需先确认 v3 功能对这些函数零依赖**（AST 可判）。
2. **继续按域拆 v3**：attention / mail / notice / library 各自成模块，让 paos.py 只剩 argparse + main + 共享工具。
3. **paos.py 最终目标**：一个薄入口（参数解析 + 调度），业务全在域模块里——那时"易懂"才算真正达成。

## 五、边界

- 没动 Store 的不变量（revision / receipt / Ledger / atomic / Restore）。
- 没删 v2 历史链代码，只是**把大前端服务+UI 物理剥离**；v2 客户端函数仍留在 paos.py 待后续按路线 1 处理。
- 所有改动只在副本，原系统不受影响。
