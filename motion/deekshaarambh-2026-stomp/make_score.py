#!/usr/bin/env python3
"""Synthesize the stomp piece's score: 32 s, 112.5 BPM, D major, celebratory.

Usage: motion/deekshaarambh-2026-stomp/make_score.py --out <dir>/score.wav

Everything is placed from beatmap.py, the same clock compose.py cuts to:
  - a stage stomp (three layered feet) and a crowd clap on every stomp-stomp-clap,
    over a dhol bhangra chaal (dha on the bass skin, ta on the treble)
  - a brass section: the hook as full chords on a 3-3-2-2-2-4 figure over
    D, A, Bm, G, brass stabs on the claps, a low horn line in the breakdown, a
    held D major chord under the identity
  - a camera shutter on every face change (two curtains when spaced, a motor
    drive click inside a burst, a soft one in the breakdown and the map)
  - a sub bass ducked by the stomps, a string pad, tom fills into the drops,
    crash cymbals, booms and crowd-cheer swells on the big hits, risers

Arc: stomps, shutters and a low brass swell; the drop at 11,000+ with a cheer;
a lean bar under the counter race; a breakdown on horn and strings for "trust";
a rise; the peak for the purpose line; a held D under the identity.
Stdlib synthesis, mixed and mastered with ffmpeg (convolution hall). Deterministic.
"""
import argparse
import math
import pathlib
import random
import subprocess
import sys
import tempfile
import wave
from array import array

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import beatmap as BM  # noqa: E402

SR = 44100
TOTAL = BM.TOTAL
N = int((TOTAL + 1.0) * SR)
TAU = 2 * math.pi
BEAT = 60 / BM.BPM
BAR = 4 * BEAT
STEP = BAR / 16
rng = random.Random(112)
midi = lambda m: 440.0 * 2 ** ((m - 69) / 12)
T = lambda f: f / BM.FPS
SIL = (T(BM.SILENCE[0]), T(BM.SILENCE[1]))

VOICING = {"D": (62, 66, 69, 74), "A": (61, 64, 69, 73), "Bm": (62, 66, 71, 74), "G": (62, 67, 71, 74)}
ROOT = {"D": 38, "A": 45, "Bm": 47, "G": 43}
HOOK = {  # 16th step -> midi melody (top voice of the brass), per chord: a 3-3-2-2-2-4 figure
    "D": [(0, 69), (3, 74), (6, 78), (8, 76), (10, 74), (12, 76)],
    "A": [(0, 73), (3, 76), (6, 81), (8, 78), (10, 76), (12, 73)],
    "Bm": [(0, 74), (3, 78), (6, 83), (8, 81), (10, 78), (12, 74)],
    "G": [(0, 71), (3, 74), (6, 79), (8, 78), (10, 76), (12, 74), (14, 76)],
}


def chord_at(t):
    bar = min(14, int(t / BAR))
    c = BM.CHORDS[bar]
    if isinstance(c, tuple):
        return c[0] if (t - bar * BAR) < BAR / 2 else c[1]
    return c


def groove(bar):
    return BM.BAR_GROOVE.get(bar, "tail")


def buf():
    return array("d", bytes(8 * N))


def place(dst, shot, t, g=1.0):
    if SIL[0] <= t < SIL[1]:
        return
    i0 = int(round(t * SR))
    for k in range(min(len(shot), N - i0)):
        dst[i0 + k] += shot[k] * g


def lp_noise(alpha):
    """one-pole lowpassed white noise generator state"""
    return [0.0, alpha]


