#!/usr/bin/env python3
"""QA gate: lint, snapshot key beats, render, inspect the real MP4, gate loudness.

Usage: pipeline/qa.py --project <dir> [--skip-render]

The renderer diverges from the preview, so after rendering, frames are pulled
straight out of the finished MP4 with ffmpeg — verify the render, not the
preview. Fails when lint reports errors or when the rendered file's mean
loudness falls outside the configured window.
"""

import argparse
import json
import pathlib
import shlex
import shutil
import subprocess
import sys

import common


def npx():
    return shutil.which("npx") or "npx"


def parse_json_loose(text):
    """Parse JSON from CLI stdout, tolerating leading non-JSON noise lines."""
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for i, ch in enumerate(text):
            if ch in "[{":
                try:
                    return json.loads(text[i:])
                except json.JSONDecodeError:
                    break
        raise ValueError("not JSON") from None


def extract_findings(data):
    """Normalize `hyperframes lint --json` output to a flat list of findings."""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        raise ValueError("unexpected lint output shape")
    for key in ("findings", "issues", "results", "problems"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    found = []
    matched = False
    for key, severity in (("errors", "error"), ("warnings", "warning"), ("info", "info")):
        value = data.get(key)
        if isinstance(value, list):
            matched = True
            for item in value:
                if isinstance(item, dict):
                    item = dict(item)
                    item.setdefault("severity", severity)
                    found.append(item)
                else:
                    found.append({"severity": severity, "message": str(item)})
    if matched:
        return found
    raise ValueError("unexpected lint output shape")


def finding_severity(finding):
    if isinstance(finding, dict):
        sev = str(
            finding.get("severity") or finding.get("level") or finding.get("type") or ""
        ).lower()
    else:
        sev = ""
    if sev.startswith("err") or sev == "fatal":
        return "error"
    if sev == "info":
        return "info"
    return "warning"


def finding_message(finding):
    if isinstance(finding, dict):
        for key in ("message", "text", "msg", "detail", "description"):
            if finding.get(key):
                message = str(finding[key])
                where = (
                    finding.get("selector")
                    or finding.get("element")
                    or finding.get("id")
                    or finding.get("file")
                )
                return f"{message} ({where})" if where else message
        return json.dumps(finding, ensure_ascii=False)
    return str(finding)


def lint(project_dir):
    """Gate one: zero lint errors before any render time is spent."""
    cmd = [npx(), "hyperframes", "lint", str(project_dir), "--json"]
    print("+ " + shlex.join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(common.REPO_ROOT), text=True, capture_output=True)
    try:
        findings = extract_findings(parse_json_loose(proc.stdout))
    except ValueError:
        # Could not read structured findings; fall back to raw output + exit code.
        sys.stdout.write(proc.stdout or "")
        sys.stderr.write(proc.stderr or "")
        if proc.returncode != 0:
            raise SystemExit(f"qa: lint failed (exit {proc.returncode})")
        print("qa: lint passed")
        return

    errors = 0
    for finding in findings:
        severity = finding_severity(finding)
        errors += severity == "error"
        print(f"lint {severity}: {finding_message(finding)}")
    if errors:
        raise SystemExit(
            f"qa: lint found {errors} error(s) — fix the composition before rendering"
        )
    if proc.returncode != 0:
        raise SystemExit(f"qa: lint failed (exit {proc.returncode})")
    if findings:
        print(f"qa: lint passed ({len(findings)} non-error finding(s))")
    else:
        print("qa: lint passed (no findings)")


def key_beats(timeline):
    """The four moments worth eyeballing: hook, 25%, 50%, and the CTA start."""
    total = float(timeline["total"])
    scenes = timeline.get("scenes") or []
    cta_start = float(scenes[-1]["start"]) if scenes else max(total - 1.0, 0.0)
    last_safe = max(total - 0.05, 0.0)
    beats = [
        ("hook", 0.2),
        ("quarter", total * 0.25),
        ("half", total * 0.5),
        ("cta", cta_start),
    ]
    return [(name, round(min(max(t, 0.0), last_safe), 2)) for name, t in beats]


def snapshot(project_dir, beats):
    """Gate two: snapshot the key beats so obvious disasters die cheap."""
    out_dir = project_dir / "snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    times = sorted({f"{t:.2f}" for _, t in beats}, key=float)
    common.run(
        [
            npx(), "hyperframes", "snapshot", str(project_dir),
            "--at", ",".join(times),
            "-o", str(out_dir),
        ],
        cwd=common.REPO_ROOT,
    )
    print(f"qa: snapshots in {out_dir} — read them, don't glance")


def render(project_dir):
    """Gate three, part one: the full high-quality render."""
    out = project_dir / "renders" / "reel.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    common.run(
        [
            npx(), "hyperframes", "render", str(project_dir),
            "--quality", "high",
            "-o", str(out),
        ],
        cwd=common.REPO_ROOT,
    )
    if not out.exists():
        raise SystemExit(f"qa: render reported success but {out} is missing")
    return out


