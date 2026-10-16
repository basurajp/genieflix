#!/usr/bin/env python3
"""Download supplied narration into a project's vo/ folder, one file per line.

Usage: pipeline/fetch_vo.py --project <dir> --manifest <vo.json> [--force]

The manifest maps 1-based line numbers to URLs (a hosted TTS such as
ElevenLabs through Higgsfield, or anywhere else you keep the takes):

  {"voice": "Cillian (ElevenLabs via Higgsfield)",
   "lines": {"1": "https://.../take1.mp3", "2": "https://.../take2.mp3"}}

Each URL lands as <project>/vo/lineNN.<ext>; voice.py then picks the "files"
backend automatically. Existing files are kept unless --force (the old one is
moved to vo.bak/ first). The manifest's line count must match lines.txt.
"""

import argparse
import pathlib
import shutil
import sys
import urllib.parse
import urllib.request

import common

VO_EXTS = (".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".webm")


def main():
    ap = argparse.ArgumentParser(description="Fill <project>/vo/ from a line-number -> URL manifest.")
    ap.add_argument("--project", required=True, help="project directory")
    ap.add_argument("--manifest", required=True, help="JSON file: {\"lines\": {\"1\": url, ...}}")
    ap.add_argument("--force", action="store_true", help="re-download lines that already have a file")
    args = ap.parse_args()

    project_dir = pathlib.Path(args.project).expanduser().resolve()
    manifest = common.load_json(pathlib.Path(args.manifest).expanduser())
    if not manifest or not isinstance(manifest.get("lines"), dict):
        raise SystemExit(f"fetch_vo: {args.manifest} has no \"lines\" object")
    lines = common.read_lines(project_dir)
    urls = {int(k): v for k, v in manifest["lines"].items()}
    missing = [i for i in range(1, len(lines) + 1) if i not in urls]
    extra = [i for i in urls if not 1 <= i <= len(lines)]
    if missing or extra:
        raise SystemExit(
            f"fetch_vo: manifest does not match lines.txt ({len(lines)} lines): "
            f"missing {missing or 'none'}, extra {extra or 'none'}"
        )

    vo_dir = project_dir / "vo"
    vo_dir.mkdir(parents=True, exist_ok=True)
    for index in sorted(urls):
        stem = f"line{index:02d}"
        ext = pathlib.Path(urllib.parse.urlparse(urls[index]).path).suffix.lower()
        ext = ext if ext in VO_EXTS else ".mp3"
        existing = [p for p in vo_dir.glob(f"{stem}.*") if p.suffix.lower() in VO_EXTS]
        if existing and not args.force:
            print(f"skip vo/{existing[0].name} (exists; --force to replace)")
            continue
        for old in existing:
            bak = project_dir / "vo.bak"
            bak.mkdir(exist_ok=True)
            shutil.move(str(old), str(bak / old.name))
        out = vo_dir / f"{stem}{ext}"
        tmp = out.with_suffix(out.suffix + ".part")
        with urllib.request.urlopen(urls[index], timeout=60) as resp, open(tmp, "wb") as fh:
            shutil.copyfileobj(resp, fh)
        tmp.replace(out)
        print(f"vo/{out.name}  {common.ffprobe_duration(out):.2f}s  {lines[index - 1][:60]}")
    print(f"fetch_vo: {vo_dir} ready — run make_reel.py --phase voice (backend: files)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
