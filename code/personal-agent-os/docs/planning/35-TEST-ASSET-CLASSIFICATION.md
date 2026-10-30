---
type: technical
title: "PAOS 测试资产分类与治理：哪些该留、哪些该删、怎么识别过时约束"
author: "Remo"
category: "Engineering Governance"
tags:
  - paos
  - testing
  - conformance
  - invariants
  - cleanup
  - technical-debt
description: "面向实施 Agent 的测试资产治理指南。给出 A/B/C/D 四类判据、过时约束的识别信号、清理流程与逐文件建议，用于逐步清除不再成立的测试。"
summary: >
  测试不是同一种东西。有的定义产品规格（必须留），有的保护当前实现（可重写），
  有的只是实现细节快照（可删），还有一类最危险：编码了已被领域迁移推翻的旧约束，
  看起来在保护正确性，实际在阻碍迁移。本文给出识别与清理它们的可执行判据。
status: active
version: "0.1.0"
date_created: 2026-08-28
date_updated: 2026-08-28
system: "Personal Agent OS"
component: "Test Governance"
aliases:
  - "PAOS 测试分类"
  - "测试资产治理"
  - "过时约束识别"
related:
  - "[[PAOS-Reverse-PRD-v0.6]]"
  - "[[cat来啦]]"
---

# PAOS 测试资产分类与治理

> 一句话：**测试不是越多越好。真正要保护的不是测试数量，而是测试背后仍然成立的产品约束。**

---

## 0. 这份文档用来做什么

PAOS 目前 `attention-dashboard-v1-static/tests` 下有 **348 项测试**（`verify.ps1` 报的 379 含 Pipeline 与 collab-run 等外部套件）。它们不是同一种东西，却被同等对待——这带来两个问题：

1. **该删的不敢删**：担心删掉的是产品约束；
2. **该留的没标清**：后人不知道某条测试守护的是产品语义还是实现细节。

在领域迁移（D1–D9）期间，这会被放大：**一些测试守护的约束，正是迁移要废弃的约束**。它们看起来在保护正确性，实际上在阻止迁移。

本文给出分类法、判据与清理流程，供实施 Agent 逐步执行。

---

## 1. 四类测试

| 类 | 名称 | 定义 | 处置 |
|---|---|---|---|
| **A** | Product Invariant | 定义"什么叫做对"，跨实现都应成立 | **保留，且应提升为可移植 conformance** |
| **B** | Implementation Regression | 保护当前实现的行为，但换实现可重写 | 保留，但可随实现重写 |
| **C** | Incidental | 只是当前代码结构 / DOM / 字段排列的快照 | **可删**，阻碍重构时优先删 |
| **D** | Obsolete Constraint ★ | 编码了已被产品决策推翻的旧约束 | **必须删或改写**，见 §3 |

**关键区别**：A 和 D 看起来一样（都在断言系统行为），但 A 守护的是**当前成立**的约束，D 守护的是**已经不成立**的约束。分辨它们靠 §3 的信号。

---

## 2. 分类判据（可执行）

### A 类判据（满足任一）

- 断言**外部可观察行为**（HTTP 状态码、JSON 响应、文件系统可观察结果）；
- 断言**权威关系**（谁能改什么、Agent 不能改人类字段）；
- 断言**不可逆性语义**（Ledger append-only、Restore 后旧 operation 失效、失败不留半写状态）；
- 断言**跨状态/时态约束**（涉及历史，不只是当前状态）。

### B 类判据

- 断言某 helper / 内部函数的返回值；
- 断言渲染字符串、序列化格式；
- 断言内部调用顺序（如"必须先 deepcopy 再 validate"）。

> **注意**：B 类里有一种容易误判的——"必须先调用 `_atomic_write()`"是 B（实现细节），
> 而"模拟写入中断后，旧完整 Project 仍可读、不出现半写 JSON"是 A（行为后果）。
> **真正的产品约束是行为后果，不是实现步骤。**

### C 类判据

