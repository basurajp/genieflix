#!/usr/bin/env python3
"""Decode a reference reel into measurements and contact sheets.

Usage: decode/decode_reel.py <video> [<video> ...] [--out <dir>] [--threshold 0.20]

What a video editor would measure by scrubbing, done with ffmpeg so the
qualitative read (named in styles/LEXICON.md) starts from numbers, not vibes:

  edit      every cut, typed: hard cut, punch-in / punch-out (same frame
            rescaled), jump cut, flash cut, dissolve, dip to black / white,
            colour wipe, whip / push candidates; shot list, average and
            median shot length, cuts in the first 3 s, cutting rate over time
  motion    per-second visual-change energy and the longest static stretch
  color     per-shot brightness, contrast, saturation, black and white points,
            shadow and highlight tint (split-tone detection), warmth, a 5-colour
            palette per shot and a 6-colour palette for the reel, plus look hints
            mapped to HyperFrames grading presets/LUT looks
  sound     integrated loudness (EBU R128), volumedetect mean, onset times,
            tempo estimate, and how many cuts land on an audio onset compared
            with chance

Outputs land in decode/refs/<video-stem>/ (or --out):

  decode.json        every measurement, machine-readable
  REPORT.md          the measured half filled in; the decode half left as
                     prompts to fill in by reading the sheets
  contact.jpg        one mid-frame per shot, labelled
  hook.jpg           the first 3 s at 10 fps (the skip-rate window)
  timeline-NN.jpg    the whole reel at 4 fps, 6 s per sheet (type animation)
  cuts/cut-NN.jpg    3 frames either side of every boundary (names the transition)
  shots/shot-NN.jpg  a large mid-frame per shot (typeface and layout detail)

Everything here is a measurement or a flagged heuristic. Transition names,
typefaces, easing and art direction are read off the sheets by a person (or
Claude), using styles/LEXICON.md — the numbers just say where to look.
"""

import argparse
import array
import json
import math
import pathlib
import random
import re
import shutil
import statistics
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "pipeline"))
import common  # noqa: E402

ANALYSIS_WIDTH = 270        # scene scoring runs on a small copy; cuts don't need pixels
SIG_W, SIG_H = 16, 28       # grey signature per frame for soft-transition tests
SOFT_SPAN_SHORT = 6         # frames either side: catches 0.2-0.4 s dissolves and whips
SOFT_SPAN_LONG = 12         # catches 0.5-1 s dissolves and dips
SOFT_ENDS_DIFF = 0.10       # mean signature difference the two ends must show
DIP_BLACK, DIP_WHITE = 0.12, 0.86   # mean grey level of a "black" / "white" frame
FLAT_SPREAD = 14            # luma 10th-90th percentile spread (8-bit) of a flat-colour frame
FLAT_MAX_FRAMES = 45        # longer flat runs are title cards, not transitions
SOFT_COLOR_SHIFT = 10.0     # YUV-average distance (8-bit levels) a camera move must cause to count
FLASH_MAX_FRAMES = 3        # a "shot" this short between two cuts is a flash/black frame
STATIC_SCORE = 0.004        # below this a frame is, to the eye, not moving
AUDIO_RATE = 22050
HOP = 512                   # ~23 ms onset-detection hop
ON_BEAT_WINDOW = 0.05       # cut within 50 ms (1.5 frames @30) of an onset counts as on it
THUMB_W, THUMB_H = 54, 96   # colour analysis thumbnail (9:16)
SHEET_W, SHEET_H = 216, 384

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
)


# ---------------------------------------------------------------- helpers

def ff(args, cwd=None, binary=False):
    """Run ffmpeg/ffprobe quietly; return stdout (bytes if binary)."""
    proc = subprocess.run(
        [str(a) for a in args], cwd=str(cwd) if cwd else None,
        capture_output=True, text=not binary,
    )
    if proc.returncode != 0:
        err = proc.stderr if not binary else proc.stderr.decode("utf-8", "replace")
        raise SystemExit(f"decode: {args[0]} failed: {err.strip()[-600:]}")
    return proc.stdout, proc.stderr


def label_font():
    for path in FONT_CANDIDATES:
        if pathlib.Path(path).is_file():
            return path
    return None


def drawtext(text_expr, font, size=22):
    """A drawtext filter for sheet labels, or '' when no font is available."""
    if not font:
        return ""
    font = font.replace("\\", "/").replace(":", "\\:")
    return (
        f",drawtext=fontfile='{font}':text='{text_expr}':x=8:y=8:fontsize={size}:"
        "fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=6"
    )


def r3(x):
    return round(float(x), 3)


def probe(video):
    out, _ = ff([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_streams", "-show_format", str(video),
    ])
    data = json.loads(out)
    vstream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not vstream:
        raise SystemExit(f"decode: no video stream in {video}")
    num, _, den = (vstream.get("avg_frame_rate") or vstream.get("r_frame_rate") or "30/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    width, height = int(vstream.get("width", 0)), int(vstream.get("height", 0))
    rotation = 0
    for side in vstream.get("side_data_list", []) or []:
        if "rotation" in side:
            rotation = int(side["rotation"])
    if abs(rotation) in (90, 270):
        width, height = height, width
    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    duration = float(data.get("format", {}).get("duration") or vstream.get("duration") or 0)
    gcd = math.gcd(width, height) or 1
    return {
        "width": width, "height": height, "aspect": f"{width // gcd}:{height // gcd}",
        "fps": round(fps, 3), "duration": r3(duration), "has_audio": has_audio,
        "video_codec": vstream.get("codec_name"),
    }


# ---------------------------------------------------------------- per-frame stats

def frame_stats(video, workdir):
    """One decode pass: signalstats + scene score for every frame."""
    stats_file = workdir / "framestats.txt"
    ff([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video), "-an",
        "-vf", f"scale={ANALYSIS_WIDTH}:-2,signalstats,select='gte(scene\\,0)',"
               "metadata=print:file=framestats.txt",
        "-f", "null", "-",
    ], cwd=workdir)
    frames, cur = [], None
    for line in stats_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("frame:"):
            m = re.search(r"pts_time:([-\d.e]+)", line)
            cur = {"t": float(m.group(1)) if m else 0.0}
            frames.append(cur)
        elif cur is not None and "=" in line:
            key, _, value = line.partition("=")
            key = key.rsplit(".", 1)[-1]
            try:
                cur[key] = float(value)
            except ValueError:
                pass
    stats_file.unlink(missing_ok=True)
    if not frames:
        raise SystemExit(f"decode: no frames decoded from {video}")
    for f in frames:
        f.setdefault("scene_score", 0.0)
    return frames


