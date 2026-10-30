---
schema: paos-skill/v1
id: docx-safe-editing
title: Docx Safe Editing
status: active
version: 2
name: docx-safe-editing
description: Use when editing existing Word .docx reports, especially documents with generated tables of contents, numbered headings, captions, or strict government/company report formatting. Prevents正文误入目录、标题层级错乱、目录域损坏, and requires structural comparison against the original document before delivery.
---

# DOCX Safe Editing

Use this skill before modifying an existing `.docx` file when the document has a table of contents, numbered headings, captions, or a strict report template.

## Core Rule

Never infer heading styles from nearby paragraphs. Word TOC behavior depends on styles and field settings, not just visible text.

Before editing:

1. Make a timestamped backup.
2. Inspect the original document's heading styles and TOC field.
3. Identify body section boundaries by real body headings, not TOC entries.
4. Apply edits only inside the body range.

After editing:

1. Validate the `.docx` zip.
2. Compare `Heading 1-3` sequence against the original unless intentionally changing the document structure.
3. Confirm ordinary正文 paragraphs are `Normal`, not `Heading 1/2/3`.
4. Confirm added lower-level headings use the correct lower style, usually `Heading 4`, if the original TOC is `TOC \o "1-3"`.
5. For every edited section, print the paragraph range, child headings, unexpected styles, and the first few paragraphs after each newly added heading.

## Known Failure Pattern

In a report where the original TOC field is:

```text
TOC \o "1-3" \h \z \u
```

`Heading 1`, `Heading 2`, and `Heading 3` enter the table of contents. `Heading 4` normally does not.

Do not set body paragraphs or fourth-level headings such as `2.4.4.1` to `Heading 2` or `Heading 3`. That writes正文 into the generated TOC after Word updates fields.

Correct mapping:

```text
2                -> Heading 1
2.4              -> Heading 2
2.4.4            -> Heading 3
2.4.4.1          -> Heading 4
ordinary正文       -> Normal
```

If the document uses localized Word style names, inspect existing styles instead of guessing. In `python-docx`, Chinese Word UI labels may appear as English internal names, for example:

```text
“4级标题”  -> Heading 4
“正文文本” -> Body Text
```

Apply existing styles only. Do not redefine style formatting unless the user explicitly asks.

## Lessons From Multi-Round DOCX Repair

These failure modes are common when editing existing reports:

- **File lock**: If saving the target file raises `PermissionError`, the file is probably open in Word/WPS. Do not keep retrying destructive writes. Save a repaired copy such as `*-修正版.docx` and report that the original was locked.
- **TOC pollution**: If body paragraphs accidentally use `Heading 1/2/3`, Word will put正文 into a `TOC \o "1-3"` table of contents. Fix body paragraphs back to the document's正文 style.
- **Wrong child heading level**: If optional child sections such as `2.4.4.1` should not enter the existing TOC, use `Heading 4`, not `Heading 3`.
- **Reverse insertion**: Repeated `addprevious()` before the same anchor can reverse paragraph order. Prefer inserting sequentially after the section heading with `addnext()` and updating the current insertion pointer.
- **Stale anchor after deletion**: If you delete a range and then insert relative to a paragraph object captured before deletion/reload, content may be inserted in the wrong place or appended near the end. Recompute anchors after deletion, or use a stable section heading paragraph that remains in the document.
- **Inheriting corrupted structure**: Do not extract replacement content from a working document that already has wrong order or wrong styles. Use a known-good source, a clean generated content list, or manually structured content.
- **Section-specific validation**: Comparing only global `Heading 1-3` is not enough. Also validate each edited section's child headings,正文 styles, and paragraph order.

Preferred robust replacement pattern:

1. Locate the preserved section heading, such as `2.4.4 场景感知和路径规划实现技术方法`.
2. Delete only the body paragraphs until the next preserved peer heading, such as `3 总体实现实施方案`.
3. Insert new paragraphs sequentially after the preserved heading with `addnext()`.
4. For each inserted paragraph, explicitly apply either the existing child heading style or the existing正文 style.
5. Validate that the next peer heading still follows the edited section and no content leaked after later sections.

## Reliable Inspection Snippet

Use this before and after editing:

```python
from docx import Document
from pathlib import Path

path = Path("document.docx")
doc = Document(str(path))

for i, p in enumerate(doc.paragraphs):
    t = p.text.strip()
    if t and p.style.name.startswith("Heading"):
        print(i, p.style.name, t[:120])
```

To compare against an original:

```python
from docx import Document

def heading_sequence(path, levels=("Heading 1", "Heading 2", "Heading 3")):
    doc = Document(path)
    return [
        (p.text.strip(), p.style.name)
        for p in doc.paragraphs
        if p.text.strip() and p.style.name in levels
    ]

print(heading_sequence("edited.docx") == heading_sequence("original.docx"))
```

If this returns `False`, explain why. If the user did not ask to change structure, fix it before delivery.

For edited section ranges:

```python
from docx import Document

doc = Document("edited.docx")

def inspect_range(start_prefix, end_prefix):
    start = next(i for i, p in enumerate(doc.paragraphs) if p.text.strip().startswith(start_prefix))
    end = next(i for i, p in enumerate(doc.paragraphs) if i > start and p.text.strip().startswith(end_prefix))
    print("range", start, end)
    for i in range(start, end):
        text = doc.paragraphs[i].text.strip()
        if text:
            print(i, doc.paragraphs[i].style.name, text[:120])

inspect_range("2.4.4 场景", "3 总体")
```

## TOC Field Check

Inspect TOC depth from OOXML:

