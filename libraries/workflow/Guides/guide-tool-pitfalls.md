---
schema: paos-workflow/v1
id: guide-tool-pitfalls
title: 工具行为陷阱：按工具与操作检索
description: 按工具/操作查已记录的时间、版本、现象与处理动作；不把单次版本现象外推成普遍定律。
tags: tools, pitfalls, feishu, cli, verification
status: active
version: 4
---

# 工具行为陷阱

按工具或操作查已知陷阱，不按项目故事重述。每条只写已有时间、版本、现象和动作；单次版本/单次操作的现象不外推为整个工具或所有版本的限制。详细飞书行为以[共享 feishu-cli references](../../skill/feishu-cli/SKILL.md)为准，本页只做可检索薄入口。

| 工具 / 操作 | 已记录现象（时间/版本） | 动作 | 来源 |
| --- | --- | --- | --- |
| `lark-cli docs +update --content @file` | 源记录 2026-09-26：只接受当前目录相对路径；该条未把版本写成当前 1.0.70 | 先 `cd` 到文件所在目录，再传相对 `@file`；不把某次限制外推成所有工具 `--file` 都禁用绝对路径 | [writing-and-block-ops·写入纪律](../../skill/feishu-cli/references/writing-and-block-ops.md#写入纪律) |
| `lark-cli docs +media-insert --file` | 源记录 2026-09-18：只接受当前目录相对路径；该条未把版本写成当前 1.0.70 | 同次 `cd` 后用 `./file`；先确认输入、再回读插入结果 | [writing-and-block-ops·媒体（图片 / 视频 / 文件）](../../skill/feishu-cli/references/writing-and-block-ops.md#媒体图片--视频--文件) |
| 飞书 XML 媒体块 `<source src="…">` | Human 2026-10-28 转交的失败报告称 schema 校验不通过；S014 明确自己未提交 `src`，其原件只证明 `token` 路径 | 写入前取目标 `<figure>` 顶级块 id，媒体用 `token` 语义；写后回读属性名与播放器/结构。只作报告风险，不写成平台定律 | [Human 输入](C:/Users/remo/Desktop/agent学习计划/PAOS-Projects/3002-Personal-Agent-OS/Works/WORKFLOW-REUSE-FRICTION-20261028/INPUT-HUMAN.md) |
| `docs +media-insert --selection-with-ellipsis` | 1.0.70，2026-10-28 S014 一次操作指定“前空翻”时视频落到加粗引导段之前；未独立复现原因，不能据此断言所有跨加粗匹配都失败 | 用已有目标块或实际唯一图注作锚点，不为工具方便新造正文段；写后回读块顺序和内容，不只看 `ok` | [S014 来源](C:/Users/remo/Desktop/agent学习计划/PAOS-Projects/3002-Personal-Agent-OS/Works/WORKFLOW-REUSE-FRICTION-20261028/SOURCE-S014.md) · [writing-and-block-ops·媒体（图片 / 视频 / 文件）](../../skill/feishu-cli/references/writing-and-block-ops.md#媒体图片--视频--文件) |
| `str_replace` 富文本链接匹配 | 2026-09-26 记录：富文本链接导致纯文本匹配 0 处但返回 `ok`；这是该次匹配范围的记录，不是所有跨节点替换 | 先局部 `fetch` 取目标块；改后核目标文本与结构，不只凭 `ok` | [reading-and-verification](../../skill/feishu-cli/references/reading-and-verification.md#验证) |
| `block_replace` + `<table>` | 2026-10-27 有“单元格替换返回 ok 但未生效”的相邻记录；整表重写副作用无原始失败件 | 替换前后各 `+fetch` 一次，核对目标位置、表数、表内容和新的 block id，确认旧表不残留；没有原件时只写风险，不宣称普遍行为 | [S014 来源](C:/Users/remo/Desktop/agent学习计划/PAOS-Projects/3002-Personal-Agent-OS/Works/WORKFLOW-REUSE-FRICTION-20261028/SOURCE-S014.md) · [writing-and-block-ops](../../skill/feishu-cli/references/writing-and-block-ops.md#搬块--改块) |
| 列表末条 `li` 作锚点 | 无原始失败件；最接近的是标题锚点替换吃掉下一节（日期未记） | 取已有目标 `li` 的 block id；改原条目用显式 `block_replace` 并核原文未丢；仅在原有编号列表需要时保留 `seq`/`seq-marker`，不强制所有列表编号 | [S014 来源](C:/Users/remo/Desktop/agent学习计划/PAOS-Projects/3002-Personal-Agent-OS/Works/WORKFLOW-REUSE-FRICTION-20261028/SOURCE-S014.md) · [writing-and-block-ops](../../skill/feishu-cli/references/writing-and-block-ops.md#搬块--改块) |

## 基本动作区分

新增内容用插入语义（如 `block_insert_after`）；改原内容才用替换。不要用“替换”锚点顺手吞掉原项，也不要用插入结果冒充原内容已更新。任何写后都以云端回读的 revision、块结构和目标文本为准。
