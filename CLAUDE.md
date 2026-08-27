# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A fully local text-to-video pipeline (built from the book *Views on Autopilot*): five lines of
text become a voiced, captioned, rendered 1080×1920 reel. Stack: **HyperFrames** (`npx
hyperframes` — renders HTML compositions to MP4, needs Node ≥ 22 + ffmpeg), a per-OS **TTS
backend** for voice, **Whisper** (via `npx hyperframes transcribe`) for word timing, and
**ffmpeg** for the audio polish chain. Python scripts are stdlib-only; Node scripts are ESM with
zero npm dependencies. `PLAYBOOK.md` holds the content rules (hooks, skip rate, retention);
`README.md` the user-facing quickstart.

## Commands

```bash
bash setup/setup-mac.sh            # or setup-linux.sh / setup-windows.ps1 (installs deps, venv, config)
npx hyperframes doctor             # verify the toolchain

# Factory (the normal path)
node factory/new.mjs <slug> "Title"     # template → factory/building/<slug>/
node factory/enqueue.mjs <slug>         # building → queue
node factory/runner.mjs                 # runs the queue; dashboard at http://localhost:4300/dashboard.html

# Manual pipeline on one project
python3 pipeline/make_reel.py --project factory/building/<slug> --phase all   # or voice | render
# ...which chains: voice → audio_chain → transcribe → build_timeline → captions → build_index (phase voice)
#                  qa (lint/snapshot/render/frames/loudness) → finish (1.1× + deliver)  (phase render)
# Each step is also standalone: python3 pipeline/<step>.py --project <dir>

# Validation (run before spending a render)
npx hyperframes lint <projectDir> --json      # must be 0 errors; qa.py enforces this
npx hyperframes snapshot <projectDir> --at 0.2,7,14
python3 -m py_compile pipeline/*.py scheduler/*.py   # plus node --check factory/*.mjs

# Cartoon episodes (multi-character; see cartoon/README.md)
python3 cartoon/cast_voices.py --project <dir>            # needs <dir>/cast.json
python3 cartoon/episodes/last-laddu/compose.py --project <dir>   # instead of build_index.py

# Scheduler
python3 scheduler/generate_manifest.py --matrix m.csv --videos-dir factory/ready-to-post --out manifest.csv
python3 scheduler/push_schedule.py --manifest manifest.csv        # dry-run; --push to execute
```

There is no test suite; verification is the QA loop above plus an end-to-end run on a scratch
project (stand-in voice WAVs via ffmpeg `sine`, `"lang": "proportional"` to skip Whisper).

## Architecture

**The plan is sacred; generated files are disposable.** A project folder's authored inputs are
`lines.txt`, `project.json`, `BRIEF.md`, `assets/` (and `cast.json` for cartoons). Everything
else — `raw/`, `audio/`, `audio_meta.json`, `words.json`, `captions.json`, `timeline.json`,
`index.html`, `renders/`, `final/` — is regenerated from the plan; `build_index.py` and the
cartoon composers overwrite `index.html` wholesale. Never hand-edit generated files to fix
something; fix the generator or the plan. All media outputs are gitignored.

**Data flow between steps is JSON contracts**, not imports: each `pipeline/*.py` step reads its
predecessors' JSON from the project dir. `audio_meta.json` (per-line file/duration/start) is the
spine; captions and every composition tween derive timing from it, which is why the same
composition re-choreographs itself for a different language or pacing. `pipeline/common.py` is
the one shared module (config, subprocess, ffprobe/volumedetect helpers) — its API is relied on
by `pipeline/`, `integrations/`, and `cartoon/`.

**Config**: `pipeline/config.json` if present, else `pipeline/config.example.json` (setup copies
it). Voice backend `auto` probes in order: Chatterbox/MLX (macOS) → Chatterbox/PyTorch
(`chatterbox-tts` in the venv, any OS, cuda/mps/cpu) → XTTS → edge-tts → Kokoro (`npx
hyperframes tts`, always available). Chatterbox specifics: non-English routes to the
multilingual model (23 languages incl. Hindi, language id follows the project `lang`); the
reference clip's first ~10 s define the voice *and its accent*; emotion knobs
`chatterbox_exaggeration` (0.5 neutral, ~0.7 dramatic) and `chatterbox_cfg_weight` (~0.3
expressive, 0.0 preserves the reference accent). The Mac default model `chatterbox-turbo-fp16`
is **English-only and ignores those knobs** — Hindi/expressive on Mac needs
`mlx-community/chatterbox-multilingual-v3`. All JSON/text reads use `utf-8-sig` — Windows
PowerShell writes BOMs.

