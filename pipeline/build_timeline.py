#!/usr/bin/env python3
"""Build timeline.json: map voiced lines to slide scenes and fix line starts.

Usage: build_timeline.py --project <dir>

project.json "beats" (keyed by 1-based line number) can shape the timeline:

  "pause_before": 0.8   seconds of silence before the line. The line's scene
                        starts where the silence starts (the visual lands first,
                        the voice after it); audio_meta.json start, captions and
                        the voice clip all move with the voice.
  "media": "none"       the scene has no media (drawn styles fill it);
  "media": "<path>"     project-relative clip or still for the scene, overriding
                        assets/footage/lineNN.* and the slides.
  "continue": true      the previous scene's shot keeps playing under this line:
                        no new media, and the owning clip's media_duration grows
                        to cover it (pipeline/footage.py trims to that span).
"""

import argparse
import re
import sys
from pathlib import Path

import common

# Animated GIFs are deliberately excluded: the renderer cannot reproduce
# them deterministically. Use a static image or a real video clip.
SLIDE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
FOOTAGE_EXTS = SLIDE_EXTS | {".mp4"}

# Extra hold on the final scene so the CTA stamp gets a beat on screen.
LAST_SCENE_HOLD = 0.6


def die(msg):
    print(f"build_timeline: error: {msg}", file=sys.stderr)
    sys.exit(1)


def find_slides(project_dir):
    """Return sorted project-relative slide paths (slide N maps to line N)."""
    slides_dir = project_dir / "assets" / "slides"
    slides = sorted(
        p.name for p in slides_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SLIDE_EXTS
    ) if slides_dir.is_dir() else []
    return ["assets/slides/" + name for name in slides]


def find_footage(project_dir):
    """{line index: project-relative path} for staged assets/footage/lineNN.*.

    Only exact lineNN stems count: lineNN-<name> files are word-anchored inserts
    (project.json beats), never a scene's own media."""
    footage_dir = project_dir / "assets" / "footage"
    found = {}
    if not footage_dir.is_dir():
        return found
    for p in sorted(footage_dir.iterdir()):
        m = re.fullmatch(r"line(\d{2})", p.stem)
        if p.is_file() and m and p.suffix.lower() in FOOTAGE_EXTS:
            found.setdefault(int(m.group(1)), "assets/footage/" + p.name)
    return found


def beat_for(beats, index):
    beat = beats.get(str(index)) or beats.get(index) or {}
    if not isinstance(beat, dict):
        die(f'project.json beats["{index}"] must be an object')
    return beat


def scene_media(beat, index, position, slides, footage):
    """What a scene shows: "none", "continue", or a project-relative path."""
    if beat.get("continue"):
        return "continue"
    media = beat.get("media")
    if media is not None:
        media = str(media).strip()
        return "none" if media in ("", "none") else media
    if index in footage:
        return footage[index]
    if slides:
        return slides[min(position, len(slides) - 1)]
    return "none"


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

    project = common.load_project(project_dir)
    beats = project.get("beats") or {}
    if not isinstance(beats, dict):
        die('project.json "beats" must be an object keyed by line number')

    # Cumulative starts: line 1 at 0.0, then previous start + duration + gap;
    # a beat's pause_before opens a silence the line's scene already covers.
    t = 0.0
    scene_starts = {}
    for ln in lines:
        pause = float(beat_for(beats, ln["index"]).get("pause_before") or 0.0)
        if pause < 0:
            die(f"line {ln['index']}: pause_before must be >= 0")
        scene_starts[ln["index"]] = round(t, 3)
        ln["start"] = round(t + pause, 3)
        t += pause + float(ln["duration"]) + line_gap

    slides = find_slides(project_dir)
    footage = find_footage(project_dir)
    if len(slides) > len(lines):
        print(f"build_timeline: note: {len(slides)} slides for {len(lines)} lines — extras ignored")

    scenes = []
    owner = None
    for i, ln in enumerate(lines):
        beat = beat_for(beats, ln["index"])
        start = scene_starts[ln["index"]]
        duration = round(ln["start"] - start, 3) + float(ln["duration"]) + line_gap
        if i == len(lines) - 1:
            duration += LAST_SCENE_HOLD
        media = scene_media(beat, ln["index"], i, slides, footage)
        scene = {
            "index": ln["index"],
            "start": start,
            "duration": round(duration, 3),
            "slide": None if media in ("none", "continue") else media,
            "media": media,
            "voice_start": ln["start"],
            "text": ln.get("text", ""),
        }
        if ln["start"] > start:
            scene["pause_before"] = round(ln["start"] - start, 3)
        if media == "continue":
            if owner is None:
                die(f"line {ln['index']}: \"continue\" needs an earlier line whose shot it continues")
            # the span counts even before footage is staged, so footage.py trims
            # the owning clip long enough for every line that continues it
            owner["media_duration"] = round(start + scene["duration"] - owner["start"], 3)
            if owner["media"] == "none":
                print(f"build_timeline: note: line {ln['index']} continues line {owner['index']}, "
                      "which has no media yet — stage it, then rebuild")
                scene["media"] = "none"
            else:
                scene["continues"] = owner["index"]
        else:
            owner = scene
            scene["media_duration"] = scene["duration"]
        scenes.append(scene)

    if all(sc["media"] in ("none", "continue") for sc in scenes) and not beats:
        die(
            f"no slide images in {project_dir / 'assets' / 'slides'} and no footage in "
            f"{project_dir / 'assets' / 'footage'} — add slide01.png, slide02.png, ... "
            "(one per line; the last repeats if there are fewer slides than lines), stage "
            "clips with pipeline/footage.py, or describe drawn scenes in project.json beats"
        )
    for sc in scenes:
        if sc["media"] == "none" and "media" not in beat_for(beats, sc["index"]) \
                and "draw" not in beat_for(beats, sc["index"]):
            print(f"build_timeline: note: line {sc['index']} has no media — the style's background shows")

    total = round(scenes[-1]["start"] + scenes[-1]["duration"], 3)

    meta["line_gap"] = line_gap
    meta["total"] = total
    common.save_json(meta_path, meta)
    common.save_json(project_dir / "timeline.json", {"scenes": scenes, "total": total})

    print(f"build_timeline: {len(scenes)} scenes, total {total:.2f}s -> {project_dir / 'timeline.json'}")


if __name__ == "__main__":
    main()
