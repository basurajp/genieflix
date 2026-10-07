#!/usr/bin/env python3
"""Synthesize the Deekshaarambh 2026 brand film score: 32 s instrumental, 120 BPM, D major.

Usage: motion/deekshaarambh-2026-film/make_score.py --out <dir>/score.wav

Arc (seconds, from config.json timing):
  0-6.5    a confident pulse: kick on the beat, an 8th-note bass, a held chord
  6.5-11   the pulse carries the footage; a plucked arpeggio joins
  11-18    space: the beat drops out, a slow pad and three soft bell notes
  18-27.5  a controlled lift: bass pulse returns, then kick, then the pad opens
  27.5-32  resolve on D and ring out to the last frame

Four sound-design accents and no others, on the brief's moments (config
timing.accents): the number resolving, the push through 2026, "trust"
settling, the final lockup. Stdlib synthesis, mixed and mastered with ffmpeg
(convolution hall). Deterministic.
"""
import argparse
import json
import math
import pathlib
import random
import subprocess
import tempfile
import wave
from array import array

HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text(encoding="utf-8-sig"))
SR = 44100
TOTAL = CFG["film"]["duration"]
BEAT = 0.5
N = int((TOTAL + 1.0) * SR)
TAU = 2 * math.pi
rng = random.Random(2026)
midi = lambda m: 440.0 * 2 ** ((m - 69) / 12)
ACC = CFG["timing"]["accents"]

D, A, BM, G, EM, FSM = (50, 54, 57, 62), (45, 52, 57, 61), (47, 54, 59, 62), (43, 50, 55, 59), (52, 55, 59, 64), (54, 57, 61, 66)
# (start, end, chord, bass root)
CHORDS = [
    (0.0, 3.5, D, 38), (3.5, 6.5, A, 45), (6.5, 8.75, BM, 47), (8.75, 11.0, G, 43),
    (11.0, 13.0, G, 43), (13.0, 15.3, D, 42), (15.3, 18.0, EM, 40),
    (18.0, 21.1, G, 43), (21.1, 24.0, A, 45), (24.0, 26.0, BM, 47), (26.0, 27.5, A, 45),
    (27.5, TOTAL + 1.0, D, 38),
]


def chord_at(t):
    for a, b, c, r in CHORDS:
        if a <= t < b:
            return c, r
    return CHORDS[-1][2], CHORDS[-1][3]


def buf():
    return array("d", bytes(8 * N))


def place(dst, shot, t, g=1.0):
    i0 = int(t * SR)
    for k in range(min(len(shot), N - i0)):
        dst[i0 + k] += shot[k] * g


def kick():
    out, ph = array("d"), 0.0
    for k in range(int(0.4 * SR)):
        t = k / SR
        ph += (48 + 110 * math.exp(-t * 30)) / SR
        out.append(math.tanh(1.6 * math.sin(TAU * ph)) * math.exp(-t * 7.5) + (rng.random() * 2 - 1) * 0.25 * math.exp(-t * 600))
    return out


def hat():
    out, prev = array("d"), 0.0
    for k in range(int(0.08 * SR)):
        n = rng.random() * 2 - 1
        out.append((n - prev) * math.exp(-k / SR * 90))
        prev = n
    return out


def bass_note(f, dur):
    out, ph = array("d"), 0.0
    for k in range(int(dur * SR)):
        t = k / SR
        ph += f / SR
        s = math.sin(TAU * ph) + 0.35 * math.sin(2 * TAU * ph) + 0.12 * math.sin(3 * TAU * ph)
        out.append(math.tanh(1.3 * s) * min(1.0, t * 300) * math.exp(-t * 4.5) * min(1.0, (dur - t) * 60))
    return out


def pluck(f, dur=0.7):
    n = max(2, int(round(SR / f)))
    line = [rng.uniform(-1, 1) for _ in range(n)]
    out, i = array("d"), 0
    for k in range(int(dur * SR)):
        a, b = line[i], line[(i + 1) % n]
        line[i] = 0.5 * (a + b) * 0.996
        i = (i + 1) % n
        out.append(a * min(1.0, (dur - k / SR) * 30))
    return out


