---
schema: paos-workflow/v1
id: guide-v12-installed-release
title: V1.2 已安装版本与采用
description: 当前安装入口、恢复方式和成员采用要求。
tags: paos, release, adoption
status: historical
version: 6
---

# V1.2 当前安装

> **退役为 V1.2 安装快照（历史保留）**：生产现行为 **V1.3 已审采用**（版本/指纹以 `paos health` 实时输出与唯一 `RELEASE-MANIFEST-V13.json` 为准）。本快照保留完整使用历史与恢复对照，不再作为现行说明；升级至 V1.3 的采用说明见 [升级与采用](../../Guides/guide-upgrade-adoption.md)。

Stage3 与 w060 已正式验收；s014 保留由 s009 跟进的人工采用例外。当前业务责任继续，不新建升级 Work，不重新申请任期或接班许可。

## 当前版本从哪里读

`paos health` 的 `build.source_commit` 标识已启动的服务。`paos install show` 给出正在使用的 Source 与 Library 路径；在对应仓库运行 `git rev-parse HEAD` 查看当前CLI源码和方法库提交。服务版本与磁盘上的提交分别记录，不能互相代替。改动怎样收口见[升级与采用](../../Guides/guide-upgrade-adoption.md#统一采用的完成标准)。

## Stage 3 验收基线

下表保留Stage 3及其窄修的验收记录，不作为后续安装的实时版本表。

| 发布项 | 已验收版本 |
| --- | --- |
| 已审 Source | e4f0189bd04a9a48b5594d4c000611e97cc75ad4 |
| 初次合并 Source | 819b642ee7ec6378c72694bc6645c16ef538f517（与 e4 候选代码树一致） |
| 已审窄修 / PR115 | ca2660002dcf47c059fb5f41b7378aadeb634eb3；s029 独审及 Rooter Windows 受影响检查各 10/10 |
| PR115 合并 | 82959713ec567a32a1183abb618f3767b2be400e（与 PR115 候选代码树一致） |
| 已审窄修 / PR116 | 384f8d0f7154bd52aee7a1fba57886b089830c28；Rooter Windows 23/23，s029 WSL 独审 PASS |
| Stage 3 收口 Source | de27c07cb80c09e6066ae8cd6d9204aca58b7f91（与 PR116 候选代码树一致） |
| 已审 Library 基线 | b55c5c53076ae12b41fe8fd335542c486ee19f49 |
| 安装调整 | 本页、实际入口、由生产使用记录重建的 Catalog；不改产品代码 |

安装描述：Windows `C:/Users/remo/.paos/installation.json`；WSL `/mnt/c/Users/remo/.paos/installation.json`。共用一份文件，Source 位于正式发布 checkout。连接地址由安装入口提供。

PR115 让 `orient` 先给出 live Work 和可信 TODO 的下一步，旧 Request 仅显示相关性提醒。PR116 让 Windows 与 WSL 的 OpenCode Wake 使用同一实际状态目录；六个现有绑定已经从两端读到同一目录和已有记录。历史公告中的版本保留为发送时事实，当前运行版本以 `health` 为准；无需重复采用公告或重新入场。

## 忘了怎样继续

读本人工位 `ENTRY.md` → `TODO.md` 当前区 → `orient`。Windows 现有窗口的 PATH 可能尚未刷新，直接使用下面的完整入口。WSL 使用已安装的 `paos`，未载入登录环境时用 `/home/remo/.local/bin/paos`。

Windows（把示例身份替换为本人）：

```powershell
& 'C:\Users\remo\.paos\bin\paos.cmd' orient 3002 3002-s027
& 'C:\Users\remo\.paos\bin\paos.cmd' inbox 3002 3002-s027
& 'C:\Users\remo\.paos\bin\paos.cmd' peers 3002 3002-s027
& 'C:\Users\remo\.paos\bin\paos.cmd' status 3002 3002-s027
```

WSL：

```sh
/home/remo/.local/bin/paos orient 2001 2001-s021
/home/remo/.local/bin/paos inbox 2001 2001-s021
/home/remo/.local/bin/paos status 2001 2001-s021
```

`health` 查看运行 Source；`install show` 查看安装配置；参数用 `--help` 或 `<子命令> --help`，当前没有 `paos help` 子命令。具体操作读 [PAOS/CAT 指南](../../Guides/guide-paos-cat-operations.md)。不用查源码来回复消息。

## 自行采用

1. 确认本人身份、正式责任和当前 TODO 相符；把过期等待移出当前区，把长过程稿放 Project Works 后链接回来。
2. 在 TEAM 本人小节确认 Harness、联系方式、工位和 TODO；运行状态由 CLI 派生，不手抄一份。
3. 继续已有可执行事项。待机成员核入口和联系即可；pending_ack 成员由本人决定正确入场并作证，Rooter 不代 Ack。
4. 给 Coordinator 持久回报实际动作、产物位置和剩余问题。交接时核下一位消费并开工；有可执行责任就继续，没有新邮件不等于任务结束。

需要下一位接续：

```sh
paos agent send 3002 --to 3002-s029 --sender-kind agent --sender-id 3002-s027 --message-id <本次稳定消息ID> --subject "交付接续" --body @<已落盘成果说明>
paos agent notify 3002 --mail <已送达消息ID> --agent 3002-s029
paos status 3002 3002-s027 --message-id <本次稳定消息ID>
paos session report 3002 3002-s027 --summary "实际进展"
```

`mail send/reply` 只落信，不自动唤醒；`agent send/notify` 使用既有绑定激活。`woken`、送达和已处理各有含义，最终看实际产物与接受。遇 uncertain，先查同一封信及实际产物，不重复副作用。

## 当前联系边界

OpenCode 服务已统一到 1.18.33，保留原生会话与当前模型选择；自动调用省略 model。Codex Wake 使用既有原生线程。跨 Runtime 调用若缺 Codex app-tools 原生入口，读面应明确人工路径，不能复制别人的调用者身份。

s014 为 WorkBuddy 人工入口；待机或人工未接入如实回报。OpenCode 打开现有会话的端口与命令读 TEAM。Rooter 不创建 Project Session：安装问题交 rooter-001，项目责任交 s009/s010，产品语义问题交 3002。

## 故障与恢复

报告命令、当前身份、真实错误和已保存成果，不先造 Work 或新会话。Rooter 的同一恢复点为 `PAOS-Rooter/rooter-001/restore-points/V12-STAGE3-20261001-183554`；只撤销本次变更，保留切换后业务成果。该恢复点的 `rooter-home` 子目录因递归复制错误标为 INVALID，禁止用它回退；以 SNAPSHOT.json 指定的有效部分为准。

生产部署、本人采用、下游交付和 Coordinator 接受分别记录，尚未完成的采用不写成 PASS。
