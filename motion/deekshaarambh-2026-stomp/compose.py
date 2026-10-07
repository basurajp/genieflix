#!/usr/bin/env python3
"""Compose the Deekshaarambh 2026 stomp piece (32 s, 1080x1920@30) into index.html.

Usage: motion/deekshaarambh-2026-stomp/compose.py --project motion/deekshaarambh-2026-stomp/project
       (run faces_prep.py, prep_assets.py and make_score.py into the same project first)

Cut to beatmap.py (112.5 BPM, a beat every 16 frames, stomp-stomp-clap):

  intro   one learner's face, eyes locked to a viewfinder, changes on every
          stomp and clap with a shutter click, then bursts
  a       the drop: the camera pulls back 34x and that face is one tile of
          "11, / 000" built from hundreds of face tiles; the plus lands teal;
          learners / chose / JAIN Online.
  b       Welcome / to the / Batch of flip colours on stomp, stomp, clap; a
          shutter burst; "20 / 26." stamped out of navy with the scroll
          recording playing inside the letters, then stepped zooms into the 0
  c       a full-bleed eye-locked window; We are / proud / to nurture; the faces
          burst faster and faster while the counter races to 11,000+;
          ambitions / this year.; the window splits into a wall of 28 faces
  d       the wall slows down under the breakdown; "trust" is filled with faces;
          the wall stops and the camera finds one face for "each one."
  e       the peak: every hit a new screen; face bricks stack up for
          "to building"; "India." filled with faces
  f       the authentic artwork revealed by one clean mask; 2026; the tagline;
          JAIN Online; nothing moves after 30.0 s

Every displayed string is checked against the locked script before writing.
The tile number and the "2026." stencil are rasterized here with ffmpeg
drawtext from the same font files the page uses.
"""
import argparse
import html
import json
import math
import pathlib
import random
import struct
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import beatmap as BM  # noqa: E402

ap = argparse.ArgumentParser(description="Compose the Deekshaarambh 2026 stomp piece into index.html.")
ap.add_argument("--project", required=True)
project = pathlib.Path(ap.parse_args().project).expanduser().resolve()
A = project / "assets"
for need in ("brand/deekshaarambh.png", "brand/jain-online.png", "footage/scroll.mp4", "img/framed_sheet.jpg",
             "img/face_cells.jpg", "img/face_mosaic.jpg", "img/grain.png", "fonts/Montserrat-500.ttf",
             "fonts/Montserrat-800.ttf", "fonts/Montserrat-900.ttf", "audio/score.wav", "gsap.min.js"):
    if not (A / need).is_file():
        raise SystemExit(f"missing assets/{need}: run faces_prep.py / prep_assets.py / make_score.py into {project} first")
FACES = json.loads((HERE / "faces.json").read_text(encoding="utf-8-sig"))
ORDER = FACES["order"]
BIG = FACES["big"]                   # cleanest source pixels: the full-size eye-locked windows
FO, FE, FEY = 1000, 200, 430         # framed posts (assets/framed): canvas, eye gap, eye line
NFACE = len(FACES["faces"])

SCRIPT = [
    "11,000+ learners chose JAIN Online.",
    "Welcome to the Batch of 2026.",
    "We are proud to nurture 11,000+ ambitions this year.",
    "But even more than that, we are proud to carry the trust behind each one.",
    "Because every learner who chooses JAIN Online brings us one step closer to building a more skilled, future-ready India.",
    "Deekshaarambh 2026",
    "Your ambition. Our commitment.",
]
FW, FH, FPS = 1080, 1920, BM.FPS
TOTAL_F = BM.TOTAL_F
L, RM = 88.0, 140.0
COLW = FW - L - RM                   # 852
NAVY, WHITE, TEAL, INK = "#071C5B", "#FFFFFF", "#2FE0C8", "#04103A"
ASC, DESC, CAP = 0.968, 0.251, 0.70
HOLD_FACE, HERO_LAST = 6, 10         # faces.json indices: the "each one." face, the face the number is born from
esc = html.escape

# ---------------------------------------------------------------- font metrics
_fonts = {}


def advances(weight, text):
    if weight not in _fonts:
        d = (A / "fonts" / f"Montserrat-{weight}.ttf").read_bytes()
        tab = {}
        for i in range(struct.unpack(">H", d[4:6])[0]):
            tag, _, off, _ = struct.unpack(">4sIII", d[12 + 16 * i:28 + 16 * i])
            tab[tag.decode("latin-1")] = off
        c = tab["cmap"]
        sub = None
        for i in range(struct.unpack(">H", d[c + 2:c + 4])[0]):
            pid, eid, off = struct.unpack(">HHI", d[c + 4 + 8 * i:c + 12 + 8 * i])
            if pid == 3 and eid == 1 and struct.unpack(">H", d[c + off:c + off + 2])[0] == 4:
                sub = c + off
        upem = struct.unpack(">H", d[tab["head"] + 18:tab["head"] + 20])[0]
        nhm = struct.unpack(">H", d[tab["hhea"] + 34:tab["hhea"] + 36])[0]
        _fonts[weight] = (d, tab, sub, upem, nhm)
    d, tab, sub, upem, nhm = _fonts[weight]
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


TRACK = {500: 0.0, 800: -0.01, 900: -0.03}


def tw(text, px, weight):
    return sum(advances(weight, text)) * px + TRACK[weight] * px * max(0, len(text) - 1)


def fit(text, weight, maxpx, maxw=COLW):
    return min(maxpx, maxw / tw(text, 1.0, weight))


def top_for_cap(cap_top, px):
    """line-height 1: the box top that puts the cap height's top at cap_top"""
    return cap_top - (px * ((1 - (ASC + DESC)) / 2 + ASC) - CAP * px)


# ---------------------------------------------------------------- timing helpers
def T(f):
    """GSAP position for frame f (a hair early so the renderer's frame f/30 always includes it)"""
    return f"{max(0.0, (f - 0.05) / FPS):.5f}"


def D(n):
    return f"{n / FPS:.5f}"


def clip(f0, f1, track):
    s0 = max(0.0, (f0 - 0.02) / FPS)
    return f'data-start="{s0:.5f}" data-duration="{(f1 - 0.02) / FPS - s0:.5f}" data-track-index="{track}"'


# ---------------------------------------------------------------- copy check
SHOWN = []


def show(text):
    SHOWN.append(text)
    return text


