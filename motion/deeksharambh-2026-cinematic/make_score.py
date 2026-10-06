#!/usr/bin/env python3
"""Synthesize the cinematic Deeksharambh 2026 score: 80 BPM, 10 bars, 30 s, D minor -> F major.

Usage: motion/deeksharambh-2026-cinematic/make_score.py --out <dir>/score.wav

Stdlib synthesis mixed with ffmpeg: string pad (crossfaded per bar, opening
filter), sub drone, an 8th-note string pulse under the faces and the trust line,
FM bells on the words that matter, toms, braam impacts on every scene change,
risers into 6, 12 and 24 s, a chime when the logo's ellipse lands at 25.5 s,
and a shimmer over the end card. Reverb is a synthetic 3 s hall IR through
ffmpeg afir. Deterministic (fixed seed).

Scene map it is written against: A 0-6, B 6-12, C 12-18, D 18-24, E 24-30.
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
BPM = 80
BEAT = 60 / BPM          # 0.75 s
BAR = 4 * BEAT           # 3 s
BARS = 10
TOTAL = BARS * BAR       # 30 s
N = int((TOTAL + 2.0) * SR)
TAU = 2 * math.pi
rng = random.Random(2026)
midi = lambda m: 440.0 * 2 ** ((m - 69) / 12)

DM, BB, F, C = (50, 53, 57, 62), (46, 50, 53, 58), (53, 57, 60, 65), (48, 52, 55, 60)
CHORDS = [DM, BB, F, C, DM, BB, F, C, BB, F]
ROOTS = [38, 34, 41, 36, 38, 34, 41, 36, 34, 41]
PAD_GAIN = [0.5, 0.62, 0.7, 0.75, 0.85, 0.9, 0.82, 0.82, 1.0, 1.0]
PAD_CUT = [0.075, 0.085, 0.105, 0.115, 0.15, 0.17, 0.13, 0.135, 0.19, 0.155]  # one-pole coefs, ~0.6-2.5 kHz
DRONE = [1.0, 1.0, 0.7, 0.7, 0.85, 0.9, 0.6, 0.6, 1.0, 0.9]
PULSE = [0, 0, 0.55, 0.72, 0.9, 1.0, 0.42, 0.5, 0, 0]


def buf():
    return array("d", bytes(8 * N))


def place(dst, shot, t, gain=1.0):
    i0 = int(t * SR)
    n = min(len(shot), N - i0)
    for k in range(n):
        dst[i0 + k] += shot[k] * gain


def env_bar(t, b, attack=0.5, release=1.0):
    """Envelope of bar b's chord at time t: fades in from its downbeat, rings past the next one."""
    t0, t1 = b * BAR, (b + 1) * BAR
    if b == BARS - 1:
        t1 = TOTAL + 0.5
    if t < t0 - 0.05 or t > t1 + release:
        return 0.0
    a = min(1.0, max(0.0, (t - t0 + 0.05) / attack))
    r = 1.0 if t <= t1 else max(0.0, 1 - (t - t1) / release)
    return a * r


# ---------- layers ----------
def pad():
    L, R = buf(), buf()
    for b, chord in enumerate(CHORDS):
        t_start, t_end = max(0.0, b * BAR - 0.05), min(TOTAL + 1.5, (b + 1) * BAR + 1.0)
        i0, i1 = int(t_start * SR), int(t_end * SR)
        voices = []
        for m in chord:
            for side, det in ((0, -0.07), (0, 0.05), (1, 0.07), (1, -0.05)):
                voices.append((side, midi(m + det) / SR, rng.random()))
        g = PAD_GAIN[b] / len(chord)
        phases = [v[2] for v in voices]
        for i in range(i0, i1):
            e = env_bar(i / SR, b) * g
            if e <= 0:
                for vi, (side, inc, _) in enumerate(voices):
                    phases[vi] = (phases[vi] + inc) % 1.0
                continue
            sl = sr = 0.0
            for vi, (side, inc, _) in enumerate(voices):
                ph = phases[vi] + inc
                ph -= int(ph)
                phases[vi] = ph
                v = 2 * ph - 1
                if side:
                    sr += v
                else:
                    sl += v
            L[i] += sl * e
            R[i] += sr * e
    # one-pole lowpass whose cutoff follows the section, smoothed
    for ch in (L, R):
        lp = 0.0
        lp2 = 0.0
        cut = PAD_CUT[0]
        for i in range(N):
            b = min(BARS - 1, int(i / SR / BAR))
            cut += (PAD_CUT[b] - cut) * 0.00002
            lp += cut * (ch[i] - lp)
            lp2 += cut * (lp - lp2)
            ch[i] = lp2
    return L, R


