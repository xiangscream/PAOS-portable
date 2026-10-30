# PR116 Windows 受影响检查：两项断言需修正

Rooter 对 exact `e8fa6b19bf3ddc6f446878a99aa2b2c385bf9722` 在 Windows 执行 `test_wake_opencode_b2b2.py`，结果 23项/2失败。原输出已保存 `V12-STAGE3-E8FA6B1-WINDOWS-WAKE-FOCUSED.txt`。Source 路径函数本身复用已有合同正确；不能在 Windows 引入 WSL 专属预期。

失败1：`test_windows_absolute_state_root_resolves_to_wsl_real_dir` 无条件要求 `/mnt/c/...`，Windows 正常应保留 `C:/...` 的绝对本机路径。

失败2：`test_posix_state_root_unchanged` 用硬编码正斜杠片段比较 Windows Path，正常 Windows 分隔符为反斜杠，导致错误失败。

请 s027 校正这三项测试的宿主合同：明确 Windows 与 POSIX/WSL 的实际期望；使用 Path 等值或 parts 比较；同一实际配置的 Linux映射仍要证明不被当相对路径。不要把整个新增测试简单跳过，也不改正确的产品逻辑。cwd清点调用一个不做IO的方法本身不能证明“没有新写入”，至少明确验证返回绝对路径及准确目标；按必要范围做，不扩全套验证。

修正后推同一 PR116，交 s029 对 exact 新 head 补窄审/受影响复跑，Rooter 核 Windows 和两环境实路径后采用。s010 上一回合确因 Codex usage limit 终止；不是在等新产品授权。Rooter 按本聊天既有 Human Stage3 整阶段发布与安装授权接本次机械收口，不代理此前被拒的部署消息、不伪造 s010 接受。

完成后成果回本报告所处 Rooter Home，并沿允许的既有联系路径通知当前 Rooter。根因/测试结果保留原文，不能把 e8 的 WSL PASS 写成 Windows PASS。
