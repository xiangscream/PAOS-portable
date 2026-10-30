---
schema: paos-tool-catalog/v1
description: 机器本地执行工具索引——每条以真实任务核实后登记；可用状态附检查时间与依据。不把安装成功当可用。
---

# Tool Catalog（机器本地）

| tool_id | 用途 | 安装位置（真实路径） | 调用入口 | 关键 IO | 依赖环境 | 维护者 | 可用状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| lark-cli | 飞书全域操作（Docx/Wiki/Sheets/Drive/IM/Mail…） | 共享入口：`PAOS-Libraries/skill/feishu-cli/`。WSL 已验证绝对路径 `/home/remo/.nvm/versions/node/v24.18.0/lib/node_modules/@larksuite/cli/bin/lark-cli`（v1.0.70，user verified）；Windows 1.0.87 独立安装当前 not_configured，不因文件存在视为可写 | 先 `lark-cli auth status --json --verify` 核验实际入口；`lark-cli <域> <动词> --help` | URL/token → JSON；不落 token 到文档 | 各 Harness 从共享 Skill 读取；WSL 配置 `/home/remo/.lark-cli/config.json`（user=张瑞翔） | 安装级（rooter-001 持有 config） | WSL 2026-10-23 auth verified；Windows profile 未配置，待处理 |
| c-index | C 盘资料元数据索引（查询非扫描） | `C:\Users\remo\Documents\资料索引\index_tool.py` + `2026-10-02_2138\files.sqlite` | `python -X utf8 index_tool.py search\|children\|omissions` | 关键词/路径 → ≤80 行元数据；不读正文不移动 | 本机 Python 3.11+；快照一致性条款见入口.txt | 资料管理会话（唯一扫描/发布方） | 已核实（r054 报告 2026-10-03：中文/空格/深层检索可用、stat 一致） |
| ffmpeg | 视频/音频处理与抽帧 | `imageio_ffmpeg.get_ffmpeg_exe()` 自带二进制；winget 版在 PATH | `ffmpeg -y -ss <t> -i in.mp4 -frames:v 1 out.jpg` | 流 → 文件/帧 | 托管 venv `pip install Pillow imageio-ffmpeg` | 本人（使用） | 已核实（feishu-cli 抽帧配方实测） |
| python | 执行底座 | WSL `/usr/bin/python3`（3.14） / Windows Python 311 | `python3 -X utf8 …` | — | WSL2 原生 shell（HOME 冲突场景见 feishu-cli ④ 姿势） | 安装级 | 已核实（r054/P AOS CLI 全走通） |
| node | 执行底座 | `/home/remo/.nvm/versions/node/v24.18.0/bin/node`（版本目录会改名——动态读别硬编码版本号） | `node x.js` | — | bash -lc 不加载 nvm——run.sh 显式 export PATH | 安装级 | 已核实 |
| dot-consult | 蒻芷团队的网页研究、推演与 GitHub 协作 | 稳定 Home `3002-s033`；网页侧会话独立 | [研究与咨询](workflow/Guides/guide-research-consultation.md)；当前收信安排读该指南指向的 CONTACT-STATE | 问题、事实与预期成果 → 原始答复、来源、代码或 PR | 模型与联系渠道按当前任务及 Human 设置 | Rooter协调，提问者判断采用 | 本人往返与当前接续条件以 CONTACT-STATE 为准；不在工具表复制 ACK、Wake 或模型状态 |

## 登记口径

- 登记经真实任务或现场核实的工具用途、位置、调用入口、维护者与检查时间；具体操作和当前限制链接唯一指南。
- `可用状态` = as_of + 依据；引用失效以实际任务判定为准。
- 历史排障脚本（8/26 轮一次性件）已按 w062 归档 `工作归档\2026-10-02下载整理\2001旧CAT诊断脚本\`——**不是 current 工具**，不在本表。
