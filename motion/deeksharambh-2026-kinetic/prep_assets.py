#!/usr/bin/env python3
"""Stage the kinetic Deeksharambh 2026 reel's assets into a project dir.

Usage:
  motion/deeksharambh-2026-kinetic/prep_assets.py --project <dir> \
      --logo deeksharambh.png --jain-online jain-online.png --cdoe jain-cdoe.png \
      --scroll scroll.mp4

Runs the cinematic piece's prep (logo pieces, 240 face tiles, mosaic, grain,
keyed lockups) into the same project, then adds what this cut needs on top:
five tall face columns (assets/img/colN.jpg, 36 tiles each, 220 px tiles on a
236 px pitch) that scroll behind the type and drive the flicker wall.
"""
import argparse
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
CINEMATIC = HERE.parent / "deeksharambh-2026-cinematic" / "prep_assets.py"
FF = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
COLS, PER_COL, TILE, GAP = 5, 36, 220, 16
NAVY = "0x030a26"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", required=True)
    for flag in ("--logo", "--jain-online", "--cdoe", "--scroll"):
        ap.add_argument(flag, required=True)
    a = ap.parse_args()
    proj = pathlib.Path(a.project).expanduser().resolve()
    subprocess.run([sys.executable, str(CINEMATIC), "--project", str(proj), "--logo", a.logo,
                    "--jain-online", a.jain_online, "--cdoe", a.cdoe, "--scroll", a.scroll], check=True)

    tiles = sorted((proj / "assets" / "tiles").glob("t*.jpg"))
    order = list(range(len(tiles)))
    random.Random(11).shuffle(order)
    img = proj / "assets" / "img"
    for c in range(COLS):
        with tempfile.TemporaryDirectory() as td:
            for k in range(PER_COL):
                shutil.copy(tiles[order[(c * PER_COL + k) % len(order)]], pathlib.Path(td) / f"{k:03d}.jpg")
            subprocess.run(FF + ["-framerate", "1", "-i", str(pathlib.Path(td) / "%03d.jpg"),
                                 "-vf", f"scale={TILE}:{TILE}:flags=lanczos,tile=1x{PER_COL}:padding={GAP}:color={NAVY}",
                                 "-frames:v", "1", "-q:v", "3", str(img / f"col{c}.jpg")], check=True)
    print(f"columns: {COLS} x {PER_COL} tiles -> {img}/col*.jpg")


if __name__ == "__main__":
    main()
