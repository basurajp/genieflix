#!/usr/bin/env python3
"""Compose "एकलव्य" — the guru-dakshina episode (Adi Parva), one forest scene.

16 beats, one sun-lit forest clearing: Eklavya builds the clay statue of the
guru who refused him, masters the bow before it, stops the barking dog with
seven harmless arrows, and gives his right thumb as गुरुदक्षिणा. New palette
(daylight greens/marigold vs. the torch-lit sabha), new characters (Eklavya,
Drona, Arjuna, the dog, the clay statue), female narrator.

Proven mechanics (see cartoon/README.md): camera hard-cuts per line with
push-in drift, attr(ry) mouths, svgOrigin for SVG parts, hard sets at fade
boundaries, immediateRender: false on cued fromTo effects, and rig scaling /
flipping on the wrapper div (the SVG viewport clips, the div doesn't).
Usage: cartoon/episodes/eklavya/compose.py --project <dir>
"""
import argparse
import html
import json
import pathlib

ap = argparse.ArgumentParser(description="Compose the Eklavya episode into index.html.")
ap.add_argument("--project", required=True)
project = pathlib.Path(ap.parse_args().project).expanduser().resolve()
meta = json.load(open(project / "audio_meta.json"))
captions = json.load(open(project / "captions.json"))
timeline = json.load(open(project / "timeline.json"))
pj = json.load(open(project / "project.json"))
cast = json.load(open(project / "cast.json"))

total = timeline["total"]
lines = meta["lines"]
if len(lines) != 16:
    raise SystemExit(
        f"this episode's staging is written for its 16 lines (got {len(lines)}) — "
        "copy this script and re-choreograph CAM + staging for a new script"
    )
fmt = lambda v: f"{v:.3f}"
SPEAKERS = cast["speakers"]
TINT = cast.get("tints", {})
MOUTH = {"ekl": "#mouth-ekl", "dro": "#mouth-dro", "arj": "#mouth-arj"}
STAMPS = cast["stamps"]

def line_of(t):
    best = 1
    for ln in lines:
        if t >= ln["start"] - 0.01:
            best = ln["index"]
    return best

def win(i):
    ln = lines[i - 1]
    return ln["start"], ln["start"] + ln["duration"]

# ---------------------------------------------------------------- camera plan
CAM = {
    1: (1.05, 540, 1000), 2: (2.10, 560, 1012), 3: (2.15, 560, 1012), 4: (1.35, 800, 1080),
    5: (1.55, 790, 1030), 6: (1.35, 330, 1030), 7: (1.25, 260, 1120), 8: (1.50, 430, 1200),
    9: (1.80, 315, 1010), 10: (1.35, 380, 1100), 11: (1.75, 160, 1010), 12: (1.05, 540, 1050),
    13: (1.70, 165, 1010), 14: (1.80, 160, 1012), 15: (1.50, 450, 1080), 16: (1.00, 540, 980),
}

def cam_xy(s, px, py):
    x = 540 - s * px
    y = 960 - s * py
    x = max(1080 - 1080 * s, min(0, x))
    y = max(1920 - 1920 * s, min(0, y))
    return x, y

tw = []
for i in range(1, 17):
    s, px, py = CAM[i]
    t0, t1 = win(i)
    if i == 16:
        t1 = total
    x0, y0 = cam_xy(s, px, py)
    s2 = s * 1.04
    x1, y1 = cam_xy(s2, px, py)
    tw.append(f'tl.set("#world", {{scale: {s:.3f}, x: {x0:.1f}, y: {y0:.1f}}}, {fmt(t0)});')
    tw.append(f'tl.to("#world", {{scale: {s2:.3f}, x: {x1:.1f}, y: {y1:.1f}, duration: {fmt(max(0.3, t1 - t0))}, ease: "none"}}, {fmt(t0)});')

# --------------------------------------------- Eklavya seats: teleports + flip
# base pose faces LEFT (toward the practice target); scaleX -1 turns him to
# the statue on the right. Flips land on hard cuts so they read as new shots.
t4a = win(4)[0]
t6a = win(6)[0]
t10a, t10b = win(10)
tw.append(f'tl.set("#eklavya", {{x: 260, scaleX: -1, transformOrigin: "50% 50%"}}, {fmt(t4a)});')
tw.append(f'tl.set("#eklavya", {{x: 0, scaleX: 1, transformOrigin: "50% 50%"}}, {fmt(t6a)});')

# ----------------------------------------------------------------- idle life
def bob(sel, amp, period, t0, t1):
    reps = max(1, int((t1 - t0) / period) - 1)
    tw.append(f'tl.to("{sel}", {{y: {amp}, duration: {period}, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, {fmt(t0)});')
    tw.append(f'tl.set("{sel}", {{y: 0}}, {fmt(t1)});')

t7a, t7b = win(7)
t15a, t15b = win(15)
bob("#ekl-body", 3, 1.6, 0, t10a)
bob("#dro-body", 2, 2.0, t7b, win(14)[1])
bob("#arj-body", 3, 1.5, t7b, win(15)[0])

def blink(sel, org, t0, t1):
    t = t0 + 0.9
    while t < t1 - 0.6:
        tw.append(f'tl.to("{sel}", {{scaleY: 0.1, svgOrigin: {org}, duration: 0.07, repeat: 1, yoyo: true, ease: "none"}}, {fmt(t)});')
        t += 3.1

blink("#eyes-ekl", '"120 90"', 0, total - 0.5)
blink("#eyes-dro", '"128 92"', t7b, total - 0.5)
blink("#eyes-arj", '"112 88"', t7b, total - 0.5)

# butterflies + light shafts keep the clearing alive for the whole runtime
for k, (dx, dy, period) in enumerate([(90, -50, 7.0), (-70, -40, 8.5)]):
    reps = max(1, int(total / period) - 1)
    tw.append(f'tl.to("#bfly-{k}", {{x: {dx}, y: {dy}, duration: {period}, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, 0);')
