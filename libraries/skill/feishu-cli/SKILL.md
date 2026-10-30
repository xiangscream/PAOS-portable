---
schema: paos-skill/v1
id: feishu-cli
title: Feishu CLI (lark-cli)
status: active
version: 2
name: feishu-cli
description: 通过已核验的 lark-cli 入口读取、编辑和创建飞书云文档（Docx/Wiki/Sheets）；跨 Codex/OpenCode/WorkBuddy 共享。当用户要求读取、修改、创建飞书文档，或给出 feishu.cn 文档链接时使用。云端是唯一事实源、写前保护用户手动编辑、写后必须回读验证。本册为主入口（环境、铁律、工作流与路由）；按任务读 references/ 四分册。
agent_created: true
---

# 飞书 CLI 操作技能（跨 Harness 共享入口）

> 本册是拆分后的主入口；详细经验按任务读 `references/` 四分册（统一从本册「任务路由」表取册名）：
> ① [读取与核对](references/reading-and-verification.md)（fetch 要点、双向比对、反向审计、验证清单）
> ② [分块写入与块操作](references/writing-and-block-ops.md)（update/replace/move/delete、表格、媒体、批量编辑硬规矩 81–96）
> ③ [画板 / 搬章 / 重编号配方](references/recipes-visual-chapter.md)（whiteboard/SVG、结构重排、字号分色规范）
> ④ [环境与编码故障](references/environment-and-encoding.md)（v1.0.70 双装、PATH、UTF-16、中文 argv、WSL NAT）
>
> 拆分来源：WorkBuddy `~/.workbuddy/skills/feishu-cli/SKILL.md`（1428 行 / 140KB）无损收录；原文在其他 Runtime 头部消费的"编号索引"与"已知结构问题"已收录至 [references/original-monolith-index.md](references/original-monolith-index.md)。引用原文编号时必须带节名（原文件规则：编号分属 20 套互不相干的清单，只有"操作纪律主线"跨节连续）。
> **共享入口**：本册位于 `PAOS-Libraries/skill/feishu-cli/`，Codex、OpenCode 与其他 Harness 直接从该目录读取；WorkBuddy 可用自己的 junction 指向同一目录，但共享能力不依赖某一 Harness。

## 编号索引说明（拆分后约定）

原单体的《编号索引》表（行 14–35）与已知结构问题（"操作纪律主线物理顺序断了"等）**已真实收录**在 [references/original-monolith-index.md](references/original-monolith-index.md)——这是 junction 切换后的检索替代与回溯依据，不指向原单体文件本身。原文编号分属 20 套互不相干的清单，跨分册引用必须带"节名 + 条目号"。

## 环境（2026-10-23 实测）

- **已验证 WSL 入口**：`/home/remo/.nvm/versions/node/v24.18.0/lib/node_modules/@larksuite/cli/bin/lark-cli`，`--version` 为 1.0.70；`auth status --json --verify` 退出 0，user ready/available/verified，身份可写。
- **Windows 是独立安装**：`C:/Users/remo/.workbuddy/binaries/node/cli-connector-packages/node_modules/@larksuite/cli/bin/lark-cli.exe` 为 1.0.87，当前 `auth status` 返回 not_configured；文件存在不等于可写，不复制/初始化其凭据。
- **PATH 不是全局判据**：不同 Harness/宿主可能解析到不同版本。先用 `command -v lark-cli`（或等价入口）与 `auth status --json --verify` 核验实际身份；WSL 已知可用时优先显式绝对路径，Windows 未配置时不要声称可写。按环境核验，不把“PATH 版本一概不可用”当普遍事实。
- user 与 bot 身份按实际 `auth status` 读取；编辑私人文档默认 user 身份。
- 每次会话先验证：

```bash
# WSL 原生（OpenCode 等）
/home/remo/.nvm/versions/node/v24.18.0/lib/node_modules/@larksuite/cli/bin/lark-cli --version
/home/remo/.nvm/versions/node/v24.18.0/lib/node_modules/@larksuite/cli/bin/lark-cli auth status --json --verify

# Windows/Codex 需要跨入 WSL 时
wsl.exe --exec bash -lc '/home/remo/.nvm/versions/node/v24.18.0/lib/node_modules/@larksuite/cli/bin/lark-cli auth status --json --verify'
```

- 成功标准以命令实际输出为准：版本、`identity=user`、`verified=true`、目标身份 ready；不硬编码用户 open_id。
- **WSL 网络断流**（timeout / network unreachable，多见 `authen/v2/oauth/token`）：疑似 NAT 出网丢失时**停下来报告用户，由用户决定是否重启 WSL——禁止不经许可 `wsl.exe --shutdown`**（会打断所有 WSL 会话与其他 Agent）。可用只读命令先确认是否真断流。详见④。

## 调用模板

Codex/Windows 跨入 WSL 时用 `wsl.exe --exec bash -lc`；OpenCode 等已在 WSL 内时直接调用已核验绝对路径，避免二次包装。若本机 `lark-cli` 已核验为可用 user 入口，也可用该入口。

