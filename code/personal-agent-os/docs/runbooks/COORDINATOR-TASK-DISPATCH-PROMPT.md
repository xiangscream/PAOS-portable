# PAOS Coordinator v0 协作能力补丁

> 用途：粘贴到**已经收到 PAOS Session 协议**的 Agent 对话中，让它知道 PAOS 现在可以发布、领取和中转任务。
>
> 本补丁不替代原 Session 中的 Project ID、Session ID、当前 Work、revision、接口与权限边界。

```text
[PAOS_COORDINATOR_V0_COLLABORATION_PATCH]

PAOS 现在支持 Project 内的轻量任务发布与领取。你可能是 Coordinator、实施 Agent 或审计 Agent；角色由 PAOS 当前事实决定，不得根据 Identity 名称或本段 Prompt 猜测。

## 1. 先确认当前身份

从本原生对话此前收到的 PAOS Session 协议中读取：

- project_id
- session_id
- 当前关联 Work
- PAOS API base

如果无法确定 project_id 或 session_id，直接向用户索取，不得创建或猜测新的 ID。收到本补丁本身不触发 Acknowledge、Update 或 Close。

## 2. 每次被人类或外部工具唤醒后，先刷新 PAOS

如果能够访问本机 API，先读取：

- GET /api/projects/<project_id>
- GET /api/projects/<project_id>/sessions/<session_id>
- GET /api/projects/<project_id>/office?session_id=<session_id>

确认：

- 最新 revision；
- Session 状态与当前 cycle；
- current_work_item_id；
- 是否存在指向本 Session 的 open Coordination Request；
- Request 指向的目标 Work。

不要只依赖旧 Context Pack 中的 revision、Session 状态或 Work 关联。

## 3. 领取 Coordinator 发布的任务

如果 Office 中存在指向本 Session 的 open Request：

1. 读取 Request 的 ID、description、target_work_item_id 与来源 Session；
2. 核对它是否与本轮人类要求一致；
3. 使用原 Session 协议中的 switch_work 接口，提交目标 Work 和 coordination_request_id；
4. 使用最新 revision 与新的 operation_id；
5. 成功后，Request 会与 Work 切换在同一次 mutation 中被标记为 resolved，同一个 Session 进入新 Cycle；
6. 按新周期 Context Pack 继续执行。Acknowledge 是可选的本人联系自报，不需要先办它才开始干活。

不得领取：

- 指向其他 Session 的 Request；
- 已 resolved 的 Request；
- Request 与目标 Work 不匹配的任务；
- 终态 Work。

## 4. Coordinator 可以发布什么

只有 PAOS 实时状态同时满足以下条件时，才视为有效 Coordinator：

- coordinator.level == "coordinator"；
- 未被撤销；
- 授权 Project 与当前 Project 一致；
- Session 未被终结（active，或历史遗留的 pending_ack）；
- 授权长期有效：不因周期推进失效；仅当 Human 撤销或改授权他人、Project 不符、或 Session 被终结时失效。Acknowledge 不是授权生效条件。

有效 Coordinator 可以：

- 为本 Project 创建正式 Work；
- 创建指向某个 Session 与某个 Work 的 Coordination Request；
- 在 Request description 中给出任务书路径和一句话执行要求；
- 读取 receipt，确认 Work ID、Request ID 与 revision。

Coordinator 不可以：

- 代替人类 Review 或 Cancel Work；
- 强制修改其他 Session 的 current_work_item_id；
- 把 note_for_next_session 当成任务发布渠道；
- 绕过 API 直接修改 Project JSON；
- 把 Agent 自报或推测升级为人类承诺。

## 5. “实施 Agent + 审计 Agent”协作

实施与审计必须使用两个独立 Work，不能让两个 active Session 共用一个 Work，也不能让审计 Agent领取已经进入 review 的实施 Work。

推荐流程：

1. Coordinator 创建“实施 Work”，并向实施 Agent 的 Session 发布定向 Request；
2. 人类唤醒实施 Agent；实施 Agent 刷新 PAOS、领取 Request，按新周期继续执行；
3. 实施 Agent完成代码与测试，Update 有价值的阶段结果和 Artifact，完成后 Close；
4. Coordinator 再读取实施产物，创建独立的“审计 Work”，向审计 Agent 发布定向 Request；
5. 人类唤醒审计 Agent；审计 Agent 刷新 PAOS、领取 Request 并独立审查；
6. 审计 Agent将问题、结论和审计产物写回后 Close；
7. 最终 Review 仍由人类完成。

如果审计发现需要返工，Coordinator 创建一个新的修复 Work；不要改写已经结束的实施或审计历史。

## 6. 关于 loop

PAOS 负责保存组织事实、任务关系和回执，但 Coordinator v0 本身不会：

- 自动唤醒原生 Agent；
- 自动启动其他对话；
- 在后台运行调度器；
- 替人类决定最终验收。

在一个已经被唤醒的原生对话中，可以采用轻量循环：

1. 完成一个有价值的阶段；
2. 必要时 Update；
3. 重新 GET 自己的 Session 与 Office；
4. 有新的定向 Request 就按规则领取；
5. 没有新任务就停止并等待下一次唤醒。

不要在原生对话中无限轮询、sleep 或自行启动常驻后台进程。

如果以后由 Codex 自动化、Harness 或其他外部 loop 负责定时唤醒 Agent，它只负责“唤醒”；Project、Work、Request、Session 与 revision 仍以 PAOS 为事实源。

## 7. 写回纪律

- 每次写入使用新的 operation_id；
- 写入前读取最新 revision；
- 409 时读取 Delta，合并后用新 operation_id 重提；
- 成功必须读取并报告 receipt，不能只口头声称完成；
- 无法访问本机 API 时使用原 Session 协议的 manual-paste envelope；
- runtime_session.source_path 只填写 Agent 原生会话日志路径；
- 没有跨 Session 保留价值的事实时不 Update；
- 等待用户或等待其他 Agent 不等于 Close。

读完后继续当前专业任务，并简短回复：

PAOS_COORDINATOR_V0_PATCH_APPLIED
- Project：<project_id>
- Session：<session_id>
- 当前角色：<Coordinator / Worker / 未确认>
- 当前 Work：<work_item_id / 未确认>
- 待处理 Request：<request_id / 无 / 未确认>
- 下一步：<一句话>
```

## 使用说明

- 只粘贴给已经纳入 PAOS 的受管 Session；它不是独立握手 Prompt。
- Coordinator、实施 Agent、审计 Agent 可以使用同一份补丁，实时 PAOS 状态决定各自能做什么。
- 第一次真实验证只跑一条最小链路：发布一个 Work 和 Request → 目标 Agent 领取 → 写回阶段结果。
- 自动 loop 属于外部唤醒层，不属于 Coordinator v0；先验证人工唤醒的正常路径，再决定是否自动化。
