---
name: handoff
schema: paos-skill/v1
id: handoff
title: Agent Handoff
description: "Compact the current conversation into a handoff document for another agent to pick up. Use when user wants to hand off work, summarize progress, or prepare context for a new session."
tags: handoff, continuity, agents
status: active
version: 1
---

# Handoff

## What to do

Write a handoff document summarising the current conversation so a fresh agent can continue the work.

**File path**: Save to `docs/handoff-<timestamp>.md`. If `docs/` doesn't exist, save to the project root instead. Get the timestamp with Bash: `date +%Y%m%d-%H%M%S`.

Before writing, use Read to scan for existing artifacts (PRDs, ADRs, open issues, recent diffs) so you can reference rather than duplicate them.

Do not duplicate content already captured in other artifacts. Reference them by relative path or URL instead.

If the user passed arguments, treat them as a description of what the next session will focus on — use that to weight the "Next steps" section accordingly.

## Handoff document structure

```markdown
# Handoff: <brief description of what was worked on>

## Current state
What was accomplished in this session. Key decisions made, code written, problems solved.
Be specific but concise — bullet points preferred. Include file paths changed if relevant.

## Next steps
What the next session should tackle, in priority order.
If user provided a focus argument, lead with that.

## Relevant artifacts
Links or paths to artifacts that provide context — don't inline their content here:
- `docs/prd-*.md` — PRD if one exists
- `docs/adr/*.md` — relevant ADRs
- Issue URLs — open tickets
- Branch / PR — if a diff exists

## Suggested skills
Skills the next session should load. For each, one line explaining why:
按当前工作目录中实际存在且与下一步相关的 Skill 选择；没有对应 Skill 就不列占位项。每项只写一行“为什么需要”。
```

## Tools

- **Read**: Scan existing artifacts before writing, to avoid duplicating content
- **Write**: Write the handoff document to disk
- **Bash**: Get the current timestamp (`date +%Y%m%d-%H%M%S`) for the filename
