#!/usr/bin/env python3
"""Compose "The Moon in the Bucket" — night-courtyard cartoon episode.

Usage: cartoon/episodes/moon-bucket/compose.py --project <dir>

Anu finds the moon fallen into the water bucket, shatters it with a touch,
and Dadu teaches her that still water heals — 14 beats, three voices, a frog.
Same proven mechanics as last-laddu (see that composer and cartoon/README.md):
camera hard-cuts per line with push-in drift, per-speaker attr(ry) mouth
flaps, svgOrigin for SVG sub-part motion, hard sets at fade boundaries, and
immediateRender: false on every fromTo whose "from" state must not exist
before its cue (fromTo renders its from-values at time zero otherwise).
"""
import argparse
import html
import json
import pathlib

ap = argparse.ArgumentParser(description="Compose the Moon in the Bucket episode into index.html.")
ap.add_argument("--project", required=True)
project = pathlib.Path(ap.parse_args().project).expanduser().resolve()
meta = json.load(open(project / "audio_meta.json"))
captions = json.load(open(project / "captions.json"))
timeline = json.load(open(project / "timeline.json"))
pj = json.load(open(project / "project.json"))
cast = json.load(open(project / "cast.json"))

total = timeline["total"]
lines = meta["lines"]
if len(lines) != 14:
    raise SystemExit(
        f"this episode's staging is written for its 14 lines (got {len(lines)}) — "
        "copy this script and re-choreograph CAM + staging for a new script"
    )
fmt = lambda v: f"{v:.3f}"
SPEAKERS = cast["speakers"]
TINT = cast.get("tints", {})
MOUTH = {"kid": "#mouth-kid", "gpa": "#mouth-gpa"}

def line_of(t):
    best = 1
    for ln in lines:
        if t >= ln["start"] - 0.01:
            best = ln["index"]
    return best

def win(i):
    ln = lines[i - 1]
    return ln["start"], ln["start"] + ln["duration"]

CAM = {
    1: (1.05, 540, 1000), 2: (1.70, 310, 1150), 3: (2.20, 560, 1370), 4: (1.70, 310, 1150),
    5: (2.30, 560, 1370), 6: (1.80, 310, 1130), 7: (1.40, 360, 1100), 8: (1.50, 480, 1250),
    9: (1.80, 340, 1080), 10: (1.50, 620, 1360), 11: (2.20, 560, 1370), 12: (1.70, 310, 1120),
    13: (1.70, 340, 1080), 14: (1.00, 540, 960),
}

def cam_xy(s, px, py):
    x = 540 - s * px
    y = 960 - s * py
    x = max(1080 - 1080 * s, min(0, x))
    y = max(1920 - 1920 * s, min(0, y))
    return x, y

tw = []
for i in range(1, 15):
    s, px, py = CAM[i]
    t0, t1 = win(i)
    if i == 14:
        t1 = total
    x0, y0 = cam_xy(s, px, py)
    s2 = s * 1.045
    x1, y1 = cam_xy(s2, px, py)
    tw.append(f'tl.set("#world", {{scale: {s:.3f}, x: {x0:.1f}, y: {y0:.1f}}}, {fmt(t0)});')
    tw.append(f'tl.to("#world", {{scale: {s2:.3f}, x: {x1:.1f}, y: {y1:.1f}, duration: {fmt(max(0.3, t1 - t0))}, ease: "none"}}, {fmt(t0)});')

# idle life
for sel, period, amp in [("#anu", 1.5, 4), ("#dadu", 1.8, 4), ("#frog", 1.1, 2)]:
    reps = max(1, int(total / period) + 1)
    tw.append(f'tl.to("{sel}", {{y: {amp}, duration: {period}, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, 0);')
# star twinkles, staggered across the whole night
for k, (period, at) in enumerate([(1.7, 0.2), (2.3, 0.8), (1.9, 1.5), (2.6, 0.5), (2.1, 1.1), (2.9, 0.3)]):
    reps = max(1, int((total - at) / period) + 1)
    tw.append(f'tl.to("#star-{k}", {{opacity: 0.25, duration: {period}, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, {fmt(at)});')
# moon glow breathing
reps = max(1, int(total / 3.2) + 1)
tw.append(f'tl.to("#moon-glow", {{opacity: 0.5, duration: 3.2, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, 0);')

