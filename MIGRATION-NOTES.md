# Portable 迁移：代码与库先就位，业务最小接续

适用对象：本仓库。S040 对原机副本的历史操作和尺寸/实测记录原文保留在 [历史迁移记录](docs/history/MIGRATION-NOTES-S040-20261029.md)，不是本仓库的目标机验收结果。

## 1. 重新取得系统资产

在目标机器取得明确 commit 的代码与方法库。不要把旧机的配置、凭据、接收器和进程目录整包当作新安装。先执行 `python portable.py plan` 检查解析出的路径，再执行 `init` 创建本机配置。

`init` 一次发布 `config/local/installation.json` 与 `library-roots.json`，不修改现有安装。重复执行时只接受匹配的配置；旧路径、损坏 JSON、文件占位、越界链接均显式报错。已有 `config/installation.json` 时拒绝再创建第二份安装。

这些配置仍使用核心已有的 `paos-installation/v1` 和 `paos-library-roots/v1`，没有另一套业务状态格式。整包移动后，`doctor` 会指出旧路径，不会悄悄回连原机；重新定位使用现有核心安装配置入口，先回读再更新。

## 2. 选择耐久业务资料，而不是按目录名删除

首轮迁入安装级 Rooter，以及每个选定项目的现任 Coordinator 工位。一起保留项目事实、当前职责、未完成输入、必要的原始消息、决策与所引用的成果。

不能仅复制两个工位文件夹就宣布接续完整：TODO 指向的 Works 原件、消息附件或决策依据也必须仍可读取。Works 可能有临时文件，也可能有唯一的正式交付；应按内容、引用和保留要求选择，而不是统一视作垃圾。历史备份是否另存也需要明确的回退来源，而非直接删除。

其他执行工位不默认在新机器启用。原工位与历史证据保留在来源归档；后续需要执行者时再登记，不冒充已保留原生对话记忆。

## 3. 方法库与复利证据

Workflow / Skill / Tool 定义以及 `references/` 中的范例随库保留。Catalog 是派生索引，应在验证库原件后重建；旧统计不能冒充新机器实测。

`.paos/usage-events/` 的事件是 append-only 原始证据，不是缓存。公开仓库忽略该目录；需要历史使用统计时应私下迁入相应事件。`init` 创建空目录只是满足核心的目录合同，不等于恢复了这些历史。

Tool Catalog 中的原机安装位置、可用性和验证日期也是待核信息，不能因为文档已复制就宣称工具已安装。

## 4. 首次显式登记新的最小 Project 记录

安装描述定位代码、data_root 和共享库，Project 登记只定位 OB 根目录、Home IDs 和 Coordinator。迁入一篇当前生效的项目口径，从该库 `INDEX.md` 指到此原文，不强制另建项目概览。Rooter 由安装级定位单独登记，不进入 Project 成员列表。

新登记文件位于 `<data_root>/project-registry/projects/<id>.json`，schema 为 `paos-project-registry/v1`，准确只有：

```json
{
  "schema": "paos-project-registry/v1",
  "id": "3002",
  "root_path": "<目标电脑上已存在的绝对项目目录>",
  "homes": ["3002-s010"],
  "coordinator_home_id": "3002-s010"
}
```

上面的路径是**解释性占位符**，不能直接作为有效登记。先确认实际 Coordinator Home ID 与现有 OB 根，再由 CLI `project register <id> --root <真实绝对目录> --coordinator <Home ID>` 建立；不会生成缺失的业务目录或猜测成员。不要把原机 Rooter、PID、Runtime UUID、旧安装路径或 Session 作为新机器的有效身份。

**不保留旧 Project JSON 运行兼容。** 如目标数据根已有原版 `paos-project/v3`，CLI 会拒绝读取/覆盖；先单独留好原件和项目证据，再使用独立的空数据根或在已核实的迁移位置重新登记。`project register` 不会自行搬走、裁切或替换任何旧字节，也不把迁移当成项目重新验收。原 Ledger/receipt 等若有历史证明价值，按原件归档，不重建假事件。

这一步只建立 Project locator，不能证明 TODO 原件、所有引用、Mail 或 native binding 已迁入；须分别回读并做新输入闭环测试。

## 5. 最后建立本机运行绑定

Runtime、认证、原生会话、Contact 执行定位、Receiver、端口和管道由目标机器重新建立。旧绑定可作为历史信息，不直接作为有效连接。保留 STOP 等耐久控制要求，不默认开启后台唤醒。

先离线读回 Rooter 和 Coordinator 的当前责任与必要原件，再用新的、可辨认的测试输入核对实际接收和消费。不要重放旧的不确定投递来做验收，也不要把发送成功当作已经消费。

## 6. 验证分别说清

`doctor` 只回答配置和必要路径是否一致；CLI 命令实跑回答程序入口是否可用；工位回读与原件检查回答能否接班；实际新输入的完整处理回答运行协作是否恢复。

各阶段分别记录 commit、配置位置、命令和真实结果。配置助手测试不替代核心测试，旧机器的 health/orient 记录也不替代新机器的闭环验证。