```bash
# 读取（分层优先，不要一上来读全文；Windows→WSL）
wsl.exe --exec bash -lc '/home/remo/.nvm/versions/node/v24.18.0/lib/node_modules/@larksuite/cli/bin/lark-cli docs +fetch --doc "<url>" --scope outline --max-depth 4 --format json'

# 读取（WSL 原生）
/home/remo/.nvm/versions/node/v24.18.0/lib/node_modules/@larksuite/cli/bin/lark-cli docs +fetch --doc "<url>" --scope outline --max-depth 4 --format json

# 本地 md 全文写入（@file 必须相对路径，先 cd）
wsl.exe --exec bash -lc 'cd /mnt/c/<目录>; /home/remo/.nvm/versions/node/v24.18.0/lib/node_modules/@larksuite/cli/bin/lark-cli docs +update --doc "<url>" --command overwrite --doc-format markdown --content @./文件.md --format json'

# stdin 插入 block（推荐，比 @file 更稳）
wsl.exe --exec bash -lc 'cd /mnt/c/<目录>; echo "<whiteboard token=\"...\" />" | /home/remo/.nvm/versions/node/v24.18.0/lib/node_modules/@larksuite/cli/bin/lark-cli docs +update --doc "<url>" --command block_insert_after --block-id "<anchor>" --content -'
```

批量操作用 WSL Node 脚本 `spawnSync(larkCliPath, [参数数组])`；中文参数一律走 ASCII 文件传递（④）。

## 核心工作流（最短清单）

```
验证 CLI 身份 → 读历史记录(+history-list) + 云端 revision + outline
→ 对比上次写后快照，锁定用户手动修改（受保护段落）
→ section/keyword 局部 fetch --detail with-ids 拿 block ID
→ 选 str_replace（行内精确替换）/ block_replace|insert_after（结构操作）/ overwrite（仅用户明确要求重建全篇）
→ 执行写入 → 回读验证 revision_id 变化 + 新文本存在 + 旧文本消失 + 受保护段落未变
→ 清理临时脚本 → 报告云端已确认结果
```

## 铁律（不可违反）

1. **云端最新版是唯一事实源**，本地同名 md 不得默认覆盖云端。
2. **写前保护**：上次 Agent 写后 → 本次开始前的所有云端变化，默认视为用户手动编辑，不得覆盖；无可信基线时默认保留 + 请求确认。
3. **写后必须回读**，`ok: true` 不等于成功（revision 可能没变、`data.result` 可能是 `partial_success`——判据见②第 7 条）。
4. **overwrite 高危**：清空重建、丢评论/图片锚点，长文档只改几节时禁用；局部改动用 str_replace + block 操作。
5. Block ID 生命周期：overwrite/block_replace/block_delete 后旧 ID 失效，连续结构操作之间必须重新 fetch。
6. `str_replace` XML 模式只支持行内匹配；Markdown 模式支持跨行和 `前缀...后缀` 省略号语法。
7. 高风险操作 exit 10 + `confirmation_required` → 必须先向用户确认再加 `--yes`，禁止静默重试。
8. 不保存/输出任何 token、App ID、授权链接到文档或脚本。
9. 回滚用 `history_version_id`（≠ revision_id），仅在用户明确要求时执行。
10. 每次写入记录 before/after revision，保留写前基线快照 `<doc-token>-before-rev-<revision>-<timestamp>.md`。

## 任务路由（读哪一册）

| 任务 | 入口 |
| --- | --- |
| fetch 层级/截图核对、双向比对、发布前体检 | ① |
| str_replace / block_* / 批量重排 / 表格 / 媒体插入 | ② |
| SVG 画板、搬章节、全篇重编号 | ③ |
| 命令找不到 config / 输出乱码 / 中文参数截断 / NAT 断流 | ④ |
| 云文档**写**操作快速指令（不涉本册深配方） | `feishu-doc-edit` 技能 |
| lark 各域官方参考（drive/im/mail/…） | `lark-cli skills read <域> references/...` 或 `lark-<域>` 技能 |

## LRC101 / 项目专属约定

LRC101 专属飞书上下文的**唯一现行落点在 Project 2001**（由 2001-s009 归位）：
`C:\Users\remo\Desktop\OBSBOT-Projects\2001-LRC101\Works\Process\LRC101-Feishu-CLI项目约定.md`（导航见 2001 `INDEX.md` →「飞书 CLI 项目上下文」）。
本技能只维护通用命令与方法；2001 已声明旧口径（旧资料阅读指引、早期自主跟拍完整版、嵌套版/FPV 增强专项）不再作为现行产品入口。拆分批次原文交接材料保留在 3002 `Works/V12-OPERATING-REVIEW-20261002/feishu-cli-LRC101-pending-s009.md`（非现行入口）。

## 常见故障速查

现象与处理表见④；两条最高频：`not_configured identity=bot` = 调到了 v1.0.87（改绝对路径）；写入成功但 revision 没变 = 无效锚点或 no-op（重新 fetch 换块 ID）。
