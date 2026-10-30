# 原生消息注入

`scripts/runtime_injection.py` 向已配置的原生会话发送一次消息。Python 接口：

```python
from runtime_injection import inject
receipt = inject(target, message)  # scripts 已在 Python 模块路径中
```

独立 CLI 为 `python scripts/runtime_injection.py`，从标准输入读取 UTF-8 JSON，向标准输出返回 JSON；成功退出 0，调用错误退出 1。

```json
{"target":{"runtime":"workbuddy","session_id":"已授权原生会话ID","runtime_file":"C:/path/to/product-authorized-extension/.runtime.json"},"message":"请读取当前工位新消息并继续本人责任。"}
```

目标来自已配置的真实联系信息：

| runtime | 必填目标字段 |
|---|---|
| codex | `session_id`、`extension.receiver_runtime_file`；接收器由目标本人从正常 Desktop 环境准备，发送方不借 Desktop 身份 |
| opencode v1 | `session_id`、`base_url`；原服务应已运行；`api_version`省略或为1 |
| opencode v2 | `session_id`、`base_url`、`api_version:2`、`auth_file`；使用已启动服务的正常Basic授权 |
| workbuddy | `session_id`、`runtime_file`；正常加载的本地扩展须已授权该目标 |

三者均可提供显式 `stop_file`。文件存在即停止发送；不从 Project 或 Work 推导停止路径。OpenCode/WorkBuddy HTTP 可用 `timeout_seconds` 设置原生调用超时，默认 30 秒。Windows locator 在 WSL 按已有路径解析合同处理。

默认省略模型参数，继承目标当前选择。只有 Human 明确指定时才给 `inject(..., model=...)` 或输入 JSON 的 `model`：Codex/WorkBuddy 为原生模型名字符串，OpenCode v1为含 `providerID` 与 `modelID` 的对象。v2.0.32的单条prompt不接受模型参数；本工具遇到显式模型参数会拒绝，不额外调用持久化模型切换接口。

`paos wake trigger <project> <home> --model MODEL` 使用同一合同。OpenCode 必须传一个完整 JSON 参数，不能传 `provider/model` 字符串。Bash/WSL 示例（替换 Project、Home 和现存消息路径，仅在 Human 已指定该模型时执行）：

```bash
paos wake trigger <project> <home> --prompt @<message-file> \
  --model '{"providerID":"opencode","modelID":"mimo-v2.6-flash-free"}'
```

Codex/WorkBuddy 的 `--model` 值是各自的原生模型名字符串，不使用上述 OpenCode 对象。其他 Shell 也须将整个 JSON 保留为一个参数；上例的引用方式适用于 Bash/WSL。

受理结果含 `accepted:true`、`runtime` 和 `session_id`。Codex正常接收器还返回 `native_status_before_submit`，只表示提交前观察；OpenCode v1含原生 `http_status:204`，v2为200并返回已关联的`message_id`和原生`native_disposition`（steer或queue）；WorkBuddy含本次原生 `request_id` 与 `native_disposition`，不返回整段SDK内容。明确拒绝为 `InjectionError` / `accepted:false`；可能已发送但回执不明为 `InjectionUncertain` / `accepted:null`、`retry:false`。受理不代表业务消费或成果。

Codex正常接收器对明确active/idle/notLoaded向既有App Tools跟进入口提交一次，不因active预先拒绝，也不指定或保证steer/queue；模型与Follow-up设置沿Human。未知状态、STOP和实例核验保持。目标本人更新接收器及确认实际加载，读[本人接收器说明](CODEX-SELF-REMINDER.md)。OpenCode v1按原目录读会话与状态后提交一次prompt_async，204仅表示原生受理，不推定queue或完成；v2的发送与关联回执见下方接入说明。两者仍使用进程退出自动释放的互斥。WorkBuddy使用产品自身调用合同。

WorkBuddy回环建立连接前明确被拒绝时，返回 `receiver_offline` / `receiver_connection_refused` / `accepted:false`。当前扩展在调用sendPrompt前返回的400/401/404为明确拒绝；SDK调用后502、连接超时/复位、响应丢失或关联回执不符仍是结果未知，不据此自动重发。S014等目标仍须取得产品支持的正常扩展安装与权限入口，错误分类不代替恢复。

工具不自动重试、启动Runtime、保存attempt或观察模型完成，也不加载Project Store、Work或Notice。旧消息是否已处理由调用方在工位当前读面判断；既有拒绝和不确定回执保持原样，不因实现更新重放。

## OpenCode v2 Windows接入

正常运行维护者用产品`OPENCODE_PASSWORD`设置本机服务密码，并在本机私有文件保存`{"password":"服务设置的同一密码"}`。`auth_file`只登记该文件路径；密码不写Contact、命令参数、项目成果或Git，不提取其他会话凭据。此合同在Windows OpenCode2.0.32上验证，用户名为产品固定值`opencode`。

```json
{
  "runtime": "opencode", "api_version": 2,
  "session_id": "原生会话ID", "base_url": "http://127.0.0.1:当前端口",
  "auth_file": "C:/本机私有目录/opencode-server-auth.json",
  "stop_file": "C:/原目标的STOP路径",
  "extension": {
    "execution_environment": "windows",
    "windows_python": "C:/实际Python/python.exe"
  }
}
```

按已安装CLI的`wake bind --driver-config`正常登记以上目标，不改原会话ID、模型或STOP。Windows进程直接发送；WSL发送者在任何HTTP请求前选择已登记的Windows Python，沿同一安装Source入口传一次UTF-8 stdin，仅传目标定位字段，不把密码带到子进程参数中。失败后不改走WSL回环或另一版API。

v2路径为：`GET /api/session/<id>`核原ID及`location.directory` → `GET /api/session/active`读全服务活动状态 → STOP → 一次`POST /api/session/<id>/prompt`，正文只有本次`id`和`text`。200回执必须关联相同会话及本次消息ID；丢失、不可解析、错关联或服务端执行结果不明均保持unknown，不重发。与v1的差异由`api_version`显式选择，不做失败后自动探测或降级。

人工查看v2用`opencode --server <URL> --session <ID>`，其客户端也须取得运行维护者设置的正常`OPENCODE_PASSWORD`；Contact不显示密码。v1继续使用`opencode attach`，直至原目标正式迁完。数据迁移、独审、发布和真实业务读取通过前，不切自动Contact。

PAOS 通信层先持久投递原消息，再解析员工联系信息调用同一 `inject`；注入失败不得删除原信。安装升级由正常发布流程统一接线并退役旧消费者，独立模块存在不等于实际安装已采用。
