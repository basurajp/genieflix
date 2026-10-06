# Deeksharambh 2026 thank-you reel (cinematic)

A 30 s, 1080×1920@30 post-event reel for JAIN Online: kinetic type,
an animated Deeksharambh logo, and graphics cut from the student-post scroll
recording. There's no narration. The synthesized score runs at 80 BPM
(beat 0.75 s, bar 3 s), so entrances land on beats and scenes change every
two bars.

| Time | Copy | Motion |
| --- | --- | --- |
| 0–6 | 11,000+ / learners / chose JAIN Online. | the number opens out of an anamorphic flare as an odometer roll, glints, fills with 240 student faces, and the camera flies through its zero |
| 6–12 | Every face. / A different ambition. | a 3D gallery of 72 face tiles (depth-of-field blur, dolly forward), tiles light up teal on "ambition.", then the camera rushes through them into a bloom |
| 12–18 | You chose us / for your education. / That trust / means everything. | clean branded frame: navy, light ribbons drawing on, JAIN Online header; masked word rises, focus-pull on "That trust" |
| 18–24 | Thank you / for making us part of the / future you’re building. | the held message under slow god rays; "Thank you" wipes on like ink |
| 24–30 | the logo, 2026, Your ambition. / Our commitment. | the logo assembles from its own pieces: the bar draws out of the flare, letters drop from it, the glyph wipes in, the swoosh writes itself on a conic mask, the ellipse lands with a bloom and a chime; CDOE and JAIN Online lockups |

The event name only ever appears as the logo. Copy is sentence case.

## Rebuild

`project/` is gitignored because it holds brand assets and student faces.

```bash
D=motion/deeksharambh-2026-cinematic
python3 $D/prep_assets.py --project $D/project --logo deeksharambh-logo.png \
  --jain-online jain-online.png --cdoe jain-cdoe.png --scroll scroll-recording.mp4
python3 $D/make_score.py --out $D/project/assets/audio/score.wav
cp template/assets/gsap.min.js $D/project/assets/
# fonts in $D/project/assets/fonts/: Montserrat-{300,400,500,600,700}.ttf,
# PlayfairDisplay-{400,500,600}i.ttf (Google Fonts, OFL)
python3 $D/compose.py --project $D/project     # refuses copy lines wider than 820 px
npx hyperframes lint $D/project                # 0 errors
npx hyperframes render $D/project --quality high -o $D/project/renders/reel.mp4
```

`tiles.json` lists the 240 framed photos (frame index, column, top edge) found
in the supplied scroll recording. They were picked by tracking each card across
frames and keeping the cleanest view, so a different recording needs a new list.
`prep_assets.py` seeks with `-ss (n - 0.5)/30`, which lands on frame n of
that 30 fps file.

## How the logo animates

`prep_assets.py` labels the logo's alpha into connected components and splits
the wordmark at its shirorekha. That gives 15 pieces that partition the logo
exactly (they recompose it with zero mismatched pixels): the bar, eight letters
with their ascenders, the glyph, the swoosh, the ellipse and three subtitle
words. `logo.json` stores each piece's box and the swoosh's angular span around
a fixed centre. The composer reveals the swoosh with a `conic-gradient` mask
whose angle is a CSS variable tweened by GSAP, which reads as the stroke being
written.

## Notes

- Fonts: Montserrat matches the poster. Playfair Display Italic is an accent on
  the emotional words (chose, ambition, trust, Thank you, future, commitment).
  Swap it out in `compose.py` if it reads off-brand.
- No 1.1× speed-up. That pass exists for narrated reels and would detune the score.
