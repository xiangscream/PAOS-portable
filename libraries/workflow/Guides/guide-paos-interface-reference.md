---
schema: paos-workflow/v1
id: guide-paos-interface-reference
title: PAOS 接口参考：本地工位、项目登记与方法库
description: Agent 无 Core HTTP 运行的本地入口；内容维护走原文件，不另建项目概览。
tags: paos, interface, reference, cli
status: active
version: 23
---

# PAOS 接口参考

本页对应 Portable 的文件直连 CLI。安装位置由 `--installation-file` 或
`PAOS_INSTALLATION_FILE` 决定；参数以同版 `--help` 为准。无需启动旧 Core。

## Home 读面

`orient <project> <home>` 读取身份、ENTRY、当前 TODO 与待处理 Mail。
`attention show <project> <home>` 读 Home 的 Current、Tasks 和 Notice；
Rooter 使用 `attention rooter-show`。`inbox` 给待处理优先的 Mail 短表，
`mail list/read` 展开原件。读取不等于输入已处理。

TODO 写入仍走 `attention todo-update/todo-write`；本片保留 v3 格式。
`attention takeover` 把一条 Mail 输入接到当前工作，随后 `attention handle`
记录具体处理结果。没有新增原始要求、项目概览或全局待办表。

## 项目与当前口径

`project show <project>` 只读登记身份、位置、Coordinator 和成员 ID。
项目最新口径是 Project Vault 中**一篇现有正文**，从 ENTRY/INDEX 或 TODO
的 `alignment_ref` 找到后直接读写；不强制新文件名，不复制到 Project JSON。

任务要求用 TODO 的当前目标/范围与原输入引用表达；需要持续注意的内容可在
后续工位格式收敛时作为置顶。当前 v3 解析器尚未支持任意自由置顶正文。

## Project 经验（只读）

`project experience <project>` 原样读取该项目 `Materials/TIPS.md`。
缺失就返回具体错误，不造空模板。普通项目经验用文件/Git维护，提炼是否进入
方法库由处理 Agent 按实际复用价值判断。

## Library 资源检索

`library search <query> [--kind workflow|skill|all]` 复用本地检索器，读取登记库，
不访问 Core。结果指回源文件；找到后再实读必要正文。
`library catalog` 重建派生索引，保留原始使用事件；`library skill-use` 记录使用。

## Tool 目录（只读）

`library tools` 读取已登记 Tool Catalog 的完整 Markdown。
工具目录说明用途，不能证明新机器已安装或在线。

## 安装数据根与程序根

`install show/configure` 沿既有安装描述定位 source_root、data_root 与 Libraries。
`health` 检查本机安装定位；`runtime_verified: false` 不会被改成在线声明。
换机重新建立本机 Contact；`wake bind` 必须显式提供本机 native session。

## 联系与运行

`peers/team` 查本地名册；`status` 组合本人工位与 Contact，不另维护进度。
`agent send --remind` 保留 Mail、Notice，然后显式提醒一次；结果未知不重投。
`wake status/bind/unbind/trigger` 沿既有适配器运行。`cat` 直接访问独立 CAT 服务，
只有这些明确需要外部运行的操作才使用对应传输。

## 已退出的入口

旧 `session`/`coordinator` 生命周期代理、`home`/`ports`/`relations`/`needs-me`、
`workbench`、`tips` HTTP 接口、`project progress-update/outcomes/acceptance-check`、
`install plan/homes/rollback` 和 Core 连接配置不再出现在本片 CLI。
不是空成功，也不保留“兼容命令”。原始历史不因入口退役而删除。

Tips 原件、引用、范例继续保留；其日常整理走
[日常输入整理](../Workflows/wf-meeting-audio-package.md)，不是重新建立旧 Tips 状态服务。
