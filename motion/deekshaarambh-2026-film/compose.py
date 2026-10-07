#!/usr/bin/env python3
"""Compose the Deekshaarambh 2026 brand film (32 s, 1080x1920@30) from config.json.

Usage: motion/deekshaarambh-2026-film/compose.py --project motion/deekshaarambh-2026-film/project
       (run prep_assets.py and make_score.py into the same project first)

One continuous world on a solid navy ground, one left edge (grid.left) for all
type, and one recurring motif: the accent plus from 11,000+. It detaches and
becomes the registration mark beside 2026, rides the push into the zero and
lands as the plus of the second 11,000+, waits as a mark through the first two
trust phrases, opens into the line that supports "trust", extends into the
baseline the purpose statement rises from, climbs with it, becomes the
wordmark's top bar for the reveal, and settles as the divider of the lockup.

  s1  numeral pulled back from oversized (two-stage, the only overshoot), then
      "learners chose" / "JAIN Online." rise from masks on the numeral's left edge
  s2  "Welcome to the" / "Batch of" / "2026." on the same grid; the first footage
      frame appears in the zero's counter and the camera pushes through it until
      the counter becomes the video window
  s3  the 3 s learner clip plays once, untouched, in a panel; type above and below
  s4  the held last frame opens to full canvas under navy and fades out as the
      sentence simplifies to "trust", which lands firm and still
  s5  three compositions on one rising column, one grid step apart
  s6  the column rises into the identity: one mask reveals the authentic
      wordmark from its own top bar; tagline in opposing moves; JAIN Online; a
      still final two seconds

Every displayed string is checked against config.json's locked script before
writing. Text, colours, timings and media paths all live in config.json.
"""
import argparse
import html
import json
import pathlib
import struct

HERE = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser(description="Compose the Deekshaarambh 2026 brand film into index.html.")
ap.add_argument("--project", required=True)
project = pathlib.Path(ap.parse_args().project).expanduser().resolve()
C = json.loads((HERE / "config.json").read_text(encoding="utf-8-sig"))
A = project / "assets"
M = C["media"]
for need in (M["logo"], M["jain_online"], M["footage"], M["footage_first"], M["footage_last"],
             "assets/fonts/Montserrat-500.ttf", "assets/fonts/Montserrat-800.ttf", "assets/audio/score.wav",
             "assets/gsap.min.js"):
    if not (project / need).is_file():
        raise SystemExit(f"missing {need} — run prep_assets.py / make_score.py into {project} first")

FW, FH, TOTAL = C["film"]["width"], C["film"]["height"], C["film"]["duration"]
T = C["type"]
G = C["grid"]
L = float(G["left"])
COLW = FW - G["right"] - L            # 852 at the brief's margins
COL = C["colors"]
TM = C["timing"]
CP = C["copy"]
esc = html.escape


# ---------------------------------------------------------------- copy check
def displayed():
    s1, s2, s3, s4, s5, s6 = (CP[k] for k in ("s1", "s2", "s3", "s4", "s5", "s6"))
    seq = [s1["number"] + "+"] + [t for t, _ in s1["lines"]]
    seq += [t for t, _ in s2["lines"]]
    seq += [t for t, _ in s3["above"]] + [s3["number"] + "+"] + [t for t, _ in s3["below"]]
    for ph in s4:
        seq += [t for t, _ in ph]
    for ph in s5:
        seq += [t for t, _ in ph]
    seq += [s6["logo_reads"], s6["year"]]
    for ln in s6["tagline"]:
        seq += [t for t, _ in ln]
    return " ".join(seq)


norm = lambda s: " ".join(s.split())
if norm(displayed()) != norm(" ".join(C["script"])):
    raise SystemExit("on-screen copy does not match the locked script:\n  shown : "
                     + norm(displayed()) + "\n  script: " + norm(" ".join(C["script"])))


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


TRACK = {"hero": -0.035, "heavy": -0.015, "medium": 0.0}
WEIGHT = {"hero": T["heavy"], "heavy": T["heavy"], "medium": T["medium"]}


