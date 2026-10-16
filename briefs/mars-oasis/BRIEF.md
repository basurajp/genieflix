# Mars Oasis: "Missiles… for gardening?"

Make-or-buy explainer reel for an MBA (operations management). Hook: Elon
Musk tried to buy Russian missiles to launch a greenhouse to Mars; that
question led to SpaceX. This folder is the plan; the project itself is built
in `factory/building/mars-oasis/` (gitignored) once assets are in.

## Start

```bash
git fetch origin claude/vibrant-brown-223314 && git checkout claude/vibrant-brown-223314
node factory/new.mjs mars-oasis "Missiles… for gardening?"
cp briefs/mars-oasis/lines.full.txt factory/building/mars-oasis/lines.txt      # or lines.short.txt
cp briefs/mars-oasis/project.json  factory/building/mars-oasis/project.json
mkdir -p factory/building/mars-oasis/assets/raw    # drop the assets below in here
```

## Open decisions

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | Visual route | A: drawn motion graphics (new `blueprint` style, no footage) · B: generated footage (Higgsfield, paid credits) · C: your footage/stock · or a mix | Mix: real or generated footage for the hook (plant, missile, Mars), blueprint graphics for the business half |
| 2 | Length | full (~77-85 s) · short (~30 s) · both | Both; the short cut is the one to test against skip rate |
| 3 | Ending | the question as a closing card · a comment keyword (e.g. "Comment MBA") | Keyword: every template's last beat is built for one, and it gives a measurable response |
| 4 | Brand | whose MBA, logo, colours, fonts, programme name | JAIN Online and EdNxt design-system skills are available if it is either |
| 5 | Voice | your cloned voice (run the voice phase locally) · a recorded VO file per line | Cloned voice through the factory |

## Fact notes (checked)

