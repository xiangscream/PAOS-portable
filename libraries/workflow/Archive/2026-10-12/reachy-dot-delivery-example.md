---
schema: paos-workflow/v1
id: historical-reachy-dot-delivery-example
title: Reachy与DOT交付案例（2026年10月）
description: 历史实际交付与故障记录，不作为当前联系参数或运行状态。
tags: historical, research, delivery
status: historical
version: 1
---

### 已完成通用例：S036 Reachy 研究（区分三条通道）

同一类「请网页同事研究」按通道走不同链，以 S036 已接受的 Reachy 玩法研究为实例（原件：`PAOS-Rooter/rooter-001/reports/DOT-CONTACT-20261007/DOT-REACHY-S036-ACCEPTANCE-20261009.md`、`DOT-REACHY-DELIVERY-20261009.json`、`REACHY-DOT-TEAM-RUN-CARD-20261009.md`；下游执行状态 `Works/DOT-COLLABORATION-20261006/DOT-EXECUTOR-SETUP-20261009-0908-READBACK-20261010.md`）：

- **委派任务通道（本例实际成功路径）**：以稳定委派任务 thread（本例 `01a11f5b-e32e-7668-a021-649164a3e021`）承载完整材料（问题/Brief：`Works/3003-w012/DOT-REQUEST.md`、`BRIEF.md`）；真实往返按 Run Card 原件描述 = 保存方（Rooter）`send_message_to_thread` → 原委派执行会话 → DOT `cloud_threads.read` / `send_message`，**没有公开可复用的 task API**，不声称/照抄 `send_message_to_task`；产物为固定路径原件（本例 `DOT-SEARCH.md` 36066 字节、SHA `8016f531…`，附 `DOT-REACHY-DELIVERY-20261009.json` 回执）由保存方核字节数/哈希后落盘。任务/线程 ID 是一次性处理标识，不是长期公共地址。
- **本人消费与收口（区分于 *保存即完成*）**：研究原件保存不等于完成；本例由 Reachy 稳定 Home `3003-s001`（员工号 S036）本人原答完成实际消费——完整读取 `DOT-SEARCH.md` 全文与结果 Mail、独立 HTTP 核 7 份来源、更新 `APPLICATIONS.md` 七组新增与三构想、核验落 `DOT-REVIEW.md`、TODO/Mail incorporated，Rooter 复核原件后收口（acceptance 已回原 DOT 链）。Run Card 早段「待 Coordinator 实读」的旧等待字样已被 acceptance 之后的真实结果取代，不引用旧等待作案例。
- **普通 Chat 研究通道**：用下方「直接普通 Chat 研究」五链（list_threads→send_message_to_thread→read_thread…）；研究与委派任务各自成链，普通 Chat 不替代委派任务，也不替本人收件箱做消费。
- **当前执行通道故障事实（如实报）**：原任务线程在创建进程阶段曾报 `helper_unknown_error`；最新 readback（2026-10-10）记录「普通执行已恢复，原任务实时 inbox 读取尚未恢复验收，原因未定」——CLI 原 inbox 调用曾遇 `WinError 10013`（executor 路径）与原线程 `MCP error -32000`；这些失败**不代表模型/工程不可用**，也不要把恢复写成自动可用；恢复前沿委派保存方人工接续，验证后另行更新。
