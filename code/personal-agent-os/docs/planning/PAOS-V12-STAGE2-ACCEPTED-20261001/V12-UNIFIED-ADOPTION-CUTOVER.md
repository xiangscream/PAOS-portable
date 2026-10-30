# V1.2 统一采用与切换

目标：改进从完整候选、正常合并到整个当前安装采用，最终由2001/3002与Rooter的真实工作证明完成。当前Stage2可准备和复核；生产切换仍等待Stage3授权。

## 发布输入

- Source：e4f0189bd04a9a48b5594d4c000611e97cc75ad4（PR114），Rooter Windows7/7（842/167×2）。c537实际HTTP/前端数据流及s029独审PASS，e4一文件显示说明复核已实际PASS（FINAL-E4-NOTE-REVIEW-S029-20261001.md）；以s010最终接受清单发布。
- Library：b55c5c53076ae12b41fe8fd335542c486ee19f49完整合流独审PASS，保留生产f95a77c祖先；双项目采用包、五人TEAM/ENTRY与软接续规则已纳候选。生产使用历史与实际roots派生物重建属于切换步骤。
- 安装描述与Library registry：Rooter Home/candidate/installation-v12/installation.json及library-roots.json。配置位于Source之外；当前显式指向隔离候选，Windows/WSL读取同一份描述已实跑。
- 转换器：随最终Source。已验证的真实冻结输入和72/213/482字节回退结果保留在V12-STAGE2-DE3A3C0-ROOTER-RECHECK-20260930.md；新candidate只复核受影响部分。
- 当前团队：由s009/s010确认。2001名单s009/s014/s021/s022，s023待本人入场；3002五人s010/s027/s029/s031/s032，其中s032为支持位，不从历史Session或Work状态推断团队归属。

## 切换执行

1. s010收完整Source/Library/业务验收、真实接力与失败样本，提交Stage2 RESULT和本切换计划。获Stage3授权后，Source正常合并发布，Rooter核实际安装与发布一致；不force push，不把开发worktree当正式服务入口。
2. Rooter与Coordinator确认正在执行的责任、外部在途写入及消费者，安排实际停止/接班窗口。冻结现有Source、Store、工位、Library、安装描述/registry、Wake绑定与消费者入口；保留原文件和Git历史，不覆盖共享工作树的未提交改动。
3. 在完整冻结副本验证最终converter的增量输出，再按相对路径叠加正式工位。保留每份TODO原字节备份和历史；不以输出目录替换整个Project。TEAM/AGENTS/ENTRY采用共享模板，当前责任由实时事实与本人校准，s023不代Ack。
4. 部署已接受的Source与Library版本。保留Library生产使用事件，不把隔离候选的零使用统计当生产历史；走官方library init/roots/catalog入口修安装结构和派生目录。写Source外统一installation描述；Windows/WSL均指这份描述和各自正确连接地址。
5. Rooter用公开Wake配置入口统一正式绑定与实际消费者。Codex跨主机需要已验证的Windows python_executable、共享state_root和当前调用环境；旧绑定只存co_agent_root不代表已经采用修复。OpenCode请求继承会话模型，旧model字段不得继续强制覆盖选择；服务版本与expected_version按实测统一。更改前确认无正在执行的旧副作用，不重放uncertain尝试。

   Codex配置候选为installation-v12/codex-driver.json，已在隔离wake-proof根通过Windows/WSL同一s010 Thread的非回合检查。WSL需传递实际调用者的原生环境；Windows→WSL的WSLENV不得只标/w而丢掉入站变量。不将私有pipe或别人的caller身份固化到配置。OpenCode缺该原生入口时如实展示人工路径，不能复制Rooter身份冒充自动支持。
6. 各Project一封定向持久公告链接最终manifest、固定TEAM、指南与安装入口。成员按入口自改自己的当前页、核身份/联系与真实任务，结果交Coordinator；需接续时使用agent send或原Mail notify，并核下游真实消费。Coordinator完成后持久结果交Project Works，并通过已获Human授权的Codex联系工具唤醒当前Rooter聊天。Rooter不是ProjectSession，不制造Assignment。
7. Rooter核旧locator退出当前路径、旧workspace不再收当前输出、当前TEAM/TODO状态读面能联系同事。归档范围经现有批准及实时Project事实确定，退出活动/自动运行但保留文件、历史和共享引用；不能凭服务名称停止无关消费者。

## 完成判定与回退

Source已合并且实际服务同版；CLI/config/Wake/Library/入口统一；2001/3002/Rooter真实恢复、交接、下游工作和收口成立；未接受例外继续留TODO。发布公告、online、ACK、测试和Git版本分别只证明相应步骤。离线或不支持自动Wake的成员保留明确人工入口，不代其确认采用。

切换失败先停止本次精确消费者，保存失败原文，按同一冻结快照回退代码、Store、配置、Library与工位。转换恢复逐文件原字节并只移除本次新增且快照中不存在的文件；生产使用历史和无关产物保持原样。回退后重读实际版本并跑一条真实联系/恢复路径，不能只恢复Git HEAD。
