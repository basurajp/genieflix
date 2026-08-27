# Cartoon lane — multi-character episodes

Everything else in this repo makes narrated reels. This lane makes *cartoons*:
several characters with their own voices, a drawn set, a camera that cuts every
line, per-speaker lip sync, and scripted physical gags — rendered by the same
HyperFrames pipeline, still fully local.

Five episodes ship as references:

- **The Last Laddu** (`episodes/last-laddu/`) — a kid, his grandma, a scheming
  cat, and a perfectly timed grandfather; English, Indian-English, and Hindi casts.
- **The Hundredth Blow** (`episodes/hundredth-blow/`) — motivational: Kabir
  and the rock everyone gave up on; strike choreography, a doubting passerby,
  and the split on blow one hundred. Narrator on `af_heart`, ear-written script.
- **The Moon in the Bucket** (`episodes/moon-bucket/`) — Anu, her Dadu, and a
  frog on a summer night; the moon falls into the water bucket, shatters at a
  touch, and heals when the water sits still. English and Hindi casts on
  Kokoro's best-graded voices with `kokoro_speed` storytelling pacing.
- **शांतिदूत कृष्ण** (`episodes/krishna-shanti/`) — the big one: a 28-beat,
  ~2.5-minute Mahabharata episode (Udyoga Parva — Krishna as the Pandavas'
  peace envoy, Duryodhan's refusal and the chaining attempt, the विश्वरूप).
  Four sets cut by narration boundaries, one persistent Krishna rig teleported
  between them (character consistency for free), four Hindi voices derived
  from two Kokoro bases via per-speaker `kokoro_speed`/`kokoro_pitch`, a
  synthesized tanpura drone on the music track, and a layered effect stack for
  the विश्वरूप (flash, aura, ray fan, divine arms, snapping chain links —
  every `fromTo` cued with `immediateRender: false`, every fade hard-killed).
  Study this one for: multi-set staging, per-project `speed_up` (it finishes
  at 1.0×), and scaling a rig via its **wrapper div** — scaling the inner SVG
  `<g>` clips at the SVG viewport (Krishna loses his head), the div doesn't.
- **एकलव्य** (`episodes/eklavya/`) — the counterpoint to the sabha episode:
  one sun-lit forest clearing (daylight greens/marigold palette), a female
  narrator (`hf_alpha`), and the Adi Parva guru-dakshina story — the clay
  statue rising from the earth, target practice, seven harmless arrows that
  silence the dog mid-bark, and the thumb offered with a smile. Study this
  one for: single-set staging, flipping a rig with `scaleX: -1` on its
  wrapper div at hard cuts (Eklavya turns between target and statue), and
  props that ride inside a character's own SVG (the arrow muzzle moves with
  the dog for free).

## How an episode is put together

1. **Script** — `lines.txt`, one beat per line. Dialogue and narration mixed.
2. **Cast** — `cast.json`: a speaker per line, and per speaker a voice for each
   engine plus an optional `pitch` multiplier (a kid = a bright voice ×1.13,
   an elder = ×0.93). Caption chips are tinted per speaker.
3. **Voices** — `cartoon/cast_voices.py --project <dir>` writes `raw/lineNN.wav`.
4. **Pipeline** — the normal steps time everything: `audio_chain`, `transcribe`,
   `build_timeline`, `captions`.
5. **Compose** — the episode's `compose.py` writes `index.html`: set, characters,
   camera plan, gags. All timing is read from the audio metadata, so the same
   staging re-choreographs itself for any language or pacing of the same beats.
6. **Render** — `pipeline/make_reel.py --project <dir> --phase render`.

## Make The Last Laddu (either language)

