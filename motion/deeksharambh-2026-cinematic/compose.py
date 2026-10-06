#!/usr/bin/env python3
"""Compose the cinematic Deeksharambh 2026 thank-you reel: 30 s, kinetic type, animated logo.

Usage: motion/deeksharambh-2026-cinematic/compose.py --project motion/deeksharambh-2026-cinematic/project
       (run prep_assets.py and make_score.py into the same project first)

The score runs at 80 BPM (beat 0.75 s, bar 3 s); every entrance sits on a beat
and every scene change on a two-bar boundary.

  A  0-6    11,000+ rolls in on an odometer out of a flare line; learners /
            chose JAIN Online.; the number fills with student faces and the
            camera flies through its zero
  B  6-12   a 3D gallery of 60 face tiles cut from the scroll recording, dolly
            forward; Every face. / A different ambition.; the camera rushes
            through the tiles into a bloom
  C  12-18  clean branded frame (navy, light ribbons, JAIN Online header):
            You chose us / for your education. / That trust / means everything.
  D  18-24  the held message: Thank you / for making us part of the /
            future you're building.
  E  24-30  the logo assembles from its own pieces: the bar draws out of a flare,
            the letters drop from it, the glyph wipes in, the swoosh writes itself
            on a conic mask, the ellipse lands with a bloom; 2026; Your ambition. /
            Our commitment.; CDOE and JAIN Online lockups

Copy is sentence case throughout and the event name only ever appears as the
logo. Renderer rules honored: full document, timed scene clips, cued fromTo
tweens use immediateRender: false, no video elements at all (the scroll
recording is used as cut-out tiles), text inside x 120-960 and y 220-1500.
"""
import argparse
import html
import json
import math
import pathlib
import random
import struct
from string import Template

ap = argparse.ArgumentParser(description="Compose the cinematic Deeksharambh 2026 reel into index.html.")
ap.add_argument("--project", required=True)
project = pathlib.Path(ap.parse_args().project).expanduser().resolve()
A = project / "assets"
for need in ("logo/logo.json", "img/mosaic.jpg", "img/grain.png", "img/jain-online.png", "img/jain-cdoe.png",
             "audio/score.wav", "fonts/Montserrat-600.ttf", "fonts/PlayfairDisplay-500i.ttf", "tiles/t000.jpg"):
    if not (A / need).is_file():
        raise SystemExit(f"missing assets/{need} — run prep_assets.py / make_score.py into {project} first")

TOTAL = 30.0
esc = html.escape


