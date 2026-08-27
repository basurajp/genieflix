#!/usr/bin/env python3
"""Export a project's narration as LTX-2 A2Vid conditioning material.

Usage: integrations/ltx2/export_a2vid.py --project <dir> [--presenter "..."] [--fps 24]

For each line in audio_meta.json this writes, under <project>/a2vid/:
  lineNN.wav        48 kHz stereo conditioning audio (from the processed line WAV)
  lineNN_prompt.txt cinematographer-style prompt for the clip
  manifest.json     per-line audio path, prompt path, duration, suggested frame
                    count (nearest 8n+1 at --fps with ~0.5 s headroom)

Generation itself happens on an NVIDIA GPU machine with the LTX-2 repository —
see integrations/ltx2/README.md. This script only prepares the inputs, so it
runs anywhere the pipeline runs.
"""
import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "pipeline"))
import common  # noqa: E402

DEFAULT_PRESENTER = (
    "a friendly presenter with a warm, confident expression, plain softly lit "
    "studio background with a subtle color gradient"
)

PROMPT_TEMPLATE = (
    "A medium close-up shot of {presenter}, centered in a vertical frame, "
    "looking directly at the camera. They speak naturally with clear lip "
    "movement, saying: \"{line}\" Their expression matches the words, with "
    "small natural head movements and blinks. The camera is static with a "
    "shallow depth of field; the background stays softly blurred. Lighting is "
    "soft and even on the face."
)


def suggested_frames(duration: float, fps: int) -> int:
    """Nearest 8n+1 frame count covering the audio plus ~0.5 s of headroom."""
    frames = int((duration + 0.5) * fps)
    return ((frames + 7) // 8) * 8 + 1


def main():
    ap = argparse.ArgumentParser(description="Prepare LTX-2 A2Vid inputs from a project's narration.")
    ap.add_argument("--project", required=True, help="project directory (voice phase must have run)")
    ap.add_argument("--presenter", default=DEFAULT_PRESENTER, help="who appears on screen")
    ap.add_argument("--fps", type=int, default=24, help="target clip frame rate (default 24)")
    args = ap.parse_args()

    project = pathlib.Path(args.project).expanduser().resolve()
    meta = common.load_json(project / "audio_meta.json")
    if not meta or not meta.get("lines"):
        raise SystemExit(f"no audio_meta.json with lines in {project} — run the voice phase first")

    out = project / "a2vid"
    out.mkdir(exist_ok=True)
    entries = []
    for ln in meta["lines"]:
        idx = ln["index"]
        src = project / ln["file"]
        if not src.is_file():
            raise SystemExit(f"missing {src} — run the voice phase first")
        wav = out / f"line{idx:02d}.wav"
        common.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src), "-ac", "2", "-ar", "48000", str(wav),
        ])
        prompt = PROMPT_TEMPLATE.format(presenter=args.presenter, line=ln["text"])
        prompt_path = out / f"line{idx:02d}_prompt.txt"
        prompt_path.write_text(prompt + "\n", encoding="utf-8")
        entries.append({
            "index": idx,
            "text": ln["text"],
            "audio": wav.name,
            "prompt": prompt_path.name,
            "duration": ln["duration"],
            "suggested_num_frames": suggested_frames(ln["duration"], args.fps),
            "fps": args.fps,
        })
        print(f"a2vid/{wav.name}  {ln['duration']:.2f}s  -> {entries[-1]['suggested_num_frames']} frames @ {args.fps} fps")

    common.save_json(out / "manifest.json", {"presenter": args.presenter, "lines": entries})
    print(f"wrote {out / 'manifest.json'}")
    print("next: generate one clip per line with LTX-2's A2Vid pipeline on a GPU machine")
    print("      (conditioning audio + prompt per line, num frames from the manifest),")
    print("      then run integrations/ltx2/stage_footage.py with the generated clips.")


if __name__ == "__main__":
    main()