```python
from zipfile import ZipFile
from lxml import etree

with ZipFile("document.docx") as z:
    root = etree.fromstring(z.read("word/document.xml"))

ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
for node in root.xpath(".//w:instrText", namespaces=ns):
    text = "".join(node.itertext())
    if "TOC" in text:
        print(text)
```

If the TOC is `\o "1-3"`, do not place new optional subsections in `Heading 1-3` unless they should appear in the TOC.

## Editing Guidance

- Use `python-docx` for paragraph-level text/style edits.
- Use OOXML zip editing only for field settings, relationships, or content not supported by `python-docx`.
- Avoid using the style of “previous paragraph” for inserted正文. It may be a heading.
- When adding paragraphs under a section, explicitly set正文 to the document's existing正文 style, for example `Body Text` or `Normal`.
- When adding subheadings, explicitly choose the intended heading style.
- Preserve original TOC entries unless the user asks to regenerate them.
- If setting `w:updateFields=true`, first ensure the heading hierarchy is correct, because Word will regenerate TOC from styles.
- Prefer writing a repaired copy if the source may be open or locked.
- Avoid extracting content from the current document after a failed or partial edit; it may already be structurally corrupted.

## Safe Replace Snippet

Use this pattern for replacing the body under a preserved section heading:

```python
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml import OxmlElement

doc = Document("source.docx")
h4 = doc.styles["Heading 4"]     # UI may show “4级标题”
body = doc.styles["Body Text"]   # UI may show “正文文本”

def delete_body_between(doc, start_prefix, end_prefix):
    start = next(i for i, p in enumerate(doc.paragraphs) if p.text.strip().startswith(start_prefix))
    end = next(i for i, p in enumerate(doc.paragraphs) if i > start and p.text.strip().startswith(end_prefix))
    for i in range(end - 1, start, -1):
        elem = doc.paragraphs[i]._element
        elem.getparent().remove(elem)
    return doc.paragraphs[start]

def insert_after(prev_para, text, style):
    new_p = OxmlElement("w:p")
    prev_para._p.addnext(new_p)
    para = Paragraph(new_p, prev_para._parent)
    para.style = style
    para.add_run(text)
    return para

items = [
    ("2.4.4.1 多传感器融合架构与数据预处理", h4),
    ("正文内容……", body),
]

cursor = delete_body_between(doc, "2.4.4 场景", "3 总体")
for text, style in items:
    cursor = insert_after(cursor, text, style)

doc.save("source-修正版.docx")
```

## Delivery Checklist

Report these points briefly:

- Backup path.
- Output path, especially if the original file was locked and a repaired copy was created.
- Whether `.docx` zip validation passed.
- Whether `Heading 1-3` sequence matches the original.
- What new heading levels were added.
- Whether edited section正文 styles are all expected.
- Whether any numbered subsection content leaked after later sections.
- Whether Word may ask to update fields on open.

## Claude Handoff Prompt

When using Claude or another agent to edit a `.docx`, give it this prompt before the task:

```text
你在编辑 Word `.docx` 前必须先读取并遵守 `docx-safe-editing/SKILL.md`。这次任务不是普通文本生成，而是高风险的既有 Word 报告编辑。

请特别吸取此前错误：

1. 不要把正文写进目录。先检查原文档 TOC 域，例如是否是 `TOC \o "1-3"`；如果是，`Heading 1-3` 会进入目录，普通正文必须使用原文档正文样式，如 `正文文本` / `Body Text` / `Normal`。
2. 不要凭肉眼判断标题样式。`2.3.4`、`2.4.4` 这类原有三级标题应保持原样；新增 `2.4.4.1` 这类四级小节应使用原文档既有的 `4级标题` / `Heading 4`，不要用 `Heading 2` 或 `Heading 3`。
3. 不要修改样式定义。只能应用文档里已有样式，不能重定义字体、字号、缩进、目录级别。
4. 不要只在 2.4.4 下硬塞内容。如果用户要求扩充 2.3.4 和 2.4.4，要先理解原文结构，把内容合理分配到两个章节。
5. 不要用一个已损坏的中间版本继续抽取内容。若发现目录污染、标题层级错乱、段落顺序错乱，回到原始文档或最近验证通过的备份重新操作。
6. 插入段落时不要继承上一段样式。每一段都要显式指定：四级标题用 `Heading 4`，正文用原文档正文样式。
7. 不要用 `addprevious()` 对同一个锚点反复插入导致顺序反转。优先保留章节标题，删除章节正文范围，再用 `addnext()` 顺序插入并更新 cursor。
8. 如果原文件被 Word/WPS 锁定，不要反复覆盖写入。创建 `*-修正版.docx` 或带时间戳的新文件，并说明原文件可能打开中。

工作流程必须是：

1. 先备份原文件。
2. 检查原文档 TOC 域、标题序列、正文样式、目标章节起止范围。
3. 与原始文档对比结构，明确哪些标题结构必须保持不变。
4. 只在目标章节正文范围内编辑。
5. 对每个新增标题和正文显式应用已有样式。
6. 保存后验证 `.docx` zip 可打开。
7. 对比编辑前后的 `Heading 1-3` 序列；若用户没有要求改结构，必须一致。
8. 抽查目标章节范围，列出段落编号、样式名和前 80 字，确认正文没有误用标题样式。
9. 最终汇报：备份路径、输出路径、是否通过 zip 校验、Heading 1-3 是否一致、使用了哪些新增标题层级、是否可能需要 Word 更新目录。

如果你不能完成上述检查，不要声称已经安全编辑。先说明缺少哪一步验证。
```

## Routing

This skill covers strict editing of existing .docx reports. General Word creation, reading, tracked changes, comments, or conversion use the runtime-provided docx skill when available; that skill is not duplicated in this shared library because its license is proprietary. When both apply, use docx for document mechanics and this skill for heading/TOC/body structure protection.
