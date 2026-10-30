# V1.2 Stage3 安装回读

生产 Source、Library、CLI、工位与联系入口已切换，生产接力已由下一位消费、独审并被 Coordinator 接受。当前十份成员 TODO 均 trusted；九人有本人采用事实，s014 保留人工待接入。s031 正式 Mail/处理标记已由本人完成。PR116 已修复并实际部署，六个绑定在双环境读到同一状态目录和已有记录。双方 Coordinator 已将最终安装证据纳入唯一 RESULT；s010 已正式验收 w060 为 done（revision804/event3002-e784），s014 人工后续已由 s009 持有。

## 实际安装

| 项 | 当前事实 |
| --- | --- |
| Source | 已审 e4f0189 → PR114 merge819b642；已审 PR115 ca26600 → 合并8295971；PR116 已审384f8d0 → 当前生产de27c07cb80c09e6066ae8cd6d9204aca58b7f91；三次候选/合并代码树分别一致 |
| Windows/WSL | 已安装 CLI health 均回读运行 Source de27c07；安装描述指正式 checkout |
| Library | 已审b55基线 → 当前ed32316df77b59867fdc43d1a3b154be34da4e66；增量仅安装/采用指南、TODO模板与Catalog校准，生产f95/c9993祖先及原使用事件1/1字节保持 |
| CLI/配置 | Windows ~/.paos/bin/paos.cmd、WSL /home/remo/.local/bin/paos，读取同一Windows安装描述；WSL连接地址由实际路由提供 |
| 工位 | converter errors=[]；六份旧TODO增量转换，已是v2的本人当前页保留；TEAM/AGENTS/ENTRY应用，十一份当前入口补稳定CLI |
| Wake | 9个当前绑定沿原生ID正式配置；OpenCode配置省略model，Codex采用已验证Windows Python/shared state，不固定私有caller |
| OpenCode | 4101/4102/4110/4111/4112/4123实际health=1.18.33，原生会话存在；session创建版本可旧，不冒充服务版本 |
| CAT | 既有五participant官方existing-only rebind、Hook setup、service setup；consumer与current session一致，实际CAT连接检查通过，model=None |
| Project Git | 2001/3002 已从本地文本基线保存 Stage3 当前页与采用报告；当前提交见 INSTALLATION-MANIFEST 的 project_git 与 V12-STAGE3-PROJECT-GIT-20261002.json。仅明确入口/TEAM/当前页/报告入库，业务目录、运行私有文件和 Source 仓库未混入 |
| 非活动项目 | 1001/1002/1003/1004/1005/2002/2003/3001用窄Human更新合同status=closed；根、文件、原Work/Session和共享引用保留，注册表仅2001/3002 active |

生产 Source 仍保留切换前已有 docs/planning/34-FRICTION-LOG-REAL-USE.md 修改，不把它丢弃或伪称 checkout clean。Library 的生产 usage-events 保留原位未跟踪，不提交私人使用历史到网页资料包。

## 成员采用与回流

两项目各一封定向持久公告，3002五人与2001四当前成员+s023待入场准确定位。公告要求本人校准、继续真实责任、下游消费及Coordinator接受；Rooter不代Ack、不建升级Work。

3002：s027 实际安装报告 → s029 独立复核 PASS → s010 全文读取并接受，生产接力闭合。s032 曾把 v2 TODO 改回 v1 并重复任务，经本人修正和主管实读 accepted；s031 实际报告被主管读取，随后本人正式 Mail 成功，exact message 的 incorporated 消费已确认。s010 已恢复并接受/合并 PR116，当前安装实证回交其更新唯一 RESULT。

2001：s009 已接受 s021/s022/s023 本人采用；s023 由本人完成 pending_ack→active（rev1209/event2001-e1205），Rooter 没有代 Ack。s014 公告已持久送达，但 manual/WorkBuddy 无自动原生入口，仍待本人确认；待机成员不造业务工作，s009 已回到 w001 产品主线。

Human 催办统计：撤回此前“Stage3 为0”的表述。本聊天在 Stage3 授权后存在多次“继续”；尚未逐条区分例行续接与意外停顿催办，不能报告为0。Stage2历史至少2次保留。短时闭环不证明长期无人监督稳定。

