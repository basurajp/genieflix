"""Shared helpers for the reel pipeline: config, project IO, subprocess, ffprobe.

Every pipeline step imports this module; its API is pinned by the build contract.
"""

import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile

# Repo root is the parent of pipeline/.
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_config() -> dict:
    """Load pipeline/config.json (falling back to config.example.json).

    Adds "_repo_root" so downstream path resolution works from any CWD.
    """
    for name in ("config.json", "config.example.json"):
        path = REPO_ROOT / "pipeline" / name
        if path.exists():
            with open(path, encoding="utf-8") as fh:
                cfg = json.load(fh)
            cfg["_repo_root"] = str(REPO_ROOT)
            return cfg
    raise SystemExit("no pipeline/config.json or pipeline/config.example.json found")


def load_project(project_dir) -> dict:
    """Parse <project_dir>/project.json."""
    path = pathlib.Path(project_dir) / "project.json"
    if not path.exists():
        raise SystemExit(f"missing project.json in {project_dir}")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_lines(project_dir) -> list:
    """Read <project_dir>/lines.txt, skipping blank lines and '#' comments."""
    path = pathlib.Path(project_dir) / "lines.txt"
    if not path.exists():
        raise SystemExit(f"missing lines.txt in {project_dir}")
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def run(cmd, cwd=None, capture=False) -> subprocess.CompletedProcess:
    """Run a command with check=True, echoing it first.

    capture=True collects stdout/stderr as text instead of streaming them.
    """
    cmd = [str(c) for c in cmd]
    print("+ " + shlex.join(cmd), flush=True)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        capture_output=capture,
    )


def ffprobe_duration(path) -> float:
    """Duration of a media file in seconds, via ffprobe."""
    proc = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture=True,
    )
    try:
        return float(proc.stdout.strip())
    except ValueError:
        raise SystemExit(f"ffprobe: could not read duration of {path}") from None


def volumedetect(path) -> dict:
    """Measure a file's loudness with ffmpeg volumedetect.

    Returns {"mean_db": float, "max_db": float}. volumedetect reports on stderr,
    so this invocation deliberately keeps ffmpeg's info-level logging on.
    """
    proc = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        capture=True,
    )
    mean = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", proc.stderr)
    peak = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", proc.stderr)
    if not mean or not peak:
        raise SystemExit(f"volumedetect: no audio statistics for {path}")
    return {"mean_db": float(mean.group(1)), "max_db": float(peak.group(1))}


def load_json(path, default=None):
    """Parse a JSON file, returning `default` when it does not exist."""
    path = pathlib.Path(path)
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path, obj):
    """Atomically write `obj` as pretty JSON (temp file + rename, indent=2)."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def venv_python(cfg) -> str:
    """Path to the voice venv's python (bin/python, or Scripts/python.exe on Windows)."""
    venv = resolve(cfg, cfg.get("voice_venv", "~/.voice-clone-venv"))
    if sys.platform == "win32":
        return str(venv / "Scripts" / "python.exe")
    return str(venv / "bin" / "python")


def resolve(cfg_or_root, p) -> pathlib.Path:
    """Expand ~ in `p` and resolve it relative to the repo root (or a given root).

    `cfg_or_root` is either a config dict (uses its "_repo_root") or a base path.
    Absolute paths are returned unchanged.
    """
    if isinstance(cfg_or_root, dict):
        root = pathlib.Path(cfg_or_root.get("_repo_root", REPO_ROOT))
    else:
        root = pathlib.Path(cfg_or_root)
    if not p:
        return root
    path = pathlib.Path(os.path.expanduser(str(p)))
    if path.is_absolute():
        return path
    return root / path
