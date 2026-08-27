#!/usr/bin/env python3
"""Generate a project's index.html composition from template/index.html.

Usage: build_index.py --project <dir>
"""

import argparse
import bisect
import html
import shutil
import sys
from pathlib import Path

import common

# Markers the template must contain; replacement is plain string substitution.
CORE_MARKERS = (
    "<!--HF:DURATION-->",
    "<!--HF:TITLE-->",
    "<!--HF:KICKER-->",
    "<!--HF:SLIDES-->",
    "<!--HF:CAPTIONS-->",
    "<!--HF:AUDIO-->",
    "<!--HF:TIMELINE-->",
)

# Track map: 0 background, 1 slides, 2 overlays, 3 captions, 4 voice,
# 5 music, 6 sfx. Overlays MUST be timed clips on a track above the media
# they cover, or the renderer composites them underneath.
TRACK_SLIDES = 1
TRACK_CAPTIONS = 3
TRACK_VOICE = 4
TRACK_MUSIC = 5
TRACK_SFX = 6

PUSH_IN_MAX = 2.5   # opening push-in length cap (scale 1.1 -> 1.0)
ENTRANCE = 0.35     # scene entrance fade, synced to its line start
PULSE_EVERY = 2.5   # inject motion so no static stretch exceeds ~3 s
PULSE_LEN = 0.6
STATIC_LIMIT = 3.0


def die(msg):
    print(f"build_index: error: {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg):
    print(f"build_index: warning: {msg}", file=sys.stderr)


def fmt(t):
    return f"{float(t):.3f}"


def require_json(project_dir, name, hint):
    path = project_dir / name
    if not path.is_file():
        die(f"{path} not found — {hint}")
    return common.load_json(path)


def ensure_assets(project_dir):
    """Copy template assets into the project: gsap always if missing,
    fonts/music/sfx files only when absent (never clobber project media)."""
    template_assets = common.REPO_ROOT / "template" / "assets"
    dest_assets = project_dir / "assets"
    dest_assets.mkdir(parents=True, exist_ok=True)

    gsap_src = template_assets / "gsap.min.js"
    gsap_dst = dest_assets / "gsap.min.js"
    if not gsap_dst.is_file():
        if not gsap_src.is_file():
            die(f"{gsap_src} missing — the vendored GSAP file must exist (offline requirement)")
        shutil.copy2(gsap_src, gsap_dst)

    for sub in ("fonts", "music", "sfx"):
        src_dir = template_assets / sub
        dst_dir = dest_assets / sub
        dst_dir.mkdir(parents=True, exist_ok=True)
        if not src_dir.is_dir():
            continue
        for src in sorted(src_dir.rglob("*")):
            if not src.is_file():
                continue
            dst = dst_dir / src.relative_to(src_dir)
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)


def build_slides(scenes):
    out = []
    for scene in scenes:
        out.append(
            f'<img id="scene-{scene["index"]}" class="clip slide" '
            f'src="{html.escape(scene["slide"])}" alt="" '
            f'data-start="{fmt(scene["start"])}" data-duration="{fmt(scene["duration"])}" '
            f'data-track-index="{TRACK_SLIDES}">'
        )
    return "\n  ".join(out)


def build_captions(captions):
    out = []
    for cap in captions:
        duration = max(0.06, float(cap["end"]) - float(cap["start"]))
        out.append(
            f'<div class="clip caption" data-start="{fmt(cap["start"])}" '
            f'data-duration="{fmt(duration)}" data-track-index="{TRACK_CAPTIONS}">'
            f'{html.escape(cap["text"])}</div>'
        )
    return "\n  ".join(out)


def music_volume(music_path, target_db):
    """data-volume multiplier that lands the bed at the target mean level."""
    stats = common.volumedetect(music_path)
    mean_db = float(stats["mean_db"])
    multiplier = 10 ** ((target_db - mean_db) / 20.0)
    if multiplier > 1.0:
        warn(
            f"music bed mean is {mean_db:.1f} dB, quieter than the {target_db:.1f} dB "
            "target even at full volume — clamping data-volume to 1.0"
        )
    volume = max(0.0001, min(1.0, multiplier))
    print(
        f"build_index: music bed mean {mean_db:.1f} dB -> data-volume {volume:.4f} "
        f"(target {target_db:.1f} dB)"
    )
    return volume