# ---------------------------------------------------------------- percussion
def stomp(soft=False):
    out = array("d", bytes(8 * int(0.55 * SR)))
    for off, g, pitch in ((0.0, 1.0, 1.0), (0.007, 0.7, 0.93), (0.016, 0.5, 1.07)):
        ph, lp = 0.0, 0.0
        i0 = int(off * SR)
        for k in range(len(out) - i0):
            t = k / SR
            ph += (50 + 95 * math.exp(-t * 24)) * pitch / SR
            lp += 0.07 * ((rng.random() * 2 - 1) - lp)
            s = (math.tanh(2.2 * math.sin(TAU * ph)) * math.exp(-t * 9)
                 + lp * 3.2 * math.exp(-t * 32)
                 + 0.22 * math.sin(TAU * 205 * pitch * t) * math.exp(-t * 30)
                 + 0.12 * math.sin(TAU * 330 * pitch * t) * math.exp(-t * 45))
            out[i0 + k] += s * g * (0.55 if soft else 1.0)
    if soft:
        lp = 0.0
        for k in range(len(out)):
            lp += 0.25 * (out[k] - lp)
            out[k] = lp
    return out


def clap():
    n = int(0.36 * SR)
    out = array("d", bytes(8 * n))
    for j in range(8):
        off = rng.uniform(0.0, 0.022)
        fc = rng.uniform(1100, 1900)
        f = 2 * math.sin(math.pi * fc / SR)
        low = band = 0.0
        i0 = int(off * SR)
        g = rng.uniform(0.6, 1.0)
        for k in range(n - i0):
            t = k / SR
            burst = sum(math.exp(-(t - d) * 110) for d in (0.0, 0.009, 0.019) if t >= d)
            low += f * band
            high = (rng.random() * 2 - 1) - low - 0.6 * band
            band += f * high
            out[i0 + k] += band * g * (0.5 * burst + 0.35 * math.exp(-t * 16))
    return out


def hat(decay=90):
    out, prev = array("d"), 0.0
    for k in range(int(0.09 * SR)):
        nz = rng.random() * 2 - 1
        out.append((nz - prev) * math.exp(-k / SR * decay))
        prev = nz
    return out


def clack(ring, body, dur, amp=1.0):
    """one shutter curtain: a hard tick, a metal ring, a small body thunk"""
    n = int(dur * SR)
    out, prev = array("d"), 0.0
    for k in range(n):
        t = k / SR
        nz = rng.random() * 2 - 1
        hp = nz - prev
        prev = nz
        out.append(amp * (hp * 0.9 * math.exp(-t * 900)
                          + 0.45 * math.sin(TAU * ring * t) * math.exp(-t * 260)
                          + 0.3 * math.sin(TAU * ring * 1.47 * t) * math.exp(-t * 340)
                          + 0.55 * math.sin(TAU * body * t) * math.exp(-t * 90)))
    return out


def shutter(kind):
    if kind == "burst":
        return clack(3100, 170, 0.03, 0.85)
    out = array("d", bytes(8 * int(0.14 * SR)))
    a = clack(2900, 180, 0.05)
    b = clack(2350, 140, 0.06, 0.75)
    for k, v in enumerate(a):
        out[k] += v
    i0 = int(0.052 * SR)
    for k, v in enumerate(b):
        out[i0 + k] += v
    for k in range(int(0.004 * SR), i0):     # the mirror's whirr between curtains
        out[k] += 0.05 * (rng.random() * 2 - 1)
    if kind == "soft":
        lp = 0.0
        for k in range(len(out)):
            lp += 0.35 * (out[k] - lp)
            out[k] = lp * 0.8
    return out


# ---------------------------------------------------------------- tones and drums
def dha():
    """dhol bass skin: a boomy membrane with a falling pitch and a palm thump"""
    out, ph, lp = array("d"), 0.0, 0.0
    for k in range(int(0.5 * SR)):
        t = k / SR
        ph += (64 + 48 * math.exp(-t * 18)) / SR
        lp += 0.05 * ((rng.random() * 2 - 1) - lp)
        out.append(math.tanh(1.6 * math.sin(TAU * ph)) * math.exp(-t * 6.5) + lp * 2.2 * math.exp(-t * 40))
    return out


def ta():
    """dhol treble skin: the cane's crack, band-passed noise with a short ring"""
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


