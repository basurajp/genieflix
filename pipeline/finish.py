#!/usr/bin/env python3
"""The 10% snappiness pass: speed up the verified render and deliver it.

Usage: pipeline/finish.py --project <dir>

Applies setpts=PTS/<speed_up> to the video and atempo=<speed_up> to the audio
(atempo preserves pitch, so the voice doesn't chipmunk), writes
final/<slug>.mp4, and copies it to the ready-to-post folder under the slug's
descriptive name. Run after qa.py has passed — this is the last step, applied
after the render and the loudness gate.
"""

import argparse
import pathlib
import shutil
import subprocess
import sys

import common


def main():
    parser = argparse.ArgumentParser(
        description="Apply the final speed-up pass and deliver the reel to ready-to-post."
    )
    parser.add_argument("--project", required=True, help="project directory")
    args = parser.parse_args()

    project_dir = pathlib.Path(args.project).expanduser().resolve()
    if not project_dir.is_dir():
        raise SystemExit(f"finish: project directory not found: {project_dir}")
    cfg = common.load_config()
    project = common.load_project(project_dir)
    slug = project.get("slug") or project_dir.name

    speed = float(cfg.get("speed_up", 1.1))
    # Single-stage atempo only accepts 0.5..2.0 — and past ~1.2 the information
    # gets hard to follow anyway; 10% is the ceiling that still tests well.
    if not 0.5 <= speed <= 2.0:
        raise SystemExit(f"finish: speed_up {speed} out of range (0.5..2.0)")

    src = project_dir / "renders" / "reel.mp4"
    if not src.exists():
        raise SystemExit(
            f"finish: no {src} — run qa.py (or make_reel.py --phase render) first"
        )

    final_dir = project_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    out = final_dir / f"{slug}.mp4"
    spd = f"{speed:g}"
    # Room tone: perfect digital silence between words is what reads as
    # "synthetic" — a barely-audible pink-noise bed makes the narration feel
    # recorded in a real place. config "room_tone_db" (default -52); 0 disables.
    room_db = float(cfg.get("room_tone_db", -52) or 0)
    if room_db < 0:
        graph = (
            f"[0:v]setpts=PTS/{spd}[v];[0:a]atempo={spd}[a0];"
            f"anoisesrc=c=pink:r=48000:a=0.4,volume={room_db:g}dB[rt];"
            f"[a0][rt]amix=inputs=2:duration=first:normalize=0[a]"
        )
    else:
        graph = f"[0:v]setpts=PTS/{spd}[v];[0:a]atempo={spd}[a]"
    common.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src),
            "-filter_complex", graph,
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(out),
        ]
    )
    duration = common.ffprobe_duration(out)

    ready_dir = common.resolve(cfg, cfg.get("ready_to_post_dir", "factory/ready-to-post"))
    ready_dir.mkdir(parents=True, exist_ok=True)
    delivered = ready_dir / f"{slug}.mp4"
    shutil.copy2(out, delivered)

    print(f"finish: wrote {out} ({duration:.2f}s at {spd}x)")
    print(f"finish: delivered {delivered}")
    print("finish: open it one final time before it goes out — confirm it plays clean start to finish")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()
        message = f"finish.py: command failed with exit {exc.returncode}"
        if detail:
            message += "\n" + detail
        sys.exit(message)
