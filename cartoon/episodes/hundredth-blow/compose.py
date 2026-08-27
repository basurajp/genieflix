#!/usr/bin/env python3
"""Compose "The Hundredth Blow" — dawn-quarry motivational episode.

Proven mechanics (see cartoon/README.md): camera hard-cuts per line with
push-in drift, attr(ry) mouths, svgOrigin for SVG parts, hard sets at fade
boundaries, immediateRender: false on cued fromTo effects.
Usage: cartoon/episodes/hundredth-blow/compose.py --project <dir>

Kabir strikes a rock everyone gave up on; the hundredth blow splits it —
"it was every blow before." 14 beats, three voices (narrator, Kabir, a
doubting passerby), strike choreography, and the split at line 10.
"""
import argparse
import html
import json
import pathlib

ap = argparse.ArgumentParser(description="Compose the Hundredth Blow episode into index.html.")
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
MOUTH = {"kab": "#mouth-kab", "pas": "#mouth-pas"}

def line_of(t):
    best = 1
    for ln in lines:
        if t >= ln["start"] - 0.01:
            best = ln["index"]
    return best

def win(i):
    ln = lines[i - 1]
    return ln["start"], ln["start"] + ln["duration"]

STAMPS = ["THE GIVEN-UP ROCK", "KABIR", "EVERY STONE BREAKS", "BLOW × 10", "GIVE IT UP?",
          "BLOW × 50", "ONE MORE", "BLOW × 99", "THE 100TH", "IT SPLIT",
          "A MIRACLE?", "EVERY BLOW BEFORE", "WHEN NOTHING MOVES", "REFUSE TO STOP"]

