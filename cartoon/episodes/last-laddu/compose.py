#!/usr/bin/env python3
"""Compose "The Last Laddu" — the reference multi-character cartoon episode.

Usage: cartoon/episodes/last-laddu/compose.py --project <dir>

Prerequisites in the project: lines.txt (this episode's 14 lines, any language),
cast.json (speakers + tints), and the pipeline outputs audio_meta.json /
captions.json / timeline.json. Writes the project's index.html: drawn kitchen
set, four characters + a cat, a hard camera cut per line with push-in drift,
per-speaker mouth flaps, and the scripted gags.

Staging is authored FOR this script's 14 beats (camera plan + gags reference
line numbers). For a new episode: copy this file, redraw the set/characters,
re-map CAM and the gag section to your own script. Timing always comes from
the audio, so any language / any pacing of these 14 beats re-choreographs
itself. Title and kicker come from project.json (title/topic); Devanagari
@font-face is emitted when assets/fonts/NotoSansDevanagari-Regular.ttf exists.

Hard-won rules baked in: SVG sub-part motion uses GSAP svgOrigin (CSS
transform-box displaces mid-animation in the renderer); mouths are attr(ry)
tweens; fade boundaries get a hard tl.set.
"""
import argparse
import html
import json
import pathlib

ap = argparse.ArgumentParser(description="Compose the Last Laddu episode into index.html.")
ap.add_argument("--project", required=True)
project = pathlib.Path(ap.parse_args().project).expanduser().resolve()

meta = json.load(open(project / "audio_meta.json"))
captions = json.load(open(project / "captions.json"))
timeline = json.load(open(project / "timeline.json"))
pj = json.load(open(project / "project.json"))
cast = json.load(open(project / "cast.json"))

total = timeline["total"]
lines = meta["lines"]
fmt = lambda v: f"{v:.3f}"

SPEAKERS = cast["speakers"]
TINT = cast.get("tints", {})
if len(lines) != 14 or len(SPEAKERS) != 14:
    raise SystemExit(
        f"this episode's staging is written for its 14 lines (got {len(lines)} lines, "
        f"{len(SPEAKERS)} speakers) — copy this script and re-choreograph CAM + gags for a new script"
    )
TITLE = pj.get("title", "The Last Laddu")
KICKER = pj.get("topic", "a tiny cartoon").upper()
deva = project / "assets" / "fonts" / "NotoSansDevanagari-Regular.ttf"
FONT_FACE = """
    @font-face {{ font-family: 'Noto Sans Devanagari'; font-weight: 400;
      src: url('assets/fonts/NotoSansDevanagari-Regular.ttf'); }}
    @font-face {{ font-family: 'Noto Sans Devanagari'; font-weight: 700;
      src: url('assets/fonts/NotoSansDevanagari-Bold.ttf'); }}
""" if deva.exists() else """
    @font-face {{ font-family: 'Noto Sans Devanagari'; src: local('Noto Sans Devanagari'); }}
"""
MOUTH = {"kid": "#mouth-kid", "gma": "#mouth-gma", "gpa": "#mouth-gpa"}

def line_of(t):
    best = 1
    for ln in lines:
        if t >= ln["start"] - 0.01:
            best = ln["index"]
    return best

def win(i):  # (start, end) of line i (1-based)
    ln = lines[i - 1]
    return ln["start"], ln["start"] + ln["duration"]

# --- camera plan: (scale, focus_x, focus_y) per line --------------------------
CAM = {
    1: (1.00, 540, 960), 2: (1.70, 280, 1180), 3: (1.60, 850, 1100), 4: (2.30, 560, 1180),
    5: (1.35, 420, 1250), 6: (1.50, 880, 1420), 7: (2.20, 880, 1380), 8: (1.70, 280, 1180),
    9: (1.05, 540, 1100), 10: (1.90, 850, 1080), 11: (1.30, 760, 1150), 12: (1.80, 950, 1080),
    13: (1.40, 450, 1300), 14: (1.50, 800, 1150),
}

