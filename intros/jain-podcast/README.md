# Jain Podcast intro (12 s, 1920×1080 @ 60 fps)

**Signal → Conversation → Identity.** A single cyan line carries the whole sequence:
a point becomes a waveform, folds into a microphone, the mic's cradle arc closes into a
charcoal pop-filter disc that flies at the lens and sweeps across it, the oversized
title it uncovers recedes into the final lock-up, and the line collapses back to a point
that blooms into a sparkle.

| Time | Phase | Visual | Audio (100 BPM, bar = 2.4 s) |
|---|---|---|---|
| 0.0–2.4 | The signal | point at 0.10 s → line → shaped waveform; charcoal rings on their own depth; slow push-in | soft tonal pulse, Dm9 pad, curious plucks |
| 2.4–4.8 | Transformation | waveform folds (centre first) into a one-stroke mic, which sways ~24° in depth | Bbmaj9, bass + kick enter, riser |
| 4.8–7.2 | Invisible transition | cradle arc closes into a disc, fills charcoal, covers the lens, its trailing rim sweeps left→right revealing oversized Jain / *Podcast* (white while huge) moving the same way; the cyan line shows through letter counters | Gm9, full groove, rounded whoosh panned L→R, motif |
| 7.2–9.6 | Identity resolves | words recede while stacked, *Podcast* turns cyan, both drop into band masks (Jain 8.2 s, Podcast 8.45 s); the line collapses to a point off the end of *Podcast* and blooms into the sparkle on the 8.4 s accent; logo rises through its mask | C9sus, motif answer, title accent at 8.4 s |
| 9.6–12.0 | Finish | static hold, only the sparkle twinkles (pulse on the final downbeat); fade to black 11.5–12.0 s | Fmaj9 signature (C–F–A), rings out, fade 11.3–12.0 s |

## Build

```bash
python3 intros/jain-podcast/music.py                          # original cue -> assets/audio/cue.wav (~8 s)
npx hyperframes lint intros/jain-podcast                      # 0 errors
npx hyperframes render intros/jain-podcast --fps 60 --quality delivery \
  -o intros/jain-podcast/renders/jain-podcast-intro.mp4       # ~1.5 min, H.264 + AAC
```

Preview with controls outside the canvas: `python3 -m http.server 8080 --directory intros/jain-podcast`,
then open `http://localhost:8080/preview.html` (play, replay, frame scrub, synced audio).
`npx hyperframes preview intros/jain-podcast` also works.

## Editing

- **Palette, timing, logo, title size**: the `CONFIG` block at the top of the script in `index.html`.
  Every frame is `draw(t)`, a pure function of time, so any change previews and renders identically.
- **Logo**: `assets/logo/jain-online-logo.svg` is the official JAIN Online dark-background lock-up
  (447×73). To swap it, replace the file and set `CONFIG.logo.aspect` (width ÷ height). It is drawn
  with `preserveAspectRatio="meet"`, so a wrong ratio letterboxes and never distorts.
- **Music**: `music.py` (stdlib only, fixed seed, so it's reproducible). Kick times are mirrored in
  `CONFIG.kicks` so the waveform breathes with the track; keep them in sync if you change drums.
- Type: "Jain" in Inter Medium 150px (-2px tracking), "Podcast" in Playfair Display SemiBold
  Italic 168px, cyan with a soft glow. Both OFL, vendored in `assets/fonts/`.
- Sparkle: `CONFIG.spark` (ray angles/lengths and offset from the end of "Podcast").
