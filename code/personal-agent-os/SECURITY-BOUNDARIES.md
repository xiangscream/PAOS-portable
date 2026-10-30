# Personal Agent OS 安全边界

版本：v0.1 | 2026-07-31

## 四层数据

| 层级 | GitHub | 默认位置 | 说明 |
|---|---|---|---|
| Code & Planning | 跟踪 | 仓库工作区 | 代码、Skill、设计、脱敏样例、任务包 |
| Private Data | 忽略 | `private-data/` | Vault 副本、Inbox、DB、raw logs、个人资料 |
| Derived Data | 忽略 | `build/` | 索引、缓存、扫描报告、构建产物 |
| Secret Store | 永不 | 环境变量 / 系统密钥存储 | Key、Token、密码 |

## 永不进入 Git

- `private-data/` 及所有子目录
- `build/` 及所有子目录
- `__pycache__/`、`*.pyc`
- `.env`、`.env.*`
- `*.log`、`*.db`、`*.sqlite`、`*.sqlite3`
- `.pem`、Key、Token、密码
- 公司内网 URL、内部项目名称、真实业务数据

## Secret Store 独立规则

- Secret Store 路径为独立根目录，不放入仓库
- 不参与自动扫描、索引、夜间整理或归档复制
- Agent 只能引用逻辑名称（如 `company-llm`）
- 不得在 Markdown、Prompt、截图或 Git 历史中记录真实凭据

## 可疑内容上报

发现任何疑似凭据进入仓库时，立即停止当前操作，报告路径和模式类型（不回显值），等待人工处置。
