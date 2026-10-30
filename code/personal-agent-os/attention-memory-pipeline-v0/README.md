# Markdown 记忆管道 v0

本实验验证：

> 如何把 Obsidian / Markdown 文件变化，只读转换成带来源的任务、Tips、项目状态、归档对象和夜间审核候选。

## 边界

- 只读取 `synthetic-vault`；
- 不访问真实 Obsidian、工作目录或 Agent 聊天；
- 不调用模型；
- 不改写来源 Markdown；
- 所有规则推断只能进入 `candidate`；
- 检测到密钥类字段时，整篇笔记阻止摄取，且不回显字段值。

## 运行

先预览，不写文件：

```powershell
python scan_vault.py --source synthetic-vault --dry-run
```

确认后生成统一状态：

```powershell
python scan_vault.py --source synthetic-vault
```

输出：

- `build/attention-state.json`：Dashboard 可消费的统一对象；
- `build/source-manifest.json`：文件哈希与变化基线；
- `build/scan-report.md`：人工可读扫描报告。

第二次运行时，扫描器自动与上一次 manifest 比较新增、修改、删除和未变化文件。

## 最小字段契约

每篇可摄取笔记至少包含：

```yaml
---
schema: attention-note/v0
id: stable-id
object_type: thread_state
domain: work
project: LRC101
thread: report-mainline
status: active
review_state: reviewed
sensitivity: internal
updated: 2026-07-29T08:30:00+08:00
---
```

任务排序可选字段：

- `attention`
- `blocking`
- `external_commitment`
- `due_at`
- `long_term`
- `last_progress_at`
- `weekly_target`
- `weekly_progress`

活动任务建议在正文中保留三段执行闭环：

- `## 当前唯一问题`
- `## 阶段交付物`
- `## 完成定义`

这三项保持为向后兼容的可选字段；缺失时扫描器保留空值，由界面明确提示补充，不自动编造内容。

## 对象与候选的区别

- `source_objects`：Markdown 已明确声明的对象；
- `review_candidates`：扫描规则发现的推进债务、过期、冲突、缺少作用域、重复或未经审核模式；
- `tips`：只捕获，不进入任务；
- `source_index`：每个对象都能回到相对路径、哈希和行号。

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试覆盖：

- 来源文件扫描前后哈希不变；
- 每个对象都有来源引用；
- Tip 不进入任务；
- 冲突只生成候选；
- 缺少项目作用域会被标记；
- 密钥类字段阻止摄取；
- dry run 不写文件；
- 新增、修改和删除能被识别。