def build_audio(project_dir, project, cfg, meta_lines, scenes, total):
    out = []
    for ln in meta_lines:
        out.append(
            f'<audio class="clip" src="{html.escape(ln["file"])}" '
            f'data-start="{fmt(ln["start"])}" data-duration="{fmt(ln["duration"])}" '
            f'data-track-index="{TRACK_VOICE}"></audio>'
        )

    music_rel = (project.get("music") or "").strip()
    if music_rel:
        music_path = project_dir / music_rel
        if music_path.is_file():
            volume = music_volume(music_path, float(cfg.get("music_target_db", -31.0)))
            out.append(
                f'<audio id="music-bed" class="clip" src="{html.escape(music_rel)}" '
                f'data-start="0" data-duration="{fmt(total)}" '
                f'data-track-index="{TRACK_MUSIC}" data-volume="{volume:.4f}"></audio>'
            )
        else:
            print(
                f"build_index: note: music file not found ({music_path}) — rendering "
                'without a bed. Drop one in assets/music/ or set "music": "" in project.json.'
            )

    sfx_volume = float(cfg.get("sfx_volume", 0.22))
    scene_starts = [scene["start"] for scene in scenes]
    used_scenes = set()
    for entry in project.get("sfx") or []:
        rel = (entry.get("file") or "").strip()
        at = float(entry.get("at", 0.0))
        sfx_path = project_dir / rel
        if not rel or not sfx_path.is_file():
            warn(f"sfx file not found, skipping: {rel or entry}")
            continue
        if at >= total:
            warn(f"sfx at {at:.2f}s is past the end ({total:.2f}s), skipping: {rel}")
            continue
        # One effect per visual beat, never stacked.
        scene_idx = max(0, bisect.bisect_right(scene_starts, at) - 1)
        if scene_idx in used_scenes:
            warn(f"sfx at {at:.2f}s lands in a scene that already has one, skipping: {rel}")
            continue
        used_scenes.add(scene_idx)
        duration = min(common.ffprobe_duration(sfx_path), total - at)
        out.append(
            f'<audio class="clip" src="{html.escape(rel)}" '
            f'data-start="{fmt(at)}" data-duration="{fmt(duration)}" '
            f'data-track-index="{TRACK_SFX}" data-volume="{sfx_volume:g}"></audio>'
        )

    return "\n  ".join(out)


def pulse_times(start, duration):
    """Pulse start times for a scene, so no static stretch exceeds ~3 s."""
    times = []
    if duration <= STATIC_LIMIT:
        return times
    t = start + PULSE_EVERY
    while t + PULSE_LEN <= start + duration - 0.2:
        times.append(t)
        t += PULSE_EVERY
    return times


def build_timeline_js(scenes, title_end, cta_start):
    """GSAP tween lines for the single paused timeline. Opacity/transform
    only — never a media element's width/height or clip-path (the frame
    renderer ignores those even when the preview honors them)."""
    ind = "    "
    js = []

    first = scenes[0]
    push = min(PUSH_IN_MAX, first["duration"])
    js.append(f"{ind}// opening push-in: motion from frame zero (scale 1.1 -> 1.0)")
    js.append(
        f'{ind}tl.fromTo("#scene-{first["index"]}", {{scale: 1.1}}, '
        f'{{scale: 1.0, duration: {fmt(push)}, ease: "power1.out"}}, 0);'
    )

    for scene in scenes[1:]:
        js.append(f"{ind}// scene {scene['index']}: entrance synced to its line start")
        js.append(
            f'{ind}tl.fromTo("#scene-{scene["index"]}", {{opacity: 0, y: 40}}, '
            f'{{opacity: 1, y: 0, duration: {fmt(ENTRANCE)}, ease: "power2.out"}}, '
            f'{fmt(scene["start"])});'
        )

    for scene in scenes:
        for t in pulse_times(scene["start"], scene["duration"]):
            js.append(f"{ind}// scene {scene['index']}: pulse — no static stretch over 3 s")
            js.append(
                f'{ind}tl.to("#scene-{scene["index"]}", '
                f'{{scale: 1.03, duration: {fmt(PULSE_LEN / 2)}, ease: "sine.inOut"}}, {fmt(t)});'
            )
            js.append(
                f'{ind}tl.to("#scene-{scene["index"]}", '
                f'{{scale: 1.0, duration: {fmt(PULSE_LEN / 2)}, ease: "sine.inOut"}}, '
                f'{fmt(t + PULSE_LEN / 2)});'
            )

    fade_start = max(0.0, title_end - ENTRANCE)
    js.append(f"{ind}// title card fades as scene 1 ends; hard set at the clip")
    js.append(f"{ind}// boundary so the final frame cannot flicker back to full opacity")
    js.append(
        f'{ind}tl.to("#title-card", {{opacity: 0, duration: {fmt(title_end - fade_start)}, '
        f'ease: "power1.in"}}, {fmt(fade_start)});'
    )
    js.append(f'{ind}tl.set("#title-card", {{opacity: 0}}, {fmt(title_end)});')

    js.append(f"{ind}// CTA stamp pops in with the last line and holds to the end")
    js.append(
        f'{ind}tl.fromTo("#cta-stamp", {{opacity: 0, scale: 0.85}}, '
        f'{{opacity: 1, scale: 1, duration: {fmt(ENTRANCE)}, ease: "back.out(1.8)"}}, '
        f'{fmt(cta_start)});'
    )
    return "\n".join(js)