def drone():
    D = buf()
    ph1 = ph2 = 0.0
    for i in range(N):
        t = i / SR
        b = min(BARS - 1, int(t / BAR))
        # crossfade roots over the first 0.4 s of each bar
        x = (t - b * BAR) / 0.4
        f = midi(ROOTS[b])
        if x < 1 and b > 0:
            f = midi(ROOTS[b - 1]) + (f - midi(ROOTS[b - 1])) * (0.5 - 0.5 * math.cos(math.pi * x))
        ph1 += f / SR
        ph2 += 2 * f / SR
        g = DRONE[b]
        if t > TOTAL - 1.5:
            g *= max(0.0, (TOTAL + 0.3 - t) / 1.8)
        sw = 0.85 + 0.15 * math.sin(TAU * t / 6)
        D[i] = (math.sin(TAU * ph1) * 0.8 + math.sin(TAU * ph2) * 0.35) * g * sw * min(1.0, t / 0.08)
    return D


def pluck(f, dur=0.36):
    out, ph, lp = array("d"), 0.0, 0.0
    for k in range(int(dur * SR)):
        t = k / SR
        ph += f / SR
        ph -= int(ph)
        cut = 0.05 + 0.35 * math.exp(-t * 14)
        lp += cut * ((2 * ph - 1) - lp)
        out.append(lp * math.exp(-t * 7) * min(1.0, t * 600))
    return out