- 只断言当前 DOM 结构、函数结构、字段排列；
- 与产品语义无关；
- 换实现必然失败，且不携带任何产品信息。

---

## 3. D 类：过时约束的识别（本文核心）

### 3.1 六个识别信号

一条测试若命中任一信号，应被怀疑为 D 类：

| # | 信号 | 说明 |
|---|---|---|
| 1 | 它守护的对象/字段**正在被领域迁移废弃** | 如 `mode`、Work 独占锁、Close→Work 投影 |
| 2 | 断言的是**已推翻的因果**（Session Close 导致 Work Close） | 与 PRD v0.6 的 P3（Work > Session）冲突 |
| 3 | 断言的是**单一性**，而迁移要求**多对多** | 如"Work 只能有一个 active Session" |
| 4 | 测试名/docstring 里的语义**已被新合同取代** | 与迁移合同逐条比对 |
| 5 | 它守护的 invariant **没有记录 Precondition** | 后人无从判断它何时该退役 |
| 6 | 它测的是与 PAOS 核心无关的**历史模块** | 如旧 Pipeline 的合成 Vault 扫描 |

### 3.2 当前已知候选（来自领域迁移审计 D0，需逐条复核）

> 以下不是"必须删"的清单，是"必须复核"的清单。删除前须确认对应迁移已落地。

| 候选 | 现状 | 迁移要求 | 处置方向 |
|---|---|---|---|
| `mode` 必填 / 强制 `managed` | schema 与 open 均强制 | 退为 legacy 只读，新 Session 不写 | 迁移落地后改写为 legacy 兼容测试 |
| Work 独占锁（`_find_conflicting_managed_session`） | open_session / _start_new_cycle / create_request_coordinator 三处调用 | 删独占锁，允许 many-to-many | **删除**，替换为多 Session 共存测试 |
| Session Close 投影 Work 状态 | `_apply_close_result` 仍投影 | Close 不再改 Work 状态 | **删除**，替换为"Close 不影响 Work"测试 |
| `review_source_session_id` 单一完成来源 | review_work 要求单一 completed source | 多 Session 可共同完成 | **改写** |
| `cancel_work` 在 >1 active 时拒绝 | 当前拒绝 | 全部 abandoned 后取消 | **改写** |
| `dashboard-v1.test.mjs`（10 项） | 旧 Pipeline 合成 Vault 扫描 | 与 PAOS 核心无关 | **C 类，可删** |

---

## 4. 清理流程（实施 Agent 执行步骤）

### 步骤 1：建立分类台账

对 `tests/` 下每个文件，按 §2 判据标注 A/B/C/D，写入本文件 §6 的表格或新建 `docs/planning/36-TEST-INVENTORY.md`。

**验收**：每个文件都有分类，没有"未分类"。

### 步骤 2：只处理 C 类与 D 类

- **C 类**：直接删。删后跑全量 `verify.ps1`，必须保持全绿。
- **D 类**：**不直接删**，先确认对应迁移是否已落地：
  - 未落地 → 保留，但在 docstring 加 `status: pending-migration` 标记；
  - 已落地 → 删除或改写为新的 invariant 测试。

### 步骤 3：为 A 类补 Precondition

每条 A 类测试的 docstring 补三元信息：

```python
def test_replay_after_restore_is_rejected(...):
    """
    intent: consumed operation IDs survive logical restore
    precondition: operation was successfully committed before restore
    status: active          # active | pending-migration | superseded
    origin: GRILL-027 / 3002-g001
    """
```

> **不要新建 INV 数据库**——元信息留在 docstring 即可，Agent 可搜索。这与 PAOS"不新增对象、复用现有结构"的原则一致。

### 步骤 4：区分可移植与不可移植

A 类里再分一层：

```text
conformance/portable/     HTTP 黑盒、文件系统可观察结果、CLI 黑盒
reference-tests/          project_store 内部、Python helper、DOM 实现
```

可移植的才是"软件规格"，不可移植的是"参考实现测试"。

