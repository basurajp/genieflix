# Scheduler — a month of posting in one push

Three hundred finished reels in a folder earn exactly zero views. This
directory turns posting into data plus a script: a folder of finished videos
becomes a month of scheduled posts across every account you run — capped,
spaced, aimed at strangers, pushed in waves.

Two scripts, one CSV between them:

1. `generate_manifest.py` — turns a topic matrix and a videos folder into
   `manifest.csv`, one row per post, with every guardrail applied.
2. `push_schedule.py` — reads the manifest and pushes it through the
   scheduler's API (Post Bridge), resumably and idempotently.

**The manifest is the product.** Every decision you would otherwise make
hundreds of separate times — spacing, captions, slots — is decided once, as
rules, and you review the resulting CSV before anything touches the internet.

## Setup

1. Connect your accounts in the Post Bridge UI. The UI is only for that —
   everything else happens from these scripts.
2. `cp scheduler/config.example.json scheduler/config.json` and edit it:
   your accounts (each `id` is the identifier your scheduler uses for that
   connected account), local time slots per platform, timezone offset, and
   the date the schedule starts. `config.json` is local and gitignored.
3. `export POSTBRIDGE_API_KEY=...` (the env var name is configurable via
   `api_key_env`).

## Workflow

```bash
# 1. Write the matrix: one row per video (topic,audience,slug,caption).
#    See matrix.example.csv. <slug>.mp4 must exist in the videos dir.

# 2. Generate the manifest
python3 scheduler/generate_manifest.py \
  --matrix scheduler/matrix.csv \
  --videos-dir factory/ready-to-post \
  --out scheduler/manifest.csv

# 3. Review manifest.csv. It is the whole plan — read it before pushing.

# 4. Dry-run (the default): shows exactly what would be uploaded and created
python3 scheduler/push_schedule.py --manifest scheduler/manifest.csv --wave-days 7

# 5. Push the first wave
python3 scheduler/push_schedule.py --manifest scheduler/manifest.csv --wave-days 7 --push

# 6. Read the numbers for a week, adjust, then push the rest
python3 scheduler/push_schedule.py --manifest scheduler/manifest.csv --push
```

The last command re-reads the whole manifest; everything already pushed in
wave one is in the ledger and is skipped automatically.

## Guardrails — how not to torch your accounts

Volume without limits reads as spam, to platforms and to people. The
generator bakes these rules in, spilling posts to later days when a cap is
hit, so the manifest cannot violate them:

- **Max 2 posts per day per account** (`max_posts_per_day_per_account`).
- **1 upload per day per YouTube channel**
  (`max_uploads_per_day_per_youtube_channel`).
- **Same topic at least 14 days apart** on any one account
  (`min_days_between_same_topic`) — the vertical and horizontal variants of
  a topic never read as a rerun to the same audience.
- **Fixed local time slots per platform** (`platform_slots`), morning and
  evening.

If a topic has so many variants that it cannot be placed without breaking
the 14-day rule, generation refuses with a message naming the topic and
account. Fix the matrix (drop a variant); don't weaken the rule.

## Protect your followers from your factory

Factory videos are coverage — search-and-discovery content for strangers,
not treats for people who already follow you. A follower who sees five
templated reels in a row will feel the template. So:

- On **Instagram**, post the batch as **trial reels** (enable trial reels on
  the account). Instagram shows those only to non-followers: strangers
  searching the topic find the video, your followers' feeds stay curated.
  Winners graduate to the main grid.
- On **YouTube**, point the bulk at a dedicated tutorials channel, not your
  main one.

## Push in waves, not all at once

Don't schedule the month blind. Push the first seven days
(`--wave-days 7 --push`), read the analytics — views, skip-rate proxies,
whether trial reels are catching — then push the remaining weeks with
adjustments. If wave one stinks, total exposure was a week of trial reels
shown to strangers: cheap experiment, capped downside.

## The ledger — boring, resumable, idempotent

APIs fail mid-push. Every successful media upload and post creation is
appended as one JSON line to `scheduler/ledger.jsonl`. On every run,
anything already in the ledger is skipped: each video is uploaded exactly
once (however many posts reuse it), each post is created exactly once, and
after a partial failure you re-run the exact same command — it fills in only
what is missing. The ledger is append-only: never edit it, and delete it
only if you truly want to re-upload and re-create everything.

## Post Bridge specifics

`push_schedule.py` talks to the API with Python's stdlib `urllib` — no
dependencies. The endpoint paths and payload shapes track Post Bridge's
public API docs (create an upload URL, PUT the file bytes, create the post)
and are centralized in the `PostBridgeClient` class at the top of that file:
if the vendor shifts its API, that class is the single place to adjust.
Everything else — guardrails, ledger, waves — is vendor-independent.

## File formats

`matrix.csv` (input): `topic,audience,slug,caption`. One row per video;
`<slug>.mp4` must exist in `--videos-dir`. Rows sharing a `topic` are
variants and get spaced by the 14-day rule.

`manifest.csv` (generated): `id,video_path,platform,account,caption,scheduled_at`

| column         | meaning                                                        |
| -------------- | -------------------------------------------------------------- |
| `id`           | `<slug>--<account>--<YYYYMMDD-HHMM>` — the ledger key          |
| `video_path`   | path to the video file to upload                               |
| `platform`     | `instagram`, `x`, `youtube`, …                                 |
| `account`      | account id from the config                                     |
| `caption`      | post caption, verbatim from the matrix                         |
| `scheduled_at` | ISO 8601 local time with the configured offset                 |

`ledger.jsonl` (generated): one JSON object per line —
`{"media": ..., "media_id": ..., "ts": ...}` per uploaded file and
`{"id": ..., "media_id": ..., "post_id": ..., "ts": ...}` per created post.

## Config reference

| key                                       | meaning                                          |
| ----------------------------------------- | ------------------------------------------------ |
| `api_base`                                | scheduler API root                               |
| `api_key_env`                             | env var holding the API key                      |
| `timezone`                                | UTC offset for all slots, e.g. `+05:30`          |
| `start_date`                              | first day of the schedule, `YYYY-MM-DD`          |
| `platform_slots`                          | local `HH:MM` posting slots per platform         |
| `accounts`                                | `{id, platform}` per connected account           |
| `max_posts_per_day_per_account`           | daily cap per account                            |
| `max_uploads_per_day_per_youtube_channel` | daily cap for YouTube channels                   |
| `min_days_between_same_topic`             | spacing between variants of one topic            |