# ---------------------------------------------------------------- face material
ROWS_SHEET = math.ceil(NFACE / 10)
reserved = {HOLD_FACE, HERO_LAST}
pool = [k for k in ORDER if k not in reserved]


def faces_for(n, offset):
    return [pool[(offset + i) % len(pool)] for i in range(n)]


big_pool = [k for k in BIG if k not in reserved]


def assign_big():
    """Every eye-locked window cut gets a face from BIG; the cuts that stay up longest get the
    cleanest faces, 1-frame burst cuts get what is left. Returns {layer: [face per change]}."""
    ends = {"hero": 64, "win": 416, "flash_b": 192, "flash_e": 656}
    layers = {"hero": BM.FACES["hero"][:-1], "win": BM.FACES["win"],
              "flash_b": [f for f in BM.FACES["flash"] if f < 192], "flash_e": [f for f in BM.FACES["flash"] if f >= 640]}
    full = {"hero": BM.FACES["hero"], "win": BM.FACES["win"], "flash_b": layers["flash_b"], "flash_e": layers["flash_e"]}
    slots = []
    for nm, frs in layers.items():
        seq = full[nm] + [ends[nm]]
        for i, f in enumerate(frs):
            slots.append((-(seq[i + 1] - f), f, nm, i))
    out = {nm: [None] * len(frs) for nm, frs in layers.items()}
    for n, (_, f, nm, i) in enumerate(sorted(slots)):
        k = big_pool[n % len(big_pool)]
        if i and out[nm][i - 1] == k:
            k = big_pool[(n + 1) % len(big_pool)]
        out[nm][i] = k
    out["hero"].append(HERO_LAST)
    return out


BIG_IDS = assign_big()


def sheet_pos(k, d):
    return f"{-(k % 10) * d:.2f}px {-(k // 10) * d:.2f}px"


def sheet_bg(d):
    return f"background-image:url('assets/img/framed_sheet.jpg'); background-size:{10 * d:.2f}px {ROWS_SHEET * d:.2f}px;"


def face_stack(prefix, ids, size, left, top):
    """stacked <img> posts (1000 px framed sources, eyes locked), all hidden; sets reveal one at a time"""
    uniq = list(dict.fromkeys(ids))
    imgs = "".join(f'<img class="fs" id="{prefix}{k}" src="assets/framed/f{k:03d}.jpg" alt="" '
                   f'style="left:{left:.2f}px; top:{top:.2f}px; width:{size:.2f}px; height:{size:.2f}px;">' for k in uniq)
    return imgs


J = []          # timeline script lines


def shuffle(prefix, frames, ids):
    prev = None
    for f, k in zip(frames, ids):
        if prev is not None and prev != k:
            J.append(f'tl.set("#{prefix}{prev}", {{opacity: 0}}, {T(f)});')
        J.append(f'tl.set("#{prefix}{k}", {{opacity: 1}}, {T(f)});')
        prev = k
    return prev


# ---------------------------------------------------------------- rasterizing type with ffmpeg
def raster(items, w, h, k=1):
    """items: (text, weight, px, x_pen, baseline). Per-glyph drawtext so tracking matches the page.
    Returns w*k x h*k gray bytes (white ink on black)."""
    with tempfile.TemporaryDirectory() as td:
        filt, n = [], 0
        for text, weight, px, x, base in items:
            adv = advances(weight, text)
            pen = x
            for i, ch in enumerate(text):
                tf = pathlib.Path(td) / f"g{n}.txt"
                tf.write_text(ch, encoding="utf-8")
                n += 1
                filt.append(f"drawtext=fontfile={A / 'fonts' / f'Montserrat-{weight}.ttf'}:textfile={tf}:"
                            f"fontsize={px * k:.2f}:x={pen * k:.2f}:y={base * k:.2f}:y_align=baseline:fontcolor=white")
                pen += adv[i] * px + TRACK[weight] * px
        vf = ",".join(filt + ["format=gray"])
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", f"color=black:s={w * k}x{h * k}",
                            "-vf", vf, "-frames:v", "1", "-f", "rawvideo", "-"], capture_output=True, check=True)
    return r.stdout


def bbox(buf, w, x0, y0, x1, y1, th=128):
    xs, ys = [], []
    for y in range(int(y0), int(y1)):
        row = buf[y * w:(y + 1) * w]
        for x in range(int(x0), int(x1)):
            if row[x] >= th:
                xs.append(x)
                ys.append(y)
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1) if xs else None


