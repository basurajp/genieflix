# Deekshaarambh 2026 brand film

A 32 s, 1080×1920, 30 fps vertical film built to the Deekshaarambh 2026
creative brief. The film is one continuous world on a solid navy ground, with
one left edge for all type and one recurring motif: the accent plus from
11,000+.

| Time | Copy | Picture |
| --- | --- | --- |
| 0–3.5 | 11,000+ / learners chose / JAIN Online. | the numeral is already on screen at 3.6×; the camera pulls back fast, overshoots a touch and settles (the film's only overshoot); the two lines rise from masks on the numeral's left edge; the plus detaches |
| 3.5–6.5 | Welcome to the / Batch of / 2026. | on the same grid; the plus lands as a registration mark; the first footage frame appears in the counter of the 0 and the camera pushes through it until the counter is the video window |
| 6.5–11 | We are proud / to nurture / 11,000+ / ambitions / this year. | the 3 s learner clip plays once, untouched, 7.0–10.0; the plus completes the second 11,000+; the held last frame opens to full canvas as the type clears |
| 11–18 | But even / more than that, · we are proud / to carry · the / trust / behind each one. | the frame sinks under navy and fades out as the sentence simplifies; "trust" lands firm and still; the plus opens into the line that supports it |
| 18–27.5 | Because / every learner / who chooses / JAIN Online · brings us / one step closer / to building · a more skilled, / future-ready / India. | one rising column, one grid step (760 px) per composition; the line is the baseline each one rises from and ends under "India." |
| 27.5–32 | Deekshaarambh 2026 · Your ambition. / Our commitment. | the column rises into the identity; the line becomes the wordmark's top bar and one mask opens the authentic artwork from it; 2026; tagline in opposing moves; JAIN Online; still from 29.9 s |

## Edit points (all in `config.json`)

- **Copy:** `script` is the locked text. `copy` holds how it is set (line
  breaks and weights). `compose.py` refuses to build if the displayed words
  stop matching `script`.
- **Colours:** `colors.navy`, `colors.text`, `colors.accent`. The accent is the
  artwork's mint because the supplied artwork has no yellow. Set it to a yellow
  if the brand wants the brief's default.
- **Timings:** `timing` holds scene boundaries, the clip window and the four
  sound accents. Choreography inside each scene is written against these.
- **Type:** `type` and `grid` (Montserrat 500/800, margins 88/140/180/320).
- **Media:** `media`. The logo file is the supplied artwork, untouched.
  `logo_show_descriptor: false` hides its "Student Induction Program" row with a
  CSS mask, because that line is not in the locked script.

## Replacing the learner clip

```bash
D=motion/deekshaarambh-2026-film
python3 $D/prep_assets.py --project $D/project --logo deekshaarambh-logo.png \
  --jain-online jain-online.png --footage NEW-CLIP.mp4
```

Set `media.footage_source_start` (0 for a clip that is already 3 s) and
`media.footage_crop` (x, y, w, h in source pixels: keep faces, drop app chrome
and contact details) first. The crop's aspect ratio sets the panel's. A
landscape clip gives a wide panel, so nothing is stretched. Prep writes
`assets/footage/learners.mp4` plus the first and last frames the transitions
use, then you rerun `compose.py`.

## Build

```bash
D=motion/deekshaarambh-2026-film
python3 $D/prep_assets.py --project $D/project --logo deekshaarambh-logo.png \
  --jain-online jain-online.png --footage learners-source.mp4
python3 $D/make_score.py --out $D/project/assets/audio/score.wav
cp template/assets/gsap.min.js $D/project/assets/
python3 $D/compose.py --project $D/project        # also checks the script word for word
npx hyperframes lint $D/project                   # 0 errors
npx hyperframes render $D/project --quality high -o $D/project/renders/film.mp4
# finishing: lay the mastered score onto the picture (the renderer's audio path
# re-levels the mix, so the master WAV goes on directly; same track, same 0 s start)
ffmpeg -i $D/project/renders/film.mp4 -i $D/project/assets/audio/score.wav -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 256k -t 32 -movflags +faststart $D/project/renders/deekshaarambh-2026-master.mp4
```

The master lands at -14.8 dB mean (volumedetect). The renderer's own mix came
out at -16.6 and -18.2 dB on two passes.

`project/` is gitignored because it holds brand files and learner faces.

## Sound

`make_score.py` synthesizes the score, so it is cleared by construction. It
has a confident 120 BPM pulse at the open, space for the trust section and a
controlled lift into the purpose line. There are four sound-design accents
(`timing.accents`) and no others: the numeral resolving, the push through 2026,
"trust" settling, and the final lockup. It has no lyrics and no voice.