def tom(f0):
    out, ph = array("d"), 0.0
    for k in range(int(0.45 * SR)):
        t = k / SR
        ph += (f0 * (1 + 0.5 * math.exp(-t * 25))) / SR
        out.append(math.tanh(1.4 * math.sin(TAU * ph)) * math.exp(-t * 7) + (rng.random() * 2 - 1) * 0.25 * math.exp(-t * 90))
    return out


def crash(dur=2.6):
    n = int(dur * SR)
    out, prev = array("d"), 0.0
    parts = [(f, rng.random() * TAU, rng.uniform(0.5, 1.0)) for f in (3170, 4230, 5390, 6610, 8120, 9480, 11200)]
    for k in range(n):
        t = k / SR
        nz = rng.random() * 2 - 1
        hp = nz - prev
        prev = nz
        tone = sum(a * math.sin(TAU * f * t + p) for f, p, a in parts) / 7
        out.append((0.75 * hp + 0.35 * tone) * math.exp(-t * 2.6) * min(1.0, t * 2000))
    return out


def cheer(dur=2.8):
    """a crowd: two formant-ish noise bands under a flutter of many voices, swelling then falling"""
    n = int(dur * SR)
    out = array("d")
    bands = []
    for fc, q in ((900, 0.5), (2400, 0.6)):
        bands.append([2 * math.sin(math.pi * fc / SR), q, 0.0, 0.0])
    flut = [(rng.uniform(5, 13), rng.random() * TAU) for _ in range(9)]
    for k in range(n):
        t = k / SR
        nz = rng.random() * 2 - 1
        s = 0.0
        for b in bands:
            f, q, low, band = b
            low += f * band
            high = nz - low - q * band
            band += f * high
            b[2], b[3] = low, band
            s += band
        am = 0.6 + 0.4 * sum(math.sin(TAU * fr * t + ph) for fr, ph in flut) / 9
        env = min(1.0, t / 0.35) * math.exp(-max(0.0, t - 0.5) * 1.3)
        out.append(s * am * env)
    return out


_brass = {}


def brass_note(m, dur, vel=1.0, dark=False):
    """synth brass: three detuned saws, a scoop up into pitch, a filter that opens on the attack
    and settles, vibrato on held notes"""
    key = (m, round(dur, 3), round(vel, 2), dark)
    if key in _brass:
        return _brass[key]
    f = midi(m)
    n = int((dur + 0.08) * SR)
    out = array("d")
    ph = [rng.random() for _ in range(3)]
    det = (-0.004, 0.0, 0.0045)
    l1 = l2 = 0.0
    for k in range(n):
        t = k / SR
        scoop = 2 ** (-0.4 / 12 * math.exp(-t / 0.035))
        vib = 1 + (0.0045 * math.sin(TAU * 5.6 * t) * min(1.0, max(0.0, (t - 0.25) / 0.2)) if dur > 0.45 else 0.0)
        s = 0.0
        for j in range(3):
            ph[j] = (ph[j] + f * (1 + det[j]) * scoop * vib / SR) % 1.0
            s += 2 * ph[j] - 1
        s /= 3
        fenv = min(1.0, t / 0.025) * (0.45 + 0.55 * math.exp(-t / 0.18))
        fc = f * ((1.2 + 5.5 * vel * fenv) if not dark else (1.0 + 2.2 * vel * fenv))
        a = min(0.95, 2 * math.pi * fc / SR)
        l1 += a * (s - l1)
        l2 += a * (l1 - l2)
        amp = min(1.0, t / 0.018) * (0.82 + 0.18 * math.exp(-t / 0.08)) * min(1.0, max(0.0, (dur + 0.06 - t) / 0.06))
        out.append(math.tanh(1.6 * l2) * amp * vel)
    _brass[key] = out
    return out