# blinks
BLINK = [("#eyes-kid", '"120 96"', 1.1, total), ("#eyes-gpa", '"140 92"', win(7)[0] + 1.0, total), ("#eyes-frog", '"70 22"', 0.7, total)]
for sel, org, t, end in BLINK:
    while t < end - 0.6:
        tw.append(f'tl.to("{sel}", {{scaleY: 0.1, svgOrigin: {org}, duration: 0.07, repeat: 1, yoyo: true, ease: "none"}}, {fmt(t)});')
        t += 3.1

# mouths
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

# --- staging, line by line ---------------------------------------------------
t1a, t1b = win(1)   # lean in, gasp
tw.append(f'tl.to("#anu", {{x: 24, duration: 1.0, ease: "power1.inOut"}}, {fmt(t1a + 0.3)});')
tw.append(f'tl.to("#anu", {{y: -30, duration: 0.16, repeat: 1, yoyo: true, ease: "power2.out"}}, {fmt(t1b - 0.5)});')
t2a, t2b = win(2)   # call + point
for k in range(2):
    tw.append(f'tl.to("#anu", {{y: -22, duration: 0.18, repeat: 1, yoyo: true, ease: "power1.out"}}, {fmt(t2a + 0.2 + k * 0.6)});')
tw.append(f'tl.to("#arm-kid", {{rotation: -55, svgOrigin: "170 210", duration: 0.35, ease: "back.out(1.6)"}}, {fmt(t2a + 0.2)});')
tw.append(f'tl.to("#arm-kid", {{rotation: 0, svgOrigin: "170 210", duration: 0.4}}, {fmt(t2b)});')
t3a, t3b = win(3)   # reflection shimmer
tw.append(f'tl.to("#reflection", {{opacity: 0.75, scale: 1.06, svgOrigin: "560 1352", duration: 0.5, repeat: {max(1, int((t3b - t3a) / 0.5) - 1)}, yoyo: true, ease: "sine.inOut"}}, {fmt(t3a)});')
t4a, t4b = win(4)   # crouch to the bucket
tw.append(f'tl.to("#anu", {{scaleY: 0.94, transformOrigin: "50% 100%", duration: 0.3, ease: "power1.inOut"}}, {fmt(t4a + 0.2)});')
t5a, t5b = win(5)   # reach... SHATTER
shatter = t5a + (t5b - t5a) * 0.45
tw.append(f'tl.to("#arm-kid", {{rotation: -95, svgOrigin: "170 210", duration: 0.6, ease: "power1.inOut"}}, {fmt(t5a)});')
tw.append(f'tl.to("#anu", {{x: 40, duration: 0.6, ease: "power1.inOut"}}, {fmt(t5a)});')
tw.append(f'tl.set("#reflection", {{opacity: 0}}, {fmt(shatter)});')
for k, (dx, dy) in enumerate([(-46, -10), (42, -14), (-8, 22)]):
    tw.append(f'tl.fromTo("#shard-{k}", {{x: 0, y: 0, opacity: 1}}, {{x: {dx}, y: {dy}, opacity: 0.55, rotation: {(-1) ** k * 18}, duration: 0.8, ease: "power2.out", immediateRender: false}}, {fmt(shatter)});')
for k in range(2):
    tw.append(f'tl.fromTo("#ripple-{k}", {{scale: 0.3, opacity: 0.9, svgOrigin: "560 1352"}}, {{scale: {1.5 + k * 0.6}, opacity: 0, duration: {0.9 + k * 0.3}, ease: "power1.out", immediateRender: false}}, {fmt(shatter + k * 0.15)});')
tw.append(f'tl.to("#arm-kid", {{rotation: 0, svgOrigin: "170 210", duration: 0.4}}, {fmt(shatter + 0.4)});')
tw.append(f'tl.to("#anu", {{x: 24, scaleY: 1.0, transformOrigin: "50% 100%", duration: 0.4}}, {fmt(shatter + 0.4)});')
t6a, t6b = win(6)   # panic jitter
for k in range(4):
    tw.append(f'tl.to("#anu", {{x: {24 + (6 if k % 2 == 0 else -6)}, duration: 0.07, repeat: 1, yoyo: true}}, {fmt(t6a + 0.3 + k * 0.16)});')