# ================================================================ section A: intro + tile number
NUM_W = 900
NPX = fit("000+", NUM_W, 340)
NCAP = CAP * NPX
GAP_N = 0.13 * NPX
ln1, ln2 = "11,", "000"
show("11,000+")                       # tiles "11," / "000" and the teal plus
PLUS_ADV = advances(NUM_W, "+")[0] * NPX
SUB_PX = 92
JO_PX = fit("JAIN Online.", 900, 150)
block_h = NCAP + GAP_N + NCAP + 70 + CAP * SUB_PX + 44 + CAP * JO_PX
n1_cap = 890 - block_h / 2
n1_base = n1_cap + NCAP
n2_cap = n1_base + GAP_N
n2_base = n2_cap + NCAP
mask = raster([(ln1, NUM_W, NPX, L, n1_base), (ln2, NUM_W, NPX, L, n2_base)], FW, FH)
P = 24                                # tile pitch
TS = 22                               # tile size
gx0, gy0 = L - 4, n1_cap - 8
tiles = []
for gy in range(int((n2_base + 12 - gy0) // P) + 1):
    for gx in range(int((COLW + 8) // P) + 1):
        x, y = gx0 + gx * P, gy0 + gy * P
        tot = 0
        for yy in range(int(y), int(y + P)):
            row = mask[yy * FW:(yy + 1) * FW]
            tot += sum(row[int(x):int(x + P)])
        cov = tot / (255 * P * P)
        if cov >= 0.3:
            tiles.append((x + (P - TS) / 2, y + (P - TS) / 2, cov, 1 if y < n1_base + GAP_N / 2 else 2))
# the hero tile: full coverage, in the left stroke of the middle 0
z_adv = advances(NUM_W, "0")[0] * NPX
hx = L + z_adv + TRACK[NUM_W] * NPX + 0.13 * NPX
hy = n2_cap + NCAP / 2
full = [t for t in tiles if t[2] >= 0.97 and t[3] == 2]
hero_tile = min(full, key=lambda t: (t[0] + TS / 2 - hx) ** 2 + (t[1] + TS / 2 - hy) ** 2)
rng = random.Random(4)
# face_cells.jpg: 20 columns of 128 px tight crops, faces.json index order
tile_cells = []
for t in tiles:
    tile_cells.append(HERO_LAST if t is hero_tile else rng.choice(ORDER))
CELL_ROWS = math.ceil(NFACE / 20)
tile_html = []
for (x, y, cov, line), c in zip(tiles, tile_cells):
    sc = "" if cov >= 0.95 else f" transform:scale({0.45 + 0.55 * cov:.2f});"
    tile_html.append(f'<i class="tl l{line}" style="left:{x:.1f}px; top:{y:.1f}px; --x:{-(c % 20) * TS}px; --y:{-(c // 20) * TS}px;{sc}"></i>')
# plus bars after "000"
p_cx = L + tw("000", NPX, NUM_W) + TRACK[NUM_W] * NPX + PLUS_ADV / 2
p_cy = n2_base - 0.36 * NPX
P_ARM, P_TH = 0.5 * NPX, 0.13 * NPX
# hero post: the tile shows the tight crop (x 62..337, y 65..340 of the 400 px aligned face, eye gap 110);
# in the framed canvas (eye gap 200, eyes centred on y 430) that square is:
KF = FE / 110
TIGHT = (FO / 2 + (62 - 200) * KF, FEY + (65 - 170) * KF, 275 * KF)
hero_size = TS * FO / TIGHT[2]
hero_l = hero_tile[0] - TS * TIGHT[0] / TIGHT[2]
hero_t = hero_tile[1] - TS * TIGHT[1] / TIGHT[2]
eye_x = hero_l + hero_size * 0.5
eye_y = hero_t + hero_size * FEY / FO
EYE_SCREEN = (540.0, 880.0)
Z0 = 1080 / hero_size                  # the hero fills the width at the start
hero_ids = BIG_IDS["hero"]
learn_cap = n2_base + 70
jo_cap = learn_cap + CAP * SUB_PX + 44
a_html = f"""
  <div id="A" class="clip full" {clip(0, 160, 2)}>
    <div id="Acam" class="full">
      <div id="Anum" class="full">
        <div id="Atl" class="full">{''.join(tile_html)}</div>
        <div class="pb" id="ph" style="left:{p_cx - P_ARM / 2:.1f}px; top:{p_cy - P_TH / 2:.1f}px; width:{P_ARM:.1f}px; height:{P_TH:.1f}px;"></div>
        <div class="pb" id="pv" style="left:{p_cx - P_TH / 2:.1f}px; top:{p_cy - P_ARM / 2:.1f}px; width:{P_TH:.1f}px; height:{P_ARM:.1f}px;"></div>
      </div>
      <div id="hero">{face_stack("h", hero_ids, hero_size, hero_l, hero_t)}</div>
    </div>
    <div class="vf" id="vfA"></div>
    <div class="t" id="a_learn" style="left:{L}px; top:{top_for_cap(learn_cap, SUB_PX):.1f}px; font-size:{SUB_PX}px; font-weight:500;"><span id="a_l1">{esc(show("learners"))}</span> <span id="a_l2" style="font-weight:900;">{esc(show("chose"))}</span></div>
    <div class="t" id="a_jo" style="left:{L}px; top:{top_for_cap(jo_cap, JO_PX):.1f}px; font-size:{JO_PX:.1f}px; font-weight:900; letter-spacing:-0.03em; color:{TEAL};">{esc(show("JAIN Online."))}</div>
  </div>"""

shuffle("h", BM.FACES["hero"], hero_ids)
J.append(f'tl.set("#Acam", {{transformOrigin: "{eye_x:.2f}px {eye_y:.2f}px", x: {EYE_SCREEN[0] - eye_x:.2f}, y: {EYE_SCREEN[1] - eye_y:.2f}, scale: {Z0:.4f}}}, 0);')
# viewfinder snaps on spaced changes
for f in BM.FACES["hero"]:
    if f in (0, 8, 16, 32, 40, 48):
        J.append(f'tl.fromTo("#vfA", {{scale: 1.08}}, {{immediateRender: false, scale: 1, duration: {D(4)}, ease: "power2.out"}}, {T(f)});')
# the pull-back: log-scale zoom from Z0 to 1, eye point drifting to its place in the number
J.append(f"""const zA = {{p: 0}};
tl.fromTo(zA, {{p: 0}}, {{immediateRender: false, p: 1, duration: {D(22)}, ease: "power3.inOut", onUpdate: () => {{
  const z = Math.pow({Z0:.4f}, 1 - zA.p), w = (z - 1) / ({Z0:.4f} - 1);
  gsap.set("#Acam", {{scale: z, x: {EYE_SCREEN[0] - eye_x:.2f} * w, y: {EYE_SCREEN[1] - eye_y:.2f} * w}});
  gsap.set("#hero", {{opacity: Math.max(0, Math.min(1, (z - 5) / 6))}});
}}}}, {T(64)});""")
J.append(f'tl.set("#Atl", {{opacity: 1}}, {T(64)});')
J.append(f'tl.to("#vfA", {{opacity: 0, scale: 0.6, duration: {D(6)}, ease: "power2.in"}}, {T(64)});')
J.append(f'tl.set(["#ph", "#pv"], {{opacity: 1}}, {T(80)});')
J.append(f'tl.fromTo(["#ph", "#pv"], {{scale: 2.2}}, {{immediateRender: false, scale: 1, duration: {D(7)}, ease: "expo.out"}}, {T(80)});')
for i, f in enumerate(BM.FACES["tiles"]):
    J.append(f'tl.set("#Atl", {{"--dx": "{-(3 + 7 * i) % 20 * TS}px", "--dy": "{-((2 + 3 * i) % CELL_ROWS) * TS}px"}}, {T(f)});')
for f in BM.FACES["tiles"]:
    J.append(f'tl.fromTo("#Anum", {{scale: 1.035}}, {{immediateRender: false, scale: 1, duration: {D(6)}, ease: "power2.out"}}, {T(f)});')
J.append(f'tl.set("#a_l1", {{opacity: 1}}, {T(96)});')
J.append(f'tl.fromTo("#a_l1", {{y: 40}}, {{immediateRender: false, y: 0, duration: {D(5)}, ease: "expo.out"}}, {T(96)});')
J.append(f'tl.set("#a_l2", {{opacity: 1}}, {T(104)});')
J.append(f'tl.fromTo("#a_l2", {{y: 40}}, {{immediateRender: false, y: 0, duration: {D(5)}, ease: "expo.out"}}, {T(104)});')
J.append(f'tl.set("#a_jo", {{opacity: 1}}, {T(112)});')
J.append(f'tl.fromTo("#a_jo", {{scale: 1.25}}, {{immediateRender: false, scale: 1, duration: {D(7)}, ease: "expo.out"}}, {T(112)});')
J.append(f'tl.to("#Anum", {{scale: 1.5, opacity: 0, duration: {D(8)}, ease: "power3.in"}}, {T(152)});')
J.append(f'tl.to(["#a_learn", "#a_jo"], {{x: -260, opacity: 0, duration: {D(7)}, ease: "power3.in"}}, {T(153)});')

# ================================================================ text screens (track 1)
screens = []      # (id, f0, f1, bg, inner_html, anim)


def word(id_, text, weight, px, cap_top, color, left=L, extra=""):
    ls = f" letter-spacing:{TRACK[weight]}em;" if TRACK[weight] else ""
    return (f'<div class="t" id="{id_}" style="left:{left:.1f}px; top:{top_for_cap(cap_top, px):.1f}px; font-size:{px:.1f}px; '
            f'font-weight:{weight};{ls} color:{color};{extra}">{esc(show(text))}</div>')


def stack(prefix, lines, center=890.0, color=WHITE, gap=0.32):
    """lines: (text, weight, maxpx); cap tops stacked, block centred on `center`."""
    sized = [(t, w, fit(t, w, m)) for t, w, m in lines]
    h = sum(CAP * px for _, _, px in sized) + sum(gap * px for _, _, px in sized[1:])
    cap = center - h / 2
    out, geo = [], []
    for i, (t, w, px) in enumerate(sized):
        if i:
            cap += gap * px
        out.append(word(f"{prefix}{i}", t, w, px, cap, color))
        geo.append((cap, px))
        cap += CAP * px
    return "".join(out), geo


def screen(id_, f0, f1, bg, lines, anim="slam", color=WHITE, center=890.0, extra="", gap=0.32):
    inner, geo = stack(f"{id_}_", lines, center, color, gap)
    screens.append((id_, f0, f1, bg, inner + extra, anim, len(lines)))
    return geo


def enter(id_, n, f, anim):
    ids = json.dumps([f"#{id_}_{i}" for i in range(n)])
    if anim == "slam":
        J.append(f'tl.fromTo({ids}, {{scale: 1.24, transformOrigin: "0% 60%"}}, {{immediateRender: false, scale: 1, duration: {D(7)}, ease: "expo.out"}}, {T(f)});')
    elif anim == "punch":
        J.append(f'tl.fromTo({ids}, {{scale: 0.78, transformOrigin: "0% 60%"}}, {{immediateRender: false, scale: 1, duration: {D(6)}, ease: "expo.out"}}, {T(f)});')
    elif anim == "slide":
        J.append(f'tl.fromTo({ids}, {{x: -180}}, {{immediateRender: false, x: 0, duration: {D(6)}, ease: "expo.out", stagger: {D(1)}}}, {T(f)});')
    elif anim == "rise":
        J.append(f'tl.fromTo({ids}, {{y: 90, opacity: 0}}, {{immediateRender: false, y: 0, opacity: 1, duration: {D(6)}, ease: "expo.out", stagger: {D(2)}}}, {T(f)});')
    elif anim == "drop":
        J.append(f'tl.fromTo({ids}, {{y: -140}}, {{immediateRender: false, y: 0, duration: {D(5)}, ease: "power4.out", stagger: {D(1)}}}, {T(f)});')
    if anim in ("slam", "punch", "drop"):        # stomp jolt
        for k, (jx, jy) in enumerate(((10, -7), (-8, 6), (5, -3), (0, 0))):
            J.append(f'tl.set("#{id_}_j", {{x: {jx}, y: {jy}}}, {T(f + k)});')


# ---- b: Welcome / to the / Batch of
screen("b1", 160, 168, WHITE, [("Welcome", 900, 300)], "slam", NAVY)
screen("b2", 168, 176, NAVY, [("to the", 900, 300)], "punch", WHITE)
screen("b3", 176, 184, TEAL, [("Batch of", 900, 300)], "slam", NAVY)

# ---- b: shutter burst (f184-192) on its own track below
flash_b = BIG_IDS["flash_b"]

# ---- b: 20 / 26. stencil over the scroll recording
YPX = min(fit("20", 900, 600), fit("26.", 900, 600))
YCAP = CAP * YPX
YGAP = 0.12 * YPX
y1_cap = 890 - (2 * YCAP + YGAP) / 2
y1_base, y2_base = y1_cap + YCAP, y1_cap + 2 * YCAP + YGAP
KP = 2                                   # stencil drawn at 2x for the zooms
ymask = raster([("20", 900, YPX, L, y1_base), ("26.", 900, YPX, L, y2_base)], FW, FH, KP)
show("2026.")
period = bbox(ymask, FW * KP, (L + tw("26", YPX, 900)) * KP, (y2_base - 0.4 * YPX) * KP, (L + tw("26.", YPX, 900) + 20) * KP, (y2_base + 10) * KP)
px0, py0, px1, py1 = (v / KP for v in period)
plate_png = A / "img" / "plate2026.png"
navy_hex = NAVY.lstrip("#")
# navy everywhere, alpha cut where the letters are
with tempfile.TemporaryDirectory() as td:
    mp = pathlib.Path(td) / "m.gray"
    mp.write_bytes(ymask)
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", f"color=c=0x{navy_hex}:s={FW * KP}x{FH * KP}",
                    "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{FW * KP}x{FH * KP}", "-i", str(mp),
                    "-filter_complex", "[1]negate[a];[0]format=rgba[c];[c][a]alphamerge", "-frames:v", "1", str(plate_png)], check=True)
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", f"color=c=0x{TEAL.lstrip('#')}:s={FW * KP}x{FH * KP}",
                    "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{FW * KP}x{FH * KP}", "-i", str(mp),
                    "-filter_complex", "[0]format=rgba[c];[c][1]alphamerge", "-frames:v", "1", str(A / "img" / "teal2026.png")], check=True)
