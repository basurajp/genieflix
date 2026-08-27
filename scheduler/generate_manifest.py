#!/usr/bin/env python3
"""Generate the posting manifest from a topic matrix.

Fans every matrix row (topic,audience,slug,caption) out to every configured
account and schedules each post into fixed local time slots, honoring the
guardrails: max posts per day per account, one upload per day per YouTube
channel, and variants of the same topic at least min_days_between_same_topic
days apart on any one account. When a day's caps are hit, posts spill to the
next day. Deterministic: the same matrix and config always produce the same
manifest.

Usage: generate_manifest.py --matrix matrix.csv --videos-dir factory/ready-to-post --out manifest.csv
"""

import argparse
import csv
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# Spill search window. A schedule that cannot fit inside a year is a matrix
# problem, not a scheduling problem — refuse instead of stretching further.
HORIZON_DAYS = 366

MATRIX_COLUMNS = ["topic", "audience", "slug", "caption"]
MANIFEST_COLUMNS = ["id", "video_path", "platform", "account", "caption", "scheduled_at"]


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def load_config(arg_path):
    """scheduler/config.json if present, else config.example.json; --config overrides."""
    if arg_path:
        path = Path(arg_path)
    else:
        path = SCRIPT_DIR / "config.json"
        if not path.exists():
            path = SCRIPT_DIR / "config.example.json"
    if not path.exists():
        die(f"config not found: {path}")
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        die(f"cannot parse {path}: {e}")
    for key in ("timezone", "start_date", "platform_slots", "accounts"):
        if key not in cfg:
            die(f"{path}: missing required key '{key}'")
    return cfg


def parse_timezone(spec):
    m = re.fullmatch(r"([+-])(\d{2}):(\d{2})", str(spec).strip())
    if not m:
        die(f"config 'timezone' must be a UTC offset like '+05:30', got '{spec}'")
    sign = 1 if m.group(1) == "+" else -1
    return timezone(sign * timedelta(hours=int(m.group(2)), minutes=int(m.group(3))))


def parse_start_date(spec):
    try:
        return date.fromisoformat(str(spec))
    except ValueError:
        die(f"config 'start_date' must be YYYY-MM-DD, got '{spec}'")


def parse_slot(spec):
    m = re.fullmatch(r"(\d{2}):(\d{2})", str(spec).strip())
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        die(f"time slot must be 'HH:MM' 24h local time, got '{spec}'")
    return int(m.group(1)), int(m.group(2))


def read_matrix(path):
    rows = []
    try:
        f = open(path, newline="", encoding="utf-8-sig")
    except OSError as e:
        die(f"cannot read matrix: {e}")
    with f:
        rdr = csv.DictReader(f)
        if rdr.fieldnames is None or not set(MATRIX_COLUMNS).issubset(rdr.fieldnames):
            die(f"{path}: header must contain columns {','.join(MATRIX_COLUMNS)}")
        for lineno, raw in enumerate(rdr, start=2):
            row = {c: (raw.get(c) or "").strip() for c in MATRIX_COLUMNS}
            if not any(row.values()):
                continue
            for c in ("topic", "slug"):
                if not row[c]:
                    die(f"{path} line {lineno}: empty '{c}'")
            if not re.fullmatch(r"[A-Za-z0-9._-]+", row["slug"]):
                die(f"{path} line {lineno}: slug '{row['slug']}' — use letters, digits, dot, dash, underscore")
            rows.append(row)
    if not rows:
        die(f"{path}: no data rows")
    seen = set()
    for row in rows:
        if row["slug"] in seen:
            die(f"{path}: duplicate slug '{row['slug']}'")
        seen.add(row["slug"])
    return rows


def validate_accounts(accounts):
    if not isinstance(accounts, list) or not accounts:
        die("config 'accounts' must be a non-empty list")
    seen = set()
    for acct in accounts:
        if not isinstance(acct, dict) or not acct.get("id") or not acct.get("platform"):
            die("each account needs 'id' and 'platform'")
        if acct["id"] in seen:
            die(f"duplicate account id '{acct['id']}' in config")
        seen.add(acct["id"])


