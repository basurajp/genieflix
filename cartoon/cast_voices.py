#!/usr/bin/env python3
"""Generate per-line narration for a multi-character cartoon cast.

Usage: cartoon/cast_voices.py --project <dir> [--engine auto|edge|kokoro] [--force]

Reads <project>/cast.json:

  {
    "speakers": ["nar", "kid", ...],          // one entry per line of lines.txt
    "voices": {
      "nar": {"edge": "en-US-GuyNeural", "kokoro": "am_michael"},
      "kid": {"edge": "en-US-AnaNeural", "kokoro": "af_sky", "kokoro_pitch": 1.13}
    }
  }

"pitch" is a post-processing multiplier applied to whichever engine ran;
"edge_pitch"/"kokoro_pitch" override it per engine (e.g. a real child voice on
edge needs no shift, while its adult kokoro fallback does).

Two engines, best available wins:
  edge    Microsoft Edge neural voices via edge-tts — human-grade, needs network.
  kokoro  `npx hyperframes tts` (Kokoro-82M) — fully offline, flatter delivery.

--engine auto (default) tries edge per line and falls back to kokoro with a
warning; the shipped casts carry both voice ids so either engine works.
"pitch" is a post-processing multiplier (asetrate/atempo keeps duration), used
to derive a kid or an elder from the same base voice.

Output: raw/lineNN.wav — exactly what pipeline/audio_chain.py expects next.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "pipeline"))
import common  # noqa: E402


def gen_edge(text, voice, out_path):
    exe = shutil.which("edge-tts") or str(pathlib.Path(sys.executable).parent / "edge-tts")
    mp3 = out_path.with_suffix(".mp3")
    subprocess.run([exe, "--voice", voice, "--text", text, "--write-media", str(mp3)],
                   check=True, capture_output=True, timeout=120)
    if not mp3.exists() or mp3.stat().st_size == 0:
        raise RuntimeError("edge-tts produced no audio")
    common.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(mp3),
                "-ac", "1", "-ar", "24000", str(out_path)])
    mp3.unlink()


def gen_kokoro(text, voice, out_path):
    common.run(["npx", "hyperframes", "tts", text, "-v", voice, "-o", str(out_path)])


def apply_pitch(path, factor):
    sr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                         "-show_entries", "stream=sample_rate", "-of", "csv=p=0", str(path)],
                        capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=path.parent) as tmp:
        tmp_path = pathlib.Path(tmp.name)
    common.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(path),
                "-af", f"asetrate={sr}*{factor},aresample={sr},atempo=1/{factor}", str(tmp_path)])
    tmp_path.replace(path)


def main():
    ap = argparse.ArgumentParser(description="Voice a cartoon cast, one WAV per line.")
    ap.add_argument("--project", required=True)
    ap.add_argument("--engine", choices=["auto", "edge", "kokoro"], default="auto")
    ap.add_argument("--force", action="store_true", help="regenerate lines whose WAV already exists")
    args = ap.parse_args()

    project = pathlib.Path(args.project).expanduser().resolve()
    cast = common.load_json(project / "cast.json")
    if not cast:
        raise SystemExit(f"missing cast.json in {project} — copy one from cartoon/episodes/")
    lines = common.read_lines(project)
    speakers = cast.get("speakers", [])
    if len(speakers) != len(lines):
        raise SystemExit(f"cast.json has {len(speakers)} speakers but lines.txt has {len(lines)} lines")

    raw = project / "raw"
    raw.mkdir(exist_ok=True)
    edge_ok = args.engine in ("auto", "edge")
    for i, (text, spk) in enumerate(zip(lines, speakers), 1):
        out = raw / f"line{i:02d}.wav"
        if out.exists() and not args.force:
            print(f"line{i:02d} [{spk}] exists, skipping")
            continue
        v = cast["voices"].get(spk)
        if not v:
            raise SystemExit(f'cast.json has no voice for speaker "{spk}"')
        used = None
        if edge_ok and v.get("edge"):
            try:
                gen_edge(text, v["edge"], out)
                used = f'edge:{v["edge"]}'
            except Exception as exc:
                if args.engine == "edge":
                    raise SystemExit(f"edge-tts failed for line {i}: {exc}")
                print(f"line{i:02d}: edge-tts unavailable ({type(exc).__name__}) — falling back to kokoro")
                edge_ok = False
        if used is None:
            if not v.get("kokoro"):
                raise SystemExit(f'no kokoro fallback voice for "{spk}" and edge is unavailable')
            gen_kokoro(text, v["kokoro"], out)
            used = f'kokoro:{v["kokoro"]}'
        engine = used.split(":", 1)[0]
        pitch = float(v.get(f"{engine}_pitch", v.get("pitch", 1.0)))
        if abs(pitch - 1.0) > 1e-3:
            apply_pitch(out, pitch)
            used += f" pitch x{pitch}"
        print(f"line{i:02d} [{spk}] {used}")

    print("next: pipeline/audio_chain.py, transcribe.py, build_timeline.py, captions.py, then the episode's compose.py")


if __name__ == "__main__":
    main()