- About $50 million: Musk's 2003 Stanford talk calls the Delta II the lowest-cost
  US vehicle at "about $50 million"
  ([transcript](https://stvp.stanford.edu/wp-content/uploads/sites/3/2024/09/opportunities-in-space-mars-oasis-transcript.pdf)).
  His later essay says $60 million against about $10 million for a refurbished
  Russian ICBM without a third stage
  ([IEEE Spectrum](https://spectrum.ieee.org/amp/elon-musk-spacex-2650251626));
  Wikipedia cites $8 million per missile quoted by Kosmotras
  ([History of SpaceX](https://en.wikipedia.org/wiki/History_of_SpaceX)). Keep "about".
- Optional stronger money beat: "$50 million for an American rocket, roughly
  $10 million for a Russian missile." Two numbers side by side stop thumbs.
- The Russian trips failed, Mars Oasis was dropped, and a feasibility study of
  cheaper US launches followed; SpaceX was founded in 2002.

Rights: naming Musk in the story is commentary. Do not use his photos,
footage or likeness in this ad (it implies endorsement of an MBA programme),
and do not show the SpaceX logo; set "SpaceX" in the reel's own type.

## Beat sheet (full cut, matches lines.full.txt)

| Line | VO | Visual | On-screen text | Transition in | Asset file(s) |
|---|---|---|---|---|---|
| 1 | Elon Musk went shopping for Russian missiles… because he wanted to grow some plants. | Plant macro on frame 0, smash cut to missile on "missiles" | MISSILES… FOR GARDENING? | (opens) | `plant.mp4`, `missile.mp4` |
| 2 | The problem was the delivery address. | Shipping label being filled in | DELIVER TO: ______ | hard cut | drawn |
| 3 | Mars. | Mars reveal, slow push-in; 0.8 s silence before the word | MARS | dip to black | `mars.mp4` or `.jpg` |
| 4 | He wanted to send a tiny greenhouse there. The project was called Mars Oasis. | Tiny greenhouse on red soil | MARS OASIS · 2001 | dissolve | `greenhouse.jpg` |
| 5 | The idea was that a photograph of plants growing on another planet could get people excited about space again. | A polaroid of green on red, dropping into frame | | hard cut | drawn (uses `greenhouse.jpg`) |
| 6 | But the cheapest American launch option he found cost about fifty million dollars. | Rocket with a swinging price tag | ABOUT $50 MILLION | hard cut | `rocket.mp4` |
| 7 | That's a pretty expensive delivery charge for a gardening project. | Receipt: item "1 small greenhouse", delivery "$50,000,000" | | punch-in | drawn |
| 8 | So he went to Russia to explore buying retired missiles. | Missile footage | | hard cut | `missile.mp4` (second section) |
| 9 | Without the warheads, obviously. | Same shot, sticker slaps on | (NO WARHEADS) | none (sticker) | |
| 10 | That route didn't work out. | Missile shot desaturates, stamp | ✕ | | |
| 11 | So he investigated whether a team could build cheaper rockets themselves. | Missile footage turns into blueprint line drawings | | match cut / line-draw morph | drawn |
| 12 | That question helped lead to SpaceX. | Blueprint rocket completes and lifts | SPACEX · 2002 | | drawn |
| 13 | And there's a useful question hiding inside this story. | Blueprint zooms out to a question mark | | zoom transition | drawn |
| 14 | When something costs too much, how do you decide whether to buy it, build it yourself, or rethink the whole plan? | Three cards on "buy", "build", "rethink" | BUY IT. BUILD IT. RETHINK IT. | | drawn |
| 15 | That's a make-or-buy decision, something you explore in an MBA through operations management. | Label locks in | MAKE-OR-BUY · MBA · OPERATIONS MANAGEMENT | | brand logo |
| 16 | You break down the costs. Compare the capabilities you have with the ones you'd need. Account for the time, investment and risk. | Checklist ticking on each phrase | COSTS · CAPABILITIES · TIME, INVESTMENT, RISK | | drawn |
| 17 | Building it yourself might turn out to be a terrible idea. But now you have a way to evaluate it. | A balance scale tipping, then settling | | | drawn |
| 18 | Think about something your company pays for every month. | Software, packaging, delivery: three quick cards | | push | `software.jpg`, `packaging.jpg`, `delivery.jpg` |
| 19 | Do you know what makes it cost that much? | End card: the question, brand, CTA | (question or keyword) | dip to black | brand logo |

Two features the beat sheet needs that the pipeline lacks today (to build in
the next session): per-line on-screen text and word-anchored inserts (cut to a
second asset at a given word, line 1), and a per-line pause before the line
(line 3).

## Assets to upload

Put them in `factory/building/mars-oasis/assets/raw/` with these names. Clips
3-8 s, vertical if you have it (landscape is fine, it gets blur-padded or
cropped), no burned-in text or watermarks, rights cleared.

| File | What | Needed for |
|---|---|---|
| `plant.mp4` | Seedling or small plant, macro close-up, shallow focus | line 1 (frame zero) |
| `missile.mp4` | Missile on a launcher or in a silo; Soviet/Russian-looking if possible | lines 1, 8-10 |
| `mars.mp4` or `mars.jpg` | Mars from space, or the surface | line 3 |
| `greenhouse.jpg` | Small greenhouse or terrarium (on red soil is a bonus) | lines 4-5 |
| `rocket.mp4` | Any rocket on the pad or launching (not SpaceX-branded) | line 6 |
| `software.jpg`, `packaging.jpg`, `delivery.jpg` | Everyday business costs | line 18 |
| `logo.svg` or `logo.png` | Programme / institution logo, transparent | lines 15, 19 |
| `brand.txt` | Colours (hex), fonts, programme name, CTA wording | everything |
| `music.mp3` | A track you have the rights to (optional) | bed |
| `voice-sample.wav` | 1-2 min of clean speech for the clone (or recorded VO per line) | voice |

Route A needs only the logo, brand.txt and the voice; everything marked
"drawn" is built in code.
