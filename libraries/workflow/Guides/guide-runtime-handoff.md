---
schema: paos-workflow/v1
id: guide-runtime-handoff
title: Runtime 接班与在途外部写入
description: 换会话保持责任与成果连续，明确外部副作用的完成、停止或接管。
tags: runtime, handoff, external-write
status: active
version: 10
---

# Runtime 接班与在途外部写入

消息唤醒后恢复的是员工已有责任，不是只完成一次收件动作。Runtime 提示应引导读取固定 ENTRY/TODO、处理消息、继续未完成且可执行的主线；只有没有后续责任、真实等待或阻碍才结束。不得用“只处理本次消息”把已经授权的原任务变成无关任务。

同一会话压缩后，按[工作循环·恢复](../Workflows/wf-agent-work-cycle.md#恢复)从固定ENTRY实际读取指南、Current与当前原件。orient用于定位。

需要新会话时，由Human或已获授权的维护者沿当前Harness支持的入口创建Runtime，提供长期Agent ID、Project和固定ENTRY，绑定原成员。模型沿原设置；有明确变更授权时使用指定模型。

## OpenCode原会话压缩

压缩时机沿[工作循环](../Workflows/wf-agent-work-cycle.md#阶段与职责重读)。使用当前登记的服务、sessionID和实际目录。首次使用或版本变化时核同版CLI/OpenAPI；当前API v2用`session.compact`，不是v1的`summarize`。

1. 本人保存Current、当前原输入、成果和在途写入状态，明确由谁执行压缩。维护者收到保存结果后接着操作，不再等本人自行压缩。
2. 维护者核原session的运行与待处理输入，在工具完成点执行`opencode api session.compact --param sessionID=<原ID> --data '{}'`。该操作沿原会话模型；已运行的任务在下一安全点处理，不停止共享server。
3. 返回受理只表示请求入队。核`session.compaction.ended`事件或原生context中的压缩消息完成；失败查原错误，回执不明先查原请求，不重复提交。
4. 沿既有Mail/Contact交还一次，给出固定ENTRY、必要指南、Current及本批原件的准确路径。本人实际重读正文，以当前页和成果纠正摘要中的旧目标、旧等待，再做下一项可执行动作；只有真实依赖才等待。
5. 核本人当前页和实际接续后收口。原历史仍由Harness保留，不为压缩复制全量聊天或另建一套交接台账。

接口说明见[OpenCode V2压缩](https://dev.opencode.ai/v2/docs/compaction/)及[API参考](https://dev.opencode.ai/v2/docs/api)。同版参数以实际安装为准。

## 交给下一任什么

切换前，将本人Current与最近的Human指令、原Runtime最近成果对齐，补全岗位主线、资料入口和未完责任；Current过时就先校准。保留必要原话和资产路径，已有脚本、模板与台账优先复用原件。

当前 TODO 留：真实责任与目标、做到哪、下一步、等谁、成果入口、在途动作。成果已有交付说明就链接它，不另写同义 Memory/Handoff。长期知识在普通 Project 文件，个人 notes 可选。

交班前明确负责切换的维护者。交班人保存下一项真实未完动作，沿既有Mail/Contact交给该维护者，再结束旧执行。维护者核该次调用、工具及相关外部写入的实际状态，再切换同一Home并提醒一次；Coordinator无需重复中转。交还后不再向旧Runtime派同一份主体任务。

新Runtime实读工位入口和当前原件，完成下一动作，由下游实际接住后记接班完成。创建、绑定或提醒受理各自只表示对应操作完成。已有成果、责任和同事关系继续沿用；原子提交、revision冲突与幂等继续保护事实一致性。

## 只有跨回合的外部修改需要交代

启动可能在本轮结束后继续改飞书、文件或其他外部目标的进程前，记录：

- 写入目标与当前基线/版本；
- 进程、脚本或任务入口，以及停止方法；
- 控制人、结果/回执查看位置；
- 任务范围和预期结束条件。

普通同步命令和只读操作不登记任务对象，PAOS不扫描整台电脑。旧 PAOS 写入绑定失效不代表旧 Python 进程停止。

## 交接结论

只能明确写：已完成并核对结果；已停止并核对目标；仍在进行且由谁明确接管。状态未知就保留未知和最后可核结果，不用“本轮未编辑”掩盖上轮未决副作用。

接手人先确认真实进程/任务与外部 revision，再决定继续、停止或修复；不盲接最后 block 序号，不与旧进程并发修改同一目标。停止需用该任务已知的精确入口，不能为了清理杀无关进程。

批量外部写入先读清参数语义，限定范围；“每批数量”不等于总批数。外部结果验收与内容含义分别判断，Git 或 PAOS receipt 不能自动回滚外部文档。
