---
schema: paos-workflow/v1
id: guide-project-work-world
title: Project 文件与 Git
description: 成果归项目、当前入口清楚、历史可读，文本版本使用现有 Git。
tags: project, files, git, current
status: active
version: 11
---

# Project 文件与 Git

项目文件承载正文、输入、判断与成果；PAOS 保存正式责任与验收。文件整理服务下一位读者，不要求完整归档仪式。

## 放在哪里

| 内容 | 正常位置 |
| --- | --- |
| 当前正文、分析、复核、交付 | Project 的 Works / Decisions 或已有对应目录 |
| 常用外部输入快照 | Materials，说明来源、版本与是否仍权威 |
| 外部 live 飞书、共享源码/资料 | INDEX/成果中的直接引用，不冒充可写副本 |
| 本人 ENTRY / TODO / Mail / 可选笔记 | 固定 Workstation |
| 工具绑定、缓存、原生聊天 | Runtime/安装配置，不混进正文 |
| 被取代的版本 | 原位历史标记或 Archive，退出当前导航 |

PROJECT 根的 INDEX 指当前正文，TEAM 指当前同事。目录按真实用途建，不为模板创建空树。Working Memory 有用内容成为普通文件；同一结论已经在报告里就引用它。

## 当前页与历史

本人负责自己的当前入口。替换文稿时更新 INDEX/成果引用，让旧稿退出 current；长过程从 TODO 移到已有报告或历史。无法判断哪个正文生效时找 Coordinator，不按文件名或修改时间猜。

Project根的HISTORY是完成项短索引，每项只留日期、负责人、结果和原件链接，例如“2026-10-14 · S043 · 排程已接受 · 结果文件链接”。共同成果引用同一份，个人只补新的发现；不在索引重写完整过程、参数和工具回执。历史过长时，把已完成记录移到Archive，保留旧定位与原件链接；工位ENTRY直链同一历史入口，按当前任务定位。

正式状态在 PAOS，TODO 解释自己准备怎么继续。checkbox 完成不代表验收；提交记录不代表业务已接受。参考快照注明来源即可，不给普通资料增加逐文件哈希和必填 provenance 账本。

每个独立交付阶段保留审阅时原文、必要交付回执和移动恢复映射；常规 Current 写入不逐次另存 TODO 全文、指纹或目录快照，异常时保留对应现场。同类已定用途资料按实际用途合批，复用现有阅读与恢复入口。

### 日常顺手维护

成果创建时选已有 Project/主题落点；下载或外部导出成为有效输入时，采用者同步归位或登记稳定原件链接。版本被替代时退出当前导航；交付或接受时更新必要引用、Current 和完成历史。维护范围围绕本次实际创建、采用、替换和交接的资料；明确的小问题当场处理，跨职责取舍交具体 Owner 并保留接续。日常归位沿已有权限直接做，不逐件等 Rooter 验收。

## 准则登记与退役

会指导 Agent 行为的文件必须能从现有入口找到：Project 规则登记在 INDEX 的当前入口；Workflow / Skill 以既有元数据登记进各自 Catalog。登记只说明主题、现行路径及适用范围，不复制正文，不另建登记系统。普通草稿、原始输入和个人临时笔记无需登记成规则。

一个主题只维护一份现行准则。工位、AGENTS、模板与其他指南只链接对应章节；环境差异在同一准则内说明，不复制一本。修改规则时，沿登记入口和旧名称、路径、关键术语检查引用它的 Project、Workflow、Skill 与实际 Harness 入口，一起处理被替代的口径。

迁移或退出旧路径时，同时核文本导航和受影响 Project 的 `project outcomes --full`：已登记成果若当前 Artifact 仍指向旧路径，由原 Owner 用现有 `session artifact-add --replaces` 追加新版并保留旧链；普通未登记文件照常归位。登记未完成时写清具体 Artifact 与下一负责人，不因正文/导航已改就称全部引用闭环。

被取代的正文移出 current：有追溯价值的放 Archive 或使用 Git 固定版本链接，必要旧路径仅留指向现行来源的短导航。历史材料标明历史，不继续自称“当前/唯一合同”；有效证据与原始日志保持原样。能从 Git 恢复的重复副本无需再堆一份归档。