def cam_xy(s, px, py):
    x = 540 - s * px
    y = 960 - s * py
    x = max(1080 - 1080 * s, min(0, x))
    y = max(1920 - 1920 * s, min(0, y))
    return x, y

tw = []
# camera: hard cut at each line start, slow push-in during the line
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

# idle bobs (divs are safe for transforms)
for sel, period, amp in [("#arjun", 1.3, 5), ("#grandma", 1.7, 4), ("#cat", 0.9, 3), ("#grandpa", 1.5, 4)]:
    reps = max(1, int(total / period) + 1)
    tw.append(f'tl.to("{sel}", {{y: {amp}, duration: {period}, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, 0);')

# blinks per character while on screen (svgOrigin = eye-line center, per-char svg coords)
BLINK = [("#eyes-kid", '"130 92"', 0.9, total), ("#eyes-gma", '"150 100"', 1.9, total), ("#eyes-gpa", '"140 96"', win(11)[0] + 1.2, total)]
for sel, org, t, end in BLINK:
    while t < end - 0.6:
        tw.append(f'tl.to("{sel}", {{scaleY: 0.1, svgOrigin: {org}, duration: 0.07, repeat: 1, yoyo: true, ease: "none"}}, {fmt(t)});')
        t += 2.7

# mouths: closed base, flap on the speaking character's caption windows
for sel in MOUTH.values():
    tw.append(f'tl.set("{sel}", {{attr: {{ry: 3}}}}, 0);')
for c in captions:
    idx = line_of(c["start"])
    spk = SPEAKERS[idx - 1]
    if spk not in MOUTH:
        continue
    sel = MOUTH[spk]
    span = c["end"] - c["start"]
    if span < 0.14:
        continue
    reps = max(1, int(span / 0.09) - 1)
    tw.append(f'tl.to("{sel}", {{attr: {{ry: 12}}, duration: 0.09, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, {fmt(c["start"])});')
    tw.append(f'tl.set("{sel}", {{attr: {{ry: 3}}}}, {fmt(c["end"])});')

# --- gags, line by line -------------------------------------------------------
t2a, t2b = win(2)   # kid begging: bounce
for k in range(3):
    tw.append(f'tl.to("#arjun", {{y: -26, duration: 0.18, repeat: 1, yoyo: true, ease: "power1.out"}}, {fmt(t2a + 0.25 + k * 0.5)});')
t3a, t3b = win(3)   # grandma finger wag (rotate arm at shoulder)
for k in range(4):
    tw.append(f'tl.to("#arm-gma", {{rotation: -28, svgOrigin: "205 210", duration: 0.16, repeat: 1, yoyo: true, ease: "sine.inOut"}}, {fmt(t3a + 0.3 + k * 0.4)});')
t4a, t4b = win(4)   # laddu sparkle
for k in range(3):
    tw.append(f'tl.fromTo("#sparkle-{k}", {{opacity: 0, scale: 0.4, svgOrigin: "560 1168"}}, {{opacity: 1, scale: 1.15, duration: 0.3, repeat: 1, yoyo: true}}, {fmt(t4a + 0.3 + k * 0.7)});')
t5a, t5b = win(5)   # kid tiptoes toward the table (6 mini-hops)
hop = (t5b - t5a - 0.2) / 6
for k in range(6):
    tw.append(f'tl.to("#arjun", {{x: {35 * (k + 1)}, duration: {fmt(hop)}, ease: "power1.inOut"}}, {fmt(t5a + 0.1 + k * hop)});')
    tw.append(f'tl.to("#arjun", {{y: -10, duration: {fmt(hop / 2)}, repeat: 1, yoyo: true, ease: "sine.out"}}, {fmt(t5a + 0.1 + k * hop)});')