Rooter使用自己的Home、安装入口和本聊天，未新建Project Session。当前接续入口为TODO及本报告；Project成果回流沿Coordinator实际产物和当前原生线程，不能代理被原生策略拒绝的消息。

## 本轮真实摩擦和修正

1. **安装服务未持续采用**：2001三个既有OpenCode端口停服，s029服务仍1.18.32。保存旧配置，恢复原会话服务并统一当前二进制；新增服务使用既有persistent sessions，没有自动创建新会话。
2. **CAT setup校验地址未继承**：服务env已含正确跨WSL地址，setup中的readiness检查未继承它，误试127.0.0.1。官方setup调用显式传CAT_BASE环境后实际检查通过。此处属于调用环境，未改CAT或PAOS产品代码，未手造scope。
3. **CLI操作入口差距**：paos --help存在，paos help不存在；项目归档和 Project 现状摘要写入目前没有完整日常CLI，只能用已有窄HTTP合同。收口时 s010 再次读取源码确认摘要写入接口，说明这部分“忘记操作后只查 help/指南”的目标仍有缺口。实际验收 Work 命令已补入指南；Project 写入入口作为明确产品债务回交主线，不伪称 CLI 已覆盖所有治理操作。
4. **旧Request污染恢复下一步**：s010正式w007/current TODO为统一采用，orient却优先旧w027/r013。s027 的 PR115 只改 CLI 下一步排序及对应复现测试；s029 exact 独审与 Rooter Windows 受影响检查各10/10，s010 已接受并正常合并。PR115 后的生产公共 orient先给w007/TODO下一步，Request仅相关性提醒。未重跑已接受e4完整7/7，未把WSL既有interop失败说成全绿。
5. **Rooter自身错误**：PowerShell向robocopy传目录数组被并成一个参数，导致Rooter临时副本复制了自己的恢复点。已停精确自有进程，rooter-home标INVALID，保留有效Store/Project/Library/config与显式rooter-operational。组合停止+递归清理被自动审批拒绝；改为只停进程成功，未再绕过拒绝删除。此错误不归咎PAOS。
6. **原生策略拒绝**：s010的一条部署指令被拒未发，保留原事实。Rooter依当前聊天Human独立Stage3授权实施安装，不代理该指令；s010现在从已运行版本继续只读回读与本人采用。
7. **Runtime 写权限与业务权限混淆**：s031 workspace-write/on-request 运行环境首次拒绝 Mail staging，而普通目录 ACL 无差异，同一正式CLI在Rooter环境可写。本人从正式审批入口用原ID恢复，s010实际incorporated消费；没有代理写信、关闭沙箱或手写回执。归类为Runtime环境A，未发现PAOS Mail合同B缺发送路径的证据。
8. **当前页会继续积累旧叙述**：s029 一度 TODO 先写 PASS 但文件尚未落盘；s032 回退TODO schema；s031把历史在途连续追加到当前区。共享TODO模板已明确“先落产物、写当前页后用installed orient复读”，历史细节放现有Works，不用新增状态库。成员自行校准，Rooter按实际文件回读收口。
9. **跨宿主 Wake 状态路径分裂已修复**：同一 Windows格式state_root曾在WSL被当相对路径，项目根/工位留下独立attempts/wake.lock。PR116 e8复用Codex driver既有路径合同；s029 WSL窄审PASS，但Rooter Windows23项2失败（新测试硬编码WSL路径/正斜杠）。同一 PR 校准宿主测试后，384 候选 Windows 23/23 与 s029 WSL 独审通过，s010 接受并合并 de27。Rooter 已部署，六个绑定双环境指向同一实际目录、读取相同已有 attempt 字节；证据为 V12-STAGE3-DE27-SHARED-STATE-PROOF-20261002.json。原分裂记录保留不重放；未声称新增跨宿主并发锁实验。
10. **本次资源停点已查明**：s010/s031先前原生回合均实际usage limit failed，不是“等Human批准”也不是Wake未发送。已完成邮件消费/报告不撤销；Rooter推进已有授权内安装发布与可用OpenCode实现/独审，项目意义和未完成Coordinator收口留明确位置，未冒充s010裁决。随后 s010 已恢复，完成 PR116 接受/合并；资源失败已不是其当前阻碍。