reps = max(1, int(total / 3.4) + 1)
tw.append(f'tl.to("#shafts", {{opacity: 0.42, duration: 3.4, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, 0);')
reps = max(1, int(total / 0.5) - 1)
tw.append(f'tl.to("#tail-dog", {{rotation: 24, svgOrigin: "28 84", duration: 0.5, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, 0);')

# --------------------------------------------------------------------- mouths
for sel in MOUTH.values():
    tw.append(f'tl.set("{sel}", {{attr: {{ry: 3}}}}, 0);')
for c in captions:
    spk = SPEAKERS[line_of(c["start"]) - 1]
    if spk not in MOUTH:
        continue
    span = c["end"] - c["start"]
    if span < 0.14:
        continue
    reps = max(1, int(span / 0.09) - 1)
    tw.append(f'tl.to("{MOUTH[spk]}", {{attr: {{ry: 12}}, duration: 0.09, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, {fmt(c["start"])});')
    tw.append(f'tl.set("{MOUTH[spk]}", {{attr: {{ry: 3}}}}, {fmt(c["end"])});')

# --------------------------------------------------------------------- stamps
for s in range(1, 17):
    t0 = win(s)[0]
    tw.append(f'tl.fromTo("#stamp-{s}", {{scale: 0.6, opacity: 0, rotation: -4}}, '
              f'{{scale: 1, opacity: 1, rotation: -2, duration: 0.35, ease: "back.out(2)"}}, {fmt(t0)});')

# ============================================================ per-beat staging
t2a, t2b = win(2)                       # the refusal, remembered: head drops
tw.append(f'tl.to("#head-ekl", {{rotation: -7, svgOrigin: "120 150", duration: 0.9, ease: "sine.inOut"}}, {fmt(t2a + 0.3)});')

t3a, t3b = win(3)                       # "सीखूँगा मैं यहीं!" — head up, hop
tw.append(f'tl.to("#head-ekl", {{rotation: 0, svgOrigin: "120 150", duration: 0.4, ease: "power1.out"}}, {fmt(t3a)});')
tw.append(f'tl.to("#eklavya", {{y: -26, duration: 0.22, repeat: 1, yoyo: true, ease: "power1.out"}}, {fmt(t3b - 1.0)});')
tw.append(f'tl.to("#arm-ekl", {{rotation: -50, svgOrigin: "158 205", duration: 0.3, ease: "power2.out"}}, {fmt(t3b - 1.0)});')
tw.append(f'tl.to("#arm-ekl", {{rotation: 0, svgOrigin: "158 205", duration: 0.5, ease: "sine.inOut"}}, {fmt(t3b - 0.4)});')

t4b = win(4)[1]                         # the clay guru rises from the earth
tw.append(f'tl.fromTo("#statue", {{y: 340}}, {{y: 0, duration: 1.3, ease: "power2.out", immediateRender: false}}, {fmt(t4a + 0.2)});')
for k in range(3):
    tw.append(f'tl.fromTo("#sdust-{k}", {{x: 0, y: 0, opacity: 0.85, scale: 0.5}}, '
              f'{{x: {(-1) ** k * (30 + 12 * k)}, y: {-26 - 9 * k}, opacity: 0, scale: 1.2, duration: 0.6, '
              f'ease: "power1.out", immediateRender: false}}, {fmt(t4a + 1.0 + 0.15 * k)});')
    tw.append(f'tl.set("#sdust-{k}", {{opacity: 0}}, {fmt(t4a + 1.75 + 0.15 * k)});')
for k in range(4):                      # sculpting pats
    tw.append(f'tl.to("#arm-ekl", {{rotation: -35, svgOrigin: "158 205", duration: 0.18, repeat: 1, yoyo: true, ease: "sine.inOut"}}, {fmt(t4a + 1.6 + 0.45 * k)});')

t5a, t5b = win(5)                       # प्रणाम to the statue
tw.append(f'tl.to("#ekl-body", {{rotation: -22, svgOrigin: "130 300", duration: 0.7, ease: "sine.inOut"}}, {fmt(t5a + 0.3)});')
tw.append(f'tl.to("#ekl-body", {{rotation: 0, svgOrigin: "130 300", duration: 0.7, ease: "sine.inOut"}}, {fmt(t5b - 0.8)});')

t6b = win(6)[1]                         # practice: three shots at the target
gap = (t6b - t6a - 1.0) / 3
for k in range(3):
    t = t6a + 0.5 + k * gap
    tw.append(f'tl.to("#arm-ekl", {{rotation: -28, svgOrigin: "158 205", duration: 0.22, ease: "power1.out"}}, {fmt(t)});')
    tw.append(f'tl.to("#arm-ekl", {{rotation: 0, svgOrigin: "158 205", duration: 0.12, ease: "power3.in"}}, {fmt(t + 0.26)});')
    tw.append(f'tl.fromTo("#shot-{k}", {{x: 0, opacity: 1}}, {{x: -300, opacity: 1, duration: 0.16, '
              f'ease: "power1.in", immediateRender: false}}, {fmt(t + 0.38)});')
    tw.append(f'tl.set("#shot-{k}", {{opacity: 0}}, {fmt(t + 0.55)});')
    tw.append(f'tl.set("#stuck-{k}", {{opacity: 1}}, {fmt(t + 0.54)});')
    tw.append(f'tl.to("#target", {{rotation: {3 if k % 2 == 0 else -3}, svgOrigin: "105 980", duration: 0.08, repeat: 3, yoyo: true}}, {fmt(t + 0.54)});')
    tw.append(f'tl.set("#target", {{rotation: 0}}, {fmt(t + 0.9)});')

