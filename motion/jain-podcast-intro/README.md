# JAIN PODCAST intro

A 12-second, 1920 x 1080, 60 fps motion identity for the JAIN Podcast segment by JAIN Online.
It is a real-time Three.js (WebGL) scene with a genuine perspective camera on one continuous
spline, plus an original synthesized cue rendered with WebAudio. The same deterministic
`renderFrame(t)` drives the browser preview and the frame-accurate MP4 export.

## Run the preview

Any static server works (ES modules need http, not `file://`):

```bash
cd motion/jain-podcast-intro
python3 -m http.server 8000        # or: npx serve .
# open http://localhost:8000/
```

Play / Pause, Replay, Sound on/off and a scrubber sit below the canvas, outside the rendered
frame. The preview renders at the canvas's on-screen resolution without motion blur; add
`?scale=1` to the URL to force full 1920 x 1080.

## Export the MP4

Needs Node 22+, ffmpeg with libx264 + aac, and Playwright's Chromium.

```bash
node render/render.mjs video --workers 2      # renders/jain-podcast-intro_1080p60.mp4
```

What it does: serves this folder, opens `render/export.html` in headless Chromium, renders all
720 frames at 1920 x 1080 with shutter-sampled motion blur, streams raw RGBA into ffmpeg
(H.264 High, CRF 14, yuv420p, BT.709 tags), renders the score offline to a 48 kHz WAV, then
muxes AAC 256 kbps with `+faststart`. On a 4-core CPU with no GPU (SwiftShader) this takes
roughly 75-90 minutes. With a GPU it's a few minutes; drop the `--use-angle=swiftshader`
flags in `render.mjs` `launch()` to use hardware WebGL.

Other commands:

```bash
node render/render.mjs stills 2.4,6.15,9.8 --scale 0.5   # PNG stills into renders/stills
node render/render.mjs audio                             # renders/score.wav + EBU R128 report
node render/render.mjs check                             # clearance, speed, yaw rate, plan.svg
node render/render.mjs budget                            # motion-blur subframes per frame (full res)
```

`check` is the path QA: minimum camera distance to every letter, the column and the star;
whether the column fully covers the frame (the hidden switch into the typography); when
PODCAST first enters the frame; speed, acceleration and yaw-rate peaks per phase.

## Where things live

| File | Holds |
| --- | --- |
| `src/config.js` | Every tunable: brand colours, timing and cues, lens, type metrics, credit/logo, star geometry and material, camera keys, star path, exploded letter poses, environment, lights, post, audio cue sheet |
| `src/engine.js` | Scene build and `pose(t)` / `renderFrame(t)` |
| `src/motion.js` | Monotone-cubic retiming, arc-length paths, quaternion orientation table |
| `src/star.js` | Star silhouette and extrusion |
| `src/type.js` | Inter Medium TTF parsing (opentype.js), -2 px tracking layout, per-letter extrusion |
| `src/materials.js` | Satin star material, white-front / charcoal-side letter material |
| `src/post.js` | MSAA HDR render, distant-only depth of field, shutter accumulation, tone curve, fade |
| `src/audio/score.js` | The music and sound design, offline render, WAV encoder |
| `assets/fonts/` | Inter Medium 4.1 (SIL OFL 1.1, licence included) |
| `assets/brand/jain-online-logo.svg` | Official JAIN Online logo used as the brand credit |
| `vendor/` | three.js r186 and opentype.js 1.3.4 (MIT), vendored so it runs offline |

### Swapping the brand credit

`CREDIT` in `src/config.js`. `kind: 'image'` uses `image.src` (SVG is rasterised at 4x the
on-screen size before upload; a transparent PNG also works) at `image.height` world units
(0.6 = 60 px). `kind: 'text'` falls back to plain "JAIN Online" in Inter Medium 46 px. The
mask reveal and settle are shared by both.

## The star

