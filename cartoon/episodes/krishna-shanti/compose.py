#!/usr/bin/env python3
"""Compose "शांतिदूत कृष्ण" — the Krishna–Duryodhan peace-envoy episode (Udyoga Parva).

28 beats, four sets (war road → Vidura's hut → the Kaurava sabha → dusk road),
four voiced characters (narrator, Krishna, Duryodhan, Dhritarashtra) plus
Vidura, Dushasana, guards and a silhouette court. One SVG rig per character,
defined once and teleported between sets, so the character never changes.
The विश्वरूप sequence (beats 21–25) is the centerpiece: flash, aura, ray
burst, a fan of divine arms, snapping chains, and Dhritarashtra's divine sight.

Proven mechanics (see cartoon/README.md): camera hard-cuts per line with
push-in drift, attr(ry) mouths, svgOrigin for SVG parts, hard sets at fade
boundaries, immediateRender: false on cued fromTo effects.
Usage: cartoon/episodes/krishna-shanti/compose.py --project <dir>
"""
import argparse
import html
import json
import math
import pathlib

ap = argparse.ArgumentParser(description="Compose the Krishna peace-envoy episode into index.html.")
ap.add_argument("--project", required=True)
project = pathlib.Path(ap.parse_args().project).expanduser().resolve()
meta = json.load(open(project / "audio_meta.json"))
captions = json.load(open(project / "captions.json"))
timeline = json.load(open(project / "timeline.json"))
pj = json.load(open(project / "project.json"))
cast = json.load(open(project / "cast.json"))

total = timeline["total"]
lines = meta["lines"]
if len(lines) != 28:
    raise SystemExit(
        f"this episode's staging is written for its 28 lines (got {len(lines)}) — "
        "copy this script and re-choreograph CAM + staging for a new script"
    )
fmt = lambda v: f"{v:.3f}"
SPEAKERS = cast["speakers"]
TINT = cast.get("tints", {})
MOUTH = {"kri": "#mouth-kri", "dur": "#mouth-dur", "dhr": "#mouth-dhr"}
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

# set boundaries follow the narration, so a re-voice re-cuts the film
S_HUT = win(5)[0]
S_SABHA = win(8)[0]
S_DUSK = win(27)[0]

# ---------------------------------------------------------------- camera plan
CAM = {
    1: (1.05, 540, 1010), 2: (1.30, 540, 1160), 3: (1.90, 540, 1085), 4: (1.35, 830, 1020),
    5: (1.35, 540, 1150), 6: (1.60, 610, 1200), 7: (1.85, 470, 1035),
    8: (1.08, 560, 1060), 9: (1.50, 480, 1080), 10: (1.80, 460, 1000), 11: (1.18, 580, 1080),
    12: (1.70, 780, 990), 13: (1.88, 785, 985), 14: (1.65, 935, 1010), 15: (1.60, 790, 990),
    16: (1.92, 785, 985), 17: (1.32, 480, 1120), 18: (1.35, 620, 1000), 19: (1.95, 460, 990),
    20: (1.80, 462, 995), 21: (1.15, 520, 1050), 22: (1.00, 540, 950), 23: (1.25, 480, 1130),
    24: (1.60, 935, 1005), 25: (1.50, 920, 1030), 26: (1.15, 520, 1080),
    27: (1.10, 540, 1120), 28: (1.00, 540, 960),
}

def cam_xy(s, px, py):
    x = 540 - s * px
    y = 960 - s * py
    x = max(1080 - 1080 * s, min(0, x))
    y = max(1920 - 1920 * s, min(0, y))
    return x, y

tw = []
for i in range(1, 29):
    s, px, py = CAM[i]
    t0, t1 = win(i)
    if i == 28:
        t1 = total
    x0, y0 = cam_xy(s, px, py)
    s2 = s * 1.04
    x1, y1 = cam_xy(s2, px, py)
    tw.append(f'tl.set("#world", {{scale: {s:.3f}, x: {x0:.1f}, y: {y0:.1f}}}, {fmt(t0)});')
    tw.append(f'tl.to("#world", {{scale: {s2:.3f}, x: {x1:.1f}, y: {y1:.1f}, duration: {fmt(max(0.3, t1 - t0))}, ease: "none"}}, {fmt(t0)});')

# ------------------------------------------------- krishna teleports (one rig)
# seated at Vidura's: the chauki hides where the standing legs would be
tw.append(f'tl.set("#legs-kri", {{opacity: 0}}, {fmt(S_HUT)});')
tw.append(f'tl.set("#legs-kri", {{opacity: 1}}, {fmt(S_SABHA)});')

# base CSS position is the road close-up; every set change re-seats the SAME rig
KRI = [
    (0.0, -2400, 0),          # hidden until his close-up
    (win(3)[0], 0, 0),        # road, camera tight on his face
    (win(4)[0], -2400, 0),    # gates are a wide shot; he is "in the chariot"
    (S_HUT, -70, -50),        # seated at Vidura's (legs behind the chauki)
    (S_SABHA, -80, -90),      # standing centre court
    (S_DUSK, -2400, 0),       # the dusk reprise is silhouette-only
]
for t, dx, dy in KRI:
    tw.append(f'tl.set("#krishna", {{x: {dx}, y: {dy}}}, {fmt(t)});')

# ----------------------------------------------------------------- idle life
def bob(sel, amp, period, t0, t1):
    reps = max(1, int((t1 - t0) / period) - 1)
    tw.append(f'tl.to("{sel}", {{y: {amp}, duration: {period}, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, {fmt(t0)});')
    tw.append(f'tl.set("{sel}", {{y: 0}}, {fmt(t1)});')

bob("#kri-body", 3, 1.7, S_HUT, win(21)[0])
bob("#dur-body", 3, 1.5, S_SABHA, win(23)[0])
bob("#vid-body", 3, 1.8, S_HUT + 0.3, S_SABHA)
bob("#dhr-body", 2, 2.2, S_SABHA, win(24)[0])

def blink(sel, org, t0, t1):
    t = t0 + 0.9
    while t < t1 - 0.6:
        tw.append(f'tl.to("{sel}", {{scaleY: 0.1, svgOrigin: {org}, duration: 0.07, repeat: 1, yoyo: true, ease: "none"}}, {fmt(t)});')
        t += 3.2

blink("#eyes-kri", '"131 90"', win(3)[0], win(3)[1])
blink("#eyes-kri", '"131 90"', S_HUT, win(21)[0])
blink("#eyes-dur", '"142 92"', S_SABHA, win(23)[0])
blink("#eyes-vid", '"120 86"', S_HUT + 0.4, S_SABHA)

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
for s in range(1, 29):
    t0 = win(s)[0]
    tw.append(f'tl.fromTo("#stamp-{s}", {{scale: 0.6, opacity: 0, rotation: -4}}, '
              f'{{scale: 1, opacity: 1, rotation: -2, duration: 0.35, ease: "back.out(2)"}}, {fmt(t0)});')

# scene dips: a fast black blink sells each set change as a cut, not a glitch
for t in (S_HUT, S_SABHA, S_DUSK):
    tw.append(f'tl.fromTo("#scene-dip", {{opacity: 0}}, {{opacity: 0.65, duration: 0.14, repeat: 1, yoyo: true, ease: "none", immediateRender: false}}, {fmt(t - 0.14)});')
    tw.append(f'tl.set("#scene-dip", {{opacity: 0}}, {fmt(t + 0.20)});')

# ============================================================ per-beat staging
# -- scene 1: the war road ---------------------------------------------------
t1a, t1b = win(1)
tw.append(f'tl.to("#cloud-0", {{x: 60, duration: {fmt(S_HUT)}, ease: "none"}}, 0);')
tw.append(f'tl.to("#cloud-1", {{x: -70, duration: {fmt(S_HUT)}, ease: "none"}}, 0);')
reps = max(1, int(S_HUT / 2.6) + 1)
tw.append(f'tl.to("#road-sun-glow", {{opacity: 0.55, duration: 2.6, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, 0);')

t2a, t2b = win(2)                       # the chariot rides in and halts centre
tw.append(f'tl.to("#chariot", {{x: 860, duration: {fmt(t2b - t2a - 0.2)}, ease: "power2.out"}}, {fmt(t2a)});')
tw.append(f'tl.to("#wheel-a", {{rotation: 640, svgOrigin: "120 300", duration: {fmt(t2b - t2a - 0.2)}, ease: "power2.out"}}, {fmt(t2a)});')
tw.append(f'tl.to("#wheel-b", {{rotation: 640, svgOrigin: "395 300", duration: {fmt(t2b - t2a - 0.2)}, ease: "power2.out"}}, {fmt(t2a)});')
bob("#chariot-body", 4, 0.5, t2a, win(4)[1])
reps = max(1, int((win(4)[1] - t2a) / 0.8) + 1)
tw.append(f'tl.to("#flag-krishna", {{skewX: 8, duration: 0.8, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, {fmt(t2a)});')

