# Decode — reverse-engineer a reference reel

```bash
python3 decode/decode_reel.py decode/inbox/ref.mp4            # -> decode/refs/ref/
python3 decode/decode_reel.py decode/inbox/*.mp4               # a batch, one folder each
python3 decode/decode_reel.py ref.mp4 --threshold 0.3          # fewer false cuts on shaky handheld
```

Stdlib Python + ffmpeg, well under a minute for a 30 s reel on a laptop. It measures what an editor
measures by scrubbing, and lays the reel out on sheets so a person (or Claude)
can name the rest with `styles/LEXICON.md`.

| Output | What it answers |
|---|---|
| `REPORT.md` | Measured half: shots, ASL / median, cuts per 10 s, every boundary typed, flash frames, motion energy and the longest static stretch, brightness / contrast / saturation / black and white points, shadow and highlight tint, palettes, look hints mapped to grades, loudness (LUFS and our volumedetect gate), tempo, cuts-on-onset vs chance. Decoded half: prompts per craft area. |
| `decode.json` | The same, machine-readable. |
| `hook.jpg` | First 3 s at 10 fps — the skip-rate window. |
| `contact.jpg` | One labelled frame per shot. |
| `timeline-NN.jpg` | The whole reel at 4 fps, 6 s per sheet — read type animation and camera moves here. |
| `cuts/cut-NN.jpg` | Three frames either side of each boundary — name the transition here. |
| `shots/shot-NN.jpg` | A large frame per shot — identify typefaces and layout. |

Boundary types the decoder tells apart: hard cut, punch-in / punch-out (the
next frame is the previous one rescaled — the creator jump-zoom), jump cut
(same set-up, subject moved), flash cut (1–3 white frames), black-frame
insert, dissolve (middle frame is a blend of its ends), dip to black / white,
colour wipe (passes through a flat colour frame), and "whip / push / zoom /
camera move" (a soft change that is none of the above — the strip says which).
It was checked against a synthetic reel with one of each planted, and against
renders of the templates in `styles/`, where it reads each template's grammar
back: swiss-editorial → 4 colour wipes, kinetic-punch → 8 alternating
punch-in/out cuts + 4 scene cuts, cine-doc → 3 dissolves + a dip to black,
neo-brutal → 3 of its 4 card pushes as transitions and the fourth (between two
black-and-white cards, so no colour shift) listed for review.

What it does not do: read text (no OCR — the sheets are for that), separate
music from voice (onsets include syllables, hence the chance ratio), identify
fonts or name the art direction. Those are judgement calls made from the sheets.

Media in `inbox/` and the sheets under `refs/` are gitignored; `REPORT.md` and
`decode.json` are small and worth committing as the record of what was learned.

## Getting reels here

Instagram and YouTube links do not download from the cloud container this repo
is usually worked on in (its network policy blocks those hosts). Either save
the reel as a file (the app's download, or a screen recording) and put it in
`decode/inbox/` on your machine, or share the files through Google Drive.
