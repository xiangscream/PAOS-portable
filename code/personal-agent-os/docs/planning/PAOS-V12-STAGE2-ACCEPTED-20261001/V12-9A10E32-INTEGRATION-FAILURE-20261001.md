# 9a10e32 安装集成结论

**不能通过最终验收。** Windows完整verifier有6项通过、Architecture失败；真实隔离HTTP团队接口返回0人，当前同一项目CLI构建器返回5人。代码独审与Node语法通过没有覆盖这条实际接线错误。

## 已实跑

Source `9a10e329f0516481dea4a8df7912305f4ec9013a`，Rooter Windows候选clean。完整verifier退出1：Python835、Node两时区各167、派生数据、compileall、JS check通过，Architecture失败。原输出为V12-9A10E32-WINDOWS-VERIFIER-20261001.txt。

Rooter将真实3002 JSON复制到隔离registry，用候选build_server及真实HTTP GET `/api/projects/3002/team`：HTTP200、team.agents=[]；同一冻结Project的canonical root下build_team_rows返回s010/s027/s029/s031/s032五行。冻结JSON原字节未变，没有生产写入。原结果为V12-9A10E32-HTTP-TEAM-PROOF-20261001.json。

原因已明确：WorkflowService.team_contact传入self.store.root（项目登记数据目录），没有取Project.root_path（实际工位目录）。所以正常安装的页面会永远看不到已有同事；不能将这个正常路径错误称为“缺工位时诚实降级”。独立执行公开check_architecture.py进一步给出：workflow_service.py:98用store.root猜目录；路径推断须留在既有project_store唯一推断点。修正现有根解析，不撤销检查或增加静默兜底。

另两项既定交付在新页面尚缺：teamAgentView只有TODO next文本，没有本人TODO入口；derive_attach仍将Codex标attach_undefined_for_driver，未给出其实际可用的人工打开入口。这不是要求新Harness。应展示已有native Thread及正式打开方法/支持范围，OpenCodeWindows打开方式同样要可直接照做。

## 原任务继续

s027在原w060修正确Project根解析与架构失败，补已有TODO/人工接入出口；不写新状态、不加兜底、不硬编码成员。s029审实际delta并检查上述同一真实输入。Rooter复核最终Windows门禁及HTTP→页面数据流，s010收统一结果。Library c078独审已通过，生产/Stage3边界保持。