b_html = f"""
  <video id="scroll" class="clip" src="assets/footage/scroll.mp4" muted playsinline {clip(192, 288, 3)}
         style="position:absolute; left:0; top:-66px; width:1080px; height:2052px;"></video>
  <div id="B26" class="clip full" {clip(192, 288, 4)}>
    <div id="plate" class="full" style="transform-origin:{L + tw("26.", YPX, 900) / 2:.1f}px 890px;">
      <img src="assets/img/plate2026.png" alt="" style="position:absolute; left:0; top:0; width:{FW}px; height:{FH}px;">
      <img id="teal26" src="assets/img/teal2026.png" alt="" style="position:absolute; left:0; top:0; width:{FW}px; height:{FH}px; opacity:0;">
      <div id="cover26" style="position:absolute; left:0; top:{y2_base - YCAP - 30:.1f}px; width:{FW}px; height:{YCAP + 60:.1f}px; background:{NAVY};"></div>
      <div id="dot" style="position:absolute; left:{px0 - 1:.1f}px; top:{py0 - 1:.1f}px; width:{px1 - px0 + 2:.1f}px; height:{py1 - py0 + 2:.1f}px; background:{TEAL}; opacity:0;"></div>
    </div>
  </div>"""
J.append(f'tl.fromTo("#plate", {{scale: 1.18}}, {{immediateRender: false, scale: 1, duration: {D(7)}, ease: "expo.out"}}, {T(192)});')
J.append(f'tl.set("#cover26", {{opacity: 0}}, {T(200)});')
J.append(f'tl.fromTo("#plate", {{y: -26}}, {{immediateRender: false, y: 0, duration: {D(6)}, ease: "expo.out"}}, {T(200)});')
J.append(f'tl.set("#dot", {{opacity: 1}}, {T(208)});')
J.append(f'tl.fromTo("#dot", {{scale: 2.4}}, {{immediateRender: false, scale: 1, duration: {D(6)}, ease: "expo.out"}}, {T(208)});')
for f in (224, 232, 240):
    J.append(f'tl.fromTo("#plate", {{scale: 1.03}}, {{immediateRender: false, scale: 1, duration: {D(5)}, ease: "power2.out"}}, {T(f)});')
