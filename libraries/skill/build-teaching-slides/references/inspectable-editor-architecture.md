# Persistent Inspect and drag architecture

## Choose the target

There are two distinct goals:

1. **AST Inspector compatibility** — edit TSX text and styles during development.
2. **Document editor behavior** — select, edit, reorder, drag, resize, save, undo, and reload reliably.

Use source patching for the first. Use a schema-backed document editor for the second.

## Recommended document model

Store content and layout outside component source:

```json
{
  "version": 1,
  "revision": 42,
  "canvas": { "width": 1920, "height": 1080 },
  "slides": [
    {
      "id": "scene-20",
      "title": "Communication layers",
      "nodes": [
        {
          "id": "scene-20-can-card",
          "type": "card",
          "parentId": "scene-20-root",
          "order": 2,
          "content": {
            "title": "CAN / CAN-FD",
            "body": "Shared frame bus with arbitration."
          },
          "layout": {
            "mode": "grid",
            "column": 2,
            "row": 1,
            "columnSpan": 1,
            "rowSpan": 1
          },
          "style": {
            "fontSize": 24,
            "padding": 20
          },
          "constraints": {
            "locked": false,
            "minWidth": 240,
            "minHeight": 120
          }
        }
      ]
    }
  ]
}
```

Every editable entity needs a stable ID. Do not use array index, current page number, DOM path, or React-generated IDs as persistence keys.

## Renderer boundary

Keep three layers separate:

1. **Document** — serializable content and layout.
2. **Renderer** — maps node types to React components.
3. **Editor state** — selection, draft changes, drag preview, undo history.

The renderer should accept a node and emit:

```tsx
<EditableNode nodeId={node.id}>
  <CardRenderer node={node} />
</EditableNode>
```

Do not save the rendered DOM. Save document operations.

## Layout modes

Support explicit modes:

- `flow` — normal document flow;
- `grid` — card grids and structured teaching layouts;
- `absolute` — fixed-canvas free placement;
- `group` — children move and resize together.

Prefer grid reorder for ordinary teaching slides. Use absolute placement only where visual composition needs it.

### Reorder

Persist:

- `parentId`;
- `order`;
- optional grid row and column.

### Free drag

Persist fixed-canvas values:

- `x`, `y`;
- `width`, `height`;
- `zIndex`;
- optional rotation.

Use slide coordinates, not viewport pixels. Convert pointer movement by the current canvas scale:

`documentDelta = screenDelta / canvasScale`

### Resize

Enforce:

- min/max size;
- parent containment;
- aspect lock for images;
- snapping;
- locked nodes;
- group behavior.

CSS transforms may be used during drag preview, but commit final coordinates to the document on drop.

## Save API

For local authoring, implement a Vite dev-server plugin or small local API:

```text
GET   /__slides/deck
PATCH /__slides/deck
PUT   /__slides/deck
```

Each write should include:

- expected `revision`;
- operation list or complete validated document;
- changed node IDs;
- client operation ID.

The server must:

1. validate schema;
2. reject duplicate or missing IDs;
3. reject stale revisions with `409 Conflict`;
4. write to a temporary file;
5. atomically replace the document;
6. increment revision;
7. return the saved revision.

Never let the client write arbitrary filesystem paths.

## Edit operations

Prefer operations that support undo:

```ts
type DeckOperation =
  | { kind: 'set-content'; nodeId: string; path: string; value: unknown }
  | { kind: 'set-style'; nodeId: string; key: string; value: unknown }
  | { kind: 'move'; nodeId: string; parentId: string; order: number }
  | { kind: 'set-layout'; nodeId: string; layout: Layout }
  | { kind: 'insert'; parentId: string; node: SlideNode }
  | { kind: 'delete'; nodeId: string };
```

Keep an inverse operation for undo/redo. Batch a drag or text session into one history item.

## Inspector panel

Expose only schema-supported fields:

- text, rich text, image source, alt text;
- typography and color tokens;
- padding, gap, alignment;
- grid position and span;
- absolute position and size;
- lock, visibility, z-index;
- duplicate, delete, group, ungroup.

Do not expose arbitrary JavaScript or raw style strings as editable data.

## Migration from TSX slides

Migrate incrementally:

1. add stable IDs to slides and modules;
2. extract text, image references, and layout props into a document;
3. render the existing components from that document;
4. add selection and property editing;
5. add grid reorder;
6. add free drag only to selected containers;
7. add server validation and atomic persistence;
8. retain a read-only fallback if the document fails validation.

Do not attempt to convert every bespoke illustration into freely draggable nodes on day one. Start with cards, text, images, and container ordering.

## Development and production

- Dev authoring may write local JSON through a Vite plugin.
- Static `dist/` cannot persist to source files.
- A deployed editor requires authentication, authorization, backups, and a content service.
- Keep runtime safety and robot control settings outside the slide editor.

## Definition of done

- Text edits survive refresh and rebuild.
- Drag, resize, and reorder survive refresh and rebuild.
- Stable IDs remain unchanged after reordering.
- Undo/redo works across content and layout changes.
- Concurrent stale writes are rejected.
- Invalid documents never replace the last valid file.
- Exported static slides remain deterministic.
- The editor can be disabled for presentation mode.