def tw(text, px, role):
    a = advances(WEIGHT[role], text)
    return sum(a) * px + TRACK[role] * px * max(0, len(text) - 1)


def baseline_off(px, lh):
    """Distance from a line box's top to its baseline for line-height lh (em)."""
    return px * ((lh - (T["ascent"] + T["descent"])) / 2 + T["ascent"])


def fit(text, px, role, maxw=None):
    maxw = maxw or COLW
    w = tw(text, 1.0, role)
    return min(px, maxw / w)


SIZE = {"hero": T["hero_px"], "heavy": T["heavy_px"], "medium": T["sentence_px"]}
LH = {"hero": 1.0, "heavy": 1.2, "medium": 1.25}

# ---------------------------------------------------------------- elements
els, wide = [], []


def line(id_, text, role, top, px=None, left=None, cls="", hidden=True):
    px = px or SIZE[role]
    px = min(px, fit(text, px, role))
    w = tw(text, px, role)
    if w > COLW + 0.5:
        wide.append((text, round(w)))
    lh = LH[role]
    weight = WEIGHT[role]
    left = L if left is None else left
    els.append(
        f'<div class="ln {cls}" id="{id_}" style="left:{left:.1f}px; top:{top:.1f}px; height:{px * lh:.1f}px;">'
        f'<span class="in{" h" if hidden else ""}" id="{id_}-in" style="font-size:{px:.1f}px; font-weight:{weight}; '
        f'line-height:{lh}; letter-spacing:{TRACK[role]}em;">{esc(text)}</span></div>')
    return {"top": top, "px": px, "w": w, "base": top + baseline_off(px, lh), "lh": lh,
            "cap": top + baseline_off(px, lh) - T["cap"] * px}


def stack(prefix, items, first_top, gaps=None):
    """Lines on the left edge; each next line's cap top sits a fixed gap under the previous baseline."""
    out, top = [], first_top
    for i, (text, role) in enumerate(items):
        px = min(SIZE[role], fit(text, SIZE[role], role))
        if i:
            prev = out[-1]
            gap = (gaps or {}).get(i, 0.36 * px if role != "hero" else 0.22 * px)
            cap_top = prev["base"] + gap + (0.2 * prev["px"] if role == "hero" else 0)
            top = cap_top - (baseline_off(px, LH[role]) - T["cap"] * px)
        out.append(line(f"{prefix}{i}", text, role, top, px))
    return out


# ---- s1: 11,000+ / learners chose / JAIN Online.
N1 = min(T["hero_px"], COLW / (sum(advances(T["heavy"], CP["s1"]["number"] + "+")) + TRACK["hero"] * 6))
num_top = 640.0
num_w = tw(CP["s1"]["number"], N1, "hero")
plus_adv = advances(T["heavy"], "+")[0] * N1
num_base = num_top + baseline_off(N1, 1.0)
P1 = {"x": L + num_w + TRACK["hero"] * N1 + plus_adv / 2, "y": num_base - 0.35 * N1, "arm": 0.52 * N1, "th": 0.13 * N1}
s1_center = (L + (num_w + plus_adv) / 2, num_base - 0.35 * N1)
s1_lines = []
top = num_base + 64 - (baseline_off(T["sentence_px"], 1.25) - T["cap"] * T["sentence_px"])
for i, (text, role) in enumerate(CP["s1"]["lines"]):
    s1_lines.append(line(f"s1l{i}", text, role if role != "heavy" else "heavy", top,
                         px=T["sentence_px"]))
    top += T["sentence_px"] * 1.18
s1_html = "".join(els)
els.clear()