t7a, t7b = win(7)   # Dadu arrives from the house
tw.append(f'tl.fromTo("#dadu", {{x: -320}}, {{x: 0, duration: {fmt(min(1.4, t7b - t7a))}, ease: "power2.out"}}, {fmt(t7a)});')
t8a, t8b = win(8)   # look down, up, down
third = (t8b - t8a) / 3
for k, rot in enumerate([7, -9, 7]):
    tw.append(f'tl.to("#head-gpa", {{rotation: {rot}, svgOrigin: "140 160", duration: 0.4, ease: "power1.inOut"}}, {fmt(t8a + k * third)});')
tw.append(f'tl.to("#head-gpa", {{rotation: 0, svgOrigin: "140 160", duration: 0.4}}, {fmt(t8b)});')
t9a, t9b = win(9)   # the idea: finger up + bounce
tw.append(f'tl.to("#arm-gpa", {{rotation: -70, svgOrigin: "75 250", duration: 0.4, ease: "back.out(1.8)"}}, {fmt(t9a + 0.15)});')
tw.append(f'tl.to("#dadu", {{y: -16, duration: 0.18, repeat: 1, yoyo: true, ease: "power1.out"}}, {fmt(t9a + 0.1)});')
tw.append(f'tl.to("#arm-gpa", {{rotation: 0, svgOrigin: "75 250", duration: 0.5}}, {fmt(t9b)});')
t10a, t10b = win(10)  # stillness; frog blinks twice; fireflies drift
tw.append(f'tl.to("#eyes-frog", {{scaleY: 0.1, svgOrigin: "70 22", duration: 0.08, repeat: 1, yoyo: true}}, {fmt(t10a + 0.8)});')
tw.append(f'tl.to("#eyes-frog", {{scaleY: 0.1, svgOrigin: "70 22", duration: 0.08, repeat: 1, yoyo: true}}, {fmt(t10a + 1.3)});')
for k in range(2):
    tw.append(f'tl.fromTo("#firefly-{k}", {{opacity: 0}}, {{opacity: 0.9, duration: 0.6, repeat: 3, yoyo: true}}, {fmt(t10a + k * 0.9)});')
    tw.append(f'tl.to("#firefly-{k}", {{x: {30 - k * 60}, y: -40, duration: {fmt(t10b - t10a)}, ease: "sine.inOut"}}, {fmt(t10a)});')
t11a, t11b = win(11)  # the heal
heal = t11a + (t11b - t11a) * 0.45
for k in range(3):
    tw.append(f'tl.to("#shard-{k}", {{x: 0, y: 0, opacity: 0, rotation: 0, duration: 0.8, ease: "power1.in"}}, {fmt(t11a)});')
tw.append(f'tl.fromTo("#reflection", {{opacity: 0, scale: 0.7, svgOrigin: "560 1352"}}, {{opacity: 1, scale: 1.0, duration: {fmt(t11b - heal)}, ease: "sine.out", immediateRender: false}}, {fmt(heal)});')
t12a, t12b = win(12)  # joy jumps
for k in range(2):
    tw.append(f'tl.to("#anu", {{y: -34, duration: 0.2, repeat: 1, yoyo: true, ease: "power1.out"}}, {fmt(t12a + 0.2 + k * 0.55)});')
tw.append(f'tl.to("#arm-kid", {{rotation: -140, svgOrigin: "170 210", duration: 0.3, ease: "back.out(1.6)"}}, {fmt(t12a + 0.2)});')
tw.append(f'tl.to("#arm-kid", {{rotation: 0, svgOrigin: "170 210", duration: 0.4}}, {fmt(t12b)});')
t13a, t13b = win(13)  # warm nod
for k in range(2):
    tw.append(f'tl.to("#head-gpa", {{rotation: 5, svgOrigin: "140 160", duration: 0.35, repeat: 1, yoyo: true, ease: "sine.inOut"}}, {fmt(t13a + 0.3 + k * 0.9)});')
t14a = win(14)[0]     # wide: frog hops onto the rim; sky moon answers
tw.append(f'tl.to("#frog", {{x: -55, y: -64, duration: 0.45, ease: "power2.out"}}, {fmt(t14a + 1.0)});')
tw.append(f'tl.to("#frog", {{y: -58, duration: 0.15, ease: "bounce.out"}}, {fmt(t14a + 1.45)});')
tw.append(f'tl.to("#moon-glow", {{opacity: 0.85, duration: 0.8, repeat: 1, yoyo: true, ease: "sine.inOut"}}, {fmt(t14a + 1.6)});')

