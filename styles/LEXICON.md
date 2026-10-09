# The Reel Lexicon

Names for everything a video designer and editor does to a reel, so a brief can
say *"swiss editorial, mask-reveal headline, karaoke captions, colour wipes on
the cuts, muted editorial grade, ASL around 3 s"* and mean one exact thing.

Every entry has three parts:

- **What** it is, in one or two sentences.
- **Spot it** — what you see on the decode sheets (`decode/decode_reel.py`),
  or which number in `REPORT.md` gives it away.
- **Build it** — how this repo produces it: a template (`styles/<name>`), a
  grade (`styles/grades.json`), a GSAP idiom, or an ffmpeg step.

Definitions were checked against the sources listed at the end. Where only
secondary sources exist (vendor blogs, tool docs) the entry says so.

---

## 1. Formats

The skeleton a reel hangs on. Decide it before style; style can't rescue the
wrong format (PLAYBOOK §2: you grade formats, not videos).

| Format | What | Spot it | Build it |
|---|---|---|---|
| **Talking head + inserts (A-roll / B-roll)** | A person to camera (A-roll) cut with illustrative footage (B-roll) and on-screen text. | One recurring face shot; contact sheet alternates face / other. | `kinetic-punch` with your clip as footage on talking lines, B-roll stills on proof lines. |
| **Faceless voice-over** | Narration over stock or generated footage; the voice and captions carry it. | No recurring face; captions on every shot. | The factory's default lane; any template. |
| **Street demo / POV** | Handheld, real place, often a second person reacting. The playbook's best performer. | Shaky motion energy, natural light, low grade. | `kinetic-punch` with grade `neutral` or `camcorder`. |
| **Listicle / steps** | "3 tools that…": numbered beats. | Big numerals or counters per shot. | `swiss-editorial` (numerals) or `neo-brutal` (badges). |
| **Before / after** | One thing shown twice, changed. | Two similar shots back to back, often a wipe between. | Two lines, same framing; `cine-doc` dissolve or `swiss-editorial` wipe. |
| **Screen recording / tutorial** | UI captured, zoomed into the click. | Flat UI frames, punch-ins on regions. | `kinetic-punch` punch-ins; grade `none` (keep UI colours exact). |
| **Story / mini-doc** | A narrative with a turn; slower cutting. | ASL > 3 s, dissolves, music swell. | `cine-doc`. |
| **Text-led / quote card** | Type is the picture; footage is texture. | Flat or blurred backgrounds, big type. | `swiss-editorial` with `--fit blur` footage. |
| **Green-screen / newsroom** | Creator keyed over a headline or screenshot. | Same person, changing flat backgrounds. | Key the creator externally (`npx hyperframes remove-background`), stage as footage. |

---

## 2. Edit grammar — the cuts

**Hard cut (straight cut)** — One shot ends, the next begins, no transition.
*Spot it:* `hard` boundaries in `REPORT.md`; `cuts/cut-NN.jpg` changes in one frame.
*Build it:* the default between scenes in every template.

**Jump cut** — The same shot with time removed, so the subject "jumps". The
creator staple for removing pauses and filler. *Spot it:* `jump cut (same set-up)`
boundaries in `REPORT.md`; near-identical neighbours on the contact sheet. *Build it:* cut the voice lines
tighter; in `kinetic-punch` the punch-in alternation reads as a jump cut.

**Punch-in (digital zoom cut)** — A cut to a tighter crop of the same frame,
done in post, to vary a single-camera shot and stress a word. Used with
restraint: punch-ins on every few seconds get tiring.
*Spot it:* `punch-in ×1.14` / `punch-out ×1.14` boundaries in `REPORT.md` (the
decoder checks whether the next frame is the previous one rescaled).
*Build it:* `kinetic-punch` alternates scale 1.0 / `punch_scale` (default 1.14) on
every caption group: `tl.fromTo(media, {scale: base}, {scale: base + 0.03, …})`.

**Match cut** — Two different shots linked by shared shape, motion or
composition (the bone-to-spaceship cut in *2001*). *Spot it:* `cuts/` strips
where a shape keeps its position across the cut. *Build it:* a footage problem —
frame the shared shape in the same place in both clips (`pipeline/footage.py --focus`).

