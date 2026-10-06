#!/usr/bin/env python3
"""Compose the kinetic Deeksharambh 2026 reel: 28 s at 120 BPM, stomp-cut type, animated logo.

Usage: motion/deeksharambh-2026-kinetic/compose.py --project motion/deeksharambh-2026-kinetic/project
       (run prep_assets.py and make_score.py into the same project first)

Every entrance lands on a beat (0.5 s) or an eighth (0.25 s):

  0-4    a wall of faces flickers every two frames behind a counter racing to
         11,000; it locks at 1.0 s with a shockwave, RGB split and shake;
         learners / chose / JAIN Online. land on the next three beats; the
         number fills with faces and the camera dives through its zero
  4-10   drop: five tilted face columns scroll in opposite directions; Every
         stomps, face. is filled with faces that cycle inside the letters;
         A different / ambition.; a pull-back to all 240 faces at once
  10-16  slice wipe into the branded frame; You / chose us / for your
         education.; the screen flips teal for That trust; means /
         everything. cascades, echoes, whips out
  16-22  Thank you echoes and collapses; for making us / part of the /
         future / you're building.; the message folds into a line of light
  22-28  the beat drops on the logo: bar slash, letters stomp, glyph wipe,
         swoosh write-on, ellipse lands with a shockwave and particles;
         2026; Your ambition. / Our commitment.; CDOE and JAIN Online lockups

Copy is sentence case; the event name only ever appears as the logo. Shake
offsets are fixed numbers (render workers must agree frame to frame), every
cued fromTo uses immediateRender: false, no video elements, and copy is
measured from the font files against the 100-960 px text column.
"""
import argparse
import html
import json
import math
import pathlib
import random
import struct
from string import Template

ap = argparse.ArgumentParser(description="Compose the kinetic Deeksharambh 2026 reel into index.html.")
ap.add_argument("--project", required=True)
project = pathlib.Path(ap.parse_args().project).expanduser().resolve()
A = project / "assets"
for need in ("logo/logo.json", "img/mosaic.jpg", "img/col0.jpg", "img/grain.png", "img/jain-online.png",
             "img/jain-cdoe.png", "audio/score.wav", "fonts/Montserrat-900.ttf", "fonts/PlayfairDisplay-600i.ttf"):
    if not (A / need).is_file():
        raise SystemExit(f"missing assets/{need} — run prep_assets.py / make_score.py into {project} first")

TOTAL = 28.0
esc = html.escape
COL_L, COL_W = 100.0, 860.0          # text column: x 100-960
CX = COL_L + COL_W / 2


# ---------- font metrics (stdlib TTF reader: cmap format 4 + hmtx) ----------
_cache = {}