t4a, t4b = win(4)                       # ...and rides on toward the gates
tw.append(f'tl.to("#chariot", {{x: 2100, duration: {fmt(t4b - t4a - 0.3)}, ease: "power2.in"}}, {fmt(t4a + 0.3)});')
tw.append(f'tl.to("#wheel-a", {{rotation: 1280, svgOrigin: "120 300", duration: {fmt(t4b - t4a - 0.3)}, ease: "power2.in"}}, {fmt(t4a + 0.3)});')
tw.append(f'tl.to("#wheel-b", {{rotation: 1280, svgOrigin: "395 300", duration: {fmt(t4b - t4a - 0.3)}, ease: "power2.in"}}, {fmt(t4a + 0.3)});')

# -- scene 2: Vidura's hut ---------------------------------------------------
t6a, t6b = win(6)                       # Vidura leans in and serves the saag
tw.append(f'tl.to("#vid-body", {{rotation: 7, svgOrigin: "120 400", duration: 0.8, ease: "sine.inOut"}}, {fmt(t6a + 0.3)});')
tw.append(f'tl.to("#vid-body", {{rotation: 0, svgOrigin: "120 400", duration: 0.8, ease: "sine.inOut"}}, {fmt(t6b - 0.9)});')
steam_end = S_SABHA - 0.1
for k in range(2):
    reps = max(1, int((steam_end - S_HUT) / 2.1) - 1)
    tw.append(f'tl.fromTo("#steam-{k}", {{y: 12, opacity: 0.55}}, {{y: -70, opacity: 0, duration: 2.1, '
              f'repeat: {reps}, ease: "power1.out", immediateRender: false}}, {fmt(S_HUT + 0.4 + 0.9 * k)});')
    tw.append(f'tl.set("#steam-{k}", {{opacity: 0}}, {fmt(steam_end)});')
reps = max(1, int((S_SABHA - S_HUT) / 0.35) - 1)
tw.append(f'tl.to("#flame-hut", {{scaleY: 0.82, svgOrigin: "790 1052", duration: 0.35, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, {fmt(S_HUT)});')

t7a, t7b = win(7)                       # "भोजन भाव से..." — open palm
tw.append(f'tl.to("#arm-kri", {{rotation: -34, svgOrigin: "170 205", duration: 0.6, ease: "sine.out"}}, {fmt(t7a + 0.2)});')
tw.append(f'tl.to("#arm-kri", {{rotation: 0, svgOrigin: "170 205", duration: 0.6, ease: "sine.inOut"}}, {fmt(t7b - 0.7)});')

# -- scene 3: the Kaurava sabha ---------------------------------------------
flick_end = win(26)[1]
for k in range(2):
    reps = max(1, int((flick_end - S_SABHA) / 0.4) - 1)
    tw.append(f'tl.to("#flame-{k}", {{scaleY: 0.85, svgOrigin: "{308 + 392 * k} 866", duration: 0.4, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, {fmt(S_SABHA)});')

t10a, t10b = win(10)                    # "पाँच गाँव" — the extended open hand
tw.append(f'tl.to("#arm-kri", {{rotation: -72, svgOrigin: "170 205", duration: 0.7, ease: "power1.out"}}, {fmt(t10a + 0.2)});')
tw.append(f'tl.to("#arm-kri", {{rotation: 0, svgOrigin: "170 205", duration: 0.8, ease: "sine.inOut"}}, {fmt(win(11)[0] + 0.8)});')

t12a, t12b = win(12)                    # Duryodhan steps forward, sneering
tw.append(f'tl.to("#duryodhan", {{x: -40, duration: 0.8, ease: "power1.inOut"}}, {fmt(t12a)});')
tw.append(f'tl.to("#head-dur", {{rotation: -5, svgOrigin: "142 150", duration: 0.4, ease: "sine.out"}}, {fmt(t12a + 0.4)});')
tw.append(f'tl.to("#head-dur", {{rotation: 0, svgOrigin: "142 150", duration: 0.4, ease: "sine.inOut"}}, {fmt(t12b)});')

t13a, t13b = win(13)                    # the refusal: fist slam + tremor
tw.append(f'tl.to("#arm-dur", {{rotation: 55, svgOrigin: "112 212", duration: 0.35, ease: "power1.out"}}, {fmt(t13b - 1.3)});')
tw.append(f'tl.to("#arm-dur", {{rotation: -12, svgOrigin: "112 212", duration: 0.12, ease: "power3.in"}}, {fmt(t13b - 0.9)});')
tw.append(f'tl.to("#arm-dur", {{rotation: 0, svgOrigin: "112 212", duration: 0.5, ease: "power1.out"}}, {fmt(t13b - 0.6)});')
for k in range(4):
    tw.append(f'tl.to("#shaker", {{x: {6 if k % 2 == 0 else -6}, duration: 0.05}}, {fmt(t13b - 0.78 + k * 0.05)});')
tw.append(f'tl.set("#shaker", {{x: 0}}, {fmt(t13b - 0.55)});')
for k in range(2):
    tw.append(f'tl.to("#flame-{k}", {{scale: 1.35, svgOrigin: "{308 + 392 * k} 866", duration: 0.12, repeat: 1, yoyo: true}}, {fmt(t13b - 0.78)});')

t14a, t14b = win(14)                    # Dhritarashtra's trembling plea
tw.append(f'tl.to("#dhr-body", {{rotation: 1.3, svgOrigin: "130 330", duration: 0.22, repeat: {max(2, int((t14b - t14a - 0.6) / 0.22))}, yoyo: true, ease: "sine.inOut"}}, {fmt(t14a + 0.2)});')
tw.append(f'tl.set("#dhr-body", {{rotation: 0}}, {fmt(t14b)});')

t15a, t15b = win(15)                    # the dark turn: head drops, scheming
tw.append(f'tl.to("#head-dur", {{rotation: 6, svgOrigin: "142 150", duration: 0.9, ease: "sine.inOut"}}, {fmt(t15a + 0.3)});')

t16a, t16b = win(16)                    # "बंदी बना लो!" — pointing at Krishna
tw.append(f'tl.to("#head-dur", {{rotation: 0, svgOrigin: "142 150", duration: 0.3, ease: "power1.out"}}, {fmt(t16a)});')
tw.append(f'tl.to("#arm-dur", {{rotation: 85, svgOrigin: "112 212", duration: 0.4, ease: "power2.out"}}, {fmt(t16a + 0.3)});')
tw.append(f'tl.to("#duryodhan", {{x: -60, duration: 0.4, ease: "power1.out"}}, {fmt(t16a + 0.3)});')

# -- scene 4: the chains -----------------------------------------------------
t17a, t17b = win(17)                    # Dushasana + guards close in
tw.append(f'tl.to("#arm-dur", {{rotation: 0, svgOrigin: "112 212", duration: 0.6, ease: "sine.inOut"}}, {fmt(t17a)});')
tw.append(f'tl.to("#duryodhan", {{x: 90, duration: 1.2, ease: "power1.inOut"}}, {fmt(t17a)});')
tw.append(f'tl.to("#dushasana", {{x: 380, duration: 1.6, ease: "power1.inOut"}}, {fmt(t17a)});')
tw.append(f'tl.to("#guard-1", {{x: -530, duration: 1.5, ease: "power1.inOut"}}, {fmt(t17a + 0.2)});')
tw.append(f'tl.to("#guard-2", {{x: -300, duration: 1.5, ease: "power1.inOut"}}, {fmt(t17a + 0.35)});')
sway_end = win(23)[0]
reps = max(1, int((sway_end - t17a) / 0.7) - 1)
tw.append(f'tl.to("#chain-dus", {{rotation: 7, svgOrigin: "236 288", duration: 0.7, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, {fmt(t17a)});')
tw.append(f'tl.set("#chain-dus", {{rotation: 0}}, {fmt(sway_end)});')

t18a, t18b = win(18)                    # Bhishma rises: "दूत पर हाथ? अधर्म!"
tw.append(f'tl.to("#bhishma", {{y: -44, duration: 0.7, ease: "power1.out"}}, {fmt(t18a + 0.3)});')

t19a, t19b = win(19)                    # Krishna's calm amusement
tw.append(f'tl.to("#head-kri", {{rotation: 5, svgOrigin: "131 152", duration: 0.45, ease: "sine.inOut"}}, {fmt(t19a)});')
tw.append(f'tl.to("#head-kri", {{rotation: 0, svgOrigin: "131 152", duration: 0.45, ease: "sine.inOut"}}, {fmt(t19b)});')

t20a, t20b = win(20)                    # one step toward Duryodhan
tw.append(f'tl.to("#krishna", {{x: -50, duration: 0.8, ease: "power1.inOut"}}, {fmt(t20a)});')
# scale the HTML wrapper, not the inner <g>: divs don't clip, the SVG viewport does
tw.append(f'tl.to("#krishna", {{scale: 1.04, transformOrigin: "50% 100%", duration: {fmt(max(0.8, t20b - t20a))}, ease: "sine.in"}}, {fmt(t20a)});')

