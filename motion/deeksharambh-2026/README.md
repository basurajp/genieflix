# Deeksharambh 2026 recap

A 40 s, 1080×1920@30 post-event reel for JAIN Online's student induction
(03 Oct 2026, 11,500+ new learners). It runs on kinetic type and motion with
no narration. A synthesized 120 BPM bed sets the clock: entrances land on
beats (0.5 s) and scene changes on downbeats (2 s).

| Time | Scene | What moves |
| --- | --- | --- |
| 0–6 | Hook | 11,500+ counter rolls up, ONE DAY. / ONE SCREEN. slam in, the screen outline draws and the camera zooms through it |
| 6–12 | Scale wall | the student-card scroll (3 strips, 2× speed), close-up then a tilted pull-back that bleeds off both edges |
| 12–16 | The event | logo wipe + glint, date and time pills, 5 HOURS. + LIVE badge, whip-pan out |
| 16–24 | Contrast | NO HOSTEL MOVE / TRAIN TICKET / GETTING LOST struck through on the beat, then JUST A LAPTOP + A LINK with the poster on the laptop screen |
| 24–28 | Meaning | दीक्षा (initiation) + आरंभ (beginning) merge into दीक्षारंभ |
| 28–36 | Welcome + CTA | WELCOME TO JAIN ONLINE, 2026 BATCH. over the scroll, then "Tag a classmate you met at Deeksharambh" |
| 36–40 | End card | logo, the poster's line, JAIN Online + CDOE lockups |

## Rebuild

The project folder (`project/`) is gitignored. It holds brand assets and
student faces, so it stays local. Rebuild it from the source files:

```bash
D=motion/deeksharambh-2026
python3 $D/prep_assets.py --project $D/project \
  --logo deeksharambh-logo.png --poster poster.png \
  --jain-online jain-online.png --cdoe jain-cdoe.png --scroll scroll-recording.mp4
python3 $D/make_music.py --out $D/project/assets/audio/music.wav
cp template/assets/gsap.min.js $D/project/assets/
# fonts: Montserrat 400/500/700/800/900 (+800/900 italic) and Noto Sans Devanagari 600/800
# as assets/fonts/<Family>-<weight>[i].ttf (Google Fonts, OFL)
python3 $D/compose.py --project $D/project
npx hyperframes lint $D/project                # 0 errors
npx hyperframes render $D/project --quality high -o $D/project/renders/reel.mp4
```

`prep_assets.py` has crop boxes measured on the supplied files. A different
logo or poster export needs new crops.

## Notes

- No 1.1× speed-up. That pass exists for narrated reels and would detune the music.
- The music is a stdlib synth bed. For reach, post a copy with Instagram's
  in-app trending audio instead. `renders/reel-silent.mp4` is the version for that.
- Renderer lessons from this piece: a `<video>` must not sit inside a timed
  wrapper (the frame extractor ignores the wrapper's offset), so the wall is an
  untimed div whose opacity is set on its window; and `-webkit-text-stroke` on
  big Montserrat glyphs shows the font's overlapping contours, so large type is
  filled, never outlined.