# ---------- font metrics (stdlib TTF reader: cmap format 4 + hmtx) ----------
def advances(ttf, text):
    d = (A / "fonts" / ttf).read_bytes()
    n = struct.unpack(">H", d[4:6])[0]
    tab = {}
    for i in range(n):
        tag, _, off, ln = struct.unpack(">4sIII", d[12 + 16 * i:28 + 16 * i])
        tab[tag.decode("latin-1")] = off
    upem = struct.unpack(">H", d[tab["head"] + 18:tab["head"] + 20])[0]
    nhm = struct.unpack(">H", d[tab["hhea"] + 34:tab["hhea"] + 36])[0]
    c = tab["cmap"]
    sub = None
    for i in range(struct.unpack(">H", d[c + 2:c + 4])[0]):
        pid, eid, off = struct.unpack(">HHI", d[c + 4 + 8 * i:c + 12 + 8 * i])
        if pid == 3 and eid == 1 and struct.unpack(">H", d[c + off:c + off + 2])[0] == 4:
            sub = c + off
    seg2 = struct.unpack(">H", d[sub + 6:sub + 8])[0]
    ends = sub + 14
    starts = ends + seg2 + 2
    deltas = starts + seg2
    ranges = deltas + seg2

    def gid(ch):
        cp = ord(ch)
        for s in range(seg2 // 2):
            end = struct.unpack(">H", d[ends + 2 * s:ends + 2 * s + 2])[0]
            if cp > end:
                continue
            start = struct.unpack(">H", d[starts + 2 * s:starts + 2 * s + 2])[0]
            if cp < start:
                return 0
            delta = struct.unpack(">h", d[deltas + 2 * s:deltas + 2 * s + 2])[0]
            ro = struct.unpack(">H", d[ranges + 2 * s:ranges + 2 * s + 2])[0]
            if ro == 0:
                return (cp + delta) & 0xFFFF
            g = struct.unpack(">H", d[ranges + 2 * s + ro + 2 * (cp - start):ranges + 2 * s + ro + 2 * (cp - start) + 2])[0]
            return (g + delta) & 0xFFFF if g else 0
        return 0

    out = []
    for ch in text:
        g = gid(ch)
        g = min(g, nhm - 1)
        out.append(struct.unpack(">H", d[tab["hmtx"] + 4 * g:tab["hmtx"] + 4 * g + 2])[0] / upem)
    return out


def textw(ttf, text, px, tracking=0.0):
    return sum(advances(ttf, text)) * px + tracking * px * max(0, len(text) - 1)


MAX_LINE = 820.0  # inside the 840 px line box, leaving room for italic overhang
THANK_PX = min(190.0, MAX_LINE / (textw("PlayfairDisplay-500i.ttf", "Thank you", 1.0)))
SP = lambda ttf, px: textw(ttf, " ", px)
LINES = {
    "learners": textw("Montserrat-300.ttf", "learners", 68, 0.16),
    "chose JAIN Online.": textw("PlayfairDisplay-500i.ttf", "chose", 82) + SP("Montserrat-600.ttf", 64)
                          + textw("Montserrat-600.ttf", "JAIN Online.", 64),
    "Every face.": textw("Montserrat-500.ttf", "Every face.", 100),
    "A different": textw("Montserrat-300.ttf", "A different", 64),
    "ambition.": textw("PlayfairDisplay-600i.ttf", "ambition.", 128),
    "You chose us": textw("Montserrat-500.ttf", "You chose us", 70),
    "for your education.": textw("Montserrat-500.ttf", "for your education.", 70),
    "That trust": textw("PlayfairDisplay-500i.ttf", "That trust", 150),
    "means everything.": textw("Montserrat-500.ttf", "means everything.", 70),
    "Thank you": textw("PlayfairDisplay-500i.ttf", "Thank you", THANK_PX),
    "for making us part of the": textw("Montserrat-400.ttf", "for making us part of the", 54),
    "future you're building.": textw("PlayfairDisplay-600i.ttf", "future", 76) + SP("Montserrat-400.ttf", 54)
                               + textw("Montserrat-400.ttf", "you\u2019re building.", 54),
    "Your ambition.": textw("Montserrat-400.ttf", "Your ", 60) + textw("PlayfairDisplay-500i.ttf", "ambition.", 70),
    "Our commitment.": textw("Montserrat-400.ttf", "Our ", 60) + textw("PlayfairDisplay-500i.ttf", "commitment.", 70),
}
too_wide = {k: round(v) for k, v in LINES.items() if v > MAX_LINE}
if too_wide:
    raise SystemExit(f"lines wider than {MAX_LINE:.0f} px: {too_wide}")


# ---------- A: the number ----------
NUM = "11,000+"
adv = advances("Montserrat-600.ttf", NUM)
NUM_PX = min(220.0, 860.0 / sum(adv))
widths = [a * NUM_PX for a in adv]
NUM_W = sum(widths)
NUM_LEFT = 525 - NUM_W / 2
NUM_TOP = 640
offs = [sum(widths[:i]) for i in range(len(widths))]
ROLLS = {0: 11, 1: 14, 3: 17, 4: 20, 5: 23}  # slot -> digits travelled


def num_layer(kind):
    spans = []
    for i, ch in enumerate(NUM):
        w, x = widths[i], offs[i]
        style = f"left:{x:.2f}px; width:{w:.2f}px;"
        if kind == "roll" and i in ROLLS:
            k = ROLLS[i]
            d = int(ch)
            digits = "".join(f'<div class="dg">{(d - k + j) % 10}</div>' for j in range(k + 1))
            spans.append(f'<div class="slot" style="{style}"><div class="win"><div class="strip" id="strip{i}">{digits}</div></div></div>')
        elif kind == "roll":
            cls = "plus" if ch == "+" else "comma"
            spans.append(f'<div class="slot" style="{style}"><div class="dg {cls}" id="sym{i}">{esc(ch)}</div></div>')
        else:
            bp = {"glint": f"background-position: calc(var(--gx) - {x:.2f}px) 0;",
                  "mos": f"background-position: {-x:.2f}px {-(NUM_W * 0.6 - NUM_PX) / 2:.2f}px;"}.get(kind, "")
            extra = " plus" if ch == "+" else ""
            spans.append(f'<div class="slot" style="{style}"><div class="dg{extra}" style="{bp}">{esc(ch)}</div></div>')
    return "".join(spans)


# ---------- B: the 3D gallery ----------
P = 1100.0
rng = random.Random(2026)
tiles = []
n_tiles = 72
tile_ids = list(range(240))
rng.shuffle(tile_ids)
for k in range(n_tiles):
    z0 = -3400 + 3200 * (k + rng.random()) / n_tiles
    th = rng.uniform(0, 2 * math.pi)
    rp = rng.uniform(310, 620)
    f = (P - z0) / P
    x, y = rp * math.cos(th) * f, rp * math.sin(th) * 1.55 * f
    ry, rx = rng.uniform(-14, 14), rng.uniform(-10, 10)
    zmid = z0 + 450
    blur = min(5.0, abs(zmid - (-700)) / 500 * 2.2)
    light = 0.5 + 0.5 * min(1.0, max(0.0, (z0 + 3400) / 3000))
    tiles.append((k, tile_ids[k], x, y, z0, ry, rx, blur, light))
# highlight a handful of mid-depth tiles on "A different ambition."
mid = sorted((t for t in tiles if -1700 < t[4] < -700), key=lambda t: t[4])
HIGHLIGHT = [t[0] for t in mid[::max(1, len(mid) // 7)]][:7]

tile_html = "\n".join(
    f'<img class="tile" id="tile{k}" src="assets/tiles/t{tid:03d}.jpg" alt="" '
    f'style="transform: translate3d({x - 100:.1f}px, {y - 100:.1f}px, {z:.1f}px) rotateY({ry:.1f}deg) rotateX({rx:.1f}deg); '
    f'filter: blur({b:.2f}px) brightness({lt:.2f});">'
    for k, tid, x, y, z, ry, rx, b, lt in tiles
)

# ---------- E: the logo ----------
logo = json.loads((A / "logo" / "logo.json").read_text())
LW, LH = logo["size"]
LOGO_W = 840.0
LS = LOGO_W / LW
LOGO_L, LOGO_T = 120.0, 530.0
pieces = {p["name"]: p for p in logo["pieces"]}
sw = logo["swoosh"]
SW_FROM = sw["start"] + 4
SW_EXTENT = SW_FROM - (sw["end"] - 4)
swp = pieces["swoosh"]
SW_CX = (sw["center"][0] - swp["x"]) * LS
SW_CY = (sw["center"][1] - swp["y"]) * LS
BAR_Y = LOGO_T + (sum(logo["bar_rows"]) / 2) * LS
BAR_X0, BAR_X1 = LOGO_L + pieces["bar"]["x"] * LS, LOGO_L + (pieces["bar"]["x"] + pieces["bar"]["w"]) * LS


def piece(nm, extra_cls=""):
    p = pieces[nm]
    return (f'<img class="lp {extra_cls}" id="lp-{nm}" src="assets/logo/{nm}.png" alt="" '
            f'style="left:{LOGO_L + p["x"] * LS:.2f}px; top:{LOGO_T + p["y"] * LS:.2f}px; '
            f'width:{p["w"] * LS:.2f}px; height:{p["h"] * LS:.2f}px;">')


ell = pieces["ellipse"]
ELL_CX = LOGO_L + (ell["x"] + ell["w"] / 2) * LS
ELL_CY = LOGO_T + (ell["y"] + ell["h"] / 2) * LS
letters = sorted((p for p in logo["pieces"] if p["group"] == "letters"), key=lambda p: p["order"])
words = sorted((p for p in logo["pieces"] if p["group"] == "subtitle"), key=lambda p: p["order"])

# ---------- shared bits ----------
rngp = random.Random(7)
dust = []
for i in range(54):
    x, y = rngp.uniform(0, 1080), rngp.uniform(0, 2400)
    s = rngp.choice([1.5, 2, 2, 2.5, 3, 4])
    dust.append(f'<div class="dust" data-rise="{rngp.uniform(300, 900):.0f}" data-sway="{rngp.uniform(-60, 60):.0f}" '
                f'style="left:{x:.0f}px; top:{y:.0f}px; width:{s}px; height:{s}px; opacity:{rngp.uniform(0.15, 0.6):.2f};"></div>')
bokeh = []
for i in range(12):
    x, y = rngp.uniform(-100, 1100), rngp.uniform(100, 1900)
    s = rngp.uniform(60, 220)
    bokeh.append(f'<div class="bokeh" data-drift="{rngp.uniform(-120, 120):.0f}" '
                 f'style="left:{x:.0f}px; top:{y:.0f}px; width:{s:.0f}px; height:{s:.0f}px; opacity:{rngp.uniform(0.05, 0.14):.2f};"></div>')


def words_html(text, cls="w"):
    return " ".join(f'<span class="mw"><span class="{cls}">{esc(w)}</span></span>' for w in text.split())


FONTS = "\n".join(
    f"@font-face {{ font-family: '{fam}'; font-weight: {w}; font-style: {st}; src: url('assets/fonts/{file}.ttf'); }}"
    for fam, w, st, file in [
        ("Montserrat", 300, "normal", "Montserrat-300"), ("Montserrat", 400, "normal", "Montserrat-400"),
        ("Montserrat", 500, "normal", "Montserrat-500"), ("Montserrat", 600, "normal", "Montserrat-600"),
        ("Montserrat", 700, "normal", "Montserrat-700"),
        ("Playfair Display", 400, "italic", "PlayfairDisplay-400i"),
        ("Playfair Display", 500, "italic", "PlayfairDisplay-500i"),
        ("Playfair Display", 600, "italic", "PlayfairDisplay-600i"),
    ]
)

CSS = Template(r"""
$FONTS
:root { --teal: #2fe0c6; --mist: #cfe0ff; }
#stage { position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #01030c;
  font-family: 'Montserrat', sans-serif; color: #fff; }
.full { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; }
.scene { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; overflow: hidden; }
.line { position: absolute; left: 120px; width: 840px; text-align: center; line-height: 1.12; white-space: nowrap; }
.mw { display: inline-block; overflow: hidden; vertical-align: bottom; padding: 0 0.14em 0.16em; margin: 0 -0.14em -0.16em; }
.w { display: inline-block; }
.serif { font-family: 'Playfair Display', serif; font-style: italic; }
.tealfill { background: linear-gradient(180deg, #d9fff8 0%, #2fe0c6 100%); -webkit-background-clip: text;
  background-clip: text; color: transparent; }
.whitefill { background: linear-gradient(180deg, #ffffff 0%, #c9d8ff 100%); -webkit-background-clip: text;
  background-clip: text; color: transparent; }

/* background */
#bg-base { background: linear-gradient(180deg, #01030c 0%, #030a24 46%, #061648 100%); }
.pool { position: absolute; border-radius: 50%; }
#pool1 { width: 1500px; height: 1500px; left: -210px; top: -700px;
  background: radial-gradient(circle, rgba(36,84,230,0.42) 0%, rgba(36,84,230,0) 62%); }
#pool2 { width: 1300px; height: 1300px; left: -600px; top: 1100px;
  background: radial-gradient(circle, rgba(47,224,198,0.16) 0%, rgba(47,224,198,0) 62%); }
#pool3 { width: 1200px; height: 1200px; left: 420px; top: 500px;
  background: radial-gradient(circle, rgba(92,80,255,0.16) 0%, rgba(92,80,255,0) 62%); }
.dust { position: absolute; border-radius: 50%; background: #dfe9ff; box-shadow: 0 0 6px rgba(160,200,255,0.9); }
.bokeh { position: absolute; border-radius: 50%; filter: blur(6px);
  background: radial-gradient(circle, rgba(130,175,255,0.9) 0%, rgba(130,175,255,0.25) 55%, rgba(130,175,255,0) 72%); }

/* flares */
.flare { position: absolute; left: 0; width: 1080px; height: 0; }
.flare .core { position: absolute; left: 90px; width: 900px; top: -1.5px; height: 3px; border-radius: 2px;
  background: linear-gradient(90deg, rgba(255,255,255,0), #ffffff 30%, #ffffff 70%, rgba(255,255,255,0));
  box-shadow: 0 0 18px 4px rgba(150,220,255,0.85); }
.flare .halo { position: absolute; left: -100px; width: 1280px; top: -22px; height: 44px; filter: blur(10px);
  background: linear-gradient(90deg, rgba(47,224,198,0), rgba(47,224,198,0.55) 40%, rgba(120,170,255,0.55) 60%, rgba(47,224,198,0)); }
.flare .streak { position: absolute; left: -200px; width: 1480px; top: -90px; height: 180px; filter: blur(30px);
  background: radial-gradient(ellipse at 50% 50%, rgba(90,150,255,0.35) 0%, rgba(90,150,255,0) 70%); }

/* A */
#a-num { position: absolute; left: 0; top: 0; width: ${NUM_W}px; height: ${NUM_H}px;
  font-weight: 600; font-size: ${NUM_PX}px; line-height: 1; clip-path: inset(43% -10% 43% -10%); }
.nl { position: absolute; left: 0; top: 0; width: ${NUM_W}px; height: ${NUM_H}px; }
.slot { position: absolute; top: 0; height: ${NUM_H}px; }
.win { position: absolute; left: -30%; right: -30%; top: 0; height: ${NUM_H}px; overflow: hidden; }
.strip { position: absolute; left: 0; right: 0; top: 0; }
.dg { height: ${NUM_H}px; line-height: ${NUM_H}px; text-align: center; white-space: nowrap;
  background: linear-gradient(180deg, #ffffff 15%, #c4d5ff 90%); -webkit-background-clip: text; background-clip: text;
  color: transparent; }
.dg.plus { background: linear-gradient(180deg, #d9fff8 10%, #2fe0c6 90%); -webkit-background-clip: text; background-clip: text; }
#a-fin, #a-glint, #a-mos { opacity: 0; }
#a-glint .dg { background: linear-gradient(100deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0) 44%,
  rgba(255,255,255,0.95) 50%, rgba(255,255,255,0) 56%, rgba(255,255,255,0) 100%);
  background-size: ${NUM_W}px 100%; background-repeat: no-repeat; -webkit-background-clip: text; background-clip: text; }
#a-mos .dg { background-image: url('assets/img/mosaic.jpg'); background-size: ${NUM_W}px ${MOS_H}px;
  -webkit-background-clip: text; background-clip: text; }
#a-numglow { position: absolute; left: ${NUM_LEFT}px; top: ${NUM_TOP}px; width: ${NUM_W}px; height: ${NUM_H}px;
  filter: drop-shadow(0 0 40px rgba(80,140,255,0.45)); }
#a-learners { top: 885px; font-size: 68px; font-weight: 300; letter-spacing: 0.16em; }
#a-chose { top: 985px; font-size: 64px; font-weight: 600; }
#a-chose .serif { font-size: 82px; font-weight: 500; }
#a-zoom { transform-origin: ${ZOOM_X}px ${ZOOM_Y}px; }

/* B */
#b-cam { perspective: ${P}px; perspective-origin: 540px 880px; opacity: 0; }
#b-world { position: absolute; left: 540px; top: 880px; width: 0; height: 0; transform-style: preserve-3d; }
.tile { position: absolute; left: 0; top: 0; width: 200px; height: 200px; border-radius: 20px;
  box-shadow: 0 0 0 1px rgba(200,220,255,0.16), 0 20px 60px rgba(0,0,12,0.65); backface-visibility: hidden; }
#b-shade { background: radial-gradient(ellipse 560px 420px at 540px 905px, rgba(1,3,14,0.82) 0%, rgba(1,3,14,0.55) 55%, rgba(1,3,14,0) 100%); }
#b-every { top: 760px; font-size: 100px; font-weight: 500; letter-spacing: -0.01em; }
#b-diff { top: 905px; font-size: 64px; font-weight: 300; letter-spacing: 0.02em; }
#b-amb { top: 965px; font-size: 128px; font-weight: 600; line-height: 1.2; }
#b-bloom { position: absolute; left: 40px; top: 380px; width: 1000px; height: 1000px; border-radius: 50%; opacity: 0;
  background: radial-gradient(circle, rgba(235,250,255,1) 0%, rgba(140,230,220,0.8) 28%, rgba(60,120,255,0.35) 55%, rgba(60,120,255,0) 72%); }

/* C + D shared background */
#cd-base { background: linear-gradient(180deg, #020a2a 0%, #05155a 55%, #0a2690 100%); }
#cd-glow { background: radial-gradient(ellipse 900px 700px at 540px 640px, rgba(70,120,255,0.28) 0%, rgba(70,120,255,0) 70%); }
#cd-ribbons path { fill: none; }
#cd-head { position: absolute; left: 375px; top: 250px; width: 330px; opacity: 0; }
#c-you, #c-for, #c-means { font-size: 70px; font-weight: 500; }
#c-you { top: 640px; }
#c-for { top: 728px; }
#c-rule { position: absolute; left: 480px; top: 862px; width: 120px; height: 2px; transform: scaleX(0);
  background: linear-gradient(90deg, rgba(47,224,198,0), #2fe0c6, rgba(47,224,198,0)); }
#c-trust { top: 885px; font-size: 150px; font-weight: 500; line-height: 1.2; }
#c-means { top: 1080px; }
#c-sweep { background: linear-gradient(105deg, rgba(255,255,255,0) 38%, rgba(200,225,255,0.22) 50%, rgba(255,255,255,0) 62%);
  background-size: 300% 100%; background-position: 120% 0; mix-blend-mode: screen; }
#d-rays { position: absolute; left: -260px; top: -1000px; width: 1600px; height: 1600px; opacity: 0;
  background: repeating-conic-gradient(from 0deg at 50% 50%, rgba(170,205,255,0.085) 0deg 3deg, rgba(170,205,255,0) 3deg 11deg);
  -webkit-mask-image: radial-gradient(circle at 50% 50%, #000 0%, rgba(0,0,0,0.6) 45%, transparent 70%);
  mask-image: radial-gradient(circle at 50% 50%, #000 0%, rgba(0,0,0,0.6) 45%, transparent 70%); }
#d-thank { top: 630px; font-size: ${THANK_PX}px; font-weight: 500; line-height: 1.2;
  -webkit-mask-image: linear-gradient(90deg, #000 calc(var(--tw) - 14%), transparent var(--tw));
  mask-image: linear-gradient(90deg, #000 calc(var(--tw) - 14%), transparent var(--tw)); --tw: -2%; }
#d-making, #d-future { font-size: 54px; font-weight: 400; letter-spacing: 0.01em; }
#d-making { top: 880px; }
#d-future { top: 950px; }
#d-future .serif { font-size: 76px; font-weight: 600; }

/* E */
#e-spot { background: radial-gradient(ellipse 760px 620px at 540px 690px, rgba(44,96,255,0.36) 0%, rgba(20,50,170,0.16) 45%, rgba(0,0,0,0) 75%); opacity: 0; }
.lp { position: absolute; }
#lp-bar { clip-path: inset(0% 50% 0% 50%); }
#lp-glyph { --gw: -14%; -webkit-mask-image: linear-gradient(115deg, #000 calc(var(--gw) - 14%), transparent var(--gw));
  mask-image: linear-gradient(115deg, #000 calc(var(--gw) - 14%), transparent var(--gw)); }
#lp-swoosh, #lp-swoosh-glow { --sw: -8deg;
  -webkit-mask-image: conic-gradient(from ${SW_FROM}deg at ${SW_CX}px ${SW_CY}px, transparent 0deg,
    transparent calc(360deg - var(--sw) - 7deg), #000 calc(360deg - var(--sw)));
  mask-image: conic-gradient(from ${SW_FROM}deg at ${SW_CX}px ${SW_CY}px, transparent 0deg,
    transparent calc(360deg - var(--sw) - 7deg), #000 calc(360deg - var(--sw))); }
#lp-swoosh-glow { filter: blur(10px) brightness(1.6); opacity: 0.0; }
#e-bloom { position: absolute; left: ${BLOOM_L}px; top: ${BLOOM_T}px; width: 300px; height: 300px; border-radius: 50%;
  background: radial-gradient(circle, rgba(200,255,245,0.95) 0%, rgba(47,224,198,0.55) 35%, rgba(47,224,198,0) 70%); opacity: 0; }
#e-glint { position: absolute; left: ${LOGO_L}px; top: ${LOGO_T}px; width: ${LOGO_W}px; height: ${LOGO_H}px;
  -webkit-mask-image: url('assets/img/deeksharambh.png'); -webkit-mask-size: ${LOGO_W}px ${LOGO_H}px;
  mask-image: url('assets/img/deeksharambh.png'); mask-size: ${LOGO_W}px ${LOGO_H}px;
  background: linear-gradient(105deg, rgba(255,255,255,0) 42%, rgba(255,255,255,0.9) 50%, rgba(255,255,255,0) 58%);
  background-size: 300% 100%; background-position: 120% 0; }
#e-year { top: 880px; font-size: 56px; font-weight: 300; letter-spacing: 0.55em; padding-left: 0.55em; }
.hair { position: absolute; top: 912px; width: 130px; height: 1.5px; }
#e-hl { left: 245px; background: linear-gradient(90deg, rgba(207,224,255,0), rgba(207,224,255,0.85)); transform-origin: 100% 50%; transform: scaleX(0); }
#e-hr { left: 705px; background: linear-gradient(90deg, rgba(207,224,255,0.85), rgba(207,224,255,0)); transform-origin: 0% 50%; transform: scaleX(0); }
#e-amb, #e-com { font-size: 60px; font-weight: 400; }
#e-amb { top: 1015px; }
#e-com { top: 1095px; }
#e-amb .serif, #e-com .serif { font-size: 70px; font-weight: 500; }
#e-cdoe { position: absolute; left: 118px; top: 252px; width: 380px; opacity: 0; }
#e-jo { position: absolute; left: 600px; top: 252px; width: 330px; opacity: 0; }
#e-sep { position: absolute; left: 548px; top: 250px; width: 1.5px; height: 70px; opacity: 0;
  background: linear-gradient(180deg, rgba(207,224,255,0), rgba(207,224,255,0.7), rgba(207,224,255,0)); }

/* overlays */
#vignette { background: radial-gradient(ellipse at 50% 46%, rgba(0,0,0,0) 56%, rgba(0,0,8,0.62) 100%); }
#grain { background-image: url('assets/img/grain.png'); background-size: 256px 256px; mix-blend-mode: overlay; opacity: 0.09; }

/* cued elements start hidden */
#a-learners, #a-chose .w, #b-every .w, #b-diff .w, #b-amb, #c-you .w, #c-for .w, #c-trust, #c-means .w,
#d-making .w, #d-future .w, #e-year, #e-amb .w, #e-com .w, .lp-l, .lp-w, #lp-ellipse, #sym2, #sym6 { opacity: 0; }
""")

page_css = CSS.substitute(
    FONTS=FONTS, NUM_LEFT=f"{NUM_LEFT:.2f}", NUM_TOP=f"{NUM_TOP}", NUM_W=f"{NUM_W:.2f}", NUM_H=f"{NUM_PX:.2f}",
    NUM_PX=f"{NUM_PX:.2f}", MOS_H=f"{NUM_W * 0.6:.2f}", ZOOM_X=f"{NUM_LEFT + offs[4] + widths[4] / 2:.2f}",
    ZOOM_Y=f"{NUM_TOP + NUM_PX * 0.52:.2f}", P=f"{P:.0f}", SW_FROM=f"{SW_FROM:.2f}", SW_CX=f"{SW_CX:.2f}",
    SW_CY=f"{SW_CY:.2f}", BLOOM_L=f"{ELL_CX - 150:.2f}", BLOOM_T=f"{ELL_CY - 150:.2f}", LOGO_L=f"{LOGO_L:.0f}",
    LOGO_T=f"{LOGO_T:.0f}", LOGO_H=f"{LH * LS:.2f}", LOGO_W=f"{LOGO_W:.0f}", THANK_PX=f"{THANK_PX:.1f}",
)

ribbons = """
<svg class="full" width="1080" height="1920" viewBox="0 0 1080 1920" id="cd-ribbons">
  <defs>
    <linearGradient id="rg1" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#3b7bff" stop-opacity="0"/><stop offset="0.45" stop-color="#8fb8ff" stop-opacity="0.95"/>
      <stop offset="0.75" stop-color="#2fe0c6" stop-opacity="0.8"/><stop offset="1" stop-color="#2fe0c6" stop-opacity="0"/>
    </linearGradient>
    <filter id="rglow" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="16"/></filter>
  </defs>
  <g id="rib-low">
    <path class="rb" d="M-240 1660 C 160 1540, 620 1500, 1320 1140" stroke="url(#rg1)" stroke-width="60" opacity="0.32" filter="url(#rglow)" pathLength="1000" stroke-dasharray="1000" stroke-dashoffset="1000"/>
    <path class="rb" d="M-240 1660 C 160 1540, 620 1500, 1320 1140" stroke="url(#rg1)" stroke-width="2.5" pathLength="1000" stroke-dasharray="1000" stroke-dashoffset="1000"/>
    <path class="rb" d="M-240 1760 C 220 1620, 700 1600, 1320 1290" stroke="url(#rg1)" stroke-width="1.5" opacity="0.7" pathLength="1000" stroke-dasharray="1000" stroke-dashoffset="1000"/>
    <path class="rb" d="M-240 1840 C 300 1700, 760 1700, 1320 1430" stroke="url(#rg1)" stroke-width="1" opacity="0.45" pathLength="1000" stroke-dasharray="1000" stroke-dashoffset="1000"/>
  </g>
  <g id="rib-high">
    <path class="rb" d="M-240 420 C 260 330, 720 190, 1320 -40" stroke="url(#rg1)" stroke-width="1.5" opacity="0.5" pathLength="1000" stroke-dasharray="1000" stroke-dashoffset="1000"/>
    <path class="rb" d="M-240 420 C 260 330, 720 190, 1320 -40" stroke="url(#rg1)" stroke-width="44" opacity="0.16" filter="url(#rglow)" pathLength="1000" stroke-dasharray="1000" stroke-dashoffset="1000"/>
  </g>
</svg>"""


def flare(fid, y, cx=540.0):
    return (f'<div class="flare" id="{fid}" style="top:{y:.1f}px; left:{cx - 540:.1f}px;">'
            f'<div class="streak"></div><div class="halo"></div><div class="core"></div></div>')


body = f"""
  <!-- track 0: living background -->
  <div id="bg" class="clip full" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="0">
    <div id="bg-base" class="full"></div>
    <div id="pool1" class="pool"></div><div id="pool2" class="pool"></div><div id="pool3" class="pool"></div>
    {''.join(bokeh)}
    {''.join(dust)}
  </div>

  <!-- A: 11,000+ learners chose JAIN Online. -->
  <div id="sA" class="clip scene" data-start="0" data-duration="6.150" data-track-index="1">
    <div id="a-zoom" class="full">
      {flare("a-flare", NUM_TOP + NUM_PX * 0.5)}
      <div id="a-numglow"><div id="a-num">
        <div class="nl" id="a-roll">{num_layer("roll")}</div>
        <div class="nl" id="a-fin">{num_layer("fin")}</div>
        <div class="nl" id="a-mos">{num_layer("mos")}</div>
        <div class="nl" id="a-glint">{num_layer("glint")}</div>
      </div></div>
      <div id="a-learners" class="line">learners</div>
      <div id="a-chose" class="line"><span class="mw"><span class="w serif tealfill">chose</span></span> {words_html("JAIN Online.")}</div>
    </div>
  </div>

  <!-- B: Every face. A different ambition. -->
  <div id="sB" class="clip scene" data-start="5.500" data-duration="7.000" data-track-index="2">
    <div id="b-cam" class="full"><div id="b-world">
{tile_html}
    </div></div>
    <div id="b-shade" class="full"></div>
    <div id="b-every" class="line">{words_html("Every face.")}</div>
    <div id="b-diff" class="line">{words_html("A different")}</div>
    <div id="b-amb" class="line serif tealfill">ambition.</div>
    <div id="b-bloom"></div>
  </div>

  <!-- C + D background: the clean branded frame -->
  <div id="cd" class="clip full" data-start="11.900" data-duration="12.400" data-track-index="1">
    <div id="cd-base" class="full"></div>
    <div id="cd-glow" class="full"></div>
    {ribbons}
    <div id="d-rays"></div>
    <img id="cd-head" src="assets/img/jain-online.png" alt="">
  </div>

  <!-- C: You chose us for your education. That trust means everything. -->
  <div id="sC" class="clip scene" data-start="11.900" data-duration="6.400" data-track-index="3">
    <div id="c-you" class="line">{words_html("You chose us")}</div>
    <div id="c-for" class="line">{words_html("for your education.")}</div>
    <div id="c-rule"></div>
    <div id="c-trust" class="line serif whitefill">That trust</div>
    <div id="c-means" class="line">{words_html("means everything.")}</div>
    <div id="c-sweep" class="full"></div>
  </div>

  <!-- D: Thank you for making us part of the future you're building. -->
  <div id="sD" class="clip scene" data-start="17.900" data-duration="6.300" data-track-index="2">
    <div id="d-hold" class="full">
      <div id="d-thank" class="line serif whitefill">Thank you</div>
      <div id="d-making" class="line">{words_html("for making us part of the")}</div>
      <div id="d-future" class="line"><span class="mw"><span class="w serif tealfill">future</span></span> {words_html("you’re building.")}</div>
    </div>
  </div>

  <!-- E: the logo builds itself; 2026; Your ambition. Our commitment. -->
  <div id="sE" class="clip scene" data-start="23.500" data-duration="{TOTAL - 23.5:.3f}" data-track-index="3">
    <div id="e-spot" class="full"></div>
    <div id="e-hold" class="full">
      {flare("e-flare", BAR_Y, (BAR_X0 + BAR_X1) / 2)}
      {piece("bar")}
      {''.join(piece(p["name"], "lp-l") for p in letters)}
      {piece("glyph")}
      <img class="lp" id="lp-swoosh-glow" src="assets/logo/swoosh.png" alt="" style="left:{LOGO_L + swp['x'] * LS:.2f}px; top:{LOGO_T + swp['y'] * LS:.2f}px; width:{swp['w'] * LS:.2f}px; height:{swp['h'] * LS:.2f}px;">
      {piece("swoosh")}
      <div id="e-bloom"></div>
      {piece("ellipse")}
      {''.join(piece(p["name"], "lp-w") for p in words)}
      <div id="e-glint"></div>
      <div class="hair" id="e-hl"></div><div class="hair" id="e-hr"></div>
      <div id="e-year" class="line">2026</div>
      <div id="e-amb" class="line">{words_html("Your")} <span class="mw"><span class="w serif tealfill">ambition.</span></span></div>
      <div id="e-com" class="line">{words_html("Our")} <span class="mw"><span class="w serif tealfill">commitment.</span></span></div>
    </div>
    <img id="e-cdoe" src="assets/img/jain-cdoe.png" alt="">
    <div id="e-sep"></div>
    <img id="e-jo" src="assets/img/jain-online.png" alt="">
  </div>

  <!-- track 4: lens + film -->
  <div id="vignette" class="clip full" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="4"></div>
  <div id="grain" class="clip full" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="6"></div>

  <audio id="score" class="clip" src="assets/audio/score.wav" data-start="0" data-duration="{TOTAL:.3f}"
         data-track-index="5" data-volume="1"></audio>
"""

JS = Template(r"""
const TOTAL = $TOTAL;
const tl = gsap.timeline({ paused: true });
const qa = (s) => Array.from(document.querySelectorAll(s));
const IR = { immediateRender: false };
const cue = (t, target, from, to) => tl.fromTo(target, from, Object.assign({}, IR, to), t);
// premium reveal: word rises out of its own mask with a focus pull
const rise = (t, target, stagger, dur) => cue(t, target,
  { yPercent: 110, opacity: 0, filter: "blur(8px)" },
  { yPercent: 0, opacity: 1, filter: "blur(0px)", duration: dur || 1.0, ease: "expo.out", stagger: stagger || 0.09 });
const drift = (t, target, stagger) => tl.to(target,
  { y: -36, opacity: 0, filter: "blur(10px)", duration: 0.6, ease: "power2.in", stagger: stagger || 0.04 }, t);

// ---------- background: never still ----------
tl.fromTo("#pool1", { x: -60, y: 0 }, { x: 160, y: 260, duration: TOTAL, ease: "sine.inOut" }, 0);
tl.fromTo("#pool2", { x: 0, y: 0 }, { x: 420, y: -380, duration: TOTAL, ease: "sine.inOut" }, 0);
tl.fromTo("#pool3", { x: 0, y: 0 }, { x: -360, y: 240, duration: TOTAL, ease: "sine.inOut" }, 0);
qa(".dust").forEach((el) => tl.fromTo(el, { y: 0, x: 0 },
  { y: -Number(el.dataset.rise), x: Number(el.dataset.sway), duration: TOTAL, ease: "none" }, 0));
qa(".bokeh").forEach((el) => tl.fromTo(el, { x: 0 }, { x: Number(el.dataset.drift), duration: TOTAL, ease: "sine.inOut" }, 0));
tl.fromTo("#grain", { backgroundPosition: "0px 0px" },
  { backgroundPosition: "49320px 32040px", duration: TOTAL, ease: "steps(360)" }, 0);

// ---------- A (0-6) ----------
tl.fromTo("#a-flare", { scaleX: 0.25, opacity: 1 }, { scaleX: 1, duration: 0.55, ease: "expo.out" }, 0);
tl.to("#a-flare", { opacity: 0, scaleY: 0.4, duration: 0.9, ease: "power2.out" }, 0.55);
tl.fromTo("#a-num", { clipPath: "inset(43% -10% 43% -10%)" },
  { clipPath: "inset(-12% -10% -12% -10%)", duration: 0.9, ease: "expo.out" }, 0.05);
const ROLLS = $ROLLS;
Object.keys(ROLLS).forEach((i, n) => {
  const k = ROLLS[i];
  const dur = 1.25 + n * 0.16;
  tl.fromTo("#strip" + i, { y: 0, filter: "blur(5px)" },
    { y: -k * $NUM_H, filter: "blur(0px)", duration: dur, ease: "power4.out" }, 0.0);
});
cue(0.9, "#sym2", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" });
cue(1.5, "#sym6", { opacity: 0, scale: 0.4, rotation: -90 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.7, ease: "expo.out" });
tl.set("#a-fin", { opacity: 1 }, 2.1);
tl.set("#a-roll", { opacity: 0 }, 2.1);
cue(1.5, "#a-learners", { opacity: 0, letterSpacing: "0.5em", filter: "blur(10px)" },
  { opacity: 1, letterSpacing: "0.16em", filter: "blur(0px)", duration: 1.3, ease: "power3.out" });
rise(2.25, "#a-chose .w", 0.12, 1.1);
tl.fromTo("#a-zoom", { scale: 1 }, { scale: 1.035, duration: 5.0, ease: "none" }, 0);
tl.set("#a-glint", { opacity: 1 }, 3.0);
tl.fromTo("#a-glint", { "--gx": "-1400px" }, { "--gx": "$GLINT_END" + "px", duration: 1.1, ease: "power2.inOut" }, 3.0);
cue(4.4, "#a-mos", { opacity: 0 }, { opacity: 1, duration: 0.7, ease: "power2.inOut" });
drift(4.5, ["#a-learners", "#a-chose"], 0.08);
tl.fromTo("#a-zoom", { scale: 1.035, filter: "blur(0px)" },
  { immediateRender: false, scale: 11, filter: "blur(6px)", duration: 1.0, ease: "power3.in" }, 5.0);
tl.fromTo("#a-zoom", { opacity: 1 }, { immediateRender: false, opacity: 0, duration: 0.25, ease: "none" }, 5.85);
tl.set("#a-zoom", { opacity: 0 }, 6.1);

// ---------- B (6-12) ----------
cue(5.55, "#b-cam", { opacity: 0 }, { opacity: 1, duration: 0.7, ease: "power2.out" });
tl.fromTo("#b-world", { z: -260, rotationZ: -5 }, { z: 900, rotationZ: 4, duration: 5.75, ease: "power1.inOut" }, 5.55);
tl.fromTo("#b-world", { z: 900 }, { immediateRender: false, z: 4300, duration: 1.05, ease: "power3.in" }, 11.3);
rise(6.75, "#b-every .w", 0.14, 1.1);
rise(8.25, "#b-diff .w", 0.12, 1.0);
cue(8.6, "#b-amb", { opacity: 0, letterSpacing: "0.12em", filter: "blur(14px) drop-shadow(0px 0px 0px rgba(47,224,198,0))", scale: 1.06 },
  { opacity: 1, letterSpacing: "0em", filter: "blur(0px) drop-shadow(0px 0px 26px rgba(47,224,198,0.45))", scale: 1, duration: 1.3, ease: "power3.out" });
$HIGHLIGHTS
drift(10.9, ["#b-every", "#b-diff", "#b-amb"], 0.07);
cue(11.55, "#b-bloom", { opacity: 0, scale: 0.15 }, { opacity: 1, scale: 2.6, duration: 0.6, ease: "power2.in" });
tl.fromTo("#b-bloom", { opacity: 1 }, { immediateRender: false, opacity: 0, duration: 0.3, ease: "none" }, 12.15);

// ---------- C (12-18): clean branded frame ----------
cue(11.9, "#cd", { opacity: 0 }, { opacity: 1, duration: 0.5, ease: "power1.out" });
tl.fromTo("#rib-low .rb", { attr: { "stroke-dashoffset": 1000 } },
  { attr: { "stroke-dashoffset": 0 }, duration: 1.8, ease: "power2.inOut", stagger: 0.12 }, 12.15);
tl.fromTo("#rib-high .rb", { attr: { "stroke-dashoffset": 1000 } },
  { attr: { "stroke-dashoffset": 0 }, duration: 1.8, ease: "power2.inOut", stagger: 0.12 }, 12.6);
tl.fromTo("#cd-ribbons", { x: -30, y: 10 }, { x: 40, y: -20, duration: 12.4, ease: "sine.inOut" }, 11.9);
cue(12.6, "#cd-head", { opacity: 0, y: -14 }, { opacity: 0.92, y: 0, duration: 1.0, ease: "power3.out" });
rise(12.75, "#c-you .w", 0.1, 1.0);
rise(13.5, "#c-for .w", 0.1, 1.0);
cue(14.4, "#c-rule", { scaleX: 0 }, { scaleX: 1, duration: 0.8, ease: "power3.inOut" });
cue(15.0, "#c-trust", { opacity: 0, letterSpacing: "0.22em", filter: "blur(16px) drop-shadow(0px 0px 0px rgba(140,180,255,0))", scale: 1.05 },
  { opacity: 1, letterSpacing: "0em", filter: "blur(0px) drop-shadow(0px 0px 30px rgba(140,180,255,0.45))", scale: 1, duration: 1.4, ease: "power3.out" });
rise(15.75, "#c-means .w", 0.12, 1.0);
tl.fromTo("#c-sweep", { backgroundPosition: "120% 0" }, { backgroundPosition: "-20% 0", duration: 1.4, ease: "power2.inOut" }, 16.5);
drift(17.4, ["#c-you", "#c-for", "#c-rule", "#c-trust", "#c-means"], 0.06);

// ---------- D (18-24): hold ----------
cue(18.0, "#d-rays", { opacity: 0, rotation: -8 }, { opacity: 1, rotation: 4, duration: 6.0, ease: "sine.inOut" });
tl.fromTo("#d-thank", { "--tw": "-2%", y: 20, filter: "blur(10px) drop-shadow(0px 0px 0px rgba(160,195,255,0))" },
  { "--tw": "116%", y: 0, filter: "blur(0px) drop-shadow(0px 0px 34px rgba(160,195,255,0.4))", duration: 1.5, ease: "power2.inOut" }, 18.75);
rise(19.5, "#d-making .w", 0.07, 1.0);
rise(20.25, "#d-future .w", 0.09, 1.0);
tl.fromTo("#d-hold", { scale: 1 }, { scale: 1.04, duration: 5.2, ease: "none" }, 18.0);
drift(23.1, ["#d-thank", "#d-making", "#d-future"], 0.06);
tl.to("#cd-head", { opacity: 0, duration: 0.6 }, 23.1);
tl.to(["#cd-ribbons", "#d-rays", "#cd-glow"], { opacity: 0, duration: 0.8, ease: "power1.in" }, 23.3);

// ---------- E (24-30): the logo assembles ----------
cue(23.5, "#e-spot", { opacity: 0 }, { opacity: 1, duration: 1.2, ease: "power2.out" });
cue(23.55, "#e-flare", { opacity: 0, scaleX: 1.7 }, { opacity: 1, scaleX: $FLARE_SX, duration: 0.45, ease: "power3.in" });
tl.fromTo("#lp-bar", { clipPath: "inset(0% 50% 0% 50%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: 0.55, ease: "expo.out" }, 24.0);
tl.to("#e-flare", { opacity: 0, scaleY: 0.3, duration: 0.7, ease: "power2.out" }, 24.1);
cue(24.15, ".lp-l", { opacity: 0, y: -34, filter: "blur(6px)" },
  { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.65, ease: "expo.out", stagger: 0.06 });
tl.fromTo("#lp-glyph", { "--gw": "-14%", scale: 0.97 }, { "--gw": "118%", scale: 1, duration: 0.7, ease: "power2.inOut" }, 24.5);
tl.fromTo(["#lp-swoosh", "#lp-swoosh-glow"], { "--sw": "-8deg" },
  { "--sw": "$SW_END" + "deg", duration: 1.0, ease: "power2.inOut" }, 24.7);
cue(24.7, "#lp-swoosh-glow", { opacity: 0 }, { opacity: 0.9, duration: 0.5, ease: "power1.out" });
tl.to("#lp-swoosh-glow", { opacity: 0, duration: 0.6, ease: "power1.in" }, 25.6);
cue(25.5, "#lp-ellipse", { opacity: 0, scale: 0.25, rotation: -35 },
  { opacity: 1, scale: 1, rotation: 0, duration: 0.85, ease: "expo.out" });
cue(25.5, "#e-bloom", { opacity: 0.95, scale: 0.4 }, { opacity: 0, scale: 2.4, duration: 1.0, ease: "power2.out" });
cue(25.8, ".lp-w", { opacity: 0, y: 14, filter: "blur(5px)" },
  { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.7, ease: "power3.out", stagger: 0.1 });
tl.fromTo("#e-glint", { backgroundPosition: "120% 0" }, { backgroundPosition: "-20% 0", duration: 0.9, ease: "power2.inOut" }, 26.25);
cue(26.25, "#e-year", { opacity: 0, letterSpacing: "0.95em", filter: "blur(8px)" },
  { opacity: 1, letterSpacing: "0.55em", filter: "blur(0px)", duration: 1.1, ease: "power3.out" });
cue(26.45, ["#e-hl", "#e-hr"], { scaleX: 0 }, { scaleX: 1, duration: 0.9, ease: "power3.out" });
rise(27.0, "#e-amb .w", 0.1, 1.0);
rise(27.375, "#e-com .w", 0.1, 1.0);
cue(27.75, ["#e-cdoe", "#e-sep", "#e-jo"], { opacity: 0, y: -12 },
  { opacity: 0.95, y: 0, duration: 1.0, ease: "power3.out", stagger: 0.08 });
tl.fromTo("#e-hold", { scale: 1 }, { scale: 1.025, duration: 6.0, ease: "none", transformOrigin: "540px 760px" }, 24.0);

window.__timelines = window.__timelines || {};
window.__timelines.reel = tl;
""")

hl = "\n".join(
    f'cue({9.0 + i * 0.375:.3f}, "#tile{k}", {{ boxShadow: "0 0 0 1px rgba(200,220,255,0.16), 0 20px 60px rgba(0,0,12,0.65)" }}, '
    f'{{ boxShadow: "0 0 0 3px rgba(47,224,198,0.95), 0 0 46px rgba(47,224,198,0.85)", duration: 0.35, ease: "power2.out", yoyo: true, repeat: 1 }});'
    for i, k in enumerate(HIGHLIGHT)
)
js = JS.substitute(
    TOTAL=f"{TOTAL:.3f}", ROLLS=json.dumps({str(k): v for k, v in ROLLS.items()}), NUM_H=f"{NUM_PX:.3f}",
    GLINT_END=f"{NUM_W + 500:.0f}", HIGHLIGHTS=hl, FLARE_SX=f"{(BAR_X1 - BAR_X0) / 900:.3f}",
    SW_END=f"{SW_EXTENT + 10:.1f}",
)

page = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Deeksharambh 2026 thank-you reel</title></head>
<body>
<div id="stage" data-composition-id="reel" data-start="0" data-duration="{TOTAL:.3f}"
     data-width="1080" data-height="1920" data-fps="30">
  <style>{page_css}</style>
{body}
  <script src="assets/gsap.min.js"></script>
  <script>{js}</script>
</div>
</body>
</html>
"""
(project / "index.html").write_text(page, encoding="utf-8")
print(f"composed: {TOTAL:.0f}s, number {NUM_PX:.0f}px x {NUM_W:.0f}px wide, {n_tiles} tiles, "
      f"{len(logo['pieces'])} logo pieces, swoosh sweep {SW_EXTENT:.0f} deg")
