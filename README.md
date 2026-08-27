# Views on Autopilot — local text-to-video pipeline

Type five lines into a file. Your laptop speaks them in your cloned voice, syncs
captions to every word, lays it all out on a 9:16 canvas, and renders a finished
Instagram reel — offline, in about twenty seconds, for ₹0.

This repository is that machine: the full working pipeline from the book, plus a
folder-driven factory that renders whatever you drop into it (with a live
dashboard), and a scheduler that turns a stockpile of finished reels into a month
of posts. Everything runs on your machine. Nothing is uploaded anywhere.

## The stack

Four free tools do the work; everything else in this repo is glue that runs them
in sequence.

| Tool | Job |
| --- | --- |
| **HyperFrames** (`npx hyperframes`) | **Renders.** Video from HTML — a composition is a web page played against a single paused timeline and photographed frame by frame into an MP4. |
| **Chatterbox** (Mac) / **XTTS** / **edge-tts** / **Kokoro** | **Voice clones.** One clean reference WAV of you talking, then any line of text spoken in your voice, locally, in seconds. |
| **Whisper** (`npx hyperframes transcribe`) | **Times.** Word-level start/end timestamps from the generated voice, so captions and entrances land on the exact syllable. |
| **ffmpeg** | **Polishes.** The broadcast audio chain, music-bed leveling, loudness measurement, and the final 10% speed-up. |

Requirements: Node >= 22, ffmpeg, Python 3.10+. The Python pipeline scripts are
stdlib-only; the Node scripts have zero npm dependencies.

## Quickstart

1. **Run the setup script for your OS** (idempotent — safe to re-run):

   | OS | Command |
   | --- | --- |
   | macOS | `./setup/setup-mac.sh` |
   | Windows | `powershell -ExecutionPolicy Bypass -File setup\setup-windows.ps1` |
   | Linux | `./setup/setup-linux.sh` |

2. **Check the toolchain**: `npx hyperframes doctor` (the setup scripts run it
   for you at the end).

