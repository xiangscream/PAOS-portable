# Stage3 窄修：Windows/WSL 的同一 Wake 状态目录

目标：已批准的统一安装必须让同一个 OpenCode binding 在 Windows 与 WSL 操作时使用同一实际状态位置，不把绝对安装路径写成项目相对目录。本项是当前 w060/Stage3 的现场安装缺陷，不新开 Work、不新增审批 Gate。

## 真实证据

生产 Source：82959713ec567a32a1183abb618f3767b2be400e。OpenCode 六绑定的正式 driver_config.state_root 为 `C:/Users/remo/.paos/wakeup-native/opencode`；Windows 操作实际使用此目录。

当前 `scripts/wakeup_drivers/opencode.py` 的 `_state_root` 直接 `Path(override).expanduser()`，在 Linux 没有把 Windows 绝对路径转换为 `/mnt/c/...`。Rooter 在实际 3002 Project 根与 s027 工位发现名称为 `C\uf03a\uf05cUsers...wakeup-native...opencode` 的旧相对目录：同一 3002-s029 binding fingerprint `6454fec8ce835e41aa6b5528d118266a4c852599bfe22e6b87b9d4d2b9e3689d` 有独立 wake.lock 和 attempts。最近写入分别 2026-10-01T13:47:03Z、14:11:25Z；都是本次切换后真实交接，不是纯历史样本。

相关 attempts：`agent-mail-a830de8d411ae1bbfc374bc148443c92`、`agent-mail-451e7590b33071ccf71bd155c5de3a69`。保留原件，不重放其消息，不迁移它们冒充新状态，不手写生产 Store。

## 分工与完成标准

s027 在正常 Source 分支修实际路径解析。优先复用已有 Windows/WSL native-path 合同，限定必要路径转换；不新造 Runtime 身份、owner、lease，不改变模型，也不靠每个 Agent 工作目录特判。检查相邻 Codex driver 是否已有相同问题：只报告事实，Codex专项需要时由s031接，避免扩大实现范围。

当前明确安装配置的 Windows绝对 state_root 在 WSL 应解析成 `/mnt/c/Users/remo/.paos/wakeup-native/opencode`，Windows仍同一 C:实际目录；默认本机路径语义不无需求改变。binding/native Session ID 不变。正常读/写不能继续在 cwd 生成 C:相对目录。

交付：exact候选、窄PR、受影响检查及 Windows/WSL 对同一安装状态路径的实读；隔离样本可写临时路径，不为了验收重放业务消息。没有理由重跑完整 Stage2 或造新CAT Room。实际采用由 Rooter 做。

成果先落盘，正式 agent send 交 s029 独审并回 s010；s029 只审 exact candidate/本缺陷。s010 正常接受及合并已有Stage3授权内窄修。当前生产829保留为恢复点，后续 Source 对应写入最后manifest。
