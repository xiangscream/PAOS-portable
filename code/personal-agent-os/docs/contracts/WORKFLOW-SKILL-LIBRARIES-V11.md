# Workflow / Skill Libraries V1.1

## Purpose

PAOS V1.1 treats reusable working methods and reusable Agent capabilities as two clean libraries outside individual Project Vaults.

- Project Vault: project-specific material, Work, Decisions, Agent Workstations and outputs.
- Workflow Library: shared ways of working.
- Skill Library: reusable Agent capabilities.

Neither library is a PAOS governance Store. Markdown remains human-readable and Obsidian-compatible.

## Workflow Library

Recommended root:

```text
<Workflow Library>/
├─ README.md
├─ Guides/
├─ Workflows/
├─ Templates/
├─ CATALOG.md
└─ .paos/
   └─ catalog.json
```

PAOS recognizes Workflow Markdown only when it carries:

```markdown
---
schema: paos-workflow/v1
id: research-review
title: Research Review
description: One-line purpose.
tags: research, review
status: active
---
```

The flat frontmatter is intentionally narrow in V1.1.

`CATALOG.md` and `.paos/catalog.json` are derived views. They may be rebuilt from source Markdown at any time.

## Skill Library

Recommended root:

```text
<Skill Library>/
├─ README.md
├─ <skill-id>/
│  └─ SKILL.md
├─ CATALOG.md
└─ .paos/
   ├─ catalog.json
   └─ usage-events/
      └─ <event>.json
```

A Skill entry uses:

```markdown
---
schema: paos-skill/v1
id: clean-writing
title: Clean Writing
description: Create clean professional writing.
tags: writing, review
version: 1
---
```

The directory name must exactly equal the stable Skill `id`. Dynamic use statistics never change the directory or filename.

## Skill usage

One Agent invocation can record a usefulness score:

- `0`: invoked but no useful value;
- `0.3`: weak/reference value;
- `0.5`: partial value;
- `1`: directly useful / solved the task.

Usage is stored as one append-only JSON event file per invocation under `.paos/usage-events/`. This avoids one shared mutable counter file and keeps the event source rebuildable.

Each event may include:

- Skill ID;
- UTC timestamp;
- usefulness score;
- Project ID;
- Agent ID;
- Work ID;
- short note.

The generated Skill Catalog derives:

- total uses;
- uses in the latest 30 days;
- last-used time;
- unique Project count;
- unique Agent count;
- usefulness total;
- usefulness average.

These values are indexes, not Skill source truth.

## Catalog safety

PAOS only overwrites `CATALOG.md` when the existing file contains the PAOS generated marker.

If a human-created `CATALOG.md` already exists, catalog generation fails closed instead of overwriting it.

README files are created only when absent and are never rewritten during later initialization.

Duplicate IDs fail visibly.

## CLI surface

V1.1 foundation commands:

```text
paos library init workflow --root <path>
paos library init skill --root <path>

paos library catalog workflow --root <path>
paos library catalog skill --root <path>

paos library skill-use \
  --root <skill-library> \
  --skill-id <skill> \
  --score 0|0.3|0.5|1 \
  [--project-id <project>] \
  [--agent-id <agent>] \
  [--work-id <work>] \
  [--note <text>]
```

These commands are filesystem-only and do not call PAOS HTTP.

## Installation registration

A3b adds one installation-local canonical Workflow/Skill root registry. See `CANONICAL-LIBRARY-ROOTS-V11.md`.

New Workstations may now receive the registered roots automatically. Library content is still never copied into each Project.

Existing Workstation `ENTRY.md` files remain protected from automatic rewrite. If roots are registered after a Workstation already exists, provisioning reports that the current ENTRY needs migration rather than silently replacing human/Agent edits.

## Acceptance

1. Workflow/Skill roots initialize non-destructively.
2. Workflow source Markdown generates a rebuildable catalog.
3. Skill directory identity is stable and matches Skill ID.
4. Skill usage creates one immutable event per invocation.
5. Skill catalog derives heat/generality/usefulness statistics without renaming Skill files.
6. Human `CATALOG.md` is never overwritten.
7. Library CLI commands perform no PAOS HTTP call.
8. Existing Project, Session and Workstation behavior remains unchanged.
9. Full verifier and diff hygiene pass.