# the guru, the prince, and the dog arrive
tw.append(f'tl.to("#drona", {{x: 270, duration: 1.7, ease: "power1.inOut"}}, {fmt(t7a + 0.2)});')
tw.append(f'tl.to("#arjuna", {{x: 500, duration: 1.7, ease: "power1.inOut"}}, {fmt(t7a + 0.4)});')
tw.append(f'tl.to("#dog", {{x: 550, duration: 1.3, ease: "power1.inOut"}}, {fmt(t7a)});')
reps = 4
tw.append(f'tl.to("#dog", {{y: -18, duration: 0.16, repeat: {reps * 2 - 1}, yoyo: true, ease: "sine.inOut"}}, {fmt(t7a)});')
tw.append(f'tl.set("#dog", {{y: 0}}, {fmt(t7a + 0.16 * reps * 2)});')

t8a, t8b = win(8)                       # seven arrows, not one wound
tw.append(f'tl.to("#head-dog", {{rotation: -14, svgOrigin: "150 70", duration: 0.2, repeat: 3, yoyo: true, ease: "sine.inOut"}}, {fmt(t8a)});')
flurry = t8a + 1.2
for k in range(7):
    t = flurry + 0.08 * k
    tw.append(f'tl.fromTo("#dshot-{k}", {{x: 0, y: 0, opacity: 1}}, {{x: -150, y: 130, opacity: 1, duration: 0.12, '
              f'ease: "power1.in", immediateRender: false}}, {fmt(t)});')
    tw.append(f'tl.set("#dshot-{k}", {{opacity: 0}}, {fmt(t + 0.13)});')
tw.append(f'tl.to("#arm-ekl", {{rotation: -26, svgOrigin: "158 205", duration: 0.06, repeat: 13, yoyo: true, ease: "none"}}, {fmt(flurry - 0.1)});')
tw.append(f'tl.set("#arm-ekl", {{rotation: 0}}, {fmt(flurry + 0.95)});')
tw.append(f'tl.set("#muzzle", {{opacity: 1}}, {fmt(flurry + 0.62)});')
tw.append(f'tl.to("#dog", {{y: -22, duration: 0.18, repeat: 1, yoyo: true, ease: "power1.out"}}, {fmt(flurry + 0.62)});')

t9a, t9b = win(9)                       # Arjuna, astonished
tw.append(f'tl.to("#arjuna", {{y: -24, duration: 0.2, repeat: 1, yoyo: true, ease: "power1.out"}}, {fmt(t9a + 0.2)});')

# Eklavya comes forward and bows at the guru's feet
tw.append(f'tl.to("#eklavya", {{x: -130, duration: 1.1, ease: "power1.inOut"}}, {fmt(t10a + 0.3)});')
tw.append(f'tl.to("#ekl-body", {{rotation: -26, svgOrigin: "130 300", duration: 0.8, ease: "sine.inOut"}}, {fmt(t10a + 1.5)});')

t11a, t11b = win(11)                    # "तुम्हारा गुरु कौन है?"
tw.append(f'tl.to("#staff-dro", {{rotation: 4, svgOrigin: "36 400", duration: 0.3, repeat: 1, yoyo: true, ease: "sine.inOut"}}, {fmt(t11a + 0.3)});')

t12a, t12b = win(12)                    # "आप ही हैं गुरुदेव!" — head lifts
tw.append(f'tl.to("#head-ekl", {{rotation: 10, svgOrigin: "120 150", duration: 0.5, ease: "sine.out"}}, {fmt(t12a)});')
tw.append(f'tl.to("#head-ekl", {{rotation: 0, svgOrigin: "120 150", duration: 0.5, ease: "sine.inOut"}}, {fmt(t12b)});')

t13a, t13b = win(13)                    # Drona remembers his promise
tw.append(f'tl.to("#head-dro", {{rotation: 6, svgOrigin: "128 150", duration: 0.9, ease: "sine.inOut"}}, {fmt(t13a + 0.3)});')

t14a, t14b = win(14)                    # the ask: open palm
tw.append(f'tl.to("#head-dro", {{rotation: 0, svgOrigin: "128 150", duration: 0.4, ease: "power1.out"}}, {fmt(t14a)});')
tw.append(f'tl.to("#arm-dro", {{rotation: 58, svgOrigin: "175 210", duration: 0.6, ease: "power1.out"}}, {fmt(t14a + 0.4)});')

# the offering: he rises, raises his hand, the forest answers with petals
tw.append(f'tl.to("#ekl-body", {{rotation: 0, svgOrigin: "130 300", duration: 0.6, ease: "sine.inOut"}}, {fmt(t15a + 0.3)});')
tw.append(f'tl.to("#arm-ekl", {{rotation: -85, svgOrigin: "158 205", duration: 0.7, ease: "power1.inOut"}}, {fmt(t15a + 1.0)});')
tw.append(f'tl.fromTo("#soft-flash", {{opacity: 0}}, {{opacity: 0.5, duration: 0.3, repeat: 1, yoyo: true, ease: "sine.inOut", immediateRender: false}}, {fmt(t15a + 1.9)});')
tw.append(f'tl.set("#soft-flash", {{opacity: 0}}, {fmt(t15a + 2.7)});')
tw.append(f'tl.set("#wrap-ekl", {{opacity: 1}}, {fmt(t15a + 2.4)});')
tw.append(f'tl.to("#arm-ekl", {{rotation: 0, svgOrigin: "158 205", duration: 0.7, ease: "sine.inOut"}}, {fmt(t15b - 0.8)});')
tw.append(f'tl.to("#arm-dro", {{rotation: 0, svgOrigin: "175 210", duration: 0.8, ease: "sine.inOut"}}, {fmt(t15a + 2.6)});')
tw.append(f'tl.to("#head-dro", {{rotation: 8, svgOrigin: "128 150", duration: 1.0, ease: "sine.inOut"}}, {fmt(t15a + 2.6)});')
tw.append(f'tl.to("#head-arj", {{rotation: 8, svgOrigin: "112 148", duration: 1.0, ease: "sine.inOut"}}, {fmt(t15a + 2.6)});')
for k in range(8):
    start = t15a + 1.9 + 0.3 * k
    reps = max(0, int((total - start) / 3.0) - 1)
    tw.append(f'tl.fromTo("#petal-{k}", {{y: 0, x: 0, opacity: 0.9, rotation: 0}}, '
              f'{{y: 560, x: {(-1) ** k * (40 + 14 * k)}, opacity: 0, rotation: {120 + 30 * k}, duration: 3.0, '
              f'repeat: {reps}, ease: "sine.in", immediateRender: false}}, {fmt(start)});')
    tw.append(f'tl.set("#petal-{k}", {{opacity: 0}}, {fmt(start + 3.0 * (reps + 1))});')

