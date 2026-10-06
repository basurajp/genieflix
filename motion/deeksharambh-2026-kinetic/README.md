# Deeksharambh 2026 kinetic reel

A 28 s, 1080×1920@30 thank-you reel for JAIN Online, cut like a modern
Instagram motion piece. Type stomps in on the beat, scenes change every bar,
and there are shakes, RGB splits, colour flips and whip pans. The 120 BPM
track is synthesized (trap drums, a bhangra dhol groove, 808 bass and a
plucked hook), so every entrance sits on a beat (0.5 s) or an eighth (0.25 s).

| Time | Copy | Motion |
| --- | --- | --- |
| 0–4 | 11,000+ / learners / chose / JAIN Online. | a wall of faces flickers every two frames while the counter races; lock at 1.0 s with flash, shockwave, RGB split, shake; one word per beat; the number fills with faces and the camera dives through its zero |
| 4–10 | Every / face. / A different / ambition. | drop into tilted face columns scrolling in opposite directions; face. is filled with faces that cycle inside the letters; ambition. slams with an underline; pull-back to a full-frame wall of faces |
| 10–16 | You / chose us / for your education. / That / trust / means / everything. | slice wipe into the branded frame; circle wipe to teal for That trust; everything. cascades and echoes, whip pan out |
| 16–22 | Thank you / for making us / part of the / future / you’re building. | whip in, Thank you echoes and collapses, future punches in with a glow; the message folds into a line of light, then a beat of silence |
| 22–28 | the logo, 2026, Your ambition. / Our commitment. | the drop: bar slash, letters stomp, glyph wipe, swoosh write-on, the ellipse lands with a shockwave and sparks; block wipes for the tagline; CDOE and JAIN Online lockups |

The event name only ever appears as the logo. Copy is sentence case.

## Rebuild

`project/` is gitignored because it holds brand assets and student faces.

```bash
D=motion/deeksharambh-2026-kinetic
python3 $D/prep_assets.py --project $D/project --logo deeksharambh-logo.png \
  --jain-online jain-online.png --cdoe jain-cdoe.png --scroll scroll-recording.mp4
python3 $D/make_score.py --out $D/project/assets/audio/score.wav
cp template/assets/gsap.min.js $D/project/assets/
# fonts in $D/project/assets/fonts/: Montserrat-{500,600,700,800,900}.ttf,
# PlayfairDisplay-{500,600}i.ttf (Google Fonts, OFL)
python3 $D/compose.py --project $D/project     # refuses copy wider than the 100-960 px column
npx hyperframes lint $D/project                # 0 errors
npx hyperframes render $D/project --quality high -o $D/project/renders/reel.mp4
```

`prep_assets.py` runs the cinematic piece's prep (logo pieces, face tiles,
mosaic) and adds five tall face columns on top.

## Notes

- Shake offsets are a fixed list in `compose.py`. Never use `Math.random`:
  render workers build the timeline independently and must agree frame to frame.
- The face flicker and the faces inside "face." are stepped tweens
  (`ease: "steps(n)"`) on a strip or background position, with no image swaps.
- No 1.1× speed-up, because it would detune the track.