# -- scene 5: विश्वरूप -------------------------------------------------------
t21a, t21b = win(21)
for dt in (0.0, 0.4):                   # double flash
    tw.append(f'tl.fromTo("#flash", {{opacity: 0}}, {{opacity: 0.95, duration: 0.09, repeat: 1, yoyo: true, ease: "none", immediateRender: false}}, {fmt(t21a + dt)});')
    tw.append(f'tl.set("#flash", {{opacity: 0}}, {fmt(t21a + dt + 0.25)});')
for k in range(6):
    tw.append(f'tl.to("#shaker", {{x: {10 if k % 2 == 0 else -10}, duration: 0.05}}, {fmt(t21a + 0.05 + k * 0.05)});')
tw.append(f'tl.set("#shaker", {{x: 0}}, {fmt(t21a + 0.4)});')
tw.append(f'tl.to("#krishna", {{scale: 1.62, transformOrigin: "50% 100%", duration: 1.6, ease: "power2.inOut"}}, {fmt(t21a + 0.1)});')
tw.append(f'tl.fromTo("#viswa-glow", {{scale: 0.2, opacity: 0, svgOrigin: "460 980"}}, '
          f'{{scale: 1.0, opacity: 0.9, duration: 1.4, ease: "power2.out", immediateRender: false}}, {fmt(t21a + 0.15)});')
tw.append(f'tl.to("#cosmic-dark", {{opacity: 0.45, duration: 0.8, ease: "sine.out"}}, {fmt(t21a + 0.2)});')
for k in range(2):
    tw.append(f'tl.to("#flame-{k}", {{scale: 1.3, svgOrigin: "{308 + 392 * k} 866", duration: 0.6, ease: "sine.out"}}, {fmt(t21a + 0.2)});')

t22a, t22b = win(22)                    # rays, the fan of arms, drifting worlds
tw.append(f'tl.to("#cosmic-dark", {{opacity: 0.72, duration: 1.2, ease: "sine.inOut"}}, {fmt(t22a)});')
tw.append(f'tl.fromTo("#rays-vis", {{scale: 0.3, opacity: 0, svgOrigin: "460 790"}}, '
          f'{{scale: 1.15, opacity: 0.85, duration: 0.9, ease: "power2.out", immediateRender: false}}, {fmt(t22a)});')
tw.append(f'tl.to("#rays-vis", {{rotation: 10, svgOrigin: "460 790", duration: {fmt(win(26)[0] - t22a)}, ease: "none"}}, {fmt(t22a)});')
for k in range(4):
    rot = (-48, -16, 16, 48)[k]
    tw.append(f'tl.fromTo("#fan-arm-{k}", {{rotation: 0, opacity: 0, svgOrigin: "460 900"}}, '
              f'{{rotation: {rot}, opacity: 0.92, duration: 0.7, ease: "power2.out", immediateRender: false}}, {fmt(t22a + 0.3 + 0.16 * k)});')
mote_end = win(26)[0]
for k in range(6):
    start = t22a + 0.4 * k
    reps = max(1, int((mote_end - start) / 2.4) - 1)
    tw.append(f'tl.fromTo("#mote-{k}", {{y: 60, opacity: 0.65}}, {{y: -150, opacity: 0, duration: 2.4, '
              f'repeat: {reps}, ease: "power1.out", immediateRender: false}}, {fmt(start)});')
    tw.append(f'tl.set("#mote-{k}", {{opacity: 0}}, {fmt(start + 2.4 * (reps + 1))});')

t23a, t23b = win(23)                    # the chains SNAP; the court is thrown
for k in range(5):
    dx = 130 + 46 * k
    dy = -70 - 22 * (k % 3)
    tw.append(f'tl.to("#clink-{k}", {{x: {dx}, y: {dy}, rotation: {90 + 70 * k}, duration: 0.32, ease: "power3.out"}}, {fmt(t23a + 0.1)});')
    tw.append(f'tl.to("#clink-{k}", {{y: 480, opacity: 0, rotation: {200 + 90 * k}, duration: 0.6, ease: "power2.in"}}, {fmt(t23a + 0.45)});')
    tw.append(f'tl.set("#clink-{k}", {{opacity: 0}}, {fmt(t23a + 1.1)});')
tw.append(f'tl.to("#dushasana", {{x: 240, rotation: -70, transformOrigin: "20% 100%", duration: 0.55, ease: "power2.in"}}, {fmt(t23a + 0.25)});')
tw.append(f'tl.to("#guard-1", {{x: -430, rotation: 72, transformOrigin: "80% 100%", duration: 0.55, ease: "power2.in"}}, {fmt(t23a + 0.3)});')
tw.append(f'tl.to("#guard-2", {{x: -190, rotation: 76, transformOrigin: "80% 100%", duration: 0.6, ease: "power2.in"}}, {fmt(t23a + 0.35)});')
tw.append(f'tl.to("#arm-dur", {{rotation: 118, svgOrigin: "112 212", duration: 0.35, ease: "power2.out"}}, {fmt(t23a + 0.2)});')
tw.append(f'tl.to("#duryodhan", {{x: 95, rotation: -7, transformOrigin: "50% 100%", duration: 0.5, ease: "power2.out"}}, {fmt(t23a + 0.25)});')
for k in range(4):
    tw.append(f'tl.to("#court-row", {{x: {7 if k % 2 == 0 else -7}, duration: 0.07}}, {fmt(t23a + 0.2 + k * 0.07)});')
tw.append(f'tl.set("#court-row", {{x: 0}}, {fmt(t23a + 0.55)});')
for k in range(4):
    tw.append(f'tl.to("#shaker", {{x: {7 if k % 2 == 0 else -7}, duration: 0.05}}, {fmt(t23a + 0.1 + k * 0.05)});')
tw.append(f'tl.set("#shaker", {{x: 0}}, {fmt(t23a + 0.35)});')

t24a, t24b = win(24)                    # divine sight for the blind king
tw.append(f'tl.to("#dhritarashtra", {{y: -26, duration: 0.8, ease: "power1.out"}}, {fmt(t24a + 0.2)});')
tw.append(f'tl.to("#eyes-dhr-closed", {{opacity: 0, duration: 0.7, ease: "sine.inOut"}}, {fmt(t24a + 0.5)});')
tw.append(f'tl.to("#eyes-dhr-divine", {{opacity: 1, duration: 0.7, ease: "sine.inOut"}}, {fmt(t24a + 0.5)});')

t25a, t25b = win(25)                    # "हे माधव! क्षमा करें..." — folded hands
tw.append(f'tl.to("#hands-dhr", {{opacity: 1, duration: 0.4, ease: "sine.out"}}, {fmt(t25a)});')
tw.append(f'tl.to("#dhr-body", {{rotation: 1.1, svgOrigin: "130 330", duration: 0.25, repeat: {max(2, int((t25b - t25a - 0.5) / 0.25))}, yoyo: true, ease: "sine.inOut"}}, {fmt(t25a + 0.2)});')
tw.append(f'tl.set("#dhr-body", {{rotation: 0}}, {fmt(t25b)});')

# -- scene 6: withdrawal + departure ----------------------------------------
t26a, t26b = win(26)
tw.append(f'tl.to("#krishna", {{scale: 1.0, transformOrigin: "50% 100%", duration: 1.2, ease: "power2.inOut"}}, {fmt(t26a)});')
tw.append(f'tl.to("#viswa-glow", {{scale: 0.2, opacity: 0, svgOrigin: "460 980", duration: 1.1, ease: "power2.in"}}, {fmt(t26a)});')
tw.append(f'tl.set("#viswa-glow", {{opacity: 0}}, {fmt(t26a + 1.15)});')
tw.append(f'tl.to("#rays-vis", {{opacity: 0, scale: 0.4, svgOrigin: "460 790", duration: 0.9, ease: "power2.in"}}, {fmt(t26a)});')
tw.append(f'tl.set("#rays-vis", {{opacity: 0}}, {fmt(t26a + 0.95)});')
for k in range(4):
    tw.append(f'tl.to("#fan-arm-{k}", {{rotation: 0, opacity: 0, svgOrigin: "460 900", duration: 0.8, ease: "power2.in"}}, {fmt(t26a + 0.1 * k)});')
    tw.append(f'tl.set("#fan-arm-{k}", {{opacity: 0}}, {fmt(t26a + 0.9 + 0.1 * k)});')
