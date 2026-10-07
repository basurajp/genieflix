"""The stomp piece's clock: one beat map that compose.py and make_score.py both import.

112.5 BPM puts a beat at exactly 16 frames at 30 fps, so every stomp, clap and
shutter click lands on a whole frame. 60 beats = 15 bars = 32.0 s.

Groove: stomp, stomp, clap per half bar (beats 0, 0.5, 1 and 2, 2.5, 3).
Face changes are listed per layer as frame numbers; each change is a shutter
click in the score (a burst click when changes are under 4 frames apart).
"""
FPS = 30
BPM = 112.5
BEAT_F = 16                      # frames per beat
BEATS = 60
TOTAL_F = BEATS * BEAT_F         # 960
TOTAL = TOTAL_F / FPS            # 32.0 s
STILL_F = 900                    # 30.0 s: nothing moves after this frame


def fb(b):
    """beat -> frame"""
    return int(round(b * BEAT_F))


def sec(f):
    return f / FPS


# ---------------------------------------------------------------- sections (beats)
SECTIONS = {
    "intro": (0, 4),      # eye-locked face burst, stomps alone
    "a": (4, 10),         # 11,000+ learners chose JAIN Online.
    "b": (10, 18),        # Welcome to the Batch of 2026.
    "c": (18, 28),        # We are proud to nurture 11,000+ ambitions this year.
    "d": (28, 40),        # But even more than that, ... the trust behind each one.
    "e": (40, 52),        # Because every learner ... India.
    "f": (52, 60),        # logo, 2026, Your ambition. Our commitment., JAIN Online
}

# per bar: which groove plays (bars are 4 beats)
BAR_GROOVE = {
    0: "intro", 1: "full", 2: "full", 3: "full", 4: "lean", 5: "build", 6: "full",
    7: "soft", 8: "soft", 9: "rise", 10: "peak", 11: "peak", 12: "peak", 13: "logo", 14: "tail",
}


def groove_hits():
    """(frame, kind) for every stomp and clap."""
    out = []
    for bar, g in BAR_GROOVE.items():
        b0 = bar * 4
        if g == "tail":
            continue
        for half in (0, 2):
            if g == "soft":
                out += [(fb(b0 + half), "stomp_soft")]
                continue
            out += [(fb(b0 + half), "stomp"), (fb(b0 + half + 0.5), "stomp"), (fb(b0 + half + 1), "clap")]
    out.append((fb(56), "clap"))           # the last clap lands the JAIN Online lockup
    return sorted(out)


# ---------------------------------------------------------------- face changes (frames)
def _run(f0, f1, step):
    return list(range(f0, f1, step))


FACES = {
    # intro: one face, eyes locked; changes on the stomps, then bursts
    "hero": [0, 8, 16] + _run(24, 32, 2) + [32, 40, 48] + _run(56, 64, 1),
    # c: the window; eighths, then sixteenths, then a burst racing the counter to 11,000
    "win": _run(288, 320, 8) + _run(320, 352, 4) + _run(352, 368, 2) + _run(368, 384, 1) + [392, 400, 408],
    # c end / d: the grid of 24; burst, then slowing down to stop on one face at "each one."
    "grid": _run(416, 448, 2) + _run(448, 512, 8) + [512, 528, 544, 552],
    # a: every tile in the number changes face at once
    "tiles": [88, 128, 136, 144],
    # b and e: full-bleed bursts before 2026 and behind "every learner"
    "flash": _run(184, 192, 2) + _run(648, 656, 2),
    # e: the faces inside "India." jump on stomp, stomp, clap
    "mosaic": [800, 808, 816],
}
COUNTER = (320, 384)             # the counter races 0 -> 11,000 with the window's burst
EACH_ONE = 560                   # b35: the grid stops; the camera finds one face
BRICKS = [704 + 2 * k for k in range(16)]   # e: face bricks land, two frames apart, b44-b46


def clicks():
    """(frame, kind): kind 'full' for a spaced click, 'burst' inside a fast run, 'soft' in the breakdown."""
    out = []
    for layer, fr in FACES.items():
        for i, f in enumerate(fr):
            gap = min([abs(f - g) for g in fr if g != f] or [99])
            if layer == "grid" and 448 <= f:
                kind = "soft"
            else:
                kind = "burst" if gap < 4 else "full"
            out.append((f, kind))
    out.append((EACH_ONE, "full"))
    return sorted(out)


# ---------------------------------------------------------------- accents (frames)
IMPACTS = [fb(4), fb(12), fb(24), fb(40), fb(48), fb(52)]
RISERS = [(fb(2.5), fb(4)), (fb(20), fb(24)), (fb(36), fb(40)), (fb(50), fb(52))]
SILENCE = (fb(27.75), fb(28))    # a dead sixteenth before the breakdown

# chords per bar (D major: I V vi IV), bar 12 splits G | A into the logo's D
CHORDS = {
    0: "D", 1: "D", 2: "A", 3: "Bm", 4: "G", 5: "A", 6: "D", 7: "Bm", 8: "G", 9: "A",
    10: "D", 11: "A", 12: ("G", "A"), 13: "D", 14: "D",
}
