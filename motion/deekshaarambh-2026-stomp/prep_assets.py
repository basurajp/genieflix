#!/usr/bin/env python3
"""Stage the stomp piece's non-face assets into a project dir.

Usage:
  motion/deekshaarambh-2026-stomp/prep_assets.py --project <dir> --scroll scroll.mp4 \
      (--brand-dir <film project>/assets/brand | --logo deekshaarambh-logo.png --jain-online jain-online.png)

- assets/brand/deekshaarambh.png, jain-online.png: the authentic artwork and the
  JAIN Online lockup, staged exactly as the brand film stages them (the film's
  prep_assets.py crops the supplied logo file to its ink and keys the lockup's
  navy ground). --brand-dir copies files the film prep already made.
- assets/footage/scroll.mp4: 3.6 s of the scroll recording at double speed,
  1080 px wide, with the app's captions removed (only the posts read), muted,
  a keyframe every 30 frames. It plays inside the letters of "2026.".
- assets/fonts/: Montserrat 500, 800 and 900 (Google Fonts, OFL).
- assets/img/grain.png: a 256 px noise tile.
- assets/geo/india-composite.geojson: the land area of India in accordance with
  the official boundary of India as per the Survey of India (Jammu and Kashmir
  and Ladakh in full), compiled by the DataMeet community, CC-0
  (github.com/datameet/maps, Country/). compose.py draws the map from it.
- assets/gsap.min.js: copied from template/assets.

The frame and the faces come from faces_prep.py (needs OpenCV; run it once per set of posts).
"""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
FF = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
FONT_CSS = "https://fonts.googleapis.com/css2?family=Montserrat:wght@500;800;900&display=swap"
SCROLL_START, SCROLL_SPEED, SCROLL_OUT = 8.0, 2.0, 3.6
INDIA_GEOJSON = "https://raw.githubusercontent.com/datameet/maps/master/Country/india-composite.geojson"
# the app's captions under each post (thin white type) are removed with a luma-only morphological opening
# (4x erosion, 4x dilation, 3x3): strokes that thin vanish, the posts and faces keep their shape
OPEN = ",".join(["erosion=threshold1=0:threshold2=0"] * 4 + ["dilation=threshold1=0:threshold2=0"] * 4)


def run(cmd):
    subprocess.run(cmd, check=True)


def fetch_fonts(dest):
    dest.mkdir(parents=True, exist_ok=True)
    if all((dest / f"Montserrat-{w}.ttf").is_file() for w in (500, 800, 900)):
        return
    req = urllib.request.Request(FONT_CSS, headers={"User-Agent": "curl/8"})
    css = urllib.request.urlopen(req, timeout=30).read().decode()
    for w, url in re.findall(r"font-weight: (\d+);.*?url\(([^)]+)\) format\('truetype'\)", css, re.S):
        (dest / f"Montserrat-{w}.ttf").write_bytes(urllib.request.urlopen(url, timeout=30).read())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", required=True)
    ap.add_argument("--scroll", required=True, help="the scroll recording of learner posts")
    ap.add_argument("--brand-dir", help="a dir holding deekshaarambh.png and jain-online.png from the film prep")
    ap.add_argument("--logo")
    ap.add_argument("--jain-online")
    a = ap.parse_args()
    proj = pathlib.Path(a.project).expanduser().resolve()
    for sub in ("brand", "footage", "img", "fonts", "audio", "geo"):
        (proj / "assets" / sub).mkdir(parents=True, exist_ok=True)

    brand = proj / "assets" / "brand"
    if a.brand_dir:
        for nm in ("deekshaarambh.png", "jain-online.png"):
            shutil.copyfile(pathlib.Path(a.brand_dir).expanduser() / nm, brand / nm)
    elif a.logo and a.jain_online:
        sys.path.insert(0, str(REPO / "motion" / "deekshaarambh-2026-film"))
        import prep_assets as film  # noqa: E402  (same crop box and key as the film)
        w, h, x, y = film.LOGO_CROP
        run(FF + ["-i", a.logo, "-vf", f"crop={w}:{h}:{x}:{y}", str(brand / "deekshaarambh.png")])
        run(FF + ["-i", a.jain_online, "-vf", f"format=rgba,colorkey={film.NAVY_KEY}:0.22:0.12", str(brand / "jain-online.png")])
    else:
        ap.error("pass --brand-dir, or --logo and --jain-online")

    run(FF + ["-ss", f"{SCROLL_START}", "-t", f"{SCROLL_OUT * SCROLL_SPEED + 0.2}", "-i", a.scroll, "-t", f"{SCROLL_OUT}", "-an",
              "-vf", f"setpts=PTS/{SCROLL_SPEED},fps=30,scale=1080:-2:flags=lanczos,{OPEN},gblur=sigma=1.0",
              "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
              "-g", "30", "-keyint_min", "30", "-sc_threshold", "0", "-movflags", "+faststart",
              str(proj / "assets" / "footage" / "scroll.mp4")])

    fetch_fonts(proj / "assets" / "fonts")
    geo = proj / "assets" / "geo" / "india-composite.geojson"
    if not geo.is_file():
        geo.write_bytes(urllib.request.urlopen(INDIA_GEOJSON, timeout=60).read())
    run(FF + ["-f", "lavfi", "-i", "nullsrc=s=256x256,geq=lum='random(1)*255':cb=128:cr=128",
              "-frames:v", "1", "-pix_fmt", "gray", str(proj / "assets" / "img" / "grain.png")])
    shutil.copyfile(REPO / "template" / "assets" / "gsap.min.js", proj / "assets" / "gsap.min.js")
    print(f"staged brand, scroll clip ({SCROLL_OUT}s at {SCROLL_SPEED}x from {SCROLL_START}s), fonts, grain, India boundary, gsap -> {proj}/assets")


if __name__ == "__main__":
    main()