t16a = win(16)[0]                       # the answer the forest still gives
tw.append(f'tl.to("#eklavya", {{x: 30, duration: 1.4, ease: "power1.inOut"}}, {fmt(t16a + 0.3)});')
tw.append(f'tl.to("#head-dro", {{rotation: 0, svgOrigin: "128 150", duration: 0.8, ease: "sine.inOut"}}, {fmt(t16a)});')
tw.append(f'tl.to("#arm-ekl", {{rotation: -120, svgOrigin: "158 205", duration: 1.0, ease: "power1.inOut"}}, {fmt(t16a + 1.8)});')
tw.append(f'tl.to("#shafts", {{opacity: 0.55, duration: {fmt(max(0.8, total - t16a - 0.5))}, ease: "sine.in"}}, {fmt(t16a + 0.4)});')

# title card retires at the end of beat 1
te = win(1)[1] + 0.3
tw.append(f'tl.to("#title-inner", {{opacity: 0, duration: 0.35}}, {fmt(te - 0.50)});')
tw.append(f'tl.set("#title-inner", {{opacity: 0}}, {fmt(te - 0.10)});')

# ------------------------------------------------------------------ html bits
caps = []
for c in captions:
    tint = TINT.get(SPEAKERS[line_of(c["start"]) - 1], "#ffffff")
    dur = max(0.12, c["end"] - c["start"])
    caps.append(
        f'<div class="caption clip" style="color: {tint};" data-start="{fmt(c["start"])}" '
        f'data-duration="{fmt(dur)}" data-track-index="4">{html.escape(c["text"])}</div>'
    )
stamps = []
for i in range(1, 17):
    t0, _ = win(i)
    dur = (win(i + 1)[0] - t0) if i < 16 else (total - t0)
    stamps.append(
        f'<div id="stamp-{i}" class="stamp clip" data-start="{fmt(t0)}" '
        f'data-duration="{fmt(dur)}" data-track-index="3">{html.escape(STAMPS[i - 1])}</div>'
    )
audio = []
for ln in lines:
    audio.append(
        f'<audio id="voice-line-{ln["index"]:02d}" class="clip" src="{ln["file"]}" '
        f'data-start="{fmt(ln["start"])}" data-duration="{fmt(ln["duration"])}" data-track-index="5"></audio>'
    )
music = pj.get("music") or ""
if music and (project / music).exists():
    audio.append(
        f'<audio id="music-bed" class="clip" src="{music}" '
        f'data-start="0" data-duration="{fmt(total)}" data-track-index="6"></audio>'
    )

# ---------------------------------------------------------------- the rigs
EKL_SVG = """
      <svg width="260" height="430" viewBox="0 0 260 430">
        <g id="ekl-body">
        <path d="M150 240 L196 232 Q206 300 198 316 L184 314 Q186 268 172 250 Z" fill="#5c3a24"/>
        <line x1="176" y1="238" x2="196" y2="222" stroke="#5c3a24" stroke-width="8" stroke-linecap="round"/>
        <line x1="186" y1="238" x2="202" y2="230" stroke="#5c3a24" stroke-width="8" stroke-linecap="round"/>
        <path d="M92 380 Q88 300 96 248 L164 248 Q172 300 168 380 Z" fill="#c8893a"/>
        <path d="M92 300 L168 300 L168 316 L92 316 Z" fill="#3f8a4f"/>
        <path d="M88 240 Q90 170 130 164 Q170 170 172 240 L168 264 L92 264 Z" fill="#8a5a3c"/>
        <path d="M92 176 L168 232 L168 250 L92 194 Z" fill="#c8893a"/>
        <path d="M88 232 Q72 258 78 298 L96 294 Q92 264 100 244 Z" fill="#8a5a3c"/>
        <rect x="74" y="252" width="24" height="9" rx="4" fill="#efa63a"/>
        <path d="M56 150 Q30 240 56 330 L66 326 Q44 240 66 154 Z" fill="#6b4a32"/>
        <line x1="60" y1="152" x2="60" y2="328" stroke="#e8e2d0" stroke-width="3"/>
        <path d="M62 236 Q80 246 92 262 L84 274 Q68 258 56 250 Z" fill="#8a5a3c"/>
        <g id="arm-ekl">
          <path d="M158 205 Q186 222 196 264 L178 274 Q168 238 146 224 Z" fill="#8a5a3c"/>
          <circle cx="188" cy="270" r="12" fill="#7a4c30"/>
          <path id="wrap-ekl" d="M176 258 Q192 252 200 262 Q198 278 182 280 Q172 270 176 258 Z" fill="#f2ead2" opacity="0"/>
          <rect x="168" y="238" width="24" height="9" rx="4" fill="#efa63a" transform="rotate(58 180 242)"/>
        </g>
        <g id="legs-ekl">
          <rect x="100" y="378" width="22" height="40" fill="#8a5a3c"/>
          <rect x="138" y="378" width="22" height="40" fill="#8a5a3c"/>
          <ellipse cx="111" cy="420" rx="20" ry="8" fill="#5c3a24"/>
          <ellipse cx="149" cy="420" rx="20" ry="8" fill="#5c3a24"/>
        </g>
        <g id="head-ekl">
          <circle cx="120" cy="90" r="52" fill="#8a5a3c"/>
          <path d="M70 78 Q74 42 120 38 Q166 42 170 78 Q136 58 100 64 Q82 68 70 78 Z" fill="#1e1208"/>
          <path d="M104 44 Q118 18 134 44 Q120 52 104 44 Z" fill="#1e1208"/>
          <path d="M120 24 Q112 4 126 -2 L132 8 Q126 16 128 26 Z" fill="#3f8a4f"/>
          <circle cx="129" cy="6" r="5" fill="#efa63a"/>
          <rect x="70" y="58" width="100" height="13" rx="6" fill="#a0442e"/>
          <g id="eyes-ekl">
            <circle cx="101" cy="90" r="9.5" fill="#fff"/><circle cx="139" cy="90" r="9.5" fill="#fff"/>
            <circle cx="99" cy="92" r="4.8" fill="#1e1208"/><circle cx="137" cy="92" r="4.8" fill="#1e1208"/>
          </g>
          <path d="M90 74 Q101 69 112 74" stroke="#1e1208" stroke-width="4.5" fill="none" stroke-linecap="round"/>
          <path d="M128 74 Q139 69 150 74" stroke="#1e1208" stroke-width="4.5" fill="none" stroke-linecap="round"/>
          <ellipse id="mouth-ekl" cx="118" cy="120" rx="10" ry="3" fill="#4a1e14"/>
          <rect x="110" y="138" width="20" height="14" fill="#8a5a3c"/>
        </g>
        </g>
      </svg>"""

