#!/usr/bin/env python3
"""Compose the Deekshaarambh 2026 stomp piece (32 s, 1080x1920@30) into index.html.

Usage: motion/deekshaarambh-2026-stomp/compose.py --project motion/deekshaarambh-2026-stomp/project
       (run faces_prep.py, prep_assets.py and make_score.py into the same project first)

Two zones, so the eye always knows where to look:

  visual zone  y 220-1080: the Deekshaarambh post frame, standing still while
               the learners' photos change inside it (eyes kept on one
               point), the number made of faces, "2026." with the scroll
               recording inside it, the wall of posts
  text zone    one left-aligned block, cap tops from y 1150, one type size,
               ending above y 1500 (Instagram's caption area). Words appear in
               place on the stomps and claps (a short fade and a 16 px rise),
               nothing slides, slams or shakes, and every phrase holds for
               about a second

Cut to beatmap.py (112.5 BPM, a beat every 16 frames, stomp-stomp-clap):

  intro   the post frame; the photo inside it changes on every stomp and
          clap with a shutter click, then bursts
  a       the camera pulls back and that face is one tile of "11,000+": crisp
          letterforms with the faces packed inside them; learners chose /
          JAIN Online.
  b       Welcome to the / Batch of; a shutter burst; "20 / 26." with the
          scroll recording playing inside the letters; a teal flash on the clap
  c       We are proud / to nurture; the shutter speeds up to every frame while
          the counter races to 11,000+; ambitions / this year.; the window
          becomes a wall of 16 posts
  d       the wall slows down under the breakdown; the trust (filled with
          faces); behind / each one. as the camera finds one post
  e       the peak: phrase cards on the beat over a burst and a drifting
          mosaic; the map of India fills with the learners' photos band by
          band, south to north, for "one step closer to building", and its
          outline lands with India.
  f       the authentic artwork revealed by one clean mask; 2026; the tagline;
          JAIN Online; nothing moves after 30.0 s

Behind everything a slow navy aurora drifts with a faint field of the posts.
Every displayed string is checked against the locked script before writing.
The number's mask and the "2026." masks are rasterized here with ffmpeg
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
for need in ("brand/deekshaarambh.png", "brand/jain-online.png", "footage/scroll.mp4", "img/framed_sheet.jpg", "img/frame.png",
             "img/face_cells.jpg", "img/face_mosaic.jpg", "img/grain.png", "fonts/Montserrat-500.ttf",
             "fonts/Montserrat-800.ttf", "fonts/Montserrat-900.ttf", "audio/score.wav", "gsap.min.js"):
    if not (A / need).is_file():
        raise SystemExit(f"missing assets/{need}: run faces_prep.py / prep_assets.py / make_score.py into {project} first")
FACES = json.loads((HERE / "faces.json").read_text(encoding="utf-8-sig"))
if "post_frame" not in FACES:
    raise SystemExit("faces.json has no post frame: run faces_prep.py --images on the learners' posts")
ORDER = FACES["order"]
BIG = FACES["big"]                   # the best-placed faces first: the large windows
PF = FACES["post_frame"]
FO = PF["canvas"]                    # rebuilt posts (assets/framed) and the frame are FO px squares
WB = PF["window"]                    # the frame's photo window; assets/inner/ holds each photo cut to it
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
esc = html.escape
HOLD_FACE, HERO_LAST = FACES["hold"], FACES["hero"]

# the two zones
VZ0, VZ1 = 220.0, 1080.0             # visual zone
VC = (VZ0 + VZ1) / 2                 # 650
WIN = VZ1 - VZ0                      # 860: the post frame and the wall fill the zone
WIN_L = (FW - WIN) / 2               # 110
WIN_T = VZ0
EYE = (WIN_L + PF["eye"][0] * WIN / FO, WIN_T + PF["eye"][1] * WIN / FO)   # where the photos' eyes sit
EGAP = PF["gap"] * WIN / FO
TZ0 = 1150.0                         # text zone: first cap top
TZ_MAX = 1500.0                      # last baseline must stay above this
TXT_W = 800                          # one weight for the copy

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
    """Every photo change in the post frame gets a face from BIG; the cuts that stay up longest get the
    best-placed faces, 1-frame burst cuts get what is left. Returns {layer: [face per change]}."""
    ends = {"hero": 64, "win": 416, "flash_b": 192, "flash_e": 672}
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
    """one post frame standing still over stacked photos cut to its window (all hidden; sets reveal
    one at a time), the frame a size px square at left, top"""
    q = size / FO
    uniq = list(dict.fromkeys(ids))
    return "".join(f'<img class="fs" id="{prefix}{k}" src="assets/inner/f{k:03d}.jpg" alt="" '
                   f'style="left:{left + WB[0] * q:.2f}px; top:{top + WB[1] * q:.2f}px; '
                   f'width:{(WB[2] - WB[0]) * q:.2f}px; height:{(WB[3] - WB[1]) * q:.2f}px;">' for k in uniq) + \
        f'<img class="pf" src="assets/img/frame.png" alt="" style="left:{left:.2f}px; top:{top:.2f}px; width:{size:.2f}px; height:{size:.2f}px;">'


J = []          # timeline script lines


def shuffle(prefix, frames, ids):
    prev = None
    for f, k in zip(frames, ids):
        if prev is not None and prev != k:
            J.append(f'tl.set("#{prefix}{prev}", {{opacity: 0}}, {T(f)});')
        J.append(f'tl.set("#{prefix}{k}", {{opacity: 1}}, {T(f)});')
        prev = k
    return prev


def window(id_, f0, f1, track, frames, ids, extra=""):
    """the post frame in the visual zone, the photos changing inside it, with the viewfinder"""
    shuffle(id_, frames, ids)
    return (f'\n  <div id="{id_}" class="clip full" {clip(f0, f1, track)}>'
            f'{face_stack(id_, ids, WIN, WIN_L, WIN_T)}<div class="vf"></div>{extra}</div>')


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


def mask_png(buf, w, h, path, color="white"):
    """gray ink buffer -> PNG of `color` with the ink as alpha (a CSS mask, or coloured letters)"""
    with tempfile.TemporaryDirectory() as td:
        mp = pathlib.Path(td) / "m.gray"
        mp.write_bytes(buf)
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-i", str(mp),
                        "-filter_complex", "[0]format=rgba[c];[c][1]alphamerge", "-frames:v", "1", str(path)], check=True)


def bbox(buf, w, x0, y0, x1, y1, th=128):
    xs, ys = [], []
    for y in range(int(y0), int(y1)):
        row = buf[y * w:(y + 1) * w]
        for x in range(int(x0), int(x1)):
            if row[x] >= th:
                xs.append(x)
                ys.append(y)
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1) if xs else None


def coverage(buf, w, x, y, s, k):
    tot = 0
    for yy in range(int(y * k), int((y + s) * k)):
        tot += sum(buf[yy * w + int(x * k):yy * w + int((x + s) * k)])
    return tot / (255 * (s * k) ** 2)


# ---------------------------------------------------------------- the text zone
cards = []            # (id, f0, f1, html)
TXT_PX = 104.0


def card(id_, f0, f1, lines):
    """lines: [{"px": size or None, "words": [(text, frame, cls)]}]. Words sit in their final
    places from the start (hidden) and fade up in place; the card fades out over 4 frames."""
    out, cap = [], TZ0
    prev_px = None
    for i, ln in enumerate(lines):
        px = ln.get("px") or TXT_PX
        weight = ln.get("weight", TXT_W)
        text = " ".join(t for t, _, _ in ln["words"])
        if tw(text, px, weight) > COLW + 0.5:
            raise SystemExit(f"text zone line too wide: {text!r} at {px:.0f}px = {tw(text, px, weight):.0f}px")
        if i:
            cap += 0.42 * min(prev_px, px)
        spans = []
        for j, (t, f, cls) in enumerate(ln["words"]):
            wid = f"{id_}w{i}{j}"
            spans.append(f'<span class="w {cls}" id="{wid}">{esc(show(t))}</span>')
            J.append(f'tl.fromTo("#{wid}", {{opacity: 0, y: 16}}, {{immediateRender: false, opacity: 1, y: 0, '
                     f'duration: {D(7)}, ease: "power2.out"}}, {T(f)});')
        ls = f" letter-spacing:{TRACK[weight]}em;" if TRACK[weight] else ""
        out.append(f'<div class="ln" style="top:{top_for_cap(cap, px):.1f}px; font-size:{px:.1f}px; font-weight:{weight};{ls}">'
                   + " ".join(spans) + "</div>")
        cap += CAP * px
        prev_px = px
    if cap > TZ_MAX:
        raise SystemExit(f"card {id_} runs to y {cap:.0f}, below the {TZ_MAX:.0f} limit")
    J.append(f'tl.to("#{id_}_in", {{opacity: 0, duration: {D(4)}, ease: "power1.in"}}, {T(f1 - 4)});')
    cards.append((id_, f0, f1, f'<div id="{id_}_in" class="full">{"".join(out)}</div>'))


def W(text, frame, cls=""):
    return (text, frame, cls)


# every normal line in the piece shares one size: the largest that fits the widest one
NORMAL_LINES = ["learners chose", "JAIN Online.", "Welcome to the", "Batch of", "We are proud", "to nurture",
                "ambitions", "this year.", "But even", "more than that,", "we are proud", "to carry", "the",
                "behind", "each one.", "Because", "every learner", "who chooses", "JAIN Online", "brings us",
                "one step closer", "to building", "a more skilled,", "future-ready"]
TXT_PX = min(112.0, min(fit(t, TXT_W, 200) for t in NORMAL_LINES))

# ================================================================ background: a slow aurora + a faint field of posts
field_jpg = A / "img" / "field.jpg"
subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(A / "img" / "framed_sheet.jpg"),
                "-vf", "scale=1800:-1,crop=1080:ih:0:0,gblur=sigma=7,eq=saturation=0.5:brightness=-0.04",
                "-q:v", "4", str(field_jpg)], check=True)
FIELD_H = 1800 / 3000 * 300 * ROWS_SHEET
BLOBS = [  # colour, size, path of (x, y) centre waypoints over 0..30 s
    ((46, 96, 255, 0.50), 1600, [(-120, 150), (380, 520), (60, 880)]),
    ((47, 224, 200, 0.16), 1400, [(900, 1450), (620, 1150), (980, 820)]),
    ((110, 72, 230, 0.30), 1500, [(120, 1750), (520, 1500), (-80, 1300)]),
    ((22, 64, 200, 0.45), 1300, [(980, 260), (700, 600), (1020, 420)]),
]


def glow(rgba):
    """a radial falloff with an eased (roughly gaussian) profile, so a blob has no visible rim"""
    r, g, b, a = rgba
    stops = [(0, 1.0), (20, 0.82), (40, 0.5), (60, 0.22), (80, 0.06), (100, 0.0)]
    return "radial-gradient(closest-side, " + ", ".join(f"rgba({r},{g},{b},{a * k:.3f}) {p}%" for p, k in stops) + ")"


blob_html = "".join(f'<div class="blob" id="blob{i}" style="width:{s}px; height:{s}px; background:{glow(c)};"></div>'
                    for i, (c, s, _) in enumerate(BLOBS))
STILL = BM.STILL_F
for i, (c, s, path) in enumerate(BLOBS):
    (x0, y0), (x1, y1), (x2, y2) = path
    J.append(f'tl.fromTo("#blob{i}", {{x: {x0 - s / 2}, y: {y0 - s / 2}}}, {{x: {x1 - s / 2}, y: {y1 - s / 2}, '
             f'duration: {D(STILL / 2)}, ease: "sine.inOut"}}, 0);')
    J.append(f'tl.to("#blob{i}", {{x: {x2 - s / 2}, y: {y2 - s / 2}, duration: {D(STILL / 2)}, ease: "sine.inOut"}}, {D(STILL / 2)});')
J.append(f'tl.fromTo("#field", {{y: 0}}, {{y: {-(FIELD_H - FH):.0f}, duration: {D(STILL)}, ease: "none"}}, 0);')
bg_html = f"""
  <div id="bg" class="clip full" {clip(0, TOTAL_F, 0)}>
    <div class="full" style="background:linear-gradient(180deg, #051649 0%, {NAVY} 42%, #0A2372 100%);"></div>
    {blob_html}
    <img id="field" src="assets/img/field.jpg" alt="" style="position:absolute; left:0; top:0; width:{FW}px; height:{FIELD_H:.0f}px; opacity:0.07;">
    <div class="full" style="background:radial-gradient(ellipse 760px 1100px at 50% 45%, rgba(0,0,0,0) 55%, rgba(2,8,32,0.55) 100%);"></div>
  </div>"""

# ================================================================ a: intro + the number made of faces
NUM_W = 900
NPX = fit("11,000+", NUM_W, 240)
NCAP = CAP * NPX
n_base = TZ0 - 0.36 * NPX            # the number sits on its sentence: baseline to cap top clears the comma
n_cap = n_base - NCAP
show("11,000+")
KM = 2
nmask = raster([("11,000", NUM_W, NPX, L, n_base)], FW, FH, KM)
mask_png(nmask, FW * KM, FH * KM, A / "img" / "mask_num.png")
P, TS = 40, 38                       # lattice pitch and tile: a 2 px seam between faces
# lattice registered on the hero tile: centred in the left stroke of the middle 0
hx = L + tw("11,0", NPX, NUM_W) + TRACK[NUM_W] * NPX + 0.135 * NPX
hy = n_cap + NCAP / 2
num_w = tw("11,000", NPX, NUM_W)
gx0 = hx - TS / 2 - P * math.ceil((hx - TS / 2 - (L - 8)) / P)
gy0 = hy - TS / 2 - P * math.ceil((hy - TS / 2 - (n_cap - 12)) / P)
rng = random.Random(4)
CELL_ROWS = math.ceil(NFACE / 20)
tiles, hero_tile = [], None
y = gy0
while y < n_base + 0.24 * NPX:
    x = gx0
    while x < L + num_w + 8:
        if coverage(nmask, FW * KM, x, y, TS, KM) > 0.0:
            is_hero = abs(x + TS / 2 - hx) < 1 and abs(y + TS / 2 - hy) < 1
            c = HERO_LAST if is_hero else rng.choice(ORDER)
            tiles.append(f'<i class="tile" style="left:{x:.1f}px; top:{y:.1f}px; --x:{-(c % 20) * TS}px; --y:{-(c // 20) * TS}px;"></i>')
            if is_hero:
                hero_tile = (x, y)
        x += P
    y += P
if hero_tile is None:
    raise SystemExit("the hero tile fell outside the number")
plus_x = L + num_w + TRACK[NUM_W] * NPX
# hero post: the tile shows the tight crop (x 62..337, y 65..340 of the 400 px aligned face, eye gap 110);
# in the post canvas, where faces_prep.py put the hero's eyes (centre hmx, hmy, gap hg), that square is:
hmx, hmy, hg = FACES["faces"][HERO_LAST]["post"]
KF = hg / 110
TIGHT = (hmx + (62 - 200) * KF, hmy + (65 - 170) * KF, 275 * KF)
hero_size = TS * FO / TIGHT[2]
hero_l = hero_tile[0] - TS * TIGHT[0] / TIGHT[2]
hero_t = hero_tile[1] - TS * TIGHT[1] / TIGHT[2]
eye_x = hero_l + hero_size * hmx / FO
eye_y = hero_t + hero_size * hmy / FO
EYE_H = (WIN_L + hmx * WIN / FO, WIN_T + hmy * WIN / FO)    # where those eyes are when the frame is in place
Z0 = WIN / hero_size                 # the intro frame is the hero tile, magnified
hero_ids = BIG_IDS["hero"]
shuffle("h", BM.FACES["hero"], hero_ids)
a_html = f"""
  <div id="A" class="clip full" {clip(0, 160, 2)}>
    <div id="Acam" class="full">
      <div id="Anum" class="full"><div id="Atl" class="full">{''.join(tiles)}<div id="Atint" class="full"></div></div></div>
      <div id="aplus" class="t" style="left:{plus_x:.1f}px; top:{top_for_cap(n_cap, NPX):.1f}px; font-size:{NPX:.1f}px;">+</div>
      <div id="hero">{face_stack("h", hero_ids, hero_size, hero_l, hero_t)}</div>
    </div>
    <div class="vf" id="vfA"></div>
  </div>"""
J.append(f'tl.set("#Acam", {{transformOrigin: "{eye_x:.2f}px {eye_y:.2f}px", x: {EYE_H[0] - eye_x:.2f}, y: {EYE_H[1] - eye_y:.2f}, scale: {Z0:.4f}}}, 0);')
# the pull-back: log-scale zoom from Z0 to 1, the eye point drifting to its place in the number
J.append(f"""const zA = {{p: 0}};
tl.fromTo(zA, {{p: 0}}, {{immediateRender: false, p: 1, duration: {D(24)}, ease: "power3.inOut", onUpdate: () => {{
  const z = Math.pow({Z0:.4f}, 1 - zA.p), w = (z - 1) / ({Z0:.4f} - 1);
  gsap.set("#Acam", {{scale: z, x: {EYE_H[0] - eye_x:.2f} * w, y: {EYE_H[1] - eye_y:.2f} * w}});
  gsap.set("#hero", {{opacity: Math.max(0, Math.min(1, (z - 2.2) / 3.2))}});
}}}}, {T(64)});""")
J.append(f'tl.set("#Atl", {{opacity: 1}}, {T(64)});')
J.append(f'tl.to("#vfA", {{opacity: 0, duration: {D(5)}}}, {T(64)});')
J.append(f'tl.fromTo("#aplus", {{opacity: 0}}, {{immediateRender: false, opacity: 1, duration: {D(6)}, ease: "power2.out"}}, {T(88)});')
for i, f in enumerate(BM.FACES["tiles"]):
    J.append(f'tl.set("#Atl", {{"--dx": "{-((3 + 7 * i) % 20) * TS}px", "--dy": "{-((2 + 3 * i) % CELL_ROWS) * TS}px"}}, {T(f)});')
J.append(f'tl.to("#Acam", {{opacity: 0, duration: {D(6)}, ease: "power1.in"}}, {T(154)});')
card("ta", 96, 160, [{"words": [W("learners", 96), W("chose", 104)]}, {"words": [W("JAIN Online.", 112, "teal")]}])

# ================================================================ b: Welcome to the Batch of 2026.
card("tb", 160, 288, [{"words": [W("Welcome", 160), W("to the", 168)]}, {"words": [W("Batch of", 176)]}])
fl_b = window("fb", 184, 192, 6, [f for f in BM.FACES["flash"] if f < 192], BIG_IDS["flash_b"])
YPX = min(fit("20", 900, 600), fit("26.", 900, 600), (VZ1 - VZ0 - 40) / (2 * CAP + 0.12))
YCAP, YGAP = CAP * YPX, 0.12 * YPX
y1_cap = VC - (2 * YCAP + YGAP) / 2
y1_base, y2_base = y1_cap + YCAP, y1_cap + 2 * YCAP + YGAP
show("2026.")
KP = 2
m20 = raster([("20", 900, YPX, L, y1_base)], FW, FH, KP)
m26 = raster([("26.", 900, YPX, L, y2_base)], FW, FH, KP)
mask_png(m20, FW * KP, FH * KP, A / "img" / "mask20.png")
mask_png(m26, FW * KP, FH * KP, A / "img" / "mask26.png")
mask_png(bytes(max(a, b) for a, b in zip(m20, m26)), FW * KP, FH * KP, A / "img" / "teal2026.png", "0x" + TEAL.lstrip("#"))
period = bbox(m26, FW * KP, (L + tw("26", YPX, 900)) * KP, (y2_base - 0.4 * YPX) * KP, (L + tw("26.", YPX, 900) + 20) * KP, (y2_base + 10) * KP)
px0, py0, px1, py1 = (v / KP for v in period)


def vmask(id_, png, f0):
    return (f'\n  <div class="vm" id="{id_}" style="-webkit-mask-image:url(\'assets/img/{png}\'); mask-image:url(\'assets/img/{png}\');">'
            f'<video id="{id_}v" class="clip" src="assets/footage/scroll.mp4" muted playsinline {clip(f0, 288, 3 if id_ == "vm20" else 4)} '
            f'style="position:absolute; left:0; top:-66px; width:1080px; height:2052px;"></video></div>')


b_html = vmask("vm20", "mask20.png", 192) + vmask("vm26", "mask26.png", 200) + f"""
  <div id="B26" class="clip full" {clip(192, 288, 9)}>
    <div id="dot" style="position:absolute; left:{px0 - 1:.1f}px; top:{py0 - 1:.1f}px; width:{px1 - px0 + 2:.1f}px; height:{py1 - py0 + 2:.1f}px; background:{TEAL}; opacity:0;"></div>
    <img id="teal26" src="assets/img/teal2026.png" alt="" style="position:absolute; left:0; top:0; width:{FW}px; height:{FH}px; opacity:0;">
  </div>"""
J.append(f'tl.fromTo("#vm20", {{opacity: 0}}, {{immediateRender: false, opacity: 1, duration: {D(4)}}}, {T(192)});')
J.append(f'tl.fromTo("#vm26", {{opacity: 0}}, {{immediateRender: false, opacity: 1, duration: {D(4)}}}, {T(200)});')
J.append(f'tl.set("#dot", {{opacity: 1}}, {T(208)});')
J.append(f'tl.set("#teal26", {{opacity: 1}}, {T(272)});')
J.append(f'tl.set("#teal26", {{opacity: 0}}, {T(280)});')
J.append(f'tl.to(["#vm20", "#vm26", "#dot"], {{opacity: 0, duration: {D(5)}, ease: "power1.in"}}, {T(282)});')

# ================================================================ c: the window, the counter, the wall
c_html = window("cw", 288, 416, 6, BM.FACES["win"], BIG_IDS["win"])
for f in BM.FACES["win"]:
    if f < 320 or f >= 384:
        J.append(f'tl.fromTo("#cw .vf", {{scale: 1.06}}, {{immediateRender: false, scale: 1, duration: {D(4)}, ease: "power2.out"}}, {T(f)});')
card("tc1", 288, 320, [{"words": [W("We", 288), W("are", 296), W("proud", 304)]}, {"words": [W("to nurture", 312)]}])
CNT_PX = 150.0
c0, c1 = BM.COUNTER
card("tc2", 320, 448, [{"px": CNT_PX, "weight": 900, "words": [W("11,000+", c0, "cnt")]},
                       {"words": [W("ambitions", 392)]}, {"words": [W("this year.", 400)]}])
# the counter: the span shows a running count, then its own text (11,000+) at the lock
J.append(f"""const cA = {{p: 0}};
tl.fromTo(cA, {{p: 0}}, {{immediateRender: false, p: 1, duration: {D(c1 - c0)}, ease: "power2.in", onUpdate: () => {{
  const el = document.getElementById("tc2w00");
  el.innerHTML = cA.p < 1 ? Math.round(11000 * cA.p).toLocaleString("en-US") : '11,000<span class="teal">+</span>';
}}}}, {T(c0)});""")

# ---- the wall of 16 (c end, d), in the visual zone
GD = WIN / 4
TARGET = (1, 1)                          # col, row of the post that becomes "each one."
cells = []
for r in range(4):
    for c in range(4):
        cells.append(f'<div class="gc" id="g{r * 4 + c}" style="left:{WIN_L + c * GD:.1f}px; top:{VZ0 + r * GD:.1f}px; '
                     f'width:{GD:.1f}px; height:{GD:.1f}px; {sheet_bg(GD)}"></div>')
NG = 16
tgt = TARGET[1] * 4 + TARGET[0]
gframes = BM.FACES["grid"]
for n, f in enumerate(gframes):
    seq = [pool[(n * NG + j) % len(pool)] for j in range(NG)]
    if n == len(gframes) - 1:
        seq[tgt] = HOLD_FACE                # pool never holds HOLD_FACE, so it appears once
    for j in range(NG):
        J.append(f'tl.set("#g{j}", {{backgroundPosition: "{sheet_pos(seq[j], GD)}"}}, {T(f)});')
tcx, tcy = WIN_L + TARGET[0] * GD + GD / 2, VZ0 + TARGET[1] * GD + GD / 2
ZG = WIN / GD
g_html = f"""
  <div id="G" class="clip full" {clip(416, 640, 5)}>
    <div id="Gcam" class="full" style="transform-origin:{tcx:.1f}px {tcy:.1f}px;">{''.join(cells)}
      <img id="hold" src="assets/framed/f{HOLD_FACE:03d}.jpg" alt="" style="position:absolute; left:{WIN_L + TARGET[0] * GD:.1f}px; top:{VZ0 + TARGET[1] * GD:.1f}px; width:{GD:.1f}px; height:{GD:.1f}px; opacity:0;"></div>
  </div>"""
E1 = BM.EACH_ONE
others = json.dumps([f"#g{j}" for j in range(NG) if j != tgt])
J.append(f'tl.set("#hold", {{opacity: 1}}, {T(E1)});')
J.append(f'tl.to({others}, {{opacity: 0, duration: {D(10)}, ease: "power2.inOut"}}, {T(E1)});')
J.append(f'tl.to("#Gcam", {{scale: {ZG:.3f}, x: {540 - tcx:.1f}, y: {VC - tcy:.1f}, duration: {D(18)}, ease: "expo.inOut"}}, {T(E1)});')
J.append(f'tl.to("#Gcam", {{opacity: 0, duration: {D(6)}, ease: "power1.in"}}, {T(630)});')

# ================================================================ d: the breakdown
card("td1", 448, 488, [{"words": [W("But even", 448)]}, {"words": [W("more than that,", 464)]}])
card("td2", 488, 528, [{"words": [W("we are proud", 488)]}, {"words": [W("to carry", 500)]}])
TR_PX = min(fit("trust", 900, 250), (TZ_MAX - TZ0 - CAP * TXT_PX - 0.42 * TXT_PX) / CAP)
card("td3", 528, 560, [{"words": [W("the", 528)]}, {"px": TR_PX, "weight": 900, "words": [W("trust", 536, "mos")]}])
J.append(f'tl.fromTo("#td3w10", {{backgroundPosition: "0px 0px"}}, {{immediateRender: false, backgroundPosition: "-120px -40px", duration: {D(24)}, ease: "none"}}, {T(536)});')
card("td4", 560, 640, [{"words": [W("behind", 560)]}, {"words": [W("each one.", E1, "teal")]}])

# ================================================================ e: the peak
fl_e = window("fe", 640, 672, 6, [f for f in BM.FACES["flash"] if f >= 640], BIG_IDS["flash_e"])
card("te1", 640, 672, [{"words": [W("Because", 640)]}, {"words": [W("every learner", 648)]}])
mp_html = f"""
  <div id="MP" class="clip full" {clip(672, 704, 7)}>
    <div id="mpan" style="position:absolute; left:{WIN_L}px; top:{VZ0}px; width:{WIN}px; height:{WIN}px; border-radius:28px;
      background:url('assets/img/face_mosaic.jpg') 0px 0px / 1344px 784px repeat;"></div>
  </div>"""
J.append(f'tl.fromTo("#mpan", {{backgroundPosition: "0px 0px"}}, {{immediateRender: false, backgroundPosition: "-168px -56px", duration: {D(32)}, ease: "none"}}, {T(672)});')
card("te2", 672, 704, [{"words": [W("who chooses", 672)]}, {"words": [W("JAIN Online", 680, "teal")]}])
# the map of India, filled with faces: one band of photos per sixteenth, south to north
geo = json.loads((A / "geo" / "india-composite.geojson").read_text(encoding="utf-8-sig"))
gm = geo["features"][0]["geometry"]
polys = gm["coordinates"] if gm["type"] == "MultiPolygon" else [gm["coordinates"]]
KX = math.cos(math.radians(22.0))    # equirectangular, x scaled at the mid latitude
lons = [pt[0] for pg in polys for ring in pg for pt in ring]
lats = [pt[1] for pg in polys for ring in pg for pt in ring]
lon0, lon1, lat0, lat1 = min(lons), max(lons), min(lats), max(lats)
MS = min(WIN / ((lon1 - lon0) * KX), (VZ1 - VZ0) / (lat1 - lat0))
MW, MH = (lon1 - lon0) * KX * MS, (lat1 - lat0) * MS
MX0, MY0 = 540 - MW / 2, VZ0 + (VZ1 - VZ0 - MH) / 2
rings = []
for pg in polys:
    for ring in pg:
        pts, last = [], None
        for lon, lat in ring:
            x, y = MX0 + (lon - lon0) * KX * MS, MY0 + (lat1 - lat) * MS
            if last is None or math.hypot(x - last[0], y - last[1]) >= 1.2:
                pts.append((x, y))
                last = (x, y)
        if len(pts) >= 3:
            rings.append(pts)
map_d = " ".join("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in r) + " Z" for r in rings)
(A / "img" / "india.svg").write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{FW}" height="{FH}" viewBox="0 0 {FW} {FH}">'
    f'<path d="{map_d}" fill="#fff" fill-rule="evenodd"/></svg>', encoding="utf-8")
edges = [(r[k], r[(k + 1) % len(r)]) for r in rings for k in range(len(r))]


def spans(y):
    xs = sorted(x1 + (y - y1) * (x2 - x1) / (y2 - y1) for (x1, y1), (x2, y2) in edges if (y1 <= y < y2) or (y2 <= y < y1))
    return list(zip(xs[0::2], xs[1::2]))


MP_P, MP_T = 24, 22
NB = len(BM.FACES["map"])
band_tiles = [[] for _ in range(NB)]
rngm = random.Random(26)
ty = MY0 - 6
while ty < MY0 + MH:
    rows = [spans(ty + d) for d in (2, MP_T / 2, MP_T - 2)]
    tx = MX0 - 6
    while tx < MX0 + MW:
        if any(a < tx + MP_T and b > tx for row in rows for a, b in row):
            band = min(NB - 1, max(0, int((MY0 + MH - (ty + MP_T)) / (MH / NB))))
            c = rngm.choice(ORDER)
            band_tiles[band].append(f'<i class="mt" style="left:{tx:.1f}px; top:{ty:.1f}px; --x:{-(c % 20) * MP_T}px; --y:{-(c // 20) * MP_T}px;"></i>')
        tx += MP_P
    ty += MP_P
n_map_tiles = sum(len(b) for b in band_tiles)
map_html = f"""
  <div id="MAP" class="clip full" {clip(704, 832, 7)}>
    <div id="MAPcam" class="full" style="transform-origin:540px {MY0 + MH / 2:.0f}px;">
      <div id="MAPm" class="full"><div id="MAPt" class="full">{''.join(f'<div class="mb" id="mb{k}">{"".join(b)}</div>' for k, b in enumerate(band_tiles))}
        <div class="full" style="background:{WHITE}; opacity:0.08;"></div></div></div>
      <svg id="mapline" class="full" viewBox="0 0 {FW} {FH}" style="opacity:0;"><path d="{map_d}" fill="none" stroke="{WHITE}" stroke-width="2.2" stroke-linejoin="round"/></svg>
    </div>
  </div>"""
for k, f in enumerate(BM.FACES["map"]):
    J.append(f'tl.fromTo("#mb{k}", {{opacity: 0}}, {{immediateRender: false, opacity: 1, duration: {D(3)}, ease: "power1.out"}}, {T(f)});')
J.append(f'tl.fromTo("#mapline", {{opacity: 0}}, {{immediateRender: false, opacity: 0.85, duration: {D(8)}, ease: "power1.out"}}, {T(768)});')
J.append(f'tl.to("#MAPcam", {{scale: 1.035, duration: {D(54)}, ease: "sine.inOut"}}, {T(770)});')
for i, f in enumerate(BM.FACES["mosaic"]):     # the faces in the map change on stomp, stomp, clap
    J.append(f'tl.set("#MAPt", {{"--dx": "{-((5 + 7 * i) % 20) * MP_T}px", "--dy": "{-((3 + 3 * i) % CELL_ROWS) * MP_T}px"}}, {T(f)});')
J.append(f'tl.to("#MAPcam", {{opacity: 0, duration: {D(6)}, ease: "power1.in"}}, {T(826)});')
card("te3", 704, 736, [{"words": [W("brings us", 704)]}, {"words": [W("one step", 712), W("closer", 720)]}])
card("te4", 736, 768, [{"words": [W("to building", 736)]}, {"words": [W("a more skilled,", 744)]}])
card("te5", 768, 832, [{"words": [W("future-ready", 768)]}, {"words": [W("India.", 776, "teal")]}])

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
show("2026")
DESC_MASK = "clip-path: polygon(0% 0%, 100% 0%, 100% 100%, 61.6% 100%, 61.6% 68.9%, 0% 68.9%);"


def tag(id_, a, b, cap):
    return (f'<div class="t" id="{id_}" style="left:{L}px; top:{top_for_cap(cap, TG_PX):.1f}px; font-size:{TG_PX}px; opacity:0;">'
            f'<span style="font-weight:500;">{esc(show(a))}</span> <span style="font-weight:900; letter-spacing:-0.02em;">{esc(show(b))}</span></div>')


f_html = f"""
  <div id="F" class="clip full" {clip(832, TOTAL_F, 8)}>
    <div id="logo-mask" style="position:absolute; left:{L}px; top:{LOGO_T}px; width:{LOGO_W:.1f}px; height:{LOGO_H:.2f}px; clip-path: inset(0px {LOGO_W:.1f}px 0px 0px);">
      <img id="logo" src="assets/brand/deekshaarambh.png" alt="" style="position:absolute; left:0; top:0; width:{LOGO_W:.1f}px; height:{LOGO_H:.2f}px; {DESC_MASK}">
    </div>
    <div class="t" id="f_yr" style="left:{L}px; top:{top_for_cap(yr_cap, YR_PX):.1f}px; font-size:{YR_PX}px; font-weight:900; letter-spacing:-0.03em; opacity:0;">2026</div>
    {tag("f_t1", "Your", "ambition.", tg1_cap)}
    {tag("f_t2", "Our", "commitment.", tg2_cap)}
    <img id="jo" src="assets/brand/jain-online.png" alt="" style="position:absolute; left:{L}px; top:{JO_T}px; width:{JO_W}px; opacity:0;">
  </div>"""
J.append(f'tl.to("#logo-mask", {{clipPath: "inset(0px 0px 0px 0px)", duration: {D(14)}, ease: "expo.out"}}, {T(832)});')
for el, f in (("#f_yr", 848), ("#f_t1", 864), ("#f_t2", 880)):
    J.append(f'tl.fromTo("{el}", {{opacity: 0, y: 16}}, {{immediateRender: false, opacity: 1, y: 0, duration: {D(8)}, ease: "power2.out"}}, {T(f)});')
J.append(f'tl.fromTo("#jo", {{opacity: 0}}, {{immediateRender: false, opacity: 1, duration: {D(4)}, ease: "power2.out"}}, {T(896)});')

# ================================================================ copy check: shown strings, in order, against the script
seq_expected = " ".join(SCRIPT).split()
seq_got = " ".join(SHOWN).split()
if seq_got != seq_expected:
    raise SystemExit("on-screen copy does not match the locked script:\n  shown : " + " ".join(seq_got)
                     + "\n  script: " + " ".join(seq_expected))

# ================================================================ page
card_html = "".join(f'\n  <div id="{id_}" class="clip full" {clip(f0, f1, 1)}>{inner}</div>'
                    for id_, f0, f1, inner in sorted(cards, key=lambda c: c[1]))
last = 0
for id_, f0, f1, _ in sorted(cards, key=lambda c: c[1]):
    if f0 < last:
        raise SystemExit(f"text cards overlap at {id_}")
    last = f1

VF_W, VF_H, VF_A = 3.25 * EGAP, 1.5 * EGAP, round(0.37 * EGAP)   # the viewfinder around the eyes
css = f"""
@font-face {{ font-family: 'Montserrat'; font-weight: 500; src: url('assets/fonts/Montserrat-500.ttf'); }}
@font-face {{ font-family: 'Montserrat'; font-weight: 800; src: url('assets/fonts/Montserrat-800.ttf'); }}
@font-face {{ font-family: 'Montserrat'; font-weight: 900; src: url('assets/fonts/Montserrat-900.ttf'); }}
#stage {{ position: relative; width: {FW}px; height: {FH}px; overflow: hidden; background: {NAVY};
  font-family: 'Montserrat', sans-serif; color: {WHITE}; }}
