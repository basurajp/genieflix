#!/usr/bin/env python3
"""Regenerate a whole project in your own voice with one command.

Usage: pipeline/revoice.py --project <dir>

Forces the full pipeline (steps 1-8): fresh TTS for every line — the previous
takes are copied to raw.bak/ and audio.bak/ before anything lands, so a bad
regeneration is never a lost one — then the polish chain, transcription with
the corrections dictionary, timeline, captions, a regenerated composition, and
finally the QA render plus the finishing pass. index.html is rebuilt from the
plan (lines.txt + project.json): hand-edits to generated files are wiped by
design. If a custom element should survive, it goes in the plan.
"""

import argparse
import pathlib
import shlex
import subprocess
import sys

import common

PIPELINE_DIR = pathlib.Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(
        description="Force a full regeneration (voice through delivery) for one project."
    )
    parser.add_argument("--project", required=True, help="project directory")
    args = parser.parse_args()

    project_dir = pathlib.Path(args.project).expanduser().resolve()
    if not project_dir.is_dir():
        raise SystemExit(f"revoice: project directory not found: {project_dir}")

    cmd = [
        sys.executable,
        str(PIPELINE_DIR / "make_reel.py"),
        "--project",
        str(project_dir),
        "--phase",
        "all",
        "--force",
    ]
    print("+ " + shlex.join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(common.REPO_ROOT))
    if proc.returncode != 0:
        raise SystemExit(f"revoice: pipeline failed (exit {proc.returncode})")
    print(f"revoice: {project_dir.name} fully regenerated and delivered")


if __name__ == "__main__":
    main()
