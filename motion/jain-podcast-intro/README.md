# JAIN PODCAST: 12-second glass intro

A real-time 3D motion identity built in Three.js (WebGL2, physical transmission
glass), with an original instrumental cue synthesised in WebAudio. The same
source drives the interactive preview and the frame-exact MP4 export.

- 1920 × 1080, 16:9, 60 fps, 12.000 s (720 frames)
- H.264 High (CRF 14, BT.709) + AAC 320 kbps, 48 kHz stereo
- Fonts and libraries are vendored. Nothing loads from the network.

## Preview

Serve the folder over HTTP (ES modules don't load from `file://`):

```bash
cd motion/jain-podcast-intro
npx serve .            # or: python3 -m http.server 8080
```

Open `http://localhost:3000/` (or `:8080`). The **Play**, **Replay** and
**Sound** controls and the scrubber sit below the canvas and never appear in
exported frames. The preview renders in real time on your GPU without motion
blur. Use `?q=half` on slower machines.

## Export

Requires Node ≥ 22, ffmpeg with libx264, and Playwright (`npm i -g playwright`,
or a local install).

```bash
node render/export.mjs                # SwiftShader (CPU) render, any machine
node render/export.mjs --gpu          # faster on a machine with a real GPU
node render/export.mjs --workers 2    # split frames across browser instances
node render/export.mjs --encode-only  # re-mux after editing audio only
```

Output goes to `out/`: `frames/f0000.png … f0719.png`,
`jain-podcast-intro.wav`, and `jain-podcast-intro.mp4`. Frames already on disk
are skipped, so an interrupted export resumes where it stopped. Delete
`out/frames` after changing the scene.

To check individual moments while editing:

```bash
node render/snap.mjs 0 2.4 5.38 9.6 --out snapshots           # stills + contact sheet
node render/snap.mjs 6.42 --blur                                # with motion blur
node render/snap.mjs 0 --clearance                              # camera-to-mesh distances
```

## Where things live

| Concern | File |
| --- | --- |
| Palette, timing and sync cues, lens, type sizes, glass parameters, brand credit | `src/config.js` |
| Camera rail, target rail, star path, letter assembly, ribbon and panel motion | `src/scene.js` |
| Star silhouette (closed Bézier), rounded panel, swept ribbon | `src/geometry.js` |
| Glass shader, reflection environment, background layers | `src/world.js` |
| Inter Medium glyph extrusion, credit plane | `src/type.js` |
| Score, synths, sound design, WAV encoder | `src/audio.js` |
| Render pipeline (MSAA HDR, tier-2 glass, DOF, motion blur, output) | `src/post.js` |
| Spline and timing math | `src/math.js` |

### Replacing the brand credit with the official logo

In `src/config.js`, set:

```js
export const BRAND_CREDIT = {
  kind: 'image',
  src: 'assets/jain-online-logo.png', // transparent PNG or SVG, placed in this folder
  heightPx: 40,
  gapPx: 46,
  opacity: 1,
  // text fields are ignored in image mode
};
```

Then re-render. The credit keeps its position, its 46 px gap below the title,
and its mask reveal.

### Replacing the music

The cue is synthesised in `src/audio.js` from the `SCORE` table. To use a
licensed track instead, export a 12.000 s, 48 kHz stereo WAV to
`out/jain-podcast-intro.wav` and run `node render/export.mjs --encode-only`.
The picture is cut to these hit points, which are also listed in
`TIMING.cues`:

| Time | Event |
| --- | --- |
| 0.00 | Opening glass accent; the first highlight blooms on the star tip |
| 2.40 | Groove enters; the orbit begins |
| 4.80 | Energy lift; the fly-through begins |
| 5.38 | Ribbon sweep across the lens (stereo whoosh, right to left) |
| 6.42 | Letter pass; PODCAST is revealed (movement accent) |
| 7.20 | Pullback and alignment (melodic resolution) |
| 9.60 | Title locks (sonic signature downbeat) |
| 10.20 | Specular glint crosses the star (crystalline resolution) |
| 11.65–12.00 | Fade to black |

## Rendering notes and limitations

- **Refraction is screen-space.** It uses three.js transmission: an image-based
  approximation, not ray-traced. It bends what is rendered behind the glass,
  so it is physically plausible but not exact. Two tweaks are documented in
  `src/world.js`:
  - The refraction offset is clamped, so close-ups never sample off-screen.
  - Absorption grows at grazing angles, so thick edges read as richer cyan.
- **Glass behind glass.** The ribbon and the frosted panel sample a second
  full-scene buffer that already contains the star, so the star stays
  visible behind them. The reverse case (ribbon seen through the star) is
  not composited. The choreography never puts them in that order.
- **No caustics or contact shadows.** Every object floats in black space, so
  there is no surface to receive them.
- **Motion blur** is true sub-frame accumulation: a 144° shutter with up to 5
  samples, chosen per frame from on-screen motion. **Depth of field** is a
  depth-aware gather in post. Both are export-only refinements. The real-time
  preview skips motion blur.
- **The cue is an original synthesised preview** (pads, bass, drums, motif,
  FM glass bells, sound effects). It is mixed to about −14 LUFS with a −1 dBFS
  peak ceiling. Replace it with a produced or licensed track for broadcast.
- **No official JAIN logo or JGi mark is reproduced.** The credit is plain
  Inter text, replaceable as shown above.

Licenses: Three.js (MIT), opentype.js (MIT), Inter (SIL OFL 1.1). The license
texts are in `vendor/`.
