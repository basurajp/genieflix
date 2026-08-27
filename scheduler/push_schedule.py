#!/usr/bin/env python3
"""Push the posting manifest through the scheduler's API — resumably.

DRY-RUN by default: prints exactly what would be uploaded and created and
touches nothing. --push executes. Every successful media upload and post
creation is appended to scheduler/ledger.jsonl, and anything already in the
ledger is skipped on later runs — after a partial failure, run the same
command again: it uploads nothing twice, creates nothing twice, and fills in
only what is missing. --wave-days N limits the run to the first N days of
the manifest (push a week, read the numbers, push the rest).

The endpoint paths and payload shapes live in the PostBridgeClient class
below — the single place to adjust if the vendor shifts its API.

Usage: push_schedule.py --manifest manifest.csv [--wave-days 7] [--push]
"""

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LEDGER_PATH = SCRIPT_DIR / "ledger.jsonl"
MANIFEST_COLUMNS = ["id", "video_path", "platform", "account", "caption", "scheduled_at"]


class PostBridgeClient:
    """Thin client for the Post Bridge HTTP API (stdlib urllib only).

    The endpoint paths and payload shapes here track Post Bridge's public
    API docs: POST /media/create-upload-url to reserve an upload, an HTTP
    PUT of the raw file bytes to the returned URL, then POST /posts to
    create the scheduled post. This class is the single place to adjust if
    the vendor shifts endpoints or fields; everything else in this script —
    guardrails, ledger, waves — is vendor-independent.
    """

    def __init__(self, api_base, api_key):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key

    def upload_video(self, path):
        """Upload one video file, return its media id."""
        path = Path(path)
        data = path.read_bytes()
        resp = self._request(
            "POST", f"{self.api_base}/media/create-upload-url",
            payload={"name": path.name, "mime_type": "video/mp4", "size_bytes": len(data)},
        )
        media_id = resp.get("media_id") or resp.get("id")
        upload_url = resp.get("upload_url") or resp.get("url")
        if not media_id or not upload_url:
            raise RuntimeError(f"unexpected create-upload-url response (keys: {sorted(resp)})")
        # The upload URL is pre-signed; no auth header on the PUT.
        self._request("PUT", upload_url, data=data, content_type="video/mp4",
                      auth=False, timeout=600)
        return media_id

    def create_post(self, account_id, media_id, caption, scheduled_at):
        """Create one scheduled post against uploaded media, return its post id."""
        resp = self._request("POST", f"{self.api_base}/posts", payload={
            "social_accounts": [account_id],
            "media": [media_id],
            "caption": caption,
            "scheduled_at": scheduled_at,
        })
        return resp.get("post_id") or resp.get("id")

    def _request(self, method, url, payload=None, data=None, content_type=None,
                 auth=True, timeout=120):
        headers = {}
        if auth:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif content_type:
            headers["Content-Type"] = content_type
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            detail = e.read(300).decode("utf-8", "replace").strip()
            raise RuntimeError(f"{method} {url} -> HTTP {e.code} {detail}") from None
        except urllib.error.URLError as e:
            raise RuntimeError(f"{method} {url} -> {e.reason}") from None
        if not body:
            return {}
        try:
            parsed = json.loads(body)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
    if not cfg.get("api_base"):
        die(f"{path}: missing required key 'api_base'")
    return cfg


def read_manifest(path):
    rows = []
    try:
        f = open(path, newline="", encoding="utf-8-sig")
    except OSError as e:
        die(f"cannot read manifest: {e}")
    with f:
        rdr = csv.DictReader(f)
        if rdr.fieldnames is None or not set(MANIFEST_COLUMNS).issubset(rdr.fieldnames):
            die(f"{path}: header must contain columns {','.join(MANIFEST_COLUMNS)}")
        for lineno, raw in enumerate(rdr, start=2):
            row = {c: (raw.get(c) or "").strip() for c in MANIFEST_COLUMNS}
            row["caption"] = raw.get("caption") or ""  # keep caption exactly as written
            if not any(v.strip() for v in row.values()):
                continue
            for c in ("id", "video_path", "platform", "account", "scheduled_at"):
                if not row[c]:
                    die(f"{path} line {lineno}: empty '{c}'")
            try:
                row["dt"] = datetime.fromisoformat(row["scheduled_at"])
            except ValueError:
                die(f"{path} line {lineno}: bad scheduled_at '{row['scheduled_at']}'")
            if row["dt"].tzinfo is None:
                die(f"{path} line {lineno}: scheduled_at must carry a UTC offset "
                    f"(e.g. 2026-09-01T09:30:00+05:30)")
            rows.append(row)
    if not rows:
        die(f"{path}: no data rows")
    seen = set()
    for row in rows:
        if row["id"] in seen:
            die(f"{path}: duplicate id '{row['id']}'")
        seen.add(row["id"])
    return rows