3. **Record your voice reference** — 1–2 minutes of clean speech, no music, no
   hum, no echo — as `voice-samples/voice-sample.wav`. See
   `voice-samples/README.md`. (Skip if you're using edge-tts or Kokoro.)

4. **Create a project**:

   ```bash
   node factory/new.mjs my-first-reel "My first reel"
   ```

5. **Fill in the plan** in `factory/building/my-first-reel/`:
   - `lines.txt` — five lines: hook, action, proof, contrast, CTA
     (the formula, with examples, is in [PLAYBOOK.md](PLAYBOOK.md));
   - `assets/slides/slide01.png …` — one visual per line (fewer is fine; the
     last slide repeats).

6. **Queue it**:

   ```bash
   node factory/enqueue.mjs my-first-reel
   ```

7. **Start the factory**: `./factory/start.command` on Mac,
   `factory\start.bat` on Windows, `node factory/runner.mjs` anywhere.

8. **Watch it work** at <http://localhost:4300/dashboard.html> — jobs flow
   Building → Queued → Voicing → Rendering → Done, with live timers, inline
   previews, and Retry/Cancel/Pause buttons.

9. **Post it.** The finished reel lands in `factory/ready-to-post/my-first-reel.mp4`.

npm aliases for the same commands: `npm run new -- <slug> "Title"`,
`npm run enqueue -- <slug>`, `npm run factory`, `npm run doctor`.

## Manual pipeline

The factory just runs these steps for you. Each is a standalone script under
`pipeline/` (run with `python3` on Mac/Linux, `py -3` on Windows); all take
`--project <dir>` and read `pipeline/config.json` themselves.

```bash
python3 pipeline/make_reel.py --project factory/building/my-first-reel            # everything, 1-8
python3 pipeline/make_reel.py --project <dir> --phase voice                        # steps 1-6 only
python3 pipeline/make_reel.py --project <dir> --phase render                       # steps 7-8 only
```

| Step | Script | Produces |
| --- | --- | --- |
| 1 | `voice.py` | `raw/lineNN.wav` — one TTS take per line (backs up old takes to `raw.bak/` before overwriting) |
| 2 | `audio_chain.py` | `audio/lineNN.wav` — the exact highpass → denoise → compress → loudnorm chain, mono 24 kHz |
| 3 | `transcribe.py` | `words.json` — per-word timestamps via Whisper, corrections dictionary applied |
| 4 | `build_timeline.py` | `timeline.json` — scenes mapped to slides, line starts and total duration |
| 5 | `captions.py` | `captions.json` — ≤4-word caption groups on the absolute timeline |
| 6 | `build_index.py` | `index.html` — the HyperFrames composition, generated from `template/` |
| 7 | `qa.py` | lint → snapshots → render → frames extracted from the real MP4 → loudness check |
| 8 | `finish.py` | `final/<slug>.mp4` — the 10% speed-up pass, copied to `factory/ready-to-post/` |

Two one-command tools from the book:

- `python3 pipeline/revoice.py --project <dir>` — regenerate the whole project in
  your voice (backs up the old audio first, then forces steps 1–8). Text script
  in, finished my-voice video out.
- `python3 pipeline/remix.py --project <dir>` — "the words are right, the sound
  isn't": re-normalize the existing voice lines, rebuild timing/captions/
  composition, re-render. No TTS.

**Generated vs sacred:** `lines.txt`, `project.json`, `BRIEF.md`, and your slides
are the plan and survive everything. `index.html`, audio, timings, and renders
are generated and get wiped on regeneration — if you want a custom element to
survive, put it in the plan (the template), never in the output.

## Repo map

```
README.md, PLAYBOOK.md        this file; the taste rulebook from the book
package.json, .gitignore      npm aliases (no dependencies); keep media out of git
setup/                        one-shot setup scripts per OS
voice-samples/                your voice reference lives here (gitignored)
pipeline/                     the step scripts above + common.py, config, corrections.json
template/                     the reference project every new video is copied from
  lines.txt, project.json     the plan: five lines + metadata
  index.html                  composition template (placeholder markers, filled by build_index.py)
  assets/                     vendored gsap.min.js, fonts/, music/, sfx/, slides/
factory/                      folders-as-state-machine renderer + dashboard
  building/ queue/ work/      a job is a folder; it moves left to right
  done/ failed/ output/       ...and ends here
  ready-to-post/              finished, named, verified MP4s
  runner.mjs, dashboard.html  the worker and the live view on :4300
scheduler/                    matrix -> manifest -> scheduled posts (see scheduler/README.md)
```

## Config reference

`pipeline/config.json` if present, else `pipeline/config.example.json`. `~` is
expanded; relative paths resolve from the repo root.

| Key | Default | What it does |
| --- | --- | --- |
| `voice_backend` | `auto` | `auto` \| `chatterbox` \| `xtts` \| `edge` \| `kokoro`. Auto probes in that order: MLX venv on a Mac → Coqui TTS in the venv → edge-tts → Kokoro (`npx hyperframes tts`, works everywhere). |
| `voice_reference` | `voice-samples/voice-sample.wav` | The reference WAV the clone copies. |
| `voice_venv` | `~/.voice-clone-venv` | Python venv holding the voice backend. The Windows setup script creates `.voice-clone-venv` inside the repo and points this at it. |
| `chatterbox_model` | `mlx-community/chatterbox-turbo-fp16` | MLX Chatterbox build (Apple Silicon Mac only). |
| `xtts_model` | `tts_models/multilingual/multi-dataset/xtts_v2` | Coqui XTTS v2 — the Windows/Linux clone path. |
| `edge_voice` | `en-US-GuyNeural` | edge-tts voice (free, not your clone, needs network). |
| `kokoro_voice` | `am_michael` | Kokoro voice for the built-in fallback TTS. |
| `whisper_model` | `small.en` | Whisper model for word timestamps. |
| `line_gap` | `0.35` | Seconds of air between narration lines. |
| `music_target_db` | `-31.0` | Effective music-bed level — felt, not heard (−33..−30 range). |
| `sfx_volume` | `0.22` | SFX level. One effect per visual beat, never stacked. |
| `speed_up` | `1.1` | The final global snappiness pass. 10% is the ceiling. |
| `loudness_min_db` / `loudness_max_db` | `-17.0` / `-13.0` | Accepted mean loudness of the final render (`volumedetect`); QA fails outside this band. |
| `ready_to_post_dir` | `factory/ready-to-post` | Where finished reels are delivered. |

## Scheduling

Once `ready-to-post/` fills up, `scheduler/` turns a topic×audience matrix into
a CSV manifest and pushes it through a scheduling API in waves — capped at 2
posts/day/account, 1 upload/day per YouTube channel, same topic ≥14 days apart,
with an idempotent ledger so re-runs never double-post. See
[`scheduler/README.md`](scheduler/README.md).

## Troubleshooting

- **Start with `npx hyperframes doctor`.** It checks Node, ffmpeg, the headless
  browser, and whisper in one shot; the setup scripts end with it for a reason.
- **`mlx_audio` won't install, or Chatterbox errors on Windows/Linux.** MLX is
  Apple's ML stack and runs only on Apple Silicon Macs. That's expected, not a
  bug: on Windows use Coqui XTTS (Path A) or edge-tts (Path B) via
  `setup/setup-windows.ps1`; on Linux, `setup/setup-linux.sh` does the same.
  `voice_backend: "auto"` picks the right one; the rest of the pipeline is
  identical on every OS.
- **Node is older than 22.** HyperFrames needs >= 22. Mac: `brew upgrade node`.
  Linux: `nvm install 22`. Windows: `winget install OpenJS.NodeJS.LTS`.
- **The voice sounds thin and quiet.** Raw clone output always does — that's
  what `audio_chain.py` fixes. If a line skipped the chain, re-run
  `python3 pipeline/audio_chain.py --project <dir>`.
- **QA fails on loudness.** The final mix's mean must sit in −17..−13 dB. Run
  `python3 pipeline/remix.py --project <dir>` to re-normalize without
  regenerating the voice.
- **Captions vanish on a real phone.** The caption band's top belongs at
  1380 px — 1600 sits under Instagram's UI. Trust the frames `qa.py` extracts
  from the real MP4, never the browser preview.
- **Renders stutter or freeze on source footage.** Re-encode it with dense
  keyframes first: `ffmpeg -i in.mp4 -g 30 -keyint_min 30 out.mp4`.
- **Hinglish/Hindi captions come out mangled.** Set `"lang"` in the project's
  `project.json` to anything other than `en` — the pipeline then skips ASR and
  times captions proportionally from your written text, so spelling stays right.
- **Dashboard says the runner is offline.** Start it (`./factory/start.command`,
  `factory\start.bat`, or `node factory/runner.mjs`). Port 4300 busy?
  `PORT=4301 node factory/runner.mjs`.

## Credit

Built from *Views on Autopilot* by Sanskar Tiwari.
