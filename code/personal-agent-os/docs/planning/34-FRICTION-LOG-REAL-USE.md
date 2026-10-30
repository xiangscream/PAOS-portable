# 真实使用摩擦记录（CAT/PAOS）

启动日期：2026-08-26/27
实验性质：PAOS + CAT 第一轮真实功能试用
Room：room-0c6d2eb49125（若后续复用 Room，请在条目中标注清楚）
Participants：
- p-3002-s018：P2.2-Coordinator-TCW（DS-H）
- p-3002-s010：Manual codex（Codex）

## R1：已记录，不立即修

### F-001 新标签打开 CAT 在 Codex 内置浏览器无反应
- 现象：PAOS 项目页的 `Co-Agent 协作室` 按钮使用 `target="_blank"`；Codex 内置浏览器中点击无反应。
- 绕过：直接访问 CAT URL 正常。
- 暂存原因：先观察是否在所有 Codex 会话可复现。
- 状态：未修。

### F-002 Room 平铺全部 Work，没有突出本 Room 与 Participants 关联 Work
- 现象：右侧 PAOS 摘要把所有 doing/review Work 都列出来；不知道哪些 Work 与本 Room / 各 Participant 的 paos_session 相关。
- 影响：多 Work 项目里无法一眼看出“这轮协作的 Now 是哪个 Work”。
- 状态：未修；优先观察 1–3 轮真实使用后决定聚合方式。

### F-003 PAOS 首页/项目页历史对象压过当前主路径
- 现象：PAOS 项目进度仍停在 v0.5 / 276 tests；历史 Work、Session 长列表压过当前主路径。
- 影响：新进入 Session / 新 Room 时，用户仍需从长列表里找当前项。
- 状态：未修；与 Now/Next UI 后续收口一起处理。

### F-004 Cycle / Session 生命周期让已分配工作难以继续
- 现象：Coordinator 的长期授权与每个 Cycle 的执行接续规则没有在入口和操作路径中清楚分开，Agent 完成一个 Cycle 后，Coordinator 难以顺畅地让它继续当前 Work。
- s009：Coordinator 授权是在 Cycle 2 建立；到 Cycle 7 时，旧规划和工位信息仍让人误以为授权会随 Cycle 过期。实际 `granted_cycle=2` 是审计信息，授权仍有效，但当前 Cycle 写入仍需要 execution claim。角色授权与 Cycle 级执行凭据的区别没有及时传达到 s009，Human 后来又明确要求它回主线继续。
- s031：Cycle 5 随 w058 收尾后，s031 仍需继续 w059。Durable Mail / Wake 没有重开 PAOS Session；Coordinator 对已完成 Session 创建的 Assignment `r043` 成为 stale finding，随后取消。正式接续必须由 Human 通过 PAOS 页面 Continue。Human 已完成 Continue：s031 Cycle 6 active，当前 Work 为 w059，Acknowledge Event=`3002-e675`（revision `694→695`）。随后 s031 写入 Session Update Event=`3002-e676`（revision `695→696`），并通过 Mail `mail-s031-w059-cycle6-request-assignment-20260924` 请求新的正式 Assignment；该 Mail 已送达，但 T-003 尚未开始。
- 影响：Work 会因 Cycle/Session 边界停住，Coordinator 和 Human 需要额外识别授权、claim、Session 状态并手工完成接续；还可能产生指向已完成 Session 的无效 Assignment。
- 状态：已记录，当前采用窄绕过，系统语义未修。对于同一 Work、同一执行者且已有 active Session 的 Human 明确续做，不再重复创建逐 Cycle Assignment；Coordinator 通过 durable Agent Mail 沿用现有责任。2026-09-24 `msg-3002-rooter-r1-s031-resume-20260924` 已送达 s031，Activation attempt=`agent-mail-73f0e5dc2ebb8a84b04ec4c95cb3bd4f` 返回 `woken`；s031 随后以 Session Update `3002-e677`（revision `696→697`）将 T-003 改回 `working`，证明当前 Work/active Cycle 可不经重复 Assignment 继续。T-003 交付仍待完成。真正变更 Work/执行者、或新 Session 需要接单时仍保留 Assignment。Coordinator 长期授权（不随 Cycle 过期）与当前治理写入所需 execution claim 仍是两件不同的事。