for f, s in ((256, 1.1), (264, 1.22), (272, 1.36), (280, 1.5)):
    J.append(f'tl.to("#plate", {{scale: {s}, duration: {D(5)}, ease: "expo.out"}}, {T(f)});')
J.append(f'tl.set("#teal26", {{opacity: 1}}, {T(272)});')
J.append(f'tl.set("#teal26", {{opacity: 0}}, {T(280)});')

# ================================================================ c: window, counter, wall
WIN = 1080.0
WIN_T = 40.0
c_ids = BIG_IDS["win"]
eyes_c = WIN_T + WIN * FEY / FO
band = 1190.0
CNT_PX = fit("11,000+", 900, 230)
amb_px, yr_px = fit("ambitions", 900, 120), 96
c_lines = []
for i, (t, w, mpx) in enumerate([("We are", 900, 200), ("proud", 900, 220), ("to nurture", 900, 200)]):
    px = fit(t, w, mpx)
    c_lines.append(word(f"c_w{i}", t, w, px, band, WHITE, extra=" opacity:0;"))
cnt_base = band + CAP * CNT_PX
show("11,000+")
amb_cap = cnt_base + 78
yr_cap = amb_cap + CAP * amb_px + 34
c_html = f"""
  <div id="C" class="clip full" {clip(288, 416, 6)}>
    <div class="full" style="background:{NAVY};"></div>
    {face_stack("c", c_ids, WIN, 0, WIN_T)}
    <div class="vf" id="vfC" style="top:{eyes_c - 150:.1f}px;"></div>
    <div class="shade" style="top:{WIN_T + WIN - 260:.1f}px; height:260px; background:linear-gradient(180deg, rgba(7,28,91,0) 0%, {NAVY} 100%);"></div>
    {''.join(c_lines)}
    <div class="t" id="c_cnt" style="left:{L}px; top:{top_for_cap(band, CNT_PX):.1f}px; font-size:{CNT_PX:.1f}px; font-weight:900; letter-spacing:-0.03em; opacity:0;"><span id="c_num">0</span><span id="c_plus" style="color:{TEAL}; opacity:0;">+</span></div>
    {word("c_amb", "ambitions", 900, amb_px, amb_cap, WHITE, extra=" opacity:0;")}
    {word("c_yr", "this year.", 500, yr_px, yr_cap, WHITE, extra=" opacity:0;")}
  </div>"""
shuffle("c", BM.FACES["win"], c_ids)
for f in BM.FACES["win"]:
    if f < 320 or f >= 384:
        J.append(f'tl.fromTo("#vfC", {{scale: 1.08}}, {{immediateRender: false, scale: 1, duration: {D(4)}, ease: "power2.out"}}, {T(f)});')
for i, (f0, f1) in enumerate(((288, 296), (296, 304), (304, 320))):
    J.append(f'tl.set("#c_w{i}", {{opacity: 1}}, {T(f0)});')
    J.append(f'tl.fromTo("#c_w{i}", {{scale: 1.2, transformOrigin: "0% 60%"}}, {{immediateRender: false, scale: 1, duration: {D(6)}, ease: "expo.out"}}, {T(f0)});')
    J.append(f'tl.set("#c_w{i}", {{opacity: 0}}, {T(f1)});')
c0, c1 = BM.COUNTER
J.append(f'tl.set("#c_cnt", {{opacity: 1}}, {T(c0)});')
J.append(f"""const cA = {{p: 0}};
tl.fromTo(cA, {{p: 0}}, {{immediateRender: false, p: 1, duration: {D(c1 - c0)}, ease: "power2.in", onUpdate: () => {{
  document.getElementById("c_num").textContent = Math.round(11000 * cA.p).toLocaleString("en-US");
}}}}, {T(c0)});""")
J.append(f'tl.set("#c_plus", {{opacity: 1}}, {T(c1)});')
J.append(f'tl.fromTo("#c_cnt", {{scale: 1.14, transformOrigin: "0% 60%"}}, {{immediateRender: false, scale: 1, duration: {D(7)}, ease: "expo.out"}}, {T(c1)});')
J.append(f'tl.set("#c_amb", {{opacity: 1}}, {T(392)});')
J.append(f'tl.fromTo("#c_amb", {{x: -160}}, {{immediateRender: false, x: 0, duration: {D(6)}, ease: "expo.out"}}, {T(392)});')
J.append(f'tl.set("#c_yr", {{opacity: 1}}, {T(400)});')
J.append(f'tl.fromTo("#c_yr", {{y: 60}}, {{immediateRender: false, y: 0, duration: {D(6)}, ease: "expo.out"}}, {T(400)});')