Four rounded tips on the axes and four broad concave flanks. Every flank is a circular arc
tangent to its tip cap and perpendicular to the diagonal at the valley, so the outline is
tangent-continuous all the way round. Extrusion is 10 % of the width, the rounded bevel 3.5 %,
72 segments per curve, normals smoothed across the bevel. The valleys sit at (±0.339, ±0.339)
instead of the suggested ±0.28: with round tip caps and no pinch in the arms, tangent-continuous
arcs can't go lower than about 0.29, and 0.28 read as a thin-armed cross in tests.

Material: `#00DAC4` base, roughness 0.4, metalness 0.06, a thin clearcoat for narrow
highlights, 7 % self-emission so shadowed faces stay cyan, and an object-space micro-bump that
is fixed to the geometry. Measured on a lit face in the render: (24, 225, 203) against the
brand (0, 218, 196).

## Camera choreography

One centripetal Catmull-Rom spline for position and one for the look target. Arc length is
retimed with a monotone cubic through timed keys, then Gaussian-smoothed, so speed and
acceleration stay continuous across every phase boundary. Orientation is a look-at quaternion
table, smoothed in quaternion space and sampled with slerp, with up to 3 degrees of bank from
lateral acceleration. One 50 mm lens throughout; scale changes come from camera travel.

| Time | Move | What carries the transition |
| --- | --- | --- |
| 0.0-2.4 | Backward dolly from about a unit off a concave flank, arcing 27 degrees; a narrow highlight runs along the bevel with the opening tone | Background rings at three depths give parallax |
| 2.4-4.8 | 60 degree descending orbit (camera drops from above the star to below it); the star counter-rotates 12 degrees and starts to lead | **Foreground occlusion:** the camera passes behind a charcoal column that fills the whole frame for 5 frames; the type switches on unseen |
| 4.8-7.2 | Diagonal fly-through: N and A beside the lens, the star slips behind the N, the I passes 1 unit from the lens, fastest pass at about 6.0 s | **Letter-edge wipe:** the A's legs cross the full frame at 6.1 s while the camera tips down onto PODCAST on a lower, tilted plane |
| 7.2-9.6 | Curved pullback rising back to eye level, passing under the J and A | **Spatial alignment:** JAIN closes up and PODCAST rotates upright into the two-line title; the star docks beside it; the logo rises through a mask |
| 9.6-12.0 | 0.32 unit lateral drift, everything sharp | Star pulse (2.8 % scale + light) and a cyan ripple on the chime; fade to black over the last 0.35 s |

## Audio

An original cue synthesized in the browser (no samples, no licences): 100 BPM, 4/4, five bars
in D major. Bar 1 is a pad with a triangle-wave pulse; bar 2 brings in the bass, kick, rim and
hats; bar 3 lifts with 16th hats and the motif (D-E-A-F#); bar 4 answers and resolves through
A13; bar 5 lands on Dmaj9 with the motif cell as the signature, then a gentle fade from 11.45 s.

Sound design sits on the sfx bus at 0.55 of the music: opening tone (0.02 s), rising filtered
texture through the orbit (2.4-4.6 s), a stereo whoosh panned left to right with the column
(4.62 s), a short swish and low tick at the fastest pass (6.0 s), a low air pass for the letter
wipe (6.38 s) and a three-partial chime with the star pulse (9.6 s).

Master: 30 Hz high-pass and a gentle compressor. The rendered WAV measures about -14 LUFS
integrated with true peak around -1.9 dBFS.

### Replacing the music

Drop a licensed 12.0 s stereo track in as `renders/score.wav` after the render, then re-mux:

```bash
ffmpeg -i renders/jain-podcast-intro_1080p60.mp4 -i your-cue.wav -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 256k -ar 48000 -t 12 -movflags +faststart out.mp4
```

Keep these hits on the grid so the picture still lands: 0.00 opening accent, 2.40 groove
entry, 4.62 occlusion whoosh, 6.00 fly-through accent, 7.20 resolution starts, 9.60 final
downbeat (star pulse), music fully out by 12.00.
