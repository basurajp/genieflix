#!/usr/bin/env python3
"""Synthesize the kinetic Deeksharambh 2026 track: 120 BPM, 14 bars, 28 s, D minor.

Usage: motion/deeksharambh-2026-kinetic/make_score.py --out <dir>/score.wav

Trap drums under a bhangra dhol chaal (synthesized dha/ta), an 808 that follows
the roots, a Karplus-Strong pluck hook with a jawari-style buzz, chord stabs on
every stomp, impacts on the section hits, a counter-tick roll for the opening
race, a snare-roll build and a dead-silent beat before the logo drop.
Stdlib synthesis, mixed with ffmpeg (short hall via afir). Deterministic.

Hit map it is written against (s): 1.0 number lock, 4.0 drop, 4.5/5.0 Every
face, 6.5 ambition, 8.0 face wall, 10.0 slice wipe, 12.0/12.5 trust, 14.0/14.5
means everything, 16.0 Thank you, 18.5 future, 21.75 silence, 22.0 logo drop,
23.0 ellipse, 24.0 2026, 26.0 last hit.
"""
import argparse
import math
import pathlib
import random
import subprocess
import tempfile
import wave
from array import array

SR = 44100
BPM = 120
BEAT = 60 / BPM
BAR = 4 * BEAT
STEP = BAR / 16
BARS = 14
TOTAL = BARS * BAR
N = int((TOTAL + 1.5) * SR)
TAU = 2 * math.pi
rng = random.Random(1103)
midi = lambda m: 440.0 * 2 ** ((m - 69) / 12)

DM, BB, F, C = (50, 53, 57, 62), (46, 50, 53, 58), (53, 57, 60, 65), (48, 52, 55, 60)
CHORDS = [DM, BB, DM, BB, F, C, DM, BB, F, C, BB, DM, BB, F]
ROOTS = [38, 34, 38, 34, 41, 36, 38, 34, 41, 36, 34, 38, 34, 41]

# per-bar arrangement
SEC = {}
for b in range(BARS):
    if b == 0:
        s = dict(kick=None, clap=False, hats=0, dhol=False, bass=0.0, pluck=False, pad=0.5)
    elif b == 1:
        s = dict(kick="trap", clap=True, hats=16, dhol=False, bass=0.7, pluck=False, pad=0.6)
    elif b in (2, 3, 4):
        s = dict(kick="trap", clap=True, hats=16, dhol=True, bass=1.0, pluck=True, pad=0.5)
    elif b in (5, 6, 7):
        s = dict(kick="four", clap=True, hats=16, dhol=True, bass=0.9, pluck=False, pad=0.55)
    elif b in (8, 9):
        s = dict(kick="half", clap=False, hats=8, dhol=False, bass=0.45, pluck=True, pad=0.9)
    elif b == 10:
        s = dict(kick="four", clap=False, hats=16, dhol=False, bass=0.6, pluck=False, pad=0.8)
    elif b in (11, 12):
        s = dict(kick="trap", clap=True, hats=16, dhol=True, bass=1.0, pluck=True, pad=0.6)
    else:
        s = dict(kick=None, clap=False, hats=0, dhol=False, bass=0.0, pluck=False, pad=1.0)
    SEC[b] = s
KICKS = {"trap": (0, 6, 8, 11), "four": (0, 4, 8, 12), "half": (0, 10)}
SILENCE = (21.75, 22.0)


def buf():
    return array("d", bytes(8 * N))


def place(dst, shot, t, gain=1.0):
    if SILENCE[0] <= t < SILENCE[1]:
        return
    i0 = int(t * SR)
    n = min(len(shot), N - i0)
    for k in range(n):
        dst[i0 + k] += shot[k] * gain


# ---------- one-shots ----------
def kick():
    out, ph = array("d"), 0.0
    for k in range(int(0.45 * SR)):
        t = k / SR
        ph += (50 + 130 * math.exp(-t * 32)) / SR
        out.append(math.tanh(2.0 * math.sin(TAU * ph)) * math.exp(-t * 7) + (rng.random() * 2 - 1) * 0.4 * math.exp(-t * 500))
    return out


def clap():
    out, lp = array("d"), 0.0
    for k in range(int(0.32 * SR)):
        t = k / SR
        burst = sum(math.exp(-(t - d) * 95) for d in (0.0, 0.010, 0.021) if t >= d)
        n = rng.random() * 2 - 1
        hp = n - lp
        lp += 0.3 * (n - lp)
        out.append(hp * (0.55 * burst + 0.55 * math.exp(-t * 14)))
    return out


