#!/usr/bin/env python3
"""Synthesize the Deeksharambh 2026 recap's music bed: 120 BPM, 20 bars, 40 s.

Usage: motion/deeksharambh-2026/make_music.py --out <dir>/music.wav

Stdlib-only synthesis (one-shots placed on a beat grid, phase-continuous pad
voices, bell-FM arp with ping-pong delay), mixed and mastered with ffmpeg.
The arrangement is written against the composition's scene map, so cuts land
on downbeats: hook 0-6, drop 6 (scale wall), break 12 (event card), groove 16
(contrast), build 24-28 (meaning), drop 28 (welcome), end card 36.
Deterministic: fixed RNG seed, same file every run.
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
BARS = 20
TOTAL = BARS * BAR
N = int(TOTAL * SR) + SR  # one second of tail room, trimmed by ffmpeg
TAU = 2 * math.pi
rng = random.Random(2026)

midi = lambda m: 440.0 * 2 ** ((m - 69) / 12)

# vi-IV-I-V in D; the last two bars resolve on D.
CHORDS = [(59, 62, 66), (55, 59, 62), (57, 62, 66), (57, 61, 64)]
BASS = [47, 43, 50, 45]
FINAL = (57, 62, 66)


def chord_of(bar):
    return FINAL if bar >= 18 else CHORDS[bar % 4]


def bass_of(bar):
    return 50 if bar >= 18 else BASS[bar % 4]


# Section plan per bar: which layers play and how loud.
def section(bar):
    if bar <= 2:
        return dict(kick=1, clap=0, hats=8, bass=0.6, pad=0.55, arp=0.55, cut=0.35)
    if bar <= 5:
        return dict(kick=1, clap=1, hats=16, bass=1.0, pad=0.8, arp=0.8, cut=1.0)
    if bar <= 7:
        return dict(kick=0, clap=0, hats=0, bass=0.5, pad=1.0, arp=0.7, cut=0.5)
    if bar <= 11:
        return dict(kick=1, clap=1, hats=8, bass=0.9, pad=0.7, arp=0.55, cut=0.8)
    if bar <= 13:
        return dict(kick=0, clap=0, hats=0, bass=0.4, pad=1.0, arp=0.8, cut=0.45)
    if bar <= 17:
        return dict(kick=1, clap=1, hats=16, bass=1.0, pad=0.85, arp=0.9, cut=1.0)
    return dict(kick=0, clap=0, hats=0, bass=0.5, pad=1.0, arp=0.0, cut=0.4)


def buf():
    return array("d", bytes(8 * N))


def place(dst, shot, t, gain=1.0):
    i0 = int(t * SR)
    n = min(len(shot), N - i0)
    for k in range(n):
        dst[i0 + k] += shot[k] * gain


# ---------- one-shots ----------
def kick():
    out, ph = array("d"), 0.0
    for k in range(int(0.42 * SR)):
        t = k / SR
        f = 48 + 110 * math.exp(-t * 28)
        ph += TAU * f / SR
        env = math.exp(-t * 7.5)
        click = math.exp(-t * 400) * 0.5
        out.append(math.tanh(1.8 * math.sin(ph)) * env + click * (rng.random() * 2 - 1))
    return out


def clap():
    out, lp = array("d"), 0.0
    for k in range(int(0.3 * SR)):
        t = k / SR
        burst = sum(math.exp(-(t - d) * 90) for d in (0.0, 0.011, 0.022) if t >= d)
        tail = math.exp(-t * 16) * 0.6
        n = rng.random() * 2 - 1
        hp = n - lp
        lp += 0.35 * (n - lp)
        out.append(hp * (burst * 0.5 + tail) + 0.25 * math.sin(TAU * 190 * t) * math.exp(-t * 40))
    return out


def hat(decay):
    out, prev = array("d"), 0.0
    for k in range(int(0.12 * SR)):
        t = k / SR
        n = rng.random() * 2 - 1
        out.append((n - prev) * math.exp(-t * decay))
        prev = n
    return out


def bell(f, dur=0.32):
    out = array("d")
    for k in range(int(dur * SR)):
        t = k / SR
        idx = 1.4 * math.exp(-t * 9)
        s = math.sin(TAU * f * t + idx * math.sin(TAU * 2 * f * t))
        out.append(s * math.exp(-t * 9) * min(1.0, t * 400))
    return out


def impact(dur=2.2):
    out, ph, lp = array("d"), 0.0, 0.0
    for k in range(int(dur * SR)):
        t = k / SR
        f = 34 + 70 * math.exp(-t * 6)
        ph += TAU * f / SR
        n = rng.random() * 2 - 1
        lp += 0.04 * (n - lp)
        out.append(math.sin(ph) * math.exp(-t * 2.2) + lp * 2.5 * math.exp(-t * 3.5))
    return out


def sweep(dur, up=True, peak=0.9):
    """Filtered-noise riser (up) or whoosh (down) through a state-variable bandpass."""
    out, low, band = array("d"), 0.0, 0.0
    n_s = int(dur * SR)
    for k in range(n_s):
        x = k / n_s
        fc = 300 + 7000 * (x ** 2 if up else (1 - x) ** 1.5)
        f = 2 * math.sin(math.pi * fc / SR)
        n = rng.random() * 2 - 1
        low += f * band
        high = n - low - 0.5 * band
        band += f * high
        env = (x ** 1.6) if up else math.sin(math.pi * min(1.0, x * 1.6)) ** 2
        tone = 0.3 * math.sin(TAU * (200 + 600 * x * x) * k / SR) * x if up else 0.0
        out.append((band * 0.9 + tone) * env * peak)
    return out


# ---------- stems ----------
def drums():
    L = buf()
    K, C, Hc, Ho = kick(), clap(), hat(90), hat(30)
    for bar in range(BARS):
        s = section(bar)
        t0 = bar * BAR
        for b in range(4):
            tb = t0 + b * BEAT
            if s["kick"]:
                place(L, K, tb, 0.95)
            if s["clap"] and b in (1, 3):
                place(L, C, tb, 0.55)
        if s["hats"] == 8:
            for b in range(4):
                place(L, Ho, t0 + b * BEAT + BEAT / 2, 0.16)
        elif s["hats"] == 16:
            for q in range(16):
                accent = 0.17 if q % 2 else 0.08
                place(L, Hc if q % 4 != 2 else Ho, t0 + q * BEAT / 4, accent)
    # Snare-roll build into the 28 s drop (bar 13), accelerating.
    t = 13 * BAR
    for step, div in ((0, 4), (1, 4), (2, 8), (3, 16)):
        n = div
        for q in range(n):
            g = 0.18 + 0.32 * ((step * n + q) / (4 * 16))
            place(L, C, 13 * BAR + step * BEAT + q * BEAT / n, g)
    return L


def bass():
    L = buf()
    for bar in range(BARS):
        s = section(bar)
        if not s["bass"]:
            continue
        f = midi(bass_of(bar))
        pumping = s["kick"]
        for e in range(8):
            if pumping and e % 2 == 0:
                continue  # off-beat bass, kick owns the downbeat
            ts = bar * BAR + e * BEAT / 2
            dur = BEAT / 2 if pumping else BEAT / 2 * 0.98
            i0, n = int(ts * SR), int(dur * SR)
            for k in range(n):
                t = k / SR
                env = min(1.0, t * 300) * min(1.0, (dur - t) * 60)
                v = 0.7 * math.sin(TAU * f * t) + 0.35 * math.sin(TAU * f / 2 * t)
                v += 0.18 * math.sin(TAU * 2 * f * t)
                L[i0 + k] += math.tanh(1.6 * v) * env * s["bass"] * 0.55
    return L


def pad():
    L, R = buf(), buf()
    detune = (-0.11, 0.09)  # semitones, one detuned voice per side
    phases = [[0.0] * 3 for _ in range(2)]
    lpL = lpR = 0.0
    kick_times = []
    for bar in range(BARS):
        if section(bar)["kick"]:
            kick_times += [bar * BAR + b * BEAT for b in range(4)]
    kick_set = sorted(kick_times)
    ki = 0
    for i in range(N):
        t = i / SR
        bar = min(BARS - 1, int(t / BAR))
        s = section(bar)
        notes = chord_of(bar)
        gain = s["pad"]
        if t > TOTAL - 4:
            gain *= max(0.0, (TOTAL + 0.6 - t) / 4.6)
        while ki + 1 < len(kick_set) and kick_set[ki + 1] <= t:
            ki += 1
        duck = 1.0
        if kick_set and kick_set[ki] <= t < kick_set[ki] + BEAT:
            d = (t - kick_set[ki]) / BEAT
            duck = 0.35 + 0.65 * min(1.0, d * 2.2)
        cutoff = 0.03 + 0.09 * s["cut"]
        outs = []
        for side in range(2):
            acc = 0.0
            for v, m in enumerate(notes):
                f = midi(m + detune[side])
                ph = phases[side][v] + f / SR
                ph -= int(ph)
                phases[side][v] = ph
                acc += 2 * ph - 1
            outs.append(acc / 3)
        lpL += cutoff * (outs[0] - lpL)
        lpR += cutoff * (outs[1] - lpR)
        fade_in = min(1.0, t / 0.08)
        L[i] = lpL * gain * duck * fade_in * 0.6
        R[i] = lpR * gain * duck * fade_in * 0.6
    return L, R


def arp():
    L, R = buf(), buf()
    pattern = (0, 1, 2, 3, 2, 1, 2, 3, 0, 1, 2, 3, 2, 3, 2, 1)
    cache = {}
    for bar in range(BARS):
        s = section(bar)
        if not s["arp"]:
            continue
        notes = chord_of(bar)
        tones = [notes[0] + 12, notes[1] + 12, notes[2] + 12, notes[0] + 24]
        for q, p in enumerate(pattern):
            m = tones[p]
            if m not in cache:
                cache[m] = bell(midi(m))
            ts = bar * BAR + q * BEAT / 4
            g = s["arp"] * (0.34 if q % 4 == 0 else 0.24)
            place(L, cache[m], ts, g)
            place(R, cache[m], ts, g)
    # Ping-pong dotted-eighth delay.
    d = int(0.75 * BEAT * SR)
    for i in range(d, N):
        L[i] += 0.32 * R[i - d]
    for i in range(d, N):
        R[i] += 0.32 * L[i - d] * 0.9
    return L, R


def fx():
    L = buf()
    place(L, impact(1.6), 0.0, 0.5)
    place(L, sweep(2.0, up=True), 4.0, 0.55)
    place(L, impact(), 6.0, 0.9)
    place(L, sweep(0.7, up=False), 8.9, 0.4)
    place(L, impact(), 12.0, 0.75)
    place(L, sweep(1.0, up=True), 15.0, 0.4)
    place(L, sweep(0.7, up=False), 23.8, 0.35)
    place(L, sweep(2.0, up=True), 26.0, 0.6)
    place(L, impact(), 28.0, 0.95)
    place(L, impact(2.6), 36.0, 0.8)
    return L


def write(path, chans):
    peak = max(1e-9, max(max(abs(v) for v in c) for c in chans))
    scale = 0.9 / peak
    with wave.open(str(path), "wb") as w:
        w.setnchannels(len(chans))
        w.setsampwidth(2)
        w.setframerate(SR)
        frames = array("h")
        for i in range(N):
            for c in chans:
                frames.append(int(max(-1.0, min(1.0, c[i] * scale)) * 32767))
        w.writeframes(frames.tobytes())
    return scale


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    out = pathlib.Path(ap.parse_args().out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        stems = {
            "drums": [drums()],
            "bass": [bass()],
            "pad": list(pad()),
            "arp": list(arp()),
            "fx": [fx()],
        }
        gains = {}
        for name, chans in stems.items():
            gains[name] = write(td / f"{name}.wav", chans)
            print(f"stem {name}: {len(chans)}ch")
        # Stems are peak-normalized; these levels set the balance.
        level = {"drums": 0.9, "bass": 0.75, "pad": 0.55, "arp": 0.45, "fx": 0.6}
        fc = (
            "[0]aformat=channel_layouts=stereo,volume={drums}[d];"
            "[1]aformat=channel_layouts=stereo,volume={bass}[b];"
            "[2]volume={pad},aecho=0.8:0.6:60|113|171:0.32|0.24|0.16[p];"
            "[3]volume={arp},aecho=0.8:0.5:83|149:0.25|0.15[a];"
            "[4]aformat=channel_layouts=stereo,volume={fx},aecho=0.8:0.55:97|181:0.3|0.2[f];"
            "[d][b][p][a][f]amix=inputs=5:normalize=0,"
            "highpass=f=28,acompressor=threshold=-14dB:ratio=2.5:attack=10:release=160:makeup=2,"
            "loudnorm=I=-14:TP=-1.5:LRA=9,alimiter=limit=0.84,"
            f"atrim=0:{TOTAL:.3f},afade=t=out:st={TOTAL - 1.2:.3f}:d=1.2,aresample=48000"
        ).format(**level)
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
            + sum((["-i", str(td / f"{n}.wav")] for n in stems), [])
            + ["-filter_complex", fc, "-c:a", "pcm_s16le", str(out)],
            check=True,
        )
    print(f"wrote {out} ({TOTAL:.1f}s @ {BPM} BPM)")


if __name__ == "__main__":
    main()