def bell(f, dur=2.5, idx=1.2):
    out = array("d")
    for k in range(int(dur * SR)):
        t = k / SR
        s = math.sin(TAU * f * t + idx * math.exp(-t * 4) * math.sin(TAU * 3.5 * f * t))
        out.append(s * math.exp(-t * 1.9) * min(1.0, t * 500))
    return out


def boom(dur=2.2, low=36, hi=70):
    out, ph, lp = array("d"), 0.0, 0.0
    for k in range(int(dur * SR)):
        t = k / SR
        ph += (low + hi * math.exp(-t * 6)) / SR
        lp += 0.03 * ((rng.random() * 2 - 1) - lp)
        out.append(math.sin(TAU * ph) * math.exp(-t * 2.3) + lp * 2.0 * math.exp(-t * 3.0))
    return out


def rise(dur):
    out, low, band = array("d"), 0.0, 0.0
    n = int(dur * SR)
    for k in range(n):
        x = k / n
        f = 2 * math.sin(math.pi * (300 + 6000 * x * x) / SR)
        low += f * band
        high = (rng.random() * 2 - 1) - low - 0.5 * band
        band += f * high
        out.append(band * x ** 2.2 * 0.8)
    return out


def section_gain(t, table):
    g = 0.0
    for a, b, v in table:
        if a <= t < b:
            g = v
    return g


def pad():
    """Saw pad per chord span, crossfaded, filter opening with the arc."""
    L, R = buf(), buf()
    level = [(0, 6.5, 0.55), (6.5, 11, 0.5), (11, 18, 0.85), (18, 24, 0.7), (24, 27.5, 0.9), (27.5, 40, 1.0)]
    cut = [(0, 11, 0.07), (11, 18, 0.05), (18, 24, 0.08), (24, 27.5, 0.12), (27.5, 40, 0.1)]
    for a, b, notes, _ in CHORDS:
        t0, t1 = max(0.0, a - 0.05), min(TOTAL + 0.9, b + 0.6)
        voices = [(side, midi(m + det) / SR, rng.random()) for m in notes for side, det in ((0, -0.06), (1, 0.06))]
        ph = [v[2] for v in voices]
        lpL = lpR = 0.0
        for i in range(int(t0 * SR), int(t1 * SR)):
            t = i / SR
            e = min(1.0, (t - t0) / 0.35) * (1.0 if t <= b else max(0.0, 1 - (t - b) / 0.6))
            sl = sr = 0.0
            for vi, (side, inc, _) in enumerate(voices):
                p = ph[vi] + inc
                p -= int(p)
                ph[vi] = p
                if side:
                    sr += 2 * p - 1
                else:
                    sl += 2 * p - 1
            c = section_gain(t, cut)
            lpL += c * (sl - lpL)
            lpR += c * (sr - lpR)
            g = section_gain(t, level) * e * 0.18
            L[i] += lpL * g
            R[i] += lpR * g
    return L, R


def rhythm():
    Dr, B = buf(), buf()
    K, H = kick(), hat()
    kick_on = [(0.0, 11.0), (21.1, 27.5)]
    hats_on = [(3.5, 11.0), (24.0, 27.5)]
    bass_on = [(0.0, 11.0, 1.0), (18.0, 27.5, 0.8)]
    t = 0.0
    while t < TOTAL:
        if any(a <= t < b for a, b in kick_on):
            place(Dr, K, t, 0.8)
        if any(a <= t < b for a, b in hats_on):
            place(Dr, H, t + 0.25, 0.12)
        t += BEAT
    t = 0.0
    while t < TOTAL:
        g = 0.0
        for a, b, v in bass_on:
            if a <= t < b:
                g = v
        if g:
            _, root = chord_at(t)
            place(B, bass_note(midi(root), 0.24), t, g * (1.0 if int(round(t / 0.25)) % 2 == 0 else 0.7))
        t += 0.25
    return Dr, B


def arps():
    L, R = buf(), buf()
    for span, g in (((6.5, 11.0), 0.5), ((24.0, 27.5), 0.4)):
        t, k = span[0], 0
        while t < span[1] - 0.01:
            notes, _ = chord_at(t)
            m = (notes[1:] + (notes[0] + 12,))[k % 4] + 12
            s = pluck(midi(m))
            place(L if k % 2 else R, s, t, g)
            place(R if k % 2 else L, s, t + 0.012, g * 0.5)
            t += 0.25
            k += 1
    for t, m in ((11.2, 78), (13.2, 74), (15.5, 76)):  # three bells in the trust section
        s = bell(midi(m), 3.0, 0.9)
        place(L, s, t, 0.35)
        place(R, s, t + 0.015, 0.3)
    return L, R


