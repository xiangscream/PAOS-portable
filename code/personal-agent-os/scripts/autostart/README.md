# Windows 独立后台运行

Core 与 WSL bridge 由 Windows Task Scheduler 的 PAOS-Core、PAOS-WSL-Bridge 两个长运行任务持有。仅手动 Start/Stop，无登录或开机触发器，不自启动。任务使用当前用户 Interactive/Limited，不存密码、不提权、不依赖 Codex 或工具进程；退出 Windows 登录态、关机或明确停止任务会结束服务。不是 Agent 调度器。

发布后安装（不会停止健康进程）：

```powershell
& scripts/windows-background.ps1 -Mode Install -Python '<已安装python.exe绝对路径>'
```

先核现有 Core/bridge 的真实 PID、命令和监听，再一次切换：

```powershell
& scripts/windows-background.ps1 -Mode Switch -CorePid <准确Core PID> -BridgePid <准确bridge PID>
& scripts/start.ps1 -NoBrowser
```

任务直接运行 pythonw -m runtime_adapters.windows_paos_service；动作等待服务退出，保持任务 Running，不用启动后立即退出的隐藏 launcher。宿主只启动 Core/bridge，退出码直传 Task Scheduler，不循环重试。bridge 启动时读取实际 WSL 网卡；没有网卡时明确失败，WSL 可用后沿 Start 入口启动。

宿主在创建任何子进程前，将自己加入仅由本人持有非继承句柄的匿名 Windows Job Object，设置 KILL_ON_JOB_CLOSE。Core、bridge及网卡查询子进程自动继承Job成员关系；Windows任务停止或宿主退出时，最后一个Job句柄关闭，Windows同时结束该Job中的子进程，不遗留监听。Job创建、设置或绑定失败时明确报错，不启动服务、不降级为无Job模式。机制见[Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)。

安装只将指向本 Source 的旧 Startup VBS 快捷方式移动到安装描述旁 windows-services/ 留档，其他快捷方式与旧消费者/唤醒任务不动。VBS 文件退役，只留历史定位。原恢复脚本调用 start.ps1 时同样只启动已安装任务，不再产生工具子进程下的服务。

启停与查看：

```powershell
& scripts/start.ps1 -NoBrowser
& scripts/stop.ps1
& scripts/restart.ps1 -NoBrowser -NoPause
& scripts/windows-background.ps1 -Mode Status
```

日志在已安装 Source 的 private-data/logs/windows-services/：每个角色有 lifecycle.jsonl（宿主 PID/PPID、服务 PID、退出码）、stdout.log、stderr.log、host-errors.log。paos.log 继续保存 Core 原有业务日志。强制结束任务可能来不及写最终退出记录，应同时读任务结果与实际父链。

Codex receiver 仍绑定目标本人 Harness；关闭 Codex 后不能提供原线程提醒。重新打开时由目标本人沿 docs/CODEX-SELF-REMINDER.md 恢复，不由后台服务代启或复制凭据。Core/bridge 存活不代表 receiver 或 Agent 在线。

验收核任务 Running、实际父链、原端口和 health，不关闭别人的 Harness 或重复业务测试。随后 Human 正常退出 Codex 的真实观察用于补齐退出后存活证据，未观察前不称已完成该场景验收。

卸载先沿 Stop 停这两个任务，再注销准确任务名；回退恢复留档的原 Startup 快捷方式与已接受 Source，不触碰其他任务、Store 或 Contact。

Windows 参数来源：[任务主体](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtaskprincipal)、[任务设置](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasksettingsset)。