def hat(decay=85):
    out, prev = array("d"), 0.0
    for k in range(int(0.1 * SR)):
        n = rng.random() * 2 - 1
        out.append((n - prev) * math.exp(-k / SR * decay))
        prev = n
    return out


def dha():
    """dhol bass side: a boomy skin with a falling pitch and a palm thump."""
    out, ph, lp = array("d"), 0.0, 0.0
    for k in range(int(0.5 * SR)):
        t = k / SR
        ph += (62 + 46 * math.exp(-t * 18)) / SR
        lp += 0.05 * ((rng.random() * 2 - 1) - lp)
        out.append(math.tanh(1.6 * math.sin(TAU * ph)) * math.exp(-t * 6.5) + lp * 2.2 * math.exp(-t * 40))
    return out


def ta():
    """dhol treble side: the cane's crack — band-passed noise with a short ring."""
    out, low, band = array("d"), 0.0, 0.0
    f = 2 * math.sin(math.pi * 2300 / SR)
    for k in range(int(0.12 * SR)):
        t = k / SR
        low += f * band
        high = (rng.random() * 2 - 1) - low - 0.35 * band
        band += f * high
        ring = 0.5 * math.sin(TAU * 430 * t) * math.exp(-t * 55) + 0.3 * math.sin(TAU * 960 * t) * math.exp(-t * 70)
        out.append(band * 0.9 * math.exp(-t * 38) + ring)
    return out


def bass808(f, dur):
    out, ph = array("d"), 0.0
    for k in range(int(dur * SR)):
        t = k / SR
        ph += f * (1 + 0.6 * math.exp(-t * 30)) / SR
        e = min(1.0, t * 400) * math.exp(-t * 1.6) * min(1.0, (dur - t) * 30)
        out.append(math.tanh(1.8 * math.sin(TAU * ph)) * e)
    return out


def pluck(f, dur=0.8):
    """Karplus-Strong with a soft-clipped tap: a bright, buzzy string."""
    n = max(2, int(round(SR / f)))
    line = [rng.uniform(-1, 1) for _ in range(n)]
    out, i = array("d"), 0
    for k in range(int(dur * SR)):
        a, b = line[i], line[(i + 1) % n]
        line[i] = 0.5 * (a + b) * 0.9965
        i = (i + 1) % n
        t = k / SR
        out.append((math.tanh(2.4 * a) * 0.55 + 0.45 * a) * min(1.0, (dur - t) * 40))
    return out


def stab(chord, dur=0.5):
    out = array("d")
    fs = [midi(m + 12) for m in chord] + [midi(chord[0])]
    phs = [rng.random() for _ in fs]
    lp = 0.0
    for k in range(int(dur * SR)):
        t = k / SR
        s = 0.0
        for j, f in enumerate(fs):
            phs[j] = (phs[j] + f / SR) % 1.0
            s += 2 * phs[j] - 1
        cut = 0.06 + 0.4 * math.exp(-t * 12)
        lp += cut * (s / len(fs) - lp)
        out.append(lp * math.exp(-t * 6) * min(1.0, t * 800))
    return out


def impact(dur=2.0):
    out, ph, lp = array("d"), 0.0, 0.0
    for k in range(int(dur * SR)):
        t = k / SR
        ph += (34 + 70 * math.exp(-t * 7)) / SR
        lp += 0.035 * ((rng.random() * 2 - 1) - lp)
        out.append(math.sin(TAU * ph) * math.exp(-t * 2.4) + lp * 2.6 * math.exp(-t * 3.2))
    return out


def sweep(dur, up=True):
    out, low, band = array("d"), 0.0, 0.0
    n = int(dur * SR)
    for k in range(n):
        x = k / n
        fc = 300 + 7500 * (x ** 2 if up else (1 - x) ** 1.4)
        f = 2 * math.sin(math.pi * fc / SR)
        low += f * band
        high = (rng.random() * 2 - 1) - low - 0.45 * band
        band += f * high
        env = x ** 1.6 if up else math.sin(math.pi * min(1.0, x * 1.5)) ** 2
        tone = 0.3 * math.sin(TAU * (180 + 700 * x * x) * k / SR) * x if up else 0.0
        out.append((band * 0.85 + tone) * env)
    return out


def chime(f, dur=2.2):
    out = array("d")
    for k in range(int(dur * SR)):
        t = k / SR
        s = math.sin(TAU * f * t + 1.6 * math.exp(-t * 6) * math.sin(TAU * 3.5 * f * t))
        out.append(s * math.exp(-t * 2.4) * min(1.0, t * 600))
    return out


def tick():
    out = array("d")
    for k in range(int(0.02 * SR)):
        t = k / SR
        out.append(math.sin(TAU * 3200 * t) * math.exp(-t * 300) + (rng.random() * 2 - 1) * 0.3 * math.exp(-t * 600))
    return out