def accents():
    Lx, Rx = buf(), buf()
    a1, a2, a3, a4 = ACC
    # 1: the number resolves — low thump and a bright D chord ping
    for b in (boom(1.6, 38, 60),):
        place(Lx, b, a1, 0.55); place(Rx, b, a1, 0.55)
    for j, m in enumerate((74, 78, 81)):
        s = bell(midi(m), 1.6, 1.6)
        place(Lx, s, a1 + 0.01 * j, 0.22); place(Rx, s, a1 + 0.012 * j, 0.22)
    # 2: through 2026 — a short rise into a soft boom
    r = rise(0.9)
    place(Lx, r, a2 - 0.9, 0.5); place(Rx, r, a2 - 0.9, 0.5)
    b = boom(2.0, 34, 50)
    place(Lx, b, a2, 0.5); place(Rx, b, a2, 0.5)
    # 3: trust settles — a warm low swell and one bell
    b = boom(2.4, 30, 25)
    place(Lx, b, a3, 0.35); place(Rx, b, a3, 0.35)
    s = bell(midi(74), 3.0, 0.7)
    place(Lx, s, a3, 0.3); place(Rx, s, a3 + 0.02, 0.3)
    # 4: the lockup — boom plus a D major chime
    b = boom(2.6, 36, 64)
    place(Lx, b, a4, 0.6); place(Rx, b, a4, 0.6)
    for j, m in enumerate((74, 78, 81, 86)):
        s = bell(midi(m), 3.4, 1.3)
        place(Lx if j % 2 else Rx, s, a4 + 0.015 * j, 0.24)
        place(Rx if j % 2 else Lx, s, a4 + 0.015 * j + 0.01, 0.16)
    return Lx, Rx


def hall(seconds=2.6, rt60=2.4):
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    out = pathlib.Path(ap.parse_args().out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        drums, bass = rhythm()
        stems = {"pad": pad(), "drums": (drums,), "bass": (bass,), "arps": arps(), "acc": accents()}
        for nm, ch in stems.items():
            write(td / f"{nm}.wav", list(ch))
        write(td / "ir.wav", list(hall()))
        lv = {"pad": 0.55, "drums": 0.7, "bass": 0.5, "arps": 0.42, "acc": 0.75}
        fc = (
            "[0]volume={pad},asplit[p][ps];"
            "[1]aformat=channel_layouts=stereo,volume={drums}[d];"
            "[2]aformat=channel_layouts=stereo,volume={bass}[b];"
            "[3]volume={arps},asplit[a][as];"
            "[4]volume={acc},asplit[x][xs];"
            "[ps]volume=0.5[s1];[as]volume=0.6[s2];[xs]volume=0.4[s3];"
            "[s1][s2][s3]amix=inputs=3:normalize=0[send];"
            "[send][5]afir=dry=0:wet=1:length=1:gtype=peak,volume=0.5[rev];"
            "[p][d][b][a][x][rev]amix=inputs=6:normalize=0,"
            "highpass=f=32,bass=g=-3:f=100,equalizer=f=2200:width_type=o:width=1.6:g=2,"
            "acompressor=threshold=-18dB:ratio=2.5:attack=12:release=180:makeup=2,"
            "loudnorm=I=-13:TP=-1.5:LRA=9,aresample=48000,"
            f"atrim=0:{TOTAL:.3f},afade=t=out:st={TOTAL - 0.6:.3f}:d=0.6,alimiter=limit=0.84:level=disabled"
        ).format(**lv)
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
        for nm in stems:
            cmd += ["-i", str(td / f"{nm}.wav")]
        cmd += ["-i", str(td / "ir.wav"), "-filter_complex", fc, "-c:a", "pcm_s16le", str(out)]
        subprocess.run(cmd, check=True)
    print(f"wrote {out} ({TOTAL:.0f}s)")


if __name__ == "__main__":
    main()
