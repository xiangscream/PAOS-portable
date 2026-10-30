# Skill Library

共享 Agent Skill 库。每个 Skill 使用稳定目录名，并以 `SKILL.md` 作为入口；动态使用统计不写进文件名。

```text
<Skill Library>/
├─ <skill-id>/
│  └─ SKILL.md
├─ CATALOG.md
└─ .paos/
   ├─ catalog.json
   └─ usage-events/
```

被 PAOS 识别的 Skill 使用扁平 frontmatter：

```markdown
---
schema: paos-skill/v1
id: example-skill
title: Example Skill
description: What this skill helps an Agent do.
tags: writing, review
version: 1
---
```

Agent 调用 Skill 后可记录 0 / 0.3 / 0.5 / 1 的价值分。PAOS 将使用次数、30 天热度、最近使用时间、跨 Project 数量与平均价值作为派生统计写入 Catalog。

共享规则的登记、替换与历史退出统一遵循[准则登记与退役](../workflow/Guides/guide-project-work-world.md#准则登记与退役)。

## Runtime-specific skills

Status of the four OpenCode runtime skills:

- cpp-pro — now merged in this library as an MIT-licensed shared definition.
- docx — Anthropic proprietary; general .docx creation/reading/editing stays in the runtime. For strict existing report editing, use the shared docx-safe-editing skill.
- pdf — Anthropic proprietary; PDF read/edit/forms/OCR stays in the runtime.
- xlsx — Anthropic proprietary; spreadsheet read/edit/create stays in the runtime.

On this installation, the original docx, pdf and xlsx definitions are under C:/Users/remo/AppData/Local/PAOS/OpenCodeV2Candidate-20261023-rooter/config/opencode/skills/. This path records the local source; it is not a dependency for other machines or Harnesses. Do not copy their proprietary text into this library; other Harnesses should use their own runtime-provided equivalents when available.