# ---------- stems ----------
def drums():
    D = buf()
    K, CL, HC, HO, DHA, TA = kick(), clap(), hat(90), hat(28), dha(), ta()
    for b in range(BARS):
        s = SEC[b]
        t0 = b * BAR
        if s["kick"]:
            for st in KICKS[s["kick"]]:
                place(D, K, t0 + st * STEP, 0.95)
        if s["clap"]:
            for st in (4, 12):
                place(D, CL, t0 + st * STEP, 0.6)
        if s["hats"]:
            div = s["hats"]
            for q in range(div):
                t = t0 + q * BAR / div
                place(D, HO if (div == 8 and q % 2) else HC, t, 0.16 if q % 2 else 0.1)
            if div == 16 and b in (2, 4, 5, 7, 11):  # 32nd roll into the next bar
                for q in range(8):
                    place(D, HC, t0 + 1.5 + q * STEP / 2, 0.08 + 0.01 * q)
        if s["dhol"]:
            for st in (0, 6, 8, 14):
                place(D, DHA, t0 + st * STEP, 0.55)
            for st in (3, 4, 10, 11, 12):
                place(D, TA, t0 + st * STEP, 0.3 if st in (4, 12) else 0.2)
    # opening race: counter ticks speeding up to the lock at 1.0 s
    T = tick()
    t, gap = 0.02, 0.09
    while t < 0.98:
        place(D, T, t, 0.22)
        t += gap
        gap = max(0.022, gap * 0.9)
    # build into the drop and into the logo
    for q in range(8):
        place(D, CL, 3.5 + q * STEP / 2, 0.15 + 0.04 * q)
    for q, (a, n) in enumerate(((20.0, 4), (20.5, 4), (21.0, 8), (21.5, 8))):
        for k in range(n):
            place(D, CL, a + k * 0.5 / n, 0.12 + 0.05 * q)
    place(D, K, 1.0, 1.0)
    place(D, K, 22.0, 1.0)
    place(D, K, 26.0, 1.0)
    return D


def bass():
    B = buf()
    for b in range(BARS):
        s = SEC[b]
        if not s["bass"] or not s["kick"]:
            continue
        hits = KICKS[s["kick"]]
        for j, st in enumerate(hits):
            nxt = hits[j + 1] if j + 1 < len(hits) else 16
            dur = (nxt - st) * STEP
            place(B, bass808(midi(ROOTS[b]), dur), b * BAR + st * STEP, s["bass"])
    place(B, bass808(midi(38), 1.8), 1.0, 0.9)
    place(B, bass808(midi(38), 2.0), 22.0, 1.0)
    place(B, bass808(midi(41), 2.0), 26.0, 0.8)
    return B


HOOK = [(0, 69), (2, 74), (4, 72), (5, 69), (7, 67), (8, 69), (10, 65), (12, 67), (14, 62)]


def plucks():
    L, R = buf(), buf()
    cache = {}
    for b in range(BARS):
        if not SEC[b]["pluck"]:
            continue
        for k, (st, m) in enumerate(HOOK):
            if m not in cache:
                cache[m] = pluck(midi(m))
            g = 0.55 if SEC[b]["kick"] != "half" else 0.45
            pan = 0.35 if k % 2 else 0.65
            place(L, cache[m], b * BAR + st * STEP, g * (1 - pan) * 1.6)
            place(R, cache[m], b * BAR + st * STEP + 0.003, g * pan * 1.6)
    return L, R


def pad():
    L, R = buf(), buf()
    for b in range(BARS):
        g = SEC[b]["pad"] * 0.25
        t0 = b * BAR
        dur = BAR + (1.2 if b == BARS - 1 else 0.25)
        for side, det in ((0, -0.08), (1, 0.08)):
            ch = L if side == 0 else R
            phs = [rng.random() for _ in CHORDS[b]]
            lp = 0.0
            for k in range(int(dur * SR)):
                t = k / SR
                tt = t0 + t
                if SILENCE[0] <= tt < SILENCE[1]:
                    continue
                s = 0.0
                for j, m in enumerate(CHORDS[b]):
                    phs[j] = (phs[j] + midi(m + det) / SR) % 1.0
                    s += 2 * phs[j] - 1
                lp += 0.09 * (s / 4 - lp)
                e = min(1.0, t / 0.08) * min(1.0, max(0.0, (dur - t) / 0.25))
                i = int(tt * SR)
                if i < N:
                    ch[i] += lp * e * g
    return L, R