def frame_signatures(video, count):
    """A 16x28 grey thumbnail per frame (values 0..1) for span comparisons."""
    raw, _ = ff([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video), "-an",
        "-vf", f"scale={SIG_W}:{SIG_H}:flags=area,format=gray",
        "-f", "rawvideo", "-",
    ], binary=True)
    size = SIG_W * SIG_H
    sigs = [[v / 255.0 for v in raw[k: k + size]] for k in range(0, len(raw) - size + 1, size)]
    if len(sigs) < count:
        sigs += [sigs[-1]] * (count - len(sigs))
    return sigs[:count]


def sig_diff(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def yuv(f):
    return (f.get("YAVG", 0.0), f.get("UAVG", 128.0), f.get("VAVG", 128.0))


def mean_yuv(frames):
    if not frames:
        return (0.0, 128.0, 128.0)
    return tuple(statistics.fmean(yuv(f)[k] for f in frames) for k in range(3))


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


# ---------------------------------------------------------------- edit detection

def detect_boundaries(frames, sigs, threshold):
    """Hard cuts and flash frames from the scene score; soft transitions and
    dips from grey signatures compared across a span."""
    n = len(frames)
    s = [f["scene_score"] for f in frames]

    hard = []
    for i in range(3, n):  # frames 1-2 are an opening animation's first move, not a cut
        if s[i] < threshold:
            continue
        window = s[max(1, i - 2): i + 3]
        if s[i] >= max(window) and (not hard or i - hard[-1] > 1):
            hard.append(i)

    # Flash / black frames: two hard cuts a frame or three apart whose middle is
    # far brighter (or darker) than both sides — one event, not two shots.
    events, skip = [], set()
    for a, b in zip(hard, hard[1:]):
        if b - a > FLASH_MAX_FRAMES or a in skip:
            continue
        mid = statistics.fmean(frames[k]["YAVG"] for k in range(a, b))
        before = frames[a - 1]["YAVG"]
        after = frames[min(b, n - 1)]["YAVG"]
        if mid > max(before, after) + 40:
            kind = "flash-frame (white)"
        elif mid < min(before, after) - 40:
            kind = "black frame"
        else:
            kind = "flicker / very short insert"
        events.append({"frame": a, "t": r3(frames[a]["t"]), "frames": b - a, "type": kind})
        skip.update((a, b))
    boundaries = []
    for i in hard:
        if i in skip:
            continue
        boundaries.append({"frame": i, "kind": "hard"})
    for ev in events:
        # a flash between two different shots is still a boundary (flash cut);
        # between two halves of the same shot it is a flash *on* a shot.
        a, b = ev["frame"], ev["frame"] + ev["frames"]
        pre = mean_yuv(frames[max(0, a - 4): a])
        post = mean_yuv(frames[b: b + 4])
        if dist(pre, post) > SOFT_COLOR_SHIFT:
            boundaries.append({"frame": a, "kind": "flash-cut" if "flash" in ev["type"] else "hard"})

    # Soft transitions (dip, dissolve, whip, push): no single frame jumps, but
    # frames a span apart differ a lot. Dips pass through black or white and are
    # found first; for the rest, compare tiny grey signatures across a span and
    # classify by the middle frame: a dissolve's middle is the average of its
    # ends, anything else (whip, push, zoom, fast camera move) is flagged for a
    # look at the strip.
    soft, motion_bursts = [], []
    hard_set = set(hard)
    near_hard = set()
    for h in hard:
        near_hard.update(range(h - SOFT_SPAN_LONG - 2, h + SOFT_SPAN_LONG + 3))

    # Dips and colour wipes first: runs of flat frames (black, white or one
    # solid colour) that the edit passes through. Entered and left by hard cuts
    # they are flash/black-frame inserts (handled above); at the very start or
    # end they are fades in/out; long runs are title cards, not transitions.
    lum = [statistics.fmean(sig) for sig in sigs]
    flat = [f.get("YHIGH", 255) - f.get("YLOW", 0) < FLAT_SPREAD for f in frames]

    def differs(k, mid):
        return not flat[k] or abs(lum[k] - lum[mid]) > 0.1

    i = 0
    while i < n:
        if not flat[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and flat[j + 1]:
            j += 1
        run = range(i, j + 1)
        darkest = min(run, key=lambda k: lum[k])
        brightest = max(run, key=lambda k: lum[k])
        if lum[darkest] < DIP_BLACK:
            mid, name, shade = darkest, "dip to black", "black"
        elif lum[brightest] > DIP_WHITE:
            mid, name, shade = brightest, "dip to white", "white"
        else:
            mid = (i + j) // 2
            u, v = frames[mid].get("UAVG", 128), frames[mid].get("VAVG", 128)
            name, shade = "colour wipe / dip through colour", f"colour (U{u:.0f} V{v:.0f})"
        # look outward from the run's extreme frame for picture that differs:
        # a fade into a flat shot is still a dip, a flat shot alone is a card
        reach = 2 * SOFT_SPAN_LONG
        lo = next((k for k in range(mid - 1, max(-1, mid - reach - 1), -1) if differs(k, mid)), None)
        hi = next((k for k in range(mid + 1, min(n, mid + reach + 1)) if differs(k, mid)), None)
        hard_edges = any(k in hard_set for k in range(i - 1, i + 2)) and any(
            k in hard_set for k in range(j, j + 3))
        varies = max(lum[k] for k in run) - min(lum[k] for k in run) > 0.1
        if lo is None and i == 0:
            events.append({"frame": j, "t": r3(frames[j]["t"]), "frames": j + 1, "type": f"opens on {shade}"})
        elif hi is None and j == n - 1:
            events.append({"frame": i, "t": r3(frames[i]["t"]), "frames": n - i, "type": f"ends on {shade}"})
        elif j - i + 1 > FLAT_MAX_FRAMES and not varies:
            events.append({"frame": i, "t": r3(frames[i]["t"]), "frames": j - i + 1, "type": f"flat {shade} card"})
        elif not hard_edges and lo is not None and hi is not None:
            entry = {"start": r3(frames[lo]["t"]), "end": r3(frames[hi]["t"]), "type": name,
                     "held_frames": j - i + 1}
            soft.append(entry)
            boundaries.append({"frame": mid, "kind": "soft", "soft_type": name, "run": entry})
            # the fade either side belongs to this dip, not to a second transition
            near_hard.update(range(mid - reach - SOFT_SPAN_LONG, mid + reach + SOFT_SPAN_LONG + 1))
        i = j + 1
    step = [0.0] + [sig_diff(sigs[k], sigs[k - 1]) for k in range(1, n)]
    cands = []
    for span in (SOFT_SPAN_SHORT, SOFT_SPAN_LONG):
        for i in range(span, n - span):
            if i in near_hard:
                continue
            a, b, m = sigs[i - span], sigs[i + span], sigs[i]
            ends = sig_diff(a, b)
            if ends < SOFT_ENDS_DIFF:
                continue
            steps = max(step[i - span + 1: i + span + 1])
            if steps > ends * 0.6:
                continue  # one frame carries most of the change: a hard cut, not a soft one
            blend = [(x + y) / 2 for x, y in zip(a, b)]
            residual = sig_diff(m, blend) / ends
            cands.append((ends, i, span, residual))
    taken = []
    for ends, i, span, residual in sorted(cands, reverse=True):
        if any(abs(i - j) <= 2 * SOFT_SPAN_LONG for j in taken):
            continue
        taken.append(i)
        lo, hi = max(0, i - span), min(n - 1, i + span)
        if residual < 0.35:
            kind = "dissolve"
        else:
            kind = "whip / push / zoom / camera move"
        pre = mean_yuv(frames[max(0, lo - 5): lo])
        post = mean_yuv(frames[hi + 1: hi + 6])
        entry = {
            "start": r3(frames[lo]["t"]), "end": r3(frames[hi]["t"]),
            "type": kind, "change": round(ends, 3), "blend_residual": round(residual, 2),
            "color_shift": round(dist(pre, post), 1),
        }
        # without a colour change a soft move may be a camera move, or a push
        # between two similar (e.g. black-and-white) shots: listed for review
        if kind == "whip / push / zoom / camera move" and entry["color_shift"] < SOFT_COLOR_SHIFT:
            motion_bursts.append(entry)
            continue
        if lo < 15:
            # the first half second: an opening entrance, not a cut between shots
            events.append({"frame": i, "t": r3(frames[i]["t"]), "frames": hi - lo + 1, "type": "opening move"})
            continue
        soft.append(entry)
        boundaries.append({"frame": i, "kind": "soft", "soft_type": kind, "run": entry})

    # a wipe or dip's own entry/exit frames can trip the hard-cut test: those
    # cuts belong to the transition
    flat_mids = [b["frame"] for b in boundaries if b.get("soft_type", "").startswith(("dip", "colour"))]
    boundaries = [b for b in boundaries
                  if not (b["kind"] == "hard" and any(abs(b["frame"] - m) <= 8 for m in flat_mids))]
    boundaries.sort(key=lambda b: b["frame"])
    for b in boundaries:
        b["t"] = r3(frames[b["frame"]]["t"])
        b["score"] = round(s[b["frame"]], 3)
        lo, hi = max(0, b["frame"] - 6), min(n, b["frame"] + 7)
        ys = [frames[k]["YAVG"] for k in range(lo, hi)]
        if min(ys) < 24:
            b["dip"] = "black"
        elif max(ys) > 225:
            b["dip"] = "white"
    return boundaries, events, motion_bursts


PUNCH_W, PUNCH_H = 36, 64      # grey thumbnails for the punch-in test
PUNCH_SCALES = [1.06 + 0.04 * k for k in range(10)]   # 1.06 .. 1.42
PUNCH_CENTRES = [(cx, cy) for cy in (0.38, 0.5, 0.62) for cx in (0.4, 0.5, 0.6)]
# compare only the picture band between the top UI/titles and the caption band,
# so a caption changing on the cut doesn't hide a punch-in
BAND = (int(PUNCH_H * 0.12), int(PUNCH_H * 0.64))


def frame_thumbs(video):
    """Every frame as a 36x64 grey thumbnail, one decode pass, kept as bytes."""
    raw, _ = ff([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video), "-an",
        "-vf", f"scale={PUNCH_W}:{PUNCH_H}:flags=area,format=gray", "-f", "rawvideo", "-",
    ], binary=True)
    size = PUNCH_W * PUNCH_H
    return [raw[k: k + size] for k in range(0, len(raw) - size + 1, size)]


def zoom_maps():
    """Source-pixel index maps for every candidate punch (scale, centre), banded."""
    w, h = PUNCH_W, PUNCH_H
    maps = []
    for sc in PUNCH_SCALES:
        for cx, cy in PUNCH_CENTRES:
            ox, oy = cx * w, cy * h
            idx = []
            for y in range(*BAND):
                sy = min(h - 1, max(0, int((y - oy) / sc + oy)))
                for x in range(w):
                    idx.append(sy * w + min(w - 1, max(0, int((x - ox) / sc + ox))))
            maps.append((sc, idx))
    return maps


def band_diff(a_vals, b_vals):
    return sum(abs(x - y) for x, y in zip(a_vals, b_vals)) / (len(a_vals) * 255.0)


def classify_cuts(video, frames, boundaries):
    """Name hard cuts an editor would name differently: a punch-in (the next
    shot is the same frame magnified), a punch-out, or a jump cut (same set-up,
    subject moved). Everything else stays a plain cut to a new shot."""
    hard = [b for b in boundaries if b["kind"] == "hard" and b["frame"] >= 1]
    if not hard:
        return
    thumbs = frame_thumbs(video)
    maps = zoom_maps()
    band = range(BAND[0] * PUNCH_W, BAND[1] * PUNCH_W)
    for b in hard:
        k = b["frame"]
        if k >= len(thumbs):
            continue
        before, after = thumbs[k - 1], thumbs[k]
        direct = band_diff([before[i] for i in band], [after[i] for i in band])
        after_band = [after[i] for i in band]
        before_band = [before[i] for i in band]
        best = (direct, None, None)
        for sc, idx in maps:
            zin = band_diff([before[i] for i in idx], after_band)
            if zin < best[0]:
                best = (zin, "punch-in", sc)
            zout = band_diff(before_band, [after[i] for i in idx])
            if zout < best[0]:
                best = (zout, "punch-out", sc)
        diff, kind, scale = best
        yuv_shift = dist(mean_yuv(frames[max(0, k - 3): k]), mean_yuv(frames[k: k + 3]))
        if kind and diff < 0.09 and diff < direct * 0.65:
            b["cut_type"] = f"{kind} ×{scale:.2f}"
        elif direct < 0.06 and yuv_shift < 6:
            b["cut_type"] = "jump cut (same set-up)"


def shot_list(frames, boundaries, duration):
    starts = [0.0] + [b["t"] for b in boundaries]
    ends = starts[1:] + [duration]
    shots = []
    for k, (a, b) in enumerate(zip(starts, ends), 1):
        if b - a <= 0:
            continue
        shots.append({"index": k, "start": r3(a), "end": r3(b), "duration": r3(b - a)})
    return shots


def edit_summary(shots, boundaries, duration):
    lengths = [s["duration"] for s in shots]
    cuts = [b["t"] for b in boundaries]
    windows = []
    t = 0.0
    while t < duration:
        windows.append({"from": r3(t), "to": r3(min(t + 5, duration)),
                        "cuts": sum(1 for c in cuts if t <= c < t + 5)})
        t += 5
    kinds = {}
    for b in boundaries:
        name = b.get("soft_type") or (b.get("cut_type", "").split(" ×")[0] if b.get("cut_type") else b["kind"])
        kinds[name] = kinds.get(name, 0) + 1
    return {
        "shots": len(shots),
        "boundaries": len(boundaries),
        "by_kind": kinds,
        "asl": r3(statistics.fmean(lengths)) if lengths else 0,
        "median_shot": r3(statistics.median(lengths)) if lengths else 0,
        "shortest_shot": r3(min(lengths)) if lengths else 0,
        "longest_shot": r3(max(lengths)) if lengths else 0,
        "cuts_per_10s": r3(len(cuts) / duration * 10) if duration else 0,
        "cuts_in_first_3s": sum(1 for c in cuts if c < 3.0),
        "first_cut_at": r3(cuts[0]) if cuts else None,
        "cutting_rate_5s_windows": windows,
    }


def motion_summary(frames, duration, fps):
    per_sec = {}
    for f in frames:
        per_sec.setdefault(int(f["t"]), []).append(f["scene_score"])
    energy = [{"second": k, "energy": round(statistics.fmean(v) * 100, 2)}
              for k, v in sorted(per_sec.items())]
    longest, run_start, best = 0.0, None, None
    for f in frames:
        if f["scene_score"] < STATIC_SCORE:
            if run_start is None:
                run_start = f["t"]
            span = f["t"] - run_start
            if span > longest:
                longest, best = span, run_start
        else:
            run_start = None
    return {
        "energy_per_second": energy,
        "mean_energy": round(statistics.fmean(f["scene_score"] for f in frames) * 100, 2),
        "longest_static_stretch": r3(longest),
        "longest_static_at": r3(best) if best is not None else None,
        "note": "energy = mean ffmpeg scene score x100 (0 = frozen, >5 = constant motion); "
                "a static stretch over ~3 s is where the playbook says viewers scroll",
    }


# ---------------------------------------------------------------- colour

def thumb_pixels(video, t):
    raw, _ = ff([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(video),
        "-frames:v", "1", "-vf", f"scale={THUMB_W}:{THUMB_H}:flags=area",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ], binary=True)
    px = [(raw[k] / 255.0, raw[k + 1] / 255.0, raw[k + 2] / 255.0)
          for k in range(0, len(raw) - 2, 3)]
    return px


def luma(p):
    return 0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]