# ---- s2: Welcome to the / Batch of / 2026.
N2 = N1
y26_top = num_top
y26_base = y26_top + baseline_off(N2, 1.0)
year_text = CP["s2"]["lines"][2][0]
year_w = tw(year_text, N2, "hero")
l1_base = y26_base - T["cap"] * N2 - 62
s2a = line("s2l1", CP["s2"]["lines"][1][0], "medium", l1_base - baseline_off(T["sentence_px"], 1.25))
s2b = line("s2l0", CP["s2"]["lines"][0][0], "medium", s2a["top"] - T["sentence_px"] * 1.18)
s2c = line("s2l2", year_text, "hero", y26_top, px=N2)
s2_html = "".join(els)
els.clear()
zero_cx = L + advances(T["heavy"], "2")[0] * N2 + TRACK["hero"] * N2 + advances(T["heavy"], "0")[0] * N2 / 2
zero_cy = y26_base - 0.35 * N2
CW, CH = 0.25 * N2, 0.44 * N2           # counter of Montserrat ExtraBold 0
P2 = {"x": L + year_w + 0.06 * N2 + 0.16 * N2, "y": y26_base - T["cap"] * N2 + 0.16 * N2, "arm": 0.32 * N2, "th": 0.08 * N2}

# ---- s3: panel geometry from the footage crop
cx0, cy0, cw0, ch0 = M["footage_crop"]
PW = COLW
PH = PW * ch0 / cw0
ab = stack("s3a", CP["s3"]["above"], 190)
PT = ab[-1]["base"] + 0.3 * T["sentence_px"] + 34
PB = PT + PH
N3 = T["hero_small_px"]
n3_top = PB + 48 - (baseline_off(N3, 1.0) - T["cap"] * N3)
n3 = line("s3n", CP["s3"]["number"], "hero", n3_top, px=N3)
n3_w = n3["w"]
P3 = {"x": L + n3_w + TRACK["hero"] * N3 + advances(T["heavy"], "+")[0] * N3 / 2, "y": n3["base"] - 0.35 * N3, "arm": 0.52 * N3, "th": 0.13 * N3}
bl = []
top = n3["base"] + 30 - (baseline_off(T["heavy_px"], 1.2) - T["cap"] * T["heavy_px"])
bl.append(line("s3b0", CP["s3"]["below"][0][0], "heavy", top))
top = bl[0]["base"] + 30 - (baseline_off(T["sentence_px"], 1.25) - T["cap"] * T["sentence_px"])
bl.append(line("s3b1", CP["s3"]["below"][1][0], "medium", top))
s3_html = "".join(els)
els.clear()
KV = PW / cw0
SRC_W, SRC_H = 624, 1186
img_left, img_top = L - cx0 * KV, PT - cy0 * KV
img_w, img_h = SRC_W * KV, SRC_H * KV
pan_cx, pan_cy = L + PW / 2, PT + PH / 2

# ---- s4: three phrases
s4p = []
for k, ph in enumerate(CP["s4"][:2]):
    s4p.append(stack(f"s4p{k}l", ph, 760))
P4 = {"x": L + 18, "y": s4p[0][0]["cap"] - 64, "arm": 36, "th": 9}
the = line("s4p2l0", CP["s4"][2][0][0], "medium", 600)
tr_px = T["hero_px"]
trust_base = the["base"] + 40 + T["cap"] * tr_px
trust = line("s4p2l1", CP["s4"][2][1][0], "hero", trust_base - baseline_off(tr_px, 1.0), px=tr_px)
L1 = {"x": L + trust["w"] / 2, "y": trust["base"] + 40, "w": trust["w"], "th": 10}
beh_cap = L1["y"] + 52
beh = line("s4p2l2", CP["s4"][2][2][0], "medium", beh_cap - (baseline_off(T["sentence_px"], 1.25) - T["cap"] * T["sentence_px"]))
s4_html = "".join(els)
els.clear()

# ---- s5: three compositions, one grid step apart on a rising column
STEP = G["step"]
s5c = []
for k, ph in enumerate(C["copy"]["s5"]):
    s5c.append(stack(f"s5c{k}l", ph, 560 + k * STEP))
s5_html = "".join(els)
els.clear()
L2 = {"y": s5c[0][-1]["base"] + 40, "w": COLW}
L3 = {"y": s5c[1][-1]["base"] - STEP + 40, "w": COLW}
india = s5c[2][-1]
L4 = {"y": india["base"] - 2 * STEP + 40, "w": india["w"]}

