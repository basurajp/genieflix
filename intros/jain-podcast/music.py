#!/usr/bin/env python3
"""Synthesise the original 12-second JAIN PODCAST intro cue (stdlib only).

100 BPM, 4/4, five bars (bar = 2.4 s), so the bar lines land on the visual
phase changes at 2.4 / 4.8 / 7.2 / 9.6 s. Progression vi-IV-ii-V-I in F major
(Dm9 | Bbmaj9 | Gm9 | C9sus | Fmaj9). Every event is placed on the beat grid
below; index.html mirrors the same grid for its audio-reactive waveform.

    python3 intros/jain-podcast/music.py            # -> assets/audio/cue.wav

Writes a dry stereo mix, then ffmpeg two-pass loudnorm (-16 LUFS, -1.5 dBTP)
and a 0.7 s fade so the cue ends with the picture instead of truncating.
"""

import array
import json
import math
import pathlib
import random
import subprocess
import wave

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "assets" / "audio" / "cue.wav"

SR = 48000
DUR = 12.0
N = int(SR * DUR)
BEAT = 0.6           # 100 BPM
S16 = BEAT / 4       # sixteenth note
BAR = BEAT * 4       # 2.4 s
TWO_PI = 2 * math.pi

rng = random.Random(20261005)  # fixed seed: the cue is identical on every run


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def at(bar, sixteenth=0.0):
    return bar * BAR + sixteenth * S16


class Bus:
    """A stereo float buffer with constant-power panning."""

    def __init__(self):
        self.l = array.array("d", bytes(8 * N))
        self.r = array.array("d", bytes(8 * N))

    def add(self, t0, samples, pan=0.0, gain=1.0, duck=None):
        start = int(t0 * SR)
        a = (pan + 1) * math.pi / 4
        gl, gr = math.cos(a) * gain, math.sin(a) * gain
        l, r = self.l, self.r
        for i, s in enumerate(samples):
            j = start + i
            if j < 0:
                continue
            if j >= N:
                break
            if duck is not None:
                s *= duck[j]
            l[j] += s * gl
            r[j] += s * gr

    def add_stereo(self, t0, left, right, gain=1.0):
        start = int(t0 * SR)
        for i in range(len(left)):
            j = start + i
            if 0 <= j < N:
                self.l[j] += left[i] * gain
                self.r[j] += right[i] * gain


# ---------------------------------------------------------------- voices

def env_adsr(n, attack, release, total):
    """Linear attack, flat hold, cosine release over `release` seconds at the end."""
    a, r = int(attack * SR), int(release * SR)
    out = [1.0] * n
    for i in range(min(a, n)):
        out[i] = i / a
    for i in range(r):
        k = n - r + i
        if 0 <= k < n:
            out[k] *= 0.5 + 0.5 * math.cos(math.pi * i / r)
    return out


def pulse(f, length=2.6):
    """Soft tonal pulse: sine + octave, 6 ms attack, long exponential tail."""
    n = int(length * SR)
    w1, w2 = TWO_PI * f / SR, TWO_PI * 2 * f / SR
    out = []
    for i in range(n):
        t = i / SR
        e = min(1.0, t / 0.006) * math.exp(-t / 0.75)
        out.append(e * (math.sin(w1 * i) + 0.22 * math.sin(w2 * i) * math.exp(-t / 0.2)))
    return out


def pad_note(f, length, detune_cents):
    """Warm pad voice: sine + soft 2nd/3rd partials, slow attack."""
    n = int(length * SR)
    ff = f * 2 ** (detune_cents / 1200)
    w = TWO_PI * ff / SR
    env = env_adsr(n, 0.45, 0.7, length)
    return [env[i] * (math.sin(w * i) + 0.18 * math.sin(2 * w * i) + 0.07 * math.sin(3 * w * i))
            for i in range(n)]


def bass_note(f, length):
    """Additive saw whose upper partials decay like a closing low-pass filter."""
    n = int(length * SR)
    w = TWO_PI * f / SR
    out = []
    rel = int(0.03 * SR)
    for i in range(n):
        t = i / SR
        bright = 0.25 + 1.6 * (1 - math.exp(-t / 0.09))     # filter closes over 90 ms
        s = 0.0
        for k in range(1, 7):
            s += math.sin(w * k * i) / k * math.exp(-(k - 1) * bright)
        e = min(1.0, t / 0.004) * (0.62 + 0.38 * math.exp(-t / 0.12))
        if i > n - rel:
            e *= (n - i) / rel
        out.append(s * e)
    return out


