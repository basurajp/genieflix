#!/usr/bin/env python3
"""Stage the cinematic Deeksharambh 2026 reel's assets into a project dir.

Usage:
  motion/deeksharambh-2026-cinematic/prep_assets.py --project <dir> \
      --logo deeksharambh.png --jain-online jain-online.png --cdoe jain-cdoe.png \
      --scroll scroll.mp4

What it builds (stdlib + ffmpeg only):
- assets/logo/*.png + logo.json: the Deeksharambh logo split into animatable
  pieces by connected components of its alpha: the shirorekha bar, the eight
  hanging letters (ascenders grouped with their letter), the Devanagari glyph,
  the swoosh, the teal ellipse and the three subtitle words. Pieces partition
  the logo exactly, so at rest they recompose the original pixel for pixel.
  logo.json also carries the swoosh's angular span around SWOOSH_C for the
  conic write-on mask.
- assets/img/: the whole logo (glint mask) and the two JAIN lockups keyed off navy.
- assets/tiles/tNNN.jpg: 240 framed student photos cut from the scroll
  recording at the frame-exact positions in tiles.json, plus
  assets/img/mosaic.jpg, a 20x12 grid of them (the number's face fill).
- assets/img/grain.png: a 256 px noise tile for the film-grain overlay.
"""
import argparse
import json
import pathlib
import subprocess
import tempfile
from array import array
from collections import deque

FF = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
HERE = pathlib.Path(__file__).resolve().parent

LOGO_CROP = (1624, 540, 226, 741)  # w, h, x, y — measured on the supplied 2000x2000 logo
NAVY = "0x04164B"
ALPHA_MIN = 8          # labeling threshold; fainter pixels join the nearest piece's crop anyway
SWOOSH_C = (1300, 330)  # conic centre for the swoosh write-on, logo px
SUB_TOP = 380           # the subtitle band starts below this row, logo px


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def rgba_of(path, crop=None):
    vf = ["-vf", f"crop={crop[0]}:{crop[1]}:{crop[2]}:{crop[3]}"] if crop else []
    out = run(FF + ["-i", str(path)] + vf + ["-f", "rawvideo", "-pix_fmt", "rgba", "-"],
              stdout=subprocess.PIPE).stdout
    return out


def label(mask, w, h):
    """4-connected components over a bytearray mask. Returns (labels, {id: [count, x0, y0, x1, y1]})."""
    lab = array("i", bytes(4 * w * h))
    info, n = {}, 0
    for start in range(w * h):
        if not mask[start] or lab[start]:
            continue
        n += 1
        lab[start] = n
        q = deque([start])
        x0 = x1 = start % w
        y0 = y1 = start // w
        cnt = 0
        while q:
            p = q.popleft()
            cnt += 1
            x, y = p % w, p // w
            if x < x0: x0 = x
            if x > x1: x1 = x
            if y < y0: y0 = y
            if y > y1: y1 = y
            for nb in (p - 1 if x > 0 else -1, p + 1 if x < w - 1 else -1, p - w, p + w):
                if 0 <= nb < w * h and mask[nb] and not lab[nb]:
                    lab[nb] = n
                    q.append(nb)
        info[n] = [cnt, x0, y0, x1, y1]
    return lab, info


