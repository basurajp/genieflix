# The Video Factory

A folder that renders whatever you drop into it, with a live dashboard so you
can watch it work. No database, no framework — one Node script and seven
folders.

## Quick start

```bash
node factory/new.mjs my-first-reel "My first reel"   # capture the idea
# ... write the five lines in building/my-first-reel/lines.txt,
#     drop slides into building/my-first-reel/assets/slides/ ...
node factory/enqueue.mjs my-first-reel               # hand it to the factory
./factory/start.command                              # mac (Windows: factory\start.bat)
```

Then open **http://localhost:4300/dashboard.html** and watch the card move
left to right. Finished MP4s land in `factory/output/` and are copied to the
ready-to-post folder (`ready_to_post_dir` in `pipeline/config.json`).

## Folders are the state machine

```
building/  →  queue/  →  work/  →  done/
                                →  failed/
```

- `building/<slug>/` — the project is being created (by you, or by a script).
- `queue/<slug>/` — ready to render; the runner picks it up within 3 seconds.
- `work/<slug>/` — being processed right now (voicing, then rendering).
- `done/<slug>/` / `failed/<slug>/` — terminal states, full project preserved.
- `output/` — one flat `<slug>.mp4` per finished job (what the dashboard streams).
- `ready-to-post/` — a second copy of every finished MP4, for the scheduler.

Because it is all folders, everything is debuggable with your file manager:
want to re-run a failed job? Drag `failed/<slug>` back into `queue/`. Want to
see what's stuck? Open the folder. Nothing can reach a corrupt half-state you
can't see.

## The one-writer rule

Once a job is in `queue/` or beyond, **the runner is the only process that
writes its `job.json`**. The creator (you, or a script filling `building/`)
owns the manifest only while the job is in `building/`; `enqueue.mjs` makes
one final write (`status: "queued"`) and hands the folder over. Clean handoff,
no two processes editing the same state, no mystery corruption. If you extend
the factory, keep this rule.

`job.json` shape:

```json
{"slug": "...", "title": "...", "status": "building", "created": "ISO8601",
 "updated": "ISO8601", "error": null, "output": null, "attempts": 0}
```

`status` is one of `building | queued | voicing | rendering | done | failed |
cancelled`. All timestamps are ISO 8601 UTC. `error` holds the last ~40 lines
of pipeline output when a job fails.

## What the runner does

`runner.mjs` scans `queue/` every 3 seconds and, per job:

1. moves `queue/<slug>` → `work/<slug>` and sets `status: "voicing"`;
2. runs `make_reel.py --phase voice` — **one voice job at a time** (the local
   voice model wants the machine to itself);
3. sets `status: "rendering"` and runs `make_reel.py --phase render` — **three
   renders at once** (what a laptop realistically sustains);
4. on success: copies `final/<slug>.mp4` to `output/` and the ready-to-post
   dir, sets `status: "done"`, moves the project to `done/`;
5. on failure: captures the error tail into `job.json`, moves to `failed/`.

Crash safety: anything found in `work/` at startup was interrupted mid-run, so
the runner moves it back to `queue/` with a note and it simply runs again.
Generated files are disposable; the plan (`lines.txt`, `project.json`,
`BRIEF.md`, slides) survives every re-run.

Environment knobs:

| Variable | Default | Meaning |
| --- | --- | --- |
| `PORT` | `4300` | dashboard / API port |
| `FACTORY_RENDER_CONCURRENCY` | `3` | parallel render jobs (voice stays at 1) |

## The dashboard

One self-contained HTML page, served by the runner. Cards flow through
Building → Queued → Voicing → Rendering → Done (or Failed), with live timers
on active jobs, inline video previews on finished ones, the error tail on
failed ones, and Retry / Cancel / Pause buttons. It polls the API every 2
seconds and shows a clear "runner offline" state when the runner isn't up.

## HTTP API

| Route | Method | Does |
| --- | --- | --- |
| `/` | GET | redirects to `/dashboard.html` |
| `/dashboard.html` | GET | the dashboard |
| `/api/jobs` | GET | every job across all state folders: `{slug, title, status, created, updated, error, output, attempts, folder, elapsed}` (`elapsed` = seconds since the last status change) |
| `/api/state` | GET | `{paused, active: {voicing, rendering}}` |
| `/api/pause` | POST | toggle pause (running jobs finish; nothing new starts) |
| `/api/retry/<slug>` | POST | from `failed/` or `done/`: reset to queued, `attempts` +1 |
| `/api/cancel/<slug>` | POST | kill the job's child process if running; job ends up in `failed/` with `status: "cancelled"` |
| `/output/<file>` | GET | streams a finished MP4, with HTTP Range support so `<video>` seeking works |

## Files

- `runner.mjs` — the worker + web server (Node ≥ 22, zero dependencies)
- `new.mjs` — `node factory/new.mjs <slug> [title...]` → `building/<slug>/` from `template/`
- `enqueue.mjs` — `node factory/enqueue.mjs <slug>` → `queue/<slug>` (refuses if `lines.txt` is missing or empty)
- `dashboard.html` — the UI (no external assets)
- `start.command` / `start.bat` — double-clickable launchers