**Two caption modes** (`project.json` `"lang"`): `"en"` runs Whisper per line for word-level
sync; anything else (`"hindi"`, `"proportional"`) skips ASR and slices each line's audio
duration across ≤4-word groups of the *written* text — spelling always exact, no model download.
Non-Latin scripts need fonts: vendor `NotoSansDevanagari-{Regular,Bold}.ttf` into the project's
`assets/fonts/` (composers emit `@font-face` when present; lint errors on undeclared families).

**The factory is folders as a state machine**: `building/ → queue/ → work/ → done/|failed/`,
outputs copied to `output/` and `ready-to-post/`. `runner.mjs` is the **only writer of
`job.json` once a job leaves `building/`** — keep that one-writer rule. Concurrency: voice ×1,
renders ×3 (`FACTORY_RENDER_CONCURRENCY`). Jobs stuck in `work/` at startup are re-queued.

**Composition contract** (HyperFrames): everything visible is a `class="clip"` element with
`data-start`/`data-duration`/`data-track-index`; one **paused** GSAP timeline registered as
`window.__timelines.reel`; the renderer drives the clock (seek-safe — no wall-clock animation).
Track map: 0 background, 1 slides/scene, 2 overlays/title, 3 captions, 4 voice, 5 music, 6 sfx.
`template/index.html` uses `<!--HF:...-->` markers that `build_index.py` string-replaces.
`build_index.py` swaps a scene's `<img>` for a muted `<video>` when
`assets/footage/lineNN.mp4` exists (the LTX-2 lane; `integrations/ltx2/stage_footage.py`
re-encodes clips with dense keyframes and strips audio first).

## Renderer rules that cost real renders to learn

- The composition must be a full HTML document (`<!DOCTYPE html>…<body>`), not a bare fragment.
- Every `<audio>`/`<video>` clip needs an `id` or it is **silent/invisible** in renders
  (lint: `media_missing_id`).
- Animating SVG sub-elements: use GSAP `svgOrigin: "x y"` (element's own viewBox coords). CSS
  `transform-box: fill-box` + scale visibly **displaces the element mid-animation** in the
  headless renderer even though the browser preview looks fine. Mouth flaps are `attr: {ry}`
  tweens for exactly this reason.
- A fade ending exactly at a clip boundary needs an explicit `tl.set(el, {opacity: 0}, t_end)`
  at the fade's exact end time — captions are dense clips, so looping fades hit this constantly.
- Scaling a character rig: scale the **wrapper div**, never the inner SVG `<g>` — content
  scaled past the SVG viewport is clipped (a scaled-up rig loses its head).
- Don't tween a `<video>`'s size or clip-path (opacity/transform only); source footage needs
  dense keyframes (`-g 30 -keyint_min 30`) or seeks freeze; no animated GIFs.
- The preview lies. Verify by extracting frames **from the rendered MP4** (qa.py does this) —
  that is how every composition bug in this repo's history was actually caught.
- Numbers that are contractual: caption band top 1380px (never lower — Instagram UI covers it),
  safe zones 220px top / 420px bottom / 120px right, loudness gate −17…−13 dB mean
  (`volumedetect`), final speed-up ×1.1 applied only after QA, canvas 1080×1920@30.

## Repo-specific conventions

- TTS input goes through `common.speakable()` (danda/em-dash/ellipsis → plain punctuation)
  in `voice.py` and `cast_voices.py`; captions keep the authored text. Never feed `।` or `—`
  to a phonemizer. Keep cast pitch multipliers within ~0.92–1.08 or formants smear.
- ffmpeg calls: `-y -hide_banner -loglevel error`; the voice polish chain in `audio_chain.py`
  (highpass → afftdn → acompressor → loudnorm I=-14) is verbatim from the book — don't tune it
  casually; `remix.py` exists for re-mixing without re-generating voice.
- Back up before overwrite: voice/audio regeneration moves old takes to `raw.bak/`/`audio.bak/`.
- Cartoon episodes hardcode their staging to their line count (compose.py asserts 14 for
  last-laddu); a new script means a copied composer with re-mapped `CAM` and gags, not a bigger
  config. Cast files are dual-engine per speaker (`"edge"` + `"kokoro"` voice ids —
  `cast_voices.py` tries edge, falls back to kokoro); `pitch` is a post-processing multiplier,
  overridable per engine via `edge_pitch`/`kokoro_pitch`.
- `vercel.json` disables deployments on purpose (repo is not a web app) — leave it.
- No AI/model attribution in committed files, commit messages, or artifacts.