tw.append(f'tl.to("#cosmic-dark", {{opacity: 0, duration: 1.3, ease: "sine.inOut"}}, {fmt(t26a + 0.3)});')
tw.append(f'tl.set("#cosmic-dark", {{opacity: 0}}, {fmt(t26a + 1.65)});')
for k in range(2):
    tw.append(f'tl.to("#flame-{k}", {{scale: 1.0, svgOrigin: "{308 + 392 * k} 866", duration: 0.8, ease: "sine.inOut"}}, {fmt(t26a + 0.3)});')
tw.append(f'tl.to("#eyes-dhr-divine", {{opacity: 0, duration: 0.8, ease: "sine.inOut"}}, {fmt(t26a + 0.4)});')
tw.append(f'tl.set("#eyes-dhr-divine", {{opacity: 0}}, {fmt(t26a + 1.25)});')
tw.append(f'tl.to("#eyes-dhr-closed", {{opacity: 1, duration: 0.8, ease: "sine.inOut"}}, {fmt(t26a + 0.4)});')
tw.append(f'tl.to("#arm-dur", {{rotation: 0, svgOrigin: "112 212", duration: 1.0, ease: "sine.inOut"}}, {fmt(t26a + 0.8)});')
tw.append(f'tl.to("#duryodhan", {{rotation: 0, transformOrigin: "50% 100%", duration: 1.0, ease: "sine.inOut"}}, {fmt(t26a + 0.8)});')
tw.append(f'tl.to("#krishna", {{x: -1150, duration: 2.1, ease: "power1.in"}}, {fmt(t26a + 1.3)});')

t27a = win(27)[0]                       # dusk: the silhouette chariot departs
tw.append(f'tl.fromTo("#chariot2", {{x: 0}}, {{x: 1900, duration: {fmt(total - t27a)}, ease: "none", immediateRender: false}}, {fmt(t27a)});')
reps = max(1, int((total - t27a) / 2.4) + 1)
tw.append(f'tl.to("#dusk-glow", {{opacity: 0.6, duration: 2.4, repeat: {reps}, yoyo: true, ease: "sine.inOut"}}, {fmt(t27a)});')
tw.append(f'tl.to("#dusk-sun", {{y: 16, duration: {fmt(total - t27a)}, ease: "none"}}, {fmt(t27a)});')

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
for i in range(1, 29):
    t0, _ = win(i)
    dur = (win(i + 1)[0] - t0) if i < 28 else (total - t0)
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

rays_lines = []
for k in range(12):
    a = math.radians(k * 30)
    x1, y1 = 460 + 225 * math.cos(a), 790 + 225 * math.sin(a)
    x2, y2 = 460 + 345 * math.cos(a), 790 + 345 * math.sin(a)
    rays_lines.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}"/>')
RAYS = "\n          ".join(rays_lines)

MOTES = "\n        ".join(
    f'<circle id="mote-{k}" cx="{330 + 55 * k}" cy="{1120 - 30 * (k % 3)}" r="{5 + (k % 3) * 2}" fill="#fff3c4" opacity="0"/>'
    for k in range(6)
)

CLINKS = "\n          ".join(
    f'<ellipse id="clink-{k}" cx="241" cy="{312 + 27 * k}" rx="11" ry="14" fill="none" stroke="#9aa2b8" stroke-width="6"/>'
    for k in range(5)
)

# ---------------------------------------------------------------- the rigs
KRI_SVG = """
      <svg width="260" height="445" viewBox="0 0 260 445">
        <g id="kri-body">
        <path d="M96 380 Q92 300 100 250 L160 250 Q168 300 164 380 Z" fill="#f0c23c"/>
        <path d="M100 258 Q131 268 160 258 L160 300 Q131 312 100 300 Z" fill="#d99f1e" opacity="0.5"/>
        <path d="M86 240 Q88 168 131 162 Q174 168 176 240 L172 268 L90 268 Z" fill="#4a66ad"/>
        <path d="M92 176 Q131 158 170 176 L176 240 L86 240 Z" fill="#4a66ad"/>
        <path d="M88 190 L174 234 L174 252 L88 208 Z" fill="#f0c23c"/>
        <circle cx="110" cy="200" r="4" fill="#fff"/><circle cx="122" cy="206" r="4" fill="#fff"/>
        <circle cx="134" cy="212" r="4" fill="#fff"/><circle cx="146" cy="218" r="4" fill="#fff"/>
        <path d="M86 236 Q70 262 76 300 L94 296 Q90 266 98 246 Z" fill="#4a66ad"/>
        <rect x="72" y="252" width="26" height="10" rx="5" fill="#e8b73a"/>
        <g id="arm-kri">
          <path d="M170 205 Q198 224 206 268 L188 278 Q178 240 156 226 Z" fill="#4a66ad"/>
          <rect x="182" y="240" width="26" height="10" rx="5" fill="#e8b73a" transform="rotate(60 195 245)"/>
          <circle cx="199" cy="276" r="13" fill="#4a66ad"/>
        </g>
        <g id="legs-kri">
          <rect x="104" y="378" width="20" height="48" fill="#3d5691"/>
          <rect x="138" y="378" width="20" height="48" fill="#3d5691"/>
          <rect x="96" y="422" width="36" height="14" rx="7" fill="#8a5a2e"/>
          <rect x="130" y="422" width="36" height="14" rx="7" fill="#8a5a2e"/>
        </g>
        <g id="head-kri">
          <circle cx="131" cy="90" r="54" fill="#4a66ad"/>
          <path d="M79 78 Q83 40 131 36 Q179 40 183 78 Q150 58 112 62 Q92 68 79 78 Z" fill="#1c1430"/>
          <path d="M84 62 Q131 40 178 62 L172 46 Q131 26 90 46 Z" fill="#e8b73a"/>
          <path d="M124 40 Q131 20 138 40 Z" fill="#e8b73a"/>
          <ellipse cx="146" cy="22" rx="9" ry="14" fill="#2e7d5b"/>
          <ellipse cx="146" cy="20" rx="4.5" ry="7" fill="#1c4f8a"/>
          <path d="M126 62 Q131 52 136 62 Q131 68 126 62 Z" fill="#e8b73a"/>
          <g id="eyes-kri">
            <circle cx="111" cy="90" r="10" fill="#fff"/><circle cx="151" cy="90" r="10" fill="#fff"/>
            <circle cx="113" cy="92" r="5" fill="#141024"/><circle cx="153" cy="92" r="5" fill="#141024"/>
          </g>
          <path d="M99 73 Q111 67 123 73" stroke="#141024" stroke-width="4.5" fill="none" stroke-linecap="round"/>
          <path d="M139 73 Q151 67 163 73" stroke="#141024" stroke-width="4.5" fill="none" stroke-linecap="round"/>
          <ellipse id="mouth-kri" cx="131" cy="122" rx="11" ry="3" fill="#33163a"/>
          <rect x="121" y="140" width="20" height="14" fill="#4a66ad"/>
        </g>
        </g>
      </svg>"""

DUR_SVG = """
      <svg width="280" height="450" viewBox="0 0 280 450">
        <g id="dur-body">
        <path d="M84 400 Q76 290 88 246 L196 246 Q208 290 200 400 Z" fill="#6e1b28"/>
        <path d="M84 400 L200 400 L196 420 L88 420 Z" fill="#4a1018"/>
        <path d="M78 250 Q80 168 142 160 Q204 168 206 250 L200 270 L84 270 Z" fill="#7a1f2e"/>
        <path d="M88 176 Q142 156 196 176 L206 250 L78 250 Z" fill="#7a1f2e"/>
        <path d="M96 178 L188 178 L196 250 L88 250 Z" fill="none" stroke="#d9a53a" stroke-width="5"/>
        <path d="M118 176 Q142 192 166 176 L166 210 Q142 222 118 210 Z" fill="#d9a53a"/>
        <path d="M196 240 Q214 266 208 306 L188 300 Q194 268 184 248 Z" fill="#d99a66"/>
        <rect x="186" y="258" width="26" height="10" rx="5" fill="#d9a53a"/>
        <g id="arm-dur">
          <path d="M112 212 Q86 234 80 282 L100 290 Q108 250 128 232 Z" fill="#d99a66"/>
          <circle cx="90" cy="292" r="14" fill="#b87840"/>
          <rect x="78" y="252" width="26" height="10" rx="5" fill="#d9a53a" transform="rotate(-60 91 257)"/>
        </g>
        <rect x="106" y="396" width="24" height="38" fill="#2c1016"/>
        <rect x="150" y="396" width="24" height="38" fill="#2c1016"/>
        <rect x="98" y="430" width="42" height="14" rx="7" fill="#1c0a10"/>
        <rect x="142" y="430" width="42" height="14" rx="7" fill="#1c0a10"/>
        <g id="head-dur">
          <circle cx="142" cy="92" r="56" fill="#d99a66"/>
          <path d="M88 76 Q92 40 142 36 Q192 40 196 76 L196 96 Q168 72 116 76 Q98 80 88 96 Z" fill="#2a1408"/>
          <path d="M92 62 Q142 38 192 62 L198 42 L172 46 L162 26 L142 42 L122 26 L112 46 L86 42 Z" fill="#d9a53a"/>
          <circle cx="142" cy="40" r="7" fill="#a01c2e"/>
          <g id="eyes-dur">
            <circle cx="120" cy="92" r="10" fill="#fff"/><circle cx="164" cy="92" r="10" fill="#fff"/>
            <circle cx="118" cy="94" r="5" fill="#1c0e04"/><circle cx="162" cy="94" r="5" fill="#1c0e04"/>
          </g>
          <path d="M106 78 L132 70" stroke="#1c0e04" stroke-width="6" stroke-linecap="round"/>
          <path d="M178 78 L152 70" stroke="#1c0e04" stroke-width="6" stroke-linecap="round"/>
          <path d="M118 116 Q130 108 142 116 Q154 108 166 116 Q154 124 142 118 Q130 124 118 116 Z" fill="#2a1408"/>
          <ellipse id="mouth-dur" cx="142" cy="128" rx="11" ry="3" fill="#5c1414"/>
          <rect x="132" y="142" width="20" height="14" fill="#d99a66"/>
        </g>
        </g>
      </svg>"""

