# The Playbook

The machine renders. It doesn't write, and it doesn't judge. These are the rules
that do — distilled from *Views on Autopilot* by Sanskar Tiwari, each one paid
for with real posts and real skip rates. The pipeline enforces most of them in
code; this file is why the numbers are what they are.

## 1. The five lines

Five lines, five beats, roughly twenty-eight seconds — long enough to make one
point completely, short enough that a viewer finishes it. Every project's
`lines.txt` is this skeleton:

1. **Hook** — the promise, the number, the wildest true thing you can say, on
   screen by the first fifth of a second. Not a greeting, not a logo, not "hey
   guys." *"I made this entire deck in sixty seconds. I typed one line, that's it."*
2. **Action** — what you actually did, plainly, no adjectives yet.
   *"Wrote the topic, hit generate, and the tool built the whole thing."*
3. **Proof** — the specifics that make it believable. Concrete nouns, not praise.
   *"Every slide has real images, clean layout, proper headings. All automatic."*
4. **Contrast** — the pain you're deleting; the viewer feels their own problem
   being named. *"No Canva. No PowerPoint. No formatting headache."*
5. **CTA** — one clear next step. *"Your first deck is free. Link in bio."* Or:
   *"Comment the word LINK and I'll send you the full guide."*

Hook → action → proof → contrast → CTA mirrors how a skeptical stranger
processes a claim: what? → how? → really? → instead of what I do now? → okay,
what do I do?

**Writing rules:**

- **Lead with the payoff, never a story.** "So last week I was struggling
  with…" costs fifteen seconds you don't have. Open on the hard claim; prove it
  after. Preload the wildest moment into frame one.
- **One idea per line.** Each line carries exactly one idea, and the visual on
  screen matches the word being spoken.
- **The mute test.** If a stranger muted the audio, could they still follow the
  video from captions and visuals alone? If not, it's not tight enough.
- **The twelve-year-old test.** If a kid can't tell you what happened in the
  first ten seconds, the market can't either. Simplicity is the cost of being
  understood by someone barely paying attention.
- **Show, don't adjective.** "All-in-one platform" is ad language, and ads get
  skipped. A screenshot of the thing actually working means everything. Build
  each line around its aha beat — the two seconds where the viewer thinks "oh,
  that's insane." No aha? Cut the line or rewrite it until it has one.
- **Write the way you talk.** The clone speaks whatever you type; corporate
  copy in a cloned voice still sounds like an ad. For a Hinglish audience,
  write casual Hinglish — "ai se ppt kaise banaye aj sikhte hai" — not
  translated corporate English.

## 2. The only metric: skip rate

Views are a result. **Skip rate** — the percentage gone within the first three
seconds — is the input that produces them. Read it 24 hours after posting:

| Skip rate | Verdict |
| --- | --- |
| under 18% | Viral-grade. Almost always gets pushed wider. The target for every opening. |
| under 30% | Good. Healthy. The open is working. |
| 40–50% | Weak. Half your viewers bailed before the point. The hook is the problem. |
| over 50% | Cooked. Kill that opening **format** entirely. Don't tweak it. Retire it. |

You're grading **formats, not videos**. One good video inside a dead format is
luck; a format that keeps landing is a machine. When a format keeps coming in
over 50%, no amount of polish saves it.

## 3. What stops the thumb

Measured, not guessed: polished studio talking-heads (good mic, clean
background) skipped at **75–80%** — cooked. A rough street demo with genuinely
bad audio skipped around **30%** and pulled roughly **five times** the views.
Concept beats polish, and it isn't close.

Cold strangers stop for:

- **Spectacle** — a real-world setting, a second person reacting, technology
  visibly doing something that shouldn't be possible.
- **Money numbers** — a real ₹ or $ figure: a bill, a price, revenue. Concrete,
  specific, ideally large.

They do **not** stop for product names, feature lists, or your milestones. "We
launched X" and "I hit 10k followers" matter to you; a stranger smells it
instantly. And **polish reads as an ad** — color grade, perfect mic, logo sting
— and people have been trained to flick past ads in well under three seconds.
Don't clean the life out of a video.

**Hook formulas that tested well:**

1. **Curiosity / news framing.** A headline, not an ad — a "the model the US
   government banned"–style hook pulled 594 views on a channel with 70
   followers, because it reads as news you might be missing, not a pitch.
2. **Speed / result.** The finished outcome and how fast: "full deck in 60
   seconds." Payoff first, method second.
3. **Pain.** Name the thing they hate out loud: "stop building slides by hand."
   A problem they feel beats a feature they don't.

## 4. Retention mechanics

These are baked into the composition builder; know them anyway:

