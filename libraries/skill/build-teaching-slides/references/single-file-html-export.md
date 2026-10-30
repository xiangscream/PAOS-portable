# Single-file HTML export

Use this workflow when the recipient should receive one double-clickable HTML file without Node.js or an HTTP server.

## Keep authoring and delivery separate

- Keep `npm run dev` and the source tree as the editable authoring environment.
- Treat the single HTML file as a read-only distribution artifact.
- Do not promise that OpenSlide Inspector can save from the single file. Saving source edits requires the dev server and source files, or a separately designed authenticated write service.
- Preserve the normal multi-file `npm run build`; add a separate command such as `npm run build:single`.

## Why renaming `dist/index.html` fails

A normal Vite/OpenSlide build can still depend on:

- `/assets/*.js` chunks;
- a separate stylesheet and fonts;
- image files emitted by `new URL(..., import.meta.url)`;
- `BrowserRouter`, which interprets the local file path as an application route;
- dynamic slide imports;
- OpenSlide's first-open deck preloader.

Therefore, copying or renaming only `dist/index.html` is not a single-file export.

## Recommended OpenSlide build

Create a dedicated Node build script in the project:

1. Call `createViteConfig` from `@open-slide/core/vite`.
2. Prepend a special Vite transform plugin.
3. In that plugin, replace `BrowserRouter` with a `MemoryRouter` whose initial entry is the intended deck route, for example `/s/robot-course-v2`.
4. Disable OpenSlide's hidden whole-deck preloader in this special build. All images and fonts are already data URIs, so HTTP-cache warming is unnecessary and can leave large decks on `LOADING ASSETS`.
5. Set:

```js
config.base = '/';
config.build = {
  ...config.build,
  assetsInlineLimit: Number.MAX_SAFE_INTEGER,
  cssCodeSplit: false,
  rollupOptions: {
    ...config.build?.rollupOptions,
    output: {
      ...config.build?.rollupOptions?.output,
      inlineDynamicImports: true,
    },
  },
};
```

6. Build into a project-scoped staging directory.
7. Read the generated `index.html`, CSS, module JS, and favicon.
8. Replace the original tags with inline `<style>`, `<script type="module">`, and data-URI favicon content.
9. Write the final file with a clear name such as `lessonv3.html`.
10. Remove only the known staging directory.

Use a fixed deck ID only when the artifact intentionally opens one deck. Otherwise expose the ID as a script argument.

## Safe HTML inlining rules

Process top-level HTML tags before injecting the large JS bundle. After JS is inserted, regular expressions may accidentally match HTML snippets embedded in OpenSlide's own export code.

Use function-form replacement:

```js
const safeJs = js.replaceAll('</script', '<\\/script');
const inlineScript = `<script type="module">${safeJs}</script>`;
html = html.replace(originalScriptTag, () => inlineScript);
```

Do not pass the full minified bundle as the second string argument to `String.replace`. Minified JavaScript can contain dollar-ampersand, dollar-apostrophe, or dollar-backtick substitution tokens; string-form replacement can interpret them and reinsert the original external `<script src>` tag.

Apply the same closing-tag protection to inline CSS:

```js
const safeCss = css.replaceAll('</style', '<\\/style');
```

Do not recursively replace a built JS file's reference to itself with a `data:text/javascript` URI. OpenSlide's HTML-download code may list the current bundle URL. Re-inlining that self-reference can multiply the output from roughly 11 MB to more than 80 MB. With `inlineDynamicImports: true`, skip remaining `.js` asset references unless inspection proves they are required at runtime.

Expected base64 growth is about one third. A much larger increase usually indicates duplication, self-inlining, or string-replacement expansion.

## File-mode runtime adjustments

`BrowserRouter` is unsuitable for a file such as:

```text
file:///C:/Users/name/Desktop/deck.html
```

The pathname becomes the local filesystem path and does not match `/s/:slideId`. For a fixed single-deck artifact, `MemoryRouter` with an initial entry is more reliable than rewriting `history`.

OpenSlide may mount every page invisibly to warm images and fonts. Disable that gate only in the single-file build; keep it in normal HTTP builds. This is especially important for decks with dozens of pages.

## Verification

Do not stop at `vite build`.

Run structural checks:

- page count and speaker-note count still pass;
- the final module script is inline and substantial;
- no top-level `<script src>` remains;
- no top-level external stylesheet remains;
- no top-level `src="/assets/..."` or `href="/assets/..."` remains;
- expected image and font data URIs exist;
- file size is plausible;
- output hash is recorded when integrity matters.

Then launch the exact file through `file://` in a real browser. Use a fresh browser profile so an existing session does not absorb the command.

Example Windows Edge check from PowerShell:

```powershell
$testDir = Join-Path $env:TEMP ("slide-edge-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $testDir | Out-Null
$shot = Join-Path $testDir "shot.png"
$args = @(
  "--headless=new",
  "--disable-gpu",
  "--allow-file-access-from-files",
  "--user-data-dir=$testDir",
  "--window-size=1600,1000",
  "--virtual-time-budget=3000",
  "--screenshot=$shot",
  "file:///C:/path/to/lessonv3.html"
)
Start-Process -FilePath "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
  -ArgumentList $args -Wait
```

Inspect the screenshot. Confirm:

- the deck itself rendered, not merely a blank shell;
- the intended route opened;
- page thumbnails and page count appear;
- critical local images display;
- the presentation control is available.

If the screenshot stays on `LOADING ASSETS`, confirm the single-file build disabled the deck preloader. If it is black, inspect route handling and the first browser console exception.

## Delivery boundary

Tell the user:

- the exact HTML path and size;
- that the recipient can double-click it;
- the regeneration command;
- that online source links still require internet when clicked;
- that Inspect/source saving remains an authoring-mode feature.