# ---- the wall of 28 (c end, d)
GD = 270.0
GCOLS, GROWS = 4, 7
G_T = (FH - GROWS * GD) / 2
TARGET = (1, 3)                          # col, row of the cell that becomes "each one."
cells = []
for r in range(GROWS):
    for c in range(GCOLS):
        cells.append(f'<div class="gc" id="g{r * GCOLS + c}" style="left:{c * GD:.0f}px; top:{G_T + r * GD:.1f}px; width:{GD:.0f}px; height:{GD:.0f}px; {sheet_bg(GD)}"></div>')
NG = GCOLS * GROWS
tgt = TARGET[1] * GCOLS + TARGET[0]
gframes = BM.FACES["grid"]
for n, f in enumerate(gframes):
    seq = [pool[(n * NG + j) % len(pool)] for j in range(NG)]
    if n == len(gframes) - 1:
        seq[tgt] = HOLD_FACE
    for j in range(NG):
        J.append(f'tl.set("#g{j}", {{backgroundPosition: "{sheet_pos(seq[j], GD)}"}}, {T(f)});')
tcx, tcy = TARGET[0] * GD + GD / 2, G_T + TARGET[1] * GD + GD / 2
ZG = 3.0
d_html_grid = f"""
  <div id="G" class="clip full" {clip(416, 640, 5)}>
    <div id="Gcam" class="full" style="transform-origin:{tcx:.1f}px {tcy:.1f}px;">{''.join(cells)}
      <img id="hold" src="assets/framed/f{HOLD_FACE:03d}.jpg" alt="" style="position:absolute; left:{TARGET[0] * GD:.0f}px; top:{G_T + TARGET[1] * GD:.1f}px; width:{GD:.0f}px; height:{GD:.0f}px; opacity:0;"></div>
    <div id="Gdim" class="full" style="background:{INK}; opacity:0;"></div>
    <div class="shade" id="Gshade" style="top:1120px; height:800px; opacity:0;"></div>
  </div>"""
J.append(f'tl.fromTo("#Gcam", {{scale: 0.55}}, {{immediateRender: false, scale: 1, duration: {D(8)}, ease: "expo.out"}}, {T(416)});')
J.append(f'tl.set("#Gdim", {{opacity: 0.62}}, {T(448)});')
J.append(f'tl.set("#hold", {{opacity: 1}}, {T(560)});')
J.append(f'tl.set("#Gdim", {{opacity: 0.55}}, {T(544)});')
J.append(f'tl.to("#Gdim", {{opacity: 0, duration: {D(10)}, ease: "power2.out"}}, {T(560)});')
others = json.dumps([f"#g{j}" for j in range(NG) if j != tgt])
J.append(f'tl.to({others}, {{opacity: 0.16, duration: {D(12)}, ease: "power2.inOut"}}, {T(560)});')
J.append(f'tl.to("#Gcam", {{scale: {ZG}, x: {540 - tcx:.1f}, y: {760 - tcy:.1f}, duration: {D(16)}, ease: "expo.inOut"}}, {T(560)});')
J.append(f'tl.to("#Gcam", {{scale: {ZG * 1.07:.3f}, duration: {D(48)}, ease: "none"}}, {T(576)});')
J.append(f'tl.to("#Gshade", {{opacity: 1, duration: {D(10)}}}, {T(560)});')
J.append(f'tl.to("#Gcam", {{opacity: 0, duration: {D(8)}, ease: "power2.in"}}, {T(630)});')

# ---- d copy
screen("d1", 448, 464, None, [("But even", 900, 230)], "rise")
screen("d2", 464, 480, None, [("more than that,", 900, 200)], "slide")
screen("d3", 480, 496, None, [("we are proud", 900, 200)], "rise")
screen("d4", 496, 512, None, [("to carry", 900, 240)], "slam")
TR_PX = fit("trust", 900, 380)
the_px = 96
tr_cap = 890 - (CAP * the_px + 40 + CAP * TR_PX) / 2 + CAP * the_px + 40
trust_html = (word("d5_0", "the", 500, the_px, tr_cap - 40 - CAP * the_px, WHITE)
              + f'<div class="t mos" id="d5_1" style="left:{L}px; top:{top_for_cap(tr_cap, TR_PX):.1f}px; font-size:{TR_PX:.1f}px; '
                f'font-weight:900; letter-spacing:-0.03em; opacity:0;">{esc(show("trust"))}</div>')
screens.append(("d5", 512, 544, NAVY, trust_html, "rise1", 1))
J.append(f'tl.set("#d5_1", {{opacity: 1}}, {T(520)});')
J.append(f'tl.fromTo("#d5_1", {{scale: 1.3, transformOrigin: "0% 60%"}}, {{immediateRender: false, scale: 1, duration: {D(8)}, ease: "expo.out"}}, {T(520)});')
J.append(f'tl.fromTo("#d5_1", {{backgroundPosition: "0px 0px"}}, {{immediateRender: false, backgroundPosition: "-160px -60px", duration: {D(24)}, ease: "none"}}, {T(520)});')
screen("d6", 544, 560, None, [("behind", 900, 240)], "punch")
screen("d7", 560, 640, None, [("each one.", 900, 170)], "rise", center=1420)

# ================================================================ e: the peak
screen("e1", 640, 648, WHITE, [("Because", 900, 300)], "slam", NAVY)
flash_e = BIG_IDS["flash_e"]
screen("e2", 648, 656, None, [("every learner", 900, 200)], "punch", center=1470)
screen("e3", 656, 672, TEAL, [("who chooses", 900, 220)], "slam", NAVY)
mos_bg = (f'<div class="full" id="e4_m" style="background:url(\'assets/img/face_mosaic.jpg\') 0px 0px / auto 1920px repeat-x;"></div>'
          f'<div class="full" style="background:{INK}; opacity:0.58;"></div>')