def kick(vel=1.0, length=0.55):
    n = int(length * SR)
    out, ph = [], 0.0
    for i in range(n):
        t = i / SR
        f = 46 + 84 * math.exp(-t / 0.04)
        ph += TWO_PI * f / SR
        click = math.exp(-t / 0.0025) * 0.35
        out.append(vel * (math.sin(ph) * math.exp(-t / 0.26) + click * math.sin(ph * 6)))
    return out


def clap(vel=1.0, length=0.35):
    n = int(length * SR)
    out, lp = [], 0.0
    for i in range(n):
        t = i / SR
        x = rng.uniform(-1, 1)
        lp += 0.25 * (x - lp)
        hp = x - lp                                          # crude high-pass
        bursts = sum(math.exp(-(t - d) / 0.006) for d in (0.0, 0.011, 0.022) if t >= d)
        e = 0.45 * bursts + math.exp(-max(0.0, t - 0.022) / 0.11) * (t >= 0.022)
        body = 0.35 * math.sin(TWO_PI * 190 * t) * math.exp(-t / 0.05)
        out.append(vel * (hp * e * 0.55 + body))
    return out


def hat(vel=1.0, length=0.09):
    n = int(length * SR)
    out, lp = [], 0.0
    for i in range(n):
        t = i / SR
        x = rng.uniform(-1, 1)
        lp += 0.6 * (x - lp)
        out.append(vel * (x - lp) * math.exp(-t / 0.022))
    return out


def bell(f, length=2.2, index=2.2, decay=0.6):
    """Two-operator FM bell (ratio 2: warm, not metallic); index decays."""
    n = int(length * SR)
    wc, wm = TWO_PI * f / SR, TWO_PI * 2 * f / SR
    out = []
    for i in range(n):
        t = i / SR
        idx = index * math.exp(-t / 0.18) + 0.25
        e = min(1.0, t / 0.003) * math.exp(-t / decay)
        out.append(e * math.sin(wc * i + idx * math.sin(wm * i)))
    return out


def svf_noise(length, cutoff_fn, amp_fn, q=0.7):
    """Noise through a state-variable band-pass with a time-varying cutoff."""
    n = int(length * SR)
    low = band = 0.0
    out = []
    for i in range(n):
        u = i / n
        fc = min(cutoff_fn(u), SR / 6)
        f = 2 * math.sin(math.pi * fc / SR)
        x = rng.uniform(-1, 1)
        high = x - low - q * band
        band += f * high
        low += f * band
        out.append(band * amp_fn(u))
    return out


# ---------------------------------------------------------------- reverb

def reverb(bus_l, bus_r, room=0.82, damp=0.35):
    """Freeverb-style: 4 damped combs + 2 all-passes per side."""
    def side(src, combs, aps):
        out = array.array("d", bytes(8 * N))
        for d in combs:
            buf, idx, store = [0.0] * d, 0, 0.0
            for i in range(N):
                y = buf[idx]
                store = y * (1 - damp) + store * damp
                buf[idx] = src[i] + store * room
                idx = idx + 1 if idx + 1 < d else 0
                out[i] += y
        for d in aps:
            buf, idx = [0.0] * d, 0
            for i in range(N):
                b = buf[idx]
                y = -out[i] + b
                buf[idx] = out[i] + b * 0.5
                idx = idx + 1 if idx + 1 < d else 0
                out[i] = y
        return out

    scale = 48000 / 44100
    cl = [int(x * scale) for x in (1116, 1277, 1422, 1617)]
    ap = [int(x * scale) for x in (556, 341)]
    wl = side(bus_l, cl, ap)
    wr = side(bus_r, [c + 25 for c in cl], [a + 25 for a in ap])
    return wl, wr


# ---------------------------------------------------------------- arrangement

