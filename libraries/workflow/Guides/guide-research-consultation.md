---
schema: paos-workflow/v1
id: guide-research-consultation
title: 研究与咨询：蒻芷、普通Chat与接续
description: 按需读取：组织咨询输入、取回完整来源和接续网页研究。
tags: research, consultation, handoff
status: active
version: 3
---

# 研究与咨询

研究、广泛搜索和方案咨询主动复用蒻芷团队（稳定 Home `3002-s033`），节省 Work 额度；普通网页 Chat 按真实任务需要使用。提问者继续现场实施并负责采用判断，咨询答复是输入。

## 组织输入与回流

先在本人 Current 关联咨询事项、下一步及等待，长材料保存到 Project。向蒻芷现有持久邮箱交付具体问题、完整可读材料、事实/版本、预期成果、完成条件与 Project 回流位置；写清答复后由谁继续。

蒻芷的当前收信安排只读 Rooter 唯一 [CONTACT-STATE](C:/Users/remo/Desktop/agent学习计划/PAOS-Rooter/rooter-001/reports/DOT-CONTACT-20261007/CONTACT-STATE.md#当前联系安排)，发送参数见 [PAOS 操作指南](guide-paos-cat-operations.md)。同题只留一个在途请求，等待期间继续其他可执行工作，不重复催信。

收到答复后保存完整原文和来源，核下游实际读取并开始接续，再更新本人 Current；留信不等于接单，答复不等于采用。普通 Chat 须提供可读正文或真实附件，单给本地路径不等于提供了文件。

## 普通Chat研究

1. 在本人TODO关联研究事项，长材料放Project文件。
2. 从产品正常普通Chat入口新建或续原Chat，核实际类型与ID。Codex任务、Work或其fork不当作普通Chat。
3. 交完整问题和获准材料，要求原始来源；沿Human指定的模型/思考设置，不自行启Pro或换档。
4. 读回完整回答，截断就续读同一回复；发送受理或摘要不代原文。
5. 核影响判断的关键来源，保存原答复和采用结论，再沿工作循环交接。

有受支持的原生工具时，从实时工具metadata核调用签名。`list_threads`核类型/ID，`send_message_to_thread`提交，`read_thread`读同一回答；`wait_threads`只用于Codex线程。不要编造工具或借其他caller身份。

## 网页Chat接续

临近上下文上限时，可从较早完整回复分支，让原Chat生成可下载handoff。说明职责和边界，结构篇幅由协作者判断。补齐分支后的有效Human原话、决定、未决问题和成果引用。

原件留对应Project或Rooter资料位置。新Chat沿原设置接续，读完整答复并核职责理解，随后更新该主题入口和通知原协调者。handoff不代表逐字历史及全部附件已经恢复。

历史案例在 [Archive](../Archive/README.md)，当前联系操作见 [PAOS 操作指南](guide-paos-cat-operations.md)。