DHR_SVG = """
      <svg width="260" height="360" viewBox="0 0 260 360">
        <g id="dhr-body">
        <path d="M66 340 Q60 220 84 190 L176 190 Q200 220 194 340 Z" fill="#e8dcc0"/>
        <path d="M70 250 Q68 300 70 340 L92 340 Q88 292 92 254 Z" fill="#d4c49a"/>
        <path d="M190 250 Q192 300 190 340 L168 340 Q172 292 168 254 Z" fill="#d4c49a"/>
        <path d="M84 190 Q86 170 130 166 Q174 170 176 190 L176 214 L84 214 Z" fill="#e8dcc0"/>
        <g id="hands-dhr" opacity="0">
          <path d="M118 230 Q130 200 142 230 L142 286 Q130 296 118 286 Z" fill="#caa27a"/>
          <path d="M124 224 L136 224" stroke="#a8825c" stroke-width="4" stroke-linecap="round"/>
        </g>
        <g id="head-dhr">
          <circle cx="130" cy="96" r="50" fill="#caa27a"/>
          <path d="M84 80 Q88 46 130 42 Q172 46 176 80 L176 92 Q150 72 108 76 Q92 80 84 92 Z" fill="#d8d4cc"/>
          <path d="M88 66 Q130 44 172 66 L176 50 L152 52 L130 38 L108 52 L84 50 Z" fill="#d9a53a"/>
          <circle cx="130" cy="46" r="6" fill="#c8ccd8"/>
          <path d="M96 120 Q130 176 164 120 L164 96 Q130 116 96 96 Z" fill="#d8d4cc"/>
          <g id="eyes-dhr-closed">
            <path d="M100 92 Q110 100 120 92" stroke="#5c4630" stroke-width="4.5" fill="none" stroke-linecap="round"/>
            <path d="M140 92 Q150 100 160 92" stroke="#5c4630" stroke-width="4.5" fill="none" stroke-linecap="round"/>
          </g>
          <g id="eyes-dhr-divine" opacity="0">
            <circle cx="110" cy="92" r="14" fill="#fff7d0" opacity="0.45"/>
            <circle cx="150" cy="92" r="14" fill="#fff7d0" opacity="0.45"/>
            <circle cx="110" cy="92" r="8" fill="#fffdf0"/>
            <circle cx="150" cy="92" r="8" fill="#fffdf0"/>
          </g>
          <ellipse id="mouth-dhr" cx="130" cy="124" rx="9" ry="3" fill="#4a2618"/>
        </g>
        </g>
      </svg>"""

VID_SVG = """
      <svg width="240" height="410" viewBox="0 0 240 410">
        <g id="vid-body">
        <path d="M70 380 Q64 250 84 210 L156 210 Q176 250 170 380 Z" fill="#f0ead8"/>
        <path d="M84 210 Q86 160 120 156 Q154 160 156 210 L156 240 L84 240 Z" fill="#f0ead8"/>
        <path d="M84 226 Q70 252 74 292 L92 288 Q88 258 96 240 Z" fill="#caa27a"/>
        <path d="M156 226 Q176 244 178 282 L160 286 Q156 256 146 240 Z" fill="#caa27a"/>
        <path d="M148 268 Q170 262 186 272 Q182 292 158 292 Q144 284 148 268 Z" fill="#8a5a2e"/>
        <ellipse cx="167" cy="270" rx="16" ry="7" fill="#4a7a3a"/>
        <g id="head-vid">
          <circle cx="120" cy="86" r="46" fill="#caa27a"/>
          <path d="M78 72 Q82 42 120 38 Q158 42 162 72 L162 84 Q138 66 102 70 Q86 74 78 84 Z" fill="#b8b4ac"/>
          <circle cx="120" cy="36" r="10" fill="#b8b4ac"/>
          <g id="eyes-vid">
            <circle cx="102" cy="86" r="8" fill="#fff"/><circle cx="138" cy="86" r="8" fill="#fff"/>
            <circle cx="104" cy="88" r="4" fill="#241408"/><circle cx="140" cy="88" r="4" fill="#241408"/>
          </g>
          <path d="M92 72 Q102 67 112 72" stroke="#5c4630" stroke-width="4" fill="none" stroke-linecap="round"/>
          <path d="M128 72 Q138 67 148 72" stroke="#5c4630" stroke-width="4" fill="none" stroke-linecap="round"/>
          <path d="M108 112 Q120 120 132 112" stroke="#6a3a24" stroke-width="4" fill="none" stroke-linecap="round"/>
        </g>
        </g>
      </svg>"""

DUS_SVG = f"""
      <svg width="280" height="440" viewBox="0 0 280 440">
        <path d="M92 390 Q86 290 96 250 L188 250 Q198 290 192 390 Z" fill="#5c1a20"/>
        <path d="M86 254 Q88 176 142 168 Q196 176 198 254 L192 274 L92 274 Z" fill="#4a5064"/>
        <path d="M94 184 L190 184 L196 254 L88 254 Z" fill="none" stroke="#8a92a8" stroke-width="5"/>
        <path d="M116 184 Q142 198 168 184 L168 214 Q142 226 116 214 Z" fill="#8a92a8"/>
        <path d="M92 230 Q74 254 78 296 L98 292 Q94 262 104 240 Z" fill="#c8905c"/>
        <g id="chain-arm">
          <path d="M188 210 Q216 232 230 276 L212 290 Q200 250 176 230 Z" fill="#c8905c"/>
          <circle cx="223" cy="286" r="13" fill="#a87040"/>
        </g>
        <g id="chain-dus">
          {CLINKS}
        </g>
        <rect x="110" y="388" width="24" height="36" fill="#2c2030"/>
        <rect x="150" y="388" width="24" height="36" fill="#2c2030"/>
        <rect x="102" y="420" width="42" height="14" rx="7" fill="#181020"/>
        <rect x="146" y="420" width="42" height="14" rx="7" fill="#181020"/>
        <circle cx="142" cy="98" r="52" fill="#c8905c"/>
        <path d="M92 86 Q94 46 142 42 Q190 46 192 86 L192 74 Q206 82 204 100 L192 100 L92 100 L80 100 Q78 82 92 74 Z" fill="#3c4254"/>
        <path d="M136 44 Q142 20 148 44 Z" fill="#a01c2e"/>
        <g id="eyes-dus">
          <circle cx="122" cy="98" r="9" fill="#fff"/><circle cx="162" cy="98" r="9" fill="#fff"/>
          <circle cx="120" cy="100" r="4.5" fill="#180c04"/><circle cx="160" cy="100" r="4.5" fill="#180c04"/>
        </g>
        <path d="M108 86 L134 78" stroke="#180c04" stroke-width="5" stroke-linecap="round"/>
        <path d="M176 86 L150 78" stroke="#180c04" stroke-width="5" stroke-linecap="round"/>
        <path d="M122 122 Q142 112 162 122 Q152 130 142 126 Q132 130 122 122 Z" fill="#2a1408"/>
        <ellipse cx="142" cy="132" rx="9" ry="3" fill="#5c1414"/>
      </svg>"""