DRO_SVG = """
      <svg width="260" height="440" viewBox="0 0 260 440">
        <g id="dro-body">
        <path d="M78 400 Q72 260 92 210 L176 210 Q196 260 190 400 Z" fill="#f2ead2"/>
        <path d="M92 210 L176 210 L190 400 L166 400 Q170 280 152 232 L92 232 Z" fill="#e0893a" opacity="0.85"/>
        <path d="M88 216 Q90 168 132 162 Q174 168 176 216 L172 240 L92 240 Z" fill="#f2ead2"/>
        <path d="M92 232 Q76 258 82 300 L100 296 Q96 266 104 246 Z" fill="#caa27a"/>
        <g id="staff-dro">
          <line x1="36" y1="180" x2="36" y2="420" stroke="#6b4a32" stroke-width="10" stroke-linecap="round"/>
          <circle cx="36" cy="174" r="9" fill="#e0893a"/>
        </g>
        <path d="M58 250 Q44 246 40 258 Q48 270 62 264 Z" fill="#caa27a"/>
        <g id="arm-dro">
          <path d="M175 210 Q200 230 206 272 L188 282 Q180 246 160 228 Z" fill="#caa27a"/>
          <circle cx="197" cy="278" r="12" fill="#b08a5c"/>
        </g>
        <circle cx="106" cy="238" r="5" fill="#8a4e34"/><circle cx="120" cy="244" r="5" fill="#8a4e34"/>
        <circle cx="134" cy="246" r="5" fill="#8a4e34"/><circle cx="148" cy="244" r="5" fill="#8a4e34"/>
        <g id="head-dro">
          <circle cx="128" cy="94" r="50" fill="#caa27a"/>
          <path d="M84 80 Q88 46 128 42 Q168 46 172 80 L172 90 Q146 70 110 74 Q94 78 84 90 Z" fill="#d8d4cc"/>
          <circle cx="128" cy="40" r="11" fill="#d8d4cc"/>
          <path d="M94 118 Q128 182 162 118 L162 96 Q128 116 94 96 Z" fill="#d8d4cc"/>
          <g id="eyes-dro">
            <circle cx="110" cy="92" r="9" fill="#fff"/><circle cx="146" cy="92" r="9" fill="#fff"/>
            <circle cx="112" cy="94" r="4.5" fill="#2a1a0c"/><circle cx="148" cy="94" r="4.5" fill="#2a1a0c"/>
          </g>
          <path d="M99 76 Q110 71 121 76" stroke="#8a8478" stroke-width="4.5" fill="none" stroke-linecap="round"/>
          <path d="M135 76 Q146 71 157 76" stroke="#8a8478" stroke-width="4.5" fill="none" stroke-linecap="round"/>
          <ellipse id="mouth-dro" cx="128" cy="124" rx="9" ry="3" fill="#4a2618"/>
        </g>
        </g>
      </svg>"""