def logo_pieces(rgba, w, h, out_dir):
    alpha = rgba[3::4]
    mask = bytearray(1 if a > ALPHA_MIN else 0 for a in alpha)
    lab, info = label(mask, w, h)
    big = {k: v for k, v in info.items() if v[0] > 2000}
    word = max(big, key=lambda k: big[k][0])
    right = [k for k in big if k != word]
    ellipse = min(right, key=lambda k: big[k][2])               # topmost: the teal ellipse
    swoosh = max(right, key=lambda k: big[k][4])                # lowest-reaching: the swoosh
    glyph = next(k for k in right if k not in (ellipse, swoosh))

    # Shirorekha: rows where the wordmark covers nearly its whole width, plus antialias rows.
    _, wx0, wy0, wx1, wy1 = big[word]
    width = wx1 - wx0 + 1
    full = [y for y in range(wy0, wy1 + 1)
            if sum(1 for x in range(wx0, wx1 + 1) if lab[y * w + x] == word) > 0.8 * width]
    b0, b1 = min(full) - 2, max(full) + 2

    piece_of = array("i", bytes(4 * w * h))  # 0 = background
    names = {}

    def name(pid, nm, group, order):
        names[pid] = (nm, group, order)

    # wordmark minus the bar band, re-labeled into letter parts
    rest = bytearray(1 if (lab[p] == word and not (b0 <= p // w <= b1)) else 0 for p in range(w * h))
    rlab, rinfo = label(rest, w, h)
    parts = {k: v for k, v in rinfo.items() if v[0] > 200}
    lower = sorted((k for k, v in parts.items() if v[2] > b1), key=lambda k: parts[k][1])
    upper = [k for k, v in parts.items() if v[4] < b0]
    owner = {}
    for u in upper:
        ux0, ux1 = parts[u][1], parts[u][3]
        ov = lambda k: max(0, min(ux1, parts[k][3]) - max(ux0, parts[k][1]))
        owner[u] = max(lower, key=ov)
    letter_id = {k: 10 + i for i, k in enumerate(lower)}
    for p in range(w * h):
        lp = lab[p]
        if not lp:
            continue
        if lp == word:
            r = rlab[p]
            if r in letter_id:
                piece_of[p] = letter_id[r]
            elif r in owner:
                piece_of[p] = letter_id[owner[r]]
            else:
                piece_of[p] = 1  # bar band (and any stray fleck)
        elif lp == glyph:
            piece_of[p] = 2
        elif lp == swoosh:
            piece_of[p] = 3
        elif lp == ellipse:
            piece_of[p] = 4
        elif info[lp][2] >= SUB_TOP:
            piece_of[p] = 5  # subtitle letters, split into words below
        else:
            piece_of[p] = 1  # stray fleck above the subtitle: rides with the bar
    name(1, "bar", "word", 0)
    for i, k in enumerate(lower):
        name(10 + i, f"l{i}", "letters", i)
    name(2, "glyph", "glyph", 0)
    name(3, "swoosh", "swoosh", 0)
    name(4, "ellipse", "ellipse", 0)

    # subtitle words: subtitle components grouped by horizontal gaps > 18 px
    subs = sorted((v for k, v in info.items() if k not in big and v[2] >= SUB_TOP), key=lambda v: v[1])
    words, cur = [], None
    for v in subs:
        if cur and v[1] - cur[3] <= 18:
            cur = [cur[0] + v[0], cur[1], min(cur[2], v[2]), max(cur[3], v[3]), max(cur[4], v[4])]
        else:
            if cur:
                words.append(cur)
            cur = list(v)
    words.append(cur)
    for i, v in enumerate(words):
        name(20 + i, f"w{i}", "subtitle", i)
    for p in range(w * h):
        if piece_of[p] == 5:
            x = p % w
            for i, v in enumerate(words):
                if v[1] - 9 <= x <= v[3] + 9:
                    piece_of[p] = 20 + i
                    break

    # faint pixels (alpha <= ALPHA_MIN) join the nearest labeled neighbour within 2 px
    for p in range(w * h):
        if piece_of[p] or not alpha[p]:
            continue
        x, y = p % w, p // w
        for r in (1, 2):
            hit = 0
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < w and 0 <= yy < h and piece_of[yy * w + xx] > 0:
                        hit = piece_of[yy * w + xx]
                        break
                if hit:
                    break
            if hit:
                piece_of[p] = -hit  # negative = assigned late, avoids cascading
                break
    for p in range(w * h):
        if piece_of[p] < 0:
            piece_of[p] = -piece_of[p]

    boxes = {}
    for p in range(w * h):
        pid = piece_of[p]
        if pid:
            x, y = p % w, p // w
            b = boxes.setdefault(pid, [x, y, x, y])
            if x < b[0]: b[0] = x
            if y < b[1]: b[1] = y
            if x > b[2]: b[2] = x
            if y > b[3]: b[3] = y

    manifest = {"size": [w, h], "bar_rows": [b0, b1], "pieces": []}
    with tempfile.TemporaryDirectory() as td:
        for pid, (x0, y0, x1, y1) in sorted(boxes.items()):
            nm, group, order = names[pid]
            pw, ph = x1 - x0 + 1, y1 - y0 + 1
            buf = bytearray(4 * pw * ph)
            for yy in range(ph):
                for xx in range(pw):
                    p = (y0 + yy) * w + (x0 + xx)
                    if piece_of[p] == pid:
                        o = 4 * (yy * pw + xx)
                        buf[o:o + 4] = rgba[4 * p:4 * p + 4]
            raw = pathlib.Path(td) / f"{nm}.raw"
            raw.write_bytes(bytes(buf))
            run(FF + ["-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{pw}x{ph}", "-i", str(raw),
                      str(out_dir / f"{nm}.png")])
            manifest["pieces"].append({"name": nm, "group": group, "order": order,
                                       "x": x0, "y": y0, "w": pw, "h": ph})

    # swoosh angular span around SWOOSH_C (CSS conic convention: 0 = up, clockwise)
    import math
    cx, cy = SWOOSH_C
    angs = []
    for p in range(w * h):
        if piece_of[p] == 3 and alpha[p] > 100:
            x, y = p % w, p // w
            angs.append(math.degrees(math.atan2(x - cx, cy - y)) % 360)
    manifest["swoosh"] = {"center": [cx, cy], "start": max(angs), "end": min(angs)}
    (out_dir / "logo.json").write_text(json.dumps(manifest, indent=1))
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", required=True)
    for flag in ("--logo", "--jain-online", "--cdoe", "--scroll"):
        ap.add_argument(flag, required=True)
    a = ap.parse_args()
    proj = pathlib.Path(a.project).expanduser().resolve()
    img, logo, tiles = proj / "assets" / "img", proj / "assets" / "logo", proj / "assets" / "tiles"
    for d in (img, logo, tiles):
        d.mkdir(parents=True, exist_ok=True)

    w, h, x, y = LOGO_CROP
    run(FF + ["-i", a.logo, "-vf", f"crop={w}:{h}:{x}:{y}", str(img / "deeksharambh.png")])
    m = logo_pieces(rgba_of(a.logo, LOGO_CROP), w, h, logo)
    print(f"logo: {len(m['pieces'])} pieces, bar rows {m['bar_rows']}, "
          f"swoosh {m['swoosh']['start']:.0f}->{m['swoosh']['end']:.0f} deg")

    for src, nm in ((a.jain_online, "jain-online.png"), (a.cdoe, "jain-cdoe.png")):
        run(FF + ["-i", src, "-vf", f"format=rgba,colorkey={NAVY}:0.22:0.12", str(img / nm)])

    spec = json.loads((HERE / "tiles.json").read_text())
    size = spec["tile"]
    for i, (frame, col, top) in enumerate(spec["tiles"]):
        # -ss (n - 0.5)/30 lands on frame n of the 30 fps recording (measured)
        run(FF + ["-ss", f"{(frame - 0.5) / 30:.4f}", "-i", a.scroll, "-frames:v", "1",
                  "-vf", f"crop={size}:{size}:{spec['cols_x'][col]}:{top}", "-q:v", "2",
                  str(tiles / f"t{i:03d}.jpg")])
    run(FF + ["-framerate", "1", "-i", str(tiles / "t%03d.jpg"),
              "-vf", "scale=58:58:flags=lanczos,tile=20x12", "-frames:v", "1", "-q:v", "2",
              str(img / "mosaic.jpg")])
    run(FF + ["-f", "lavfi", "-i", "nullsrc=s=256x256,geq=lum='random(1)*255':cb=128:cr=128",
              "-frames:v", "1", "-pix_fmt", "gray", str(img / "grain.png")])
    print(f"tiles: {len(spec['tiles'])} -> {tiles}; mosaic + grain in {img}")


if __name__ == "__main__":
    main()