def rgb_to_hsv(p):
    r, g, b = p
    mx, mn = max(p), min(p)
    d = mx - mn
    if d == 0:
        h = 0.0
    elif mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h * 60.0, (d / mx if mx else 0.0), mx


HUE_NAMES = (
    (15, "red"), (45, "orange"), (70, "yellow"), (150, "green"), (195, "teal/cyan"),
    (255, "blue"), (290, "purple"), (330, "magenta"), (360, "red"),
)


def hue_name(h):
    for limit, name in HUE_NAMES:
        if h < limit:
            return name
    return "red"


def tint(pixels):
    """Hue name + strength of the average colour of a pixel set."""
    if not pixels:
        return None
    mean = tuple(statistics.fmean(p[k] for p in pixels) for k in range(3))
    h, s, _ = rgb_to_hsv(mean)
    return {"hue": round(h), "name": hue_name(h) if s > 0.04 else "neutral",
            "strength": round(s, 3), "rgb": to_hex(mean)}


def to_hex(p):
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02x}" for c in p)


def kmeans(pixels, k, iters=12, seed=7):
    """Deterministic k-means++ in plain Python; returns [(hex, share)]."""
    if not pixels:
        return []
    rng = random.Random(seed)
    pts = pixels if len(pixels) <= 6000 else rng.sample(pixels, 6000)
    centers = [pts[rng.randrange(len(pts))]]
    while len(centers) < k:
        d2 = [min(sum((a - b) ** 2 for a, b in zip(p, c)) for c in centers) for p in pts]
        total = sum(d2)
        if total == 0:
            break
        r, acc = rng.random() * total, 0.0
        for p, d in zip(pts, d2):
            acc += d
            if acc >= r:
                centers.append(p)
                break
    for _ in range(iters):
        groups = [[] for _ in centers]
        for p in pts:
            j = min(range(len(centers)), key=lambda c: sum((a - b) ** 2 for a, b in zip(p, centers[c])))
            groups[j].append(p)
        centers = [tuple(statistics.fmean(p[d] for p in g) for d in range(3)) if g else centers[j]
                   for j, g in enumerate(groups)]
    counts = [0] * len(centers)
    for p in pts:
        j = min(range(len(centers)), key=lambda c: sum((a - b) ** 2 for a, b in zip(p, centers[c])))
        counts[j] += 1
    order = sorted(range(len(centers)), key=lambda j: -counts[j])
    return [{"hex": to_hex(centers[j]), "share": round(counts[j] / len(pts), 3)} for j in order]


