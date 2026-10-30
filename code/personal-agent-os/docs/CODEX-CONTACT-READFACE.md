# Codex 联系读投影

既有Contact仍保存原Thread登记事实。configured=true仅表示原生目标已登记；Codex投影进一步返回thread_registered=true与target_status=thread_registered，不表示可唤醒。

receiver独立表达本人入口准备：

| state | 读到的事实 |
| --- | --- |
| not_registered | 未登记extension.receiver_runtime_file |
| runtime_file_missing | 已登记，但运行文件不存在 |
| runtime_file_unreadable | 文件不可读，reason给出异常类型 |
| runtime_file_invalid | JSON/schema/原Thread/回环grant不符，reason给出具体读合同缺口 |
| process_unknown | PID未记录、查询不能确定，或运行文件来自另一宿主/UNC |
| process_not_running | 本机PID已不存活，旧运行文件不表示已准备 |
| prepared | 匹配原Thread的回环grant存在，记录PID在本机存活 |

prepared只表示上述准备事实，不验证PID对应程序或回环HTTP可达性，不表示Harness空闲、STOP许可、提醒送达或本人业务消费。online_state仍为unknown，既有checked_at仍为原生探测时间；receiver.checked_at仅是本次文件/PID读取时间。PID可能被复用，不能靠准备状态宣称入口在线。

投影不连接pipe、入口或模型，不发送提醒，不启动/恢复/修改接收器。token、pipe和任意运行文件额外字段不进入输出。blocking_reason及repair_owner为null（未记录）；文件缺失不是已经查明的启动拒绝原因，不从TODO/报告猜原因或负责人。

Windows使用只读OpenProcess/GetExitCodeProcess；不以os.kill(pid,0)查询Windows进程。WSL读取Windows运行文件时不把Windows PID当Linux PID，进程事实保持未知。STOP与Thread登记继续独立表达，准备状态不覆盖它们。

status、peers与team复用同一paos_contact投影。status保留activation=null与native_turn.state=not_observed；peers/team文本显示Receiver准备状态。读投影改好不等于S036已实际接入。