- **Title on screen by 0.2 s** — bold kicker + title chip at frame one. It can
  fade later when other graphics need the room.
- **Hook in the first second** — the biggest number or claim, motion plus
  magnitude.
- **Slow push-in on the opening shot** — scale 1.1 → 1.0. Motion from moment
  zero tells the eye something is happening.
- **A visual state change every 2–3 seconds, the whole video.** No static
  stretch over three seconds, ever — a pulse, a stamp, a swapped chip.
  Stillness is a cue to scroll; never give it.
- **Sync every entrance to the exact spoken word.** That's what the word-level
  timestamps are for. On the syllable feels composed; drifting feels sloppy
  even when the viewer can't say why.
- **Cut everything that doesn't earn its seconds.** Cut at sentence boundaries,
  then re-transcribe so the timing stays honest.
- **End on a CTA stamp**, one clear ask, held on screen.
- **Speed the final cut up 10%** (`setpts=PTS/1.1` + `atempo=1.1`, applied
  after render and loudness QA). Ten percent is the ceiling — at 15–20% the
  information gets hard to follow.

## 5. Sound

The audience never notices good audio; they only notice bad audio. Raw clone
output is quiet and thin — ~10 dB too soft, no presence. The chain (applied by
`audio_chain.py`, in this exact order, into mono 24 kHz WAV):

```
highpass=f=80              cut the rumble — nothing below 80 Hz is your voice
afftdn=nr=12:nf=-32        denoise gently; more and the voice goes underwater
acompressor=threshold=-22dB:ratio=3:attack=8:release=180:makeup=6
                           radio-voice consistency: catch consonants in 8 ms,
                           release naturally over 180 ms, +6 dB makeup
loudnorm=I=-14:TP=-1.0:LRA=7
                           hot and forward — on a phone speaker, quiet loses
```

- **Measure, don't hope.** `volumedetect` on every final render; the mean must
  sit in **−17..−13 dB** or QA fails. Your ears lie, especially at night after
  hearing a line forty times.
- **Music is felt, not heard.** Local files only — never a mid-render fetch.
  Effective level around **−33..−30 dB** (target −31); the multiplier is
  `10^((target − track_mean_dB) / 20)`, clamped to at most 1.0. When in doubt,
  quieter — music that competes with the voice makes both lose.
- **SFX are seasoning, not the meal.** One soft effect per visual beat,
  maximum, at ~0.22 volume. **Never stack them** — layered UI ticks become a
  nervous "khic khic khic" that makes a good video feel cheap. One clean effect
  on the beat that matters; silence everywhere else. Restraint reads as
  expensive.

## 6. Captions and the safe zone

Most reels are watched on mute; captions are the primary channel. On the
1080×1920 canvas:

