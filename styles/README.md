# Styles — reel templates with a named art direction

The classic template (`template/index.html`) is one look. `styles/` holds
more, each a complete art direction: type system, motion grammar, transitions,
caption treatment, CTA and a default grade. Pick one per project:

```bash
node factory/new.mjs coffee-reel "₹4 lakh from one reel" --style swiss-editorial
# or set "style" in an existing project's project.json
```

Everything else in the pipeline stays the same — five lines, voice, captions,
QA, finish. `LEXICON.md` names every technique these templates use (and the
ones they don't yet); `grades.json` is the colour library.

| Style | Art direction | Default grade | Best for |
|---|---|---|---|
| `swiss-editorial` | International Typographic Style: grid, flush-left Inter Tight, one red accent, mask-revealed type, karaoke captions, colour wipe on every cut, giant scene numerals, paper CTA card | `muted-editorial` | explainers, money/data claims, founder POV |
| `kinetic-punch` | Creator edit: word-by-word pop captions (Montserrat 900, thick outline, live word yellow, money green), punch-in jump cuts, flash + zoom transitions, progress bar, sticker CTA with drawn arrow | `bright-pop` | talking heads, street demos, fast tutorials |
| `cine-doc` | Cinematic documentary: letterbox matte, tracking-in Instrument Serif title, roman-numeral chapter cards, cross-dissolves, Ken Burns drift, cinema subtitles, dip to black into an end title | `teal-orange` | stories, journeys, places, before/after |
| `neo-brutal` | Neubrutalism collage: dot-grid paper, footage in hard-shadow cards pushed in and flung out, Bricolage Grotesque + Space Mono stickers, marker-highlight captions, stepped wiggles | `mono-classic` | tools, listicles, playful brands |

All four honour the repo's contracts: 1080×1920@30, safe zones (220 top / 420
bottom / 120 right), caption band from 1380 px, one paused GSAP timeline,
transforms and opacity only on media, seeded randomness, OFL fonts vendored so
renders work offline.

## Footage: raw or generated

Every scene can be a clip or a still. `pipeline/footage.py` stages it:

```bash
# one clip, from 12.5 s in, cropped to fill 9:16, graded with the style's default
python3 pipeline/footage.py --project <dir> --line 3 --src ~/raw/barista.mov --start 12.5

# a whole folder named line01.mov, line02.jpg, ... ; landscape footage blur-padded
python3 pipeline/footage.py --project <dir> --src-dir ~/raw/coffee --fit blur

# pick a grade by eye: every grade on one frame of your clip -> <dir>/grades/<clip>.jpg
python3 pipeline/footage.py --project <dir> --grade-sheet ~/raw/barista.mov --at 4
python3 pipeline/footage.py --project <dir> --src-dir ~/raw/coffee --grade cinestill-night --grain 0.4

# a real film-stock or brand LUT
python3 pipeline/footage.py --project <dir> --line 1 --src clip.mp4 --lut ~/luts/portra.cube
```

It reframes to 1080×1920 (`--fit cover` with `--focus` 0..1 for the crop
centre, or `--fit blur`), trims to the line's length plus a 0.6 s handle (run
it after the voice phase so `audio_meta.json` knows the lengths; it holds the
last frame if a clip runs short), bakes the grade, strips audio and re-encodes
with a keyframe every 30 frames so the renderer can seek. Stills become graded
JPEGs with headroom for push-ins. The previous take goes to `assets/footage.bak/`.
Generated footage from `integrations/ltx2/` works the same way.

Grades are baked with ffmpeg on purpose: HyperFrames' live shader grading
(`data-color-grading`) is far richer but rendered at ~18 s per frame on a
machine without a GPU. On a GPU machine you can layer it on anyway with
`"hf_grading": {"preset": "...", ...}` in `project.json` (see
`npx hyperframes media-treatment --capabilities`).

## Tuning a style per project

`project.json`:

```json
{
  "style": "swiss-editorial",
  "style_params": { "accent": "#0057ff", "handle": "@genieflix", "cta_note": "free template" },
  "hf_grading": null
}
```

`style_params` merge over the style's `params` in `style.json`. Each style
documents its own: accent colours, punch-in scale, dissolve length, chapter
labels, CTA wording. The grade is chosen at staging time (`footage.py --grade`).

## How a style template works

`pipeline/build_index.py` reads `styles/<style>/index.html` and fills four
markers: `<!--HF:DURATION-->`, `<!--HF:SLIDES-->` (the scene `<img>`/`<video>`
clips, class `scene`), `<!--HF:AUDIO-->` and `<!--HF:DATA-->` — a JSON blob
with the scenes, every caption group with per-word timings, the title, kicker,
CTA keyword and the merged params. Optional markers (`<!--HF:TITLE-->`,
`<!--HF:FONT_FACES-->`, …) are filled when present.

The template's own script then builds everything else from that data with the
shared runtime `styles/_lib/reel.js` (`window.REEL`): `clip()` creates real
timed clips, `maskWords()` / `charSpans()` prepare type for reveals,
`isEmphasis()` spots money numbers, `rng()` is a seeded PRNG, `fadeOutAt()`
adds the hard stop a boundary fade needs. Fonts and the runtime are copied into
the project's `assets/style/` on every build (generated, safe to delete).

### Adding a style

1. Copy the closest style folder to `styles/<new-name>/`.
2. Edit `style.json` (name, lexicon terms, default grade, `scene_overlap`, params).
3. Vendor any new font as woff2 with its licence into `assets/fonts/` and
   declare it in the template's `<style>`; reference it as
   `assets/style/fonts/<file>`.
4. Write the choreography: one paused timeline, transforms/opacity only,
   `clip-path` only on non-media, nothing random, nothing wall-clock.
5. Build a scratch project with `"lang": "proportional"` and stand-in voice,
   `npx hyperframes lint` to 0 errors, snapshot, render, and read frames from
   the MP4. Then decode your own render with `decode/decode_reel.py` — if the
   decoder can't name your transitions, viewers won't feel them either.

## From a reference reel to a style

1. Drop the reel in `decode/inbox/` (MP4/MOV; screen-recordings of the app work).
2. `python3 decode/decode_reel.py decode/inbox/<file>.mp4`
3. Read `decode/refs/<name>/hook.jpg`, `contact.jpg`, `timeline-*.jpg`,
   `cuts/`; fill the **Decoded** half of `REPORT.md` with `LEXICON.md` names.
4. Map it: closest style + params + grade, or a new style folder when the
   grammar differs (see above). The report's "Rebuild recipe" section is that map.