def color_profile(pixels):
    ls = sorted(luma(p) for p in pixels)
    pct = lambda q: ls[min(len(ls) - 1, int(q * (len(ls) - 1)))]  # noqa: E731
    hsv = [rgb_to_hsv(p) for p in pixels]
    shadows = [p for p in pixels if luma(p) < 0.3]
    highs = [p for p in pixels if luma(p) > 0.7]
    mids = [p for p in pixels if 0.3 <= luma(p) <= 0.7] or pixels
    return {
        "brightness": round(statistics.fmean(ls), 3),
        "contrast": round(pct(0.95) - pct(0.05), 3),
        "black_point": round(pct(0.02), 3),
        "white_point": round(pct(0.98), 3),
        "saturation": round(statistics.fmean(s for _, s, _ in hsv), 3),
        "warmth": round(statistics.fmean(p[0] - p[2] for p in mids), 3),
        "shadow_tint": tint(shadows),
        "highlight_tint": tint(highs),
    }


WARM = {"red", "orange", "yellow"}
COOL = {"teal/cyan", "blue", "green"}


def look_hints(prof):
    """Heuristic grade names (LEXICON.md) + the HyperFrames grading to start from."""
    hints = []
    sat, con = prof["saturation"], prof["contrast"]
    st, ht = prof.get("shadow_tint") or {}, prof.get("highlight_tint") or {}
    if sat < 0.06:
        hints.append(("monochrome", '{"preset":"mono-clean"}'))
    elif sat < 0.2 and con > 0.6:
        hints.append(("bleach bypass", 'LUT look "bleach-bypass"'))
    if st.get("name") in COOL and ht.get("name") in WARM and st.get("strength", 0) > 0.06:
        hints.append(("teal & orange split tone", 'LUT look "teal-orange-blockbuster"'))
    elif st.get("strength", 0) > 0.08 and ht.get("strength", 0) > 0.08 and st.get("name") != ht.get("name"):
        hints.append((f"split tone ({st.get('name')} shadows / {ht.get('name')} highlights)",
                      "wheels: shadows/highlights hue"))
    if prof["black_point"] > 0.08 and con < 0.75:
        hints.append(("matte / lifted blacks (film fade)", 'LUT look "film-fade" or {"preset":"vintage-wash"}'))
    if prof["black_point"] < 0.01 and con > 0.75:
        hints.append(("crushed blacks / deep contrast", '{"preset":"deep-contrast"}'))
    if prof["white_point"] < 0.82:
        hints.append(("rolled-off highlights", "curves: lower the white point"))
    if sat > 0.42 and prof["brightness"] > 0.45:
        hints.append(("bright pop / saturated creator look", '{"preset":"bright-pop"}'))
    if prof["brightness"] < 0.25:
        hints.append(("low-key", '{"preset":"night-lift"} if detail must survive'))
    elif prof["brightness"] > 0.65 and con < 0.7:
        hints.append(("high-key", '{"preset":"clean-studio"}'))
    if prof["warmth"] > 0.08 and not any("teal" in h[0] for h in hints):
        hints.append(("warm cast", '{"preset":"warm-daylight"}'))
    elif prof["warmth"] < -0.06:
        hints.append(("cool cast", "adjust.temperature < 0"))
    if 0.06 <= sat < 0.2 and con <= 0.6 and not hints:
        hints.append(("muted / desaturated editorial", '{"preset":"muted-editorial"}'))
    return [{"look": a, "rebuild_with": b} for a, b in hints]


