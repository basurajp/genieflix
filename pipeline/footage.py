#!/usr/bin/env python3
"""Stage raw or generated footage as a project's scene media: reframe, trim, grade.

Usage:
  footage.py --project <dir> --line 3 --src clip.mov [--start 12.5] [--fit cover|blur]
             [--focus 0.5] [--grade teal-orange] [--lut look.cube] [--grain 0.3] [--vignette 0.4]
  footage.py --project <dir> --src-dir raw/              # stages every lineNN.* file found
  footage.py --project <dir> --grade-sheet clip.mov      # every grade on one frame, labelled
  footage.py --list-grades

Writes <project>/assets/footage/lineNN.mp4 for clips (or lineNN.jpg for stills):

  * reframed to 1080x1920 — "cover" crops to fill (--focus picks the crop
    centre, 0 = left edge, 1 = right edge); "blur" fits the whole frame inside a
    blurred, zoomed copy of itself (the usual treatment for landscape footage)
  * trimmed from --start to the line's duration plus a short handle, and padded
    by holding the last frame if the clip runs short
  * graded with a named grade from styles/grades.json (default: the project
    style's "grade", else none), an optional .cube LUT, grain and vignette —
    baked in with ffmpeg, so the preview, the render and every OS agree
  * audio stripped, constant 30 fps, a keyframe every 30 frames (seek-safe)

The previous take is moved to assets/footage.bak/ before it is overwritten.
build_index.py then uses assets/footage/lineNN.* for that scene.
"""

import argparse
import pathlib
import re
import shutil
import sys

import common

W, H = 1080, 1920
STILL_W, STILL_H = 1350, 2400   # stills get 25% headroom for push-ins
HANDLE = 0.6                     # extra seconds past the line (dissolves, CTA hold)
CLIP_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
STILL_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
GRADES_FILE = common.REPO_ROOT / "styles" / "grades.json"


def load_grades():
    data = common.load_json(GRADES_FILE, {}) or {}
    return data.get("grades") or {}


def style_grade(project):
    style = str(project.get("style") or "").strip()
    if not style or style == "classic":
        return None
    meta = common.load_json(common.REPO_ROOT / "styles" / style / "style.json", {}) or {}
    return meta.get("grade")


def ff_escape(path):
    """Escape a path for use inside an ffmpeg filter argument."""
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def reframe_chain(fit, focus, out_w, out_h):
    if fit == "blur":
        return (
            f"split[bg][fg];"
            f"[bg]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{out_h},gblur=sigma=40,eq=brightness=-0.08[bgb];"
            f"[fg]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease[fgs];"
            f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2"
        )
    return (
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{out_h}:(iw-{out_w})*{focus:.3f}:(ih-{out_h})/2"
    )


def grade_chain(name, grades, lut=None, grain=None, vignette=None):
    if name and name not in grades:
        raise SystemExit(
            f"footage: unknown grade '{name}' — available: {', '.join(sorted(grades))}"
        )
    g = grades.get(name or "none", {})
    parts = []
    if g.get("filters"):
        parts.append(g["filters"])
    if lut:
        lut = pathlib.Path(lut).expanduser().resolve()
        if not lut.is_file():
            raise SystemExit(f"footage: LUT not found: {lut}")
        parts.append(f"lut3d=file='{ff_escape(lut)}'")
    grain = g.get("grain", 0.0) if grain is None else grain
    vignette = g.get("vignette", 0.0) if vignette is None else vignette
    if vignette and vignette > 0:
        # ffmpeg's lens angle: wider darkens more (PI/5 = 0.63 is its default)
        angle = 0.25 + min(vignette, 1.0) * 0.55
        parts.append(f"vignette=angle={angle:.3f}")
    if grain and grain > 0:
        parts.append(f"noise=alls={round(min(grain, 1.0) * 22)}:allf=t+u")
    return ",".join(parts)


def line_seconds(project_dir, index):
    meta = common.load_json(project_dir / "audio_meta.json", {}) or {}
    gap = float(meta.get("line_gap", 0.35))
    for ln in meta.get("lines", []):
        if ln.get("index") == index and ln.get("duration"):
            return float(ln["duration"]) + gap + HANDLE
    return None


def backup(out):
    if out.exists():
        bak = out.parent.parent / "footage.bak"
        bak.mkdir(parents=True, exist_ok=True)
        shutil.move(str(out), str(bak / out.name))


def stage(project_dir, index, src, start, fit, focus, grade, lut, grain, vignette, grades):
    src = pathlib.Path(src).expanduser().resolve()
    if not src.is_file():
        raise SystemExit(f"footage: source not found: {src}")
    out_dir = project_dir / "assets" / "footage"
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob(f"line{index:02d}.*"):
        backup(stale)
    look = grade_chain(grade, grades, lut, grain, vignette)

    if src.suffix.lower() in STILL_EXTS:
        out = out_dir / f"line{index:02d}.jpg"
        chain = reframe_chain(fit, focus, STILL_W, STILL_H) + ("," + look if look else "")
        # noise with allf=t needs a timeline; on a still it is plain grain
        common.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
            "-vf", "format=rgb24," + chain, "-frames:v", "1", "-q:v", "2", str(out),
        ])
        print(f"assets/footage/{out.name}  still, grade {grade or 'none'}")
        return out

    out = out_dir / f"line{index:02d}.mp4"
    need = line_seconds(project_dir, index)
    src_dur = common.ffprobe_duration(src) - start
    if src_dur <= 0:
        raise SystemExit(f"footage: --start {start} is past the end of {src.name}")
    length = need if need else min(src_dur, 12.0)
    pad = max(0.0, length - src_dur)
    chain = "fps=30,format=rgb24," + reframe_chain(fit, focus, W, H)
    if look:
        chain += "," + look
    if pad > 0:
        chain += f",tpad=stop_mode=clone:stop_duration={pad + 0.1:.2f}"
    chain += ",format=yuv420p"
    common.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{length:.3f}",
        "-vf", chain, "-an",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-g", "30", "-keyint_min", "30", "-movflags", "+faststart",
        str(out),
    ])
    note = f", held last frame {pad:.2f}s" if pad > 0 else ""
    print(f"assets/footage/{out.name}  {length:.2f}s, {fit}, grade {grade or 'none'}{note}")
    return out


