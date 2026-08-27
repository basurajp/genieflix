#!/usr/bin/env python3
"""Generate raw narration (raw/lineNN.wav), one WAV per line of lines.txt.

Usage: pipeline/voice.py --project <dir> [--force] [--line N]

Backends (config "voice_backend"; "auto" picks the first available in this order):
chatterbox (macOS voice clone via mlx_audio) -> xtts (Coqui voice clone) ->
edge (edge-tts neural voice) -> kokoro (npx hyperframes tts; runs everywhere).
Existing lines are skipped unless --force or --line is given; before any
overwrite the old take is copied to raw.bak/ (and audio.bak/) — never destroyed.
"""

import argparse
import pathlib
import shutil
import subprocess
import sys

import common

BACKENDS = ("chatterbox", "xtts", "edge", "kokoro")


def venv_imports(python, module):
    """True when the voice venv's python exists and can import `module`."""
    if not pathlib.Path(python).exists():
        return False
    try:
        proc = subprocess.run(
            [python, "-c", "import " + module],
            capture_output=True,
        )
    except OSError:
        return False
    return proc.returncode == 0


def edge_tts_command(cfg):
    """Locate the edge-tts executable on PATH or inside the voice venv."""
    exe = shutil.which("edge-tts")
    if exe:
        return exe
    venv = common.resolve(cfg, cfg.get("voice_venv", "~/.voice-clone-venv"))
    for candidate in (venv / "bin" / "edge-tts", venv / "Scripts" / "edge-tts.exe"):
        if candidate.exists():
            return str(candidate)
    return None


def detect_backend(cfg):
    """Resolve the configured voice backend, auto-detecting when set to "auto"."""
    choice = cfg.get("voice_backend", "auto")
    if choice in BACKENDS:
        return choice
    if choice != "auto":
        raise SystemExit(
            f"unknown voice_backend {choice!r}; expected auto|" + "|".join(BACKENDS)
        )
    python = common.venv_python(cfg)
    if sys.platform == "darwin" and venv_imports(python, "mlx_audio"):
        return "chatterbox"
    if venv_imports(python, "TTS"):
        return "xtts"
    if edge_tts_command(cfg):
        return "edge"
    return "kokoro"


def require_reference(cfg):
    ref = common.resolve(cfg, cfg["voice_reference"])
    if not ref.exists():
        raise SystemExit(
            f"voice reference not found: {ref}\n"
            "Record 1-2 minutes of clean speech (no music, no echo) and save it "
            "there — see voice-samples/README.md."
        )
    return ref


def xtts_language(lang):
    """Map a project lang to an XTTS language code (hinglish speaks best as hi)."""
    lang = (lang or "en").strip().lower()
    if not lang or lang == "en":
        return "en"
    if lang.startswith("hi"):
        return "hi"
    return lang[:2]


def collect_output(raw_dir, stem):
    """Normalize a backend's output to raw/<stem>.wav.

    mlx_audio may write <stem>_000.wav (and split long text into several parts);
    rename a single part, concatenate multiple.
    """
    target = raw_dir / f"{stem}.wav"
    if target.exists():
        return
    parts = sorted(
        p for p in raw_dir.glob(f"{stem}*.wav") if p != target and ".tmp" not in p.name
    )
    if not parts:
        raise SystemExit(f"voice backend produced no output for {stem} in {raw_dir}")
    if len(parts) == 1:
        parts[0].rename(target)
        return
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for part in parts:
        cmd += ["-i", str(part)]
    cmd += ["-filter_complex", f"concat=n={len(parts)}:v=0:a=1", str(target)]
    common.run(cmd)
    for part in parts:
        part.unlink()


def generate_chatterbox(cfg, project, text, stem, raw_dir):
    ref = require_reference(cfg)
    common.run(
        [
            common.venv_python(cfg),
            "-m",
            "mlx_audio.tts.generate",
            "--model",
            cfg["chatterbox_model"],
            "--text",
            text,
            "--ref_audio",
            str(ref),
            "--output_path",
            str(raw_dir),
            "--file_prefix",
            stem,
        ]
    )
    collect_output(raw_dir, stem)


