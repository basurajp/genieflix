# Mars Oasis: "Missiles… for gardening?"

Make-or-buy story reel for a story page: interesting stories that make people
think "I could do that with an MBA". Hook: Elon Musk tried to buy Russian
missiles to launch a greenhouse to Mars; that question helped lead to SpaceX.
This folder is the plan; each cut is built in `factory/building/<slug>/`
(gitignored) on the machine that has the assets and the voice takes.

| File | What |
|---|---|
| `lines.full.txt`, `project.json` | full cut, 20 lines (~80-86 s after the 1.1x pass) |
| `lines.short.txt`, `project.short.json` | short cut, 8 lines (~36-38 s) |
| `vo.full.json`, `vo.short.json` | the voice takes, one URL per line, for `pipeline/fetch_vo.py` |

## Decisions (settled 2026-10-16)

| # | Decision | Chosen |
|---|---|---|
| 1 | Visual route | Mix, in the **`papercut`** style (Vox-style collage): footage for the story beats from your asset pool, photo cut-outs and news/research clippings with highlighter animations, drawn paper props for the business half. `blueprint` (engineering drawing) is built too: set `"style": "blueprint"` to switch. |
| 2 | Length | Both cuts. |
| 3 | Ending | A follow CTA, voiced: "We share stories that inspire. For your weekly dose of quirky stories, follow now!" End card: FOLLOW NOW. |
| 4 | Brand | None. A story page; no institution, logo or handle on screen. |
| 5 | Voice | Higgsfield preset voice **Cillian**, ElevenLabs engine (picked from four auditions; the "Jagdish" voice element was not used). Every line is generated: `vo.*.json`. |

## Fact notes (checked)

