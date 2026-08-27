#!/usr/bin/env python3
"""Install generated avatar clips into a project as scene footage.

Usage: integrations/ltx2/stage_footage.py --project <dir> --clips <dir>

Takes lineNN.mp4 files from --clips (any source: LTX-2 A2Vid, another
generator, real footage) and installs each as <project>/assets/footage/lineNN.mp4:

  * re-encoded with a keyframe every frame or two (-g 30 -keyint_min 30) so the
    frame-by-frame renderer can seek anywhere without freezing
  * audio stripped — the composition plays the project's processed voice WAVs,
    and keeping the clip's own track would double the narration

build_index.py then uses assets/footage/lineNN.mp4 for any scene that has one,
falling back to the scene's slide image otherwise. Rebuild + render after:

  python3 pipeline/build_index.py --project <dir>
  python3 pipeline/make_reel.py --project <dir> --phase render
"""
import argparse
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "pipeline"))
import common  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Stage generated clips as seek-safe, muted scene footage.")
    ap.add_argument("--project", required=True, help="project directory")
    ap.add_argument("--clips", required=True, help="directory holding lineNN.mp4 files")
    args = ap.parse_args()

    project = pathlib.Path(args.project).expanduser().resolve()
    clips_dir = pathlib.Path(args.clips).expanduser().resolve()
    if not clips_dir.is_dir():
        raise SystemExit(f"not a directory: {clips_dir}")

    meta = common.load_json(project / "audio_meta.json", {}) or {}
    durations = {ln["index"]: ln["duration"] for ln in meta.get("lines", [])}

    clips = sorted(p for p in clips_dir.iterdir() if re.fullmatch(r"line\d{2}\.mp4", p.name))
    if not clips:
        raise SystemExit(f"no lineNN.mp4 files in {clips_dir}")

    out_dir = project / "assets" / "footage"
    out_dir.mkdir(parents=True, exist_ok=True)
    for clip in clips:
        idx = int(clip.stem[4:])
        out = out_dir / clip.name
        # Dense keyframes: the renderer seeks to arbitrary instants, and a sparse
        # GOP freezes on a stale frame (PLAYBOOK.md, gotcha #3).
        common.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(clip), "-an",
            "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
            "-g", "30", "-keyint_min", "30",
            str(out),
        ])
        clip_dur = common.ffprobe_duration(out)
        need = durations.get(idx)
        note = ""
        if need is not None and clip_dur + 0.05 < need:
            note = f"  WARNING: clip is {clip_dur:.2f}s but line {idx} runs {need:.2f}s — the last frame will hold"
        print(f"assets/footage/{out.name}  {clip_dur:.2f}s{note}")

    print(f"staged {len(clips)} clip(s) — rebuild with pipeline/build_index.py, then render")


if __name__ == "__main__":
    main()