**Smash cut** — An abrupt cut between very different moments, loud to quiet
or calm to chaos, for comedy or shock. *Spot it:* large brightness / energy jump
at a hard boundary. *Build it:* hard cut plus a sound change (silence or impact).

**Cutting on action (match on action)** — Cut in the middle of a movement and
continue it in the next shot; the motion hides the edit. *Spot it:* motion blur
on both sides of a cut. *Build it:* trim clips so the move straddles the scene
boundary (`--start` on `footage.py`).

**Cutaway / insert** — Leave the main subject for a detail, then return.
*Build it:* a short line that is only the detail; the template treats it as a scene.

**J-cut / L-cut (split edits)** — In a J-cut you hear the next shot before you
see it; in an L-cut the current shot's sound carries over the next picture.
*Spot it:* sound onsets that lead or lag cuts (`REPORT.md` → Sound).
*Build it:* not automatic: the pipeline cuts voice and picture together. Shift a
scene's media with `--start`, or add an SFX that starts before its scene.

**Cross-cutting (parallel editing)** — Alternating between two lines of action
happening at once. Rare in reels; useful for before/after told as one.

**The Kuleshov effect** — Viewers read a shot by what's next to it (the same
neutral face reads hungry next to soup, grieving next to a coffin). Why the
proof line's visual must be the *thing*, not a pleasant generic: the cut does
half the persuading.

---

## 3. Transitions

**Cross-dissolve** — The outgoing shot fades out as the incoming fades in.
Signals time passing or a softer change. *Spot it:* `dissolve` (the decoder
checks that the middle frame is a blend of its ends). *Build it:* `cine-doc`
(`scene_overlap` 0.6 s + incoming opacity 0→1).

**Dip to black / white** — Fade through a black (or white) frame. Black closes a
chapter; white feels like a flash or memory. *Spot it:* `dip to black/white`.
*Build it:* `cine-doc` dips into the CTA.

**Flash frame / flash cut** — One to three white frames on the cut: energy,
"click", a camera flash. *Spot it:* `flash-frame (white)` events.
*Build it:* `kinetic-punch` (`.flash` clip, 0.2 s, opacity 0.9→0).

**Colour wipe** — A solid colour field sweeps across, covers the frame at the
cut, and clears to reveal the next shot. Graphic, brand-coloured.
*Spot it:* `colour wipe / dip through colour`. *Build it:* `swiss-editorial`
(accent panel, expo.in in, two-frame hold, expo.out out).

**Push / slide** — The incoming shot pushes the outgoing one off frame.
*Spot it:* `whip / push / zoom` boundaries; between two similar shots
(e.g. both black and white) it lands under "possible transitions" for review. *Build it:* `neo-brutal`
cards (x 1150 → 0 in with `back.out`, flung to −1250 out).

**Whip pan (swish pan)** — A very fast pan that smears into motion blur; the
next shot starts with a matching pan the same way, so the blur carries the eye.
*Spot it:* blurred frames on both sides of a soft boundary. *Build it:* a
footage move; fake it with an x tween plus a blur-smeared still of the cut frame.

**Zoom transition** — The camera (or a digital zoom) rushes in at the cut and
the next shot lands from the zoom. *Build it:* `kinetic-punch` (incoming scale
1.32 → 1.0 in 0.42 s, `expo.out`, under the flash).

**Speed ramp** — Playback speed changes inside a clip (fast → slow → fast),
often into a whip or a key moment. *Build it:* in staging, before
transcription: `ffmpeg setpts` segments. Never after timing is fixed (PLAYBOOK
gotcha #5).

**Light leak / film burn** — Warm flares washing over a cut. *Build it:*
HyperFrames' registry overlay (`npx hyperframes add` — the `Organic Light Leak`
treatment) or a screen-blended leak clip as footage.

**Glitch / RGB split / datamosh** — Digital corruption as a transition.
*Build it:* grade `camcorder` for the chroma bleed; full glitch needs
HyperFrames' `digitalGlitch` effect (GPU only, see §8).

---

## 4. Pacing and rhythm

