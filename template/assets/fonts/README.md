# Fonts

Nothing here is required — the template ships with a system font stack.

To use a custom font:

1. Drop the font files in this folder (`.woff2` preferred, `.ttf` works).
2. Edit the commented `@font-face` block near the top of `template/index.html`
   and point it at `assets/fonts/<file>`, then use the family in the CSS.
3. Edit the **template**, not a project's generated `index.html` — the
   generated file is rebuilt from the template and hand-edits are wiped.

Local files only: renders run fully offline, so no font CDN links.
Only bundle fonts you are licensed to embed in published video.