def brass_chord(L, R, t, notes, dur, vel=1.0, gain=1.0, dark=False):
    for j, m in enumerate(notes):
        s = brass_note(m, dur, vel, dark)
        g = gain * (1.0 if j == 0 else 0.62)
        pan = 0.5 + (0.22 if j % 2 else -0.22) * (j > 0)
        place(L, s, t + 0.002 * j, g * (1 - pan) * 1.4)
        place(R, s, t + 0.002 * j + 0.004, g * pan * 1.4)


def voicing_under(m, c):
    """the melody note on top, the two chord tones just under it, the root an octave above the bass"""
    pcs = {n % 12 for n in VOICING[c]}
    below = [x for x in range(m - 1, m - 13, -1) if x % 12 in pcs][:2]
    return [m] + below + [ROOT[c] + 12]


def boom(dur=2.4, low=34, hi=80):
    out, ph, lp = array("d"), 0.0, 0.0
    for k in range(int(dur * SR)):
        t = k / SR
        ph += (low + hi * math.exp(-t * 6)) / SR
        lp += 0.03 * ((rng.random() * 2 - 1) - lp)
        out.append(math.sin(TAU * ph) * math.exp(-t * 2.2) + lp * 2.2 * math.exp(-t * 3.4))
    return out


def rise(dur):
    out, low, band = array("d"), 0.0, 0.0
    n = int(dur * SR)
    for k in range(n):
        x = k / n
        f = 2 * math.sin(math.pi * (250 + 7000 * x * x) / SR)
        low += f * band
        high = (rng.random() * 2 - 1) - low - 0.45 * band
        band += f * high
        tone = 0.25 * math.sin(TAU * (220 + 660 * x * x) * k / SR) * x
        out.append((band * 0.8 + tone) * x ** 2.0)
    return out


# ---------------------------------------------------------------- stems
def drums():
    D = buf()
    ST, SS, CL = stomp(), stomp(soft=True), clap()
    for f, kind in BM.groove_hits():
        t = T(f)
        if kind == "stomp":
            place(D, ST, t, 1.0)
        elif kind == "stomp_soft":
            place(D, SS, t, 0.8)
        else:
            place(D, CL, t, 0.62)
    H, HO = hat(95), hat(26)
    for bar in range(15):
        g = groove(bar)
        t0 = bar * BAR
        if g in ("full", "peak", "build", "logo"):
            for q in range(16):
                place(D, H, t0 + q * STEP, 0.07 if q % 2 else 0.045)
        if g == "peak":
            for q in (2, 6, 10, 14):
                place(D, HO, t0 + q * STEP, 0.12)
        if g == "full":
            for q in (6, 14):
                place(D, HO, t0 + q * STEP, 0.08)
    # builds: clap rolls tightening into the hits
    for a, b in BM.RISERS[1:3]:
        ta, tb = T(a), T(b)
        span = tb - ta
        t, k = ta + span / 2, 0
        for div, part in ((8, 0.5), (16, 0.25), (32, 0.25)):
            n_ = int(round(part * span / (BAR / div)))
            for _ in range(n_):
                place(D, CL, t, 0.12 + 0.35 * (t - ta) / span)
                t += BAR / div
    return D


def shutters():
    L, R = buf(), buf()
    cache = {k: shutter(k) for k in ("full", "burst", "soft")}
    for f, kind in BM.clicks():
        t = T(f)
        g = {"full": 0.75, "burst": 0.55, "soft": 0.4}[kind]
        place(L, cache[kind], t, g)
        place(R, cache[kind], t + 0.0007, g * 0.92)
    return L, R


def duck_env():
    """sidechain: dip under every stomp in the driving bars"""
    env = array("d", [1.0]) * N
    for f, kind in BM.groove_hits():
        if kind != "stomp":
            continue
        bar = int(T(f) / BAR)
        if groove(bar) not in ("full", "peak", "build", "logo", "rise"):
            continue
        i0 = int(T(f) * SR)
        for k in range(int(0.28 * SR)):
            if i0 + k >= N:
                break
            env[i0 + k] = min(env[i0 + k], 1 - 0.6 * math.exp(-k / SR / 0.09))
    return env