**ASL (average shot length)** — Running time ÷ number of shots. Low ASL = fast
cutting. Report the **median** too: a few long shots drag the mean.
*Spot it:* `REPORT.md` → Edit. Measure your reference reels and copy their
number rather than guessing. The factory default (one scene per spoken line)
runs 4–5 s, which is why every template adds motion *inside* scenes, and why
`kinetic-punch` adds a punch-in on every caption group.

**Cutting rate** — Cuts per 10 s, and how it changes over the reel (the 5 s
windows in `REPORT.md`). Worth reading on every reference: where does it cut
fastest, and where does it let a shot breathe?

**Cutting on the beat** — Cuts landing on music hits. *Spot it:*
`cuts_on_onset_ratio` vs `chance_ratio` — the decoder only calls it beat-driven
when the first clearly beats the second. *Build it:* pick a music BPM where the
beat lands near your line gaps, or nudge `line_gap` in `config.json`; HyperFrames'
`npx hyperframes beats <project>` writes the music bed's beat grid.

**Visual state change every 2–3 s** — The playbook's anti-scroll rule. *Spot
it:* `longest_static_stretch` in `REPORT.md` (over 3 s is a warning). *Build it:*
every template moves something continuously — Ken Burns, punch-ins, a progress
bar, rotating stickers.

**Hook window** — The first 3 s decide the skip rate. *Spot it:* `hook.jpg`
(10 fps). Count: is the promise on screen by 0.2 s? Does something move from
frame zero? When is the first cut?

---

## 5. Camera and framing moves

**Ken Burns effect** — Slow pan and zoom across a still (or slow footage), drifting
from detail to detail; named after the documentarian, used where no moving
footage exists. *Build it:* every template; `cine-doc` alternates push-in and
pull-out with lateral drift (`sine.inOut`).

**Push-in / pull-out (dolly in / out)** — The frame moves toward or away from
the subject. Push-in = intensity, pull-out = reveal or release.

**Handheld / camera shake** — Organic jitter. Small shake on an impact word
reads as energy. *Build it:* `kinetic-punch` shakes the caption on money words
with a seeded PRNG (`R.rng`) — never `Math.random` (parallel render workers
would disagree).

**Letterbox / matte** — Black bars that crop to a wider frame (2.39:1 is the
anamorphic "scope" ratio). On a 9:16 reel the bars can sit over the phone's UI
zones, so they cost nothing visible. *Build it:* `cine-doc` (300 px / 420 px bars).

**Reframe (9:16 from landscape)** — Crop to fill (`--fit cover`, `--focus` sets
the crop centre) or fit inside a blurred copy of itself (`--fit blur`, the
"blur-pad" common for landscape clips).