- Keep everything out of the **bottom 420 px** (Instagram's UI), the **top
  220 px**, and the **right 120 px** (action buttons).
- The caption band's top sits at **1380 px** — low enough to feel like a
  caption, high enough to clear the UI. **Never 1600**: at 1600 the app covers
  half your words on a real phone, and the desktop preview will never show you.
- **Word groups of at most 4 words**, breaking at punctuation and natural
  pauses — not walls of text. Style: ~85%-opaque black rounded chip, white bold
  text, centered.
- **Two timing modes.** English: real per-word Whisper timestamps. Hinglish /
  any non-English (`lang` ≠ `en` in `project.json`): skip ASR entirely and time
  proportionally — split the written line into groups and give each a slice of
  the line's audio duration by character length. Clean text, correct timing, no
  ASR spelling errors.
- **Fix the machine's hearing.** ASR fumbles brand and product names. The
  corrections dictionary (`pipeline/corrections.json`) rewrites the transcript
  before captioning, keeping timestamps intact. A caption that misspells your
  own product is worse than no caption.

## 7. The six gotchas

Each of these cost a wasted render once. The renderer is stricter and more
literal than the preview; when they disagree, the renderer wins — build for the
renderer.

1. **Don't animate a `<video>`'s size or clip-path.** The renderer ignores
   `clip-path` and width/height tweens on video (the preview honors them — the
   trap). Opacity and transforms (scale, translate) work. For
   picture-in-picture or reframes, use multiple static video clips and
   cross-fade opacity at the seams.
2. **Untimed overlays sink beneath the video.** Anything above a video must be
   a proper timed clip — start, duration, and a higher track index. Nothing
   floats; everything is placed.
3. **Re-encode source footage with dense keyframes** (`-g 30 -keyint_min 30`)
   before use, or arbitrary seeks freeze on stale frames. Silent and maddening.
4. **Fades ending exactly on a clip boundary need a hard stop** — an explicit
   set-opacity-to-zero at the boundary, in addition to the tween, or the last
   frame can flicker at full opacity.
5. **Speed changes happen before transcription**, or every timestamp is wrong.
   The one exception is the final global 10% pass, applied last precisely
   because nothing depends on the timings anymore.
6. **No animated GIFs.** Their rendering isn't reliably deterministic. Static
   image or a real video clip. Determinism is the whole game.

## 8. The QA loop

Run on every video, no exceptions (`qa.py` automates it):

1. **Lint and validate** before rendering. Zero errors first — a composition
   that doesn't validate is a render you're going to waste.
2. **Snapshot the key beats** — hook, mid-point, CTA — and actually read the
   PNGs. Clipped text? Caption in the safe zone?
3. **Render, then extract frames from the real MP4 and read those.** The
   snapshot honors CSS the renderer doesn't; the output is the truth. If you
   keep one habit from the whole book, keep this one: **verify the render, not
   the preview.**
4. **Measure loudness** on the finished file. Mean in −17..−13 dB or fix it
   before shipping.
5. **Deliver deliberately** — one known folder (`ready-to-post/`), a
   descriptive filename, one final play-through to confirm the file is the one
   you think it is.

The dangerous failure mode is *plausible-but-wrong* — a caption 200 px too low,
a PiP that jumps, a voice 4 dB quiet. It sails past a casual glance. Automate
the making; never fully automate the judging.

## 9. Factory rules

- **Folders are the state machine**: `building/ → queue/ → work/ → done/` or
  `failed/`, outputs to `output/` and `ready-to-post/`. Everything is
  debuggable with a file manager; a failed job re-runs by moving it back to
  `queue/` (or the dashboard's Retry button).
- **One writer, no fights.** The creator owns `job.json` while the project is
  in `building/`; the runner owns it from `queue/` on. Clean handoff, no two
  processes editing the same state, no mystery corruption.
- **Three renders at once, voice one at a time** — what a laptop realistically
  sustains; the local voice model wants the machine to itself. A hundred queued
  videos drain in about two hours, unattended.
- **Capture is instant, building is async.** The moment an idea exists, it gets
  a `building/<slug>/` folder with a `BRIEF.md` — it shows on the dashboard
  immediately, and nothing is lost to "I'll do it later."
- **The plan is sacred; the generated files are disposable.** `lines.txt`,
  `project.json`, `BRIEF.md`, slides survive; `index.html` and audio are
  regenerated from them and hand-edits get wiped. Custom elements go in the
  template, not the output. And the scripts **back up before they overwrite**
  (`raw.bak/`, `audio.bak/`) — a bad regeneration is never a lost one.

## 10. Scheduling guardrails

Volume without limits reads as spam, to platforms and to people. Baked into the
manifest generator:

- **Max 2 posts per day per account.**
- **Max 1 upload per day per YouTube channel.**
- **Same topic at least 14 days apart** across variants — nobody sees a rerun.
- **Fixed local time slots per platform**, morning and evening.
- **Protect your followers from your factory.** Factory videos are coverage for
  strangers, not treats for followers: on Instagram push them as trial reels
  (shown only to non-followers; winners graduate to the grid); on YouTube, a
  dedicated tutorials channel, not the main one.
- **Push in waves**: schedule the first 7 days, read the numbers, push the rest
  with adjustments. If wave one stinks, exposure was a week of trial reels.
- **Idempotent ledger.** Every created post gets a ledger line; re-runs skip
  anything already there, upload each video once, and just fill in what failed.
  Boring, resumable, idempotent — any batch script that touches the network
  needs this.
- **Post where the data says.** Testing a platform is cheap; dropping one is a
  column in the matrix. Spray, measure, prune.

## 11. Two lanes, and the economics

Talking-head reels with a real face out-pull pure-generated ones by roughly
**two to one**. So the factory isn't a replacement for showing up — it's the
coverage lane:

- **Lane 1 — the factory.** Always-on, ₹0 per video, ~20-second renders. Covers
  every competitor, feature, and use-case a customer might search for. It keeps
  the account alive, catches search intent, and compounds — a hundred quiet
  videos working at once is a distribution engine.
- **Lane 2 — the hero swings.** Your actual face, doing something real. Fewer,
  bigger. The factory is the floor that lets showing up be the ceiling.

The economics only work because each video is free: make ten, post the two that
test under an 18% skip rate, bin the rest without flinching. You're not buying
views — you're buying **rate of learning**. Drive topics with a matrix (topics
with proven demand × audiences: a 5×5 grid is twenty-five videos before a
second thought), let skip rate settle every argument, and retire what's cooked.

The tools are the easy part. The taste — writing hooks that stop a thumb,
reading a skip rate honestly, killing a format you're fond of — is the work.
Now go render something.