def grade_sheet(project_dir, src, at, grades, fit, focus):
    """Render every grade onto one frame of src, labelled, as a contact sheet."""
    src = pathlib.Path(src).expanduser().resolve()
    out_dir = project_dir / "grades"
    tmp = out_dir / "_cells"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    font = None
    for cand in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "C:/Windows/Fonts/arialbd.ttf"):
        if pathlib.Path(cand).is_file():
            font = cand
            break
    names = [n for n in grades if n != "none"]
    for k, name in enumerate(["none"] + names):
        look = grade_chain(name, grades)
        label = ""
        if font:
            label = (f",drawtext=fontfile='{ff_escape(font)}':text='{name}':x=12:y=12:"
                     "fontsize=30:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=8")
        seek = ["-ss", f"{at:.3f}"] if src.suffix.lower() not in STILL_EXTS else []
        common.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *seek, "-i", str(src),
            "-frames:v", "1", "-vf",
            "format=rgb24," + reframe_chain(fit, focus, W, H) + ("," + look if look else "")
            + f",scale=360:640{label}",
            str(tmp / f"g{k:03d}.png"),
        ])
    cols = 5
    rows = -(-(len(names) + 1) // cols)
    out = out_dir / f"{re.sub(r'[^A-Za-z0-9_-]+', '-', src.stem)}.jpg"
    common.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-framerate", "1",
        "-i", str(tmp / "g%03d.png"), "-vf", f"tile={cols}x{rows}:padding=6:color=0x111111",
        "-frames:v", "1", "-q:v", "3", str(out),
    ])
    shutil.rmtree(tmp)
    print(f"grade sheet: {out}")


def main():
    ap = argparse.ArgumentParser(description="Reframe, trim and grade footage into a project's scene media.")
    ap.add_argument("--project", help="project directory")
    ap.add_argument("--line", type=int, help="1-based line (scene) this footage plays under")
    ap.add_argument("--src", help="source clip or still")
    ap.add_argument("--src-dir", help="stage every lineNN.<ext> file in this directory")
    ap.add_argument("--start", type=float, default=0.0, help="source in-point in seconds (clips)")
    ap.add_argument("--fit", choices=("cover", "blur"), default="cover",
                    help="cover = crop to fill 9:16; blur = fit inside a blurred copy (landscape footage)")
    ap.add_argument("--focus", type=float, default=0.5, help="horizontal crop centre for cover, 0..1")
    ap.add_argument("--grade", help="grade name from styles/grades.json, or 'none' (default: the style's)")
    ap.add_argument("--lut", help=".cube LUT applied after the grade")
    ap.add_argument("--grain", type=float, help="film grain 0..1 (default: the grade's)")
    ap.add_argument("--vignette", type=float, help="vignette 0..1 (default: the grade's)")
    ap.add_argument("--grade-sheet", metavar="SRC", help="write grades/<name>.jpg comparing every grade on SRC")
    ap.add_argument("--at", type=float, default=1.0, help="frame time for --grade-sheet")
    ap.add_argument("--list-grades", action="store_true", help="print the grade library")
    args = ap.parse_args()

    grades = load_grades()
    if args.list_grades:
        for name, g in grades.items():
            print(f"{name:18s} {g.get('look', '')}")
        return
    if not args.project:
        ap.error("--project is required")
    project_dir = pathlib.Path(args.project).expanduser().resolve()
    project = common.load_project(project_dir)
    if not 0.0 <= args.focus <= 1.0:
        ap.error("--focus must be between 0 and 1")

    if args.grade_sheet:
        grade_sheet(project_dir, args.grade_sheet, args.at, grades, args.fit, args.focus)
        return

    grade = args.grade if args.grade is not None else style_grade(project)
    if grade == "none":
        grade = None
    jobs = []
    if args.src_dir:
        src_dir = pathlib.Path(args.src_dir).expanduser().resolve()
        for f in sorted(src_dir.iterdir()):
            m = re.fullmatch(r"line(\d{2})", f.stem)
            if m and f.suffix.lower() in CLIP_EXTS | STILL_EXTS:
                jobs.append((int(m.group(1)), f))
        if not jobs:
            raise SystemExit(f"footage: no lineNN.<clip|still> files in {src_dir}")
    elif args.src and args.line:
        jobs.append((args.line, pathlib.Path(args.src)))
    else:
        ap.error("give --line with --src, or --src-dir")

    for index, src in jobs:
        stage(project_dir, index, src, args.start if args.src else 0.0, args.fit, args.focus,
              grade, args.lut, args.grain, args.vignette, grades)
    print(f"staged {len(jobs)} item(s) — rebuild with pipeline/build_index.py, then render")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
