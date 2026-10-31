# Codex 精确本人提醒入口

本机授权调用方可通过目标会话自己的被动回环入口提交一条提醒。入口只接受自身的原生线程 ID 与消息，不提供读会话、工具代理、任意线程选择、模型切换或审批操作。受理不代表模型完成或本人业务处理。

## 目标侧启动

由目标本人从 Codex Desktop 正常提供的原生工具环境执行人工 prepare：使用已安装 Windows Python，工作目录为安装 Source 的 `scripts`，运行 `python -X utf8 -B codex_receiver_session_start.py --prepare-current`。本入口沿 installation、registry 和 Contact 唯一定位调用者本人的 Home，读取已登记 Python、运行文件和 STOP；不接收目标、pipe 或身份覆盖参数，也不读取伪造的 Hook 事件。

人工 prepare 与真实 SessionStart 共用环境、Home、STOP 校验及同一启动段。启动使用 `CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB`，标准输入关闭，stdout/stderr 仍留原运行文件旁。`CREATE_NO_WINDOW` 只隐藏控制台；当宿主 Job 允许 breakaway 时，第二个标志使新接收器脱离该工具 Job。[Microsoft 进程创建标志](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags)及[Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)说明了这一机制。

宿主拒绝创建时只尝试一次，输出 `receiver_prepare_unavailable` 及原错误，人工命令以非零状态退出；不改 Job 策略，不重试或换启动路径。环境缺失、未登记、歧义或 STOP 仍明确停止。创建成功只报告启动器 PID；随后读正式 `wake status` 确认就绪。正常 prepare 与 SessionStart 不替换健康实例，登记迁移也不加载新代码。

接收器行为代码需要更新时，由本人在同一个 Desktop 工具环境、安装 Source 的 `scripts` 目录运行 `python -X utf8 -B codex_receiver_session_start.py --update-current`。本入口仍只解析本人的 Home，不接受 PID、Thread、pipe 或目标覆盖。它在原 native 锁内核准确 runtime-file/stop-file、OS 实例和既有鉴权空消息拒绝，再用同一 Windows 进程句柄核创建标识后停止旧被动接收器。STOP、未知、外 Thread、无法鉴权或实例变化时保留原状。旧登记留给正常 prepare 归档，新进程沿原 locator 与 STOP 启动；不要求操作者拼终止命令，不由 Rooter 代管他人实例。

更新后读正式 `wake status`：须有新 receiver 的已核 OS 实例、`prepared=true`，且 `receiver_behavior=native_followup`。此标记由实际发布运行文件的新接收器写入；只迁旧登记不会添加它。启动器 PID、磁盘代码已更新或旧实例 prepared 都不能代替加载确认。只更新需要载入接收器行为的实例；调用方单独更新传输错误分类不要求重启所有接收器。

入口不接受 pipe、caller 或目标 ID 参数；只能继承启动者自己的 `CODEX_THREAD_ID` 与 `CODEX_APP_TOOLS_PIPE_PATH`，绑定同一个线程。不得从别人进程/文件提取或复制这些值来启动。它内部使用已存在的 Desktop app-tools 客户端，只查询本人状态，再向本人线程发送。不能用另起 CLI/app-server 的会话冒充 Desktop 线程。

这是 Human/S010 本机专项范围内的自建精确提醒适配器，不是官方审核扩展，也不把通用 app-tools 权限转授给 HTTP 调用方。持有本人私有运行文件的已授权本机调用方才可提醒；运行文件只保存新生成的回环授权和目标 ID，不保存 Desktop pipe。树外实际送达已按 S034 现场接受（S040 无 Codex 环境调用→S034 原 Codex 会话内真实到达），旧阶段“尚须专项验证”句退役；启动边界与“只查本人会话”限定保持不变，交接与意图行接续共享 OPS（workflow/Guides/ops-entry.md 的 Codex一次性原生提醒行）。

## 外部提交合同

私有运行文件为 `paos-codex-self-reminder/v1`：`endpoint`、`session_id`、随机 `token`、`pid`、`process_identity`、`receiver_behavior`。进程实例来自receiver自身的OS：Windows为GetProcessTimes创建FILETIME，Linux为boot_id与/proc启动tick。使用真实os.getpid，不使用启动器或venv redirector的PID。`receiver_behavior=native_followup`标明已加载宿主跟进行为，不是授权、queue或业务完成证明。只绑127.0.0.1临时端口。