screens.append(("e4m", 672, 688, NAVY, mos_bg, None, 0))
J.append(f'tl.fromTo("#e4_m", {{backgroundPosition: "0px 0px"}}, {{immediateRender: false, backgroundPosition: "-420px 0px", duration: {D(16)}, ease: "none"}}, {T(672)});')
screen("e4", 672, 688, None, [("JAIN Online", 900, 220)], "slam")
screen("e5", 688, 704, WHITE, [("brings us", 900, 240)], "punch", NAVY)
screen("e6", 704, 712, None, [("one step", 900, 220)], "drop", center=470)
screen("e7", 712, 720, None, [("closer", 900, 260)], "drop", center=470)
screen("e8", 720, 736, None, [("to building", 900, 220)], "slam", center=470)
screen("e9", 736, 752, None, [("a more skilled,", 900, 200)], "slide", center=470)
screen("e10", 752, 768, None, [("future-ready", 900, 220)], "slam", center=470)
IN_PX = fit("India.", 900, 420)
india_html = (f'<div class="t mos" id="e11_0" style="left:{L}px; top:{top_for_cap(890 - CAP * IN_PX / 2, IN_PX):.1f}px; '
              f'font-size:{IN_PX:.1f}px; font-weight:900; letter-spacing:-0.03em;">{esc(show("India."))}</div>')
screens.append(("e11", 768, 832, NAVY, india_html, "india", 1))
J.append(f'tl.fromTo("#e11_0", {{scale: 1.3, transformOrigin: "0% 60%"}}, {{immediateRender: false, scale: 1, duration: {D(8)}, ease: "expo.out"}}, {T(768)});')
for i, f in enumerate(BM.FACES["mosaic"]):
    J.append(f'tl.set("#e11_0", {{backgroundPosition: "{-48 * (3 + 5 * i)}px {-48 * (1 + 2 * i)}px"}}, {T(f)});')
    J.append(f'tl.fromTo("#e11_0", {{scale: 1.05}}, {{immediateRender: false, scale: 1, duration: {D(6)}, ease: "power2.out"}}, {T(f)});')
J.append(f'tl.to("#e11_0", {{scale: 1.6, opacity: 0, duration: {D(8)}, ease: "power3.in"}}, {T(824)});')

# ---- bricks: one step closer to building
BK = 270.0
bricks = []
b_ids = faces_for(16, 55)
for n, f in enumerate(BM.BRICKS):
    r, c = 3 - n // 4, n % 4
    bricks.append(f'<div class="bk" id="bk{n}" style="left:{c * BK:.0f}px; top:{FH - (4 - r) * BK:.0f}px; width:{BK:.0f}px; height:{BK:.0f}px; '
                  f'{sheet_bg(BK)} background-position:{sheet_pos(b_ids[n], BK)};"></div>')
    J.append(f'tl.fromTo("#bk{n}", {{y: -260, opacity: 0}}, {{immediateRender: false, y: 0, opacity: 1, duration: {D(3)}, ease: "power3.in"}}, {T(f - 3)});')
J.append(f'tl.to("#Wdim", {{opacity: 0.55, duration: {D(6)}}}, {T(736)});')
w_html = f"""
  <div id="W" class="clip full" {clip(704, 768, 7)}>
    <div class="full" style="background:{NAVY};"></div>
    {''.join(bricks)}
    <div id="Wdim" class="full" style="background:{INK}; opacity:0;"></div>
  </div>"""

# ---- shutter bursts (b and e) on track 6 with C
fl_html = ""
for nm, (f0, f1), ids in (("fb", (184, 192), flash_b), ("fe", (648, 656), flash_e)):
    frs = [f for f in BM.FACES["flash"] if f0 <= f < f1]
    fl_html += f"""
  <div id="{nm}" class="clip full" {clip(f0, f1, 6)}>
    <div class="full" style="background:{NAVY};"></div>
    {face_stack(nm, ids, 1080, 0, EYE_SCREEN[1] - 1080 * FEY / FO)}
    <div class="vf" style="top:{EYE_SCREEN[1] - 150:.0f}px;"></div>
    <div class="shade" style="top:1180px; height:740px;"></div>
  </div>"""
    shuffle(nm, frs, ids)

# ================================================================ f: identity
LOGO_W = COLW
LK = LOGO_W / 1624
LOGO_H = 540 * LK
LOGO_T = 560.0
YR_PX = 120
yr_cap = LOGO_T + LOGO_H + 70
TG_PX = 84
tg1_cap = yr_cap + CAP * YR_PX + 76
tg2_cap = tg1_cap + CAP * TG_PX + 0.42 * TG_PX
JO_W, JO_T = 330, 1330
show("Deekshaarambh")
DESC_MASK = "clip-path: polygon(0% 0%, 100% 0%, 100% 100%, 61.6% 100%, 61.6% 68.9%, 0% 68.9%);"


def tag(id_, a, b, cap):
    return (f'<div class="t" id="{id_}" style="left:{L}px; top:{top_for_cap(cap, TG_PX):.1f}px; font-size:{TG_PX}px; opacity:0;">'
            f'<span style="font-weight:500;">{esc(a)}</span> <span style="font-weight:900; letter-spacing:-0.02em;">{esc(b)}</span></div>')


f_html = f"""
  <div id="F" class="clip full" {clip(832, TOTAL_F, 8)}>
    <div class="full" style="background:{NAVY};"></div>
    <div id="logo-mask" style="position:absolute; left:{L}px; top:{LOGO_T}px; width:{LOGO_W:.1f}px; height:{LOGO_H:.2f}px; clip-path: inset(0px {LOGO_W:.1f}px 0px 0px);">
      <img id="logo" src="assets/brand/deekshaarambh.png" alt="" style="position:absolute; left:0; top:0; width:{LOGO_W:.1f}px; height:{LOGO_H:.2f}px; {DESC_MASK}">
    </div>
    {word("f_yr", "2026", 900, YR_PX, yr_cap, WHITE, extra=" opacity:0;")}
    {tag("f_t1", show("Your"), show("ambition."), tg1_cap)}
    {tag("f_t2", show("Our"), show("commitment."), tg2_cap)}
    <img id="jo" src="assets/brand/jain-online.png" alt="" style="position:absolute; left:{L}px; top:{JO_T}px; width:{JO_W}px; opacity:0;">
  </div>"""
J.append(f'tl.to("#logo-mask", {{clipPath: "inset(0px 0px 0px 0px)", duration: {D(12)}, ease: "expo.out"}}, {T(832)});')
J.append(f'tl.set("#f_yr", {{opacity: 1}}, {T(848)});')
J.append(f'tl.fromTo("#f_yr", {{y: 50}}, {{immediateRender: false, y: 0, duration: {D(6)}, ease: "expo.out"}}, {T(848)});')
J.append(f'tl.set("#f_t1", {{opacity: 1}}, {T(864)});')
J.append(f'tl.fromTo("#f_t1", {{x: -120}}, {{immediateRender: false, x: 0, duration: {D(7)}, ease: "expo.out"}}, {T(864)});')
J.append(f'tl.set("#f_t2", {{opacity: 1}}, {T(880)});')
J.append(f'tl.fromTo("#f_t2", {{x: 120}}, {{immediateRender: false, x: 0, duration: {D(7)}, ease: "expo.out"}}, {T(880)});')
J.append(f'tl.fromTo("#jo", {{opacity: 0, y: 14}}, {{immediateRender: false, opacity: 1, y: 0, duration: {D(4)}, ease: "power2.out"}}, {T(896)});')