# ---- s6: identity
LOGO_W = COLW
LK = LOGO_W / 1624
LOGO_T = 520.0
LOGO_H = 540 * LK
BAR_Y = LOGO_T + 174 * LK
BAR_W = 1113 * LK
BAR_TH = 25 * LK
yr_px = 110
yr_base = 740 + T["cap"] * yr_px
year = line("s6y", CP["s6"]["year"], "hero", yr_base - baseline_off(yr_px, 1.0), px=yr_px)
DIV = {"y": yr_base + 66, "w": 96, "th": 8}
tag = []
top = DIV["y"] + 60 - (baseline_off(84, 1.25) - T["cap"] * 84)
for i, parts in enumerate(CP["s6"]["tagline"]):
    spans = " ".join(f'<span style="font-weight:{WEIGHT[r]};">{esc(t)}</span>' for t, r in parts)
    els.append(f'<div class="ln" id="s6t{i}" style="left:{L:.1f}px; top:{top:.1f}px; height:{84 * 1.25:.1f}px;">'
               f'<span class="in h" id="s6t{i}-in" style="font-size:84px; line-height:1.25;">{spans}</span></div>')
    tw_ = sum(tw(t + (" " if j < len(parts) - 1 else ""), 84, r) for j, (t, r) in enumerate(parts))
    if tw_ > COLW:
        wide.append((" ".join(t for t, _ in parts), round(tw_)))
    top += 84 * 1.16
s6_html = "".join(els)
els.clear()
JO_W = 330
JO_T = 1290

if wide:
    raise SystemExit(f"lines wider than the {COLW:.0f} px column: {wide}")

# descriptor mask: hide the artwork's 'Student Induction Program' row (x < 1000, y > 372 in artwork px)
DESC = "" if M["logo_show_descriptor"] else (
    "clip-path: polygon(0% 0%, 100% 0%, 100% 100%, 61.6% 100%, 61.6% 68.9%, 0% 68.9%);")

css = f"""
@font-face {{ font-family: 'Montserrat'; font-weight: 500; src: url('assets/fonts/Montserrat-500.ttf'); }}
@font-face {{ font-family: 'Montserrat'; font-weight: 800; src: url('assets/fonts/Montserrat-800.ttf'); }}
#stage {{ position: relative; width: {FW}px; height: {FH}px; overflow: hidden; background: {COL['navy']};
  font-family: 'Montserrat', sans-serif; color: {COL['text']}; }}
.full {{ position: absolute; left: 0; top: 0; width: {FW}px; height: {FH}px; }}
.ln {{ position: absolute; overflow: hidden; white-space: nowrap; width: {COLW + 40:.0f}px; }}
.in {{ display: block; }}
#bg {{ background: {COL['navy']}; }}
#c1 {{ transform-origin: {s1_center[0]:.1f}px {s1_center[1]:.1f}px; }}
#c1 .ln {{ overflow: visible; }}
#s1num {{ position: absolute; left: {L:.1f}px; top: {num_top:.1f}px; font-size: {N1:.1f}px; font-weight: {T['heavy']};
  line-height: 1; letter-spacing: {TRACK['hero']}em; white-space: nowrap; }}
.pl {{ position: absolute; background: {COL['accent']}; }}
#c2 {{ transform-origin: {zero_cx:.1f}px {zero_cy:.1f}px; }}
#win {{ clip-path: inset({zero_cy - CH / 2:.1f}px {FW - zero_cx - CW / 2:.1f}px {FH - zero_cy - CH / 2:.1f}px {zero_cx - CW / 2:.1f}px round 50%); opacity: 0; }}
.frame {{ position: absolute; left: {img_left:.2f}px; top: {img_top:.2f}px; width: {img_w:.2f}px; height: {img_h:.2f}px;
  transform-origin: {pan_cx - img_left:.1f}px {pan_cy - img_top:.1f}px; }}
#lastf {{ opacity: 0; }}
#lv {{ position: absolute; left: {L:.1f}px; top: {PT:.2f}px; width: {PW:.2f}px; height: {PH:.2f}px; }}
#veil {{ background: {COL['navy']}; opacity: 0; }}
#motif {{ position: absolute; left: 0; top: 0; width: 0; height: 0; opacity: 0; }}
#mh, #mv {{ position: absolute; left: 0; top: 0; background: {COL['accent']}; }}
#c5 {{ will-change: transform; }}
#logo-mask {{ position: absolute; left: {L:.1f}px; top: {LOGO_T:.1f}px; width: {LOGO_W:.1f}px; height: {LOGO_H:.2f}px;
  clip-path: inset({BAR_Y - LOGO_T:.2f}px 0px {LOGO_T + LOGO_H - BAR_Y:.2f}px 0px); }}
#logo {{ position: absolute; left: 0; top: 0; width: {LOGO_W:.1f}px; height: {LOGO_H:.2f}px; {DESC} }}
#jo {{ position: absolute; left: {L:.1f}px; top: {JO_T}px; width: {JO_W}px; opacity: 0; }}
#grain {{ background-image: url('assets/img/grain.png'); background-size: 256px 256px; mix-blend-mode: overlay; opacity: 0.045; }}
"""