def read_ledger(path):
    """Return ({post id: entry}, {abs video path: media_id}) from the append-only ledger."""
    posts, media = {}, {}
    if not path.exists():
        return posts, media
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                print(f"warning: {path} line {lineno}: unreadable entry skipped", file=sys.stderr)
                continue
            if "id" in entry:
                posts[entry["id"]] = entry
            elif "media" in entry:
                media[entry["media"]] = entry.get("media_id")
    return posts, media


def append_ledger(path, entry):
    """Append one entry and fsync — the ledger must survive a mid-push crash."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def main():
    ap = argparse.ArgumentParser(
        description="Push a posting manifest through the scheduler's API. "
                    "Dry-run by default; --push executes; the ledger makes re-runs idempotent."
    )
    ap.add_argument("--manifest", required=True, help="manifest CSV from generate_manifest.py")
    ap.add_argument("--wave-days", type=int, metavar="N",
                    help="only rows scheduled within the first N days of the manifest")
    ap.add_argument("--push", action="store_true",
                    help="actually upload media and create posts (default: dry-run)")
    ap.add_argument("--config", help="config JSON (default: scheduler/config.json, else config.example.json)")
    args = ap.parse_args()
    if args.wave_days is not None and args.wave_days < 1:
        die("--wave-days must be >= 1")

    cfg = load_config(args.config)
    rows = read_manifest(args.manifest)
    rows.sort(key=lambda r: (r["dt"], r["id"]))

    first_day = rows[0]["dt"].date()
    if args.wave_days:
        wave = [r for r in rows if (r["dt"].date() - first_day).days < args.wave_days]
        beyond = len(rows) - len(wave)
    else:
        wave, beyond = rows, 0

    posts_done, media_done = read_ledger(LEDGER_PATH)

    todo, skipped = [], []
    for r in wave:
        (skipped if r["id"] in posts_done else todo).append(r)

    uploads = []
    seen = set(media_done)
    for r in todo:
        r["media_key"] = str(Path(r["video_path"]).resolve())
        if r["media_key"] not in seen:
            seen.add(r["media_key"])
            uploads.append(r["video_path"])

    missing = [p for p in uploads if not Path(p).exists()]
    if missing:
        die("video file(s) not found:\n  " + "\n  ".join(missing))

    print(f"manifest: {args.manifest} ({len(rows)} rows)")
    print(f"ledger:   {LEDGER_PATH} ({len(posts_done)} posts, {len(media_done)} media)")
    print(f"wave:     {wave[0]['dt'].date()} .. {wave[-1]['dt'].date()} — "
          f"{len(wave)} row(s) in window, {beyond} beyond it")

    if not args.push:
        print("\nDRY RUN — nothing will be uploaded or created. Re-run with --push to execute.\n")
        for p in uploads:
            print(f"  UPLOAD  {p}")
        for r in todo:
            print(f"  CREATE  {r['id']}  {r['platform']}/{r['account']}  {r['scheduled_at']}")
        for r in skipped:
            print(f"  SKIP    {r['id']}  (already in ledger)")
        print(f"\nplan: {len(uploads)} upload(s), {len(todo)} post(s) to create, "
              f"{len(skipped)} already in ledger")
        return

    env = cfg.get("api_key_env", "POSTBRIDGE_API_KEY")
    api_key = os.environ.get(env, "").strip()
    if not api_key:
        die(f"environment variable {env} is not set — export your API key, then re-run")
    client = PostBridgeClient(cfg["api_base"], api_key)

    media_ids = dict(media_done)
    failed_media = set()
    n_uploaded = n_created = 0
    failures = []
    for r in todo:
        key = r["media_key"]
        if key not in media_ids:
            if key in failed_media:
                failures.append((r["id"], "upload of its video failed earlier in this run"))
                continue
            print(f"upload  {r['video_path']}", flush=True)
            try:
                media_id = client.upload_video(r["video_path"])
            except Exception as e:
                print(f"  FAILED: {e}", file=sys.stderr)
                failed_media.add(key)
                failures.append((r["id"], str(e)))
                continue
            append_ledger(LEDGER_PATH, {"media": key, "media_id": media_id, "ts": now_iso()})
            media_ids[key] = media_id
            n_uploaded += 1
        print(f"create  {r['id']}  {r['platform']}/{r['account']}  {r['scheduled_at']}", flush=True)
        try:
            post_id = client.create_post(r["account"], media_ids[key], r["caption"],
                                         r["scheduled_at"])
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            failures.append((r["id"], str(e)))
            continue
        append_ledger(LEDGER_PATH, {"id": r["id"], "media_id": media_ids[key],
                                    "post_id": post_id, "ts": now_iso()})
        n_created += 1

    print(f"\ndone: {n_uploaded} uploaded, {n_created} created, "
          f"{len(skipped)} skipped (ledger), {len(failures)} failed")
    if failures:
        for fid, why in failures:
            print(f"  failed: {fid}: {why}", file=sys.stderr)
        print("re-run the same command once the API recovers — the ledger resumes "
              "where this run stopped", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
