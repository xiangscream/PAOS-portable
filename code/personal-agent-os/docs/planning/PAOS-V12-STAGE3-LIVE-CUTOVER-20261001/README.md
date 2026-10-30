# V1.2 FINAL / STAGE 3 RESULT

**统一生产安装与真实跨 Agent 交付已经成立，PR116 的跨 Windows/WSL 状态路径修复也已上线。** s009、s010 已实际消费当前实证并纳入各自唯一 RESULT；w060 已由 s010 正式验收为 done，s014 保留人工采用例外。

## 已实际落地

- Source：已审 e4 → 合并819；PR115 已审 ca26600 → 合并829；PR116 已审384f8d0 → 合并/运行 **de27c07**。每组候选/合并代码树相同；两端已安装 CLI 与运行服务版本一致。
- Library：已审 b55 → 安装 **ed32316**。指南、TODO模板及 Catalog 已随安装校准，原使用事件1/1字节保留。可复现增量见 [Library patch](installed-library-calibration.patch)。
- 六个 OpenCode 服务1.18.33、九个自动 Wake 绑定、五个 CAT 消费者沿既有原生会话和固定工位采用。模型选择保持不变。六个 OpenCode 绑定在 Windows/WSL 指向同一真实目录并读取相同已有记录。
- 十份成员 TODO 均为可信 v2，TEAM 连接本人 ENTRY/TODO。3002五人与2001四人有本人采用事实，s023 自行完成入场确认。
- s027真实产物 → s029独审 → s010接受已闭合。s031通过本人正式审批入口解决 Mail 写入失败，报告实际被s010消费，本人已处理来信。
- s010 最终完成通知已由 s027/s029/s031 实际消费，三份当前页均移除旧验收等待；s031正式进展为 done、成员仍 active。见 [接收者最终状态](FINAL-MEMBER-CONSUMPTION.json)。
- 八个非活动 Project 已 closed 并退出自动运行，原文件、责任与共享引用保留；旧两个 CAT participant 无运行消费者。
- 旧候选 PR111/112/113 已由 Rooter 正常关闭并保留历史。PR112 的 instance/write-owner 路线明确标为后续设计放弃，关闭不等于旧代码原样吸收。

## 剩余责任与限制

1. 两位 Coordinator 已接受当前安装结果；w060 已于 revision804/event3002-e784 正式转为 done。成员 Session 保持 active，完成 Work 不以员工离场为前提。
2. s014 的 WorkBuddy 为人工入口，公告已送达、本人未确认；保留 w043 待机责任与后续本人采用，不安排假工作。
3. 历史中文 message_id 的处理标记问题、INVALID 临时备份、既有未提交业务文件明确保留。有效恢复范围见 [恢复点说明](RESTORE-SNAPSHOT.json)，不能用 INVALID rooter-home 回退。
4. CLI 仍有明确缺口：Project 现状摘要写入与归档仍依赖已有 HTTP 合同，收口时 s010 再次查源码确认接口。这项作为产品债务交主线；本次已把常用 Work 验收命令补进共享指南，不宣称所有治理动作都已有日常 CLI。

此前 s010 资源停点已恢复，其已实际接受并合并 PR116。原失败证据保留为历史，不再当当前阻碍。

s010 在正式验收和发出收口通知后又遇到模型容量不足，具体错误见 [原生错误记录](S010-CAPACITY-ERROR.json)。已落账验收及成果不撤销，Rooter 接续机械收尾，未更换其模型。

## 给网页主线的实际教训

本次落地暴露的消耗来自几类不同问题：生产服务未随候选统一采用；Windows/WSL 对路径的解释不同；Runtime 沙箱写权限与 PAOS 业务权限混淆；当前 TODO 被旧等待和历史叙述污染；资源额度终止打断接续。修复应按实际根因处理，不能全部归为“Agent 不主动”，也不能只用更长的员工手册代替安装采用。

已做的软改进是共享入口与版本事实集中、当前页写后从生产 orient 回读、长记录归 Works、缺少消费证据时才做有界检查，以及 Coordinator 暂时不可用时继续独立授权内事项。接续完成仍以真实产物和下游接受为准。

**撤回“Stage3 额外 Human 催办为0”。** 聊天中有多次“继续”，尚未逐条区分例行续接和意外停顿催办；未完成分类前不填0。Stage2至少2次保留。当前短时链不证明长期无人监督稳定。

## 证据入口

- [安装回读及现场摩擦](READBACK.md)、[当前安装清单](INSTALLATION-MANIFEST.json)、[十份成员当前页](CURRENT-MEMBER-READBACK.json)。
- [3002 Coordinator RESULT](COORDINATOR-3002-RESULT.md)、[2001 Coordinator RESULT](COORDINATOR-2001-RESULT.md)、[生产独审](S029-PRODUCTION-HANDOFF-REVIEW.md)。
- [PR116 Windows 23/23 原输出](PR116-384-WINDOWS-FOCUSED-ORIGINAL.txt)、[新 exact 独审](PR116-384-S029-INDEPENDENT-REVIEW.md)、[生产双环境路径实证](PR116-PRODUCTION-SHARED-STATE-PROOF.json)。早期两项 Windows 失败原输出继续保留。
- [当前安装交回 s010](DE27-PRODUCTION-RETURN.md)、[交回 s009](2001-FINAL-INSTALLATION-RETURN.md)。
- visible-terminal-original/ 保存原生可见终端错误和权限元数据；不含推理内容、凭据或整个私人 Store/Mailbox。

完整 verifier 采用已接受的 e4 Windows 7/7；后续两次窄修核各自受影响部分，不将 WSL 结果冒充 Windows 结果。本包的状态目录证据为只读路径/已有文件回读，没有声称新增跨宿主并发锁实验。

[正式 Work 完成回执](W060-DONE-RECEIPT.json)记录真实状态转移；[排队接续样本](COORDINATOR-QUEUED-CONTINUATION.json)记录前回合结束约一秒后既有 Wake 启动下一回合。Rooter 曾误判为停链并多发提醒，已纠正，不能把该样本写成“需要人工提醒才恢复”。
