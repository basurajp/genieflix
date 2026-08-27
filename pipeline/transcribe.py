#!/usr/bin/env python3
"""Per-line word timestamps -> words.json, with the correction pass applied.

Usage: pipeline/transcribe.py --project <dir>

English projects (project.json "lang": "en") run each processed audio/lineNN.wav
through `npx hyperframes transcribe --json` (local Whisper) and store word
timestamps RELATIVE to that line's own audio. Any other lang (e.g. "hinglish")
skips ASR entirely — Whisper's English model mangles the words — and writes an
empty line list; captions.py then times captions proportionally from the written
text, so spelling stays exactly as authored.

Corrections: ASR mis-hears brand and product names, so pipeline/corrections.json
ships a comment-free dictionary shaped as {"replacements": {"misheard": "Correct"}}
— extend it with the names you use.
Each transcribed word is matched case-insensitively (surrounding punctuation
ignored) and its text replaced while the start/end timestamps stay intact.
The project's cta_keyword is uppercased the same way.
"""

import argparse
import json
import pathlib
import shutil
import subprocess
import sys

import common


def parse_json_stdout(text):
    """Extract the first JSON object/array from CLI stdout, tolerating noise
    (npm warnings, progress lines) before or after it."""
    decoder = json.JSONDecoder()
    for pos, char in enumerate(text):
        if char not in "{[":
            continue
        try:
            obj, _ = decoder.raw_decode(text, pos)
        except ValueError:
            continue
        if isinstance(obj, (dict, list)):
            return obj
    raise ValueError("no JSON found in transcribe output")


def extract_words(obj):
    """Pull a word list out of the transcript JSON, tolerating several shapes:
    top-level "words", "segments"[]."words", or a bare list of words/segments."""
    raw = []
    if isinstance(obj, dict):
        if isinstance(obj.get("words"), list):
            raw = obj["words"]
        elif isinstance(obj.get("segments"), list):
            raw = [
                word
                for segment in obj["segments"]
                if isinstance(segment, dict)
                for word in (segment.get("words") or [])
            ]
    elif isinstance(obj, list):
        if obj and isinstance(obj[0], dict) and "words" in obj[0]:
            raw = [
                word
                for segment in obj
                if isinstance(segment, dict)
                for word in (segment.get("words") or [])
            ]
        else:
            raw = obj

    words = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        text = item.get("word", item.get("text"))
        try:
            start = float(item.get("start"))
            end = float(item.get("end"))
        except (TypeError, ValueError):
            continue
        if text is None:
            continue
        text = str(text).strip()
        if not text:
            continue
        words.append({"word": text, "start": round(start, 3), "end": round(end, 3)})
    words.sort(key=lambda w: (w["start"], w["end"]))
    return words


def split_token(token):
    """Split a word into (leading punctuation, core, trailing punctuation)."""
    start, end = 0, len(token)
    while start < end and not token[start].isalnum():
        start += 1
    while end > start and not token[end - 1].isalnum():
        end -= 1
    return token[:start], token[start:end], token[end:]


def apply_corrections(words, replacements, cta_keyword):
    """Fix word text in place (timestamps untouched); return how many changed."""
    fixed = 0
    for word in words:
        prefix, core, suffix = split_token(word["word"])
        if not core:
            continue
        key = core.lower()
        if key in replacements and core != replacements[key]:
            word["word"] = prefix + replacements[key] + suffix
            fixed += 1
        elif cta_keyword and key == cta_keyword.lower() and core != cta_keyword.upper():
            word["word"] = prefix + cta_keyword.upper() + suffix
            fixed += 1
    return fixed


def transcribe_line(project_dir, wav, whisper_model):
    npx = shutil.which("npx") or "npx"
    proc = common.run(
        [
            npx, "hyperframes", "transcribe", str(wav),
            "-d", str(project_dir),
            "--model", whisper_model,
            "--json",
        ],
        cwd=project_dir,
        capture=True,
    )
    try:
        obj = parse_json_stdout(proc.stdout)
    except ValueError:
        raise SystemExit(
            f"transcribe.py: could not parse JSON for {wav}\n"
            f"stdout was:\n{proc.stdout.strip()[:2000]}"
        ) from None
    return extract_words(obj)


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe each processed line WAV to word timestamps (words.json)."
    )
    parser.add_argument("--project", required=True, help="project directory")
    args = parser.parse_args()

    project_dir = pathlib.Path(args.project).expanduser().resolve()
    cfg = common.load_config()
    project = common.load_project(project_dir)
    words_path = project_dir / "words.json"

    lang = str(project.get("lang", "en") or "en").strip().lower()
    if lang != "en":
        common.save_json(
            words_path,
            {"lines": [], "note": f"lang={lang}: ASR skipped, captions use proportional timing"},
        )
        print(f"lang={lang}: skipping ASR — captions.py will time groups proportionally")
        print(f"wrote {words_path}")
        return

    meta = common.load_json(project_dir / "audio_meta.json")
    if not meta or not meta.get("lines"):
        raise SystemExit(f"missing or empty audio_meta.json in {project_dir} — run audio_chain.py first")

    corrections = common.load_json(common.REPO_ROOT / "pipeline" / "corrections.json", {}) or {}
    replacements = {
        str(k).lower(): str(v) for k, v in (corrections.get("replacements") or {}).items()
    }
    cta_keyword = str(project.get("cta_keyword") or "").strip()

    result = []
    for entry in meta["lines"]:
        index = entry["index"]
        wav = project_dir / entry["file"]
        if not wav.exists():
            raise SystemExit(f"missing {wav} — run audio_chain.py first")
        words = transcribe_line(project_dir, wav, cfg.get("whisper_model", "small.en"))
        fixed = apply_corrections(words, replacements, cta_keyword)
        if not words:
            print(f"warning: no words for line {index} — captions.py will fall back to proportional timing")
        note = f" ({fixed} corrected)" if fixed else ""
        print(f"line {index:02d}: {len(words)} words{note}")
        result.append({"index": index, "words": words})

    common.save_json(words_path, {"lines": result})
    print(f"wrote {words_path}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()
        message = f"transcribe.py: command failed with exit {exc.returncode}"
        if detail:
            message += "\n" + detail
        sys.exit(message)