def build():
    dry, send = Bus(), Bus()

    kicks = []   # (time, velocity) — also drives the pad sidechain duck

    # Drums -------------------------------------------------------------
    for s in (0, 8):                                 # bar 2: soft kick on 1 and 3
        kicks.append((at(1, s), 0.55))
    for b in (2, 3):                                 # bars 3-4: 1, 2-and, 3 (+ pickup)
        for s in (0, 6, 8) + ((14,) if b == 3 else ()):
            kicks.append((at(b, s), 0.95 if s == 0 else 0.75))
    kicks.append((at(4, 0), 1.0))                    # final downbeat

    for t, v in kicks:
        dry.add(t, kick(v), gain=0.9)

    for b in (2, 3):
        for s in (4, 12):
            dry.add(at(b, s), clap(0.8), pan=0.05, gain=0.42)
    dry.add(at(3, 15), clap(0.35), pan=-0.1, gain=0.3)           # ghost into the settle

    for s in range(2, 16, 4):                                    # bar 2: off-beat 8ths
        dry.add(at(1, s), hat(0.5), pan=0.25, gain=0.32)
    for b in (2, 3):
        for s in range(16):
            vel = 0.75 if s % 4 == 2 else (0.32 if s % 2 else 0.45)
            dry.add(at(b, s), hat(vel), pan=(0.28 if s % 2 else -0.18), gain=0.32)

    # Sidechain duck from the kicks (subtle pump on pad + bass tails).
    duck = array.array("d", [1.0] * N)
    for t, v in kicks:
        j0 = int(t * SR)
        for i in range(int(0.35 * SR)):
            j = j0 + i
            if j < N:
                duck[j] = min(duck[j], 1 - 0.42 * v * math.exp(-i / SR / 0.11))

    # Pads ----------------------------------------------------------------
    chords = [
        [50, 57, 60, 64, 65],        # Dm9
        [46, 53, 57, 60, 62],        # Bbmaj9
        [43, 50, 53, 57, 58],        # Gm9
        [48, 53, 55, 58, 62],        # C9sus
        [41, 48, 52, 55, 57, 60],    # Fmaj9 (final)
    ]
    for b, chord in enumerate(chords):
        t0 = at(b) - (0.0 if b == 0 else 0.05)
        length = (DUR - t0) if b == 4 else BAR + 0.75
        gain = 0.05 if b == 0 else 0.065
        if b == 0:
            t0, length = 0.25, BAR - 0.25 + 0.75
        for m in chord:
            for k, (cents, pan) in enumerate(((-6, -0.45), (6, 0.45))):
                s = pad_note(hz(m), length, cents)
                dry.add(t0, s, pan=pan, gain=gain, duck=duck)
                send.add(t0, s, pan=pan, gain=gain * 0.6)
    # Bar 4 resolves its sus: E3 slides in on beat 3 (the title settle).
    s = pad_note(hz(52), BAR / 2 + 0.7, 0)
    dry.add(at(3, 8), s, gain=0.06, duck=duck)

    # Bass ----------------------------------------------------------------
    bass = {
        1: [(0, 4, 34), (6, 2, 46), (8, 4, 34), (14, 2, 41)],
        2: [(0, 4, 31), (6, 2, 43), (8, 4, 31), (12, 2, 38), (14, 2, 41)],
        3: [(0, 4, 36), (6, 2, 48), (8, 4, 36), (12, 2, 43), (14, 2, 46)],
    }
    for b, notes in bass.items():
        for s, ln, m in notes:
            dry.add(at(b, s), bass_note(hz(m), ln * S16 * 0.92), gain=0.34, duck=duck)
    dry.add(at(4, 0), bass_note(hz(29), DUR - at(4, 0)), gain=0.36)  # final F1 rings out

    # Opening pulse (the cyan point appears at 0.10 s) ----------------------
    p = pulse(hz(74))
    dry.add(0.10, p, gain=0.22)
    send.add(0.10, p, gain=0.3)
    dry.add(0.10, kick(0.35), gain=0.5)                               # felt, not heard

    # Curious bar-1/2 plucks (low FM index = rounded) -----------------------
    arp1 = [(4, 69), (6, 72), (8, 74), (10, 76), (12, 72), (14, 69)]
    arp2 = [(2, 74), (6, 77), (10, 81), (14, 77)]
    for b, arp in ((0, arp1), (1, arp2)):
        for s, m in arp:
            x = bell(hz(m), 1.2, index=0.9, decay=0.28)
            pan = -0.35 if s % 4 == 0 else 0.35
            dry.add(at(b, s), x, pan=pan, gain=0.07)
            send.add(at(b, s), x, pan=pan, gain=0.09)

    # Motif: statement (bar 3), answer (bar 4), signature (bar 5) -------------
    statement = [(2, 74, 2), (4, 77, 2), (6, 79, 2), (8, 81, 6)]
    answer = [(2, 74, 2), (4, 77, 2), (6, 79, 2), (8, 84, 4), (12, 82, 4)]
    signature = [(0, 72, 2), (2, 77, 2), (4, 81, 14)]
    for b, motif, g in ((2, statement, 0.11), (3, answer, 0.11), (4, signature, 0.12)):
        for s, m, ln in motif:
            length = min(3.0, ln * S16 + 1.4)
            x = bell(hz(m), length, index=1.8, decay=0.5 if ln < 8 else 0.9)
            dry.add(at(b, s), x, pan=0.1, gain=g)
            send.add(at(b, s), x, pan=0.1, gain=g * 1.1)

    # Title-settle accent at 8.4 s: reversed swell into a G5+C6 bell dyad ------
    t_acc = at(3, 8)
    n_sw = int(0.45 * SR)
    sw = [((i / n_sw) ** 3) * math.sin(TWO_PI * hz(84) * i / SR) for i in range(n_sw)]
    send.add(t_acc - 0.45, sw, gain=0.05)
    for m in (79, 96):
        x = bell(hz(m), 2.0, index=1.2, decay=0.7)
        dry.add(t_acc, x, pan=(-0.3 if m == 79 else 0.3), gain=0.045)
        send.add(t_acc, x, gain=0.06)

    # Riser under the waveform morph (2.4 -> 4.78 s) ---------------------------
    rlen = 2.38
    riser = svf_noise(rlen, lambda u: 300 * (20 ** u), lambda u: (u ** 2.2) * (1 if u < 0.985 else (1 - u) / 0.015), q=0.5)
    gl = [((i / (rlen * SR)) ** 2) * math.sin(TWO_PI * (220 * (rlen * SR) / math.log(4) / SR)
          * (4 ** (i / (rlen * SR)) - 1)) for i in range(int(rlen * SR))]
    n_r = len(riser)
    left = [riser[i] * (1 - 0.5 * i / n_r) + 0.1 * gl[i] for i in range(n_r)]
    right = [riser[i] * (0.5 + 0.5 * i / n_r) + 0.1 * gl[i] for i in range(n_r)]
    dry.add_stereo(at(1), left, right, gain=0.16)

    # Rounded whoosh with the occluding sweep, panned left -> right ------------
    wlen = 1.05
    whoosh = svf_noise(wlen, lambda u: 380 + 2400 * math.sin(math.pi * min(1, u * 1.15)) ** 1.5,
                       lambda u: math.sin(math.pi * u) ** 2.4, q=0.9)
    nw = len(whoosh)
    left, right = [], []
    for i in range(nw):
        a = (-0.85 + 1.7 * i / nw + 1) * math.pi / 4
        left.append(whoosh[i] * math.cos(a))
        right.append(whoosh[i] * math.sin(a))
    dry.add_stereo(at(2) - 0.12, left, right, gain=0.55)
    send.add_stereo(at(2) - 0.12, left, right, gain=0.15)

    # Mix -----------------------------------------------------------------
    wl, wr = reverb(send.l, send.r)
    mix_l = array.array("d", (dry.l[i] + 0.22 * wl[i] for i in range(N)))
    mix_r = array.array("d", (dry.r[i] + 0.22 * wr[i] for i in range(N)))

    peak = max(max(abs(x) for x in mix_l), max(abs(x) for x in mix_r)) or 1.0
    g = 0.7 / peak
    pcm = array.array("h")
    for i in range(N):
        for x in (mix_l[i], mix_r[i]):
            y = math.tanh(x * g * 1.15) / math.tanh(1.15)    # gentle soft clip
            pcm.append(int(max(-1.0, min(1.0, y)) * 32767))
    return pcm


def ffmpeg(*args, capture=False):
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "info" if capture else "error", *args]
    return subprocess.run(cmd, check=True, capture_output=capture, text=True)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    dry_path = OUT.with_name("cue.dry.wav")
    pcm = build()
    with wave.open(str(dry_path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())

    # Two-pass loudnorm, then the tail fade (11.3 -> 12.0 s) at exactly 12.000 s.
    probe = ffmpeg("-i", str(dry_path), "-af",
                   "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-",
                   capture=True).stderr
    m = json.loads(probe[probe.rindex("{"):probe.rindex("}") + 1])
    ln = ("loudnorm=I=-16:TP=-1.5:LRA=11:linear=true"
          f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
          f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
          f":offset={m['target_offset']}")
    ffmpeg("-i", str(dry_path), "-af",
           f"{ln},aresample={SR},afade=t=out:st=11.3:d=0.7:curve=qsin,atrim=0:{DUR}",
           "-c:a", "pcm_s16le", str(OUT))
    dry_path.unlink()
    print(f"wrote {OUT.relative_to(HERE.parent.parent)}")


if __name__ == "__main__":
    main()
