# Slides

One visual per line: `slide01.png`, `slide02.png`, ... Sorted filename order
maps slide N to line N. Any count >= 1 works — with fewer slides than lines,
the last slide repeats.

- PNG or JPG (WebP also works). Screenshots of the real thing beat stock
  art: prove the claim on screen.
- No animated GIFs — the renderer cannot reproduce them deterministically.
  Use a static image instead, or real footage re-encoded with dense
  keyframes (`-g 30 -keyint_min 30`) so frame seeks never freeze.
- Slides render contained on the dark stage, clear of the caption band and
  the phone UI zones, so any aspect ratio is safe.