t6a, t6b = win(6)   # cat slides in from the right, tail flicking
tw.append(f'tl.fromTo("#cat", {{x: 360}}, {{x: 0, duration: {fmt(min(1.6, t6b - t6a))}, ease: "power2.out"}}, {fmt(t6a)});')
reps = max(1, int((total - t6a) / 0.5))
tw.append(f'tl.to("#tail", {{rotation: 24, svgOrigin: "24 74", duration: 0.5, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, {fmt(t6a)});')
t7a, t7b = win(7)   # cat narrows its eyes
tw.append(f'tl.to("#eyes-cat", {{scaleY: 0.45, svgOrigin: "104 52", duration: 0.3, ease: "power1.in"}}, {fmt(t7a + 0.1)});')
tw.append(f'tl.to("#eyes-cat", {{scaleY: 1.0, svgOrigin: "104 52", duration: 0.3}}, {fmt(win(9)[0])});')
t8a, t8b = win(8)   # kid crouches one-two-three
for k in range(3):
    tw.append(f'tl.to("#arjun", {{scaleY: 0.92, transformOrigin: "50% 100%", duration: 0.16, repeat: 1, yoyo: true}}, {fmt(t8a + 0.2 + k * 0.55)});')
t9a, t9b = win(9)   # THE CHAOS: jumps, shake, plate hops, laddu launches
tw.append(f'tl.to("#arjun", {{y: -90, duration: 0.28, repeat: 1, yoyo: true, ease: "power2.out"}}, {fmt(t9a + 0.1)});')
tw.append(f'tl.to("#cat", {{y: -120, x: -60, duration: 0.3, repeat: 1, yoyo: true, ease: "power2.out"}}, {fmt(t9a + 0.2)});')
for k in range(6):
    tw.append(f'tl.to("#shaker", {{x: {8 if k % 2 == 0 else -8}, duration: 0.05}}, {fmt(t9a + 0.35 + k * 0.05)});')
tw.append(f'tl.set("#shaker", {{x: 0}}, {fmt(t9a + 0.7)});')
tw.append(f'tl.to("#plate", {{y: -60, rotation: 14, svgOrigin: "560 1198", duration: 0.3, ease: "power2.out"}}, {fmt(t9a + 0.35)});')
tw.append(f'tl.to("#plate", {{y: 0, rotation: 0, svgOrigin: "560 1198", duration: 0.4, ease: "bounce.out"}}, {fmt(t9a + 0.65)});')
tw.append(f'tl.set("#laddu-table", {{opacity: 0}}, {fmt(t9a + 0.35)});')   # the real one takes flight
tw.append(f'tl.fromTo("#laddu-fly", {{x: 0, y: 0, rotation: 0}}, {{x: 120, y: -420, rotation: 380, duration: {fmt(t9b - t9a - 0.35)}, ease: "power2.out"}}, {fmt(t9a + 0.35)});')
t10a, t10b = win(10)  # grandma erupts; laddu hangs in the air (cartoon time)
tw.append(f'tl.to("#grandma", {{scale: 1.06, transformOrigin: "50% 100%", duration: 0.2, repeat: 1, yoyo: true}}, {fmt(t10a)});')
tw.append(f'tl.to("#brows-gma", {{y: 6, rotation: -8, svgOrigin: "150 82", duration: 0.2}}, {fmt(t10a)});')
tw.append(f'tl.to("#laddu-fly", {{y: -440, rotation: 420, duration: {fmt(t10b - t10a)}, ease: "sine.inOut"}}, {fmt(t10a)});')
t11a, t11b = win(11)  # grandpa slides in through the door; laddu falls into his hand
tw.append(f'tl.fromTo("#grandpa", {{x: 260}}, {{x: 0, duration: 1.0, ease: "power2.out"}}, {fmt(t11a)});')
tw.append(f'tl.to("#grandma", {{x: -120, duration: 0.8, ease: "power1.inOut"}}, {fmt(t11a)});')
tw.append(f'tl.to("#arm-gpa", {{rotation: -46, svgOrigin: "70 260", duration: 0.5, ease: "power1.out"}}, {fmt(t11a + 0.4)});')
tw.append(f'tl.to("#laddu-fly", {{x: 385, y: 55, rotation: 720, duration: {fmt(t11b - t11a - 0.15)}, ease: "power1.in"}}, {fmt(t11a)});')
t12a, t12b = win(12)  # grandpa bites: laddu to mouth, shrink, happy squint
tw.append(f'tl.to("#laddu-fly", {{x: 400, y: -8, scale: 0.55, duration: 0.5, ease: "power1.inOut"}}, {fmt(t12a + 0.2)});')
tw.append(f'tl.to("#laddu-fly", {{scale: 0.12, opacity: 0, duration: 0.35}}, {fmt(t12a + 0.9)});')
tw.append(f'tl.set("#laddu-fly", {{opacity: 0}}, {fmt(t12a + 1.25)});')
tw.append(f'tl.to("#eyes-gpa", {{scaleY: 0.35, svgOrigin: "140 96", duration: 0.3}}, {fmt(t12a + 1.0)});')
t13a, t13b = win(13)  # cat licks crumbs under the table; kid sweeps
tw.append(f'tl.to("#cat", {{x: -180, y: 8, duration: 0.8, ease: "power1.inOut"}}, {fmt(t13a)});')
for k in range(3):
    tw.append(f'tl.to("#head-cat", {{y: 6, svgOrigin: "104 52", duration: 0.18, repeat: 1, yoyo: true}}, {fmt(t13a + 0.9 + k * 0.4)});')