def pulse():
    L, R = buf(), buf()
    cache = {}
    for b, chord in enumerate(CHORDS):
        if not PULSE[b]:
            continue
        root, third, fifth = chord[0] - 12, chord[1] - 12, chord[2] - 12
        seq = [root, fifth, root + 12, fifth, root, fifth, root + 12, third + 12]
        sub = 16 if b in (4, 5) else 8
        for q in range(sub):
            m = seq[(q if sub == 8 else q // 2) % 8]
            if m not in cache:
                cache[m] = pluck(midi(m))
            ts = b * BAR + q * BAR / sub
            acc = 1.0 if q % (sub // 4) == 0 else 0.7
            g = PULSE[b] * acc * (0.55 if sub == 16 else 0.75)
            place(L, cache[m], ts, g * (1.0 if q % 2 else 0.8))
            place(R, cache[m], ts + 0.004, g * (0.8 if q % 2 else 1.0))
    return L, R


def bell(f, dur=1.6, bright=1.4):
    out = array("d")
    for k in range(int(dur * SR)):
        t = k / SR
        idx = bright * math.exp(-t * 5)
        s = math.sin(TAU * f * t + idx * math.sin(TAU * 3.5 * f * t)) * 0.7
        s += 0.25 * math.sin(TAU * 2.0 * f * t) * math.exp(-t * 4)
        out.append(s * math.exp(-t * 2.6) * min(1.0, t * 500))
    return out


MELODY = [
    (0.0, 74, 1.5, 0.9), (1.5, 69, 0.9, 0.6), (2.25, 77, 0.9, 0.7), (3.0, 76, 1.5, 0.75), (4.5, 74, 1.6, 0.7),
    (6.75, 81, 1.4, 0.55), (8.25, 79, 1.0, 0.5), (8.6, 77, 1.6, 0.6),
    (12.75, 72, 1.2, 0.55), (13.5, 74, 1.2, 0.55), (15.0, 77, 2.0, 0.8), (15.0, 81, 2.0, 0.6), (15.75, 76, 1.4, 0.5),
    (18.75, 77, 1.6, 0.75), (19.5, 76, 0.9, 0.55), (20.25, 72, 1.6, 0.65), (21.0, 74, 0.9, 0.55),
    (21.75, 77, 0.9, 0.6), (22.5, 79, 1.8, 0.7),
    (27.0, 77, 2.4, 0.6), (28.5, 81, 2.4, 0.45), (29.25, 84, 2.0, 0.35),
]


def bells():
    L, R = buf(), buf()
    for n, (t, m, dur, g) in enumerate(MELODY):
        shot = bell(midi(m), dur + 1.0)
        pan = 0.62 if n % 2 else 0.38
        place(L, shot, t, g * (1 - pan) * 1.4)
        place(R, shot, t, g * pan * 1.4)
    # the ellipse chime and the end-card shimmer
    for m, g in ((89, 0.55), (93, 0.45), (96, 0.35), (101, 0.22)):
        shot = bell(midi(m), 2.6, 2.2)
        place(L, shot, 25.5, g)
        place(R, shot, 25.52, g)
    arp = [70, 74, 77, 82, 77, 74] * 2 + [65, 69, 72, 77, 72, 69] * 3
    for q, m in enumerate(arp):
        t = 24.0 + 0.1875 + q * 0.1875
        if t > 29.0:
            break
        shot = bell(midi(m + 12), 0.9, 0.8)
        g = 0.13 * min(1.0, (t - 24.0) / 1.5)
        place(L if q % 2 else R, shot, t, g)
        place(R if q % 2 else L, shot, t + 0.28, g * 0.45)
    return L, R


def tom(f0=110, dur=0.7):
    out, ph, lp = array("d"), 0.0, 0.0
    for k in range(int(dur * SR)):
        t = k / SR
        ph += (f0 * (0.62 + 0.38 * math.exp(-t * 9))) / SR
        lp += 0.08 * ((rng.random() * 2 - 1) - lp)
        out.append(math.sin(TAU * ph) * math.exp(-t * 5.5) + lp * 1.6 * math.exp(-t * 20))
    return out


def braam(root, dur=3.2, drive=2.2):
    """Low saw cluster with a fast swell and a slow, closing filter: the trailer 'braam'."""
    out = array("d")
    fs = [midi(root - 12), midi(root - 12 + 7), midi(root), midi(root - 12) * 1.004]
    phs = [0.0] * 4
    lp = lp2 = 0.0
    for k in range(int(dur * SR)):
        t = k / SR
        s = 0.0
        for j, f in enumerate(fs):
            phs[j] = (phs[j] + f / SR) % 1.0
            s += 2 * phs[j] - 1
        s = math.tanh(drive * s / 4)
        cut = 0.02 + 0.16 * math.exp(-t * 2.2) * min(1.0, t * 12)
        lp += cut * (s - lp)
        lp2 += cut * (lp - lp2)
        e = min(1.0, t * 20) * math.exp(-t * 1.1)
        out.append(lp2 * e)
    return out


def boom(dur=2.4):
    out, ph, lp = array("d"), 0.0, 0.0
    for k in range(int(dur * SR)):
        t = k / SR
        ph += (32 + 58 * math.exp(-t * 5)) / SR
        lp += 0.03 * ((rng.random() * 2 - 1) - lp)
        out.append(math.sin(TAU * ph) * math.exp(-t * 1.8) + lp * 3.0 * math.exp(-t * 2.6))
    return out


def riser(dur, peak=1.0):
    out, low, band = array("d"), 0.0, 0.0
    n = int(dur * SR)
    for k in range(n):
        x = k / n
        fc = 250 + 6500 * x ** 2.2
        f = 2 * math.sin(math.pi * fc / SR)
        low += f * band
        high = (rng.random() * 2 - 1) - low - 0.4 * band
        band += f * high
        tone = 0.35 * math.sin(TAU * (90 + 500 * x ** 2) * k / SR)
        out.append((band * 0.8 + tone * x) * x ** 1.8 * peak)
    return out


def perc():
    P = buf()
    for t, root, g in ((0.0, 50, 0.9), (6.0, 46, 1.0), (12.0, 50, 1.0), (24.0, 46, 1.15)):
        place(P, braam(root), t, 0.8 * g)
        place(P, boom(), t, 0.9 * g)
    place(P, boom(1.8), 15.0, 0.55)
    place(P, braam(53, 2.4, 1.6), 18.0, 0.35)
    for t, d in ((4.0, 2.0), (10.0, 2.0), (22.0, 2.0)):
        place(P, riser(d), t, 0.55)
    T1, T2 = tom(105), tom(78, 0.9)
    for b in (4, 5):
        for beat in (0, 2):
            place(P, T2 if beat == 0 else T1, b * BAR + beat * BEAT, 0.5)
    for q, t in enumerate((17.25, 17.4375, 17.625, 17.8125)):
        place(P, T1, t, 0.25 + 0.08 * q)
    return P


def hall_ir(seconds=3.2, rt60=3.0):
    L, R = array("d"), array("d")
    decay = 6.91 / rt60
    lpL = lpR = 0.0
    for k in range(int(seconds * SR)):
        t = k / SR
        e = math.exp(-decay * t) * min(1.0, t * 300)
        a = 0.35 + 0.6 * math.exp(-t * 1.2)  # darker tail
        lpL += a * ((rng.random() * 2 - 1) - lpL)
        lpR += a * ((rng.random() * 2 - 1) - lpR)
        L.append(lpL * e)
        R.append(lpR * e)
    for d, g in ((0.011, 0.6), (0.019, 0.45), (0.027, 0.35)):
        i = int(d * SR)
        L[i] += g
        R[i + 7] += g
    return L, R


def write(path, chans, n=None):
    n = n or len(chans[0])
    peak = max(1e-9, max(max(abs(v) for v in c[:n]) for c in chans))
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
        stems = {"pad": pad(), "drone": (drone(),), "pulse": pulse(), "bells": bells(), "perc": (perc(),)}
        for nm, ch in stems.items():
            write(td / f"{nm}.wav", list(ch))
            print(f"stem {nm}")
        irL, irR = hall_ir()
        write(td / "ir.wav", [irL, irR])
        lv = {"pad": 0.6, "drone": 0.28, "pulse": 0.45, "bells": 0.55, "perc": 0.8}
        fc = (
            "[0]volume={pad},asplit[pd][ps];"
            "[1]aformat=channel_layouts=stereo,volume={drone}[dr];"
            "[2]volume={pulse},asplit[pu][pus];"
            "[3]volume={bells},asplit[be][bes];"
            "[4]aformat=channel_layouts=stereo,volume={perc},asplit[pe][pes];"
            "[ps]volume=0.55[s1];[pus]volume=0.5[s2];[bes]volume=0.95[s3];[pes]volume=0.3[s4];"
            "[s1][s2][s3][s4]amix=inputs=4:normalize=0[send];"
            "[send][5]afir=dry=0:wet=1:length=1:gtype=peak,volume=0.5[rev];"
            "[pd][dr][pu][be][pe][rev]amix=inputs=6:normalize=0,"
            "highpass=f=32,bass=g=-6:f=120,equalizer=f=1500:width_type=o:width=1.6:g=3,treble=g=2.5:f=4000,"
            "acompressor=threshold=-16dB:ratio=2:attack=20:release=250:makeup=1.5,"
            "loudnorm=I=-12.5:TP=-1.5:LRA=11,aresample=48000,"
            f"atrim=0:{TOTAL:.3f},afade=t=out:st={TOTAL - 1.6:.3f}:d=1.6,alimiter=limit=0.84:level=disabled"
        ).format(**lv)
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
        for nm in stems:
            cmd += ["-i", str(td / f"{nm}.wav")]
        cmd += ["-i", str(td / "ir.wav"), "-filter_complex", fc, "-c:a", "pcm_s16le", str(out)]
        subprocess.run(cmd, check=True)
    print(f"wrote {out} ({TOTAL:.0f}s @ {BPM} BPM)")


if __name__ == "__main__":
    main()
