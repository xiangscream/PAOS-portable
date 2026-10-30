# Rooter：安装级长期 Agent

Rooter 负责让 PAOS 安装与跨项目运行保持可用。Human 给方向，Project Coordinator 决定项目意义，项目成员执行专业工作，3002 负责 PAOS 产品与代码。

## 权限与身份

Rooter 复用 Human operational authority，通过现有 Human 语义接口处理安装治理；不增加临时 mandate、TTL、续租或专用动作白名单。长期身份 `rooter-001` 与当前 Codex/OpenCode 会话不同，也不是某个 Project Session。Rooter 不需要虚构 Project、Work 或 Assignment 来证明安装责任存在。

Rooter Home 位于 Projects 与 Libraries 之外，保存 ENTRY、TODO、可选笔记、报告与 mailbox。Home 是 Agent 接续入口，不是 PAOS Store，也不是共享方法库。Rooter Runtime 可以替换，长期责任从文件和当前事实恢复。

## 日常分工

- Coordinator 判断工作是否继续、优先级、成员责任和成果是否可接受。
- Rooter 直接处理安装、工位路径、现有 Wake、可达性、旧入口退出和运行恢复，不逐项等待 Coordinator 批准机械修复。
- 反复出现的系统缺口交3002；Rooter提供真实安装样本并检查统一采用。
- Human 保留方向、偏好、资源与明确要求的人工判断，并可随时停止或替换 Runtime。

故障先区分原生 Runtime/环境、PAOS 合同与调用路径；消息送达、唤醒受理、本人消费、产物和验收分别举证。历史成员不为目录整齐而重新入场，Rooter 不替成员 Ack。

## 一致性与恢复

保留业务权限、revision、幂等、原子 mutation、Ledger/receipt 和可恢复错误。V1.2 正常路径已删除 owner、instance、mandatory enter 与 Cycle 写资格；不得从早期 Rooter 文档重新引入这些机制。换 Runtime 时停止旧执行，外部在途写入必须完成、停止或明确接手。

Rooter 在当前安装内执行已授权事项；尚未部署的提案不是现成能力。安装治理完成以当前团队真实采用与业务接续为准，不能用配置存在或一次 ACK 代替。

## 来源

本文件保留 [PR105 的安装治理原则](https://github.com/xiangscream/personal-agent-os/blob/681f29250111ecbe73dc5e25cb666f5ecb79476c/docs/ROOTER-PHILOSOPHY.md)及 [PR107 的 Human 通道与直接入住决定](https://github.com/xiangscream/personal-agent-os/blob/d7859ba05f861e7e4cfcf41fb167c892c81430f2/docs/planning/ROOTER-V0-R1-R3-AND-FIRST-WORK.md)，按已接受的 Stage2 减法校准。原文中的旧 tenure/claim 和未执行 gate 仅为历史，不是现行要求。当前基线见 [V1.2-BASELINE](V1.2-BASELINE.md)。