body = f"""
  <div id="bg" class="clip full" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="0"></div>

  <div id="s1" class="clip full" data-start="0" data-duration="3.650" data-track-index="1">
    <div id="c1" class="full">
      <div id="s1num">{esc(CP['s1']['number'])}</div>
      <div id="p1h" class="pl" style="left:{P1['x'] - P1['arm'] / 2:.1f}px; top:{P1['y'] - P1['th'] / 2:.1f}px; width:{P1['arm']:.1f}px; height:{P1['th']:.1f}px;"></div>
      <div id="p1v" class="pl" style="left:{P1['x'] - P1['th'] / 2:.1f}px; top:{P1['y'] - P1['arm'] / 2:.1f}px; width:{P1['th']:.1f}px; height:{P1['arm']:.1f}px;"></div>
    </div>
    <div id="s1lines" class="full">{s1_html}</div>
  </div>

  <div id="s2" class="clip full" data-start="3.400" data-duration="3.150" data-track-index="2">
    <div id="c2" class="full">{s2_html}</div>
  </div>

  <div id="win" class="clip full" data-start="5.600" data-duration="9.500" data-track-index="3">
    <img class="frame" id="firstf" src="{M['footage_first']}" alt="">
    <img class="frame" id="lastf" src="{M['footage_last']}" alt="">
  </div>
  <video id="lv" class="clip" src="{M['footage']}" muted playsinline
         data-start="{TM['footage_play'][0]:.3f}" data-duration="{TM['footage_play'][1] - TM['footage_play'][0]:.3f}" data-track-index="4"></video>
  <div id="veil" class="clip full" data-start="10.300" data-duration="4.800" data-track-index="5"></div>

  <div id="s3" class="clip full" data-start="6.400" data-duration="4.700" data-track-index="6">{s3_html}</div>
  <div id="s4" class="clip full" data-start="10.900" data-duration="7.300" data-track-index="7">{s4_html}</div>
  <div id="s5" class="clip full" data-start="17.800" data-duration="10.400" data-track-index="8">
    <div id="c5" class="full">{s5_html}</div>
  </div>
  <div id="s6" class="clip full" data-start="27.300" data-duration="{TOTAL - 27.3:.3f}" data-track-index="9">
    <div id="logo-mask"><img id="logo" src="{M['logo']}" alt=""></div>
    {s6_html}
    <img id="jo" src="{M['jain_online']}" alt="">
  </div>

  <div id="motif-clip" class="clip full" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="10">
    <div id="motif"><div id="mh"></div><div id="mv"></div></div>
  </div>
  <div id="grain" class="clip full" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="11"></div>
  <audio id="score" class="clip" src="assets/audio/score.wav" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="12" data-volume="1"></audio>
"""


def plus(p):
    return {"x": p["x"], "y": p["y"], "hw": p["arm"], "hh": p["th"], "vw": p["th"], "vh": p["arm"]}


def bar(x, y, w, th):
    return {"x": x, "y": y, "hw": w, "hh": th, "vw": th, "vh": th}


