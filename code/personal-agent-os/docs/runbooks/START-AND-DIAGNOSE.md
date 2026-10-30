# 启动与诊断手册

版本：v0.1 | 2026-07-31

## 系统五层组成

| 层 | 说明 |
|---|---|
| L1 服务 | Python HTTP 服务，绑定 `127.0.0.1:8766` |
| L2 端口 | 端口检测与占用验证 |
| L3 数据 | Dashboard JSON 数据（来自 Pipeline 扫描） |
| L4 来源 | 合成 Markdown（synthetic-vault）或真实 Private Data Root |
| L5 浏览器 | Dashboard 页面 + Tips 交互 |

## 依赖

- Python 3.11+
- Node.js 20+（仅 JS 测试；Dashboard 页面运行不依赖 npm）
- PowerShell 7 或 Windows PowerShell 5.1

## 环境变量

| 变量 | 用途 | 示例 |
|---|---|---|
| `PAOS_PYTHON` | 显式指定 Python 解释器路径 | `C:\path\to\python.exe` |
| `PAOS_NODE` | 显式指定 Node 路径 | `C:\path\to\node.exe` |
| `PERSONAL_AGENT_OS_INBOX` | 覆盖默认 Tips 收件箱路径 | `D:\MyInbox` |

## 启动

```powershell
# 推荐：双击桌面快捷方式或直接调用
.\scripts\start.ps1

# 或从仓库根目录手动启动 canonical server
python attention-dashboard-v1-static/paos_server.py --port 8766
```

`paos_server.py` 是当前 canonical 入口；它在现有 HTTP server 外层附加 build identity。直接运行旧 `local_server.py` 仅保留开发/历史兼容用途，Doctor 会把缺少 build identity 的实例视为无法证明与当前 checkout 一致。

## 停止

Ctrl+C 停止前台 Python 进程；Windows 后台实例使用 `scripts\stop.ps1`。

## 健康接口

```text
GET http://127.0.0.1:8766/api/health
→ {"ok":true,"service":"attention-dashboard-v1",...,"build":{"schema":"paos-build-identity/v1",...}}
```

运行实例还会通过响应头报告 runtime/static fingerprint；`start.ps1` 与 `doctor.ps1` 用这些值判断当前服务是否来自预期 checkout。

## 诊断

```powershell
.\scripts\doctor.ps1
```

按服务、health/build identity、页面、数据与来源逐层输出故障位置。

## 重建派生数据

```powershell
Remove-Item -Recurse -Force attention-memory-pipeline-v0/build
cd attention-memory-pipeline-v0
python scan_vault.py
```

## 验证

```powershell
.\scripts\verify.ps1
```

运行当前仓库的完整验证门禁；测试数量会随版本变化，以本次命令实际输出为准。
