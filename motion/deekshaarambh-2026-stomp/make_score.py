#!/usr/bin/env python3
"""Synthesize the stomp piece's score: 32 s, 112.5 BPM, D major, stomp-stomp-clap.

Usage: motion/deekshaarambh-2026-stomp/make_score.py --out <dir>/score.wav

Everything is placed from beatmap.py, the same clock compose.py cuts to:
  - a stage stomp (three layered feet) and a crowd clap on every stomp-stomp-clap
  - a camera shutter on every face change: a two-curtain click when changes are
    spaced, a short motor-drive click inside a burst, a soft one in the breakdown
  - a piano hook on a 3-3-2-2-2-4 figure over D, A, Bm, G, doubled by a pluck an
    octave up; piano stabs on the claps; a sub bass ducked by the stomps; a pad
  - risers into the drops, impacts on the section hits, bells on 2026 and the logo

Arc: stomps and shutters alone with the hook on solo piano, the drop at 11,000+,
a lean bar under the counter race, a breakdown on piano for "trust", a rise,
the peak for the purpose line, and a held D under the identity.
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
HOOK = {  # 16th step -> midi, per chord (a 3-3-2-2-2-4 figure)
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


# ---------------------------------------------------------------- tones
_piano = {}


def piano(m, dur=1.3, vel=1.0):
    key = (m, round(dur, 2), round(vel, 2))
    if key in _piano:
        return _piano[key]
    f = midi(m)
    n = int(dur * SR)
    out = array("d", bytes(8 * n))
    kf = (f / 440) ** 0.35
    for p in range(1, 11):
        fp = p * f * math.sqrt(1 + 0.00038 * p * p)
        if fp > 10000:
            break
        amp = vel * p ** -1.25 * (1.0 if p < 3 else 0.6 + 0.4 * vel)
        d1, d2 = (5.0 + 2.2 * p) * kf, (0.9 + 0.5 * p) * kf
        for det in (-0.06 * p, 0.06 * p):
            w = TAU * (fp + det) / SR
            c, s = math.cos(w), math.sin(w)
            x, y = 1.0, 0.0
            for k in range(n):
                t = k / SR
                e = 0.55 * math.exp(-t * d1) + 0.45 * math.exp(-t * d2)
                out[k] += y * amp * e * 0.5
                x, y = x * c - y * s, x * s + y * c
    lp = 0.0
    for k in range(int(0.02 * SR)):       # hammer felt
        t = k / SR
        lp += 0.2 * ((rng.random() * 2 - 1) - lp)
        out[k] += lp * 0.5 * vel * math.exp(-t * 220)
    for k in range(n):
        t = k / SR
        out[k] = math.tanh(1.3 * out[k]) * min(1.0, t * 900) * min(1.0, (dur - t) * 25)
    _piano[key] = out
    return out


def pluck(f, dur=0.9):
    n = max(2, int(round(SR / f)))
    line = [rng.uniform(-1, 1) for _ in range(n)]
    out, i = array("d"), 0
    for k in range(int(dur * SR)):
        a, b = line[i], line[(i + 1) % n]
        line[i] = 0.5 * (a + b) * 0.9972
        i = (i + 1) % n
        out.append(a * min(1.0, (dur - k / SR) * 30))
    return out


def bell(f, dur=3.0, idx=1.3):
    out = array("d")
    for k in range(int(dur * SR)):
        t = k / SR
        s = math.sin(TAU * f * t + idx * math.exp(-t * 4) * math.sin(TAU * 3.5 * f * t))
        out.append(s * math.exp(-t * 1.8) * min(1.0, t * 500))
    return out


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
                place(D, H, t0 + q * STEP, 0.11 if q % 2 else 0.07)
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


def keys():
    """piano hook + stabs, pluck double"""
    L, R = buf(), buf()
    PL, PR = buf(), buf()
    for bar in range(15):
        g = groove(bar)
        t0 = bar * BAR
        c = chord_at(t0 + 0.01)
        # hook
        if g in ("intro", "full", "build", "peak", "soft", "rise"):
            vel = {"intro": 0.7, "soft": 0.6, "rise": 0.7}.get(g, 0.9)
            for st in range(16):
                t = t0 + st * STEP
                m = dict(HOOK[chord_at(t)]).get(st)
                if m is None:
                    continue
                acc = 1.0 if st in (0, 6) else 0.8
                s = piano(m, 1.1, round(vel * acc, 2))
                place(L, s, t, 0.5)
                place(R, s, t + 0.004, 0.5)
                if g in ("full", "peak", "build"):
                    pk = pluck(midi(m + 12), 0.6)
                    place(PL, pk, t, 0.22 if st % 2 else 0.3)
                    place(PR, pk, t + 0.011, 0.3 if st % 2 else 0.22)
        # stabs on the claps; held chords in the breakdown and the identity
        if g in ("full", "peak", "lean", "build", "logo"):
            for beat in (1, 3):
                t = t0 + beat * BEAT
                for m in VOICING[chord_at(t)]:
                    s = piano(m, 0.5, 0.75)
                    place(L, s, t, 0.3)
                    place(R, s, t + 0.003, 0.3)
        if g in ("soft", "rise", "logo", "tail"):
            for m in VOICING[c] + (ROOT[c] + 12,):
                s = piano(m - 12, 2.2 if g != "tail" else 3.0, 0.65)
                gg = 0.2 if g in ("soft", "rise") else 0.32
                place(L, s, t0, gg)
                place(R, s, t0 + 0.005, gg)
    return L, R, PL, PR


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
        place(L, r, T(a), 0.5)
        place(R, r, T(a) + 0.006, 0.5)
    for f in BM.IMPACTS:
        bm = boom()
        place(L, bm, T(f), 0.85)
        place(R, bm, T(f), 0.85)
    for f, notes in ((BM.fb(12), (74, 78, 81)), (BM.fb(32.5), (78, 86)), (BM.fb(52), (74, 78, 81, 86, 90))):
        for j, m in enumerate(notes):
            s = bell(midi(m), 3.2)
            place(L if j % 2 else R, s, T(f) + 0.012 * j, 0.2)
            place(R if j % 2 else L, s, T(f) + 0.012 * j + 0.01, 0.13)
    # bricks landing: a dull wooden knock per brick
    knock = array("d")
    for k in range(int(0.06 * SR)):
        t = k / SR
        knock.append(math.sin(TAU * 240 * t) * math.exp(-t * 70) + 0.4 * (rng.random() * 2 - 1) * math.exp(-t * 300))
    for i, f in enumerate(BM.BRICKS):
        place(L, knock, T(f), 0.25 + 0.02 * i)
        place(R, knock, T(f) + 0.002, 0.25 + 0.02 * i)
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
    return (f"1-0.3*min(1\\,max(0\\,(t-{b28:.3f})/0.12))"
            f"+0.3*min(1\\,max(0\\,(t-{b36:.3f})/{b40 - b36:.3f}))")


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
    kl, kr, pl, pr = keys()
    stems = {"drums": (drums(),), "shutter": shutters(), "bass": (bass(env),), "keys": (kl, kr),
             "pluck": (pl, pr), "pad": pad(env), "fx": fx()}
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        for nm, ch in stems.items():
            write(td / f"{nm}.wav", list(ch))
        write(td / "ir.wav", list(hall()))
        lv = {"drums": 0.9, "shutter": 0.5, "bass": 0.55, "keys": 0.62, "pluck": 0.3, "pad": 0.3, "fx": 0.55}
        fc = (
            "[0]aformat=channel_layouts=stereo,volume={drums},asplit[d][ds];"
            "[1]volume={shutter},asplit[sh][shs];"
            "[2]aformat=channel_layouts=stereo,volume={bass}[b];"
            "[3]volume={keys},asplit[k][ks];"
            "[4]volume={pluck},asplit[p][ps];"
            "[5]volume={pad},asplit[pa][pas];"
            "[6]volume={fx},asplit[x][xs];"
            "[ds]volume=0.32[s0];[shs]volume=0.12[s1];[ks]volume=0.4[s2];[ps]volume=0.5[s3];[pas]volume=0.4[s4];[xs]volume=0.35[s5];"
            "[s0][s1][s2][s3][s4][s5]amix=inputs=6:normalize=0[send];"
            "[send][7]afir=dry=0:wet=1:length=1:gtype=peak,volume=0.5[rev];"
            "[d][sh][b][k][p][pa][x][rev]amix=inputs=8:normalize=0,"
            "highpass=f=30,bass=g=-2:f=90,equalizer=f=3000:width_type=o:width=1.5:g=2,"
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