def extract_frames(mp4, project_dir, beats):
    """Gate three, part two: pull frames from the real MP4 — the output is the truth."""
    duration = common.ffprobe_duration(mp4)
    last_safe = max(duration - 0.05, 0.0)
    frames_dir = project_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for i, (name, t) in enumerate(beats, 1):
        out = frames_dir / f"{i:02d}-{name}.png"
        common.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-ss", f"{min(t, last_safe):.3f}",
                "-i", str(mp4),
                "-frames:v", "1",
                str(out),
            ]
        )
    print(f"qa: frames from the rendered MP4 in {frames_dir} — verify the render, not the preview")


def loudness_gate(cfg, mp4):
    """Gate four: the number catches what tired ears miss."""
    lo = float(cfg.get("loudness_min_db", -17.0))
    hi = float(cfg.get("loudness_max_db", -13.0))
    stats = common.volumedetect(mp4)
    mean, peak = stats["mean_db"], stats["max_db"]
    print(f"qa: rendered loudness mean {mean:.1f} dB, peak {peak:.1f} dB (window {lo:.1f}..{hi:.1f})")
    if not lo <= mean <= hi:
        raise SystemExit(
            f"qa: loudness gate failed — mean {mean:.1f} dB is outside [{lo:.1f}, {hi:.1f}].\n"
            "The voice drifted quiet or the music crept up; run pipeline/remix.py "
            "to renormalize the mix without regenerating the voice."
        )


def main():
    parser = argparse.ArgumentParser(
        description="Run the QA loop: lint, snapshot, render, extract frames, measure loudness."
    )
    parser.add_argument("--project", required=True, help="project directory")
    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="skip the render; inspect the existing renders/reel.mp4 if there is one",
    )
    args = parser.parse_args()

    project_dir = pathlib.Path(args.project).expanduser().resolve()
    if not project_dir.is_dir():
        raise SystemExit(f"qa: project directory not found: {project_dir}")
    cfg = common.load_config()

    if not (project_dir / "index.html").exists():
        raise SystemExit(
            f"qa: no index.html in {project_dir} — run build_index.py "
            "(or make_reel.py --phase voice) first"
        )
    timeline = common.load_json(project_dir / "timeline.json")
    if not timeline or "total" not in timeline:
        raise SystemExit(
            f"qa: no timeline.json in {project_dir} — run build_timeline.py first"
        )
    beats = key_beats(timeline)

    lint(project_dir)
    snapshot(project_dir, beats)

    mp4 = project_dir / "renders" / "reel.mp4"
    if args.skip_render:
        if not mp4.exists():
            print("qa: --skip-render and no renders/reel.mp4 yet — lint + snapshots only")
            return
        print("qa: --skip-render — inspecting the existing renders/reel.mp4")
    else:
        mp4 = render(project_dir)

    extract_frames(mp4, project_dir, beats)
    loudness_gate(cfg, mp4)
    print("qa: all gates passed — renders/reel.mp4 is verified")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()
        message = f"qa.py: command failed with exit {exc.returncode}"
        if detail:
            message += "\n" + detail
        sys.exit(message)
