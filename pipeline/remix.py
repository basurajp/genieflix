#!/usr/bin/env python3
"""Fix the mix without regenerating the voice: renormalize, rebuild, re-render.

Usage: pipeline/remix.py --project <dir>

The "words are right, the sound isn't" tool. Loudness-normalizes each
processed narration line in place (loudnorm only — no TTS), refreshes the
recorded durations, then rebuilds the timeline, captions, and composition
(which recomputes the music bed level under the narration) and re-runs the QA
render and the finishing pass. The old mix is copied to audio.bak/ first.
"""

import argparse
import os
import pathlib
import shlex
import shutil
import subprocess
import sys

import common

PIPELINE_DIR = pathlib.Path(__file__).resolve().parent

# Loudnorm alone: the highpass/denoise/compressor half of the chain already ran
# on these files, and re-running it would degrade audio that already sounds right.
LOUDNORM = "loudnorm=I=-14:TP=-1.0:LRA=7"

REBUILD_STEPS = ("build_timeline.py", "captions.py", "build_index.py", "qa.py", "finish.py")


def renormalize_lines(project_dir, meta):
    """Loudnorm each audio/lineNN.wav in place and refresh its duration."""
    lines = meta.get("lines") or []
    if not lines:
        raise SystemExit(
            "remix: audio_meta.json has no lines — run make_reel.py --phase voice first"
        )
    bak_dir = project_dir / "audio.bak"
    for entry in lines:
        rel = entry.get("file") or f"audio/line{int(entry['index']):02d}.wav"
        wav = project_dir / rel
        if not wav.exists():
            raise SystemExit(f"remix: missing {wav} — run make_reel.py --phase voice first")
        bak_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wav, bak_dir / wav.name)  # never destroy the old mix
        tmp = wav.with_suffix(".tmp.wav")
        common.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(wav),
                "-af", LOUDNORM,
                "-ac", "1", "-ar", "24000",
                str(tmp),
            ]
        )
        os.replace(tmp, wav)
        # loudnorm can shift a duration a hair, so the timeline is rebuilt below.
        entry["duration"] = round(common.ffprobe_duration(wav), 3)
        print(f"remix: {rel} renormalized ({entry['duration']:.2f}s)")


def run_step(script, project_dir):
    cmd = [sys.executable, str(PIPELINE_DIR / script), "--project", str(project_dir)]
    print(f"\n=== {script} ===", flush=True)
    print("+ " + shlex.join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(common.REPO_ROOT))
    if proc.returncode != 0:
        raise SystemExit(f"remix: step {script} failed (exit {proc.returncode})")


def main():
    parser = argparse.ArgumentParser(
        description="Renormalize the narration mix and re-render without regenerating the voice."
    )
    parser.add_argument("--project", required=True, help="project directory")
    args = parser.parse_args()

    project_dir = pathlib.Path(args.project).expanduser().resolve()
    if not project_dir.is_dir():
        raise SystemExit(f"remix: project directory not found: {project_dir}")
    common.load_config()  # fail early on a broken config
    common.load_project(project_dir)  # fail early on a malformed project

    meta_path = project_dir / "audio_meta.json"
    meta = common.load_json(meta_path)
    if not meta:
        raise SystemExit(
            f"remix: no {meta_path} — run make_reel.py --phase voice first"
        )

    renormalize_lines(project_dir, meta)
    common.save_json(meta_path, meta)
    print(f"remix: updated {meta_path}")

    for script in REBUILD_STEPS:
        run_step(script, project_dir)

    print(f"\nremix: {project_dir.name} re-mixed, re-rendered, and delivered")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()
        message = f"remix.py: command failed with exit {exc.returncode}"
        if detail:
            message += "\n" + detail
        sys.exit(message)
