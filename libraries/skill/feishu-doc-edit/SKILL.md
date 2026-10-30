---
schema: paos-skill/v1
id: feishu-doc-edit
title: Feishu Doc Edit
status: active
version: 1
name: feishu-doc-edit
description: 通过 WSL lark-cli 编辑飞书云文档（Docx/Wiki）的写入技巧。当需要修改、更新、插入、删除、移动飞书文档内容，或避免 overwrite 破坏用户手动编辑时使用。核心原则：写前必抓云端最新版、保护用户手动编辑、写后必须回读验证、禁止无确认 overwrite。读取操作见 feishu-cli 技能。
agent_created: true
---

# 飞书文档编辑技巧（lark-cli docs +update）

编辑飞书云文档的**写入操作**手册。聚焦"怎么改"——指令选择、格式规则、写后验证、常见坑。读取操作见 `feishu-cli` 技能。

## 环境（与 feishu-cli 相同）

```bash
wsl.exe --exec bash -lc 'export PATH=/home/remo/.nvm/versions/node/v24.18.0/bin:$PATH; lark-cli auth status --json --verify'
```

- WSL 内 lark-cli，user 身份编辑私人文档（用户：张瑞翔）
- 操作前先读 CLI 内置参考（与 CLI 版本匹配，禁止 grep 本地 SKILL.md 替代）：
  ```bash
  lark-cli skills read lark-doc references/lark-doc-update.md
  ```
- 终端中文乱码是解码问题，云端正文正常，不要据此改写云端。标准做法：WSL 内重定向到 `/mnt/c/...` 的 json，再用 Read 读文件。

## 铁律（违反即事故）

1. **写前必抓云端最新版**：`docs +fetch --scope outline` + revision。本地旧稿不是现状——他人可能已编辑过。
2. **保护用户手动编辑**：上次 Agent 写后到本次开始前的所有云端变化，默认视为用户手动编辑，不得覆盖。无可信基线时保留 + 请求确认。
3. **写后必须回读验证**：`ok: true` 不等于成功。确认 revision 变化 + 新文本存在 + 旧文本消失 + 受保护段落未变。
4. **禁止 overwrite**：`--command overwrite` 会清空文档内所有图片 block、覆盖用户手动修改（删图/改文）。仅用户明确要求重建全篇时使用，且先确认。
5. **Block ID 有生命周期**：`overwrite`/`block_replace`/`block_delete` 后旧 ID 失效；连续结构操作之间必须重新 fetch。
6. 高风险操作需确认：exit 10 + `confirmation_required` → 先向用户确认再加 `--yes`，禁止静默重试。
7. 不输出 token/App ID/授权链接到文档或脚本。
8. 每次写入记录 before/after revision；保留写前基线快照 `<doc-token>-before-rev-<revision>.md`。

## 指令选择矩阵（先选操作，再写内容）

| 要做什么 | 指令 | 必填参数 |
|---|---|---|
| 改一个词/短语 | `str_replace` | `--pattern` `--content` |
| 删除一段文本 | `str_replace`（content 传空串） | `--pattern` |
| 删除指定块（可批量） | `block_delete` | `--block-id`（逗号分隔） |
| 在某块之后插入新内容 | `block_insert_after` | `--block-id` `--content` |
| 替换整块 | `block_replace` | `--block-id` `--content` |
| 复制已有块到锚点后 | `block_copy_insert_after` | `--block-id` `--src-block-ids` |
| 移动已有块到指定位置 | `block_move_after` | `--block-id` `--src-block-ids` |
| 文末追加 | `append`（= block_insert_after --block-id -1） | `--content` |
| 整篇重建（⚠️仅用户明确要求） | `overwrite` | `--content` |

**通用参数**：`--doc <url|token>`、`--doc-format xml|markdown`（默认 xml）、`--revision-id`（默认 -1 最新）、`--dry-run`（先试跑）、`--content @file`（相对路径文件）。

## 格式选择规则

- **局部精修**（str_replace / block_insert_after / block_replace / block_delete / block_move_after）：**优先 XML**（默认）。XML 能稳定表达 block 结构和样式；不要因为 Markdown 写起来简单就自行切换。
- **整段写入**（append / overwrite）：XML 和 Markdown 均可。用户提供 `.md` 本地文件或明确要求 Markdown 时用 Markdown，否则默认 XML。
- **Markdown 局限**：不携带 block ID、无样式（颜色/对齐/callout）。需要按 block ID 定位时，先 `docs +fetch --scope outline|range|keyword|section --detail with-ids` **局部获取**目标段落，不要全量 fetch。拿到 block ID 后 `--content` 仍可用 Markdown。
- **str_replace 匹配范围**：
  - XML 模式：`--pattern` 只支持**行内匹配**，不能跨 block/段落。涉及整段或多 block 改动，改用 `block_replace`。
  - Markdown 模式：支持**行内 + 跨行匹配**；支持 `前缀...后缀` 省略号语法（三个英文句点串联首尾片段，中间内容整体被替换）。
- **多行内容推荐 heredoc 或 `--content @file.md`**，避免 shell 转义踩坑。

## 写前工作流（每次编辑前走完）

```
验证 CLI 身份 → 读历史记录(+history-list) + 云端 revision + outline
→ 对比上次写后快照，锁定用户手动修改（受保护段落）
→ section/keyword 局部 fetch --detail with-ids 拿 block ID
→ 选指令（见矩阵）→ 执行写入
→ 回读验证 revision 变化 + 新文本存在 + 旧文本消失 + 受保护段落未变
→ 清理临时脚本 → 报告云端已确认结果
```

## 常见故障速查

| 现象 | 处理 |
|---|---|
| `invalid file path` | @file 用了绝对路径 → 先 cd 再用 `@./文件名` |
| node: command not found | PowerShell 破坏 $PATH → 外层单引号 + 显式 export PATH |
| 写入成功但 revision 没变 | 无效锚点或 no-op → 重新 fetch 换有效 block ID |
| 标题被替换成残句 | 富文本 span 局部匹配 → 取 block ID 用 block_replace 重建整块 |
| 中文乱码 | 终端解码问题，云端正文实际正确，不要据此改写云端 |
| Wiki URL 无法操作 | 先 `lark-cli drive +inspect --url "<wiki-url>"` 取底层 token |
| exit 10 + confirmation_required | 高风险操作 → 先向用户确认再加 `--yes` |