.full {{ position: absolute; left: 0; top: 0; width: {FW}px; height: {FH}px; }}
.t {{ position: absolute; white-space: nowrap; line-height: 1; }}
.blob {{ position: absolute; left: 0; top: 0; border-radius: 50%; }}
.ln {{ position: absolute; left: {L}px; white-space: nowrap; line-height: 1; }}
.w {{ display: inline-block; opacity: 0; }}
.teal {{ color: {TEAL}; }}
.cnt {{ font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }}
.mos {{ color: transparent; background: linear-gradient(rgba(255,255,255,0.16), rgba(255,255,255,0.16)),
  url('assets/img/face_mosaic.jpg') 0px 0px / 1344px 784px repeat;
  -webkit-background-clip: text; background-clip: text; }}
#Anum {{ -webkit-mask-image: url('assets/img/mask_num.png'); mask-image: url('assets/img/mask_num.png');
  -webkit-mask-size: {FW}px {FH}px; mask-size: {FW}px {FH}px; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat; }}
#Atl {{ --dx: 0px; --dy: 0px; opacity: 0; }}
#Atint {{ background: {WHITE}; opacity: 0.10; }}
.tile {{ position: absolute; width: {TS}px; height: {TS}px;
  background-image: url('assets/img/face_cells.jpg'); background-size: {20 * TS}px {CELL_ROWS * TS}px; background-repeat: repeat;
  background-position: calc(var(--x) + var(--dx)) calc(var(--y) + var(--dy)); }}
