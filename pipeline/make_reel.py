#!/usr/bin/env python3
"""Run the whole reel pipeline for one project, step by step.

Usage: pipeline/make_reel.py --project <dir> [--phase voice|render|all] [--force]

Phases: voice = steps 1-6 (TTS through the generated composition), render =
steps 7-8 (QA render + finishing pass + delivery), all = both. Every step runs
as its own subprocess so each script stays usable standalone; output streams
through, and the first failure stops the run with the failing step named.
"""

import argparse
import pathlib
import shlex
import subprocess
import sys

import common

PIPELINE_DIR = pathlib.Path(__file__).resolve().parent

VOICE_STEPS = (
    "voice.py",
    "audio_chain.py",
    "transcribe.py",
    "build_timeline.py",
    "captions.py",
    "build_index.py",
)
RENDER_STEPS = ("qa.py", "finish.py")


def run_step(script, project_dir, extra=()):
    """Run one pipeline step as a subprocess, streaming its output."""
    cmd = [
        sys.executable,
        str(PIPELINE_DIR / script),
        "--project",
        str(project_dir),
        *extra,
    ]
    print(f"\n=== {script} ===", flush=True)
    print("+ " + shlex.join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(common.REPO_ROOT))
    if proc.returncode != 0:
        raise SystemExit(f"make_reel: step {script} failed (exit {proc.returncode})")


def main():
    parser = argparse.ArgumentParser(
        description="Chain the pipeline steps (voice -> compose -> QA -> deliver) for one project."
    )
    parser.add_argument("--project", required=True, help="project directory")
    parser.add_argument(
        "--phase",
        choices=("voice", "render", "all"),
        default="all",
        help="voice = steps 1-6, render = steps 7-8, all = 1-8 (default)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="regenerate voice lines even if their raw WAVs exist (old takes are backed up)",
    )
    args = parser.parse_args()

    project_dir = pathlib.Path(args.project).expanduser().resolve()
    if not project_dir.is_dir():
        raise SystemExit(f"make_reel: project directory not found: {project_dir}")

    steps = []
    if args.phase in ("voice", "all"):
        for script in VOICE_STEPS:
            extra = ("--force",) if (script == "voice.py" and args.force) else ()
            steps.append((script, extra))
    if args.phase in ("render", "all"):
        for script in RENDER_STEPS:
            steps.append((script, ()))

    for script, extra in steps:
        run_step(script, project_dir, extra)

    print(f"\nmake_reel: phase '{args.phase}' complete for {project_dir.name}")


if __name__ == "__main__":
    main()
