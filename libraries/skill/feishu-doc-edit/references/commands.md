# feishu-doc-edit 命令示例库

从 `lark-cli skills read lark-doc references/lark-doc-update.md` 提炼的可直接复制命令。所有命令在 WSL 内执行，外层单引号防 PowerShell 展开 `$PATH`。

## 基础前缀

```bash
LARK='wsl.exe --exec bash -lc '\''export PATH=/home/remo/.nvm/versions/node/v24.18.0/bin:$PATH;'
# 实际执行示例：
wsl.exe --exec bash -lc 'export PATH=/home/remo/.nvm/versions/node/v24.18.0/bin:$PATH; lark-cli docs +update --doc "<doc_url>" ...'
```

## str_replace — 文本替换

```bash
# 简单替换
lark-cli docs +update --doc "<doc_url>" --command str_replace \
  --pattern "张三" --content "李四"

# 替换为富文本（加粗 + 链接）——XML 默认格式
lark-cli docs +update --doc "<doc_url>" --command str_replace \
  --pattern "旧链接" --content '<b>新链接</b> <a href="https://example.com">点击查看</a>'

# 删除文本：content 传空串
lark-cli docs +update --doc "<doc_url>" --command str_replace \
  --pattern "废弃的内容" --content ""

# Markdown 模式跨行替换（--pattern 与 --content 需真实换行，推荐 heredoc）
lark-cli docs +update --doc "<doc_url>" --command str_replace \
  --doc-format markdown \
  --pattern "$(printf '## 旧标题\n\n第一段原文')" \
  --content - <<'EOF'
## 新标题

改写后的第一段
EOF

# Markdown 省略号语法：匹配「## 旧标题」到「结束语。」之间的全部内容并整体替换
lark-cli docs +update --doc "<doc_url>" --command str_replace \
  --doc-format markdown \
  --pattern "## 旧标题...结束语。" \
  --content - <<'EOF'
## 新标题

重写后的正文...

新的结束语。
EOF
```

## block_insert_after — 锚点后插入（逐章填写的正确姿势）

```bash
# 在指定 block 之后插入新章节
lark-cli docs +update --doc "<doc_url>" --command block_insert_after \
  --block-id "目标block_id" \
  --content '<h2>新章节</h2><ul><li>要点 1</li><li>要点 2</li></ul>'

# 文末追加（等价于 append）
lark-cli docs +update --doc "<doc_url>" --command block_insert_after \
  --block-id -1 \
  --content '<h2>结尾章节</h2><p>正文内容</p>'
```

## block_replace — 替换整块

```bash
# 富文本标题被 str_replace 弄坏时，用 block_replace 重建整块
lark-cli docs +update --doc "<doc_url>" --command block_replace \
  --block-id "损坏的block_id" \
  --content '<h1>正确标题</h1>'
```

## block_delete — 删除块（可批量）

```bash
lark-cli docs +update --doc "<doc_url>" --command block_delete \
  --block-id "block1,block2,block3"
```

## block_move_after / block_copy_insert_after — 移动/复制

```bash
# 移动已有块
lark-cli docs +update --doc "<doc_url>" --command block_move_after \
  --block-id "锚点block_id" --src-block-ids "源block1,源block2"

# 复制源块到锚点后（源块保留）
lark-cli docs +update --doc "<doc_url>" --command block_copy_insert_after \
  --block-id "锚点block_id" --src-block-ids "源block1"
```

## overwrite — 整篇重建（⚠️ 高危，仅用户明确要求）

```bash
# 本地 md 全文写入（@file 必须相对路径，先 cd）
wsl.exe --exec bash -lc 'cd /mnt/c/<目录>; export PATH=/home/remo/.nvm/versions/node/v24.18.0/bin:$PATH; lark-cli docs +update --doc "<doc_url>" --command overwrite --doc-format markdown --content @./文件.md --format json'

# 危险：会清空文档内所有已插入的图片 block，并覆盖用户在飞书 web 上的手动修改
```

## 获取 block ID（写操作前置）

```bash
# outline 拿标题锚点
lark-cli docs +fetch --doc "<doc_url>" --scope outline --max-depth 4 --format json

# 局部 fetch 拿 block ID（--detail with-ids）
lark-cli docs +fetch --doc "<doc_url>" --scope section --start-block-id "<headingID>" --detail with-ids --format json
# 或 keyword 定位
lark-cli docs +fetch --doc "<doc_url>" --scope keyword --keyword "目标词" --detail with-ids --format json
```

## 写后回读验证

```bash
# 验证 revision + 新文本存在 + 旧文本消失
lark-cli docs +fetch --doc "<doc_url>" --scope full --doc-format markdown --format json
# 关注：data.document.revision_id 是否变化；content 中新旧文本状态
```

## 临时文件路径约定

- WSL 输出重定向：`/mnt/c/Users/remo/WorkBuddy/2026-08-10-09-52-48/<name>.json`（Windows 侧 Read 读取，避免中文乱码）
- 用完删除（走回收站）：`python C:/Users/remo/.workbuddy/tools/recycle.py "<path>"`