def bass(env):
    B = buf()
    cache = {}
    for bar in range(15):
        g = groove(bar)
        if g in ("intro", "soft", "tail"):
            continue
        lvl = {"full": 1.0, "peak": 1.0, "lean": 0.85, "build": 0.9, "rise": 0.7, "logo": 1.0}[g]
        for q in range(8):                       # eighths, root and octave
            t = bar * BAR + q * 2 * STEP
            r = ROOT[chord_at(t)]
            m = r + (12 if q % 2 and g == "peak" else 0)
            key = (m, 0.26)
            if key not in cache:
                ph, o = 0.0, array("d")
                fr = midi(m)
                for k in range(int(0.26 * SR)):
                    tt = k / SR
                    ph += fr / SR
                    s = math.sin(TAU * ph) + 0.3 * math.sin(2 * TAU * ph) + 0.12 * math.sin(3 * TAU * ph)
                    o.append(math.tanh(1.4 * s) * min(1.0, tt * 400) * math.exp(-tt * 3.5) * min(1.0, (0.26 - tt) * 50))
                cache[key] = o
            place(B, cache[key], t, lvl * (1.0 if q % 2 == 0 else 0.75))
    # held subs: under the logo and the tail, under the breakdown's downbeats
    for bar in (7, 8, 13, 14):
        t = bar * BAR
        r = ROOT[chord_at(t + 0.01)]
        ph, o = 0.0, array("d")
        dur = BAR + (1.0 if bar == 14 else 0.05)
        for k in range(int(dur * SR)):
            tt = k / SR
            ph += midi(r) / SR
            o.append(math.sin(TAU * ph) * min(1.0, tt * 60) * min(1.0, (dur - tt) * 8) * (0.55 if bar < 13 else 0.8))
        place(B, o, t)
    for i in range(N):
        B[i] *= env[i]
    return B


def brass():
    """the hook as brass chords, stabs on the claps, horn in the breakdown, swells and the final chord"""
    L, R = buf(), buf()
    for bar in range(15):
        g = groove(bar)
        t0 = bar * BAR
        c = chord_at(t0 + 0.01)
        if g in ("full", "build", "peak"):
            steps = [st for st in range(16) if dict(HOOK[chord_at(t0 + st * STEP)]).get(st) is not None]
            for i, st in enumerate(steps):
                t = t0 + st * STEP
                m = dict(HOOK[chord_at(t)])[st]
                nxt = steps[i + 1] if i + 1 < len(steps) else 16
                dur = min(0.5, (nxt - st) * STEP * 0.82)
                vel = 1.0 if st in (0, 6) else 0.85
                brass_chord(L, R, t, voicing_under(m, chord_at(t)), dur, vel, 0.55 if g != "peak" else 0.62)
        if g in ("full", "peak", "lean", "build", "logo"):
            for beat in (1, 3):
                t = t0 + beat * BEAT
                cc = chord_at(t)
                brass_chord(L, R, t, [VOICING[cc][-1]] + list(VOICING[cc][:-1]) + [ROOT[cc] + 12], 0.16, 1.0, 0.42)
        if g == "soft":                       # breakdown: a low horn sings the hook's long notes
            for st, m in HOOK[c]:
                if st in (0, 6, 12):
                    brass_chord(L, R, t0 + st * STEP, [m - 12], 0.75 if st < 12 else 0.6, 0.55, 0.5, dark=True)
        if g == "rise":                       # swells climbing into the peak
            for beat in range(4):
                cc = chord_at(t0 + beat * BEAT)
                brass_chord(L, R, t0 + beat * BEAT, voicing_under(VOICING[cc][-1] + (beat >= 2) * 2, cc), BEAT * 0.9,
                            0.55 + 0.12 * beat, 0.32 + 0.08 * beat)
    # intro: a low swell into the drop
    brass_chord(L, R, T(BM.fb(1)), [50, 57, 62], T(BM.fb(4)) - T(BM.fb(1)) - 0.05, 0.6, 0.3, dark=True)
    # the identity: one big held D major chord, then the last clap's stab
    brass_chord(L, R, T(BM.fb(52)), [78, 74, 69, 66, 62, 50], 3.3, 1.0, 0.52)
    brass_chord(L, R, T(BM.fb(56)), [81, 78, 74, 69, 62, 50], 3.0, 0.9, 0.42)
    return L, R