def hits():
    H = buf()
    for t, g in ((1.0, 0.9), (4.0, 1.0), (12.0, 0.8), (22.0, 1.0), (26.0, 0.9)):
        place(H, impact(), t, g)
    for t, c in ((1.0, DM), (2.0, DM), (2.5, DM), (4.5, DM), (5.0, DM), (6.5, BB), (10.0, DM), (10.25, DM),
                 (10.5, DM), (12.5, DM), (14.0, BB), (14.5, BB), (18.5, F), (23.0, DM), (24.0, BB)):
        place(H, stab(c), t, 0.5)
    for t, d in ((0.0, 1.0), (3.0, 1.0), (20.0, 1.75)):
        place(H, sweep(d), t, 0.5)
    for t in (3.75, 9.5, 13.5, 15.5, 21.0):
        place(H, sweep(0.5, up=False), t, 0.45)
    return H


def bells():
    L, R = buf(), buf()
    for t, notes, g in ((18.5, (77, 81), 0.35), (23.0, (86, 89, 93, 98), 0.32), (26.0, (77, 81, 84, 89), 0.3)):
        for j, m in enumerate(notes):
            c = chime(midi(m), 2.4)
            place(L if j % 2 else R, c, t + 0.01 * j, g)
            place(R if j % 2 else L, c, t + 0.01 * j + 0.012, g * 0.6)
    return L, R


def hall_ir(seconds=1.8, rt60=1.6):
    L, R = array("d"), array("d")
    decay = 6.91 / rt60
    a = b = 0.0
    for k in range(int(seconds * SR)):
        t = k / SR
        e = math.exp(-decay * t) * min(1.0, t * 400)
        a += 0.5 * ((rng.random() * 2 - 1) - a)
        b += 0.5 * ((rng.random() * 2 - 1) - b)
        L.append(a * e)
        R.append(b * e)
    return L, R


def write(path, chans):
    n = len(chans[0])
    peak = max(1e-9, max(max(abs(v) for v in c) for c in chans))
    s = 0.9 / peak
    with wave.open(str(path), "wb") as w:
        w.setnchannels(len(chans))
        w.setsampwidth(2)
        w.setframerate(SR)
        fr = array("h")
        for i in range(n):
            for c in chans:
                fr.append(int(max(-1.0, min(1.0, c[i] * s)) * 32767))
        w.writeframes(fr.tobytes())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    out = pathlib.Path(ap.parse_args().out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        stems = {"drums": (drums(),), "bass": (bass(),), "plucks": plucks(), "pad": pad(),
                 "hits": (hits(),), "bells": bells()}
        for nm, ch in stems.items():
            write(td / f"{nm}.wav", list(ch))
        irL, irR = hall_ir()
        write(td / "ir.wav", [irL, irR])
        lv = {"drums": 0.85, "bass": 0.6, "plucks": 0.62, "pad": 0.32, "hits": 0.6, "bells": 0.45}
        fc = (
            "[0]aformat=channel_layouts=stereo,volume={drums},asplit[dr][drs];"
            "[1]aformat=channel_layouts=stereo,volume={bass}[ba];"
            "[2]volume={plucks},asplit[pl][pls];"
            "[3]volume={pad},asplit[pa][pas];"
            "[4]aformat=channel_layouts=stereo,volume={hits},asplit[hi][his];"
            "[5]volume={bells},asplit[be][bes];"
            "[drs]volume=0.12[s0];[pls]volume=0.45[s1];[pas]volume=0.4[s2];[his]volume=0.3[s3];[bes]volume=0.7[s4];"
            "[s0][s1][s2][s3][s4]amix=inputs=5:normalize=0[send];"
            "[send][6]afir=dry=0:wet=1:length=1:gtype=peak,volume=0.45[rev];"
            "[dr][ba][pl][pa][hi][be][rev]amix=inputs=7:normalize=0,"
            "highpass=f=30,bass=g=-3:f=90,equalizer=f=2500:width_type=o:width=1.5:g=3,"
            "acompressor=threshold=-20dB:ratio=4:attack=5:release=110:makeup=4,alimiter=limit=0.7:attack=2:release=40:level=disabled,"
            "loudnorm=I=-10.5:TP=-1.5:LRA=8,aresample=48000,"
            f"atrim=0:{TOTAL:.3f},afade=t=out:st={TOTAL - 1.2:.3f}:d=1.2,alimiter=limit=0.84:level=disabled"
        ).format(**lv)
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
        for nm in stems:
            cmd += ["-i", str(td / f"{nm}.wav")]
        cmd += ["-i", str(td / "ir.wav"), "-filter_complex", fc, "-c:a", "pcm_s16le", str(out)]
        subprocess.run(cmd, check=True)
    print(f"wrote {out} ({TOTAL:.0f}s @ {BPM} BPM)")


if __name__ == "__main__":
    main()