# ================================================================ assemble screens
s_html = []
last_end = {}
for id_, f0, f1, bg, inner, anim, n in sorted(screens, key=lambda s: s[1]):
    track = 1 if bg is not None else 9
    if last_end.get(track, 0) > f0:
        track = 10
    last_end[track] = f1
    bgdiv = f'<div class="full" style="background:{bg};"></div>' if bg else ""
    s_html.append(f'\n  <div id="{id_}" class="clip full" {clip(f0, f1, track)}>{bgdiv}<div id="{id_}_j" class="full">{inner}</div></div>')
    if anim and anim not in ("rise1", "india"):
        enter(id_, n, f0, anim)

# ---- copy check: shown strings, in order, against the script
seq_expected = " ".join(SCRIPT).split()
seq_got = " ".join(SHOWN).split()
if seq_got != seq_expected:
    raise SystemExit("on-screen copy does not match the locked script:\n  shown : " + " ".join(seq_got)
                     + "\n  script: " + " ".join(seq_expected))

# ================================================================ page
grain_end = BM.STILL_F
css = f"""
@font-face {{ font-family: 'Montserrat'; font-weight: 500; src: url('assets/fonts/Montserrat-500.ttf'); }}
@font-face {{ font-family: 'Montserrat'; font-weight: 800; src: url('assets/fonts/Montserrat-800.ttf'); }}
@font-face {{ font-family: 'Montserrat'; font-weight: 900; src: url('assets/fonts/Montserrat-900.ttf'); }}
#stage {{ position: relative; width: {FW}px; height: {FH}px; overflow: hidden; background: {NAVY};
  font-family: 'Montserrat', sans-serif; color: {WHITE}; }}
.full {{ position: absolute; left: 0; top: 0; width: {FW}px; height: {FH}px; }}
.t {{ position: absolute; white-space: nowrap; line-height: 1; }}
#A {{ background: {NAVY}; }}
#Atl {{ --dx: 0px; --dy: 0px; opacity: 0; }}
.tl {{ position: absolute; width: {TS}px; height: {TS}px; border-radius: 3px;
  background-image: url('assets/img/face_cells.jpg'); background-size: {20 * TS}px {CELL_ROWS * TS}px; background-repeat: repeat;
  background-position: calc(var(--x) + var(--dx)) calc(var(--y) + var(--dy)); }}
.pb {{ position: absolute; background: {TEAL}; opacity: 0; }}
.fs {{ position: absolute; opacity: 0; }}
#a_l1, #a_l2, #a_jo {{ opacity: 0; }}
.vf {{ position: absolute; left: 240px; width: 600px; height: 300px; top: {EYE_SCREEN[1] - 150:.0f}px;
  background:
    linear-gradient({WHITE},{WHITE}) left top / 70px 6px no-repeat, linear-gradient({WHITE},{WHITE}) left top / 6px 70px no-repeat,
    linear-gradient({WHITE},{WHITE}) right top / 70px 6px no-repeat, linear-gradient({WHITE},{WHITE}) right top / 6px 70px no-repeat,
    linear-gradient({WHITE},{WHITE}) left bottom / 70px 6px no-repeat, linear-gradient({WHITE},{WHITE}) left bottom / 6px 70px no-repeat,
    linear-gradient({WHITE},{WHITE}) right bottom / 70px 6px no-repeat, linear-gradient({WHITE},{WHITE}) right bottom / 6px 70px no-repeat;
  opacity: 0.9; }}
.shade {{ position: absolute; left: 0; width: {FW}px; background: linear-gradient(180deg, rgba(4,16,58,0) 0%, rgba(4,16,58,0.92) 55%, {INK} 100%); }}
.gc, .bk {{ position: absolute; background-repeat: no-repeat; }}
.gc {{ box-shadow: inset 0 0 0 3px {NAVY}; }}
.bk {{ opacity: 0; box-shadow: inset 0 0 0 4px {NAVY}; }}
.mos {{ color: transparent; background: url('assets/img/face_mosaic.jpg') 0px 0px / 1008px 588px repeat;
  -webkit-background-clip: text; background-clip: text; }}
#grain {{ background-image: url('assets/img/grain.png'); background-size: 256px 256px; mix-blend-mode: overlay; opacity: 0.07; }}
"""

js = "\n".join([
    "const tl = gsap.timeline({ paused: true });",
    f'tl.fromTo("#grain", {{backgroundPosition: "0px 0px"}}, {{backgroundPosition: "{grain_end * 164}px {grain_end * 105}px", duration: {D(grain_end)}, ease: "steps({grain_end // 2})"}}, 0);',
] + J + [
    f'tl.set({{}}, {{}}, {D(TOTAL_F)});',
    "window.__timelines = window.__timelines || {};",
    "window.__timelines.reel = tl;",
])

body = f"""
  <div id="bg" class="clip full" {clip(0, TOTAL_F, 0)} style="background:{NAVY};"></div>
{a_html}
{b_html}
{c_html}
{fl_html}
{d_html_grid}
{w_html}
{''.join(s_html)}
{f_html}
  <div id="grain" class="clip full" {clip(0, TOTAL_F, 11)}></div>
  <audio id="score" class="clip" src="assets/audio/score.wav" {clip(0, TOTAL_F, 12)} data-volume="1"></audio>
"""

page = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Deekshaarambh 2026</title></head>
<body>
<div id="stage" data-composition-id="reel" data-start="0" data-duration="{BM.TOTAL:.3f}"
     data-width="{FW}" data-height="{FH}" data-fps="{FPS}">
  <style>{css}</style>
{body}
  <script src="assets/gsap.min.js"></script>
  <script>
{js}
  </script>
</div>
</body>
</html>
"""
(project / "index.html").write_text(page, encoding="utf-8")
print(f"composed {BM.TOTAL:.0f}s @ {BM.BPM} BPM: {len(tiles)} face tiles (number {NPX:.0f}px), 20/26. at {YPX:.0f}px, "
      f"{len(BM.clicks())} shutter cuts, {len(J)} timeline entries; script check passed")