def dhol():
    Dh = buf()
    DHA, TA = dha(), ta()
    for bar in range(15):
        g = groove(bar)
        if g not in ("full", "peak", "build", "logo", "rise"):
            continue
        t0 = bar * BAR
        for st in (0, 6, 8, 14):
            place(Dh, DHA, t0 + st * STEP, 0.6 if g != "rise" else 0.4)
        for st in (3, 4, 10, 11, 12):
            place(Dh, TA, t0 + st * STEP, (0.34 if st in (4, 12) else 0.22) * (0.7 if g == "rise" else 1.0))
        if g == "peak":                       # extra ta on the off-sixteenths
            for st in (7, 15):
                place(Dh, TA, t0 + st * STEP, 0.16)
    return Dh


def pad(env):
    L, R = buf(), buf()
    lvl = {"intro": 0.3, "full": 0.45, "lean": 0.42, "build": 0.55, "soft": 0.42, "rise": 0.55,
           "peak": 0.6, "logo": 0.8, "tail": 0.9}
    for bar in range(15):
        g = groove(bar)
        for half in (0, 1):
            t0 = bar * BAR + half * BAR / 2
            c = chord_at(t0 + 0.01)
            dur = BAR / 2 + (1.0 if bar == 14 and half else 0.03)
            notes = VOICING[c] + (ROOT[c] + 12,)
            for side, det, ch in ((0, -0.07, L), (1, 0.07, R)):
                ph = [rng.random() for _ in notes]
                inc = [midi(m + det) / SR for m in notes]
                lp = 0.0
                i0 = int(t0 * SR)
                cut = 0.05 if g in ("soft", "tail", "intro") else 0.09
                for k in range(int(dur * SR)):
                    s = 0.0
                    for j in range(len(notes)):
                        p = ph[j] + inc[j]
                        p -= int(p)
                        ph[j] = p
                        s += 2 * p - 1
                    lp += cut * (s / 5 - lp)
                    i = i0 + k
                    if i < N:
                        ch[i] += lp * lvl[g] * 0.2
    for i in range(N):
        L[i] *= env[i]
        R[i] *= env[i]
    return L, R


def fx():
    L, R = buf(), buf()
    for a, b in BM.RISERS:
        r = rise(T(b) - T(a))
        place(L, r, T(a), 0.42)
        place(R, r, T(a) + 0.006, 0.42)
    CR = crash()
    for f in BM.IMPACTS:
        bm = boom()
        place(L, bm, T(f), 0.8)
        place(R, bm, T(f), 0.8)
        place(L, CR, T(f), 0.3)
        place(R, CR, T(f) + 0.009, 0.3)
    CH = cheer()
    for f, g in ((BM.fb(4), 0.32), (BM.fb(40), 0.36), (BM.fb(52), 0.42)):
        place(L, CH, T(f) + 0.02, g)
        place(R, cheer(), T(f) + 0.05, g)
    # tom fills: the last beat before each drop, high to low
    for f in (BM.fb(4), BM.fb(24), BM.fb(40), BM.fb(52)):
        for k, f0 in enumerate((180, 150, 120, 95)):
            tm = tom(f0)
            t = T(f) - BEAT + k * BEAT / 4
            place(L, tm, t, 0.32 if k % 2 else 0.24)
            place(R, tm, t, 0.24 if k % 2 else 0.32)
    return L, R


