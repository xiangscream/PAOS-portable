# Portable 当前收敛结果：本地 Agent 工作链

本片起点：`9066765f99d1fae9593e05dc26a12b47af42ac6c`（上片候选 `6506e07` 加复现检查）。
原系统、真实工位、凭据和生产 Runtime 未改动。改动位于既有 PR #1 分支。

## 实现

`paos.py` 删除旧 Core HTTP 业务命令及其无人调用的辅助函数。
ProjectRegistry 复用 data_root/project-registry/projects，只显式创建五字段最小登记（旧文件绝不覆盖）；
`orient/inbox/status/attention/agent/mail/peers/team/workstation/wake` 直接读取登记。
Library search/tools 调用既有文件模块。只有显式 CAT/原生提醒仍依赖外部通道。

Project 展示只保留定位与成员，旧人类要求/项目概览不再成为 CLI 的维护动作。
Home 写入不再旁路生成 Workbench，避免“真实 TODO 已更新，展示副本却旧了”。
换机绑定必须显式给出本机 native session，不继承 Project 中残留的旧运行身份。

## 验证入口

`python code/personal-agent-os/scripts/verify.py`

- 包根：37 项初始化测试 + 30 项新文件直连/输入接续测试。
- 核心：22 项接收器测试 + 8 项保留的数据根与备份测试。
- 保留的扫描管道：25 项，其中 1 项因没有真实预生成 build 而跳过。
- 架构检查与 Python 语法检查。

新测试使用完整源码和隔离真实文件，封住网络；提醒测试只替换最终 native 提交，不替换
Mail/Notice/TODO 写者。接收器原测试使用临时 localhost 服务和假 Desktop，不调用模型。
测试含跨项目、Rooter、显式安装路径、重复提醒、未知提醒、坏登记、字节不变与 CLI 子进程。

退出的 `test_d31_install_homes.py` 对应已经删除的安装普查接口；旧 D3.2 的 Core 启动测试
随服务退役。其仍适用的安装/备份断言已移入 `test_installation_files.py`，不是跳过错误后称通过。

## 没有完成的部分

上一轮尚保留 TODO v3；见文末本轮 v4 改造。
已增加 `project register` 新项目定位入口；没有旧 Project JSON 的批量迁移、真实日会自动消费任务或生产 Windows/WSL 采用。
旧通用 Skill 中的报告模板仍是按需方法，不是硬基座必经流程；继续按真实使用精简。

部署判断以真实新机业务闭环为准，不把此处的测试/CI当成已部署。

## 教学要点

解耦不是只拆文件。旧链是“读工位先依赖服务、服务又依赖旧业务对象”；本片直接减少
这条依赖，把定位归本地登记，把工作归既有 Home 写者，把解释信息归 Workflow。
不再恢复整套旧平台来满足一个 Agent 读取自己 TODO 的需求。

## 下一片：Project 结构真正退役（本轮）

- 唯一持久新 schema：`paos-project-registry/v1`；仅 `schema`、`id`、`root_path`、`homes`、`coordinator_home_id`。
- 不再接受项目管理 `human/generated/next_items/key_files` 与旧 Session/Work 负载。原 v3 JSON 是另需保留的历史原件，不在新文件读/写链兼容。
- 新 CLI `project register` 从已存在的 OB 目录登记 Coordinator/可选 Homes；同值不改字节，不同值不覆盖；不创建空业务文档或 Runtime 身份。
- 旧 `paos_coordinator.py` 的无消费 Work 前置检查和 `paos_workstation.py` 的 `key_files` 预检/周期材料化已退出源码；`paos_v12_convert`、`paos_v13_convert`、`migrate_workless_installation` 及不再被 CLI 调用的兼容/渲染脚本也已退出。真实 Home 写者和跨项目持久消息仍复用。
- `ProjectRegistry.read()` 的短期内存适配仅为调用现有 Home/Mail 接口，**不持久化** Session status、项目摘要或 revision；名册“active”只指登记，不证明进程在线。

保留未完成：现行 v4 的 Pinned/Tasks 已实现；生产项目迁移需先独立保留原旧文件，再准确登记和回读；并未真实操作用户本机。

## TODO v4 工位合同（本轮候选）

- 新增 `paos_todo.py`，删除 875 行旧 `paos_todo_v3.py`；以原生 Markdown 固定栏目替代逐行 JSON 值，任务状态唯一来自 checkbox 标记，不再维护 `state` 复制字段。
- `Pinned` 完整承载自由正文、引用与已批准持续要求；`Current` 只保留 objective/next_action/waiting/inflight/context_refs/result_refs/updated_at；`Tasks` 继续保留稳定任务 ID、来源、接受与回告引用。
- 只写当前区会保留其前后的 Pinned、Tasks 原始字节与换行，修改前进行指纹检查；完整写入验证语义往返和身份。
- 旧格式不兼容。没有自动改写生产工位，实际迁移需核原件；真实接收器/Obsidian 的点击交互仍未实机验收。