def schedule(rows, cfg, tz, start, videos_dir):
    """Place every (matrix row x account) on the earliest day that breaks no guardrail."""
    accounts = cfg["accounts"]
    max_per_day = int(cfg.get("max_posts_per_day_per_account", 2))
    max_yt_per_day = int(cfg.get("max_uploads_per_day_per_youtube_channel", 1))
    min_gap = int(cfg.get("min_days_between_same_topic", 14))
    slots_by_platform = {p: list(v) for p, v in cfg["platform_slots"].items()}
    for slots in slots_by_platform.values():
        for s in slots:
            parse_slot(s)

    day_counts = {a["id"]: {} for a in accounts}   # account -> {date: posts that day}
    topic_days = {a["id"]: {} for a in accounts}   # account -> {topic: [dates used]}
    posts = []
    for row in rows:
        for acct in accounts:
            aid, platform = acct["id"], acct["platform"]
            slots = slots_by_platform.get(platform)
            if not slots:
                die(f"no platform_slots configured for platform '{platform}' (account '{aid}')")
            cap = min(max_per_day, len(slots))
            if platform == "youtube":
                cap = min(cap, max_yt_per_day)
            if cap < 1:
                die(f"account '{aid}': effective daily cap is zero — check caps and slots in config")

            counts = day_counts[aid]
            used = topic_days[aid].setdefault(row["topic"], [])
            placed = None
            blocked_by_topic = False
            for offset in range(HORIZON_DAYS):
                d = start + timedelta(days=offset)
                n = counts.get(d, 0)
                if n >= cap:
                    continue
                if any(abs((d - u).days) < min_gap for u in used):
                    blocked_by_topic = True
                    continue
                placed = (d, slots[n])
                break
            if placed is None:
                if blocked_by_topic:
                    die(
                        f"cannot place topic '{row['topic']}' (slug '{row['slug']}') on account '{aid}' "
                        f"without violating the {min_gap}-day same-topic rule within {HORIZON_DAYS} days "
                        f"of {start} — {len(used)} other variant(s) of this topic are already scheduled "
                        f"there. Drop a variant of this topic from the matrix, or lower "
                        f"min_days_between_same_topic in the config."
                    )
                die(
                    f"cannot place slug '{row['slug']}' on account '{aid}': every slot within "
                    f"{HORIZON_DAYS} days of {start} is full. Shrink the matrix or add accounts/slots."
                )

            d, slot = placed
            counts[d] = counts.get(d, 0) + 1
            used.append(d)
            hh, mm = parse_slot(slot)
            when = datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz)
            posts.append({
                "id": f"{row['slug']}--{aid}--{when:%Y%m%d-%H%M}",
                "video_path": str(videos_dir / (row["slug"] + ".mp4")),
                "platform": platform,
                "account": aid,
                "caption": row["caption"],
                "scheduled_at": when.isoformat(),
            })
    return posts


def main():
    ap = argparse.ArgumentParser(
        description="Turn a topic matrix + a folder of videos into a guardrailed posting manifest."
    )
    ap.add_argument("--matrix", required=True, help="matrix CSV with columns topic,audience,slug,caption")
    ap.add_argument("--videos-dir", required=True, help="directory holding <slug>.mp4 for every matrix row")
    ap.add_argument("--out", required=True, help="manifest CSV to write")
    ap.add_argument("--config", help="config JSON (default: scheduler/config.json, else config.example.json)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    tz = parse_timezone(cfg["timezone"])
    start = parse_start_date(cfg["start_date"])
    validate_accounts(cfg["accounts"])

    rows = read_matrix(args.matrix)
    videos_dir = Path(args.videos_dir)
    missing = [str(videos_dir / (r["slug"] + ".mp4"))
               for r in rows if not (videos_dir / (r["slug"] + ".mp4")).exists()]
    if missing:
        die("video file missing for matrix row(s):\n  " + "\n  ".join(missing))

    posts = schedule(rows, cfg, tz, start, videos_dir)
    posts.sort(key=lambda p: (p["scheduled_at"], p["account"], p["id"]))

    out = Path(args.out)
    if out.parent != Path(""):
        out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(MANIFEST_COLUMNS)
        for p in posts:
            w.writerow([p[c] for c in MANIFEST_COLUMNS])

    days = sorted(p["scheduled_at"][:10] for p in posts)
    by_platform = {}
    for p in posts:
        by_platform[p["platform"]] = by_platform.get(p["platform"], 0) + 1
    counts = "  ".join(f"{k}={v}" for k, v in sorted(by_platform.items()))
    print(f"wrote {out}: {len(posts)} posts ({len(rows)} videos x {len(cfg['accounts'])} accounts)")
    print(f"  window: {days[0]} .. {days[-1]}   per-platform: {counts}")
    print("  review the CSV — it is the whole plan — then dry-run the push:")
    print(f"    python3 {SCRIPT_DIR / 'push_schedule.py'} --manifest {out} --wave-days 7")


if __name__ == "__main__":
    main()
