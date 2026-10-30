# PAOS Portable — Agent 工作底座

正常入口是 `scripts/paos.py`。项目与工位读取直接使用本机登记和文件，
不需要旧 Core HTTP 服务；CAT 和显式原生提醒是外部运行通道。

## 先读什么

开发先读 `docs/DEVELOPMENT-PRINCIPLES.md`。业务方法从安装的
`libraries/workflow/Guides/guide-work-method.md` 按需进入；不在源码复制第二套流程。

## 代码边界

- `paos_registry.py`：只读既有 `<data_root>/project-registry/projects/<id>.json`，定位项目及成员；不写项目、不创建替代状态库。
- `paos.py`：参数、调用既有模块、输出结果。仅 CAT 使用本文件的 HTTP 客户端。
- `paos_home.py`、`paos_workstation.py`：固定工位定位和文件；Rooter 是安装级工位。
- `paos_todo_v3.py`：现有 TODO 解析与写入；本片没有改成自由 Markdown 格式。
- `paos_mail.py`、`paos_notice.py`、`paos_attention_service.py`：持久输入与处理事实；不再生成第二份 Workbench 当前页。
- `paos_library.py`：Workflow/Skill 索引、搜索与使用记录；正文是方法，不是硬状态机。
- Contact / runtime injection：显式本机绑定与一次提醒；不从迁入的 Project 旧字段恢复原生会话。

不再提供旧 `session`、`coordinator`、`workbench`、`tips` HTTP 代理和
`project progress-update`。用户要求/项目概览不再作为 CLI 需要维护的字段。
历史数据未被此代码变更删除。尚存未使用旧模块按实际调用继续裁减，不恢复旧服务来补接口。

## 验证

在包根或任意工作目录执行：

```text
python code/personal-agent-os/scripts/verify.py
```

验证当前包：初始化/真实文件接续、接收器/安装合同、保留的扫描管道和 Python 语法。
不是原系统 Dashboard 的七道门，也不是生产工位、原生模型或 Windows Desktop 采用证明。

仅改本次具名代码与材料。真实项目、工位、凭据和生产服务不因测试被更改。
