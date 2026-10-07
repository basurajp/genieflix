#!/usr/bin/env python3
"""Stage the Deekshaarambh 2026 brand film's assets into a project dir.

Usage:
  motion/deekshaarambh-2026-film/prep_assets.py --project <dir> \
      --logo deekshaarambh-logo.png --jain-online jain-online.png --footage learners-source.mp4

- assets/brand/deekshaarambh.png: the supplied artwork, cropped to its ink only
  (transparent margin removed). The pixels are not edited.
- assets/brand/jain-online.png: the supplied JAIN Online lockup with its navy
  ground keyed to alpha.
- assets/footage/learners.mp4: the learner clip. config.json's media block says
  where to start (footage_source_start), how long (footage_seconds, 3 s, original
  speed) and what to show (footage_crop, which keeps faces and drops app chrome).
  Muted, re-encoded with a keyframe every frame-second for seek-safe rendering.
- assets/footage/first.jpg / last.jpg: the clip's first and last frames, full
  source frame. The composition reveals the first inside the zero of 2026 and
  holds the last behind the trust section.
- assets/fonts/: Montserrat 500 and 800 (Google Fonts, OFL), the event typeface.
- assets/img/grain.png: a 256 px noise tile for the very light film grain.

Replacing the learner clip: pass --footage <new file>, adjust footage_crop /
footage_source_start in config.json if needed, rerun this and compose.py.
"""
import argparse
import json
import pathlib
import re
import subprocess
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
FF = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
LOGO_CROP = (1624, 540, 226, 741)  # w, h, x, y: the artwork's ink box in the supplied 2000x2000 file
NAVY_KEY = "0x04164B"
FONT_CSS = "https://fonts.googleapis.com/css2?family=Montserrat:wght@500;800&display=swap"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def fetch_fonts(dest):
    dest.mkdir(parents=True, exist_ok=True)
    if all((dest / f"Montserrat-{w}.ttf").is_file() for w in (500, 800)):
        return
    req = urllib.request.Request(FONT_CSS, headers={"User-Agent": "curl/8"})
    css = urllib.request.urlopen(req, timeout=30).read().decode()
    for w, url in re.findall(r"font-weight: (\d+);.*?url\(([^)]+)\) format\('truetype'\)", css, re.S):
        (dest / f"Montserrat-{w}.ttf").write_bytes(urllib.request.urlopen(url, timeout=30).read())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", required=True)
    ap.add_argument("--logo", required=True)
    ap.add_argument("--jain-online", required=True)
    ap.add_argument("--footage", required=True, help="the learner footage source (replacement point)")
    a = ap.parse_args()
    cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8-sig"))
    m = cfg["media"]
    proj = pathlib.Path(a.project).expanduser().resolve()
    for sub in ("brand", "footage", "img", "fonts", "audio"):
        (proj / "assets" / sub).mkdir(parents=True, exist_ok=True)

    w, h, x, y = LOGO_CROP
    run(FF + ["-i", a.logo, "-vf", f"crop={w}:{h}:{x}:{y}", str(proj / m["logo"])])
    run(FF + ["-i", a.jain_online, "-vf", f"format=rgba,colorkey={NAVY_KEY}:0.22:0.12", str(proj / m["jain_online"])])

    t0, dur = m["footage_source_start"], m["footage_seconds"]
    cx, cy, cw, ch = m["footage_crop"]
    fps = cfg["film"]["fps"]
    run(FF + ["-ss", f"{t0}", "-i", a.footage, "-t", f"{dur}", "-an",
              "-vf", f"crop={cw}:{ch}:{cx}:{cy},fps={fps}",
              "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p",
              "-g", str(fps), "-keyint_min", str(fps), "-sc_threshold", "0", "-movflags", "+faststart",
              str(proj / m["footage"])])
    # bridge frames: full source frames at the clip's first and last frame
    run(FF + ["-ss", f"{t0}", "-i", a.footage, "-frames:v", "1", "-q:v", "2", str(proj / m["footage_first"])])
    last = t0 + dur - 1.0 / fps
    run(FF + ["-ss", f"{last:.4f}", "-i", a.footage, "-frames:v", "1", "-q:v", "2", str(proj / m["footage_last"])])

    fetch_fonts(proj / "assets" / "fonts")
    run(FF + ["-f", "lavfi", "-i", "nullsrc=s=256x256,geq=lum='random(1)*255':cb=128:cr=128",
              "-frames:v", "1", "-pix_fmt", "gray", str(proj / "assets" / "img" / "grain.png")])
    print(f"staged brand, footage ({dur:.1f}s from {t0:.2f}s, crop {cw}x{ch}+{cx}+{cy}), fonts, grain -> {proj}/assets")


if __name__ == "__main__":
    main()