本人正常prepare验证原Desktop环境、准确self/Thread与STOP。同Thread有效grant只有在正向进程不存在、或OS实例/精确receiver启动调用确定失配时才归档旧文件，在原locator发布新入口。无关同号进程不被终止或接管。实例相符的活receiver、查询未知、无权限、外Thread与STOP均不覆盖。prepare与sender复用原native锁，服务循环不持锁，不需要rebind。

缺process_identity的旧登记不再仅凭pid_alive显示prepared。旧登记先核OS实际启动参数是否符合已安装的 `python -X utf8 -B -m wakeup_native.codex_receiver --runtime-file ... --stop-file ...` 合同；runtime-file与目标stop-file都须按规范化路径或samefile核为同一位置。任一参数确定失配可由本人正常prepare归档恢复；参数无法读取或任一路径无法确定则unknown，不发迁移探测。不会将进程名、文件mtime或端口可达当作实例身份。

旧receiver若仍按原合同运行，读面保持legacy_identity_unverified。本人正常prepare在原锁内，用旧token向原/send提交准确self与空message；既有协议在任何Desktop状态/模型调用前返回HTTP400/invalid_request，授权不符为401、错self为403。只有已核调用参数、该授权响应，以及验证前后相同OS创建实例都成立，才先保留旧原字节为`.legacy-*`，原子添加身份字段，保留原PID/endpoint/token和现有服务。生命周期追加identity_migrated。本次prepare启动器可正常退出；应从正式status看原receiver已迁移，不能把启动器PID当新服务。

空消息验证失败、超时、实例变化或STOP出现时保留原登记，不重启旧进程、不发布另一个入口。旧HTTP服务正处理在途提交时，验证可能超时；待该自然提交结束后由原Owner正常prepare，不重投业务。OS权限/执行位置无法核定时，从原Owner正常Windows入口恢复或交Rooter查准确失败，禁止force、手改grant或借凭据。自定义启动方式不作为已安装调用合同的替代。

`wake status`复用Contact读面，不发HTTP/原生探针。prepared要求PID与OS实例相符；process_identity_mismatch可同时是pid_alive=true/prepared=false。旧身份未验证或查询失败为unknown，sender在POST前拒绝。WSL沿登记Windows执行入口核Windows实例，不把Windows PID当Linux PID。启动参数只在旧登记判定时读取，不进入读面、回执或日志。

一次提醒明确区分receiver_offline（陈旧死进程或连接明确拒绝）、receiver_not_prepared（未登记/无有效grant）、native_busy、native_stopped、native_rejected与delivery_uncertain。使用协议error_code而非错误字符串猜状态；Windows子回执和两CLI保留原因、负责Owner、动作及retry=false。未知仍accepted=null，不自动换路或重发。

`POST <endpoint>/send`，请求头 `Authorization: Bearer <本人入口授权>`，JSON 恰为 `{"session_id":"<目标本人>","message":"<一次提醒>"}`。多余字段、错目标或空消息都在原生调用前拒绝；不接受 model/caller/tool/method/pipe 参数。调用方不持有 Desktop 凭据，不能向入口索取历史或调用其他工具。