def color_analysis(video, shots):
    all_px = []
    for shot in shots:
        t = shot["start"] + shot["duration"] / 2
        px = thumb_pixels(video, t)
        all_px.extend(px)
        prof = color_profile(px)
        shot["color"] = prof
        shot["palette"] = kmeans(px, 5)
        shot["look_hints"] = [h["look"] for h in look_hints(prof)]
    overall = color_profile(all_px)
    return overall, kmeans(all_px, 6, iters=10), look_hints(overall)


# ---------------------------------------------------------------- sound

def audio_analysis(video, duration, cut_times):
    raw, _ = ff([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video), "-vn",
        "-ac", "1", "-ar", str(AUDIO_RATE), "-f", "s16le", "-",
    ], binary=True)
    pcm = array.array("h")
    pcm.frombytes(raw[: len(raw) - len(raw) % 2])
    if sys.byteorder == "big":
        pcm.byteswap()
    if len(pcm) < HOP * 8:
        return {"note": "audio too short to analyse"}

    hop_s = HOP / AUDIO_RATE
    energy = []
    for k in range(0, len(pcm) - HOP, HOP):
        frame = pcm[k: k + HOP]
        energy.append(sum(x * x for x in frame) / HOP)
    log_e = [math.log10(e + 1.0) for e in energy]
    odf = [0.0] + [max(0.0, log_e[i] - log_e[i - 1]) for i in range(1, len(log_e))]

    # Peak-pick: local max over +-3 hops, above a 0.5 s moving mean + one std.
    std = statistics.pstdev(odf) or 1e-9
    half = int(0.25 / hop_s)
    onsets, last = [], -1.0
    for i in range(3, len(odf) - 3):
        if odf[i] < max(odf[i - 3: i + 4]):
            continue
        local = odf[max(0, i - half): i + half]
        if odf[i] > statistics.fmean(local) + std * 0.8 and i * hop_s - last > 0.1:
            onsets.append(i * hop_s)
            last = i * hop_s

    # Tempo: autocorrelation of the onset envelope, 60-180 BPM, with a mild
    # log-gaussian prior at 120 BPM to dodge octave errors.
    m = statistics.fmean(odf)
    x = [v - m for v in odf]
    best, best_lag, ac0 = -1e18, None, sum(v * v for v in x) or 1e-9
    for lag in range(int(60 / 180 / hop_s), int(60 / 60 / hop_s) + 1):
        ac = sum(x[i] * x[i - lag] for i in range(lag, len(x))) / ac0
        bpm = 60 / (lag * hop_s)
        weight = math.exp(-0.5 * (math.log2(bpm / 120) / 0.9) ** 2)
        if ac * weight > best:
            best, best_lag = ac * weight, lag
    bpm = 60 / (best_lag * hop_s) if best_lag else None
    confidence = round(best, 3)

    on_beat = 0
    for c in cut_times:
        if any(abs(c - o) <= ON_BEAT_WINDOW for o in onsets):
            on_beat += 1
    covered = min(1.0, len(onsets) * 2 * ON_BEAT_WINDOW / duration) if duration else 0
    _, err = ff(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vn",
                 "-af", "ebur128=framelog=quiet", "-f", "null", "-"])
    lufs = re.search(r"I:\s*(-?[\d.]+)\s*LUFS", err)
    lra = re.search(r"LRA:\s*([\d.]+)\s*LU", err)
    vd = common.volumedetect(video)
    return {
        "integrated_lufs": float(lufs.group(1)) if lufs else None,
        "loudness_range_lu": float(lra.group(1)) if lra else None,
        "volumedetect_mean_db": vd["mean_db"], "volumedetect_peak_db": vd["max_db"],
        "pipeline_gate": "-17..-13 dB mean (volumedetect)",
        "onsets": [r3(o) for o in onsets],
        "onsets_per_second": round(len(onsets) / duration, 2) if duration else 0,
        "tempo_bpm": round(bpm, 1) if bpm else None,
        "tempo_confidence": confidence,
        "cuts_on_onset": on_beat,
        "cuts_total": len(cut_times),
        "cuts_on_onset_ratio": round(on_beat / len(cut_times), 2) if cut_times else None,
        "chance_ratio": round(covered, 2),
        "note": "onsets include speech syllables as well as music hits; cutting is "
                "beat-driven only when cuts_on_onset_ratio clearly beats chance_ratio",
    }


