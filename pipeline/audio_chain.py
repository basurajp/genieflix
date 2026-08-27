#!/usr/bin/env python3
"""Polish raw narration into audio/lineNN.wav and record per-line durations.

Usage: pipeline/audio_chain.py --project <dir> [--line N]

Applies the book's exact chain (highpass -> denoise -> compressor -> loudnorm)
while converting to mono 24 kHz — raw clone output is quiet and thin, this makes
it sound like a good mic. Updates audio_meta.json with index/text/file/duration;
build_timeline.py later fills each line's start and the total.
"""

import argparse
import pathlib
import shutil
import subprocess
import sys

import common

# Exact chain from the book. Every filter earns its place:
# highpass cuts rumble below the voice, afftdn denoises gently (more sounds
# underwater), acompressor evens the dynamics into a present radio level, and
# loudnorm pins the integrated loudness so reel #40 matches reel #1.
CHAIN = (
    "highpass=f=80,"
    "afftdn=nr=12:nf=-32,"
    "acompressor=threshold=-22dB:ratio=3:attack=8:release=180:makeup=6,"
    "loudnorm=I=-14:TP=-1.0:LRA=7"
)


def process_line(project_dir, index):
    """Run the chain on raw/lineNN.wav -> audio/lineNN.wav; return the duration."""
    stem = f"line{index:02d}"
    raw = project_dir / "raw" / f"{stem}.wav"
    if not raw.exists():
        raise SystemExit(f"missing {raw} — run voice.py first")
    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    out = audio_dir / f"{stem}.wav"
    if out.exists():
        bak_dir = project_dir / "audio.bak"
        bak_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out, bak_dir / out.name)
    common.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(raw),
            "-af", CHAIN,
            "-ac", "1", "-ar", "24000",
            str(out),
        ]
    )
    return common.ffprobe_duration(out)


def main():
    parser = argparse.ArgumentParser(
        description="Apply the polish chain to raw narration and update audio_meta.json."
    )
    parser.add_argument("--project", required=True, help="project directory")
    parser.add_argument("--line", type=int, help="process only this 1-based line")
    args = parser.parse_args()

    project_dir = pathlib.Path(args.project).expanduser().resolve()
    cfg = common.load_config()
    common.load_project(project_dir)  # fail early on a malformed project
    lines = common.read_lines(project_dir)
    if not lines:
        raise SystemExit(f"lines.txt in {project_dir} has no usable lines")
    if args.line is not None and not 1 <= args.line <= len(lines):
        raise SystemExit(f"--line {args.line} out of range (1..{len(lines)})")

    meta_path = project_dir / "audio_meta.json"
    meta = common.load_json(meta_path, {}) or {}
    existing = {
        entry.get("index"): entry
        for entry in meta.get("lines", [])
        if isinstance(entry, dict)
    }

    entries = []
    for index, text in enumerate(lines, 1):
        if args.line is not None and index != args.line:
            previous = existing.get(index)
            if previous is not None:
                entries.append(previous)
            continue
        duration = process_line(project_dir, index)
        entry = dict(existing.get(index) or {})
        entry.update(
            {
                "index": index,
                "text": text,
                "file": f"audio/line{index:02d}.wav",
                "duration": round(duration, 3),
            }
        )
        entries.append(entry)
        print(f"audio/line{index:02d}.wav  {duration:.2f}s")

    out = {"lines": entries, "line_gap": float(cfg.get("line_gap", 0.35))}
    if "total" in meta:
        out["total"] = meta["total"]
    common.save_json(meta_path, out)
    print(f"updated {meta_path}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()
        message = f"audio_chain.py: command failed with exit {exc.returncode}"
        if detail:
            message += "\n" + detail
        sys.exit(message)