ARJ_SVG = """
      <svg width="230" height="400" viewBox="0 0 230 400">
        <g id="arj-body">
        <path d="M70 360 Q66 258 80 218 L156 218 Q170 258 166 360 Z" fill="#3556a8"/>
        <path d="M80 218 L156 218 L156 238 L80 238 Z" fill="#c8ccd8"/>
        <path d="M112 218 L124 218 L124 360 L112 360 Z" fill="#c8ccd8" opacity="0.6"/>
        <path d="M76 176 Q78 130 114 126 Q150 130 152 176 L148 224 L80 224 Z" fill="#3556a8"/>
        <path d="M80 224 Q64 248 70 288 L88 284 Q84 256 92 236 Z" fill="#e0aa78"/>
        <path d="M152 224 Q168 248 162 288 L144 284 Q148 256 140 236 Z" fill="#e0aa78"/>
        <path d="M158 200 L196 160 Q206 220 178 268 L166 258 Q182 222 172 196 Z" fill="#6b4a32" opacity="0.9"/>
        <rect x="88" y="358" width="20" height="30" fill="#2a3c6e"/>
        <rect x="122" y="358" width="20" height="30" fill="#2a3c6e"/>
        <rect x="80" y="384" width="38" height="12" rx="6" fill="#1a2440"/>
        <rect x="116" y="384" width="38" height="12" rx="6" fill="#1a2440"/>
        <g id="head-arj">
          <circle cx="112" cy="88" r="46" fill="#e0aa78"/>
          <path d="M70 76 Q74 44 112 40 Q150 44 154 76 L154 86 Q128 66 96 70 Q80 74 70 86 Z" fill="#2a1808"/>
          <path d="M76 62 Q112 42 148 62 L152 46 L130 50 L112 36 L94 50 L72 46 Z" fill="#e8c84a"/>
          <circle cx="112" cy="44" r="5" fill="#a02c2e"/>
          <g id="eyes-arj">
            <circle cx="96" cy="88" r="8.5" fill="#fff"/><circle cx="130" cy="88" r="8.5" fill="#fff"/>
            <circle cx="98" cy="90" r="4.3" fill="#1c0e04"/><circle cx="132" cy="90" r="4.3" fill="#1c0e04"/>
          </g>
          <path d="M86 73 Q96 68 106 73" stroke="#1c0e04" stroke-width="4" fill="none" stroke-linecap="round"/>
          <path d="M120 73 Q130 68 140 73" stroke="#1c0e04" stroke-width="4" fill="none" stroke-linecap="round"/>
          <ellipse id="mouth-arj" cx="112" cy="116" rx="9" ry="3" fill="#6e2c1e"/>
          <rect x="104" y="132" width="18" height="12" fill="#e0aa78"/>
        </g>
        </g>
      </svg>"""

DOG_SVG = """
      <svg width="210" height="150" viewBox="0 0 210 150">
        <path id="tail-dog" d="M28 84 Q6 66 12 44 L24 50 Q20 66 36 76 Z" fill="#8a5c34"/>
        <ellipse cx="95" cy="95" rx="62" ry="34" fill="#a4713f"/>
        <rect x="52" y="112" width="13" height="30" rx="6" fill="#8a5c34"/>
        <rect x="76" y="116" width="13" height="28" rx="6" fill="#a4713f"/>
        <rect x="112" y="116" width="13" height="28" rx="6" fill="#a4713f"/>
        <rect x="132" y="112" width="13" height="30" rx="6" fill="#8a5c34"/>
        <g id="head-dog">
          <circle cx="150" cy="70" r="34" fill="#a4713f"/>
          <path d="M126 46 Q118 20 138 24 Q146 36 142 52 Z" fill="#6b4423"/>
          <path d="M168 42 Q176 18 156 24 Q150 36 156 50 Z" fill="#8a5c34"/>
          <ellipse cx="176" cy="80" rx="20" ry="14" fill="#c8935c"/>
          <circle cx="188" cy="76" r="7" fill="#2a1808"/>
          <circle cx="144" cy="64" r="6" fill="#2a1808"/><circle cx="162" cy="64" r="6" fill="#2a1808"/>
          <path d="M174 92 q6 10 14 6" stroke="#d86a5a" stroke-width="6" fill="none" stroke-linecap="round"/>
          <g id="muzzle" opacity="0">
            <line x1="158" y1="60" x2="196" y2="98" stroke="#6b4a32" stroke-width="4"/>
            <line x1="196" y1="62" x2="156" y2="96" stroke="#6b4a32" stroke-width="4"/>
            <line x1="152" y1="76" x2="200" y2="82" stroke="#6b4a32" stroke-width="4"/>
            <line x1="164" y1="56" x2="188" y2="102" stroke="#6b4a32" stroke-width="4"/>
            <line x1="190" y1="56" x2="164" y2="100" stroke="#6b4a32" stroke-width="4"/>
            <line x1="154" y1="66" x2="198" y2="92" stroke="#6b4a32" stroke-width="4"/>
            <line x1="154" y1="88" x2="198" y2="68" stroke="#6b4a32" stroke-width="4"/>
          </g>
        </g>
      </svg>"""

STATUE_SVG = """
      <svg width="300" height="480" viewBox="0 0 300 480">
        <path d="M40 428 L260 428 L248 396 L52 396 Z" fill="#8a8072"/>
        <path d="M60 396 L240 396 L232 372 L68 372 Z" fill="#9a9082"/>
        <path d="M92 372 Q86 250 104 210 L192 210 Q210 250 204 372 Z" fill="#b06a4a"/>
        <path d="M104 210 L192 210 L204 372 L184 372 Q188 262 172 226 L104 226 Z" fill="#8a4e34" opacity="0.55"/>
        <path d="M100 216 Q102 172 148 166 Q194 172 196 216 L192 238 L104 238 Z" fill="#b06a4a"/>
        <circle cx="148" cy="98" r="48" fill="#b06a4a"/>
        <path d="M106 84 Q110 52 148 48 Q186 52 190 84 L190 94 Q164 74 130 78 Q114 82 106 94 Z" fill="#8a4e34"/>
        <circle cx="148" cy="46" r="10" fill="#8a4e34"/>
        <path d="M116 120 Q148 178 180 120 L180 100 Q148 118 116 100 Z" fill="#8a4e34"/>
        <path d="M126 92 Q136 88 144 92" stroke="#6e3c26" stroke-width="4" fill="none" stroke-linecap="round"/>
        <path d="M152 92 Q162 88 172 92" stroke="#6e3c26" stroke-width="4" fill="none" stroke-linecap="round"/>
        <circle cx="118" cy="242" r="6" fill="#efa63a"/><circle cx="134" cy="250" r="6" fill="#efa63a"/>
        <circle cx="150" cy="252" r="6" fill="#efa63a"/><circle cx="166" cy="250" r="6" fill="#efa63a"/>
        <circle cx="180" cy="242" r="6" fill="#efa63a"/>
        <g fill="#c8b89a">
          <circle id="sdust-0" cx="90" cy="400" r="10" opacity="0"/>
          <circle id="sdust-1" cx="150" cy="410" r="12" opacity="0"/>
          <circle id="sdust-2" cx="215" cy="402" r="9" opacity="0"/>
        </g>
      </svg>"""