te = win(1)[1] + 0.3
tw.append(f'tl.to("#title-card", {{opacity: 0, duration: 0.35}}, {fmt(te - 0.35)});')
tw.append(f'tl.set("#title-card", {{opacity: 0}}, {fmt(te)});')

caps = []
for c in captions:
    tint = TINT.get(SPEAKERS[line_of(c["start"]) - 1], "#ffffff")
    dur = max(0.12, c["end"] - c["start"])
    caps.append(
        f'<div class="caption clip" style="color: {tint};" data-start="{fmt(c["start"])}" '
        f'data-duration="{fmt(dur)}" data-track-index="4">{html.escape(c["text"])}</div>'
    )
audio = []
for ln in lines:
    audio.append(
        f'<audio id="voice-line-{ln["index"]:02d}" class="clip" src="{ln["file"]}" '
        f'data-start="{fmt(ln["start"])}" data-duration="{fmt(ln["duration"])}" data-track-index="5"></audio>'
    )
dadu_start = win(7)[0]
TITLE = pj.get("title", "The Moon in the Bucket")
KICKER = pj.get("topic", "a tiny cartoon").upper()

page = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{html.escape(TITLE)}</title></head>
<body>
<div id="stage" data-composition-id="reel" data-start="0" data-duration="{fmt(total)}"
     data-width="1080" data-height="1920" data-fps="30">
  <style>
    #stage {{ background: #0a1228; font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; overflow: hidden; }}
    #world {{ position: absolute; inset: 0; transform-origin: 0px 0px; }}
    .abs {{ position: absolute; }}
    .caption {{ position: absolute; top: 1380px; left: 50%; transform: translateX(-50%);
      max-width: 840px; background: rgba(0, 0, 0, 0.85); border-radius: 18px; padding: 18px 34px;
      font-size: 54px; font-weight: 700; text-align: center; }}
    #title-card {{ position: absolute; top: 120px; left: 0; right: 120px; margin: 0 auto; width: fit-content;
      text-align: center; z-index: 5; }}
    #kicker {{ color: #9db8f0; font-size: 38px; font-weight: 800; letter-spacing: 9px; }}
    #title-chip {{ margin-top: 16px; background: rgba(8, 12, 28, 0.92); border: 2px solid rgba(157, 184, 240, 0.55);
      border-radius: 22px; padding: 18px 42px; color: #fff; font-size: 64px; font-weight: 800; }}
  </style>

  <div id="world" class="clip" data-start="0" data-duration="{fmt(total)}" data-track-index="0">

    <svg class="abs" style="left:0; top:0;" width="1080" height="1920" viewBox="0 0 1080 1920">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#070d1f"/><stop offset="0.75" stop-color="#14224a"/><stop offset="1" stop-color="#1d2f5e"/>
        </linearGradient>
        <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stop-color="#fdf6d8" stop-opacity="0.7"/><stop offset="1" stop-color="#fdf6d8" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="1080" height="1300" fill="url(#sky)"/>
      <rect x="0" y="1300" width="1080" height="620" fill="#241d33"/>
      <ellipse cx="540" cy="1300" rx="720" ry="60" fill="#2c2440"/>
      <g fill="#ffffff">
        <circle id="star-0" cx="140" cy="240" r="5"/><circle id="star-1" cx="420" cy="150" r="4"/>
        <circle id="star-2" cx="640" cy="260" r="5"/><circle id="star-3" cx="240" cy="480" r="4"/>
        <circle id="star-4" cx="960" cy="140" r="4"/><circle id="star-5" cx="520" cy="420" r="3"/>
      </g>
      <circle id="moon-glow" cx="830" cy="330" r="190" fill="url(#glow)" opacity="0.35"/>
      <circle cx="830" cy="330" r="92" fill="#f4ecc8"/>
      <circle cx="800" cy="305" r="14" fill="#e3d9ae"/><circle cx="856" cy="352" r="18" fill="#e3d9ae"/>
      <circle cx="838" cy="300" r="8" fill="#e3d9ae"/>
      <path d="M0 700 L250 700 L250 1300 L0 1300 Z" fill="#171226"/>
      <path d="M-20 710 L135 600 L270 710 Z" fill="#100d1c"/>
      <rect x="60" y="800" width="120" height="140" rx="10" fill="#ffb84d" opacity="0.9"/>
      <line x1="120" y1="800" x2="120" y2="940" stroke="#171226" stroke-width="10"/>
      <line x1="60" y1="870" x2="180" y2="870" stroke="#171226" stroke-width="10"/>
      <rect x="190" y="1120" width="60" height="180" rx="8" fill="#100d1c"/>
      <path d="M980 1300 Q1000 1080 1040 1050 Q1064 1080 1050 1300 Z" fill="#171226"/>
      <g id="bucket">
        <path d="M480 1330 L640 1330 L620 1470 L500 1470 Z" fill="#5a6a7c"/>
        <path d="M480 1330 L640 1330 L636 1352 L484 1352 Z" fill="#465566"/>
        <ellipse cx="560" cy="1330" rx="80" ry="16" fill="#77879a"/>
        <ellipse cx="560" cy="1330" rx="66" ry="12" fill="#0c1d3d"/>
        <ellipse id="reflection" cx="560" cy="1330" rx="34" ry="9" fill="#f2ecd0"/>
        <ellipse id="shard-0" cx="548" cy="1330" rx="12" ry="4" fill="#f2ecd0" opacity="0"/>
        <ellipse id="shard-1" cx="572" cy="1332" rx="10" ry="3.5" fill="#f2ecd0" opacity="0"/>
        <ellipse id="shard-2" cx="560" cy="1327" rx="8" ry="3" fill="#f2ecd0" opacity="0"/>
        <ellipse id="ripple-0" cx="560" cy="1330" rx="40" ry="10" fill="none" stroke="#9db4d8" stroke-width="3" opacity="0"/>
        <ellipse id="ripple-1" cx="560" cy="1330" rx="40" ry="10" fill="none" stroke="#9db4d8" stroke-width="2" opacity="0"/>
      </g>
      <circle id="firefly-0" cx="760" cy="1240" r="6" fill="#ffe27a" opacity="0"/>
      <circle id="firefly-1" cx="340" cy="1200" r="5" fill="#ffe27a" opacity="0"/>
    </svg>

    <div id="anu" class="abs clip" style="left:200px; top:1030px; width:240px; height:440px;"
         data-start="0" data-duration="{fmt(total)}" data-track-index="2">
      <svg width="240" height="440" viewBox="0 0 240 440">
        <circle cx="52" cy="96" r="26" fill="#2b1a10"/>
        <circle cx="188" cy="96" r="26" fill="#2b1a10"/>
        <circle cx="120" cy="92" r="64" fill="#f2b98b"/>
        <path d="M60 82 Q64 34 120 32 Q176 34 180 82 Q140 58 104 64 Q80 70 60 82 Z" fill="#2b1a10"/>
        <g id="eyes-kid">
          <circle cx="98" cy="94" r="12" fill="#fff"/><circle cx="142" cy="94" r="12" fill="#fff"/>
          <circle cx="100" cy="96" r="6" fill="#241408"/><circle cx="144" cy="96" r="6" fill="#241408"/>
          <circle cx="102" cy="93" r="2.2" fill="#fff"/><circle cx="146" cy="93" r="2.2" fill="#fff"/>
        </g>
        <path d="M86 74 Q98 68 110 74" stroke="#241408" stroke-width="5" fill="none" stroke-linecap="round"/>
        <path d="M130 74 Q142 68 154 74" stroke="#241408" stroke-width="5" fill="none" stroke-linecap="round"/>
        <circle cx="86" cy="118" r="10" fill="#eda28a" opacity="0.5"/>
        <circle cx="154" cy="118" r="10" fill="#eda28a" opacity="0.5"/>
        <ellipse id="mouth-kid" cx="120" cy="128" rx="13" ry="3" fill="#8c3040"/>
        <rect x="108" y="152" width="24" height="16" fill="#f2b98b"/>
        <path d="M64 320 Q66 172 120 168 Q174 172 176 320 Q120 336 64 320 Z" fill="#b9a7e6"/>
        <path d="M64 250 Q48 280 56 320 L80 314 Q72 282 80 252 Z" fill="#f2b98b"/>
        <g id="arm-kid">
          <path d="M170 210 Q206 240 200 296 L178 302 Q182 258 158 232 Z" fill="#f2b98b"/>
          <circle cx="190" cy="304" r="14" fill="#f2b98b"/>
        </g>
        <rect x="88" y="330" width="26" height="88" fill="#f2b98b"/>
        <rect x="126" y="330" width="26" height="88" fill="#f2b98b"/>
        <rect x="80" y="414" width="42" height="18" rx="8" fill="#7a5f9e"/>
        <rect x="120" y="414" width="42" height="18" rx="8" fill="#7a5f9e"/>
      </svg>
    </div>

    <div id="dadu" class="abs clip" style="left:20px; top:940px; width:280px; height:540px;"
         data-start="{fmt(dadu_start)}" data-duration="{fmt(total - dadu_start)}" data-track-index="2">
      <svg width="280" height="540" viewBox="0 0 280 540">
        <g id="head-gpa">
          <circle cx="140" cy="96" r="60" fill="#e5a87e"/>
          <path d="M84 86 Q88 54 116 46 Q102 70 110 86 Z" fill="#d5d5d5"/>
          <path d="M196 86 Q192 54 164 46 Q178 70 170 86 Z" fill="#d5d5d5"/>
          <g id="eyes-gpa">
            <circle cx="118" cy="92" r="10" fill="#fff"/><circle cx="162" cy="92" r="10" fill="#fff"/>
            <circle cx="120" cy="94" r="5" fill="#241408"/><circle cx="164" cy="94" r="5" fill="#241408"/>
          </g>
          <path d="M104 76 Q116 70 128 76" stroke="#c0c0c0" stroke-width="6" fill="none" stroke-linecap="round"/>
          <path d="M152 76 Q164 70 176 76" stroke="#c0c0c0" stroke-width="6" fill="none" stroke-linecap="round"/>
          <path d="M114 122 Q140 134 166 122" stroke="#d5d5d5" stroke-width="9" fill="none" stroke-linecap="round"/>
          <ellipse id="mouth-gpa" cx="140" cy="138" rx="12" ry="3" fill="#7a2c38"/>
        </g>
        <rect x="126" y="152" width="28" height="18" fill="#e5a87e"/>
        <path d="M78 390 Q80 176 140 172 Q200 176 202 390 L202 524 Q140 540 78 524 Z" fill="#e8ddc4"/>
        <g id="arm-gpa">
          <path d="M75 250 Q38 290 46 348 L70 356 Q64 302 88 274 Z" fill="#e5a87e"/>
          <circle cx="58" cy="360" r="16" fill="#e5a87e"/>
        </g>
        <path d="M205 250 Q240 290 232 348 L208 354 Q214 302 194 274 Z" fill="#e5a87e"/>
      </svg>
    </div>

    <div id="frog" class="abs clip" style="left:668px; top:1408px; width:140px; height:80px;"
         data-start="0" data-duration="{fmt(total)}" data-track-index="2">
      <svg width="140" height="80" viewBox="0 0 140 80">
        <ellipse cx="70" cy="52" rx="46" ry="26" fill="#5a9e4a"/>
        <circle cx="52" cy="22" r="14" fill="#5a9e4a"/>
        <circle cx="88" cy="22" r="14" fill="#5a9e4a"/>
        <g id="eyes-frog">
          <circle cx="52" cy="20" r="8" fill="#fff"/><circle cx="88" cy="20" r="8" fill="#fff"/>
          <circle cx="52" cy="21" r="4" fill="#1c2e14"/><circle cx="88" cy="21" r="4" fill="#1c2e14"/>
        </g>
        <path d="M56 44 Q70 52 84 44" stroke="#3d6e32" stroke-width="4" fill="none" stroke-linecap="round"/>
        <ellipse cx="34" cy="72" rx="14" ry="7" fill="#4a8a3c"/>
        <ellipse cx="106" cy="72" rx="14" ry="7" fill="#4a8a3c"/>
      </svg>
    </div>

  </div>

  {chr(10).join('  ' + c for c in caps)}

  <div id="title-card" class="clip" data-start="0" data-duration="{fmt(te)}" data-track-index="4">
    <div id="kicker">{html.escape(KICKER)}</div>
    <div id="title-chip">{html.escape(TITLE)}</div>
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