def advances(ttf, text):
    if ttf not in _cache:
        d = (A / "fonts" / ttf).read_bytes()
        tab = {}
        for i in range(struct.unpack(">H", d[4:6])[0]):
            tag, _, off, _ = struct.unpack(">4sIII", d[12 + 16 * i:28 + 16 * i])
            tab[tag.decode("latin-1")] = off
        upem = struct.unpack(">H", d[tab["head"] + 18:tab["head"] + 20])[0]
        nhm = struct.unpack(">H", d[tab["hhea"] + 34:tab["hhea"] + 36])[0]
        c = tab["cmap"]
        sub = None
        for i in range(struct.unpack(">H", d[c + 2:c + 4])[0]):
            pid, eid, off = struct.unpack(">HHI", d[c + 4 + 8 * i:c + 12 + 8 * i])
            if pid == 3 and eid == 1 and struct.unpack(">H", d[c + off:c + off + 2])[0] == 4:
                sub = c + off
        _cache[ttf] = (d, tab, upem, nhm, sub)
    d, tab, upem, nhm, sub = _cache[ttf]
    seg2 = struct.unpack(">H", d[sub + 6:sub + 8])[0]
    ends, starts = sub + 14, sub + 16 + seg2
    deltas, ranges = starts + seg2, starts + 2 * seg2
    u16 = lambda o: struct.unpack(">H", d[o:o + 2])[0]

    def gid(cp):
        for s in range(seg2 // 2):
            if cp > u16(ends + 2 * s):
                continue
            st = u16(starts + 2 * s)
            if cp < st:
                return 0
            delta = struct.unpack(">h", d[deltas + 2 * s:deltas + 2 * s + 2])[0]
            ro = u16(ranges + 2 * s)
            if ro == 0:
                return (cp + delta) & 0xFFFF
            g = u16(ranges + 2 * s + ro + 2 * (cp - st))
            return (g + delta) & 0xFFFF if g else 0
        return 0

    return [u16(tab["hmtx"] + 4 * min(gid(ord(ch)), nhm - 1)) / upem for ch in text]


def tw(ttf, text, px, track=0.0):
    return sum(advances(ttf, text)) * px + track * px * max(0, len(text) - 1)


def fit(ttf, text, px, maxw=COL_W - 20, track=0.0):
    return min(px, maxw / tw(ttf, text, 1.0, track))


M9, M8, M7, P6 = "Montserrat-900.ttf", "Montserrat-800.ttf", "Montserrat-700.ttf", "PlayfairDisplay-600i.ttf"
TR = -0.03  # display tracking for the stomp type

SZ = {
    "num": fit(M9, "11,000+", 250, track=TR),
    "learners": 76, "chose1": 150, "jain": 64,
    "every": fit(M9, "Every", 270, track=TR), "face": fit(M9, "face.", 270, track=TR),
    "diff": fit(M8, "A different", 100), "amb": fit(P6, "ambition.", 210),
    "you": 240, "choseus": None, "edu": fit(M7, "for your education.", 74),
    "that": 200, "trust": fit(P6, "trust", 330), "means": fit(M9, "means", 170, track=TR),
    "every2": fit(M9, "everything.", 130, track=TR),
    "thank": fit(P6, "Thank you", 200), "making": fit(M8, "for making us", 88),
    "part": 88, "future": fit(P6, "future", 240), "building": fit(M8, "you’re building.", 88),
    "year": 64, "tag": 62, "tagi": 72,
}
# "chose us" shares a line: Playfair chose + Montserrat us, scaled together
cu = tw(P6, "chose ", 220) + tw(M9, "us", 240, TR)
k = min(1.0, (COL_W - 20) / cu)
SZ["choseus"] = (220 * k, 240 * k)
CHECK = {
    "11,000+": tw(M9, "11,000+", SZ["num"], TR), "Every": tw(M9, "Every", SZ["every"], TR),
    "face.": tw(M9, "face.", SZ["face"], TR), "ambition.": tw(P6, "ambition.", SZ["amb"]),
    "chose us": tw(P6, "chose ", SZ["choseus"][0]) + tw(M9, "us", SZ["choseus"][1], TR),
    "trust": tw(P6, "trust", SZ["trust"]), "everything.": tw(M9, "everything.", SZ["every2"], TR),
    "Thank you": tw(P6, "Thank you", SZ["thank"]), "you’re building.": tw(M8, "you’re building.", SZ["building"]),
    "part of the": tw(M8, "part of the", SZ["part"]),
    "Your ambition.": tw(M7, "Your ", SZ["tag"]) + tw(P6, "ambition.", SZ["tagi"]),
    "Our commitment.": tw(M7, "Our ", SZ["tag"]) + tw(P6, "commitment.", SZ["tagi"]),
}
wide = {k2: round(v) for k2, v in CHECK.items() if v > COL_W}
if wide:
    raise SystemExit(f"copy wider than the {COL_W:.0f} px column: {wide}")
W = {k2: v for k2, v in CHECK.items()}
W["learners"] = tw(M8, "learners", SZ["learners"])
W["edu"] = tw(M7, "for your education.", SZ["edu"])

# ---------- logo ----------
logo = json.loads((A / "logo" / "logo.json").read_text())
LW, LH = logo["size"]
LOGO_W = 840.0
LS = LOGO_W / LW
LOGO_L, LOGO_T = 120.0, 520.0
pieces = {p["name"]: p for p in logo["pieces"]}
sw = logo["swoosh"]
SW_FROM = sw["start"] + 4
SW_EXTENT = SW_FROM - (sw["end"] - 4)
swp = pieces["swoosh"]
SW_CX, SW_CY = (sw["center"][0] - swp["x"]) * LS, (sw["center"][1] - swp["y"]) * LS
BAR_Y = LOGO_T + (sum(logo["bar_rows"]) / 2) * LS
BAR_X0 = LOGO_L + pieces["bar"]["x"] * LS
BAR_X1 = LOGO_L + (pieces["bar"]["x"] + pieces["bar"]["w"]) * LS
ell = pieces["ellipse"]
ELL_CX, ELL_CY = LOGO_L + (ell["x"] + ell["w"] / 2) * LS, LOGO_T + (ell["y"] + ell["h"] / 2) * LS
letters = sorted((p for p in logo["pieces"] if p["group"] == "letters"), key=lambda p: p["order"])
lwords = sorted((p for p in logo["pieces"] if p["group"] == "subtitle"), key=lambda p: p["order"])


def piece(nm, cls=""):
    p = pieces[nm]
    return (f'<img class="lp {cls}" id="lp-{nm}" src="assets/logo/{nm}.png" alt="" style="left:{LOGO_L + p["x"] * LS:.2f}px; '
            f'top:{LOGO_T + p["y"] * LS:.2f}px; width:{p["w"] * LS:.2f}px; height:{p["h"] * LS:.2f}px;">')


# ---------- face material ----------
COLW, PITCH, STRIP_H = 220, 236, 8480
rng = random.Random(28)
cells = []
CELL, GAPC = 254, 18
cs = CELL / COLW
for r in range(7):
    for c in range(4):
        x = 5 + c * (CELL + GAPC)
        y = 8 + r * (CELL + GAPC)
        a = rng.randint(0, 20)
        cells.append((len(cells), x, y, (r * 4 + c + r) % 5, a))
cell_html = "".join(
    f'<div class="cell" style="left:{x}px; top:{y}px;"><img class="cstrip" id="cs{i}" data-a="{a}" '
    f'src="assets/img/col{col}.jpg" alt=""></div>' for i, x, y, col, a in cells)
cols_html = "".join(f'<img class="col" id="col{c}" src="assets/img/col{c}.jpg" alt="" style="left:{c * 240}px;">'
                    for c in range(5))
cols4_html = "".join(f'<img class="col" id="dcol{c}" src="assets/img/col{(c + 2) % 5}.jpg" alt="" style="left:{c * 240}px;">'
                     for c in range(5))

rngp = random.Random(9)
sparks = "".join(
    f'<div class="spark" data-a="{rngp.uniform(0, 360):.1f}" data-d="{rngp.uniform(160, 420):.0f}" '
    f'style="left:{ELL_CX - 5:.1f}px; top:{ELL_CY - 5:.1f}px; width:{rngp.choice([6, 8, 10])}px; height:{rngp.choice([6, 8, 10])}px;"></div>'
    for _ in range(22))
dust = "".join(
    f'<div class="dust" data-r="{rngp.uniform(200, 700):.0f}" style="left:{rngp.uniform(0, 1080):.0f}px; '
    f'top:{rngp.uniform(0, 2200):.0f}px; width:{rngp.choice([2, 2, 3, 4])}px; height:{rngp.choice([2, 2, 3, 4])}px; '
    f'opacity:{rngp.uniform(0.2, 0.6):.2f};"></div>' for _ in range(40))

# fixed shake offsets (deterministic across render workers)
SHAKE = [(1.0, -0.6), (-0.85, 0.9), (0.7, 0.45), (-0.5, -0.75), (0.32, 0.38), (-0.15, -0.2), (0, 0)]

FONTS = "\n".join(
    f"@font-face {{ font-family: '{fam}'; font-weight: {w}; font-style: {st}; src: url('assets/fonts/{f}.ttf'); }}"
    for fam, w, st, f in [("Montserrat", 500, "normal", "Montserrat-500"), ("Montserrat", 600, "normal", "Montserrat-600"),
                          ("Montserrat", 700, "normal", "Montserrat-700"), ("Montserrat", 800, "normal", "Montserrat-800"),
                          ("Montserrat", 900, "normal", "Montserrat-900"),
                          ("Playfair Display", 500, "italic", "PlayfairDisplay-500i"),
                          ("Playfair Display", 600, "italic", "PlayfairDisplay-600i")])


def mw(text, cls="w"):
    return " ".join(f'<span class="mw"><span class="{cls}">{esc(t)}</span></span>' for t in text.split())


def bw(id_, text, width, top, extra_cls="", style=""):
    """A centred line revealed by a teal block wipe."""
    return (f'<div class="line bwl {extra_cls}" id="{id_}" style="top:{top}px; {style}">'
            f'<div class="bwbar" id="{id_}-bar" style="left:{COL_W / 2 - width / 2 - 16:.1f}px; width:{width + 32:.1f}px;"></div>'
            f'<span class="bwt" id="{id_}-t">{text}</span></div>')


css = Template(r"""
$FONTS
#stage { position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #030a26; color: #fff;
  font-family: 'Montserrat', sans-serif; }
.full { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; }
.scene { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; overflow: hidden; }
.line { position: absolute; left: ${COL_L}px; width: ${COL_W}px; text-align: center; white-space: nowrap; line-height: 1.05; }
.left { text-align: left; }
.st { font-weight: 900; letter-spacing: -0.03em; }
.it { font-family: 'Playfair Display', serif; font-style: italic; font-weight: 600; }
.teal { color: #2fe0c6; }
.navy { color: #071450; }
.mw { display: inline-block; overflow: hidden; vertical-align: bottom; padding: 0 0.14em 0.16em; margin: 0 -0.14em -0.16em; }
.w { display: inline-block; }
.bwbar { position: absolute; top: 4%; height: 92%; background: #2fe0c6; transform: scaleX(0); transform-origin: 0% 50%; }
.bwt { position: relative; opacity: 0; }
.ch { display: inline-block; }

/* background */
#bg-base { background: linear-gradient(180deg, #020822 0%, #051466 60%, #0b28a8 100%); }
#pool { position: absolute; left: -300px; top: -400px; width: 1700px; height: 1700px; border-radius: 50%;
  background: radial-gradient(circle, rgba(47,110,255,0.4) 0%, rgba(47,110,255,0) 62%); }
.dust { position: absolute; border-radius: 50%; background: #dfe9ff; }

/* S1 */
.cell { position: absolute; width: ${CELL}px; height: ${CELL}px; overflow: hidden; border-radius: 18px; }
.cstrip { position: absolute; left: 0; top: 0; width: ${CELL}px; height: auto; }
#s1-wall { filter: brightness(0.5) saturate(1.15); }
#s1-tint { background: radial-gradient(ellipse 620px 520px at 540px 800px, rgba(3,10,38,0.86) 0%, rgba(3,10,38,0.5) 70%, rgba(3,10,38,0.25) 100%); }
#s1-num, #s1-mos { top: 610px; font-size: ${NUM}px; }
#s1-mos { color: transparent; background: url('assets/img/mosaic.jpg') center / auto 140% repeat-x;
  -webkit-background-clip: text; background-clip: text; opacity: 0; }
#s1-plus { color: #2fe0c6; display: inline-block; opacity: 0; }
#s1-mos .p2 { color: transparent; }
.ring { position: absolute; width: 200px; height: 200px; border-radius: 50%; border: 6px solid #2fe0c6; opacity: 0;
  box-shadow: 0 0 40px rgba(47,224,198,0.7), inset 0 0 30px rgba(47,224,198,0.5); }
#s1-learners { top: 885px; font-size: 76px; font-weight: 800; }
#s1-chose { top: 975px; font-size: 150px; line-height: 1.15; }
#s1-jain { top: 1170px; }
#s1-chip { display: inline-block; background: #ffffff; color: #071450; font-weight: 800; font-size: 64px;
  padding: 14px 40px 18px; border-radius: 22px; opacity: 0; }
#s1-zoom { transform-origin: ${ZX}px ${ZY}px; }

/* S2 */
#s2-colwrap { position: absolute; left: -60px; top: -340px; width: 1200px; height: 2600px; transform: rotate(-8deg) scale(1.22);
  transform-origin: 600px 1300px; }
.col { position: absolute; top: 0; width: 220px; height: ${STRIP_H}px; }
#s2-dim { background: rgba(3,10,38,0.5); }
#s2-band { position: absolute; left: 0; top: 560px; width: 1080px; height: 640px; background: rgba(3,10,38,0.86);
  opacity: 0; }
#s2-every { top: 570px; font-size: ${EVERY}px; }
#s2-face { top: 860px; font-size: ${FACE}px; color: transparent;
  background: url('assets/img/mosaic.jpg') 0px 0px / 1160px 696px repeat;
  -webkit-background-clip: text; background-clip: text;
  filter: drop-shadow(0 0 2px #2fe0c6) drop-shadow(0 0 22px rgba(47,224,198,0.55)); }
#s2-diff { top: 760px; font-size: ${DIFF}px; font-weight: 800; }
#s2-amb { top: 880px; font-size: ${AMB}px; line-height: 1.2; }
#s2-mark { position: absolute; left: ${MARK_L}px; top: 1105px; width: ${MARK_W}px; height: 22px; background: #2fe0c6;
  transform: scaleX(0); transform-origin: 0 50%; }
#s2-mospanel { background: #030a26; opacity: 0; }
#s2-mos { position: absolute; left: 0; top: -12px; width: 1080px; height: 1944px; opacity: 0; transform-origin: 540px 972px; }
.slice { position: absolute; left: 0; width: 1080px; height: 241px; }

/* S3 */
#s3-base { background: linear-gradient(180deg, #030a2a 0%, #06186a 60%, #0b2aa0 100%); }
#s3-head { position: absolute; left: 375px; top: 250px; width: 330px; opacity: 0; }
#s3-you { top: 430px; font-size: ${YOU}px; }
#s3-cu { top: 660px; font-size: ${CU2}px; }
#s3-cu .it { font-size: ${CU1}px; }
#s3-cu .st { font-size: ${CU2}px; }
#s3-teal { background: #2fe0c6; clip-path: circle(0% at 530px 880px); }
#s3-that { top: 560px; font-size: 200px; }
#s3-trust { top: 740px; font-size: ${TRUST}px; line-height: 1.2; }
#s3-uline { position: absolute; left: 230px; top: 1170px; width: 600px; height: 20px; background: #071450;
  transform: scaleX(0); transform-origin: 0 50%; }
#s3-means { top: 690px; font-size: ${MEANS}px; }
#s3-ev, .s3-echo { top: 900px; font-size: ${EV}px; }
.s3-echo { opacity: 0; }

/* S4 */
#s4-colwrap { position: absolute; left: -60px; top: -340px; width: 1200px; height: 2600px; transform: rotate(8deg) scale(1.22);
  transform-origin: 600px 1300px; opacity: 0.16; }
#s4-tint { background: radial-gradient(ellipse 640px 700px at 540px 900px, rgba(3,10,38,0.92) 0%, rgba(3,10,38,0.7) 70%, rgba(3,10,38,0.5) 100%); }
.thank { top: 500px; font-size: ${THANK}px; line-height: 1.2; }
.thank.echo { opacity: 0; }
#s4-making, #s4-part, #s4-build { font-size: 88px; font-weight: 800; letter-spacing: -0.01em; }
#s4-making { top: 760px; font-size: ${MAKING}px; }
#s4-part { top: 860px; }
#s4-future { top: 940px; font-size: ${FUTURE}px; line-height: 1.2; }
#s4-build { top: 1225px; font-size: ${BUILD}px; }

/* S5 */
#s5-spot { background: radial-gradient(ellipse 760px 640px at 540px 690px, rgba(44,96,255,0.42) 0%, rgba(20,50,170,0.16) 45%, rgba(0,0,0,0) 75%); opacity: 0; }
.flare { position: absolute; left: ${FL_L}px; width: 1080px; height: 0; top: ${BAR_Y}px; opacity: 0; }
.flare .core { position: absolute; left: 90px; width: 900px; top: -2px; height: 4px; border-radius: 2px;
  background: linear-gradient(90deg, rgba(255,255,255,0), #fff 25%, #fff 75%, rgba(255,255,255,0));
  box-shadow: 0 0 20px 5px rgba(150,220,255,0.9); }
.flare .halo { position: absolute; left: -100px; width: 1280px; top: -26px; height: 52px; filter: blur(12px);
  background: linear-gradient(90deg, rgba(47,224,198,0), rgba(47,224,198,0.6) 40%, rgba(120,170,255,0.6) 60%, rgba(47,224,198,0)); }
.lp { position: absolute; }
#lp-bar { clip-path: inset(0% 50% 0% 50%); }
#lp-glyph { --gw: -14%; -webkit-mask-image: linear-gradient(115deg, #000 calc(var(--gw) - 14%), transparent var(--gw));
  mask-image: linear-gradient(115deg, #000 calc(var(--gw) - 14%), transparent var(--gw)); }
#lp-swoosh { --sw: -8deg;
  -webkit-mask-image: conic-gradient(from ${SW_FROM}deg at ${SW_CX}px ${SW_CY}px, transparent 0deg,
    transparent calc(360deg - var(--sw) - 7deg), #000 calc(360deg - var(--sw)));
  mask-image: conic-gradient(from ${SW_FROM}deg at ${SW_CX}px ${SW_CY}px, transparent 0deg,
    transparent calc(360deg - var(--sw) - 7deg), #000 calc(360deg - var(--sw))); }
.spark { position: absolute; border-radius: 50%; background: #c9fff5; box-shadow: 0 0 12px #2fe0c6; opacity: 0; }
#s5-glint { position: absolute; left: ${LOGO_L}px; top: ${LOGO_T}px; width: ${LOGO_W}px; height: ${LOGO_H}px;
  -webkit-mask-image: url('assets/img/deeksharambh.png'); -webkit-mask-size: ${LOGO_W}px ${LOGO_H}px;
  mask-image: url('assets/img/deeksharambh.png'); mask-size: ${LOGO_W}px ${LOGO_H}px;
  background: linear-gradient(105deg, rgba(255,255,255,0) 42%, rgba(255,255,255,0.95) 50%, rgba(255,255,255,0) 58%);
  background-size: 300% 100%; background-position: 120% 0; }
#s5-year { top: 880px; font-size: 64px; font-weight: 800; letter-spacing: 0.45em; padding-left: 0.45em; }
.hair { position: absolute; top: 914px; width: 150px; height: 3px; background: #2fe0c6; transform: scaleX(0); }
#s5-hl { left: 190px; transform-origin: 100% 50%; }
#s5-hr { left: 740px; transform-origin: 0% 50%; }
#s5-amb, #s5-com { font-size: ${TAG}px; font-weight: 700; }
#s5-amb .it, #s5-com .it { font-size: ${TAGI}px; }
#s5-cdoe { position: absolute; left: 118px; top: 252px; width: 380px; opacity: 0; }
#s5-jo { position: absolute; left: 600px; top: 252px; width: 330px; opacity: 0; }
#s5-sep { position: absolute; left: 548px; top: 250px; width: 2px; height: 70px; background: rgba(207,224,255,0.6); opacity: 0; }

/* overlays */
#flash { background: #f2fbff; opacity: 0; }
#vignette { background: radial-gradient(ellipse at 50% 46%, rgba(0,0,0,0) 58%, rgba(0,0,10,0.6) 100%); }
#grain { background-image: url('assets/img/grain.png'); background-size: 256px 256px; mix-blend-mode: overlay; opacity: 0.1; }

/* cued elements start hidden */
#s1-num, #s1-learners, #s1-chose .w, #s2-every, #s2-face, #s2-diff .w, #s2-amb, #s3-you, #s3-cu .w, #s3-that,
#s3-trust, #s3-means, #s3-ev .ch, #s4-making .w, #s4-part .w, #s4-future, #s4-build .w, .thank,
#s5-year, #s5-amb .w, #s5-com .w, .lp-l, .lp-w, #lp-ellipse, #s2-colwrap, #s1-wall { opacity: 0; }
""").substitute(
    FONTS=FONTS, COL_L=f"{COL_L:.0f}", COL_W=f"{COL_W:.0f}", CELL=CELL, NUM=f"{SZ['num']:.1f}", STRIP_H=STRIP_H,
    ZX=f"{CX - W['11,000+'] / 2 + tw(M9, '11,', SZ['num'], TR) + tw(M9, '0', SZ['num'], TR) / 2:.1f}",
    ZY=f"{610 + SZ['num'] * 0.55:.1f}", EVERY=f"{SZ['every']:.1f}", FACE=f"{SZ['face']:.1f}", DIFF=f"{SZ['diff']:.1f}",
    AMB=f"{SZ['amb']:.1f}", MARK_L=f"{CX - W['ambition.'] / 2:.1f}", MARK_W=f"{W['ambition.']:.1f}",
    YOU=SZ["you"], CU1=f"{SZ['choseus'][0]:.1f}", CU2=f"{SZ['choseus'][1]:.1f}", TRUST=f"{SZ['trust']:.1f}",
    MEANS=f"{SZ['means']:.1f}", EV=f"{SZ['every2']:.1f}", THANK=f"{SZ['thank']:.1f}", MAKING=f"{SZ['making']:.1f}",
    FUTURE=f"{SZ['future']:.1f}", BUILD=f"{SZ['building']:.1f}", FL_L=f"{(BAR_X0 + BAR_X1) / 2 - 540:.1f}",
    BAR_Y=f"{BAR_Y:.1f}", SW_FROM=f"{SW_FROM:.2f}", SW_CX=f"{SW_CX:.2f}", SW_CY=f"{SW_CY:.2f}", LOGO_L=f"{LOGO_L:.0f}",
    LOGO_T=f"{LOGO_T:.0f}", LOGO_W=f"{LOGO_W:.0f}", LOGO_H=f"{LH * LS:.2f}", TAG=SZ["tag"], TAGI=SZ["tagi"],
)

ev_chars = "".join(f'<span class="ch">{esc(c)}</span>' for c in "everything.")
echo_ev = "".join(f'<div class="line st teal s3-echo" id="eve{i}">everything.</div>' for i in range(4))
thanks = "".join(f'<div class="line it thank{" echo" if i else ""}" id="ty{i}">Thank you</div>' for i in range(7))
slices = "".join(f'<div class="slice" id="sl{i}" style="top:{i * 240}px; background:{"#2fe0c6" if i % 2 else "#0b2aa8"};"></div>'
                 for i in range(8))

body = f"""
  <div id="bg" class="clip full" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="0">
    <div id="bg-base" class="full"></div><div id="pool"></div>{dust}
  </div>

  <!-- S1: 11,000+ learners chose JAIN Online. -->
  <div id="sA" class="clip scene" data-start="0" data-duration="4.200" data-track-index="1">
    <div id="s1-wall" class="full">{cell_html}</div>
    <div id="s1-tint" class="full"></div>
    <div id="s1-zoom" class="full">
      <div id="s1-shake" class="full">
        <div id="s1-num" class="line st"><span id="s1-n">0</span><span id="s1-plus">+</span></div>
        <div id="s1-mos" class="line st"><span>11,000</span><span class="p2">+</span></div>
        <div class="ring" id="ring1" style="left:{CX - 100:.0f}px; top:{610 + SZ['num'] * 0.5 - 100:.0f}px;"></div>
        <div id="s1-learners" class="line">learners</div>
        <div id="s1-chose" class="line it teal">{mw("chose")}</div>
        <div id="s1-jain" class="line"><span id="s1-chip">JAIN Online.</span></div>
      </div>
    </div>
  </div>

  <!-- S2: Every face. A different ambition. -->
  <div id="sB" class="clip scene" data-start="3.900" data-duration="6.300" data-track-index="2">
    <div id="s2-colwrap">{cols_html}</div>
    <div id="s2-dim" class="full"></div>
    <div id="s2-band"></div>
    <div id="s2-pump" class="full">
      <div id="s2-every" class="line st">Every</div>
      <div id="s2-face" class="line st">face.</div>
      <div id="s2-diff" class="line">{mw("A different")}</div>
      <div id="s2-amb" class="line it teal">ambition.</div>
      <div id="s2-mark"></div>
    </div>
    <div id="s2-mospanel" class="full"></div>
    <div id="s2-mos"><img src="assets/img/mosaic.jpg" alt="" style="position:absolute; left:0; top:0px; width:1080px; height:648px;"><img src="assets/img/mosaic.jpg" alt="" style="position:absolute; left:0; top:648px; width:1080px; height:648px;"><img src="assets/img/mosaic.jpg" alt="" style="position:absolute; left:0; top:1296px; width:1080px; height:648px;"></div>
  </div>

  <!-- S3: You chose us for your education. That trust means everything. -->
  <div id="sC" class="clip scene" data-start="9.900" data-duration="6.300" data-track-index="1">
    <div id="s3-inner" class="full">
      <div id="s3-base" class="full"></div>
      <img id="s3-head" src="assets/img/jain-online.png" alt="">
      <div id="s3-shake" class="full">
        <div id="s3-you" class="line st left">You</div>
        <div id="s3-cu" class="line left"><span class="mw"><span class="w it teal">chose</span></span> <span class="mw"><span class="w st">us</span></span></div>
        {bw("s3-edu", "for your education.", W["edu"], 930, "", f"font-size:{SZ['edu']:.1f}px; font-weight:700;")}
        <div id="s3-teal" class="full">
          <div id="s3-that" class="line st navy">That</div>
          <div id="s3-trust" class="line it navy">trust</div>
          <div id="s3-uline"></div>
        </div>
        <div id="s3-means" class="line st">means</div>
        {echo_ev}
        <div id="s3-ev" class="line st teal">{ev_chars}</div>
      </div>
    </div>
  </div>

  <!-- S4: Thank you for making us part of the future you're building. -->
  <div id="sD" class="clip scene" data-start="15.900" data-duration="6.200" data-track-index="2">
    <div id="s4-colwrap">{cols4_html}</div>
    <div id="s4-tint" class="full"></div>
    <div id="s4-inner" class="full">
      {thanks}
      <div id="s4-making" class="line">{mw("for making us")}</div>
      <div id="s4-part" class="line">{mw("part of the")}</div>
      <div id="s4-future" class="line it teal">future</div>
      <div id="s4-build" class="line">{mw("you’re building.")}</div>
    </div>
  </div>

  <!-- S5: logo, 2026, Your ambition. Our commitment. -->
  <div id="sE" class="clip scene" data-start="21.500" data-duration="{TOTAL - 21.5:.3f}" data-track-index="3">
    <div id="s5-spot" class="full"></div>
    <div class="flare" id="s5-flare"><div class="halo"></div><div class="core"></div></div>
    <div id="s5-shake" class="full">
      {piece("bar")}
      {''.join(piece(p["name"], "lp-l") for p in letters)}
      {piece("glyph")}
      {piece("swoosh")}
      <div class="ring" id="ring2" style="left:{ELL_CX - 100:.1f}px; top:{ELL_CY - 100:.1f}px;"></div>
      {sparks}
      {piece("ellipse")}
      {''.join(piece(p["name"], "lp-w") for p in lwords)}
      <div id="s5-glint"></div>
      <div class="hair" id="s5-hl"></div><div class="hair" id="s5-hr"></div>
      <div id="s5-year" class="line">2026</div>
      {bw("s5-amb", f'Your <span class="it teal">ambition.</span>', W["Your ambition."], 1010)}
      {bw("s5-com", f'Our <span class="it teal">commitment.</span>', W["Our commitment."], 1095)}
    </div>
    <img id="s5-cdoe" src="assets/img/jain-cdoe.png" alt="">
    <div id="s5-sep"></div>
    <img id="s5-jo" src="assets/img/jain-online.png" alt="">
  </div>

  <div id="slices" class="clip full" data-start="9.400" data-duration="1.000" data-track-index="4">{slices}</div>
  <div id="flash" class="clip full" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="5"></div>
  <div id="vignette" class="clip full" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="6"></div>
  <div id="grain" class="clip full" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="7"></div>
  <audio id="score" class="clip" src="assets/audio/score.wav" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="8" data-volume="1"></audio>
"""

js = Template(r"""
const TOTAL = $TOTAL;
const tl = gsap.timeline({ paused: true });
const qa = (s) => Array.from(document.querySelectorAll(s));
const IR = { immediateRender: false };
const cue = (t, target, from, to) => tl.fromTo(target, from, Object.assign({}, IR, to), t);
const SHAKE = $SHAKE;
const shake = (t, target, amp) => SHAKE.forEach(([x, y], i) =>
  tl.to(target, { x: x * amp, y: y * amp, duration: 0.035, ease: "none" }, t + i * 0.035));
const stomp = (t, target, origin) => cue(t, target,
  { opacity: 0, scale: 1.55, filter: "blur(12px)", transformOrigin: origin || "50% 50%" },
  { opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.32, ease: "expo.out" });
const rgb = (t, target) => cue(t, target,
  { textShadow: "-14px 0px 0px rgba(255,45,95,0.85), 14px 0px 0px rgba(40,240,255,0.85)" },
  { textShadow: "0px 0px 0px rgba(255,45,95,0), 0px 0px 0px rgba(40,240,255,0)", duration: 0.38, ease: "power2.out" });
const rise = (t, target, stagger) => cue(t, target, { yPercent: 115, opacity: 0 },
  { yPercent: 0, opacity: 1, duration: 0.42, ease: "expo.out", stagger: stagger || 0.06 });
const flash = (t, peak, dur) => cue(t, "#flash", { opacity: peak }, { opacity: 0, duration: dur || 0.22, ease: "power2.out" });
const punch = (t, target, s) => cue(t, target, { scale: s || 1.07 }, { scale: 1, duration: 0.4, ease: "expo.out" });
const wipe = (t, id) => {
  tl.set("#" + id + "-bar", { transformOrigin: "0% 50%" }, t);
  cue(t, "#" + id + "-bar", { scaleX: 0 }, { scaleX: 1, duration: 0.16, ease: "power3.in" });
  tl.set("#" + id + "-t", { opacity: 1 }, t + 0.16);
  tl.set("#" + id + "-bar", { transformOrigin: "100% 50%" }, t + 0.16);
  tl.to("#" + id + "-bar", { scaleX: 0, duration: 0.22, ease: "power3.out" }, t + 0.16);
};
const ring = (t, id, s) => cue(t, id, { opacity: 1, scale: 0.2 }, { opacity: 0, scale: s || 5, duration: 0.7, ease: "expo.out" });
const pumps = (a, b, target) => { for (let t = a; t < b - 0.01; t += 0.5)
  tl.fromTo(target, { scale: 1.022 }, { immediateRender: false, scale: 1, duration: 0.32, ease: "power2.out" }, t); };

// ---------- background ----------
tl.fromTo("#pool", { x: -80, y: 0 }, { x: 260, y: 420, duration: TOTAL, ease: "sine.inOut" }, 0);
qa(".dust").forEach((el) => tl.fromTo(el, { y: 0 }, { y: -Number(el.dataset.r), duration: TOTAL, ease: "none" }, 0));
tl.fromTo("#grain", { backgroundPosition: "0px 0px" }, { backgroundPosition: "46080px 30240px", duration: TOTAL, ease: "steps(336)" }, 0);

// ---------- S1 (0-4) ----------
tl.set("#s1-wall", { opacity: 1 }, 0);
qa(".cstrip").forEach((el) => {
  const a = Number(el.dataset.a);
  tl.fromTo(el, { y: -a * $PITCH }, { y: -(a + 14) * $PITCH, duration: 0.95, ease: "steps(14)" }, 0);
});
tl.fromTo("#s1-wall", { scale: 1.12 }, { scale: 1.0, duration: 1.0, ease: "power2.out" }, 0);
tl.set("#s1-num", { opacity: 1 }, 0);
const cnt = { v: 0 }, nEl = document.querySelector("#s1-n");
tl.fromTo(cnt, { v: 0 }, { v: 11000, duration: 0.98, ease: "power2.in",
  onUpdate: () => { nEl.textContent = Math.round(cnt.v).toLocaleString("en-IN"); } }, 0);
tl.fromTo("#s1-num", { scale: 0.86, filter: "blur(3px)" }, { scale: 1.0, filter: "blur(0px)", duration: 0.98, ease: "power2.in" }, 0);
// lock
flash(1.0, 0.85, 0.25);
tl.to("#s1-wall", { opacity: 0, scale: 1.25, duration: 0.25, ease: "power2.out" }, 1.0);
punch(1.0, "#s1-num", 1.28);
rgb(1.0, "#s1-num");
cue(1.0, "#s1-plus", { opacity: 0, scale: 0, rotation: -120 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.45, ease: "back.out(2.6)" });
ring(1.0, "#ring1", 6);
shake(1.0, "#s1-shake", 22);
wipe(1.5, "s1-learners-w");
rise(2.0, "#s1-chose .w");
punch(2.0, "#s1-chose", 1.12);
cue(2.5, "#s1-chip", { opacity: 0, scale: 0.3 }, { opacity: 1, scale: 1, duration: 0.42, ease: "back.out(2.2)" });
shake(2.5, "#s1-shake", 10);
cue(3.0, "#s1-mos", { opacity: 0 }, { opacity: 1, duration: 0.25, ease: "power1.out" });
tl.fromTo("#s1-mos", { backgroundPosition: "0px 50%" }, { backgroundPosition: "-1160px 50%", duration: 1.0, ease: "none" }, 3.0);
tl.to(["#s1-learners-w", "#s1-chose", "#s1-jain"], { y: 60, opacity: 0, filter: "blur(10px)", duration: 0.25, ease: "power2.in", stagger: 0.04 }, 3.2);
tl.fromTo("#s1-zoom", { scale: 1, filter: "blur(0px)" }, { immediateRender: false, scale: 16, filter: "blur(4px)", duration: 0.5, ease: "power3.in" }, 3.5);
flash(4.0, 0.9, 0.25);
tl.set("#s1-zoom", { opacity: 0 }, 4.02);

// ---------- S2 (4-10) ----------
tl.set("#s2-colwrap", { opacity: 1 }, 3.95);
[0, 1, 2, 3, 4].forEach((c) => {
  const up = c % 2 === 0;
  tl.fromTo("#col" + c, { y: up ? -300 : -5500 }, { y: up ? -5500 : -300, duration: 6.2, ease: "none" }, 3.9);
});
cue(3.95, "#s2-colwrap", { scale: 1.8, filter: "blur(12px)" }, { scale: 1.22, filter: "blur(0px)", duration: 0.5, ease: "expo.out" });
pumps(4.0, 8.0, "#s2-pump");
cue(4.45, "#s2-band", { scaleY: 0, opacity: 1 }, { scaleY: 1, opacity: 1, duration: 0.2, ease: "expo.out" });
stomp(4.5, "#s2-every");
rgb(4.5, "#s2-every");
shake(4.5, "#s2-pump", 14);
cue(5.0, "#s2-face", { opacity: 0, scale: 1.55, filter: "blur(12px) drop-shadow(0px 0px 2px #2fe0c6) drop-shadow(0px 0px 22px rgba(47,224,198,0.55))" },
  { opacity: 1, scale: 1, filter: "blur(0px) drop-shadow(0px 0px 2px #2fe0c6) drop-shadow(0px 0px 22px rgba(47,224,198,0.55))", duration: 0.32, ease: "expo.out" });
tl.fromTo("#s2-face", { backgroundPosition: "0px 0px" }, { backgroundPosition: "-1160px -232px", duration: 1.0, ease: "steps(15)" }, 5.0);
tl.to(["#s2-every", "#s2-face"], { y: -330, scale: 0.5, duration: 0.3, ease: "expo.inOut", transformOrigin: "50% 0%" }, 6.0);
tl.to("#s2-band", { scaleY: 1.25, duration: 0.3, ease: "expo.inOut" }, 6.0);
rise(6.0, "#s2-diff .w", 0.08);
stomp(6.5, "#s2-amb");
shake(6.5, "#s2-pump", 18);
cue(7.0, "#s2-mark", { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "expo.out" });
tl.to(["#s2-every", "#s2-face", "#s2-diff", "#s2-amb", "#s2-mark", "#s2-band"],
  { x: -1150, filter: "blur(16px)", duration: 0.3, ease: "power3.in", stagger: 0.03 }, 7.6);
cue(7.95, "#s2-mospanel", { opacity: 0 }, { opacity: 1, duration: 0.1 });
cue(8.0, "#s2-mos", { opacity: 1, scale: 5.5, rotation: 10 }, { opacity: 1, scale: 1.12, rotation: -4, duration: 0.95, ease: "expo.out" });
tl.fromTo("#s2-mos", { scale: 1.12, rotation: -4 }, { immediateRender: false, scale: 1.2, rotation: -6, duration: 1.0, ease: "none" }, 8.95);
flash(8.0, 0.6, 0.2);

// slice wipe 9.5 -> 10.25
qa(".slice").forEach((el, i) => {
  const dir = i % 2 ? 1 : -1;
  tl.set(el, { x: 1080 * dir }, 9.4);
  cue(9.45 + i * 0.015, el, { x: 1080 * dir }, { x: 0, duration: 0.2, ease: "power3.in" });
  tl.to(el, { x: -1080 * dir, duration: 0.22, ease: "power3.out" }, 10.0 + i * 0.015);
});

// ---------- S3 (10-16) ----------
tl.fromTo("#s3-head", { opacity: 0, y: -16 }, { immediateRender: false, opacity: 0.95, y: 0, duration: 0.35, ease: "expo.out" }, 10.1);
stomp(10.0, "#s3-you", "0% 50%");
rgb(10.0, "#s3-you");
rise(10.25, "#s3-cu .w", 0.25);
shake(10.5, "#s3-shake", 10);
wipe(11.0, "s3-edu");
tl.fromTo("#s3-teal", { clipPath: "circle(0% at 530px 880px)" }, { clipPath: "circle(150% at 530px 880px)", duration: 0.32, ease: "power3.in" }, 11.7);
tl.set(["#s3-you", "#s3-cu", "#s3-edu"], { opacity: 0 }, 12.02);
stomp(12.0, "#s3-that");
stomp(12.5, "#s3-trust");
punch(12.5, "#s3-teal", 1.04);
shake(12.5, "#s3-shake", 20);
cue(13.0, "#s3-uline", { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "expo.out" });
tl.to("#s3-teal", { clipPath: "circle(0% at 530px 880px)", duration: 0.25, ease: "power3.in" }, 13.5);
flash(13.75, 0.4, 0.18);
stomp(14.0, "#s3-means");
cue(14.5, "#s3-ev .ch", { opacity: 0, y: 120, skewX: -18 }, { opacity: 1, y: 0, skewX: 0, duration: 0.36, ease: "expo.out", stagger: 0.025 });
rgb(14.5, "#s3-ev");
qa(".s3-echo").forEach((el, i) => {
  cue(15.0 + i * 0.06, el, { opacity: 0.0, y: 0 }, { opacity: [0.5, 0.34, 0.22, 0.12][i], y: 150 * (i + 1), duration: 0.3, ease: "expo.out" });
});
tl.to("#s3-inner", { x: -1300, filter: "blur(26px)", duration: 0.32, ease: "power3.in" }, 15.6);

// ---------- S4 (16-22) ----------
tl.fromTo("#s4-colwrap img", { y: (i) => (i % 2 ? -4000 : -1200) }, { y: (i) => (i % 2 ? -2800 : -2400), duration: 6.2, ease: "none" }, 15.9);
cue(15.95, "#s4-inner", { x: 1300, filter: "blur(26px)" }, { x: 0, filter: "blur(0px)", duration: 0.32, ease: "expo.out" });
tl.set("#ty0", { opacity: 1 }, 15.95);
qa(".thank.echo").forEach((el, i) => {
  const k = i + 1, off = (k % 2 ? -1 : 1) * Math.ceil(k / 2) * 150;
  cue(16.25, el, { opacity: 0, y: 0 }, { opacity: 0.42 - Math.ceil(k / 2) * 0.1, y: off, duration: 0.35, ease: "expo.out" });
  tl.to(el, { y: 0, opacity: 0, duration: 0.25, ease: "power3.in" }, 16.75);
});
punch(17.0, "#ty0", 1.08);
rise(17.5, "#s4-making .w", 0.06);
rise(18.0, "#s4-part .w", 0.06);
stomp(18.5, "#s4-future");
cue(18.5, "#s4-future", { textShadow: "0px 0px 0px rgba(47,224,198,0)" }, { textShadow: "0px 0px 40px rgba(47,224,198,0.8)", duration: 0.3 });
tl.to("#s4-future", { textShadow: "0px 0px 18px rgba(47,224,198,0.35)", duration: 1.0 }, 18.8);
rise(19.0, "#s4-build .w", 0.06);
tl.fromTo("#s4-inner", { scale: 1 }, { immediateRender: false, scale: 1.035, duration: 2.0, ease: "none" }, 19.3);
tl.to(["#ty0", "#s4-making", "#s4-part", "#s4-future", "#s4-build"],
  { y: (i) => [$BARY - 600, $BARY - 810, $BARY - 905, $BARY - 1080, $BARY - 1270][i], scaleY: 0.03, opacity: 0.0,
    duration: 0.4, ease: "power3.in", stagger: 0.03 }, 21.3);

// ---------- S5 (22-28) ----------
cue(21.55, "#s5-flare", { opacity: 0, scaleX: 1.8 }, { opacity: 1, scaleX: $FLARE_SX, duration: 0.45, ease: "power3.in" });
cue(21.6, "#s5-spot", { opacity: 0 }, { opacity: 1, duration: 0.6 });
tl.fromTo("#lp-bar", { clipPath: "inset(0% 50% 0% 50%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: 0.14, ease: "power2.out" }, 22.0);
flash(22.0, 0.7, 0.22);
tl.to("#s5-flare", { opacity: 0, duration: 0.3 }, 22.05);
cue(22.05, ".lp-l", { opacity: 0, y: -80, filter: "blur(6px)" },
  { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.36, ease: "back.out(2.2)", stagger: 0.035 });
shake(22.0, "#s5-shake", 16);
tl.fromTo("#lp-glyph", { "--gw": "-14%" }, { "--gw": "118%", duration: 0.22, ease: "power2.out" }, 22.32);
tl.fromTo("#lp-swoosh", { "--sw": "-8deg" }, { "--sw": "$SW_END" + "deg", duration: 0.42, ease: "power2.inOut" }, 22.45);
cue(23.0, "#lp-ellipse", { opacity: 0, scale: 0, rotation: -60 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.5, ease: "back.out(2.6)" });
ring(23.0, "#ring2", 6);
qa(".spark").forEach((el) => {
  const a = Number(el.dataset.a) * Math.PI / 180, d = Number(el.dataset.d);
  cue(23.0, el, { opacity: 1, x: 0, y: 0 }, { opacity: 0, x: Math.cos(a) * d, y: Math.sin(a) * d, duration: 0.7, ease: "expo.out" });
});
flash(23.0, 0.45, 0.2);
shake(23.0, "#s5-shake", 12);
cue(23.25, ".lp-w", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.3, ease: "expo.out", stagger: 0.06 });
punch(23.5, "#s5-shake", 1.05);
tl.fromTo("#s5-glint", { backgroundPosition: "120% 0" }, { backgroundPosition: "-20% 0", duration: 0.5, ease: "power2.inOut" }, 23.5);
stomp(24.0, "#s5-year");
cue(24.05, ["#s5-hl", "#s5-hr"], { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "expo.out" });
wipe(24.5, "s5-amb");
wipe(25.0, "s5-com");
cue(25.5, ["#s5-cdoe", "#s5-sep", "#s5-jo"], { opacity: 0, y: -20 }, { opacity: 0.95, y: 0, duration: 0.35, ease: "expo.out", stagger: 0.06 });
pumps(22.0, 26.0, "#s5-shake");
flash(26.0, 0.35, 0.3);
tl.fromTo("#s5-glint", { backgroundPosition: "120% 0" }, { immediateRender: false, backgroundPosition: "-20% 0", duration: 0.7, ease: "power2.inOut" }, 26.0);
tl.fromTo("#s5-shake", { scale: 1 }, { immediateRender: false, scale: 1.03, duration: 2.0, ease: "none", transformOrigin: "540px 760px" }, 26.0);

window.__timelines = window.__timelines || {};
window.__timelines.reel = tl;
""").substitute(
    TOTAL=f"{TOTAL:.3f}", SHAKE=json.dumps(SHAKE), PITCH=f"{PITCH * cs:.3f}", BARY=f"{BAR_Y:.1f}",
    FLARE_SX=f"{(BAR_X1 - BAR_X0) / 900:.3f}", SW_END=f"{SW_EXTENT + 10:.1f}",
)

# the learners line uses a block wipe; give it the bar structure
body = body.replace('<div id="s1-learners" class="line">learners</div>',
                    bw("s1-learners-w", "learners", W["learners"], 885, "", "font-size:76px; font-weight:800;"))
css = css.replace("#s1-learners, ", "")

page = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Deeksharambh 2026 kinetic reel</title></head>
<body>
<div id="stage" data-composition-id="reel" data-start="0" data-duration="{TOTAL:.3f}"
     data-width="1080" data-height="1920" data-fps="30">
  <style>{css}</style>
{body}
  <script src="assets/gsap.min.js"></script>
  <script>{js}</script>
</div>
</body>
</html>
"""
(project / "index.html").write_text(page, encoding="utf-8")
print(f"composed: {TOTAL:.0f}s; sizes " + ", ".join(f"{k2} {v:.0f}" for k2, v in SZ.items() if isinstance(v, float)))