STATES = {
    "P1": plus(P1), "P2": plus(P2), "P3": plus(P3), "P4": plus(P4),
    "L1": bar(L1["x"], L1["y"], L1["w"], L1["th"]),
    "L2": bar(L + L2["w"] / 2, L2["y"], L2["w"], 8),
    "L3": bar(L + L3["w"] / 2, L3["y"], L3["w"], 8),
    "L4": bar(L + L4["w"] / 2, L4["y"], L4["w"], 10),
    "L5": bar(L + BAR_W / 2, BAR_Y, BAR_W, BAR_TH),
    "L6": bar(L + DIV["w"] / 2, DIV["y"], DIV["w"], DIV["th"]),
}

ts = {k: v[0] for k, v in TM.items() if isinstance(v, list) and v and isinstance(v[0], (int, float))}
js = f"""
const tl = gsap.timeline({{ paused: true }});
const TOTAL = {TOTAL:.3f};
const S = {json.dumps({k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in STATES.items()})};
const qa = (s) => Array.from(document.querySelectorAll(s));
// masked phrase reveal: rise from below the mask, decelerate, stop
const up = (t, ids, stagger, dur) => tl.fromTo(ids.map((i) => "#" + i + "-in"), {{ yPercent: 105 }},
  {{ immediateRender: false, yPercent: 0, duration: dur || 0.48, ease: "expo.out", stagger: stagger || 0.1 }}, t);
const out = (t, ids, dur) => tl.to(ids.map((i) => "#" + i + "-in"), {{ yPercent: -105, opacity: 0, duration: dur || 0.34, ease: "power2.in" }}, t);
// the motif: a container at the shape's centre, two centred bars
const motif = (t, k, dur, ease) => {{
  const s = S[k];
  tl.to("#motif", {{ x: s.x, y: s.y, duration: dur, ease: ease || "power3.inOut" }}, t);
  tl.to("#mh", {{ width: s.hw, height: s.hh, duration: dur, ease: ease || "power3.inOut" }}, t);
  tl.to("#mv", {{ width: s.vw, height: s.vh, duration: dur, ease: ease || "power3.inOut" }}, t);
}};

tl.set(".h", {{ yPercent: 105 }}, 0);
tl.set(["#mh", "#mv"], {{ xPercent: -50, yPercent: -50 }}, 0);
tl.set("#motif", {{ x: S.P1.x, y: S.P1.y }}, 0);
tl.set("#mh", {{ width: S.P1.hw, height: S.P1.hh }}, 0);
tl.set("#mv", {{ width: S.P1.vw, height: S.P1.vh }}, 0);
tl.fromTo("#grain", {{ backgroundPosition: "0px 0px" }}, {{ backgroundPosition: "52480px 33600px", duration: TOTAL, ease: "steps(320)" }}, 0);

// ---------- s1: the numeral is already there; the camera pulls back to find it
tl.fromTo("#c1", {{ scale: 3.6, filter: "blur(4px)" }}, {{ scale: 0.978, filter: "blur(0px)", duration: 0.82, ease: "expo.out" }}, 0);
tl.to("#c1", {{ scale: 1.0, duration: 0.45, ease: "sine.inOut" }}, 0.82);
up(1.15, ["s1l0", "s1l1"], 0.12, 0.48);
// detach: the plus becomes the free motif and travels to the year
tl.set("#motif", {{ opacity: 1 }}, 2.9);
tl.set(["#p1h", "#p1v"], {{ opacity: 0 }}, 2.9);
motif(2.95, "P2", 0.65);
tl.to(["#s1num", "#s1lines"], {{ y: -70, opacity: 0, duration: 0.38, ease: "power2.in" }}, 3.0);

// ---------- s2: the welcome becomes a doorway
up(3.5, ["s2l0", "s2l1"], 0.0, 0.46);
up(3.78, ["s2l2"], 0, 0.5);
tl.fromTo("#win", {{ opacity: 0 }}, {{ immediateRender: false, opacity: 1, duration: 0.3, ease: "power1.out" }}, 5.65);
// the push: camera scales into the zero and steers its counter onto the panel; the window IS the counter until it becomes the panel
const PUSH = {json.dumps({"zx": round(zero_cx, 2), "zy": round(zero_cy, 2), "px": round(pan_cx, 2), "py": round(pan_cy, 2), "cw": round(CW, 2), "ch": round(CH, 2), "pw": round(PW, 2), "ph": round(PH, 2), "fw": FW, "fh": FH, "send": 22})};
const pushAt = (p) => {{
  const s = 1 + (PUSH.send - 1) * p, dx = (PUSH.px - PUSH.zx) * p, dy = (PUSH.py - PUSH.zy) * p;
  gsap.set("#c2", {{ x: dx, y: dy, scale: s, filter: "blur(" + (2.5 * p * p).toFixed(2) + "px)" }});
  const cx = PUSH.zx + dx, cy = PUSH.zy + dy;
  const w = Math.min(PUSH.cw * s, PUSH.pw), h = Math.min(PUSH.ch * s, PUSH.ph);
  const k = Math.min(1, Math.max(0, (PUSH.cw * s - 0.45 * PUSH.pw) / (0.55 * PUSH.pw)));
  const rx = (w / 2) * (1 - k), ry = (h / 2) * (1 - k);
  gsap.set("#win", {{ clipPath: "inset(" + (cy - h / 2).toFixed(1) + "px " + (PUSH.fw - cx - w / 2).toFixed(1) + "px " +
    (PUSH.fh - cy - h / 2).toFixed(1) + "px " + (cx - w / 2).toFixed(1) + "px round " + rx.toFixed(1) + "px / " + ry.toFixed(1) + "px)" }});
}};
const push = {{ p: 0 }};
tl.fromTo(push, {{ p: 0 }}, {{ immediateRender: false, p: 1, duration: 0.6, ease: "power3.in", onUpdate: () => pushAt(push.p) }}, 5.92);
tl.to("#motif", {{ x: S.P3.x, duration: 0.6, ease: "power2.in" }}, 5.95);
tl.to("#motif", {{ y: S.P3.y, duration: 0.6, ease: "power2.out" }}, 5.95);
tl.to("#mh", {{ width: S.P3.hw, height: S.P3.hh, duration: 0.6, ease: "power3.inOut" }}, 5.95);
tl.to("#mv", {{ width: S.P3.vw, height: S.P3.vh, duration: 0.6, ease: "power3.inOut" }}, 5.95);

// ---------- s3: the people take over
up(6.55, ["s3a0", "s3a1"], 0.08, 0.46);
up(6.78, ["s3n"], 0, 0.46);
up(6.86, ["s3b0"], 0, 0.46);
up(7.02, ["s3b1"], 0, 0.44);
tl.set("#firstf", {{ opacity: 0 }}, {TM['footage_play'][0] + 0.1:.3f});
tl.set("#lastf", {{ opacity: 1 }}, {TM['footage_play'][0] + 0.1:.3f});
out(10.3, ["s3a0", "s3a1"], 0.32);
tl.to(["#s3n-in", "#s3b0-in", "#s3b1-in"], {{ yPercent: 105, opacity: 0, duration: 0.32, ease: "power2.in" }}, 10.3);
motif(10.32, "P4", 0.6);
tl.to("#win", {{ clipPath: "inset(0px 0px 0px 0px round 0%)", duration: 0.65, ease: "power3.inOut" }}, 10.35);
tl.to("#lastf", {{ scale: 1.3, duration: 0.65, ease: "power3.inOut" }}, 10.35);
tl.fromTo("#veil", {{ opacity: 0 }}, {{ immediateRender: false, opacity: 0.84, duration: 0.75, ease: "power1.inOut" }}, 10.4);
tl.to("#veil", {{ opacity: 1, duration: 2.4, ease: "sine.inOut" }}, 12.2);

// ---------- s4: trust, slower
up(11.15, ["s4p0l0", "s4p0l1"], 0.14, 0.55);
out(12.65, ["s4p0l0", "s4p0l1"], 0.32);
up(13.1, ["s4p1l0", "s4p1l1"], 0.14, 0.55);
out(14.95, ["s4p1l0", "s4p1l1"], 0.3);
up(15.35, ["s4p2l0"], 0, 0.45);
up(15.5, ["s4p2l1"], 0, 0.62);
motif(15.78, "L1", 0.5, "power3.out");
up(16.0, ["s4p2l2"], 0, 0.45);
out(17.35, ["s4p2l0", "s4p2l1", "s4p2l2"], 0.34);
motif(17.4, "L2", 0.6);

// ---------- s5: one rising column
up(18.05, {json.dumps([f"s5c0l{i}" for i in range(len(s5c[0]))])}, 0.1, 0.48);
tl.to("#c5", {{ y: -{STEP}, duration: 0.6, ease: "power3.inOut" }}, 20.85);
tl.to({json.dumps([f"#s5c0l{i}" for i in range(len(s5c[0]))])}, {{ opacity: 0.14, duration: 0.6, ease: "power2.inOut" }}, 20.85);
motif(20.85, "L3", 0.6);
up(21.2, {json.dumps([f"s5c1l{i}" for i in range(len(s5c[1]))])}, 0.1, 0.48);
tl.to("#c5", {{ y: -{2 * STEP}, duration: 0.6, ease: "power3.inOut" }}, 23.75);
tl.to({json.dumps([f"#s5c0l{i}" for i in range(len(s5c[0]))])}, {{ opacity: 0, duration: 0.4 }}, 23.75);
tl.to({json.dumps([f"#s5c1l{i}" for i in range(len(s5c[1]))])}, {{ opacity: 0.14, duration: 0.6, ease: "power2.inOut" }}, 23.75);
up(24.05, ["s5c2l0", "s5c2l1"], 0.13, 0.48);
up(24.36, ["s5c2l2"], 0, 0.55);
motif(24.2, "L4", 0.6, "power3.out");

// ---------- s6: rise into the identity
tl.to("#c5", {{ y: -{3 * STEP}, duration: 0.6, ease: "power3.inOut" }}, 27.5);
tl.to({json.dumps([f"#s5c1l{i}" for i in range(len(s5c[1]))] + [f"#s5c2l{i}" for i in range(len(s5c[2]))])}, {{ opacity: 0, duration: 0.5, ease: "power2.in" }}, 27.5);
motif(27.5, "L5", 0.6);
tl.to("#logo-mask", {{ clipPath: "inset(0px 0px 0px 0px)", duration: 0.6, ease: "expo.out" }}, 28.1);
motif(28.35, "L6", 0.55);
up(28.5, ["s6y"], 0, 0.45);
tl.fromTo("#s6t0-in", {{ x: -40, opacity: 0, yPercent: 0 }}, {{ immediateRender: false, x: 0, opacity: 1, duration: 0.5, ease: "expo.out" }}, 28.85);
tl.fromTo("#s6t1-in", {{ x: 40, opacity: 0, yPercent: 0 }}, {{ immediateRender: false, x: 0, opacity: 1, duration: 0.5, ease: "expo.out" }}, 29.1);
tl.fromTo("#jo", {{ opacity: 0, y: 12 }}, {{ immediateRender: false, opacity: 0.95, y: 0, duration: 0.45, ease: "power2.out" }}, 29.4);

window.__timelines = window.__timelines || {{}};
window.__timelines.reel = tl;
"""

# tagline lines enter sideways, not from the mask
css += "#s6t0-in, #s6t1-in { opacity: 0; }\n"

page = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Deekshaarambh 2026</title></head>
<body>
<div id="stage" data-composition-id="reel" data-start="0" data-duration="{TOTAL:.3f}"
     data-width="{FW}" data-height="{FH}" data-fps="{C['film']['fps']}">
  <style>{css}</style>
{body}
  <script src="assets/gsap.min.js"></script>
  <script>{js}</script>
</div>
</body>
</html>
"""
(project / "index.html").write_text(page, encoding="utf-8")
print(f"composed {TOTAL:.0f}s: numeral {N1:.0f}px, panel {PW:.0f}x{PH:.0f} at y {PT:.0f}, India. {india['px']:.0f}px, script check passed")