# ------------------------------------------------------------------ the page
TITLE = pj.get("title", "एकलव्य")
KICKER = pj.get("topic", "गुरुभक्ति की कथा")
deva = project / "assets" / "fonts" / "NotoSansDevanagari-Regular.ttf"
FONT_FACE = """
    @font-face { font-family: 'Noto Sans Devanagari'; font-weight: 400;
      src: url('assets/fonts/NotoSansDevanagari-Regular.ttf'); }
    @font-face { font-family: 'Noto Sans Devanagari'; font-weight: 700;
      src: url('assets/fonts/NotoSansDevanagari-Bold.ttf'); }
""" if deva.exists() else """
    @font-face { font-family: 'Noto Sans Devanagari'; src: local('Noto Sans Devanagari'); }
"""

page = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{html.escape(TITLE)}</title></head>
<body>
<div id="stage" data-composition-id="reel" data-start="0" data-duration="{fmt(total)}"
     data-width="1080" data-height="1920" data-fps="30">
  <style>{FONT_FACE}
    #stage {{ background: #24471f; font-family: -apple-system, "Segoe UI", Roboto, "Noto Sans Devanagari", Helvetica, Arial, sans-serif; overflow: hidden; }}
    #world, #shaker {{ position: absolute; inset: 0; }}
    #world {{ transform-origin: 0px 0px; }}
    .abs {{ position: absolute; }}
    .caption {{ position: absolute; top: 1380px; left: 50%; transform: translateX(-50%);
      max-width: 840px; background: rgba(10, 28, 14, 0.85); border-radius: 18px; padding: 18px 34px;
      font-size: 54px; font-weight: 700; text-align: center; }}
    .stamp {{ position: absolute; top: 300px; left: 50%; transform: translateX(-50%) rotate(-2deg);
      background: rgba(16, 36, 20, 0.88); border: 2px solid #efa63a; color: #ffe8b8; border-radius: 14px;
      padding: 14px 32px; font-size: 42px; font-weight: 800; letter-spacing: 2px; white-space: nowrap; opacity: 0; }}
    #title-card {{ position: absolute; top: 110px; left: 0; right: 120px; margin: 0 auto; width: fit-content;
      text-align: center; z-index: 5; }}
    #kicker {{ color: #1e4a2c; font-size: 36px; font-weight: 800; letter-spacing: 6px; }}
    #title-chip {{ margin-top: 14px; background: rgba(255, 255, 255, 0.88); border: 3px solid #efa63a;
      border-radius: 22px; padding: 18px 42px; color: #1e4a2c; font-size: 64px; font-weight: 800; }}
  </style>

  <div id="world" class="clip" data-start="0" data-duration="{fmt(total)}" data-track-index="0">
  <div id="shaker">

    <!-- the clearing: one sun-lit set for the whole episode -->
    <div class="abs clip" style="left:0; top:0;" data-start="0" data-duration="{fmt(total)}" data-track-index="0">
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        <defs>
          <linearGradient id="daysky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#8ecfdd"/><stop offset="0.7" stop-color="#c2e4c4"/>
            <stop offset="1" stop-color="#d8ecc8"/>
          </linearGradient>
          <radialGradient id="sunhi" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stop-color="#fff7d0" stop-opacity="0.9"/><stop offset="1" stop-color="#fff7d0" stop-opacity="0"/>
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="1080" height="1400" fill="url(#daysky)"/>
        <circle cx="860" cy="330" r="140" fill="url(#sunhi)"/>
        <circle cx="860" cy="330" r="70" fill="#fff2b8"/>
        <path d="M0 1100 Q180 1010 360 1080 Q560 1000 760 1070 Q920 1010 1080 1080 L1080 1400 L0 1400 Z" fill="#2e6b40"/>
        <path d="M0 1180 Q240 1100 480 1160 Q740 1090 1080 1170 L1080 1400 L0 1400 Z" fill="#3f8a4f"/>
        <path d="M-40 0 Q140 60 130 260 Q220 180 260 60 L300 0 Z" fill="#2e6b40"/>
        <path d="M1120 0 Q940 80 950 300 Q860 220 820 80 L780 0 Z" fill="#2e6b40"/>
        <path d="M-20 120 Q120 160 140 340 L100 340 Q60 220 -20 190 Z" fill="#3f8a4f" opacity="0.8"/>
        <path d="M1100 140 Q960 180 940 360 L980 360 Q1020 240 1100 210 Z" fill="#3f8a4f" opacity="0.8"/>
        <g id="target">
          <rect x="40" y="500" width="120" height="850" rx="24" fill="#6b4a32"/>
          <path d="M52 560 Q100 520 148 560 L148 500 L52 500 Z" fill="#5a3c26"/>
          <circle cx="105" cy="980" r="64" fill="#f2ead2"/>
          <circle cx="105" cy="980" r="42" fill="#d86a5a"/>
          <circle cx="105" cy="980" r="18" fill="#f2ead2"/>
          <g stroke="#3f2c1c" stroke-width="7" stroke-linecap="round">
            <line id="stuck-0" x1="118" y1="952" x2="168" y2="920" opacity="0"/>
            <line id="stuck-1" x1="122" y1="984" x2="176" y2="982" opacity="0"/>
            <line id="stuck-2" x1="116" y1="1010" x2="164" y2="1044" opacity="0"/>
          </g>
        </g>
        <rect x="0" y="1330" width="1080" height="590" fill="#4f9455"/>
        <path d="M0 1330 Q540 1300 1080 1330 L1080 1360 Q540 1332 0 1360 Z" fill="#3f8a4f"/>
        <path d="M180 1420 Q540 1380 900 1430 L900 1500 Q540 1450 180 1500 Z" fill="#a37a4e" opacity="0.7"/>
        <g fill="#efa63a">
          <circle cx="240" cy="1368" r="9"/><circle cx="262" cy="1360" r="7"/><circle cx="250" cy="1382" r="6"/>
          <circle cx="920" cy="1400" r="9"/><circle cx="944" cy="1392" r="7"/>
        </g>
        <g fill="#e26a8a">
          <circle cx="700" cy="1364" r="7"/><circle cx="718" cy="1372" r="6"/>
        </g>
        <path id="bfly-0" d="M330 700 q-14 -16 -4 -26 q12 -2 10 14 q14 -12 20 2 q-2 12 -20 8 Z" fill="#efa63a"/>
        <path id="bfly-1" d="M760 620 q-12 -14 -3 -22 q10 -2 8 12 q12 -10 17 2 q-2 10 -17 7 Z" fill="#7ab8e8"/>
        <g id="shafts" opacity="0.25">
          <path d="M700 0 L840 0 L520 900 L440 900 Z" fill="#fff7d0"/>
          <path d="M880 0 L980 0 L740 800 L680 800 Z" fill="#fff7d0"/>
        </g>
      </svg>
    </div>

    <!-- the clay guru (rises at beat 4, stays forever) -->
    <div id="statue" class="abs clip" style="left:770px; top:900px; width:300px; height:480px;"
         data-start="{fmt(t4a)}" data-duration="{fmt(total - t4a)}" data-track-index="1">{STATUE_SVG}
    </div>

    <div id="arjuna" class="abs clip" style="left:-300px; top:960px; width:230px; height:400px;"
         data-start="{fmt(t7a)}" data-duration="{fmt(total - t7a)}" data-track-index="2">{ARJ_SVG}
    </div>

    <div id="drona" class="abs clip" style="left:-240px; top:920px; width:260px; height:440px;"
         data-start="{fmt(t7a)}" data-duration="{fmt(total - t7a)}" data-track-index="2">{DRO_SVG}
    </div>

    <div id="dog" class="abs clip" style="left:-250px; top:1230px; width:210px; height:150px;"
         data-start="{fmt(t7a)}" data-duration="{fmt(total - t7a)}" data-track-index="2">{DOG_SVG}
    </div>

    <div id="eklavya" class="abs clip" style="left:430px; top:930px; width:260px; height:430px;"
         data-start="0" data-duration="{fmt(total)}" data-track-index="2">{EKL_SVG}
    </div>

    <!-- arrows in flight + falling marigold petals -->
    <div class="abs clip" style="left:0; top:0;" data-start="{fmt(t6a)}" data-duration="{fmt(total - t6a)}" data-track-index="2">
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        <g stroke="#3f2c1c" stroke-width="6" stroke-linecap="round">
          <line id="shot-0" x1="470" y1="1145" x2="540" y2="1145" opacity="0"/>
          <line id="shot-1" x1="470" y1="1152" x2="540" y2="1152" opacity="0"/>
          <line id="shot-2" x1="470" y1="1158" x2="540" y2="1158" opacity="0"/>
          <line id="dshot-0" x1="520" y1="1150" x2="575" y2="1128" opacity="0"/>
          <line id="dshot-1" x1="524" y1="1158" x2="579" y2="1136" opacity="0"/>
          <line id="dshot-2" x1="516" y1="1166" x2="571" y2="1144" opacity="0"/>
          <line id="dshot-3" x1="522" y1="1174" x2="577" y2="1152" opacity="0"/>
          <line id="dshot-4" x1="518" y1="1182" x2="573" y2="1160" opacity="0"/>
          <line id="dshot-5" x1="526" y1="1190" x2="581" y2="1168" opacity="0"/>
          <line id="dshot-6" x1="520" y1="1198" x2="575" y2="1176" opacity="0"/>
        </g>
        <g fill="#efa63a">
          <ellipse id="petal-0" cx="330" cy="420" rx="9" ry="5" opacity="0"/>
          <ellipse id="petal-1" cx="420" cy="380" rx="8" ry="5" opacity="0"/>
          <ellipse id="petal-2" cx="510" cy="440" rx="9" ry="5" opacity="0"/>
          <ellipse id="petal-3" cx="600" cy="390" rx="8" ry="5" opacity="0"/>
          <ellipse id="petal-4" cx="690" cy="430" rx="9" ry="5" opacity="0"/>
          <ellipse id="petal-5" cx="380" cy="470" rx="7" ry="4" opacity="0"/>
          <ellipse id="petal-6" cx="560" cy="470" rx="7" ry="4" opacity="0"/>
          <ellipse id="petal-7" cx="650" cy="360" rx="7" ry="4" opacity="0"/>
        </g>
      </svg>
    </div>

    <div id="soft-flash" class="abs" style="left:0; top:0; width:1080px; height:1920px; background:#fff9dc; opacity:0;"></div>

  </div>
  </div>

  {chr(10).join('  ' + s for s in stamps)}

  {chr(10).join('  ' + c for c in caps)}

  <div id="title-card" class="clip" data-start="0" data-duration="{fmt(te)}" data-track-index="4">
    <div id="title-inner">
      <div id="kicker">{html.escape(KICKER)}</div>
      <div id="title-chip">{html.escape(TITLE)}</div>
    </div>
  </div>

  {chr(10).join('  ' + a for a in audio)}

  <script src="assets/gsap.min.js"></script>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join('    ' + t for t in tw)}
    window.__timelines = window.__timelines || {{}};
    window.__timelines.reel = tl;
  </script>
</div>
</body>
</html>
"""
(project / "index.html").write_text(page, encoding="utf-8")
print(f"composed {TITLE!r}: {total:.2f}s, {len(captions)} captions, {len(lines)} lines")