```bash
node factory/new.mjs my-laddu "The Last Laddu"
cp cartoon/episodes/last-laddu/lines.en.txt factory/building/my-laddu/lines.txt
cp cartoon/episodes/last-laddu/cast.en.json  factory/building/my-laddu/cast.json
# (Hindi: use lines.hi.txt + cast.hi.json, set the Devanagari title/topic in
#  project.json, and drop NotoSansDevanagari-{Regular,Bold}.ttf into
#  factory/building/my-laddu/assets/fonts/ so captions render everywhere)

python3 cartoon/cast_voices.py --project factory/building/my-laddu
for s in audio_chain transcribe build_timeline captions; do
  python3 pipeline/$s.py --project factory/building/my-laddu
done
python3 cartoon/episodes/last-laddu/compose.py --project factory/building/my-laddu
npx hyperframes lint factory/building/my-laddu
python3 pipeline/make_reel.py --project factory/building/my-laddu --phase render
```

Set `"lang"` in project.json to anything other than `en` (e.g. `hindi`,
`proportional`) — cartoon captions come from the written lines with
proportional timing, so dialogue spelling is always exactly as authored.

## Voice quality — read this if the voices sound robotic

Three tiers, best first:

1. **Your own voice clone** (Chapter 4 of the playbook): record a ~10 s
   reference per character (you, doing the voices — or one person pitch-shifted
   per role via `"pitch"`), generate with the Chatterbox/XTTS path, drop the
   WAVs into `raw/` yourself, and skip `cast_voices.py`. Human, because it is a
   human. Chatterbox adds emotion knobs (`chatterbox_exaggeration` ~0.7 for
   drama, `chatterbox_cfg_weight` ~0.3 for expressive pacing, 0.0 to keep the
   reference's accent) and speaks Hindi + 22 other languages from the same
   reference — see the config reference in the root README.
2. **edge-tts** (default): Microsoft neural voices — very close to human, free,
   needs internet. The shipped casts use real character voices, including an
   actual child voice for Arjun (`en-US-AnaNeural`). `pip install edge-tts`
   (the setup scripts' venv is fine). Note: some restricted networks block the
   speech endpoint; normal home/office networks work.
   **Indian voices**: `cast.en-in.json` casts the episode in Indian-accented
   English (`en-IN-PrabhatNeural` / `en-IN-NeerjaNeural`); the Hindi cast's
   edge upgrade uses `hi-IN-MadhurNeural` / `hi-IN-SwaraNeural`.
3. **Kokoro** (offline fallback): `npx hyperframes tts` — always works,
   flattest delivery. `cast_voices.py --engine auto` tries edge first and
   falls back per line automatically.

Whatever the engine, the text it *speaks* is normalized first
(`common.speakable`): Devanagari danda `।`, em-dashes and `...` become plain
periods/commas. Phonemizers render those literally or drop the pause —
this is the difference between "pronunciation is wrong" and clean Hindi.
Captions always show the line exactly as authored. Keep pitch shifts inside
~0.92–1.08: further out the formants smear and the voice stops sounding human.

## Authoring a new episode

Copy `episodes/last-laddu/compose.py` and treat it as a storyboard in code:

- **Set**: one background SVG (the kitchen) + prop clips (table, plate).
- **Characters**: each is a wrapper `<div class="clip">` holding an SVG rig.
  Walks, jumps, and slides animate the div (HTML transforms are safe);
  inner parts (arms, brows, tails, eyes) rotate/scale with GSAP `svgOrigin`
  — never CSS `transform-box`, which displaces mid-animation in the renderer.
  Mouths are `attr: {ry}` tweens; the speaking character's mouth flaps during
  that line's caption windows automatically.
- **Camera**: `CAM = {line: (scale, focus_x, focus_y)}` — a hard cut per line
  with a slow push-in, clamped so the frame never leaves the set.
- **Gags**: one block per line, scheduled inside `win(i)` so they stretch and
  shrink with the performance.
- Keep the pipeline's rules: every element is a timed clip with an id, fades
  ending on a boundary get a hard `tl.set`, and `npx hyperframes lint` must
  report zero errors before you spend a render.
- `fromTo` renders its *from*-values at time zero unless you pass
  `immediateRender: false` — any fromTo whose from-state must not exist before
  its cue (a shatter, a reveal) needs that flag, or the effect leaks into the
  opening frames.
