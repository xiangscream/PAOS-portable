# Personal Agent OS 安装与恢复

PAOS 的代码与用户数据分开恢复：代码来自 Git；用户环境保存在 `private-data/`。`build/`、`runtime/` 等派生产物不进入安装级备份，可在新环境中重新生成。

## Windows 干净安装

在普通用户权限下即可准备 PAOS：

```powershell
git clone <PAOS repository URL>
cd personal-agent-os
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
powershell -ExecutionPolicy Bypass -File scripts\doctor.ps1
```

`install.ps1` 会：

- 检查 Python 3；也支持用 `PAOS_PYTHON` 指定解释器；
- 创建 PAOS 需要的 `private-data/` 目录；
- 在安全条件满足时生成缺失的 Dashboard 派生数据；
- 不要求管理员权限，不修改系统端口保留或网络配置。

如果已有 `build/` 但内容不完整，安装脚本会停止并给出显式处理提示，不会用 synthetic 数据覆盖已有派生产物。

## 升级现有安装

升级前先停止 PAOS 并做一次安装级备份：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
powershell -ExecutionPolicy Bypass -File scripts\backup.ps1
git pull
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
powershell -ExecutionPolicy Bypass -File scripts\doctor.ps1
```

`start.ps1` 会核对正在运行的服务与当前 checkout 的 build identity，不会把旧进程当作新版本继续使用。

## 安装级备份

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
powershell -ExecutionPolicy Bypass -File scripts\backup.ps1
```

默认备份到用户 Documents 下的 `PAOS Backups`。也可以指定目录：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\backup.ps1 -Destination "D:\我的 PAOS 备份"
```

备份 ZIP 包含：

- `private-data/` 中实际存储的文件；
- `paos-backup-manifest.json`，记录创建时间、来源 commit、文件数量和备份范围。

备份 ZIP 不包含：

- `build/`、`runtime/` 等可重建派生产物；
- Secret Store 内容；
- `private-data/` 文件中引用的外部 Vault、插件目录或其他外部路径的实际内容。

外部路径的引用文本会随其所在配置文件一起保存，但引用目标不会被递归复制。`private-data/` 下的符号链接也不会被跟随；跳过项会记录在 manifest 中。

备份要求 PAOS 服务先停止，避免在多个状态文件同时变化时得到不一致的环境快照。

## 恢复整个 PAOS 用户环境

在新 checkout 中先运行 `install.ps1`，再恢复备份：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\restore-backup.ps1 -Archive "D:\我的 PAOS 备份\paos-backup-20260912-160000.zip"
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
powershell -ExecutionPolicy Bypass -File scripts\doctor.ps1
```

恢复流程会先校验 ZIP 和 manifest，再在临时目录中展开，最后替换 `private-data/`。如果当前 `private-data/` 已有文件，`restore-backup.ps1` 会先自动生成一份 `paos-pre-restore-*.zip`，只有这一步成功后才继续恢复。

恢复不会修改 Secret Store，也不会尝试复制或重建外部引用目标。外部 Vault、插件和其他受控路径需要在新机器上分别准备，并保持配置中的路径有效。

## Project Restore 与安装级 Restore

两者用途不同：

| 操作 | 作用范围 | 用途 |
|---|---|---|
| Project 页“恢复上一版” | 单个 Project 的业务状态 | 撤销项目 JSON 的一次错误修改 |
| `restore-backup.ps1` | 整个 `private-data/` 用户环境 | 换机器、损坏恢复、升级回退 |

Project Restore 使用 `private-data/project-registry/backups/` 中的项目级历史，不代替整机备份。安装级 Restore 也不会替你选择某个 Project 的历史版本；它恢复的是备份时整个用户环境的状态。

## 常见故障

| 故障 | 处理 |
|---|---|
| PAOS/看板打不开 | 运行 `scripts\doctor.ps1` 定位故障层 |
| 服务端口冲突 | 运行 `scripts\stop.ps1`；未知进程不会被自动结束 |
| 当前进程与 checkout 版本不一致 | 运行 `scripts\restart.ps1`，再运行 Doctor |
| `dashboard-data.json` 缺失 | 运行 `scripts\install.ps1`；已有不完整 `build/` 时按脚本提示显式处理 |
| 单个 Project 被误改 | 使用 Project 页“恢复上一版” |
| 整个 `private-data/` 损坏或迁移 | 从最近的安装级 ZIP 运行 `restore-backup.ps1` |
| 浏览器本地状态异常 | 清除对应 localhost 站点的 localStorage 后刷新 |
| Tips 写入失败 | 检查 `private-data/inbox/tips` 权限与磁盘状态 |

## 回到上一代码版本

用户数据与 Git 版本分离。需要回退代码时，先停止并备份，再切换到上一个已验证 commit：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
powershell -ExecutionPolicy Bypass -File scripts\backup.ps1
git checkout <previous-verified-commit>
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
powershell -ExecutionPolicy Bypass -File scripts\doctor.ps1
```

如果旧代码不兼容较新的 `private-data/`，使用升级前生成的安装级备份恢复对应用户环境。不要把 Secret Store、外部 Vault 或插件目录当作 PAOS ZIP 的一部分。