CAM = {
    1: (1.15, 660, 1250), 2: (1.60, 310, 1170), 3: (1.80, 310, 1150), 4: (1.35, 480, 1260),
    5: (1.60, 170, 1220), 6: (1.70, 520, 1300), 7: (1.90, 310, 1140), 8: (1.80, 620, 1300),
    9: (1.50, 480, 1250), 10: (1.25, 660, 1280), 11: (1.30, 400, 1200), 12: (1.80, 310, 1140),
    13: (1.15, 540, 1100), 14: (1.00, 540, 960),
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

# idle life + slow sunrise across the whole video
for sel, period, amp in [("#kabir", 1.5, 4), ("#passerby", 1.8, 3)]:
    reps = max(1, int(total / period) + 1)
    tw.append(f'tl.to("{sel}", {{y: {amp}, duration: {period}, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, 0);')
tw.append(f'tl.to("#sun", {{y: -70, duration: {fmt(total)}, ease: "none"}}, 0);')
tw.append(f'tl.to("#bird-0", {{x: 320, y: -30, duration: {fmt(total)}, ease: "none"}}, 0);')
tw.append(f'tl.to("#bird-1", {{x: -280, y: -18, duration: {fmt(total)}, ease: "none"}}, 0);')
reps = max(1, int(total / 3.0) + 1)
tw.append(f'tl.to("#sun-glow", {{opacity: 0.55, duration: 3.0, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, 0);')

# blinks
BLINK = [("#eyes-kab", '"130 90"', 1.2, total), ("#eyes-pas", '"110 84"', win(5)[0] + 0.6, total)]
for sel, org, t, end in BLINK:
    while t < end - 0.6:
        tw.append(f'tl.to("{sel}", {{scaleY: 0.1, svgOrigin: {org}, duration: 0.07, repeat: 1, yoyo: true, ease: "none"}}, {fmt(t)});')
        t += 3.0

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

# stamps pop per line
for s in range(1, 15):
    t0 = win(s)[0]
    tw.append(f'tl.fromTo("#stamp-{s}", {{scale: 0.6, opacity: 0, rotation: -4}}, '
              f'{{scale: 1, opacity: 1, rotation: -2, duration: 0.35, ease: "back.out(2)"}}, {fmt(t0)});')

def strike(t, hard=1.0):
    """One hammer blow at time t: windup, hit, rock shake, dust puff."""
    out = [
        f'tl.to("#arm-kab", {{rotation: -75, svgOrigin: "150 200", duration: 0.28, ease: "power1.out"}}, {fmt(t)});',
        f'tl.to("#arm-kab", {{rotation: 30, svgOrigin: "150 200", duration: 0.12, ease: "power3.in"}}, {fmt(t + 0.28)});',
        f'tl.to("#arm-kab", {{rotation: 0, svgOrigin: "150 200", duration: 0.3, ease: "power1.out"}}, {fmt(t + 0.55)});',
        f'tl.to("#rock", {{x: {4 * hard}, duration: 0.05, repeat: 3, yoyo: true}}, {fmt(t + 0.40)});',
        f'tl.set("#rock", {{x: 0}}, {fmt(t + 0.62)});',
    ]
    for k in range(2):
        out.append(
            f'tl.fromTo("#dust-{k}", {{x: 0, y: 0, opacity: 0.9, scale: 0.5}}, '
            f'{{x: {(-1) ** k * (26 + 10 * k)}, y: {-24 - 8 * k}, opacity: 0, scale: 1.1, duration: 0.5, '
            f'ease: "power1.out", immediateRender: false}}, {fmt(t + 0.40)});'
        )
        out.append(f'tl.set("#dust-{k}", {{opacity: 0}}, {fmt(t + 0.95)});')
    return out

t4a, t4b = win(4)
for k in range(3):
    tw += strike(t4a + 0.3 + k * ((t4b - t4a - 0.9) / 3))
t5a, t5b = win(5)   # the doubter appears
tw.append(f'tl.fromTo("#passerby", {{x: -260}}, {{x: 0, duration: 0.9, ease: "power2.out"}}, {fmt(t5a)});')
tw.append(f'tl.to("#passerby", {{x: -260, duration: 0.8, ease: "power2.in"}}, {fmt(t5b + 0.1)});')
t6a, t6b = win(6)   # faster, tired strikes + sweat
for k in range(4):
    tw += strike(t6a + 0.15 + k * ((t6b - t6a - 0.8) / 4), hard=1.4)
tw.append(f'tl.fromTo("#sweat", {{opacity: 0, y: 0}}, {{opacity: 1, y: 26, duration: 0.7, ease: "power1.in", immediateRender: false}}, {fmt(t6a + 1.2)});')
tw.append(f'tl.set("#sweat", {{opacity: 0}}, {fmt(t6a + 1.95)});')
t7a, t7b = win(7)   # heavy breath: torso rise
tw.append(f'tl.to("#kabir", {{scaleY: 0.97, transformOrigin: "50% 100%", duration: 0.5, repeat: 3, yoyo: true, ease: "sine.inOut"}}, {fmt(t7a)});')
t8a, t8b = win(8)   # 98, 99
tw += strike(t8a + 0.2)
tw += strike(t8a + 0.2 + (t8b - t8a) / 2)
tw.append(f'tl.to("#crack", {{opacity: 1, duration: 0.3}}, {fmt(t8b - 0.4)});')
t9a, t9b = win(9)   # the long windup... and the blow lands at the line's end
tw.append(f'tl.to("#arm-kab", {{rotation: -110, svgOrigin: "150 200", duration: {fmt(max(0.8, t9b - t9a - 0.55))}, ease: "power1.inOut"}}, {fmt(t9a)});')
tw.append(f'tl.to("#arm-kab", {{rotation: 32, svgOrigin: "150 200", duration: 0.13, ease: "power4.in"}}, {fmt(t9b - 0.45)});')
t10a, t10b = win(10)  # THE SPLIT
tw.append(f'tl.fromTo("#flash", {{opacity: 0}}, {{opacity: 0.85, duration: 0.09, repeat: 1, yoyo: true, immediateRender: false}}, {fmt(t10a)});')
tw.append(f'tl.to("#rock-l", {{rotation: -13, x: -38, svgOrigin: "560 1450", duration: 0.7, ease: "power2.out"}}, {fmt(t10a + 0.05)});')
tw.append(f'tl.to("#rock-r", {{rotation: 13, x: 38, svgOrigin: "760 1450", duration: 0.7, ease: "power2.out"}}, {fmt(t10a + 0.05)});')
tw.append(f'tl.set("#crack", {{opacity: 0}}, {fmt(t10a + 0.05)});')
tw.append(f'tl.fromTo("#rays", {{scale: 0.3, opacity: 0, svgOrigin: "660 1330"}}, {{scale: 1.25, opacity: 0.8, duration: 0.6, ease: "power2.out", immediateRender: false}}, {fmt(t10a + 0.1)});')
tw.append(f'tl.to("#rays", {{opacity: 0, duration: 0.8}}, {fmt(t10a + 0.9)});')
for k in range(4):
    tw.append(
        f'tl.fromTo("#burst-{k}", {{x: 0, y: 0, opacity: 1, scale: 0.6}}, '
        f'{{x: {(-1) ** k * (40 + 22 * k)}, y: {-46 - 14 * k}, opacity: 0, scale: 1.3, duration: 0.9, '
        f'ease: "power2.out", immediateRender: false}}, {fmt(t10a + 0.05)});'
    )
    tw.append(f'tl.set("#burst-{k}", {{opacity: 0}}, {fmt(t10a + 1.0)});')
for k in range(5):
    tw.append(f'tl.to("#shaker", {{x: {9 if k % 2 == 0 else -9}, duration: 0.05}}, {fmt(t10a + 0.05 + k * 0.05)});')
tw.append(f'tl.set("#shaker", {{x: 0}}, {fmt(t10a + 0.35)});')
tw.append(f'tl.to("#arm-kab", {{rotation: 0, svgOrigin: "150 200", duration: 0.6, ease: "power1.out"}}, {fmt(t10a + 0.5)});')
t11a, t11b = win(11)  # the doubter returns, astonished
tw.append(f'tl.to("#passerby", {{x: 0, duration: 0.8, ease: "power2.out"}}, {fmt(t11a)});')
tw.append(f'tl.to("#passerby", {{y: -26, duration: 0.2, repeat: 1, yoyo: true, ease: "power1.out"}}, {fmt(t11a + 0.9)});')
t12a, t12b = win(12)  # hammer to shoulder, quiet pride
tw.append(f'tl.to("#arm-kab", {{rotation: -38, svgOrigin: "150 200", duration: 0.6, ease: "power1.inOut"}}, {fmt(t12a)});')
t14a = win(14)[0]     # dawn floods in
tw.append(f'tl.fromTo("#dawnlight", {{opacity: 0}}, {{opacity: 0.28, duration: {fmt(total - t14a)}, ease: "sine.in", immediateRender: false}}, {fmt(t14a)});')

te = win(1)[1] + 0.3
tw.append(f'tl.to("#title-inner", {{opacity: 0, duration: 0.35}}, {fmt(te - 0.50)});')
tw.append(f'tl.set("#title-inner", {{opacity: 0}}, {fmt(te - 0.10)});')

caps = []
for c in captions:
    tint = TINT.get(SPEAKERS[line_of(c["start"]) - 1], "#ffffff")
    dur = max(0.12, c["end"] - c["start"])
    caps.append(
        f'<div class="caption clip" style="color: {tint};" data-start="{fmt(c["start"])}" '
        f'data-duration="{fmt(dur)}" data-track-index="4">{html.escape(c["text"])}</div>'
    )
stamps = []
for i in range(1, 15):
    t0, _ = win(i)
    dur = (win(i + 1)[0] - t0) if i < 14 else (total - t0)
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
pas_start = win(5)[0]
TITLE = pj.get("title", "The Hundredth Blow")
KICKER = pj.get("topic", "a story about not stopping").upper()

page = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{html.escape(TITLE)}</title></head>
<body>
<div id="stage" data-composition-id="reel" data-start="0" data-duration="{fmt(total)}"
     data-width="1080" data-height="1920" data-fps="30">
  <style>
    #stage {{ background: #2a1420; font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; overflow: hidden; }}
    #world, #shaker {{ position: absolute; inset: 0; }}
    #world {{ transform-origin: 0px 0px; }}
    .abs {{ position: absolute; }}
    .caption {{ position: absolute; top: 1380px; left: 50%; transform: translateX(-50%);
      max-width: 840px; background: rgba(0, 0, 0, 0.85); border-radius: 18px; padding: 18px 34px;
      font-size: 54px; font-weight: 700; text-align: center; }}
    .stamp {{ position: absolute; top: 300px; left: 50%; transform: translateX(-50%) rotate(-2deg);
      background: rgba(30, 14, 10, 0.88); border: 2px solid #d98a3a; color: #ffd9a0; border-radius: 14px;
      padding: 14px 32px; font-size: 42px; font-weight: 800; letter-spacing: 4px; white-space: nowrap; opacity: 0; }}
    #title-card {{ position: absolute; top: 110px; left: 0; right: 120px; margin: 0 auto; width: fit-content;
      text-align: center; z-index: 5; }}
    #kicker {{ color: #f0b06a; font-size: 36px; font-weight: 800; letter-spacing: 8px; }}
    #title-chip {{ margin-top: 14px; background: rgba(30, 14, 10, 0.92); border: 2px solid rgba(240, 176, 106, 0.6);
      border-radius: 22px; padding: 18px 42px; color: #fff; font-size: 64px; font-weight: 800; }}
  </style>

  <div id="world" class="clip" data-start="0" data-duration="{fmt(total)}" data-track-index="0">
  <div id="shaker">

    <svg class="abs" style="left:0; top:0;" width="1080" height="1920" viewBox="0 0 1080 1920">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#241031"/><stop offset="0.55" stop-color="#7c3648"/>
          <stop offset="0.85" stop-color="#c96a3e"/><stop offset="1" stop-color="#e8934d"/>
        </linearGradient>
        <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stop-color="#ffdf9e" stop-opacity="0.8"/><stop offset="1" stop-color="#ffdf9e" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="1080" height="1400" fill="url(#sky)"/>
      <g id="sun">
        <circle id="sun-glow" cx="540" cy="1180" r="220" fill="url(#glow)" opacity="0.4"/>
        <circle cx="540" cy="1180" r="105" fill="#ffd98a"/>
      </g>
      <path d="M0 1180 Q200 1050 430 1140 Q700 1010 830 1120 Q960 1060 1080 1130 L1080 1400 L0 1400 Z" fill="#472536"/>
      <path d="M0 1260 Q260 1150 520 1240 Q800 1140 1080 1250 L1080 1400 L0 1400 Z" fill="#331a28"/>
      <rect x="0" y="1380" width="1080" height="540" fill="#241318"/>
      <ellipse cx="540" cy="1390" rx="720" ry="52" fill="#2c1a20"/>
      <path id="bird-0" d="M180 420 q14 -14 26 0 q14 -14 26 0" stroke="#2a1420" stroke-width="6" fill="none" stroke-linecap="round"/>
      <path id="bird-1" d="M760 320 q12 -12 22 0 q12 -12 22 0" stroke="#2a1420" stroke-width="5" fill="none" stroke-linecap="round"/>
      <g id="rays" opacity="0">
        <g stroke="#ffde9a" stroke-width="14" stroke-linecap="round">
          <line x1="660" y1="1140" x2="660" y2="1030"/><line x1="800" y1="1190" x2="880" y2="1110"/>
          <line x1="520" y1="1190" x2="440" y2="1110"/><line x1="850" y1="1330" x2="950" y2="1310"/>
          <line x1="470" y1="1330" x2="370" y2="1310"/>
        </g>
      </g>
      <g id="rock">
        <path id="rock-l" d="M560 1450 L548 1330 Q570 1240 660 1230 L660 1246 L640 1300 L662 1360 L648 1450 Z" fill="#6b6f7a"/>
        <path id="rock-r" d="M648 1450 L662 1360 L640 1300 L660 1246 L660 1230 Q762 1236 776 1330 L764 1450 Z" fill="#7b8090"/>
        <path d="M582 1300 Q600 1284 622 1296" stroke="#585c66" stroke-width="6" fill="none"/>
        <path d="M690 1280 Q712 1268 730 1284" stroke="#6a6f7e" stroke-width="6" fill="none"/>
        <path id="crack" d="M660 1246 L648 1290 L666 1330 L652 1382 L662 1430" stroke="#241318" stroke-width="7" fill="none" opacity="0"/>
      </g>
      <g fill="#c9b8a4">
        <circle id="dust-0" cx="620" cy="1330" r="10" opacity="0"/>
        <circle id="dust-1" cx="700" cy="1340" r="8" opacity="0"/>
        <circle id="burst-0" cx="640" cy="1300" r="12" opacity="0"/>
        <circle id="burst-1" cx="680" cy="1290" r="10" opacity="0"/>
        <circle id="burst-2" cx="660" cy="1320" r="14" opacity="0"/>
        <circle id="burst-3" cx="660" cy="1270" r="9" opacity="0"/>
      </g>
    </svg>

    <div id="kabir" class="abs clip" style="left:200px; top:1052px; width:260px; height:420px;"
         data-start="0" data-duration="{fmt(total)}" data-track-index="2">
      <svg width="260" height="420" viewBox="0 0 260 420">
        <circle cx="130" cy="86" r="58" fill="#e0a276"/>
        <path d="M76 74 Q80 32 130 30 Q180 32 184 74 Q150 52 112 58 Q90 62 76 74 Z" fill="#241408"/>
        <rect x="76" y="52" width="108" height="16" rx="8" fill="#c9462e"/>
        <g id="eyes-kab">
          <circle cx="110" cy="88" r="11" fill="#fff"/><circle cx="152" cy="88" r="11" fill="#fff"/>
          <circle cx="112" cy="90" r="5.5" fill="#241408"/><circle cx="154" cy="90" r="5.5" fill="#241408"/>
        </g>
        <path d="M98 70 Q110 64 122 70" stroke="#241408" stroke-width="5" fill="none" stroke-linecap="round"/>
        <path d="M140 70 Q152 64 164 70" stroke="#241408" stroke-width="5" fill="none" stroke-linecap="round"/>
        <ellipse id="mouth-kab" cx="130" cy="120" rx="12" ry="3" fill="#7a2c30"/>
        <path id="sweat" d="M176 76 q8 10 0 16 q-8 -6 0 -16" fill="#9ed2f0" opacity="0"/>
        <rect x="118" y="142" width="24" height="16" fill="#e0a276"/>
        <path d="M74 300 Q76 162 130 158 Q184 162 186 300 Z" fill="#b3552e"/>
        <rect x="96" y="176" width="68" height="90" rx="10" fill="#8a3f22"/>
        <path d="M74 232 Q58 262 66 302 L88 296 Q82 264 90 238 Z" fill="#e0a276"/>
        <g id="arm-kab">
          <path d="M150 200 Q192 216 206 262 L186 274 Q172 234 142 224 Z" fill="#e0a276"/>
          <rect x="196" y="150" width="14" height="130" rx="7" fill="#8a5a2e" transform="rotate(24 203 215)"/>
          <rect x="176" y="128" width="66" height="34" rx="8" fill="#5a6070" transform="rotate(24 209 145)"/>
        </g>
        <rect x="100" y="300" width="24" height="90" fill="#5a4632"/>
        <rect x="136" y="300" width="24" height="90" fill="#5a4632"/>
        <rect x="92" y="386" width="42" height="18" rx="8" fill="#33261a"/>
        <rect x="128" y="386" width="42" height="18" rx="8" fill="#33261a"/>
      </svg>
    </div>

    <div id="passerby" class="abs clip" style="left:-30px; top:1120px; width:220px; height:360px;"
         data-start="{fmt(pas_start)}" data-duration="{fmt(total - pas_start)}" data-track-index="2">
      <svg width="220" height="360" viewBox="0 0 220 360">
        <circle cx="110" cy="80" r="50" fill="#e9ae83"/>
        <path d="M62 70 Q66 32 110 30 Q154 32 158 70 L158 120 Q134 96 86 100 Q68 104 62 120 Z" fill="#8a6a52"/>
        <g id="eyes-pas">
          <circle cx="94" cy="82" r="9" fill="#fff"/><circle cx="128" cy="82" r="9" fill="#fff"/>
          <circle cx="96" cy="84" r="4.5" fill="#241408"/><circle cx="130" cy="84" r="4.5" fill="#241408"/>
        </g>
        <path d="M84 66 Q94 61 104 66" stroke="#5a4632" stroke-width="4" fill="none" stroke-linecap="round"/>
        <path d="M118 66 Q128 61 138 66" stroke="#5a4632" stroke-width="4" fill="none" stroke-linecap="round"/>
        <ellipse id="mouth-pas" cx="110" cy="108" rx="10" ry="3" fill="#7a2c38"/>
        <rect x="100" y="126" width="20" height="14" fill="#e9ae83"/>
        <path d="M60 280 Q62 142 110 138 Q158 142 160 280 L160 344 Q110 356 60 344 Z" fill="#7a5a8a"/>
        <path d="M60 200 Q42 230 50 280 L70 274 Q64 236 74 208 Z" fill="#e9ae83"/>
        <path d="M160 200 Q178 230 170 280 L150 274 Q156 236 146 208 Z" fill="#e9ae83"/>
      </svg>
    </div>

    <div id="flash" class="abs" style="left:0; top:0; width:1080px; height:1920px; background:#fff7e0; opacity:0;"></div>
    <div id="dawnlight" class="abs clip" style="left:0; top:0; width:1080px; height:1920px;
         background: linear-gradient(180deg, rgba(255,214,140,0) 0%, rgba(255,196,110,0.9) 100%); opacity:0;"
         data-start="{fmt(t14a)}" data-duration="{fmt(total - t14a)}" data-track-index="1"></div>

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