# ---------------------------------------------------------------- sheets

def make_sheets(video, out_dir, shots, boundaries, frames, duration):
    font = label_font()
    for sub in ("shots", "cuts"):
        d = out_dir / sub
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    for old in out_dir.glob("timeline-*.jpg"):
        old.unlink()

    # contact sheet: one labelled mid-frame per shot
    tmp = out_dir / "_contact"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    for k, shot in enumerate(shots, 1):
        t = shot["start"] + shot["duration"] / 2
        label = f"#{shot['index']:02d}  {shot['start']:.2f}s  ({shot['duration']:.2f}s)"
        ff(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video),
            "-frames:v", "1", "-vf", f"scale={SHEET_W}:{SHEET_H}" + drawtext(label.replace(":", "\\:"), font, 15),
            str(tmp / f"c{k:04d}.png")])
        ff(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video),
            "-frames:v", "1", "-vf", "scale=540:-2", "-q:v", "3",
            str(out_dir / "shots" / f"shot-{shot['index']:02d}.jpg")])
    cols = 6
    rows = max(1, math.ceil(len(shots) / cols))
    ff(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "1",
        "-i", str(tmp / "c%04d.png"), "-vf", f"tile={cols}x{rows}:padding=4:color=0x111111",
        "-frames:v", "1", "-q:v", "3", str(out_dir / "contact.jpg")])
    shutil.rmtree(tmp)

    # hook: first 3 s at 10 fps
    ff(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-t", "3",
        "-vf", f"fps=10,scale={SHEET_W}:{SHEET_H}" + drawtext("%{pts\\:hms}", font, 16)
        + ",tile=6x5:padding=4:color=0x111111",
        "-frames:v", "1", "-q:v", "3", str(out_dir / "hook.jpg")])

    # timeline: whole reel at 4 fps, 24 frames (6 s) per sheet
    ff(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
        "-vf", f"fps=4,scale={SHEET_W}:{SHEET_H}" + drawtext("%{pts\\:hms}", font, 16)
        + ",tile=6x4:padding=4:color=0x111111",
        "-q:v", "3", "-fps_mode", "passthrough", str(out_dir / "timeline-%02d.jpg")])

    # cut strips: 3 frames either side of every boundary
    times = [f["t"] for f in frames]
    for k, b in enumerate(boundaries[:80], 1):
        i = b["frame"]
        lo, hi = max(0, i - 3), min(len(frames) - 1, i + 2)
        t0, t1 = times[lo], times[hi]
        ff(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-copyts",
            "-ss", f"{max(0.0, t0 - 1.0):.3f}", "-i", str(video),
            "-vf", f"select='between(t\\,{t0 - 0.004:.4f}\\,{t1 + 0.004:.4f})',"
                   f"scale={SHEET_W}:{SHEET_H}" + drawtext("%{pts\\:hms}", font, 16)
                   + f",tile={hi - lo + 1}x1:padding=4:color=0x111111",
            "-frames:v", "1", "-q:v", "3", str(out_dir / "cuts" / f"cut-{k:02d}.jpg")])
    return {"labels": bool(font), "timeline_sheets": len(list(out_dir.glob("timeline-*.jpg")))}


