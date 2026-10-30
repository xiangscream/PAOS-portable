# OpenSlide and React engineering

## Project inventory

Locate:

- `package.json` scripts;
- slide registry such as `slides/<deck>/index.tsx`;
- page modules such as `pages-*.tsx`;
- design system or `theme.tsx`;
- speaker notes;
- asset cache scripts;
- structural validation scripts;
- OpenSlide configuration.

Confirm whether the visible page number includes the cover. In many decks:

`presentation page = Scene index + 1`

Never assume this without reading the registry.

## Standard commands

Typical workflow:

```bash
npm ci
npm run dev
npm run validate
npm run build
npm run preview
```

Use the actual scripts present in `package.json`. Serve `dist/` over HTTP; do not assume double-clicking `index.html` will work with absolute asset paths or history routing.

For TypeScript type-only imports, use one consistent form:

```ts
import type { Page, SlideMeta, DesignSystem } from '@open-slide/core';
```

Do not write `import type { Page, type DesignSystem }`; Babel rejects a nested `type` modifier when the whole import is already type-only.

If `npm ci` reports a blocked `esbuild` postinstall, review the package and approve the required install script through the package manager's supported allow-scripts mechanism. Do not use a forced dependency upgrade as the first response to an unrelated build warning.

## Hot reload failures

If edits do not appear:

1. confirm the dev server was started from the same project root being edited;
2. confirm the browser route belongs to that deck;
3. check terminal and browser overlays for the first parse error;
4. verify no second dev server is serving an older checkout or port;
5. make a visible literal edit in the active page file;
6. restart the dev server after dependency or config changes;
7. on mounted Windows filesystems, test watcher polling or move the active authoring tree to a filesystem with reliable file notifications.

HMR does not recover from every syntax error. Fix the first parser error before judging whether later edits refreshed.

## Diagnose black screens

Check:

1. correct route and base path;
2. browser console runtime error;
3. bundle and asset HTTP status;
4. slide registry import/export mismatch;
5. duplicate or missing scene IDs;
6. stale dev server or wrong port;
7. HMR parse errors;
8. remote image failures;
9. production-only path behavior.

An HTTP 200 for `index.html` does not prove the React route rendered successfully.

## Built-in Inspector behavior

OpenSlide Inspector edits the rendered element, then uses source-location metadata to patch the TSX AST. A save can fail with `no JSX element at location` when the runtime location does not identify a unique editable JSX element.

Common fragile patterns:

- an entire page compressed onto one source line;
- many JSX elements sharing one line/column neighborhood;
- text passed through custom component props;
- repeated content generated from one `.map()` call site;
- computed values or spread styles that cannot be rewritten as a literal;
- wrapper components whose rendered DOM maps to a different source file;
- stale source maps after large edits;
- saving from preview or production instead of the connected dev server.

Dragging a DOM element in developer tools or applying a temporary CSS transform is not persistence. Built-in Inspector source patching also does not automatically create parent/child order, snapping, resizing, grouping, or collision rules.

## Source-patching compatibility pattern

Use readable direct call sites:

```tsx
<Card
  data-node-id="scene-20-can"
  style={{
    padding: 24,
    gridColumn: '1 / 2',
  }}
>
  <div style={{ fontSize: 28, fontWeight: 900 }}>
    CAN / CAN-FD
  </div>
  <div style={{ fontSize: 24, lineHeight: 1.4 }}>
    Shared frame bus with arbitration and error handling.
  </div>
</Card>
```

Avoid making every editable card a one-line invocation with all text hidden in props if reliable source patching is required.

## Inspector acceptance test

In dev mode:

1. edit one direct text node;
2. edit one font size;
3. edit one image attribute;
4. save;
5. confirm the source file changed;
6. refresh and confirm persistence;
7. build again.

If a deck needs reliable drag/reorder/resize, do not keep extending AST patching indefinitely. Migrate to the schema-backed architecture in [inspectable-editor-architecture.md](inspectable-editor-architecture.md).

## Static build boundary

The production `dist/` is normally read-only. Browser edits cannot persist into bundled source without a write service. Keep authoring writes in the dev environment, or explicitly design an authenticated content API.