升级收口在原有交付记录写清现行来源、退出的旧入口和剩余例外，并从实际入场路径回读；不增加独立审批或每人一份自查报告。Workflow / Skill 源文件变化后重建 Catalog，保留使用记录。若两份内容是否仍有效涉及项目判断，交 Coordinator 确定；确定后的引用与归档清理由维护者完成。

## 项目文本 Git

2001/3002 的正文、INDEX、TEAM、工位 ENTRY/TODO、项目规则可进入本地 Git。Source 与 Library 保持独立仓库，不嵌成同一份历史。

四层仓库边界：Project Vault（项目事实/文档/成果，项目自身 repo，Source 目录在其中为被排除的嵌套独立 repo）、Source（产品代码，PR 流程）、PAOS-Libraries（Workflow/Skill 方法层，独立 repo）、Rooter Home（安装治理与 restore-points，不属项目 Git）。回退路径 = 所在层 repo 历史为准，restore-points 仅安装级回退点；跨层回退（如 Source 与 Library 版本配对）以共享安装说明的登记为准。跨 WSL/Windows 读同一 repo 的 git 状态可能因行尾配置产生整文件伪差异：以 Windows 侧实读为准或先统一 eol，不要据伪差异断言他人改动。

排除 private-data、运行绑定、缓存、密钥配置、大媒体与原生聊天；Workstation mailbox/log 是否跟踪按安装隐私与真实恢复用途决定，不把整棵 Runtime 目录收进 Git。共享目录提交前读差异，只提交自己负责的路径或 hunk，不用 `git add .` 带走同事修改。提交时区分本轮自己负责的成果与入口，不混入同事或先前批准范围外的改动。

Git 域按明确授权的项目边界与居民协议固定；同一仓库被多个工作树（含 Windows/WSL 混宿）共用时，登记修复只由实际归属 Git 宿主执行，不跨宿主 `worktree add/prune`，不删对方 `.git` 指针；误损先报告原宿主维护者并回执修复。

在有意义的进展或交付处提交，给出做了什么。冲突查看双方新内容再合并；不会处理时请同事一起解决，不整文件覆盖。Git 提供版本、差异和恢复，不手抄 Git log，也不能回滚飞书的外部写入。

## Project 经验原件

Project 自己的经验默认归 `<登记根>/Materials/TIPS.md`：普通 UTF-8 Markdown，由 Owner 通过正常文件/Git 维护，记录实际场景、做法/结论、依据与适用范围，用明确标题或锚点定位条目。它是该项目经验的唯一读取入口；没有经验不凑条数。已有其它经验文档不自动搬迁或合并，Owner 可在入口指向真实原件，读者自行打开。

只读回用：工作台“Project经验”区域按需读取，或 `paos project experience <project_id>`（同一 `GET /api/projects/<id>/experience`）。返回位置、原字节 SHA-256、字节数、观察时间与完整正文；不写文件、不建目录/模板、不跟随文档内链接，也不把 SHA 当业务接受。文件缺失时明确“尚未建立”，不在旧 root、Inbox、Library 或相似文件里猜替代源。安装级 Tips 的 `project` 是自由文本，不能当 Project ID 或替代本文件。

多人修改沿原 Project 文件/Git 协作，出现差异由作者合并，不能最后写者覆盖他人；Core 不提供写锁或跨文件事务。

## 历史方法

[V1.2 转换与回退演练](../Archive/2026-10-12/v12-conversion-recovery-drill.md)仅供按需追溯；当前工作沿本次授权和现行安装入口继续。

## 归档与边界

Coordinator 判断项目内容与团队责任，Rooter处理安装、跨项目运行与旧项目退出。Human 明确保留的主稿或方向取舍仍遵循其要求。普通成果归位和个人当前页维护无需逐文件审批。

旧 Project 退出 active/自动运行时保留历史与引用；2001/3002 仍使用的共享资料原位保留。归档不改历史责任状态，不重新 onboarding 历史成员，不为目录整齐搬整个 Vault。