def hall(seconds=2.2, rt60=1.9):
    L, R = array("d"), array("d")
    dec = 6.91 / rt60
    a = b = 0.0
    for k in range(int(seconds * SR)):
        t = k / SR
        e = math.exp(-dec * t) * min(1.0, t * 300)
        a += 0.45 * ((rng.random() * 2 - 1) - a)
        b += 0.45 * ((rng.random() * 2 - 1) - b)
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


TARGET_MEAN = -13.6     # dB, volumedetect mean; the repo's gate is -17 to -13


def arc_expr():
    """mix automation: the breakdown sits ~3 dB under, the rise bar climbs back to full for the peak"""
    b28, b36, b40 = (T(BM.fb(b)) for b in (28, 36, 40))
    return (f"1-0.18*min(1\\,max(0\\,(t-{b28:.3f})/0.12))"
            f"+0.18*min(1\\,max(0\\,(t-{b36:.3f})/{b40 - b36:.3f}))")


def mean_volume(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    return float(r.stderr.split("mean_volume:")[1].split("dB")[0])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    out = pathlib.Path(ap.parse_args().out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    env = duck_env()
    stems = {"drums": (drums(),), "shutter": shutters(), "bass": (bass(env),), "brass": brass(),
             "dhol": (dhol(),), "pad": pad(env), "fx": fx()}
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        for nm, ch in stems.items():
            write(td / f"{nm}.wav", list(ch))
        write(td / "ir.wav", list(hall()))
        lv = {"drums": 0.9, "shutter": 0.36, "bass": 0.55, "brass": 0.62, "dhol": 0.62, "pad": 0.26, "fx": 0.55}
        fc = (
            "[0]aformat=channel_layouts=stereo,volume={drums},asplit[d][ds];"
            "[1]volume={shutter},asplit[sh][shs];"
            "[2]aformat=channel_layouts=stereo,volume={bass}[b];"
            "[3]volume={brass},asplit[k][ks];"
            "[4]aformat=channel_layouts=stereo,volume={dhol},asplit[p][ps];"
            "[5]volume={pad},asplit[pa][pas];"
            "[6]volume={fx},asplit[x][xs];"
            "[ds]volume=0.3[s0];[shs]volume=0.1[s1];[ks]volume=0.38[s2];[ps]volume=0.18[s3];[pas]volume=0.4[s4];[xs]volume=0.3[s5];"
            "[s0][s1][s2][s3][s4][s5]amix=inputs=6:normalize=0[send];"
            "[send][7]afir=dry=0:wet=1:length=1:gtype=peak,volume=0.5[rev];"
            "[d][sh][b][k][p][pa][x][rev]amix=inputs=8:normalize=0,"
            "highpass=f=30,bass=g=-2:f=90,equalizer=f=2200:width_type=o:width=1.5:g=1.5,treble=g=-3:f=7000,"
            "acompressor=threshold=-15dB:ratio=2.2:attack=8:release=140:makeup=2,"
            "alimiter=limit=0.75:attack=2:release=50:level=disabled,aresample=48000,"
            f"atrim=0:{TOTAL:.3f},afade=t=out:st={TOTAL - 0.7:.3f}:d=0.7,"
            f"volume=eval=frame:volume='{arc_expr()}'"
        ).format(**lv)
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
        for nm in stems:
            cmd += ["-i", str(td / f"{nm}.wav")]
        mix = td / "mix.wav"
        cmd += ["-i", str(td / "ir.wav"), "-filter_complex", fc, "-c:a", "pcm_f32le", str(mix)]
        subprocess.run(cmd, check=True)
        # master: one static gain to the target mean (keeps the arc's dynamics), then a peak limiter
        gain = TARGET_MEAN - mean_volume(mix)
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(mix), "-af",
                        f"volume={gain:.2f}dB,alimiter=limit=0.89:attack=1:release=60:level=disabled",
                        "-c:a", "pcm_s16le", str(out)], check=True)
    print(f"wrote {out} ({TOTAL:.0f}s @ {BM.BPM} BPM, {len(BM.clicks())} shutter clicks)")


if __name__ == "__main__":
    main()