# ---------------------------------------------------------------- report

def fmt_palette(pal):
    return " ".join(f"`{p['hex']}` {round(p['share'] * 100)}%" for p in pal)


def write_report(out_dir, name, data):
    m, e, mo, c = data["media"], data["edit"], data["motion"], data["color"]
    a = data.get("audio") or {}
    st, ht = c["overall"].get("shadow_tint") or {}, c["overall"].get("highlight_tint") or {}
    hints = "\n".join(f"- {h['look']} — start from {h['rebuild_with']}" for h in c["look_hints"]) or "- none flagged"
    shot_rows = "\n".join(
        f"| {s['index']} | {s['start']:.2f} | {s['duration']:.2f} | {s['color']['brightness']:.2f} | "
        f"{s['color']['contrast']:.2f} | {s['color']['saturation']:.2f} | {', '.join(s['look_hints']) or '—'} | "
        f"{fmt_palette(s['palette'][:3])} |"
        for s in data["shots"]
    )
    bound_rows = "\n".join(
        f"| {k} | {b['t']:.2f} | {b.get('soft_type') or b.get('cut_type') or b['kind']}{' + dip to ' + b['dip'] if b.get('dip') and not b.get('soft_type', '').startswith('dip') else ''} | {b['score']:.2f} | `cuts/cut-{k:02d}.jpg` |"
        for k, b in enumerate(data["boundaries"], 1)
    ) or "| — | — | no boundaries: a oner | — | — |"
    events = "\n".join(f"- {ev['t']:.2f}s {ev['type']} ({ev['frames']} frame{'s' if ev['frames'] > 1 else ''})"
                       for ev in data["events"]) or "- none"
    bursts = "\n".join(f"- {mb['start']:.2f}–{mb['end']:.2f}s (change {mb['change']})"
                       for mb in data["motion_bursts"]) or "- none"
    audio_block = (
        f"- Integrated loudness **{a.get('integrated_lufs')} LUFS**, LRA {a.get('loudness_range_lu')} LU; "
        f"volumedetect mean {a.get('volumedetect_mean_db')} dB (our gate: −17..−13)\n"
        f"- Tempo estimate **{a.get('tempo_bpm')} BPM** (confidence {a.get('tempo_confidence')}); "
        f"{a.get('onsets_per_second')} onsets/s\n"
        f"- Cuts on an audio onset: **{a.get('cuts_on_onset')}/{a.get('cuts_total')}** "
        f"(ratio {a.get('cuts_on_onset_ratio')} vs chance {a.get('chance_ratio')})"
        if a.get("tempo_bpm") is not None or a.get("integrated_lufs") is not None
        else "- no audio track" if not m["has_audio"] else f"- {a.get('note')}"
    )
    text = f"""# Decode — {name}

Source: `{data['source']}` · {m['width']}×{m['height']} ({m['aspect']}) · {m['fps']} fps · {m['duration']:.2f} s

The **Measured** half is generated by `decode/decode_reel.py`. The **Decoded** half
is filled in by reading `hook.jpg`, `contact.jpg`, `timeline-*.jpg`, `cuts/` and
`shots/`, using the names in `styles/LEXICON.md`. Heuristic labels below are
pointers, not verdicts — the sheets overrule them.

## Measured

### Edit
- **{e['shots']} shots**, {e['boundaries']} boundaries {e['by_kind']}
- ASL **{e['asl']:.2f} s**, median {e['median_shot']:.2f} s, range {e['shortest_shot']:.2f}–{e['longest_shot']:.2f} s
- **{e['cuts_per_10s']:.1f} cuts / 10 s**; {e['cuts_in_first_3s']} cut(s) in the first 3 s; first cut at {e['first_cut_at']} s
- Cutting rate by 5 s window: {', '.join(str(w['cuts']) for w in e['cutting_rate_5s_windows'])}

| # | at (s) | type | score | strip |
|---|---|---|---|---|
{bound_rows}

Flash, black-frame and fade events:
{events}

Possible transitions or camera moves (soft change without a colour shift —
check `timeline-*.jpg` at these times):
{bursts}

### Motion
- Mean visual-change energy **{mo['mean_energy']}** (0 frozen, >5 constant motion)
- Longest static stretch **{mo['longest_static_stretch']:.2f} s** at {mo['longest_static_at']} s
- Energy per second: {', '.join(str(x['energy']) for x in mo['energy_per_second'])}

### Color
- Brightness {c['overall']['brightness']:.2f} · contrast {c['overall']['contrast']:.2f} · saturation {c['overall']['saturation']:.2f} · warmth {c['overall']['warmth']:+.2f}
- Black point {c['overall']['black_point']:.3f} · white point {c['overall']['white_point']:.3f}
- Shadow tint **{st.get('name')}** ({st.get('strength')}) · highlight tint **{ht.get('name')}** ({ht.get('strength')})
- Reel palette: {fmt_palette(c['palette'])}

Look hints:
{hints}

| shot | start | dur | bright | contrast | sat | hints | palette |
|---|---|---|---|---|---|---|---|
{shot_rows}

### Sound
{audio_block}

## Decoded

Fill each with lexicon names, then the concrete numbers that rebuild it.

### Format
<!-- e.g. faceless B-roll + VO, talking head + inserts, POV, listicle, green-screen, split-screen -->

### Hook (0–3 s, `hook.jpg`)
<!-- what is on screen at 0.2 s; text promise; motion from frame zero; first cut timing -->

### Edit grammar (`cuts/`)
<!-- per boundary: hard cut / jump cut / match cut / smash cut / whip / zoom / flash / dissolve / J- or L-cut -->

### Pacing
<!-- ASL vs our default; where it speeds up or breathes; does it cut on the beat? -->

### Motion design (`timeline-*.jpg`)
<!-- entrances, easing family (expo/back/elastic/linear/stepped), overshoot, camera moves, punch-ins, shake, parallax -->

### Typography
<!-- classification (grotesk / geometric / serif / condensed / mono), weight, case, size, placement, colour,
     animation (word pop / karaoke highlight / typewriter / mask reveal / stagger / scramble), caption style -->

### Color & finishing
<!-- grade name, shadow/highlight tint, contrast curve, texture (grain, halation, vignette, VHS, halftone) -->

### Art direction
<!-- the named style(s) from LEXICON.md and the 3 traits that make it read that way -->

### Sound design
<!-- music genre/BPM, whooshes on cuts, risers, impacts, ducking, silence beats -->

### Rebuild recipe
<!-- template (templates/<style>), style.json knobs, grade payload, fonts, pacing numbers, SFX placement -->
"""
    (out_dir / "REPORT.md").write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- main

