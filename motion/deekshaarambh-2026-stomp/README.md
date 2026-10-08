# Deekshaarambh 2026 stomp

A 32 s, 1080×1920, 30 fps stomp-style piece on the brand film's locked
script. The cuts land on a stomp, stomp, clap at 112.5 BPM, where a beat is
exactly 16 frames. The picture is built from the learners' own posts, the
original full-resolution files. Every post is the same Deekshaarambh frame
with a photo in its window, so the piece rebuilds that frame once, keeps it
still, and changes only the photos inside it, each cut from its own post with
the eyes kept on one point. Every photo change is a camera shutter in the
score. The scroll recording of the posts plays only inside "2026.".

**Two zones keep the eye still.** The visual zone (y 220–1080) holds the posts,
the number, "2026." and the wall. The text zone is one left-aligned block at one
size (cap tops from y 1150, ending above y 1500, clear of Instagram's caption
area). Words fade up in place on the stomps and claps (7 frames, a 16 px rise)
and every phrase holds for about a second. Nothing slides, slams or shakes.
Behind everything a slow navy aurora drifts with a faint field of posts, and it
goes still at 30 s.

| Beats (s) | Text zone | Visual zone |
| --- | --- | --- |
| 0–4 (0–2.1) | | the post frame standing still; the photo inside changes on each stomp and clap, then bursts |
| 4–10 (2.1–5.3) | 11,000+ / learners chose / JAIN Online. | the camera pulls back and that post's face is one tile of "11,000+": crisp letterforms cut from a lattice of 89 faces, teal plus, sitting directly on its sentence |
| 10–18 (5.3–9.6) | Welcome to the / Batch of | a shutter burst; "20 / 26." with the scroll recording playing inside the letters; a teal flash on the clap |
| 18–28 (9.6–14.9) | We are proud / to nurture · 11,000+ / ambitions / this year. | the photos in the frame change faster, to one every frame, while the counter races to 11,000+; then a wall of 16 posts |
| 28–40 (14.9–21.3) | But even / more than that, · we are proud / to carry · the / trust · behind / each one. | the wall slows under the breakdown, stops, and the camera finds one post |
| 40–52 (21.3–27.7) | Because / every learner · who chooses / JAIN Online · brings us / one step closer · to building / a more skilled, · future-ready / India. | a burst, a drifting mosaic of faces, then the map of India filling with the learners' photos band by band from the south; its outline lands with "India." |
| 52–60 (27.7–32) | (identity) | the authentic artwork revealed by one clean mask; 2026; the tagline; JAIN Online; still from 30.0 s |

`beatmap.py` is the clock both scripts import: the groove, every face change
(and so every shutter click), the counter, the map, the impacts and risers.
To move a cut, change it there and rerun both `compose.py` and `make_score.py`.

## Build

```bash
D=motion/deekshaarambh-2026-stomp
SCROLL=learner-posts-scroll.mp4
POSTS=learner-posts/          # the original post images, one learner per file

# 1. the frame and the photos (once per set of posts). Needs OpenCV, unlike the rest
#    of the repo: a venv with opencv-contrib-python-headless and numpy, plus the YuNet
#    model face_detection_yunet_2023mar.onnx (opencv_zoo). --pick-hold / --pick-hero take
#    a file name to choose the post held on "each one." and the one the number grows from.
venv/bin/python $D/faces_prep.py --project $D/project --images $POSTS \
  --yunet face_detection_yunet_2023mar.onnx [--pick-hold <file>] [--pick-hero <file>]

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

`faces.json` is committed (numbers only: each post's file name, pixel size,
detection score, eye landmarks and where its eyes land in the rebuilt post,
`order`, the distinct sharp faces, `big`, the best-placed of them for the
frame, `hold` and `hero`, and `post_frame`, the window and the eye target). `project/` is gitignored because it holds brand files and
learner faces; the posts themselves stay out of the repo too.

## Notes

- **One frame, many photos.** `faces_prep.py` takes the per-pixel median of
  every post 1254 px or larger: where the posts agree it is the frame (clean,
  1000 px, `assets/img/frame.png`), and where they disagree it is the photo
  window (the sparks, scroll and paper plane that overlap the window stay in
  the frame). Each learner's photo is cut only from their own post's window,
  then scaled and moved toward one eye point and spacing as far as that photo
  allows: the window is always filled and no photo pixel is shown larger than
  1.25 screen pixels, so a close-up stays a close-up. Eyes land within about
  35 px of the point on a typical post, and the frame's longest-held photos
  are the best-placed ones. The wall shows 16 whole posts rebuilt the same
  way. The number, the map and the letter fills use tight face crops so the
  faces read at 22–38 px. A file without the frame is cropped from the whole
  image the same way.
- **The map of India** comes from DataMeet's `india-composite.geojson`
  (github.com/datameet/maps, `Country/`, CC-0): the land area of India in
  accordance with the official boundary of India as per the Survey of India,
  Jammu and Kashmir and Ladakh in full, with the islands. `prep_assets.py`
  downloads it; `compose.py` projects it (equirectangular, x scaled at 22°N),
  simplifies it to 1.2 px and writes `assets/img/india.svg`, which masks a
  lattice of 462 face tiles. Keep this source (or another Survey of India
  conformant one) if the map is ever replaced: a map of India with a different
  external boundary is a legal problem in India.
- **The number reads as a number.** "11,000" is a CSS mask rendered from the
  Montserrat Black outlines (ffmpeg drawtext, the same font file the page
  uses) over a gapless lattice of face tiles; the plus is solid teal type.
- **The scroll recording's captions are removed.** The app prints a caption
  under every post. It is spelled differently from the event name, so
  `prep_assets.py` removes it with a luma-only morphological opening before
  the clip plays inside "2026.". The posts and faces keep their shape.
- **Source resolution.** The original posts are 720–2560 px squares, so the
  860 px frame is mostly a reduction. Posts are kept when the face detector is
  confident (0.8 or more), the head is within 25° of level and the eyes are at
  least 40 px apart; near-duplicates (the same learner posted twice) are
  dropped from the shuffles.
- **Flashing:** the face bursts change the picture up to 30 times a second
  for under a second at a time, which is the point of the style. Platforms
  that screen for photosensitive content may flag it.
- **Sound:** `make_score.py` synthesizes everything, so it is cleared by
  construction: stage stomps and crowd claps over a dhol bhangra chaal, a
  brass section playing the hook as chords with stabs on the claps, a low horn
  line in the breakdown, a held D major brass chord under the identity, tom
  fills, crashes and crowd-cheer swells on the big hits, a sub bass, a string
  pad, risers and the camera shutters. The master is a static gain to
  −13.6 dB mean plus a limiter; the breakdown sits about 5 LU under the peak.