XTTS_SNIPPET = """\
import sys
from TTS.api import TTS
model, text, ref, lang, out = sys.argv[1:6]
TTS(model).tts_to_file(text=text, speaker_wav=ref, language=lang, file_path=out)
"""


def generate_xtts(cfg, project, text, stem, raw_dir):
    ref = require_reference(cfg)
    common.run(
        [
            common.venv_python(cfg),
            "-c",
            XTTS_SNIPPET,
            cfg["xtts_model"],
            text,
            str(ref),
            xtts_language(project.get("lang", "en")),
            str(raw_dir / f"{stem}.wav"),
        ]
    )


def generate_edge(cfg, project, text, stem, raw_dir):
    exe = edge_tts_command(cfg)
    if not exe:
        raise SystemExit("edge-tts not found on PATH or in the voice venv")
    tmp = raw_dir / f"{stem}.tmp.mp3"
    try:
        common.run([exe, "--voice", cfg["edge_voice"], "--text", text, "--write-media", str(tmp)])
        common.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(tmp), "-ac", "1", "-ar", "24000",
                str(raw_dir / f"{stem}.wav"),
            ]
        )
    finally:
        tmp.unlink(missing_ok=True)


def generate_kokoro(cfg, project, text, stem, raw_dir):
    npx = shutil.which("npx") or "npx"
    common.run(
        [npx, "hyperframes", "tts", text, "-o", str(raw_dir / f"{stem}.wav"), "-v", cfg["kokoro_voice"]]
    )


GENERATORS = {
    "chatterbox": generate_chatterbox,
    "xtts": generate_xtts,
    "edge": generate_edge,
    "kokoro": generate_kokoro,
}


def backup_line(project_dir, stem):
    """Copy the existing raw/audio takes for a line aside before overwriting."""
    for src_name, bak_name in (("raw", "raw.bak"), ("audio", "audio.bak")):
        src = project_dir / src_name / f"{stem}.wav"
        if src.exists():
            bak_dir = project_dir / bak_name
            bak_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, bak_dir / src.name)
            print(f"backed up {src_name}/{src.name} -> {bak_name}/{src.name}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate raw narration WAVs (raw/lineNN.wav) for a project."
    )
    parser.add_argument("--project", required=True, help="project directory")
    parser.add_argument(
        "--force", action="store_true", help="regenerate every line even if its raw WAV exists"
    )
    parser.add_argument("--line", type=int, help="regenerate only this 1-based line")
    args = parser.parse_args()

    project_dir = pathlib.Path(args.project).expanduser().resolve()
    cfg = common.load_config()
    project = common.load_project(project_dir)
    lines = common.read_lines(project_dir)
    if not lines:
        raise SystemExit(f"lines.txt in {project_dir} has no usable lines")
    if args.line is not None and not 1 <= args.line <= len(lines):
        raise SystemExit(f"--line {args.line} out of range (1..{len(lines)})")

    backend = detect_backend(cfg)
    print(f"voice backend: {backend}")
    raw_dir = project_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for index, text in enumerate(lines, 1):
        if args.line is not None and index != args.line:
            continue
        stem = f"line{index:02d}"
        target = raw_dir / f"{stem}.wav"
        if target.exists() and not args.force and args.line is None:
            print(f"skip {stem}.wav (exists; use --force or --line {index})")
            continue
        if target.exists():
            backup_line(project_dir, stem)
        GENERATORS[backend](cfg, project, text, stem, raw_dir)
        if not target.exists():
            raise SystemExit(f"backend {backend} did not produce raw/{stem}.wav")
        print(f"wrote raw/{stem}.wav")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()
        message = f"voice.py: command failed with exit {exc.returncode}"
        if detail:
            message += "\n" + detail
        sys.exit(message)