- About $50 million: Musk's 2003 Stanford talk calls the Delta II the lowest-cost
  US vehicle at "about $50 million"
  ([transcript](https://stvp.stanford.edu/wp-content/uploads/sites/3/2024/09/opportunities-in-space-mars-oasis-transcript.pdf)).
  His later essay says $60 million against about $10 million for a refurbished
  Russian ICBM without a third stage
  ([IEEE Spectrum](https://spectrum.ieee.org/amp/elon-musk-spacex-2650251626));
  Wikipedia cites $8 million per missile quoted by Kosmotras
  ([History of SpaceX](https://en.wikipedia.org/wiki/History_of_SpaceX)). Keep "about".
- Mars Oasis was the 2001 plan; the Russia trips were October 2001 and February
  2002 per Wikipedia ([History of SpaceX](https://en.wikipedia.org/wiki/History_of_SpaceX)),
  while Musk has said he went three times
  ([Fast Company](https://www.fastcompany.com/3006829/spacex-founder-elon-musk-considered)).
  The reel never states a trip count. SpaceX was founded in 2002.
- The note cards that stand in for missing clippings use the reel's own words
  with a source line ("Source: Musk, Stanford talk, 2003"; "Source: History of
  SpaceX, Wikipedia"). Only put a quote on screen from a screenshot of the
  real document.

Rights, said once: this page funnels to MBA/MCA programmes, so it is
commercial. A recognisable photo of Musk carries right-of-publicity and
implied-endorsement risk, and press photos and article screenshots are usually
copyrighted. Use images you have a licence for (or CC-BY with credit), keep
clippings to short excerpts used as commentary, and never imply he endorses
anything. No SpaceX logo; "SpaceX" is set in the reel's own type.

## Beats (full cut; `project.json` holds the exact spec)

| Line | VO (short) | Visual | On-screen | In |
|---|---|---|---|---|
| 1 | …shopping for Russian missiles… | plant on frame 0; cut-out of Musk slides in on "Elon"; smash cut to the missile on "missiles" | MISSILES… FOR GARDENING? (first word turns red on the cut) | opens |
| 2 | delivery address | drawn shipping label, address field blinking empty | (label: DELIVER TO:) | paper sheet push |
| 3 | Mars. | Mars still; 0.8 s of silence first, dip to black | MARS | dip |
| 4 | tiny greenhouse… Mars Oasis | greenhouse still | MARS OASIS · 2001 | dissolve |
| 5 | a photograph of plants… | polaroid of the greenhouse photo dropping in | | sheet push |
| 6 | about fifty million dollars | rocket footage + cost clipping, highlighter on "fifty" | ABOUT $50 MILLION | cut |
| 7 | expensive delivery charge | receipt prints; delivery row lights up, total circled | | punch-in |
| 8 | went to Russia… | missile footage + Russia clipping, highlighter on "Russia" | | cut |
| 9 | Without the warheads | same shot rolling, sticker slaps on | (NO WARHEADS) | none |
| 10 | didn't work out | same shot drains to grey, stamp | NO DEAL | none |
| 11 | build cheaper rockets | the shot gives way to a line-drawn rocket | | none (morph) |
| 12 | helped lead to SpaceX | rocket lifts off on "SpaceX" | SPACEX · 2002 | none |
| 13 | a useful question | construction circles, a drawn question mark | | zoom |
| 14 | buy it, build it, or rethink | three cards, each on its word | BUY IT. BUILD IT. RETHINK IT. | sheet push |
| 15 | make-or-buy… MBA… operations | three labels lock in on their words | MAKE-OR-BUY · MBA · OPERATIONS MANAGEMENT | sheet push |
| 16 | costs, capabilities, time | checklist ticks on each phrase | | sheet push |
| 17 | terrible idea… evaluate it | balance scale tips on "terrible", settles on "evaluate" | | sheet push |
| 18 | your company pays for every month | software, packaging, delivery tiles on the words | | push |
| 19 | what makes it cost that much? | the question again | WHAT MAKES IT COST THAT MUCH? | sheet push |
| 20 | follow now! | taped CTA card, marker underline and arrow | FOLLOW NOW | dip |

Short cut: lines 1-3 as above; 4 rocket + price tag, greenhouse insert on
"tiny"; 5 missile + Russia clipping, sticker on "warheads"; 6 same shot greys
out, stamp on "failed", rocket drawn over it on "build" and launched on
"SpaceX"; 7 buy/build/rethink cards then MAKE-OR-BUY · MBA labels; 8 CTA.

## Assets to stage from your pool

| File (rename to this) | Goes to | Used on |
|---|---|---|
| `plant.mp4` | `footage.py --line 1` | 1 (frame zero) |
| `missile.mp4` | `footage.py --line 1 --as line01-missile`, and `--line 8 --start <s>` (full) / `--line 5` (short) | 1, 8-11 / 5-6 |
| `mars.mp4` or `mars.jpg` | `footage.py --line 3` | 3 |
| `greenhouse.jpg` | `footage.py --line 4` (full), `--line 4 --as line04-greenhouse` (short) | 4-5 / 4 |
| `rocket.mp4` | `footage.py --line 6` (full), `--line 4` (short) | 6 / 4 |
| `musk.png` (transparent cut-out) | copy to `assets/cutouts/musk.png` | 1 |
| `cost.png` (screenshot: the $50M line) | copy to `assets/clippings/cost.png` | 6 |
| `russia.png` (screenshot: a story on the Russia trips) | copy to `assets/clippings/russia.png` | 8 / 5 |

The missile shot in the full cut rolls under lines 8-11 (about 14 s); a
shorter clip holds its last frame, so use the longest take you have. Clippings
default to one highlighter box at `[4, 40, 92, 18]` (x, y, w, h in percent of
the image): edit `highlights` (and add a `circle`) in the beat to sit on the
real line. Anything not staged is skipped or replaced by a drawn or typed
version, so the reel builds either way.

## Run it on your PC (Windows PowerShell; `python` = Python 3)

```powershell
git fetch origin claude/vibrant-brown-223314; git checkout claude/vibrant-brown-223314; git pull

# full cut (repeat with mars-oasis-short, lines.short.txt, project.short.json, vo.short.json)
node factory/new.mjs mars-oasis "Missiles… for gardening?" --style papercut
copy briefs\mars-oasis\lines.full.txt factory\building\mars-oasis\lines.txt
copy briefs\mars-oasis\project.json   factory\building\mars-oasis\project.json
python pipeline\fetch_vo.py   --project factory\building\mars-oasis --manifest briefs\mars-oasis\vo.full.json
python pipeline\make_reel.py  --project factory\building\mars-oasis --phase voice

$P = "factory\building\mars-oasis"; $S = "C:\path\to\your\pool"
python pipeline\footage.py --project $P --line 1 --src $S\plant.mp4
python pipeline\footage.py --project $P --line 1 --src $S\missile.mp4 --as line01-missile
python pipeline\footage.py --project $P --line 3 --src $S\mars.jpg
python pipeline\footage.py --project $P --line 4 --src $S\greenhouse.jpg
python pipeline\footage.py --project $P --line 6 --src $S\rocket.mp4
python pipeline\footage.py --project $P --line 8 --src $S\missile.mp4 --start 2
mkdir $P\assets\cutouts, $P\assets\clippings
copy $S\musk.png $P\assets\cutouts\;  copy $S\cost.png $P\assets\clippings\;  copy $S\russia.png $P\assets\clippings\
python pipeline\build_timeline.py --project $P
python pipeline\build_index.py    --project $P
python pipeline\make_reel.py      --project $P --phase render     # QA gates, 1.1x, -> factory\ready-to-post\
python decode\decode_reel.py factory\ready-to-post\mars-oasis.mp4  # check the cuts land where the table says
```

If a voice URL stops working, download that take from the Higgsfield gallery
and save it as `vo\lineNN.mp3`; `voice.py` picks it up the same way.

## QA in the cloud session (stand-ins)

The real footage, cut-outs, clippings and voice takes could not reach the cloud
session (the assets are on your PC; the network policy blocks the Higgsfield
CDN), so both cuts were verified with stand-ins: labelled colour clips named
like the assets above, a stand-in cut-out and clipping, and noise-shaped voice
files cut to each real take's length.
