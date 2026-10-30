---
schema: paos-workflow/v1
id: historical-v12-conversion-recovery-drill
title: V1.2 转换与回退演练（历史）
description: 从Project文件指南v5移出的原演练正文，按需追溯，不参与当前恢复。
tags: historical, conversion
status: historical
version: 1
---

来源：`Guides/guide-project-work-world.md` v5，Library `0204b078c172ddea156d4822df6d90a38de0edad`。以下保留原正文。

## V1.2 转换与回退演练

`paos_v12_convert.py` 的输出是**需要叠加的变更文件集，不是完整 Project Vault**。不能用输出目录替换现有项目目录。

1. 同一时间冻结 Project JSON 与整个 `Workstations/`，放入同一个只读 fixture；Project JSON 的 revision 和工位文件都要能代表同一输入时点。
2. 用 exact candidate 的 converter 对 fixture 执行 dry-run：

   ```text
   python <Source>/scripts/paos_v12_convert.py --project-json <fixture>/project.json --vault <fixture> --out <candidate-output> --json
   ```

   若当前 Runtime 的 Python 不在 PATH，使用该 Runtime 已配置的 Python 路径。先核 `errors`、Project JSON 不变和报告中的 Agent 清单；再逐份检查新 TODO 是否保留当前责任、等待、成果和本人 Ack 边界。`pending_ack` 只能保留为等待本人确认，转换不代表 Agent 已 Ack。
3. 构造隔离候选时，先完整复制 fixture，再把 converter 输出中相同相对路径的文件叠加进去。保留未被输出提及的 Project 和 Workstation 文件。
4. 演练回退时，对每份本轮生成的 `TODO.pre-v12.md` 将原字节恢复为同目录 `TODO.md`，删除本轮新增的备份文件，并恢复原始 `project.json`。逐项比较完整文件路径与内容，确认结果回到冻结输入；不要仅凭 `errors=[]` 宣布转换与回退通过。

上述转换步骤是 V1.2 历史演练方法，不是当前待办。未来转换先在副本演练，生产写入按该次升级的实际授权执行。