def decode(video, out_dir, threshold=0.20, sheets=True):
    out_dir.mkdir(parents=True, exist_ok=True)
    media = probe(video)
    print(f"decode: {video.name}: {media['width']}x{media['height']} {media['fps']}fps {media['duration']:.2f}s")
    frames = frame_stats(video, out_dir)
    duration = media["duration"] or frames[-1]["t"]
    sigs = frame_signatures(video, len(frames))
    boundaries, events, bursts = detect_boundaries(frames, sigs, threshold)
    classify_cuts(video, frames, boundaries)
    shots = shot_list(frames, boundaries, duration)
    edit = edit_summary(shots, boundaries, duration)
    motion = motion_summary(frames, duration, media["fps"])
    print(f"decode: {edit['shots']} shots, ASL {edit['asl']:.2f}s, {edit['cuts_per_10s']:.1f} cuts/10s")
    overall, palette, hints = color_analysis(video, shots)
    audio = audio_analysis(video, duration, [b["t"] for b in boundaries]) if media["has_audio"] else None
    data = {
        "source": video.name, "media": media, "threshold": threshold,
        "edit": edit, "boundaries": [{k: v for k, v in b.items() if k != "frame"} for b in boundaries],
        "events": events, "motion_bursts": bursts, "motion": motion, "shots": shots,
        "color": {"overall": overall, "palette": palette, "look_hints": hints},
        "audio": audio,
    }
    if sheets:
        data["sheets"] = make_sheets(video, out_dir, shots, boundaries, frames, duration)
    (out_dir / "decode.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_report(out_dir, video.stem, data)
    print(f"decode: wrote {out_dir}/REPORT.md, decode.json" + (", sheets" if sheets else ""))
    return data


def main():
    ap = argparse.ArgumentParser(description="Measure a reference reel and build contact sheets for decoding it.")
    ap.add_argument("videos", nargs="+", help="reference video file(s)")
    ap.add_argument("--out", help="output directory (single video only; default decode/refs/<stem>/)")
    ap.add_argument("--threshold", type=float, default=0.20,
                    help="scene score for a hard cut (default 0.20, low enough for punch-ins and jump "
                         "cuts; raise to ~0.3 if fast handheld motion shows up as false cuts)")
    ap.add_argument("--no-sheets", action="store_true", help="measurements only, no images")
    args = ap.parse_args()
    if args.out and len(args.videos) > 1:
        raise SystemExit("decode: --out works with a single video; omit it for batches")
    for v in args.videos:
        video = pathlib.Path(v).expanduser().resolve()
        if not video.is_file():
            raise SystemExit(f"decode: not a file: {video}")
        slug = re.sub(r"[^a-z0-9]+", "-", video.stem.lower()).strip("-") or "reel"
        out_dir = pathlib.Path(args.out).expanduser().resolve() if args.out else REPO_ROOT / "decode" / "refs" / slug
        decode(video, out_dir, args.threshold, sheets=not args.no_sheets)


if __name__ == "__main__":
    main()