def main():
    ap = argparse.ArgumentParser(
        description="Assemble a project's index.html from the template, timeline, captions, and audio."
    )
    ap.add_argument("--project", required=True, help="project directory")
    args = ap.parse_args()

    project_dir = Path(args.project).expanduser().resolve()
    if not project_dir.is_dir():
        die(f"project directory not found: {project_dir}")
    if not (project_dir / "project.json").is_file():
        die(f"{project_dir / 'project.json'} not found")

    cfg = common.load_config()
    project = common.load_project(project_dir)
    meta = require_json(project_dir, "audio_meta.json", "run voice.py and audio_chain.py first")
    timeline = require_json(project_dir, "timeline.json", "run build_timeline.py first")
    captions = require_json(project_dir, "captions.json", "run captions.py first")

    scenes = timeline.get("scenes") or []
    total = float(timeline.get("total") or 0.0)
    if not scenes or total <= 0:
        die("timeline.json has no scenes — re-run build_timeline.py")
    meta_lines = sorted(meta.get("lines") or [], key=lambda ln: ln["index"])
    if not meta_lines or any("start" not in ln for ln in meta_lines):
        die("audio_meta.json is missing line starts — re-run build_timeline.py")
    if not captions:
        warn("captions.json is empty — rendering without caption chips")

    template_path = common.REPO_ROOT / "template" / "index.html"
    if not template_path.is_file():
        die(f"template not found: {template_path}")
    template = template_path.read_text(encoding="utf-8")
    for marker in CORE_MARKERS:
        if marker not in template:
            die(f"template is missing required marker {marker}")

    ensure_assets(project_dir)

    title_end = round(scenes[0]["start"] + scenes[0]["duration"], 3)
    cta_start = float(scenes[-1]["start"])
    kicker = (project.get("topic") or "new").strip().upper()
    title = (project.get("title") or project.get("slug") or "reel").strip()
    cta_keyword = (project.get("cta_keyword") or "LINK").strip()

    replacements = {
        "<!--HF:DURATION-->": fmt(total),
        "<!--HF:TITLE-->": html.escape(title),
        "<!--HF:KICKER-->": html.escape(kicker),
        "<!--HF:TITLE_DURATION-->": fmt(title_end),
        "<!--HF:CTA_START-->": fmt(cta_start),
        "<!--HF:CTA_DURATION-->": fmt(total - cta_start),
        "<!--HF:CTA_KEYWORD-->": html.escape(cta_keyword),
        "<!--HF:SLIDES-->": build_slides(scenes),
        "<!--HF:CAPTIONS-->": build_captions(captions),
        "<!--HF:AUDIO-->": build_audio(project_dir, project, cfg, meta_lines, scenes, total),
        "<!--HF:TIMELINE-->": build_timeline_js(scenes, title_end, cta_start),
    }

    out = template
    for marker, value in replacements.items():
        out = out.replace(marker, value)
    if "<!--HF:" in out:
        die("unreplaced HF markers remain in the generated index.html — template drift?")

    out_path = project_dir / "index.html"
    out_path.write_text(out, encoding="utf-8")
    print(
        f"build_index: wrote {out_path} ({len(scenes)} scenes, "
        f"{len(captions)} captions, {total:.2f}s)"
    )


if __name__ == "__main__":
    main()