旧locator退出证据：当前9个正式Wake绑定、5个CAT消费者指向固定工位及现有原生ID；实际进程清单只有两个当前项目，旧p-2001-s017和p-3002-s029b进程匹配为0，8个关闭项目无Wake绑定。旧文件保留为历史；这是本次现场退出证据，不宣称永远不会出现外部旧写入。

## 恢复点与剩余责任

同一恢复点：restore-points/V12-STAGE3-20261001-183554。SNAPSHOT.json列有效范围；rooter-home无效，不用它回退。Source common Git配置曾指错误WSL worktree，已保存原件并修为正常Windows checkout；回退代码时使用已保存healthy配置，不能恢复旧损坏配置。

回退只撤本次改动，不整树覆盖新成果。后来成员更改TODO/TEAM时保留业务内容，按本次安装差异恢复；Project Git及历史不因回退删除。新增的服务/launcher/环境配置与原件都可定位。

已闭合：3002实际下游独审与Coordinator接受、2001四人本人采用及s023自Ack、s031本人正式处理标记与主管消费、Rooter持久收件/回报、旧消费者退出、orient窄修实际上线。PR116 路径修复与双环境采用已闭合。双项目 Git 已保存明确当前成果，GitHub e53939a/PR110#5947725520 已回流。w060 生命周期已正式收口；s014 人工采用和 INVALID 副本保留如实列出，产品主线已有Human正文审阅不变成机械治理审批。

## 收口接续观察（2026-10-02）

s010 完成组件图回合后，已有 Wake 排队消息在约一秒后启动下一回合，继续读取工位与未完责任。原回合完成时间 1790927671，新回合 01a0fb9b-92f1-74d1-8c7f-3ff7ccc2e83a 开始时间 1790927672；输入为既有通知“检查 Workstation mailbox，并从当前工位继续。”。Rooter 先误把单回合完成判断为停链，后补了不必要的显式提醒，核对记录后已纠正。此样本证明本次既有队列接续实际发生，不证明长期稳定；收口仍以成果及正式回执为准。今后结束态检查应包含已经排队或刚启动的下一回合，避免重复催动。

## 正式收口

生产 public delta 确认：2026-10-02T08:02:45Z，s010 通过 coordinator.work.transitioned 将 w060 doing→done，revision804/event3002-e784。完成判断引用已接受 Stage2、生产交接与最终安装实证；三名成员 Session 保持 active，没有伪造个人 Close。回执见 V12-STAGE3-W060-CLOSEOUT-20261002.json。

共享操作指南和 Coordinator Workflow 已补可复制的 work-transition 验收命令，并明确 Work 完成不要求成员 Session 先结束；Library 当前 ed32316df77b59867fdc43d1a3b154be34da4e66。这是文档校准，Source 仍为 de27。两位 Coordinator 先前实读 fc619 的证据按当时版本保留，不改写为读过后续指南提交。

s010 随后实读并接受 ed32316；完成通知已投递三名执行者。其本次原生回合在业务验收后因 `Selected model is at capacity. Please try a different model.` 中断，属于模型容量错误，不能写成 PAOS 权限拒绝。Rooter 未改模型；s027/s029 已实际消费并把当前页改为无活 Work/待机，s031 已由原通知激活并读取正式完成结果。原生错误见 V12-STAGE3-S010-CAPACITY-20261002.json。

PR111/112/113 已由 Rooter 正常关闭为旧候选，分支及讨论保留；PR112 的 instance/write-owner 方案明确标为后继设计未采用，不以关闭PR宣称旧代码完整合流。

最终成员回流：s027、s029 已消费 msg-s010-w060-final-accepted-20261002，当前页移除独审/采用等待并转为无活 Work 待机；s031 同封信已 incorporated，当前页明确 Work done、无未完业务，Session progress done（3002-e786），成员仍 active。完成消息已走到接收者的实际当前页和正式进展，不止送达。
