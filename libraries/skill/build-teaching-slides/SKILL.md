---
schema: paos-skill/v1
id: build-teaching-slides
title: Build Teaching Slides
status: active
version: 1
name: build-teaching-slides
description: Build, redesign, audit, package, and maintain browser-based teaching slide decks with structured course flow, reusable React/OpenSlide components, synchronized speaker notes, evidence boundaries, production validation, offline or single-file HTML delivery, and editor-ready architecture. Use when creating or improving educational web slides, fixing slide sequencing or overflow, adding detailed teaching scripts, exporting a deck as one double-clickable HTML file, making OpenSlide Inspector edits save reliably, or implementing persistent drag, resize, reorder, and browser-based layout editing.
---

# Build Teaching Slides

Build the deck as a teaching system, not a collection of attractive pages. Preserve the chain:

`learning objective → page sequence → visual explanation → speaker notes → validation → delivery`

## Start by routing the task

- For content structure, page sequencing, or speaker notes, read [references/workflow.md](references/workflow.md).
- For an OpenSlide / React codebase, Inspect save failures, dev/build/preview issues, or page registration, read [references/open-slide-engineering.md](references/open-slide-engineering.md).
- For one-file offline delivery, double-clickable `.html` export, `file://` routing, or asset inlining, read [references/single-file-html-export.md](references/single-file-html-export.md).
- For persistent browser editing, free dragging, resizing, reordering, or saving Inspector changes, read [references/inspectable-editor-architecture.md](references/inspectable-editor-architecture.md).
- Before changing an unfamiliar deck, run:

```bash
node <skill-dir>/scripts/audit-slide-project.mjs <project-root> [slide-directory]
```

Treat the report as a heuristic inventory, then inspect the referenced files directly.

## Core workflow

1. Inspect the repository, package scripts, slide registry, shared theme, speaker notes, assets, and existing validation.
2. Build a page map before editing. Give every page one teaching question, one conclusion, and an explicit transition.
3. Correct factual and architectural errors before polishing layout. Prefer primary sources for current technical claims.
4. Reuse shared components and tokens, but keep editable content traceable to stable nodes.
5. Keep body text readable at presentation distance. Reduce wording before reducing font size.
6. Synchronize each visual page with a speaker note containing:
   - teaching goal;
   - recommended narration;
   - misconception or evidence boundary;
   - transition;
   - source links when needed.
7. Validate structure, build production output, and preview through HTTP. For a single-file deliverable, additionally open the exact file through `file://` in a real browser.
8. Hand off the exact files changed, commands run, remaining warnings, and pages needing manual visual review.

## Teaching and visual rules

- Introduce a term before comparing it.
- Show pipeline direction and input/output contracts; do not present connected algorithms as an unordered name list.
- Separate facts, public evidence, inference, and product speculation.
- Prefer real product images or official diagrams when the lesson depends on physical construction.
- Use generated diagrams for abstract relationships only when they materially improve understanding.
- Keep titles short, explanatory text direct, and card density balanced.
- Preserve fixed-canvas safety: no clipped bottoms, no hidden text, no accidental overflow.
- Do not solve density by shrinking all text. Split the concept, shorten copy, or move detail into speaker notes.

## Editor-ready requirement

Choose the editing architecture deliberately:

### Source-patching mode

Use only when retaining the built-in OpenSlide Inspector is sufficient.

- Keep one semantic JSX element per source line.
- Keep editable text and simple style literals at the direct call site.
- Avoid compressing a whole slide into one line.
- Avoid ambiguous repeated call sites, deeply forwarded text props, and computed style spreads for content the user must edit.
- Accept that built-in Inspect mainly edits text/style/attributes and does not provide a general persistent layout model.

### Schema-backed mode

Use when the user expects reliable saving, drag/reorder, resize, or relatively free placement.

- Store slide content and layout in JSON or another serializable document model.
- Give every slide and node a stable ID.
- Render React components from the document; never infer persistence from DOM position.
- Persist drag results as `parentId`, `order`, grid coordinates, or fixed-canvas `x/y/w/h/z`.
- Validate edits server-side, use revision checks, write atomically, and preserve undo history.
- Keep production deployments read-only unless an authenticated write service is explicitly required.

Do not promise “free dragging” by adding CSS transforms alone. If the new coordinates are not saved to the document model, the feature is only a temporary preview.

## Verification gates

Require all applicable gates:

- page and note counts align;
- registry order matches page numbering;
- duplicate IDs are absent;
- selected Inspect edits survive refresh;
- drag, reorder, and resize survive refresh when enabled;
- invalid edits are rejected without corrupting the deck;
- `npm run build` exits with code 0;
- production preview loads the intended route and assets;
- a requested single-file export has no top-level external JS/CSS/local-asset dependency and renders through `file://`;
- only understood warnings remain.

## Completion report

Lead with the outcome. Include:

- pages or systems changed;
- whether speaker notes were synchronized;
- whether Inspect save and drag persistence are implemented or only specified;
- validation/build result;
- distribution format and whether it was tested by HTTP, `file://`, or both;
- remaining visual review or migration work.
