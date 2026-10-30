# V1.2 Stage 2 本地安装复核

最终Source已通过Windows完整7/7，Library合流独审已通过。s029最终一文件说明独审也已PASS，s010已实际消费并冻结Stage2候选验收；生产切换未发生。Reviewer Runtime异常已恢复，原会话同模型压缩后实际读取文件、检查diff、写复核报告并交付下游。

## 当前候选

| 项目 | 版本与实际结果 |
|---|---|
| Source | e4f0189bd04a9a48b5594d4c000611e97cc75ad4，PR114；Windows完整7/7，Python842、Node两时区各167、架构9边界及其余通过 |
| 联系数据流 | c537已获s029独审PASS；同真实3002冻结JSON经实际HTTP得到五人，实际teamAgentView生成五卡片及可复制TODO路径/Codex人工字段；e4仅改显示说明 |
| Library | b55c5c53076ae12b41fe8fd335542c486ee19f49完整合流独审PASS；保留生产f95a77c祖先、五人TEAM与软接续规则 |
| 接班/接力 | 严格fresh Codex/OpenCode有实际产物，受控agent send链经下一位Agent消费复核、Coordinator接受 |
| 安装/转换 | Source外descriptor与roots跨Windows/WSL实读；2001/3002/Home冻结72/213/482文件原字节回退；converter未变 |
| 生产采用 | Source仍3b86ac555a7526fcd5160fb7dd8404c98bad9733，正式服务/绑定/Library未统一采用 |

e4相对c537只有scripts/paos_contact.py的默认manual_open.note字符串（4增2减），把失实终端指示换成真实Codex Desktop人工入口和有原生导航工具时的条件路径。不把工具名称出现称为OpenCode已支持自动联系。

## 本地运行暴露的三类断点

1. **接线缺失能躲过聚焦测试。** 9a10独审/14项聚焦通过，但Rooter真实HTTP得到零同事，CLI同一输入有五人；完整Windows6/7同时报架构错误。根因是把registry目录当Project工位根。s027在原任务修为c537，实际HTTP→前端数据流和完整验证现已通过。失败原文保留，不再把已修问题列当前阻塞。
2. **原生回合完成不代表Agent工作了。** s029原会话最后三次Wake输出日历、无可用内容、乱码，无工具调用或复核报告；最后单轮约644572 tokens。服务健康、请求进入正确会话、没有改模型，简单追加相同Wake无法解决。Rooter在原会话用官方summarize保持当前glm-5.3-flash，压缩完成后通过正式agent send交接续材料，约13万token下重新读取邮件/文件、检查diff并交付最终PASS报告。该次Wake观察180秒返回uncertain，而后精确父消息的回合实际完成；原观察态保留，不重放。长上下文与恢复效果构成诊断依据；尚不能据此认定所有停顿都由上下文引起。
3. **责任停在局部结果。** 历史plain Mail未激活、Coordinator局部PASS后idle、旧TODO继续等待已解决授权，以及两名协调者重复激活，都有真实记录。受控链成功不等于长期稳定，整阶段额外Human催办至少2次。下一位实际接住、产物回流、Coordinator消费和完整安装采用必须分别核实。

Rooter也有可避免的损耗：当前报告与TODO更新滞后、猜CLI参数、误用WSL连接地址/环境方向、与Coordinator重复激活。这些属于本地执行错误，不能全部包装成Source缺陷。当前文件已校准，旧实现错误与锁等待均已关闭。

## 网页主线需要判断什么

最后独审已收齐，s010已冻结[RESULT与Stage3切换包](PAOS-V12-STAGE2-ACCEPTED-20261001/README.md)。请围绕完整候选是否够资格切生产判断一次；普通命令/显示说明/窄修不再增加新Gate。

统一采用按冻结快照正常合并发布，然后同步Source/CLI/config/Wake/Library/TEAM/工位与消费者，发一份公告让2001/3002成员各自恢复真实责任。Rooter核旧locator退出、旧workspace不再接当前输出、真正下游工作与结果收口。保留生产usage事件，使用实际roots重建catalog，不以候选零统计替换历史；归档项目保留文件和共享引用。

同时把Runtime退化列为实际运行摩擦：读面应能区分消息送达、原生回合结束与业务产物，恢复从工位当前事实继续。不要为每个失败再造授权、任期或无限自唤醒调度器。当前OpenCode服务版本尚不统一，属于正式部署待办。

## 审查材料与限制

- [Library候选差异](PAOS-V12-LIBRARY-CANDIDATE.patch)：生产f95a77c→最终b55，保留生产祖先。
- [Codex可见原始样本](evidence/PAOS-V12-STAGE2-VISIBLE-LOGS-20261001/README.md)：Rooter/s010/s031共432条，原字节保留，不含隐藏推理/工具载荷/私有环境，不称全量transcript。
- [s029异常原生样本](evidence/PAOS-V12-STAGE2-VISIBLE-LOGS-20261001/s029-native-before-compaction.json)与[恢复样本](evidence/PAOS-V12-STAGE2-VISIBLE-LOGS-20261001/s029-native-after-compaction.json)：可见消息及状态/token，恢复样本仅含tool名称/状态，不含工具载荷、reasoning parts或凭据。
- [最终e4独审原文](evidence/PAOS-V12-STAGE2-VISIBLE-LOGS-20261001/FINAL-E4-NOTE-REVIEW-S029-20261001.md)。
- 真实HTTP/前端函数检查没有浏览器导航或生产采用证据；隔离Codex双侧检查不证明OpenCode取得Codex原生调用能力。
