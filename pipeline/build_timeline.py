#!/usr/bin/env python3
"""Build timeline.json: map voiced lines to slide scenes and fix line starts.

Usage: build_timeline.py --project <dir>
"""

import argparse
import sys
from pathlib import Path

import common

# Animated GIFs are deliberately excluded: the renderer cannot reproduce
# them deterministically. Use a static image or a real video clip.
SLIDE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

# Extra hold on the final scene so the CTA stamp gets a beat on screen.
LAST_SCENE_HOLD = 0.6


def die(msg):
    print(f"build_timeline: error: {msg}", file=sys.stderr)
    sys.exit(1)


def find_slides(project_dir):
    """Return sorted project-relative slide paths (slide N maps to line N)."""
    slides_dir = project_dir / "assets" / "slides"
    if not slides_dir.is_dir():
        die(f"no slides directory at {slides_dir} — add assets/slides/slide01.png (one per line)")
    slides = sorted(
        p.name for p in slides_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SLIDE_EXTS
    )
    if not slides:
        die(
            f"no slide images in {slides_dir} — add slide01.png, slide02.png, ... "
            "(one per line; the last repeats if there are fewer slides than lines)"
        )
    return ["assets/slides/" + name for name in slides]


def main():
    ap = argparse.ArgumentParser(
        description="Compute line start times and write timeline.json for a video project."
    )
    ap.add_argument("--project", required=True, help="project directory")
    args = ap.parse_args()

    project_dir = Path(args.project).expanduser().resolve()
    if not project_dir.is_dir():
        die(f"project directory not found: {project_dir}")

    cfg = common.load_config()
    line_gap = float(cfg.get("line_gap", 0.35))

    meta_path = project_dir / "audio_meta.json"
    if not meta_path.is_file():
        die(f"{meta_path} not found — run voice.py and audio_chain.py first")
    meta = common.load_json(meta_path)
    lines = meta.get("lines") or []
    if not lines:
        die("audio_meta.json has no lines — run voice.py and audio_chain.py first")
    for ln in lines:
        if "index" not in ln or "duration" not in ln:
            die("audio_meta.json lines are missing index/duration — re-run audio_chain.py")
    lines.sort(key=lambda ln: ln["index"])

    # Cumulative starts: line 1 at 0.0, then previous start + duration + gap.
    t = 0.0
    for ln in lines:
        ln["start"] = round(t, 3)
        t += float(ln["duration"]) + line_gap

    slides = find_slides(project_dir)
    if len(slides) > len(lines):
        print(f"build_timeline: note: {len(slides)} slides for {len(lines)} lines — extras ignored")

    scenes = []
    for i, ln in enumerate(lines):
        duration = float(ln["duration"]) + line_gap
        if i == len(lines) - 1:
            duration += LAST_SCENE_HOLD
        scenes.append({
            "index": ln["index"],
            "start": ln["start"],
            "duration": round(duration, 3),
            "slide": slides[min(i, len(slides) - 1)],
            "text": ln.get("text", ""),
        })

    total = round(scenes[-1]["start"] + scenes[-1]["duration"], 3)

    meta["line_gap"] = line_gap
    meta["total"] = total
    common.save_json(meta_path, meta)
    common.save_json(project_dir / "timeline.json", {"scenes": scenes, "total": total})

    print(f"build_timeline: {len(scenes)} scenes, total {total:.2f}s -> {project_dir / 'timeline.json'}")


if __name__ == "__main__":
    main()