#aplus {{ color: {TEAL}; font-weight: 900; opacity: 0; }}
.fs {{ position: absolute; opacity: 0; }}
.pf {{ position: absolute; }}
.vf {{ position: absolute; left: {EYE[0] - VF_W / 2:.0f}px; top: {EYE[1] - VF_H / 2:.0f}px; width: {VF_W:.0f}px; height: {VF_H:.0f}px;
  background:
    linear-gradient({WHITE},{WHITE}) left top / {VF_A}px 4px no-repeat, linear-gradient({WHITE},{WHITE}) left top / 4px {VF_A}px no-repeat,
    linear-gradient({WHITE},{WHITE}) right top / {VF_A}px 4px no-repeat, linear-gradient({WHITE},{WHITE}) right top / 4px {VF_A}px no-repeat,
    linear-gradient({WHITE},{WHITE}) left bottom / {VF_A}px 4px no-repeat, linear-gradient({WHITE},{WHITE}) left bottom / 4px {VF_A}px no-repeat,
    linear-gradient({WHITE},{WHITE}) right bottom / {VF_A}px 4px no-repeat, linear-gradient({WHITE},{WHITE}) right bottom / 4px {VF_A}px no-repeat;
  opacity: 0.85; }}
.vm {{ position: absolute; left: 0; top: 0; width: {FW}px; height: {FH}px; opacity: 0;
  -webkit-mask-size: {FW}px {FH}px; mask-size: {FW}px {FH}px; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat; }}
