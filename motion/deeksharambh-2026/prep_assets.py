#!/usr/bin/env python3
"""Stage the Deeksharambh 2026 recap's brand assets and scale footage into a project dir.

Usage:
  motion/deeksharambh-2026/prep_assets.py --project motion/deeksharambh-2026/project \
      --logo deeksharambh.png --poster poster.png --jain-online jain-online.png \
      --cdoe jain-cdoe.png --scroll scroll.mp4

- The Deeksharambh logo is already transparent: cropped to its ink.
- The two JAIN lockups ship on solid navy: keyed to alpha with colorkey.
- The poster loses its dark screenshot border.
- The scroll recording becomes three muted 2x-speed strips with dense keyframes
  (-g 30) so the renderer's seeks never freeze; each starts at a different
  point in the scroll so stacked strips never show the same faces side by side.
"""
import argparse
import pathlib
import subprocess

FF = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]

# Measured on the supplied files (alpha bbox / border scan).
LOGO_CROP = "1624:540:226:741"
POSTER_CROP = "1178:1178:18:19"
NAVY = "0x04164B"

# (name, source in-point s, source out-point s) — 14 s of scroll -> 7 s at 2x.
STRIPS = [("scroll-a", 0.0, 14.0), ("scroll-b", 6.0, 20.0), ("scroll-c", 12.0, 26.0)]


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", required=True)
    for flag in ("--logo", "--poster", "--jain-online", "--cdoe", "--scroll"):
        ap.add_argument(flag, required=True)
    a = ap.parse_args()
    proj = pathlib.Path(a.project).expanduser().resolve()
    img = proj / "assets" / "img"
    foot = proj / "assets" / "footage"
    img.mkdir(parents=True, exist_ok=True)
    foot.mkdir(parents=True, exist_ok=True)

    run(FF + ["-i", a.logo, "-vf", f"crop={LOGO_CROP}", str(img / "deeksharambh.png")])
    run(FF + ["-i", a.poster, "-vf", f"crop={POSTER_CROP}", str(img / "poster.png")])
    for src, name in ((a.jain_online, "jain-online.png"), (a.cdoe, "jain-cdoe.png")):
        run(FF + ["-i", src, "-vf", f"format=rgba,colorkey={NAVY}:0.22:0.12", str(img / name)])

    for name, t0, t1 in STRIPS:
        run(FF + [
            "-ss", f"{t0}", "-to", f"{t1}", "-i", a.scroll, "-an",
            "-vf", "setpts=PTS/2,fps=30,scale=720:-2:flags=lanczos,unsharp=5:5:0.6",
            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
            "-g", "30", "-keyint_min", "30", "-sc_threshold", "0", "-movflags", "+faststart",
            str(foot / f"{name}.mp4"),
        ])
    print(f"staged assets into {proj}/assets")


if __name__ == "__main__":
    main()