def guard_svg(mirror):
    inner = """
        <path d="M78 380 Q74 292 82 254 L158 254 Q166 292 162 380 Z" fill="#3a2c34"/>
        <path d="M74 258 Q76 190 120 182 Q164 190 166 258 L160 276 L80 276 Z" fill="#565c6e"/>
        <path d="M98 194 Q120 206 142 194 L142 220 Q120 230 98 220 Z" fill="#8a92a8"/>
        <line x1="186" y1="120" x2="186" y2="400" stroke="#6a5238" stroke-width="9" stroke-linecap="round"/>
        <path d="M186 118 L174 94 L198 94 Z" fill="#9aa2b8"/>
        <path d="M160 236 Q178 250 182 284 L166 290 Q160 262 148 248 Z" fill="#bc8858"/>
        <path d="M80 236 Q64 258 68 296 L86 292 Q82 264 92 248 Z" fill="#bc8858"/>
        <rect x="92" y="378" width="22" height="34" fill="#241a24"/>
        <rect x="126" y="378" width="22" height="34" fill="#241a24"/>
        <rect x="84" y="408" width="40" height="13" rx="6" fill="#140e16"/>
        <rect x="124" y="408" width="40" height="13" rx="6" fill="#140e16"/>
        <circle cx="120" cy="92" r="46" fill="#bc8858"/>
        <path d="M76 82 Q78 46 120 42 Q162 46 164 82 L164 94 L76 94 Z" fill="#3c4254"/>
        <circle cx="104" cy="94" r="7" fill="#241408"/><circle cx="136" cy="94" r="7" fill="#241408"/>
        <path d="M104 118 Q120 112 136 118" stroke="#241408" stroke-width="4" fill="none" stroke-linecap="round"/>"""
    if mirror:
        return f'<svg width="220" height="425" viewBox="0 0 220 425"><g transform="translate(220 0) scale(-1 1)">{inner}</g></svg>'
    return f'<svg width="220" height="425" viewBox="0 0 220 425">{inner}</svg>'

CHARIOT_SVG = """
      <svg width="560" height="410" viewBox="0 0 560 410">
        <g id="chariot-body">
          <path d="M330 120 Q420 96 500 130 L500 190 Q420 168 330 186 Z" fill="#8a4a2e"/>
          <path d="M470 150 Q520 170 540 220 Q520 250 480 244 Q450 200 440 168 Z" fill="#e8e2d4"/>
          <path d="M540 220 Q560 232 556 252 Q540 260 524 250 Z" fill="#e8e2d4"/>
          <path d="M446 246 L452 310 L438 310 L430 250 Z" fill="#d8d2c4"/>
          <path d="M478 246 L488 310 L474 310 L466 250 Z" fill="#d8d2c4"/>
          <path d="M60 160 Q64 110 130 106 L240 106 Q262 128 258 200 L262 250 L58 250 Q48 200 60 160 Z" fill="#a02c2e"/>
          <path d="M66 166 Q70 122 132 118 L234 118 L240 160 L64 200 Z" fill="#c8452e"/>
          <path d="M60 160 L258 160" stroke="#e8b73a" stroke-width="7"/>
          <path d="M58 244 L262 244" stroke="#e8b73a" stroke-width="7"/>
          <path d="M96 108 Q90 40 130 26 L134 40 Q106 56 110 108 Z" fill="#8a4a2e"/>
          <g id="flag-krishna">
            <path d="M132 28 L212 44 L132 62 Z" fill="#f0c23c"/>
            <circle cx="158" cy="45" r="9" fill="#a02c2e"/>
          </g>
          <path d="M240 170 L360 150 L360 162 L242 184 Z" fill="#6a3a22"/>
        </g>
        <g id="wheel-a">
          <circle cx="120" cy="300" r="72" fill="#5c3018"/>
          <circle cx="120" cy="300" r="58" fill="#7a4424"/>
          <g stroke="#3c1e0c" stroke-width="9">
            <line x1="120" y1="248" x2="120" y2="352"/><line x1="68" y1="300" x2="172" y2="300"/>
            <line x1="84" y1="264" x2="156" y2="336"/><line x1="156" y1="264" x2="84" y2="336"/>
          </g>
          <circle cx="120" cy="300" r="14" fill="#e8b73a"/>
        </g>
        <g id="wheel-b">
          <circle cx="395" cy="300" r="72" fill="#5c3018"/>
          <circle cx="395" cy="300" r="58" fill="#7a4424"/>
          <g stroke="#3c1e0c" stroke-width="9">
            <line x1="395" y1="248" x2="395" y2="352"/><line x1="343" y1="300" x2="447" y2="300"/>
            <line x1="359" y1="264" x2="431" y2="336"/><line x1="431" y1="264" x2="359" y2="336"/>
          </g>
          <circle cx="395" cy="300" r="14" fill="#e8b73a"/>
        </g>
      </svg>"""