**Symmetry / centred framing** — Subject dead centre, symmetrical staging
(Wes Anderson's signature, often with whip pans and pastel palettes).

---

## 6. Motion design

### The twelve principles (Thomas & Johnston, *The Illusion of Life*, 1981)

Squash and stretch · anticipation · staging · straight-ahead vs pose-to-pose ·
follow-through and overlapping action · slow in and slow out · arcs · secondary
action · timing · exaggeration · solid drawing · appeal.

The four that matter most for type and UI-style motion:

- **Slow in / slow out (easing)** — Nothing starts or stops at full speed.
- **Anticipation** — A small move the other way before the big one (`back.in`).
- **Follow-through / overshoot** — Past the mark, then settle (`back.out`, `elastic.out`).
- **Staging** — One thing moves at a time where the eye should be.

### Easing names (GSAP)

| Ease | Feel | Where we use it |
|---|---|---|
| `power1`–`power4` (`.in/.out/.inOut`) | Gentle → strong acceleration curves | exits (`power3.in`), drifts |
| `expo.out` | Very fast attack, long settle — "premium", editorial | `swiss-editorial` reveals |
| `expo.inOut` | Snap through the middle | wipes, clip-path opens |
| `back.out(n)` | Overshoot then settle (follow-through); `n` = how far | stickers, word pops, cards |
| `elastic.out` | Springy wobble | sparingly, playful brands |
| `sine.inOut` | Smooth, breathing | Ken Burns, ambient motion |
| `steps(n)` | Jumps in n frames, no in-betweens: stop-motion / hand-made | `neo-brutal` wiggles |
| `none` (linear) | Mechanical, constant | progress bars, rotations |

**Stagger** — The same animation on a list, offset per item (`stagger: 0.06`);
`from: "center"` spreads from the middle.

**Timing rules of thumb** used across the templates: entrances 0.3–0.7 s,
exits faster than entrances (0.2–0.35 s), word pops 0.15–0.2 s, nothing slower
than 1 s unless it is ambient.

### Renderer-safe motion (learned from renders, see CLAUDE.md)

Tween transforms and opacity. Never tween `letter-spacing`, `width`, `height`
or other layout properties (they snap to whole pixels and jitter — HyperFrames'
lint rejects them). `clip-path` tweens are fine on text and divs, not on
`<video>`. Every value must be a pure function of time: one paused timeline, no
timers, no wall clock, no `Math.random`.

---

## 7. Kinetic typography

**Kinetic typography** — Text that moves or changes over time; the type is the
animation.

**Mask reveal (track-matte reveal)** — Text slides into view from behind an
invisible edge, as if rising out of a slot. *Build it:* `R.maskWords()` wraps
each word as `<span class="m"><span class="mi">` (outer `overflow: hidden`),
then `yPercent: 105 → 0`. `swiss-editorial` everywhere.

**Clip-path wipe** — A shape uncovers the element (`clipPath: inset(0 0 100% 0)
→ inset(0 0 0% 0)`). `swiss-editorial` CTA card.

**Stagger reveal** — Words or letters enter one after another.

**Tracking in** — Letters drift together as a title resolves, the cinematic
title move. *Build it:* per-letter spans (`R.charSpans`) with x offsets from
`R.trackOffsets` easing to 0. `cine-doc` title and end card.

**Typewriter** — Characters appear one at a time, often with a blinking caret.

**Scramble / decode** — Random glyphs cycling before resolving to the word.
*Build it:* swap textContent at fixed times with `tl.call` — seeded, not random.

**Word-by-word pop captions ("Hormozi-style")** — 2–4 words on screen, each
popping in with a little bounce as it's spoken, heavy all-caps sans with a thick
black outline, the live word recoloured (yellow; green/red for emphasis). Specs
come from tools that reverse-engineered the look (secondary sources).
*Build it:* `kinetic-punch` (Montserrat 900, `-webkit-text-stroke` +
`paint-order: stroke fill`, `back.out(3)` pop, money words green).

**Karaoke reveal** — Words appear exactly on their spoken syllable and stay.
*Build it:* `swiss-editorial` (mask reveal at each word's start time).

**Marker highlight** — A highlighter swipe behind the live word. *Build it:*
`neo-brutal` (`.hl` span, `scaleX 0→1` from the left, out to the right).

**Cinema subtitles** — Sentence-length lines, no box, hard cuts on and off,
bottom of the picture. *Build it:* `cine-doc` merges caption groups up to
`subtitle_chars` (42).

**Boxed caption chip** — Text on a ~85%-opaque rounded box. The classic
template's default.

**Lower third** — A name/title strip in the lower third of frame. *Build it:*
`cine-doc` chapter cards are the vertical-video version (upper area, since the
lower third is where captions and the app UI live).

**Sticker typography** — Text on rotated, outlined or shadowed blocks, like a
physical sticker. `kinetic-punch` hook and CTA, `neo-brutal` throughout.

### Type classification (what to ask for)

| Class | Character | Fonts vendored here (all SIL OFL) |
|---|---|---|
| Neo-grotesk | Neutral, rational, Helvetica lineage — Swiss | Inter Tight (`swiss-editorial`) |
| Geometric sans | Built from circles/lines, heavy weights read loud | Montserrat (`kinetic-punch`) |
| Grotesque (quirky) | Irregular, characterful display sans | Bricolage Grotesque (`neo-brutal`) |
| Display serif / transitional | Literary, cinematic, editorial | Instrument Serif (`cine-doc`) |
| Humanist / clean sans | Readable subtitles and labels | Instrument Sans (`cine-doc`) |
| Monospace | Technical, labels, tags, index numbers | IBM Plex Mono, Space Mono |

Non-Latin scripts: every template's stack falls back to Noto Sans Devanagari;
vendor `NotoSansDevanagari-{Regular,Bold}.ttf` into the project's
`assets/fonts/` for Hindi (`build_index.py` declares them).

---

## 8. Art directions

**International Typographic Style (Swiss Style)** — Grid, asymmetric layouts,
sans-serif type (Helvetica, Akzidenz-Grotesk, Univers), flush-left /
ragged-right, photography over illustration, lots of white space; clarity over
decoration. Josef Müller-Brockmann's *Grid Systems in Graphic Design* (Niggli,
1981) is the canonical text. → **`swiss-editorial`**.

**Bauhaus** — Primary colours with black and white, circles/squares/triangles,
sans-serif often lowercase, type as a design element. (Strictly a school and
teaching method, 1919–1933, whose output varied — "Bauhaus style" in a brief
means this visual shorthand.) → `neo-brutal` with params
`yellow/blue/pink` set to primaries.

**Neubrutalism (neo-brutalism)** — Raw, loud, hand-made: thick black outlines,
zero-blur offset shadows, flat saturated colour, oversized quirky type with
plain body text, asymmetric layouts. Sources are design blogs, not scholarship.
→ **`neo-brutal`**.

**Memphis** — Milan, early 1980s (Ettore Sottsass): bold primaries plus pastels,
squiggles, dots, terrazzo patterns, geometric shapes, "form follows fun".
→ `neo-brutal` with pastel params and pattern shapes.

**Y2K** — Early-2000s futurism: chrome and liquid-metal type, inflated bubble
forms, translucency, candy colours (bubblegum pink, electric blue, lime).

**Vaporwave** — 80s/90s internet nostalgia: Greek busts, Windows-95 windows,
Japanese text, malls, neon pinks and cyans, deliberate low-fi glitch.
**Synthwave** is its glossier, polished 80s-retro cousin.

**Editorial / magazine** — Big serif or grotesk headlines, captions as
pull-quotes, generous margins, muted photography. → `swiss-editorial` or `cine-doc`.

**Cinematic documentary** — Letterbox, slow camera, serif titles, chapter
cards, dissolves, film grade and grain. → **`cine-doc`**.

**Creator-native / UGC** — Looks shot on a phone by a person, not a brand:
captions on every word, punch-ins, flash cuts, stickers, no glossy grade. The
playbook's data says this out-pulls polish. → **`kinetic-punch`**.

**Lo-fi / camcorder / found footage** — Soft detail, chroma bleed, noise, REC
dot, timecode or date stamp. → grade `camcorder`; HyperFrames' `Creator
Camcorder` / `VHS Playback` treatments on GPU machines.

**Collage / zine / cut-out** — Photos as cut-outs on paper, tape, stickers,
mixed type, often B&W photos on colour fields. → `neo-brutal` + `mono-classic`.

**Minimalism** — Few elements, one typeface, lots of space, slow motion.

**Wes Anderson-style** — Symmetrical centred framing, planar staging, pastel
palettes, whip pans.

---

## 9. Colour grading

**Correction vs grade** — Correction fixes exposure, white balance and contrast
so shots match; the grade is the look on top. `neutral` is correction-only.

**LUT (look-up table)** — A file (`.cube`) mapping input colours to output
colours: a portable grade. Real film emulations ship as scanned LUTs.
*Build it:* `footage.py --lut look.cube`.

**Split toning** — Different tints in shadows and highlights (from darkroom
printing). Warm highlights / cool shadows is the common pairing.

**Teal & orange** — Split tone with cool teal shadows/backgrounds and warm
highlights and skin; complementary colours separate the subject from the
background. Dominant in blockbusters (only secondary sources found on its
history). → grade **`teal-orange`**.

**Bleach bypass (skip bleach, silver retention)** — Skipping the bleach step
keeps silver in the film alongside the colour dyes: a black-and-white image
over the colour one. Lower saturation, higher contrast, denser blacks, more
grain (*Saving Private Ryan*, *Se7en*). → grade **`bleach-bypass`** (a mono layer
overlay-blended over colour).

**Cross-processing** — Developing slide (E-6) film in negative (C-41)
chemistry (or the reverse): strong colour shifts (often yellow-green), higher
saturation and contrast. → grade **`cross-process`**.

**Day for night** — Shooting in daylight and darkening plus blue-tinting to
read as night (moonlight reads bluish to the eye). → grade **`day-for-night`**.

**Matte / lifted blacks / film fade** — Blacks raised so nothing is pure
black, highlights rolled off. → grade **`film-fade`**.

**Crushed blacks / high contrast** — Shadows clipped to black. → `noir`.

**High-key / low-key** — Bright and low-contrast vs dark and contrasty
(chiaroscuro). The decoder flags both.

**Monochrome** — Black and white; strongest with one accent colour in the type.
→ grade **`mono-classic`**.

**Film emulation** — Grades imitating a stock's colour, contrast and grain.
Parametric grades suggest a stock; only a scanned LUT reproduces one.
→ `warm-film` (portrait-stock feel), or `--lut` with a real scan.

**Halation** — The red glow around bright lights on film without an
anti-halation layer — the signature of CineStill 800T, a Kodak cinema stock with
its rem-jet backing removed. Tungsten-balanced, so daylight shots go cold blue.
→ grade **`cinestill-night`** (red-tinted blur of the highlights, screen-blended).

**Muted editorial** — Saturation pulled to ~75 %, gentle lift, cool shadows:
lets type carry the colour. → grade **`muted-editorial`**.

**Bright pop** — Saturated, contrasty, sharpened for phone screens. → **`bright-pop`**.

Compare grades on your own footage before choosing:
`python3 pipeline/footage.py --project <dir> --grade-sheet clip.mp4`.

**Why grades are baked, not live.** HyperFrames has a real-time shader grading
engine (`data-color-grading`: wheels, curves, HSL secondaries, LUTs, grain,
halftone, VHS, glitch). Measured in a CPU-only container it rendered at about
18 s per frame — over four hours for a 30 s reel. With a GPU it is the richer
option (set `"hf_grading": {...}` in `project.json`); without one, the ffmpeg
grades here render at normal speed and look the same in preview and render.

---

## 10. Texture and finishing

| Term | What | Build it |
|---|---|---|
| **Film grain** | Fine random texture of film emulsion | grade `grain`, or `--grain 0..1` |
| **Vignette** | Darkened corners pulling the eye centre | grade `vignette`, `--vignette 0..1`; CSS radial overlay in `cine-doc` |
| **Halation** | Red glow round highlights | `cinestill-night` |
| **Bloom** | White glow round highlights | HyperFrames `bloom` (GPU) |
| **Chromatic aberration / RGB split** | Colour fringes offset by channel | `camcorder` (`chromashift`) |
| **Scanlines / CRT** | Horizontal display lines, curved glass | HyperFrames `scanlines` / `crtCurvature` (GPU) |
| **Halftone** | Image as print dots | HyperFrames `Editorial Halftone` (GPU) |
| **Gate weave** | Slight frame wobble of a film projector | 1–2 px seeded x/y jitter on the scene |
| **Paper / dot grid** | Printed-surface background | `neo-brutal` `#paper` |

---

## 11. Sound for the edit

**Riser** — Builds pitch, volume or density toward a moment; it should crest
exactly on the hit. **Whoosh** — A short pass-by sweep placed on the cut to
mask it. **Impact (hit)** — The percussive, low-end payoff. **Sound bridge** —
Sound that carries across a cut (the J- and L-cut family). **Ducking** — Music
dipping under the voice. **Silence** — A one-beat drop before a reveal.

Repo rules still apply (PLAYBOOK §5): music felt not heard (~−31 dB), one SFX
per visual beat at most, never stacked. Each `style.json` names the SFX that
fit its grammar.

---

## 12. Brief vocabulary → this repo

| Say in a brief | Means here |
|---|---|
| "Swiss", "editorial grid", "red accent" | `"style": "swiss-editorial"`, `style_params.accent` |
| "Hormozi captions", "creator edit", "punch-ins" | `"style": "kinetic-punch"`, `punch_scale` |
| "cinematic", "doc", "film look" | `"style": "cine-doc"`, grade `teal-orange` / `warm-film` |
| "neubrutalism", "collage", "stickers" | `"style": "neo-brutal"` |
| "B&W with one colour" | grade `mono-classic` + any accent param |
| "matte film", "faded" | grade `film-fade` |
| "silver, gritty" | grade `bleach-bypass` |
| "neon night, glow" | grade `cinestill-night` |
| "VHS", "camcorder", "found footage" | grade `camcorder` |
| "cut on the beat" | check `cuts_on_onset_ratio`; set music BPM and `line_gap` |
| "faster" | shorter lines (more scenes), `kinetic-punch`; target ASL < 2 s |

---

## Sources

Editing grammar: [Vimeo — J-cuts, L-cuts and jump cuts](https://vimeo.com/blog/post/j-cuts-l-cuts) ·
[No Film School — eight essential cuts](https://nofilmschool.com/essential-cuts-every-video-editor-needs-know) ·
[Backstage — types of cuts](https://www.backstage.com/magazine/article/types-of-cuts-in-film-75730/) ·
[Wikipedia — Cutting on action](https://en.wikipedia.org/wiki/Cutting_on_action) ·
[No Film School — Kuleshov effect](https://nofilmschool.com/Kuleshov-effect-definition) ·
[How To Film School — punch in](https://howtofilmschool.com/dictionary/punch-in/) ·
[Splice — fast transitions](https://spliceapp.com/blog/mastering-fast-transitions-in-video-editing/)

Pacing: [Wikipedia — Shot (filmmaking), ASL](https://en.wikipedia.org/wiki/Shot_(filmmaking)) ·
[Cinemetrics](https://cinemetrics.uchicago.edu/article/ed328545-4793-48f9-91ed-7ab04ac4a560)

Motion: [Wikipedia — Twelve basic principles of animation](https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation) ·
[Wikipedia — Ken Burns effect](https://en.wikipedia.org/wiki/Ken_Burns_effect)

Type and captions: [Framer — masked text reveal](https://www.framer.com/marketplace/components/masked-text-reveal/) ·
[Choppity — Hormozi editing style](https://www.choppity.com/tools/recreate-video-editing-style/alex-hormozi/) (vendor) ·
[OpenClip — Hormozi-style captions](https://openclip.app/use-cases/hormozi-style-captions) (vendor)

Art direction: [Wikipedia — Swiss Style](https://en.wikipedia.org/wiki/Swiss_Style_(design)) ·
[Slanted — Grid Systems in Graphic Design](https://www.slanted.de/?p=792761) ·
[Design Shack — Bauhaus graphic design](https://designshack.net/articles/trends/bauhaus-graphic-design/) ·
[SVGator — neubrutalism](https://www.svgator.com/blog/neubrutalism-in-web-design-embracing-the-ugly/) (blog) ·
[Art in Context — Memphis design](https://artincontext.org/?p=49717) ·
[Made Good Designs — Y2K graphic design](https://madegooddesigns.com/y2k-graphic-design/) (blog) ·
[Bandcamp Daily — vaporwave iconography](https://daily.bandcamp.com/features/vaporwave-iconography-column) ·
[Videomaker — Wes Anderson style](https://www.videomaker.com/how-to/directing/storytelling/what-can-we-learn-from-the-wes-anderson-style/)

Colour: [Wikipedia — Bleach bypass](https://en.wikipedia.org/wiki/Bleach_bypass) ·
[ASC — silver retention](https://theasc.com/magazine/nov98/soupdujour/pg3.htm) ·
[Lomography — cross processing](https://www.lomography.com/school/what-is-cross-processing-fa-bne2kolj) ·
[Wikipedia — Day for night](https://en.wikipedia.org/wiki/Day_for_night) ·
[Blender manual — split toning](https://docs.blender.org/manual/zh-hans/5.2/compositing/types/creative/split_toning.html) ·
[Morphic — teal and orange](https://morphic.com/de/ai-glossary/teal-and-orange) (secondary) ·
[B&H — CineStill 800T](https://www.bhphotovideo.com/c/product/1046360-REG/cinestill_800135_cinestill_800_tungsten_film.html) ·
[Wikipedia — Anamorphic widescreen](https://en.wikipedia.org/wiki/Anamorphic_widescreen)

Sound: [IRPR — riser](https://sounddesign.irpr.agency/glossary/riser/) ·
[IRPR — whoosh](https://sounddesign.irpr.agency/glossary/whoosh/) ·
[IRPR — impact](https://sounddesign.irpr.agency/glossary/impact/)