tw.append(f'tl.fromTo("#broom", {{opacity: 0}}, {{opacity: 1, duration: 0.25}}, {fmt(t13a)});')
tw.append(f'tl.set("#arjun", {{x: 0, y: 0}}, {fmt(t13a)});')
for k in range(3):
    tw.append(f'tl.to("#broom", {{rotation: 10, transformOrigin: "20% 10%", duration: 0.35, repeat: 1, yoyo: true, ease: "sine.inOut"}}, {fmt(t13a + 0.3 + k * 0.75)});')
t14a = win(14)[0]     # grandma's secret box pops up; wink
tw.append(f'tl.fromTo("#laddu-box", {{scale: 0.3, opacity: 0}}, {{scale: 1, opacity: 1, duration: 0.45, ease: "back.out(2)"}}, {fmt(t14a + 0.3)});')
tw.append(f'tl.to("#wink-gma", {{scaleY: 0.12, svgOrigin: "175 100", duration: 0.12, repeat: 1, yoyo: true}}, {fmt(t14a + 1.2)});')
tw.append(f'tl.to("#wink-gma", {{scaleY: 0.12, svgOrigin: "175 100", duration: 0.12, repeat: 1, yoyo: true}}, {fmt(t14a + 1.5)});')

# title card out after line 1 (hard zero at the boundary)
te = win(1)[1] + 0.3
tw.append(f'tl.to("#title-card", {{opacity: 0, duration: 0.35}}, {fmt(te - 0.35)});')
tw.append(f'tl.set("#title-card", {{opacity: 0}}, {fmt(te)});')

# --- caption chips (outside #world, speaker-tinted) --------------------------
caps = []
for c in captions:
    idx = line_of(c["start"])
    tint = TINT.get(SPEAKERS[idx - 1], "#ffffff")
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

cat_start = win(6)[0]
gpa_start = win(11)[0]
broom_start = win(13)[0]
box_start = win(14)[0]

page = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{html.escape(TITLE)}</title></head>
<body>
<div id="stage" data-composition-id="reel" data-start="0" data-duration="{fmt(total)}"
     data-width="1080" data-height="1920" data-fps="30">
  <style>{FONT_FACE}
    #stage {{ background: #1a130a; font-family: -apple-system, "Segoe UI", Roboto, "Noto Sans Devanagari", Helvetica, Arial, sans-serif; overflow: hidden; }}
    #world, #shaker {{ position: absolute; inset: 0; }}
    #world {{ transform-origin: 0px 0px; }}
    .abs {{ position: absolute; }}
    .caption {{ position: absolute; top: 1380px; left: 50%; transform: translateX(-50%);
      max-width: 840px; background: rgba(0, 0, 0, 0.85); border-radius: 18px; padding: 18px 34px;
      font-size: 54px; font-weight: 700; text-align: center; }}
    #title-card {{ position: absolute; top: 120px; left: 0; right: 120px; margin: 0 auto; width: fit-content;
      text-align: center; z-index: 5; }}
    #kicker {{ color: #f0b64a; font-size: 38px; font-weight: 800; letter-spacing: 9px; }}
    #title-chip {{ margin-top: 16px; background: rgba(26, 19, 8, 0.92); border: 2px solid rgba(240, 182, 74, 0.6);
      border-radius: 22px; padding: 18px 42px; color: #fff; font-size: 68px; font-weight: 800; }}
  </style>

  <div id="world" class="clip" data-start="0" data-duration="{fmt(total)}" data-track-index="0">
  <div id="shaker">

    <svg class="abs" style="left:0; top:0;" width="1080" height="1920" viewBox="0 0 1080 1920">
      <rect x="0" y="0" width="1080" height="1500" fill="#f6e3bd"/>
      <rect x="0" y="1500" width="1080" height="420" fill="#a9713a"/>
      <g stroke="#8f5c2d" stroke-width="4">
        <line x1="0" y1="1600" x2="1080" y2="1600"/><line x1="0" y1="1720" x2="1080" y2="1720"/>
        <line x1="220" y1="1500" x2="180" y2="1920"/><line x1="560" y1="1500" x2="560" y2="1920"/>
        <line x1="880" y1="1500" x2="940" y2="1920"/>
      </g>
      <rect x="110" y="290" width="320" height="360" rx="14" fill="#fff" stroke="#c9a25e" stroke-width="10"/>
      <rect x="130" y="310" width="280" height="320" fill="#bfe4f2"/>
      <circle cx="360" cy="380" r="34" fill="#ffe9a8"/>
      <path d="M150 520 Q210 470 270 520 Q330 560 400 520 L400 630 L150 630 Z" fill="#dff2f9" opacity="0.7"/>
      <path d="M130 310 Q170 460 130 630 L186 630 Q160 460 186 310 Z" fill="#e2703a"/>
      <path d="M410 310 Q370 460 410 630 L354 630 Q380 460 354 310 Z" fill="#e2703a"/>
      <rect x="660" y="430" width="320" height="18" rx="6" fill="#8f5c2d"/>
      <rect x="690" y="360" width="52" height="70" rx="8" fill="#d96a4b"/>
      <rect x="770" y="345" width="58" height="85" rx="8" fill="#7fa85a"/>
      <rect x="860" y="370" width="46" height="60" rx="8" fill="#e0b13e"/>
      <rect x="915" y="660" width="150" height="840" rx="8" fill="#7a4a22"/>
      <rect x="932" y="680" width="116" height="800" rx="6" fill="#8f5c2d"/>
      <circle cx="955" cy="1090" r="12" fill="#e0b13e"/>
    </svg>

    <svg id="table" class="abs clip" style="left:0; top:0;" width="1080" height="1920" viewBox="0 0 1080 1920"
         data-start="0" data-duration="{fmt(total)}" data-track-index="1">
      <rect x="350" y="1210" width="420" height="26" rx="10" fill="#8a5a2b"/>
      <rect x="380" y="1236" width="26" height="264" fill="#744a22"/>
      <rect x="714" y="1236" width="26" height="264" fill="#744a22"/>
      <g id="plate">
        <ellipse cx="560" cy="1198" rx="88" ry="18" fill="#ffffff"/>
        <ellipse cx="560" cy="1194" rx="64" ry="12" fill="#e8e8e8"/>
      </g>
      <g id="laddu-table">
        <circle cx="560" cy="1168" r="30" fill="#e8a33d"/>
        <circle cx="549" cy="1160" r="4" fill="#c77f24"/><circle cx="568" cy="1156" r="4" fill="#c77f24"/>
        <circle cx="574" cy="1174" r="4" fill="#c77f24"/><circle cx="552" cy="1178" r="4" fill="#c77f24"/>
      </g>
      <g fill="#ffd24a">
        <path id="sparkle-0" d="M505 1120 l6 14 14 6 -14 6 -6 14 -6 -14 -14 -6 14 -6 Z" opacity="0"/>
        <path id="sparkle-1" d="M612 1108 l6 14 14 6 -14 6 -6 14 -6 -14 -14 -6 14 -6 Z" opacity="0"/>
        <path id="sparkle-2" d="M560 1092 l6 14 14 6 -14 6 -6 14 -6 -14 -14 -6 14 -6 Z" opacity="0"/>
      </g>
    </svg>

    <div id="arjun" class="abs clip" style="left:150px; top:1046px; width:260px; height:460px;"
         data-start="0" data-duration="{fmt(total)}" data-track-index="2">
      <svg width="260" height="460" viewBox="0 0 260 460">
        <path d="M70 64 Q66 18 130 16 Q194 18 190 64 L186 96 Q130 76 74 96 Z" fill="#2b1a10"/>
        <circle cx="130" cy="86" r="62" fill="#f2b98b"/>
        <path d="M72 74 Q80 34 130 32 Q180 34 188 74 Q150 52 118 58 Q90 62 72 74 Z" fill="#2b1a10"/>
        <g id="eyes-kid">
          <circle cx="108" cy="88" r="12" fill="#fff"/><circle cx="152" cy="88" r="12" fill="#fff"/>
          <circle cx="110" cy="90" r="6" fill="#241408"/><circle cx="154" cy="90" r="6" fill="#241408"/>
        </g>
        <path d="M96 68 Q108 62 120 68" stroke="#241408" stroke-width="5" fill="none" stroke-linecap="round"/>
        <path d="M140 68 Q152 62 164 68" stroke="#241408" stroke-width="5" fill="none" stroke-linecap="round"/>
        <ellipse id="mouth-kid" cx="130" cy="122" rx="14" ry="3" fill="#8c3040"/>
        <rect x="118" y="146" width="24" height="16" fill="#f2b98b"/>
        <path d="M74 300 Q76 168 130 164 Q184 168 186 300 Z" fill="#ffd24a"/>
        <path d="M74 232 Q60 260 66 300 L92 294 Q84 258 92 232 Z" fill="#f2b98b"/>
        <path d="M186 232 Q200 260 194 300 L168 294 Q176 258 168 232 Z" fill="#f2b98b"/>
        <rect x="86" y="296" width="88" height="52" rx="10" fill="#4a6fa5"/>
        <rect x="92" y="348" width="28" height="86" fill="#f2b98b"/>
        <rect x="140" y="348" width="28" height="86" fill="#f2b98b"/>
        <rect x="84" y="430" width="44" height="20" rx="8" fill="#37424f"/>
        <rect x="132" y="430" width="44" height="20" rx="8" fill="#37424f"/>
      </svg>
    </div>

    <div id="grandma" class="abs clip" style="left:700px; top:928px; width:300px; height:580px;"
         data-start="0" data-duration="{fmt(total)}" data-track-index="2">
      <svg width="300" height="580" viewBox="0 0 300 580">
        <circle cx="150" cy="52" r="30" fill="#c9c9c9"/>
        <circle cx="150" cy="102" r="64" fill="#e9ae83"/>
        <path d="M90 88 Q94 44 150 42 Q206 44 210 88 Q170 66 130 70 Q104 74 90 88 Z" fill="#c9c9c9"/>
        <g id="eyes-gma">
          <g id="wink-gma"><circle cx="175" cy="100" r="11" fill="#fff"/><circle cx="177" cy="102" r="5.5" fill="#241408"/></g>
          <circle cx="126" cy="100" r="11" fill="#fff"/><circle cx="128" cy="102" r="5.5" fill="#241408"/>
        </g>
        <g id="brows-gma">
          <path d="M114 82 Q126 76 138 82" stroke="#8a8a8a" stroke-width="5" fill="none" stroke-linecap="round"/>
          <path d="M162 82 Q174 76 186 82" stroke="#8a8a8a" stroke-width="5" fill="none" stroke-linecap="round"/>
        </g>
        <circle cx="126" cy="100" r="16" fill="none" stroke="#5a4632" stroke-width="4"/>
        <circle cx="175" cy="100" r="16" fill="none" stroke="#5a4632" stroke-width="4"/>
        <line x1="142" y1="100" x2="159" y2="100" stroke="#5a4632" stroke-width="4"/>
        <ellipse id="mouth-gma" cx="150" cy="138" rx="13" ry="3" fill="#8c3040"/>
        <rect x="136" y="162" width="28" height="18" fill="#e9ae83"/>
        <path d="M84 420 Q86 186 150 182 Q214 186 216 420 L216 560 Q150 580 84 560 Z" fill="#2e8b8b"/>
        <path d="M84 260 Q120 300 84 420 L120 420 Q140 320 120 254 Z" fill="#247070" opacity="0.7"/>
        <g id="arm-gma">
          <path d="M205 210 Q248 250 240 310 L214 316 Q220 262 192 232 Z" fill="#e9ae83"/>
          <rect x="222" y="300" width="26" height="34" rx="10" fill="#e9ae83"/>
        </g>
        <path d="M95 210 Q56 252 66 312 L92 318 Q86 264 108 232 Z" fill="#e9ae83"/>
      </svg>
    </div>

    <div id="grandpa" class="abs clip" style="left:850px; top:952px; width:280px; height:556px;"
         data-start="{fmt(gpa_start)}" data-duration="{fmt(total - gpa_start)}" data-track-index="2">
      <svg width="280" height="556" viewBox="0 0 280 556">
        <circle cx="140" cy="96" r="62" fill="#e5a87e"/>
        <path d="M82 84 Q86 52 116 44 Q100 70 108 84 Z" fill="#cfcfcf"/>
        <path d="M198 84 Q194 52 164 44 Q180 70 172 84 Z" fill="#cfcfcf"/>
        <g id="eyes-gpa">
          <circle cx="118" cy="94" r="11" fill="#fff"/><circle cx="162" cy="94" r="11" fill="#fff"/>
          <circle cx="120" cy="96" r="5.5" fill="#241408"/><circle cx="164" cy="96" r="5.5" fill="#241408"/>
        </g>
        <path d="M104 78 Q116 72 128 78" stroke="#bdbdbd" stroke-width="6" fill="none" stroke-linecap="round"/>
        <path d="M152 78 Q164 72 176 78" stroke="#bdbdbd" stroke-width="6" fill="none" stroke-linecap="round"/>
        <path d="M116 128 Q140 142 164 128 Q140 152 116 128 Z" fill="#d8d8d8"/>
        <ellipse id="mouth-gpa" cx="140" cy="128" rx="13" ry="3" fill="#7a2c38"/>
        <rect x="126" y="158" width="28" height="18" fill="#e5a87e"/>
        <path d="M76 400 Q78 180 140 176 Q202 180 204 400 L204 540 Q140 556 76 540 Z" fill="#efe6d2"/>
        <path d="M96 190 L184 190 L176 330 L104 330 Z" fill="#b98a4a"/>
        <g id="arm-gpa">
          <path d="M70 260 Q30 300 40 360 L66 368 Q60 312 84 282 Z" fill="#e5a87e"/>
          <circle cx="52" cy="372" r="18" fill="#e5a87e"/>
        </g>
        <path d="M210 260 Q244 300 236 360 L210 366 Q216 312 196 282 Z" fill="#e5a87e"/>
      </svg>
    </div>

    <div id="cat" class="abs clip" style="left:770px; top:1382px; width:200px; height:130px;"
         data-start="{fmt(cat_start)}" data-duration="{fmt(total - cat_start)}" data-track-index="2">
      <svg width="200" height="130" viewBox="0 0 200 130">
        <path id="tail" d="M24 74 Q-8 60 6 30 L18 36 Q10 56 32 64 Z" fill="#d97e3a"/>
        <ellipse cx="70" cy="88" rx="52" ry="34" fill="#e8933f"/>
        <g id="head-cat">
          <circle cx="124" cy="62" r="34" fill="#e8933f"/>
          <path d="M100 38 L94 10 L116 26 Z" fill="#e8933f"/>
          <path d="M148 38 L154 10 L132 26 Z" fill="#e8933f"/>
          <g id="eyes-cat">
            <ellipse cx="114" cy="58" rx="7" ry="9" fill="#2f4f2f"/>
            <ellipse cx="138" cy="58" rx="7" ry="9" fill="#2f4f2f"/>
          </g>
          <path d="M120 74 L128 74 L124 80 Z" fill="#b25b28"/>
          <line x1="98" y1="72" x2="76" y2="68" stroke="#b25b28" stroke-width="3"/>
          <line x1="150" y1="72" x2="172" y2="68" stroke="#b25b28" stroke-width="3"/>
        </g>
        <rect x="36" y="112" width="14" height="16" rx="6" fill="#d97e3a"/>
        <rect x="86" y="112" width="14" height="16" rx="6" fill="#d97e3a"/>
      </svg>
    </div>

    <div id="broom" class="abs clip" style="left:96px; top:1120px; width:60px; height:400px; opacity:0;"
         data-start="{fmt(broom_start)}" data-duration="{fmt(total - broom_start)}" data-track-index="3">
      <svg width="60" height="400" viewBox="0 0 60 400">
        <rect x="24" y="0" width="12" height="300" rx="6" fill="#9a6a34"/>
        <path d="M10 300 L50 300 L58 392 L2 392 Z" fill="#d9b24a"/>
        <g stroke="#b8933a" stroke-width="3"><line x1="14" y1="310" x2="8" y2="388"/><line x1="30" y1="310" x2="30" y2="388"/><line x1="46" y1="310" x2="52" y2="388"/></g>
      </svg>
    </div>

    <div id="laddu-box" class="abs clip" style="left:600px; top:1150px; width:230px; height:170px; opacity:0;"
         data-start="{fmt(box_start)}" data-duration="{fmt(total - box_start)}" data-track-index="3">
      <svg width="230" height="170" viewBox="0 0 230 170">
        <rect x="6" y="60" width="218" height="104" rx="12" fill="#a5453b"/>
        <rect x="0" y="44" width="230" height="26" rx="10" fill="#c25a4e"/>
        <g fill="#e8a33d" stroke="#c77f24" stroke-width="3">
          <circle cx="46" cy="104" r="24"/><circle cx="114" cy="104" r="24"/><circle cx="182" cy="104" r="24"/>
          <circle cx="80" cy="140" r="22"/><circle cx="148" cy="140" r="22"/>
        </g>
      </svg>
    </div>

    <div id="laddu-fly" class="abs clip" style="left:528px; top:1136px; width:64px; height:64px;"
         data-start="{fmt(win(9)[0])}" data-duration="{fmt(win(12)[1] + 0.4 - win(9)[0])}" data-track-index="3">
      <svg width="64" height="64" viewBox="0 0 64 64">
        <circle cx="32" cy="32" r="30" fill="#e8a33d"/>
        <circle cx="21" cy="24" r="4" fill="#c77f24"/><circle cx="40" cy="20" r="4" fill="#c77f24"/>
        <circle cx="46" cy="38" r="4" fill="#c77f24"/><circle cx="24" cy="42" r="4" fill="#c77f24"/>
      </svg>
    </div>

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