# ------------------------------------------------------------------ the page
TITLE = pj.get("title", "शांतिदूत कृष्ण")
KICKER = pj.get("topic", "महाभारत की कथा")
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
    #stage {{ background: #1a0c14; font-family: -apple-system, "Segoe UI", Roboto, "Noto Sans Devanagari", Helvetica, Arial, sans-serif; overflow: hidden; }}
    #world, #shaker {{ position: absolute; inset: 0; }}
    #world {{ transform-origin: 0px 0px; }}
    .abs {{ position: absolute; }}
    .caption {{ position: absolute; top: 1380px; left: 50%; transform: translateX(-50%);
      max-width: 840px; background: rgba(0, 0, 0, 0.85); border-radius: 18px; padding: 18px 34px;
      font-size: 54px; font-weight: 700; text-align: center; }}
    .stamp {{ position: absolute; top: 300px; left: 50%; transform: translateX(-50%) rotate(-2deg);
      background: rgba(24, 8, 14, 0.88); border: 2px solid #d9a53a; color: #ffe2ae; border-radius: 14px;
      padding: 14px 32px; font-size: 42px; font-weight: 800; letter-spacing: 2px; white-space: nowrap; opacity: 0; }}
    #title-card {{ position: absolute; top: 110px; left: 0; right: 120px; margin: 0 auto; width: fit-content;
      text-align: center; z-index: 5; }}
    #kicker {{ color: #f0c06a; font-size: 36px; font-weight: 800; letter-spacing: 6px; }}
    #title-chip {{ margin-top: 14px; background: rgba(24, 8, 14, 0.92); border: 2px solid rgba(240, 192, 106, 0.6);
      border-radius: 22px; padding: 18px 42px; color: #fff; font-size: 64px; font-weight: 800; }}
  </style>

  <div id="world" class="clip" data-start="0" data-duration="{fmt(total)}" data-track-index="0">
  <div id="shaker">

    <!-- SET 1: the war road to Hastinapura -->
    <div class="abs clip" style="left:0; top:0;" data-start="0" data-duration="{fmt(S_HUT)}" data-track-index="0">
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        <defs>
          <linearGradient id="warsky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#141026"/><stop offset="0.55" stop-color="#4a2438"/>
            <stop offset="0.85" stop-color="#8a4032"/><stop offset="1" stop-color="#a85a36"/>
          </linearGradient>
          <radialGradient id="rsun" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stop-color="#ffb46a" stop-opacity="0.8"/><stop offset="1" stop-color="#ffb46a" stop-opacity="0"/>
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="1080" height="1400" fill="url(#warsky)"/>
        <circle id="road-sun-glow" cx="540" cy="1120" r="200" fill="url(#rsun)" opacity="0.35"/>
        <circle cx="540" cy="1120" r="88" fill="#e88a4a"/>
        <path id="cloud-0" d="M80 340 Q150 290 240 320 Q330 280 420 330 Q360 380 240 370 Q140 386 80 340 Z" fill="#221c34" opacity="0.9"/>
        <path id="cloud-1" d="M620 220 Q700 170 810 205 Q920 170 1000 230 Q930 280 800 268 Q690 286 620 220 Z" fill="#261e38" opacity="0.85"/>
        <g id="gates">
          <path d="M850 760 L890 720 L1080 720 L1080 1360 L850 1360 Z" fill="#6e5238"/>
          <path d="M880 820 Q975 740 1070 820 L1070 1360 L880 1360 Z" fill="#3c2a1c"/>
          <rect x="850" y="700" width="240" height="34" fill="#8a6a48"/>
          <path d="M872 700 L872 640 L906 660 L872 668 Z" fill="#a02c2e"/>
          <path d="M1010 700 L1010 628 L1046 650 L1010 658 Z" fill="#a02c2e"/>
          <rect x="856" y="760" width="18" height="600" fill="#8a6a48"/>
        </g>
        <g id="army-l" fill="#1a1224">
          <path d="M0 1230 L440 1230 L440 1380 L0 1380 Z" opacity="0.001"/>
          <g>
            <circle cx="40" cy="1270" r="16"/><circle cx="92" cy="1262" r="16"/><circle cx="144" cy="1272" r="16"/>
            <circle cx="196" cy="1260" r="16"/><circle cx="248" cy="1270" r="16"/><circle cx="300" cy="1262" r="16"/>
            <circle cx="352" cy="1272" r="16"/><rect x="24" y="1276" width="344" height="104"/>
            <line x1="60" y1="1250" x2="60" y2="1130" stroke="#1a1224" stroke-width="7"/>
            <line x1="160" y1="1250" x2="160" y2="1110" stroke="#1a1224" stroke-width="7"/>
            <line x1="264" y1="1250" x2="264" y2="1124" stroke="#1a1224" stroke-width="7"/>
            <path d="M160 1110 L214 1122 L160 1136 Z" fill="#c8a03a"/>
          </g>
        </g>
        <g id="army-r" fill="#160e1c">
          <circle cx="740" cy="1270" r="16"/><circle cx="792" cy="1262" r="16"/><circle cx="844" cy="1272" r="16"/>
          <circle cx="896" cy="1260" r="16"/><circle cx="948" cy="1270" r="16"/><circle cx="1000" cy="1262" r="16"/>
          <rect x="724" y="1276" width="316" height="104"/>
          <line x1="780" y1="1250" x2="780" y2="1118" stroke="#160e1c" stroke-width="7"/>
          <line x1="900" y1="1250" x2="900" y2="1104" stroke="#160e1c" stroke-width="7"/>
          <path d="M900 1104 L954 1116 L900 1130 Z" fill="#a02c2e"/>
        </g>
        <rect x="0" y="1330" width="1080" height="180" fill="#5c3c2c"/>
        <rect x="0" y="1500" width="1080" height="420" fill="#2c1a16"/>
        <path d="M0 1420 L1080 1404 L1080 1414 L0 1432 Z" fill="#3c281e" opacity="0.8"/>
      </svg>
    </div>

    <!-- SET 2: Vidura's hut -->
    <div class="abs clip" style="left:0; top:0;" data-start="{fmt(S_HUT)}" data-duration="{fmt(S_SABHA - S_HUT)}" data-track-index="0">
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        <rect x="0" y="0" width="1080" height="1920" fill="#4a3020"/>
        <rect x="0" y="0" width="1080" height="1360" fill="#6a4632"/>
        <path d="M0 0 L1080 0 L1080 90 L0 130 Z" fill="#3c2818"/>
        <rect x="660" y="560" width="240" height="300" rx="16" fill="#241c38"/>
        <circle cx="790" cy="640" r="42" fill="#e8e2d0"/>
        <path d="M770 622 Q790 602 812 622 Q812 648 790 656 Q768 648 770 622 Z" fill="#241c38" opacity="0.35"/>
        <rect x="648" y="548" width="264" height="14" fill="#4c3424"/>
        <rect x="648" y="860" width="264" height="14" fill="#4c3424"/>
        <rect x="60" y="480 " width="300" height="12" fill="#4c3424"/>
        <path d="M100 480 Q104 420 140 416 Q176 420 180 480 Z" fill="#8a5c34"/>
        <path d="M220 480 Q222 436 252 432 Q282 436 284 480 Z" fill="#a06a3c"/>
        <g id="diya">
          <path d="M760 1056 Q790 1076 820 1056 Q810 1084 770 1084 Z" fill="#b87840"/>
          <path id="flame-hut" d="M786 1052 Q778 1030 790 1012 Q802 1030 794 1052 Z" fill="#ffc46a"/>
          <circle cx="790" cy="1032" r="30" fill="#ffb46a" opacity="0.22"/>
        </g>
        <rect x="700" y="1080" width="180" height="16" fill="#4c3424"/>
        <rect x="0" y="1360" width="1080" height="560" fill="#3c2414"/>
        <path d="M0 1360 L1080 1360 L1080 1376 L0 1376 Z" fill="#2c1a0e"/>
        <ellipse cx="480" cy="1420" rx="420" ry="46" fill="#5c3a22" opacity="0.5"/>
      </svg>
    </div>

    <!-- SET 3: the Kaurava sabha -->
    <div class="abs clip" style="left:0; top:0;" data-start="{fmt(S_SABHA)}" data-duration="{fmt(S_DUSK - S_SABHA)}" data-track-index="0">
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        <defs>
          <linearGradient id="sabhawall" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#2c0c18"/><stop offset="1" stop-color="#571a28"/>
          </linearGradient>
          <radialGradient id="torchglow" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stop-color="#ffb46a" stop-opacity="0.55"/><stop offset="1" stop-color="#ffb46a" stop-opacity="0"/>
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="1080" height="1400" fill="url(#sabhawall)"/>
        <rect x="0" y="200" width="1080" height="26" fill="#d9a53a" opacity="0.35"/>
        <rect x="30" y="260" width="70" height="1090" fill="#200a12"/>
        <rect x="20" y="260" width="90" height="40" fill="#8a6428"/>
        <rect x="620" y="300" width="64" height="1050" fill="#240c14"/>
        <rect x="610" y="300" width="84" height="36" fill="#8a6428"/>
        <g id="torch-0">
          <circle cx="308" cy="850" r="120" fill="url(#torchglow)"/>
          <rect x="296" y="866" width="24" height="70" rx="8" fill="#5c3018"/>
          <path id="flame-0" d="M308 866 Q288 820 308 780 Q328 820 308 866 Z" fill="#ffb44a"/>
        </g>
        <g id="torch-1">
          <circle cx="700" cy="850" r="120" fill="url(#torchglow)"/>
          <rect x="688" y="866" width="24" height="70" rx="8" fill="#5c3018"/>
          <path id="flame-1" d="M700 866 Q680 820 700 780 Q720 820 700 866 Z" fill="#ffb44a"/>
        </g>
        <path d="M770 1250 L1080 1250 L1080 1340 L740 1340 Z" fill="#6e2430"/>
        <path d="M740 1340 L1080 1340 L1080 1400 L710 1400 Z" fill="#571a24"/>
        <path d="M770 1250 L1080 1250 L1080 1264 L770 1264 Z" fill="#d9a53a" opacity="0.7"/>
        <path d="M830 1250 L830 860 Q940 800 1050 860 L1050 1250 Z" fill="#7a2430"/>
        <path d="M846 1250 L846 880 Q940 828 1034 880 L1034 1250 Z" fill="#d9a53a" opacity="0.28"/>
        <g id="court-row" fill="#200a12">
          <circle cx="180" cy="1210" r="22"/><path d="M148 1224 L212 1224 L216 1330 L144 1330 Z"/>
          <circle cx="300" cy="1218" r="22"/><path d="M268 1232 L332 1232 L336 1330 L264 1330 Z"/>
          <circle cx="420" cy="1210" r="22"/><path d="M388 1224 L452 1224 L456 1330 L384 1330 Z"/>
          <circle cx="540" cy="1220" r="22"/><path d="M508 1234 L572 1234 L576 1330 L504 1330 Z"/>
        </g>
        <g id="bhishma" transform="translate(450 0)">
          <circle cx="150" cy="1010" r="30" fill="#2a1420"/>
          <path d="M126 996 Q150 976 174 996 L174 1010 Q150 994 126 1010 Z" fill="#c8ccd8"/>
          <path d="M112 1036 L188 1036 L196 1330 L104 1330 Z" fill="#2a1420"/>
          <line x1="206" y1="1000" x2="206" y2="1330" stroke="#6a5238" stroke-width="10" stroke-linecap="round"/>
        </g>
        <g id="drona" transform="translate(430 0)">
          <circle cx="268" cy="1030" r="26" fill="#241016"/>
          <path d="M248 1018 Q268 1002 288 1018 L288 1030 Q268 1016 248 1030 Z" fill="#b8b4ac"/>
          <path d="M236 1052 L300 1052 L306 1330 L230 1330 Z" fill="#241016"/>
        </g>
        <rect x="0" y="1330" width="1080" height="590" fill="#2c0e16"/>
        <path d="M0 1340 L1080 1340 L1080 1352 L0 1352 Z" fill="#d9a53a" opacity="0.25"/>
        <path d="M120 1400 L980 1400 L1010 1920 L90 1920 Z" fill="#571420" opacity="0.7"/>
      </svg>
    </div>

    <!-- SET 4: dusk departure -->
    <div class="abs clip" style="left:0; top:0;" data-start="{fmt(S_DUSK)}" data-duration="{fmt(total - S_DUSK)}" data-track-index="0">
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        <defs>
          <linearGradient id="dusksky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#2c1030"/><stop offset="0.5" stop-color="#7a2c3c"/>
            <stop offset="0.82" stop-color="#c86a3a"/><stop offset="1" stop-color="#e8944a"/>
          </linearGradient>
          <radialGradient id="dsun" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stop-color="#ffd98a" stop-opacity="0.85"/><stop offset="1" stop-color="#ffd98a" stop-opacity="0"/>
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="1080" height="1400" fill="url(#dusksky)"/>
        <g id="dusk-sun">
          <circle id="dusk-glow" cx="560" cy="1150" r="240" fill="url(#dsun)" opacity="0.4"/>
          <circle cx="560" cy="1150" r="120" fill="#ffcf7a"/>
        </g>
        <path d="M0 1210 Q240 1080 480 1170 Q760 1060 1080 1180 L1080 1400 L0 1400 Z" fill="#3c1626"/>
        <path d="M0 1290 Q300 1190 600 1270 Q860 1180 1080 1280 L1080 1400 L0 1400 Z" fill="#2a1020"/>
        <path d="M120 420 q16 -16 30 0 q16 -16 30 0" stroke="#241016" stroke-width="6" fill="none" stroke-linecap="round"/>
        <path d="M820 330 q13 -13 24 0 q13 -13 24 0" stroke="#241016" stroke-width="5" fill="none" stroke-linecap="round"/>
        <rect x="0" y="1340" width="1080" height="580" fill="#1e0c14"/>
        <path d="M0 1404 L1080 1390 L1080 1400 L0 1416 Z" fill="#3c281e" opacity="0.6"/>
      </svg>
    </div>

    <div id="cosmic-dark" class="abs" style="left:0; top:0; width:1080px; height:1920px; background:#05020c; opacity:0;"></div>

    <!-- the envoy's chariot -->
    <div id="chariot" class="abs clip" style="left:-600px; top:1020px; width:560px; height:410px;"
         data-start="0" data-duration="{fmt(S_HUT)}" data-track-index="1">{CHARIOT_SVG}
    </div>

    <!-- विश्वरूप radiance (behind Krishna) -->
    <div class="abs clip" style="left:0; top:0;" data-start="{fmt(win(21)[0])}" data-duration="{fmt(S_DUSK - win(21)[0])}" data-track-index="1">
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        <defs>
          <radialGradient id="vglow" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stop-color="#fff3c8" stop-opacity="0.95"/>
            <stop offset="0.55" stop-color="#ffce6a" stop-opacity="0.5"/>
            <stop offset="1" stop-color="#ffce6a" stop-opacity="0"/>
          </radialGradient>
        </defs>
        <g transform="translate(30 -10)">
        <circle id="viswa-glow" cx="460" cy="980" r="470" fill="url(#vglow)" opacity="0"/>
        <g id="fan-arm-0" opacity="0">
          <path d="M442 900 L442 662 Q460 632 478 662 L478 900 Z" fill="#f5cf6e"/>
          <circle cx="460" cy="648" r="20" fill="none" stroke="#b8862e" stroke-width="5"/>
          <line x1="460" y1="630" x2="460" y2="666" stroke="#b8862e" stroke-width="4"/>
          <line x1="442" y1="648" x2="478" y2="648" stroke="#b8862e" stroke-width="4"/>
        </g>
        <g id="fan-arm-1" opacity="0">
          <path d="M442 900 L442 662 Q460 632 478 662 L478 900 Z" fill="#f5cf6e"/>
          <path d="M448 660 Q460 626 472 660 Q472 674 460 678 Q448 674 448 660 Z" fill="#f8f4e8"/>
        </g>
        <g id="fan-arm-2" opacity="0">
          <path d="M442 900 L442 662 Q460 632 478 662 L478 900 Z" fill="#f5cf6e"/>
          <line x1="460" y1="676" x2="460" y2="636" stroke="#8a5c1e" stroke-width="7" stroke-linecap="round"/>
          <circle cx="460" cy="630" r="13" fill="#8a5c1e"/>
        </g>
        <g id="fan-arm-3" opacity="0">
          <path d="M442 900 L442 662 Q460 632 478 662 L478 900 Z" fill="#f5cf6e"/>
          <circle cx="460" cy="644" r="8" fill="#e88aa0"/>
          <circle cx="446" cy="654" r="8" fill="#e88aa0"/>
          <circle cx="474" cy="654" r="8" fill="#e88aa0"/>
        </g>
        <g id="rays-vis" opacity="0" stroke="#ffe9a0" stroke-width="10" stroke-linecap="round">
          {RAYS}
        </g>
        </g>
      </svg>
    </div>

    <!-- KRISHNA — one rig for the whole film -->
    <div id="krishna" class="abs clip" style="left:410px; top:1000px; width:260px; height:445px;"
         data-start="0" data-duration="{fmt(total)}" data-track-index="2">{KRI_SVG}
    </div>

    <!-- the chauki + thali that seat him at Vidura's -->
    <div id="chauki" class="abs clip" style="left:280px; top:1230px; width:400px; height:180px;"
         data-start="{fmt(S_HUT)}" data-duration="{fmt(S_SABHA - S_HUT)}" data-track-index="2">
      <svg width="400" height="180" viewBox="0 0 400 180">
        <rect x="20" y="10" width="360" height="34" rx="8" fill="#8a5c34"/>
        <rect x="30" y="40" width="340" height="132" fill="#6a4424"/>
        <path d="M30 68 L370 68 M30 100 L370 100 M30 132 L370 132" stroke="#5a3a1e" stroke-width="5"/>
        <ellipse cx="310" cy="130" rx="64" ry="18" fill="#c8b89a"/>
        <ellipse cx="310" cy="124" rx="46" ry="12" fill="#a89878"/>
        <ellipse cx="310" cy="120" rx="30" ry="9" fill="#4a7a3a"/>
        <path id="steam-0" d="M296 106 q-8 -18 4 -34 q10 -14 2 -30" stroke="#e8e2d0" stroke-width="5" fill="none" stroke-linecap="round" opacity="0"/>
        <path id="steam-1" d="M326 106 q8 -18 -4 -34 q-10 -14 -2 -30" stroke="#e8e2d0" stroke-width="5" fill="none" stroke-linecap="round" opacity="0"/>
      </svg>
    </div>

    <div id="vidura" class="abs clip" style="left:640px; top:1000px; width:240px; height:410px;"
         data-start="{fmt(S_HUT)}" data-duration="{fmt(S_SABHA - S_HUT)}" data-track-index="2">{VID_SVG}
    </div>

    <div id="dhritarashtra" class="abs clip" style="left:820px; top:920px; width:260px; height:360px;"
         data-start="{fmt(S_SABHA)}" data-duration="{fmt(S_DUSK - S_SABHA)}" data-track-index="2">{DHR_SVG}
    </div>

    <div id="duryodhan" class="abs clip" style="left:650px; top:900px; width:280px; height:450px;"
         data-start="{fmt(S_SABHA)}" data-duration="{fmt(S_DUSK - S_SABHA)}" data-track-index="2">{DUR_SVG}
    </div>

    <div id="dushasana" class="abs clip" style="left:-330px; top:910px; width:280px; height:440px;"
         data-start="{fmt(win(17)[0])}" data-duration="{fmt(S_DUSK - win(17)[0])}" data-track-index="2">{DUS_SVG}
    </div>

    <div id="guard-1" class="abs clip" style="left:1140px; top:930px; width:220px; height:425px;"
         data-start="{fmt(win(17)[0])}" data-duration="{fmt(S_DUSK - win(17)[0])}" data-track-index="2">{guard_svg(False)}
    </div>

    <div id="guard-2" class="abs clip" style="left:1180px; top:940px; width:220px; height:425px;"
         data-start="{fmt(win(17)[0])}" data-duration="{fmt(S_DUSK - win(17)[0])}" data-track-index="2">{guard_svg(True)}
    </div>

    <!-- worlds drifting inside the radiance (in front of Krishna) -->
    <div class="abs clip" style="left:0; top:0;" data-start="{fmt(win(22)[0])}" data-duration="{fmt(S_DUSK - win(22)[0])}" data-track-index="2">
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        {MOTES}
      </svg>
    </div>

    <!-- the departing silhouette -->
    <div id="chariot2" class="abs clip" style="left:-420px; top:1160px; width:380px; height:280px;"
         data-start="{fmt(S_DUSK)}" data-duration="{fmt(total - S_DUSK)}" data-track-index="1">
      <svg width="380" height="280" viewBox="0 0 380 280">
        <g fill="#1c0e14">
          <path d="M40 110 Q44 75 90 72 L165 72 Q180 88 178 136 L180 170 L38 170 Q32 136 40 110 Z"/>
          <path d="M66 74 Q62 30 90 20 L93 30 Q74 42 76 74 Z"/>
          <path d="M91 22 L148 34 L91 48 Z"/>
          <path d="M165 118 L250 104 L250 112 L166 128 Z"/>
          <path d="M250 104 Q286 116 300 148 Q286 168 258 164 Q240 136 236 116 Z"/>
          <path d="M300 148 Q314 156 310 170 Q300 176 290 168 Z"/>
          <path d="M262 166 L268 214 L258 214 L252 168 Z"/>
          <path d="M284 166 L292 214 L282 214 L274 168 Z"/>
          <circle cx="82" cy="212" r="46"/>
          <circle cx="196" cy="212" r="46"/>
        </g>
        <circle cx="82" cy="212" r="32" fill="#2c161e"/>
        <circle cx="196" cy="212" r="32" fill="#2c161e"/>
      </svg>
    </div>

    <div id="flash" class="abs" style="left:0; top:0; width:1080px; height:1920px; background:#fff7e0; opacity:0;"></div>
    <div id="scene-dip" class="abs" style="left:0; top:0; width:1080px; height:1920px; background:#000; opacity:0;"></div>

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
