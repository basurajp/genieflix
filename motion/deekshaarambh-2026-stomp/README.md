# Deekshaarambh 2026 stomp

A 32 s, 1080×1920, 30 fps stomp-style piece on the brand film's locked
script. Every cut lands on a stomp, stomp, clap at 112.5 BPM, where a beat
is exactly 16 frames. The picture is built from the learners' own posts.
Each post is detected, super-resolved and turned so the eyes sit on one
line. Every face change is a camera shutter in the score.

| Beats (s) | Copy | Picture |
| --- | --- | --- |
| 0–4 (0–2.1) | | one post, eyes locked in a viewfinder, changes on each stomp and clap, then bursts |
| 4–10 (2.1–5.3) | 11,000+ / learners chose / JAIN Online. | the camera pulls back 25× and that face is one tile of "11, / 000" built from 300 face tiles; the plus lands teal; all tiles change face on the hits |
| 10–18 (5.3–9.6) | Welcome / to the / Batch of / 2026. | colour flips on stomp, stomp, clap; a shutter burst; "20 / 26." stamped out of navy with the scroll recording playing inside the letters; the letters grow on each hit and flash teal on the clap |
| 18–28 (9.6–14.9) | We are / proud / to nurture / 11,000+ / ambitions / this year. | a full-width eye-locked window; the shutter speeds up from eighths to every frame while the counter races to 11,000+; the window splits into a wall of 28 posts |
| 28–40 (14.9–21.3) | But even / more than that, / we are proud / to carry / the trust / behind / each one. | the wall slows under the breakdown; "trust" is filled with faces; the wall stops and the camera finds one post |
| 40–52 (21.3–27.7) | Because / every learner / who chooses / JAIN Online / brings us / one step / closer / to building / a more skilled, / future-ready / India. | the peak: a new screen on every hit; posts stack like bricks; "India." filled with faces |
| 52–60 (27.7–32) | Deekshaarambh 2026 / Your ambition. / Our commitment. | the authentic artwork revealed by one clean mask; 2026; the tagline; JAIN Online; nothing moves after 30.0 s |

`beatmap.py` is the clock both scripts import: the groove, every face change
(and so every shutter click), the counter, the bricks, the impacts and risers.
To move a cut, change it there and rerun both `compose.py` and `make_score.py`.

## Build

```bash
D=motion/deekshaarambh-2026-stomp
SCROLL=learner-posts-scroll.mp4

# 1. faces (once per recording). Needs OpenCV, unlike the rest of the repo:
#    a venv with opencv-contrib-python-headless and numpy, plus two models:
#    YuNet face_detection_yunet_2023mar.onnx (opencv_zoo) and EDSR_x4.pb (Saafke/EDSR_Tensorflow).
#    --candidates is a JSON list of [frame, column, top] squares to try (the
#    cinematic piece's tile finder makes one); omit it to reuse faces.json.
venv/bin/python $D/faces_prep.py --project $D/project --scroll $SCROLL \
  --yunet face_detection_yunet_2023mar.onnx --edsr EDSR_x4.pb [--candidates tiles.json --count 160]

# 2. brand, the scroll clip, fonts, grain, gsap (stdlib + ffmpeg)
python3 $D/prep_assets.py --project $D/project --scroll $SCROLL \
  --brand-dir motion/deekshaarambh-2026-film/project/assets/brand
#   (or --logo <supplied logo file> --jain-online <supplied lockup>, cropped and keyed as the film does)

# 3. score, composition, checks, render
python3 $D/make_score.py --out $D/project/assets/audio/score.wav
python3 $D/compose.py --project $D/project        # also checks the script word for word
npx hyperframes lint $D/project                   # 0 errors
npx hyperframes render $D/project --quality high -o $D/project/renders/stomp.mp4
# finishing: the renderer re-levels audio, so the mastered score goes on directly
ffmpeg -i $D/project/renders/stomp.mp4 -i $D/project/assets/audio/score.wav -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 256k -t 32 -movflags +faststart $D/project/renders/deekshaarambh-2026-stomp.mp4
```

`faces.json` is committed (numbers only: which squares of the recording hold
a face, the landmarks, a blockiness score, and two lists: `order`, the
distinct sharp faces, and `big`, the ones with the cleanest source pixels for
the full-width windows). `project/` is gitignored because it holds brand
files and learner faces.

## Notes

- **The posts keep their frames.** The large windows and the wall show each
  learner's whole post (the branded frame and the photo), turned and scaled
  so the eyes land on the same line. The number tiles and the letter fills
  use tight face crops so the faces read at 22 px.
- **The scroll recording's captions are removed.** The app prints a caption
  under every post. It is spelled differently from the event name, so
  `prep_assets.py` removes it with a luma-only morphological opening before
  the clip plays inside "2026.". The posts and faces keep their shape.
- **Source resolution** is the limit: faces in the recording are about 116 px
  posts with eyes 20–35 px apart. EDSR ×4 plus the alignment holds up at the
  sizes used here. The fastest shuffles use the softer faces, and the holds
  use the cleanest ones.
- **Flashing:** the face bursts change the picture up to 30 times a second
  for under a second at a time, which is the point of the style. Platforms
  that screen for photosensitive content may flag it.
- **Sound:** `make_score.py` synthesizes everything (stage stomps, crowd
  claps, a two-curtain camera shutter, piano hook, pluck, sub, pad, risers,
  bells), so it is cleared by construction. The master is a static gain to
  −13.6 dB mean plus a limiter. The breakdown sits about 4 LU under the peak.
