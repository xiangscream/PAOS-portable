# Teaching slide workflow

## 1. Establish the learning contract

Record:

- audience and prior knowledge;
- course duration;
- practical outcome;
- vocabulary that must be introduced;
- claims that require sources;
- what belongs on the slide versus in narration.

A page should answer one question. A section should end with a reusable mental model.

## 2. Inventory before editing

Inspect:

- slide registry and page numbering;
- slide source files and shared components;
- design tokens and canvas size;
- speaker-note storage and indexing;
- local and remote assets;
- dev, validate, build, and preview commands;
- existing editor or Inspector behavior.

Preserve unrelated user changes. Never overwrite a dirty worktree casually.

When receiving an external redesign archive:

1. unpack into a staging directory;
2. inventory files and dependencies;
3. compare routes, assets, notes, and configuration;
4. migrate only the selected clean version into the target directory;
5. install dependencies from the lockfile;
6. validate before further content edits.

## 3. Build the page map

For each page, write:

| Field | Requirement |
|---|---|
| Teaching question | What should the audience understand here? |
| Visual job | Compare, sequence, map, explain structure, or show evidence |
| Main conclusion | One sentence that can be repeated aloud |
| Prerequisite | Which earlier idea does this page depend on? |
| Transition | Why does the next page follow? |
| Note depth | What detail stays out of the visible canvas? |

Reorder before rewriting. Add a transition page only when a real conceptual boundary is missing.

## 4. Research and evidence

- Use primary sources for technical claims when available.
- Separate official product disclosure from tutorials, community projects, and inference.
- Do not infer a full proprietary stack from one public algorithm.
- Put evidence boundaries in the narration and, when central, on the slide.
- Cache required assets for offline builds when licensing and project policy allow.

## 5. Write visual content

Use progressive disclosure:

1. define the object;
2. give the physical or product intuition;
3. show the mechanism;
4. state the trade-off;
5. connect it to the larger system.

Avoid unexplained acronym piles. For each new term, answer:

- what is it;
- what does it consume;
- what does it produce;
- where does it run;
- what does it not guarantee.

## 6. Design the page

- Prefer one visual structure per page.
- Use a flow for sequences, a table for repeated comparisons, a tree for hierarchy, and cards for independent concepts.
- Keep three heading levels at most.
- Use body text that remains readable at presentation distance.
- Shorten content before shrinking text.
- Keep consistent card padding, line height, and accent logic.
- Use real images for physical products; use abstract diagrams for relationships.
- Check bottom edge, long Chinese lines, image crop, and dense tables.

## 7. Write speaker notes

Each note should include:

1. `讲解目标`
2. `建议话术`
3. a concrete example
4. a misconception or evidence boundary
5. `转场`
6. `建议时间`
7. sources when needed

Do not repeat visible text verbatim. Explain why the page matters.

## 8. Implement

- Reuse theme tokens and shared components.
- Keep scene/page IDs stable while reordering registry entries deliberately.
- Keep notes indexed to the rendered order.
- Prefer readable multiline JSX over compressed one-line pages.
- If browser editing matters, follow [inspectable-editor-architecture.md](inspectable-editor-architecture.md) from the start.

For manual positioning, identify the owning layout first:

- parent grid controls columns, rows, spans, and gaps;
- flex parent controls order, alignment, and growth;
- child margin changes spacing but not the parent's placement logic;
- fixed height can be neutralized by flex shrink unless `flex-basis`, `minHeight`, or grid tracks also reserve space;
- changing image height does not necessarily move the text below if the card itself is constrained.

Teach the user which parent property controls the intended movement rather than suggesting random pixel changes.

## 9. Validate

Run, in order:

1. project-specific structural validation;
2. TypeScript or framework checks;
3. production build;
4. production preview through HTTP;
5. targeted route and asset checks;
6. manual visual review.

For fixed-canvas slides, review every page at the intended aspect ratio. Check overflow, text size, image completeness, and transitions.

## 10. Hand off

Report:

- what changed and why;
- exact changed files;
- build output status;
- remaining warnings;
- pages needing visual judgment;
- how to run dev, build, and preview;
- whether browser edits persist and where they are stored.