### F-005 Rooter 首轮落地被额外 Assignment / 任期手续拖慢
- 现象：Rooter Home 与 Runtime 入口已建立、Human 也直接批准入职并给出真实首项责任，但流程中仍出现 R2 builder rehearsal、额外 PAOS Assignment、R3 任期审查等候选步骤。Human 判定这些步骤没有增加必要的治理事实或风险证据，要求 Rooter 直接开始负责 Project 2001 的 V1.1 日常路径收敛。
- 与既有摩擦的联系：F-004 已记录 s009 将 `granted_cycle=2` 误读为授权到期，以及 s031 在 Cycle 5 完成后需要 Human Continue、旧 `r043` 随后成为 stale Assignment。当前又在 s009 固定工位 TODO 中发现“派发须满足当前任期”的旧说法仍与长期授权规则并存，说明纠偏虽进了 Mail / 新流程，但没有干净进入日常入口。
- 影响：真实项目继续工作被额外 Assignment、反复确认任期和保持 Agent active 的手续取代；还会留下与实际责任脱节的 Request、Assignment 和 TODO。
- 当前采用的方向：Rooter 的稳定 Home + Human admission 即承载其长期责任，不虚构 PAOS Project Session / Work。相同负责人、相同 Work、现有 active Session 的继续工作沿用现有责任与 TODO / durable Mail；只有责任人、Work 或范围实质变化，或新 Session 确实需要治理接单时才创建 Assignment。Coordinator grant 是长期授权事实；execution claim 只约束当前 Cycle 的 PAOS 写入，不是角色任期。Runtime 不可达时修复或报告真实 adapter blocker，不以新 Assignment 掩盖。
- 状态：Human 已明确此取舍；本次已将 Project 2001 的真实责任通知 s009，Mail=`msg-3002-rooter-2001-v11-convergence-20260924`，正确落入 canonical Vault mailbox，Wake attempt=`agent-mail-da61ff5dac5739caa69c44e8fabf439f`。该次仅证明 durable delivery 与 native turn 已启动；Agent 是否已读、修正 TODO 并使当前 roster 统一使用 V1.1，仍待其回报。未修改 PAOS 治理代码。

### F-006 Runtime 升级覆盖不完整，旧会话答复又让主线停摆
- 现象：s027 的 OpenCode 唤醒配置暴露缺口时，Codex/current-pointer 候选 `5fa04ffe` 只改 Codex 与 CAT 投影，没有改 `opencode_cat_adapter.py`；同期 OpenCode 指南引用的旧四参数 setup 已被移除。真实样本只证明 OpenCode 中出现 user message、观察窗口内没有 assistant turn，不能据此断言 generation fence 是根因。随后 s010 的旧 Codex 会话在收到接续后重复回答“s027 是否还在运行”，没有执行固定 TODO 上的新事项，PAOS 主线因此第二次停下。
- 影响：跨 Harness 的升级覆盖和入职/运行说明不同步；Coordinator 把旧会话有响应误当成工作已接手，Human 必须再次发现配置问题、指出继续方向并催办。
- 流程修正：Runtime 升级按 Codex、OpenCode、DS-H 分别核对实现、setup/撤销说明和实际 binding；发现缺口当轮进入固定 TODO 并指派对应责任人。旧会话一次答非当前问题即视为 handoff 失败，不再重复发送同一提示；切换到核实过的当前入口，并由 Coordinator 继续 TODO 已授权的工作。只有 durable 交付、真实原生回合、Agent 读取与实际产物均有证据，才算接手或完成。
- 状态：已将当前 s027 覆盖缺口、未证实根因和旧会话接续规则写入 Stage 2 与 s010 TODO；P1′ fallback 的真实回归输入已校准为 `frozen-20260930b`，`frozen-20260930e` 不适用。Runtime 与 TODO 流程改进仍需在本轮真实 Stage 2 接力和扰动验收中验证；未放宽 generation fence，也未改生产。

### F-007 推 PR 时把本地候选分支误当成 PR 源分支
- 现象：本地 exact candidate `3fb359d` 已通过 Rooter、s029 与 Windows 全量验证，但首次按旧本地 ref 将它推到 `feat/v12-integrated-converter-a4a`；GitHub PR #114 实际 head 是 `feat/v12-integrated-release`。读取 PR 元数据后，已将同一候选无强推快进到真实 PR head，GitHub 回读 SHA 一致。旧候选分支也因此保持在同一提交，没有代码内容分叉。
- 影响：若不读回 PR head，已验证代码与网页主线仍会分离，形成“本地完成、PR 未更新”的假交接。
- 流程修正：推送前从 GitHub 读取 PR 的 head branch 与 head SHA；确认本地 exact candidate 是该 head 的后继，只快进该 PR head；推送后再次读取 PR 元数据确认 SHA。本地 checkout 名称、旧 tracking ref 和 branch ancestry 均不能代替 PR 当前 head 元数据。
- 状态：PR #114 已更新到 `3fb359d`；exact-head 验证及 Stage 2 未完成边界已写入 PR comment `5903626950`。本轮无 merge/deploy 或生产变更。

## 执行规则
- 每个摩擦必须等真实使用后才有 go/no-go。
- 能追溯到 Room、Exchange、PAOS revision 的，记录对应 ID。
- 修复只在单个小提交中完成，不混入功能扩展。
