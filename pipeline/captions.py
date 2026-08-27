#!/usr/bin/env python3
"""Build captions.json: caption groups of at most 4 words on the absolute timeline.

Usage: pipeline/captions.py --project <dir>

English projects group the real Whisper word timestamps from words.json —
breaking at punctuation, pauses longer than 0.28 s, or 4 words — and offset each
group by its line's start on the timeline. Non-English projects (and any line
whose ASR came back empty) get proportional timing instead: the written line is
split into groups of at most 4 words and each group receives a slice of the
line's audio duration sized to its share of the characters, so the spelling is
always the author's and the sync still pins to the real audio.
"""

import argparse
import pathlib
import sys

import common

MAX_WORDS = 4
PAUSE_GAP = 0.28  # seconds of silence between words that forces a group break
BREAK_PUNCT = ".,!?;:"
CLOSERS = "\"'’”)]"  # closing quotes/brackets that may trail punctuation


def ends_with_break(token):
    return token.rstrip(CLOSERS)[-1:] in BREAK_PUNCT


def group_timed_words(words):
    """Chunk Whisper words into caption groups of <= MAX_WORDS."""
    groups, current = [], []
    for pos, word in enumerate(words):
        current.append(word)
        nxt = words[pos + 1] if pos + 1 < len(words) else None
        if (
            len(current) >= MAX_WORDS
            or ends_with_break(word["word"])
            or (nxt is not None and nxt["start"] - word["end"] > PAUSE_GAP)
        ):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def timed_captions(words, line_start):
    captions = []
    for group in group_timed_words(words):
        start = line_start + group[0]["start"]
        end = line_start + group[-1]["end"]
        if end <= start:
            end = start + 0.05
        captions.append(
            {
                "text": " ".join(w["word"] for w in group),
                "start": round(start, 3),
                "end": round(end, 3),
            }
        )
    return captions


def split_text(text):
    """Split written text into groups of <= MAX_WORDS, breaking at punctuation."""
    groups, current = [], []
    for token in text.split():
        current.append(token)
        if len(current) >= MAX_WORDS or ends_with_break(token):
            groups.append(" ".join(current))
            current = []
    if current:
        groups.append(" ".join(current))
    return groups


def proportional_captions(text, line_start, duration):
    """Give each written group a slice of the line's audio time proportional to
    its character length. No ASR involved — spelling comes from the text."""
    groups = split_text(text)
    if not groups or duration <= 0:
        return []
    weights = [max(1, len(g)) for g in groups]
    total = float(sum(weights))
    captions, cursor = [], float(line_start)
    for group, weight in zip(groups, weights):
        slice_dur = duration * weight / total
        captions.append(
            {"text": group, "start": round(cursor, 3), "end": round(cursor + slice_dur, 3)}
        )
        cursor += slice_dur
    return captions


def main():
    parser = argparse.ArgumentParser(
        description="Build captions.json (groups of <=4 words, absolute timeline seconds)."
    )
    parser.add_argument("--project", required=True, help="project directory")
    args = parser.parse_args()

    project_dir = pathlib.Path(args.project).expanduser().resolve()
    project = common.load_project(project_dir)
    lang = str(project.get("lang", "en") or "en").strip().lower()

    meta = common.load_json(project_dir / "audio_meta.json")
    if not meta or not meta.get("lines"):
        raise SystemExit(f"missing or empty audio_meta.json in {project_dir} — run audio_chain.py first")

    words_by_line = {}
    if lang == "en":
        words = common.load_json(project_dir / "words.json")
        if words is None:
            raise SystemExit(f"missing words.json in {project_dir} — run transcribe.py first")
        words_by_line = {
            entry.get("index"): entry.get("words") or []
            for entry in words.get("lines", [])
            if isinstance(entry, dict)
        }

    captions = []
    for entry in meta["lines"]:
        index = entry["index"]
        start = entry.get("start")
        duration = entry.get("duration")
        if start is None:
            raise SystemExit("audio_meta.json has no line start times — run build_timeline.py first")
        if duration is None:
            raise SystemExit(f"audio_meta.json line {index} has no duration — run audio_chain.py first")
        line_words = words_by_line.get(index) or []
        if lang == "en" and line_words:
            captions.extend(timed_captions(line_words, float(start)))
        else:
            if lang == "en":
                print(f"line {index:02d}: no ASR words — using proportional timing")
            captions.extend(
                proportional_captions(entry.get("text", ""), float(start), float(duration))
            )

    captions.sort(key=lambda c: (c["start"], c["end"]))
    out_path = project_dir / "captions.json"
    common.save_json(out_path, captions)
    print(f"wrote {out_path} ({len(captions)} caption groups)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