.gc {{ position: absolute; background-repeat: no-repeat; }}
#MAPm {{ -webkit-mask-image: url('assets/img/india.svg'); mask-image: url('assets/img/india.svg');
  -webkit-mask-size: {FW}px {FH}px; mask-size: {FW}px {FH}px; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat; }}
#MAPt {{ --dx: 0px; --dy: 0px; }}
.mb {{ position: absolute; left: 0; top: 0; width: {FW}px; height: {FH}px; opacity: 0; }}
.mt {{ position: absolute; width: {MP_T}px; height: {MP_T}px;
  background-image: url('assets/img/face_cells.jpg'); background-size: {20 * MP_T}px {CELL_ROWS * MP_T}px; background-repeat: repeat;
  background-position: calc(var(--x) + var(--dx)) calc(var(--y) + var(--dy)); }}
#grain {{ background-image: url('assets/img/grain.png'); background-size: 256px 256px; mix-blend-mode: overlay; opacity: 0.06; }}
"""

js = "\n".join([
    "const tl = gsap.timeline({ paused: true });",
    f'tl.fromTo("#grain", {{backgroundPosition: "0px 0px"}}, {{backgroundPosition: "{STILL * 164}px {STILL * 105}px", duration: {D(STILL)}, ease: "steps({STILL // 2})"}}, 0);',
] + J + [
    f'tl.set({{}}, {{}}, {D(TOTAL_F)});',
    "window.__timelines = window.__timelines || {};",
    "window.__timelines.reel = tl;",
])

body = f"""{bg_html}
{a_html}
{fl_b}
{b_html}
{c_html}
{g_html}
{fl_e}
{mp_html}
{map_html}
{card_html}
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
print(f"composed {BM.TOTAL:.0f}s @ {BM.BPM} BPM: number {NPX:.0f}px from {len(tiles)} face tiles, India from {n_map_tiles}, copy {TXT_PX:.0f}px "
      f"in {len(cards)} cards, 20/26. at {YPX:.0f}px, {len(BM.clicks())} shutter cuts; script check passed")
