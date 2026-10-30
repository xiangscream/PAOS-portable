# 架构审查期间的运行观察

## PAOS 服务恢复

s010 原生任务发现 8766 拒绝连接、CAT 8770 可读。Rooter 独立执行已安装 `paos --json health` 得到 `unreachable / WinError 10061`；端口无监听，未发现 Windows Python 进程。

Rooter 调用生产 Source 的 `scripts/start.ps1 -NoBrowser`，使用现有 Python 环境，恢复回环服务和 172.20.224.1:8766 WSL bridge。随后 Windows 与 WSL 的已安装 CLI health 均返回 `ok=true`、Source `de27c07cb80c09e6066ae8cd6d9204aca58b7f91`。

本次恢复未升级代码、未改 Store/模型或重放业务消息。服务退出原因未取得证据；不能把它归因于 Cycle、权限、app-server 或模型容量。后续架构评审应讨论服务生存期、退出日志和安装启动入口是否足够，而非据此直接增加调度平台。

## s010 原生回合中断

Rooter 原生消息已进入 s010 会话并触发 turn `01a0fbc5-4064-7241-8ed1-636c43b1120a`。s010 实际回复并读取材料、核三份旧 PR；在最终结论前中断：

`Selected model is at capacity. Please try a different model.`

Rooter 保留模型配置，只发一次带恢复事实的接续，要求完成短结论。该错误证明本回合受到模型容量影响，不证明 PAOS 唤醒失败，也不撤销 Stage3 已完成事实。

## 当前说明的漂移

Rooter AGENTS.md 仍写 Stage2 实施，已校准为 Stage3 完成后的架构审查。s010 读到 Source/docs/ARCHITECTURE.md 开头仍自称 v0.5、当前基线8dd56f6；USER-AND-ARCHITECTURE-GUIDE.md 则已明确标为历史。两者应在审查中区分，不能把所有旧文档都当作当前合同。