### 步骤 5：每包独立提交

- 一个文件（或一组强相关测试）一个 commit；
- 每个 commit 后跑：聚焦测试 → 架构检查 → 完整 `verify.ps1`；
- 报告：提交号、文件范围、删除/改写了什么、测试数字变化；
- **禁止** broad git add、**禁止** push、**禁止**清理不属于本次的既有改动。

---

## 5. 边界与禁止

1. **不删 A 类**。不确定时，默认保留并标记 `status: unknown`。
2. **不在迁移未落地时删 D 类**。删早了会丢失回归保护。
3. **不因"测试太多"而删**。删除理由必须是"它守护的约束已不成立"，不是"它碍事"。
4. **不改断言语义来让测试变绿**。测试红了，说明要么代码错，要么约束变了——后者要走迁移流程，不能改测试绕过。
5. **不碰**：`mutate_v2`、`revision`、`receipt`、`backup`、原子写、`Restore` 语义相关的 A 类测试。
6. **不清理用户既有的未提交改动**。

---

## 6. 逐文件清单（实测，2026-08-28）

| 文件 | 项数 | 建议分类 | 说明 |
|---|---:|---|---|
| `test_v2_sessions.py` | 98 | **A 为主** | Session 生命周期核心；含 `SessionHttpTests`（可移植）与 Store 层（不可移植） |
| `test_project_store.py` | 52 | **A + B** | 事务/并发/Restore 属 A；helper 细节属 B |
| `project-dashboard.test.mjs` | 45 | **B/C** | 前端 DOM 与渲染，换实现可重写 |
| `test_local_server.py` | 37 | **A（可移植）** | `ProjectApiTests` 等为 HTTP 黑盒，是跨实现 conformance 的基础 |
| `test_collab_watcher.py` | 27 | **A** | Watcher / CAT 协作语义 |
| `test_t101_fixes.py` | 24 | **A** | 阻塞回归；含 `T101HttpTests`（可移植） |
| `test_narrow_write_contract.py` | 21 | **纯 A** | 最核心的产品 invariant，且有 HTTP 端点对应，优先转可移植 |
| `test_v2_store.py` | 17 | **A** | 原子性 / 幂等 / 路径冲突 |
| `session-model.test.mjs` | 13 | **B** | 前端纯函数 |
| `dashboard-v1.test.mjs` | 10 | **C** | 旧 Pipeline 合成 Vault 扫描，与 PAOS 核心无关 |
| `test_plugin_registry.py` | 4 | **B** | 插件契约，较新 |

**分布估计**：A 类约 200–240 项；B/C 类约 68 项（前端为主）；**当前可跨实现复用的 HTTP oracle 约 60 项**。

> 投入少量工作把 A 类中"有 HTTP 端点"的部分（窄写合同、Session 生命周期）改写为黑盒测试，
> 可把可移植 conformance 提升到约 **80–100 项**——这是 Clean-room 重建实验的前置条件。

---

## 7. 清理后应该留下什么

不是"更少的测试"，而是：

```text
一条 A 类测试 = 一条仍然成立的产品约束
                 + 它成立的前提（precondition）
                 + 它的来源（origin）
                 + 它是否可跨实现验证（portable?）
```

当这套信息齐全时，删测试就不再靠勇气，而靠判据：**precondition 不成立，invariant 自然退役。**

---

> [!warning]
> D 类测试是本文存在的理由。它们看起来最像"有用的测试"，实际在保护已经死掉的约束。
> 识别它们的唯一方法，是把每条测试守护的约束**和当前产品合同逐条比对**——
> 而不是看它是否通过。**通过的测试，也可能是错的测试。**

> [!abstract]
> 测试的价值不来自数量，而来自它守护的约束是否仍然成立。分类（A/B/C/D）给出判据，
> Precondition 给出退役条件，可移植分层给出长期价值。清理的目标不是减少测试，
> 是让每一条留下的测试都能回答：它在保护什么，以及它什么时候该退场。