目标状态明确为active、idle或notLoaded时，入口向既有 `send_message_to_thread` 提交一次已授权提醒；未知状态仍在提交前拒绝。它不传queue、model或设置覆盖，宿主决定如何处理跟进。成功为 HTTP 200、`accepted:true`、准确 `session_id`、`completed:false`，并含 `native_status_before_submit`。该字段只是提交前观察，不保证加入当前turn或下一turn排队。[官方提示说明](https://learn.chatgpt.com/docs/prompting#steering-and-queuing)区分两者；App Server的turn/steer不是本入口调用合同。

STOP为409；缺原生状态为503；发送后无法确认回执为502 `delivery_not_confirmed`、`retry:false`。入口不自动重发、不轮询Mail/Notice、不记录业务attempt；公共调用方也不得在不确定发送后切换路径再次提交。既有已拒绝或不确定的旧提醒不因本行为更新而自动重放。

S032 公共接线使用显式 `receiver_runtime_file` 选择此路径。未配置时沿原同源调用合同；已选择入口后发生错误就返回错误，不降级到另一发送方式。公共错误映射由公共作者负责。

## WSL调用Windows接收器

Windows接收器的`127.0.0.1`由Windows执行端访问。共享runtime文件的路径映射不改变调用者的回环网络位置。需要从WSL调用时，在现有Contact的extension中明确登记`execution_environment: "windows"`和`windows_python: "<已安装Windows Python的绝对.exe路径>"`，保留原receiver_runtime_file、Thread和STOP；不按失败结果临时换路。缺省或`local`仍使用当前进程环境，不根据盘符、端口、网关或连通性猜测执行位置。

显式Windows选路只支持带receiver_runtime_file的Codex本人入口。WSL一次启动已登记Windows Python，执行安装描述符source_root下的scripts/runtime_injection.py；message和最小target合同经UTF-8 stdin交接，不落临时文件或argv，不传Desktop pipe/caller凭据。不以WSL_DISTRO_NAME标签作为执行能力判据；按显式配置实际调用，OSError明确返回执行不可用，不探测、不fallback、不换Source路径。Windows子进程持有Windows原生锁、重新核STOP及准确self grant，再执行一次POST。当前进程已在Windows时不再启动另一个包装进程。执行环境不是身份，也不改变模型或授予别的Thread权限。

进程启动失败直接报错；启动后超时、损坏或目标不符的回执，以及本人receiver的HTTP502 delivery_not_confirmed，均抛InjectionUncertain，禁止重发或切回WSL。独立工具对此输出accepted=null、uncertain=true、retry=false；agent send --remind与wake trigger返回state=delivery_uncertain、accepted=null、retry=false。连接明确拒绝、授权、busy、STOP和前置条件拒绝保持确定拒绝，其他未确认响应不能当作未送达。

agent send的runtime_wake_performed只聚合本次调用：有确证受理成员为true；没有确证但存在未知成员为null；没有提醒或全部确定未执行才为false。每位成员的reminders保留各自真值，Mail持久投递、原生受理、本人消费及业务结果分别记录。成功的accepted只证明原生受理，不证明目标消费或业务完成。

## 生命周期诊断

接收器在运行文件旁追加 `<运行文件名>.lifecycle.jsonl`，记录 UTC 时间、PID，以及 `starting`、`ready`、`exit`。启动记录包含父PID和Python路径，就绪记录包含本人Thread和回环地址；退出记录只保存正常返回或异常类型、已定义错误码，不保存异常正文、消息、token或Desktop pipe。每条记录立即flush，历史记录保留；启动/退出生命周期日志写入失败直接报错。

正常发送方为每次实际HTTP调用生成32位十六进制 `request_id`，通过 `X-PAOS-Request-ID` 头传给receiver，原生payload仍只有session_id/message，不将编号、异常或凭据放入模型消息。缺少该头时receiver只生成本地关联编号；它不是授权或去重凭据。成功技术回执包含request_id；错误回执的diagnostic只包含request_id、phase、exception_type、errno/winerror、http_status和native_status等机器字段，WSL→Windows回包保留这些字段。状态拒绝的`native_status`为`systemError`、`not_returned`（宿主未返回状态）或`unrecognized`（宿主返回协议未识别值）；不复制原始状态文本。异常自由文本不进入diagnostic。

同一生命周期日志按该编号记录 `request_received`、`status_read_started/returned`、`native_submit_started`、`native_result_returned/unknown`、`request_rejected` 及 `http_reply_returned/failed`，附本次请求起算的elapsed_ms。native_submit_started只表示开始调用原生发送封装，不证明其中某个底层pipe请求已被受理；http_reply_returned只表示本端写入返回，不证明调用方收到。回写断连只记机器错误，不重复原生发送。请求诊断日志写入失败时，在既有stderr写request_log_failed与机器错误；不改变已发生的提交结果、不重投，也不因此停止接收器。

调用方HTTP等待失败仍为delivery_uncertain/accepted=null/retry=false；diagnostic.phase=http_wait不指认底层原生阶段。只有同request_id的已有receiver事件才能进一步定位。字段与日志仅改善后续定位，不恢复历史unknown，也不建立队列或自动接续。采用需原Owner加载已接受的新receiver代码；仅替换磁盘文件不能使在跑的旧进程产生新阶段记录。

正常返回和传播到服务外层的Python异常会留下退出记录；强制终止、宿主结束或系统故障可能没有退出记录。只有启动/就绪记录而进程已不存在时，退出原因仍未知，应结合目标本人保留的stdout/stderr及Windows事件检查，不归因父PID消失，不自动重启。STOP是发送栅栏，不会自行结束接收器。日志不改变runtime授权格式或公共prepared判定。

## SessionStart接线

一个用户级SessionStart定义供已登记的Codex Home使用，不含逐Agent参数。`scripts/codex_receiver_session_start.py`仅处理startup/resume：事件session_id必须等于宿主原有CODEX_THREAD_ID，并继承本人CODEX_APP_TOOLS_PIPE_PATH。它沿既有installation和`ProjectRegistry.read`读取五字段登记的Home适配视图及准确root的Contact，以及安装描述rooter_home的Rooter Contact；Rooter沿公开合同使用`rooter-001`身份和既有rooter_home校验，目录名可以不同，不创建Project Session，也不要求存在Project登记目录。旧schema、缺失或空root的坏项目登记明确失败，不把当前目录当root。当前Thread须在Project与Rooter之间唯一匹配一个已登记且存在的Home；使用该Contact原有receiver_runtime_file、stop_file和windows_python做一次隐藏prepare。环境缺失、未登记、歧义、Home缺失或STOP存在均明确停止，不建身份、不改Contact、不借凭据。

仓库提供`docs/CODEX-RECEIVER-SESSIONSTART.example.json`作为统一安装示例；文件存在不代表某台机器已安装或信任。定义中的Python用于运行Hook；实际prepare使用匹配Contact登记的windows_python，工作目录取installation中的正式Source/scripts。新员工完成正常Home和Contact登记即可使用同一定义，不复制其他员工身份或维护第二份索引。正常prepare沿已有锁及同Thread陈旧登记轮换合同；活实例、未知状态或不同Thread不会被覆盖。Hook只报告已启动及PID，ready应读正式wake status，失败详情保留在原runtime旁的prepare stdout/stderr。

本机于2026-10-14随[PR179](https://github.com/xiangscream/personal-agent-os/pull/179)采用该定义，已写入`C:/Users/remo/.codex/hooks.json`，与仓库示例逐字段一致，原两个Stop command保持。安装完成不等于已信任，也不证明全员自动恢复。

## 接线验收限制

官方支持上述SessionStart事件，非managed新定义必须review/trust，信任与当前定义关联：[官方Hooks说明](https://learn.chatgpt.com/docs/hooks)。本机2026-10-15只读配置已有SessionStart信任记录，不能将未见恢复归因于Human未配置；记录存在也不替代当前定义被宿主接受及事件实际执行的证据。需要审阅时通过受支持的产品入口（官方CLI为`/hooks`），不写信任缓存、不用bypass。真实Desktop startup/resume是否触发已安装Hook并继承本人环境，仍须原会话实际观察。

恢复有两条现有入口：原Owner从当前Desktop工具环境执行“目标侧启动”的 `--prepare-current`；或由宿主真实startup/resume触发已经安装、正常信任且继承本人环境的Hook。两者共用同一启动段，均须随后读正式wake status确认prepared/pid_alive，启动PID或文件存在不能代替就绪。人工模式不合成SessionStart；Hook仍从标准输入处理真实事件，现有用户Hook定义不变。

常驻观察应核具体工具Job的成员，以及创建工具结束、后继自然回合中的正式状态。嵌套Job可能仍有外层归属；不能仅因 `IsProcessInJob(..., NULL)` 为true就反复停止活实例。脱离工具Job不等于持续自愈，也不承诺Desktop退出、注销或重启后的可用性。历史缺exit的退出原因仍未知；自然正式来件的受理与业务消费另核，不盲发测试提醒。

当前matcher不处理其他SessionStart来源，也不监听接收器进程退出。普通消息、切回已打开的聊天或接收器突然退出本身，都不是本实现的恢复触发条件；不因此承诺持续自愈。若Hook缺本人环境，保留明确断点，由Owner沿原工具入口prepare，不借用其他会话。退出日志只有starting/ready且无exit时，原因继续未知，不能仅凭父进程消失或当前无接收器就归因宿主清理、整机重启或信任缺失。

## 验证

运行 `python -m unittest discover -s tests -p test_codex_receiver.py -v`。关键检查覆盖真实 HTTP 授权、目标范围、明确状态下的一次跟进、未知状态与 STOP、回执不确定不重试、私有文件不含原生 pipe，以及正常退出清理。实际 HTTP 跟进与发送后解码失败检查见 `attention-dashboard-v1-static/tests/test_codex_host_followup.py`；坏请求在原生调用前仍返回 400，发送后的 JSON/Unicode 回执解码失败为 502、结果未知。

本次采用由原 S031 独审、S010 接受发布、Rooter 正常安装，再由受影响目标本人更新并核实际加载。后续沿已授权真实业务核原生受理、本人消费及业务结果，不新增付费测试或重放旧提醒。
