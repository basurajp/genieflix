#!/usr/bin/env python3
"""Compose the Deeksharambh 2026 post-event recap: a 40 s kinetic-type motion reel.

Usage: motion/deeksharambh-2026/compose.py --project motion/deeksharambh-2026/project
       (run prep_assets.py and make_music.py into the same project first)

No narration: the type is the voice and the 120 BPM bed is the clock, so every
entrance sits on a beat (0.5 s) and every scene change on a downbeat.

  S1 0-6    hook        11,500+ counter, ONE DAY. ONE SCREEN., zoom through the screen
  S2 6-12   scale wall  the student-card scroll, close-up then a tilted pull-back
  S3 12-16  the event   logo reveal + glint, date and time pills, 5 HOURS. LIVE
  S4 16-24  contrast    NO HOSTEL MOVE / TRAIN TICKET / GETTING LOST, struck through;
                        JUST A LAPTOP + A LINK (the poster on the laptop screen)
  S5 24-28  meaning     दीक्षा (initiation) + आरंभ (beginning) = दीक्षारंभ
  S6 28-36  welcome     WELCOME TO JAIN ONLINE, 2026 BATCH., CTA: tag a classmate
  S7 36-40  end card    logo, poster line, JAIN Online + CDOE lockups

Renderer rules honored: full document, every media element has an id, scene
containers are timed clips, cued fromTo tweens use immediateRender: false,
videos are only moved with transforms/opacity, text stays out of the bottom
420 px and right 120 px.
"""
import argparse
import html
import pathlib
import random

ap = argparse.ArgumentParser(description="Compose the Deeksharambh 2026 recap into index.html.")
ap.add_argument("--project", required=True)
project = pathlib.Path(ap.parse_args().project).expanduser().resolve()

TOTAL = 40.0
for need in ("assets/img/deeksharambh.png", "assets/img/poster.png", "assets/img/jain-online.png",
             "assets/img/jain-cdoe.png", "assets/footage/scroll-a.mp4", "assets/audio/music.wav"):
    if not (project / need).is_file():
        raise SystemExit(f"missing {need} — run prep_assets.py / make_music.py into {project} first")


def chars(text, cls="ch"):
    return "".join(
        f'<span class="{cls}">{"&nbsp;" if c == " " else html.escape(c)}</span>' for c in text
    )


def words(text, cls="w"):
    return " ".join(f'<span class="{cls}">{html.escape(w)}</span>' for w in text.split())


FONTS = "\n".join(
    f"@font-face {{ font-family: '{fam}'; font-weight: {w}; font-style: {st}; "
    f"src: url('assets/fonts/{file}.ttf'); }}"
    for fam, w, st, file in [
        ("Montserrat", 400, "normal", "Montserrat-400"), ("Montserrat", 500, "normal", "Montserrat-500"),
        ("Montserrat", 700, "normal", "Montserrat-700"), ("Montserrat", 800, "normal", "Montserrat-800"),
        ("Montserrat", 900, "normal", "Montserrat-900"), ("Montserrat", 800, "italic", "Montserrat-800i"),
        ("Montserrat", 900, "italic", "Montserrat-900i"),
        ("Noto Sans Devanagari", 600, "normal", "NotoSansDevanagari-600"),
        ("Noto Sans Devanagari", 800, "normal", "NotoSansDevanagari-800"),
    ]
)

rng = random.Random(3)
particles = []
for i in range(40):
    x, y, r = rng.uniform(20, 1060), rng.uniform(200, 2300), rng.choice([2, 3, 3, 4, 5, 6])
    o = rng.uniform(0.25, 0.8)
    particles.append(
        f'<div class="pt" id="pt{i}" data-rise="{rng.uniform(500, 1300):.0f}" '
        f'style="left:{x:.0f}px; top:{y:.0f}px; width:{r}px; height:{r}px; opacity:{o:.2f};"></div>'
    )

GHOST = " · ".join(["11,500+"] * 6)

ICON_CAL = """<svg width="46" height="46" viewBox="0 0 24 24" fill="none" stroke="#2fe0c6" stroke-width="1.8"
  stroke-linecap="round"><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/>
  <path d="M7.5 14h1M11.5 14h1M15.5 14h1M7.5 17.5h1M11.5 17.5h1"/></svg>"""
ICON_CLOCK = """<svg width="46" height="46" viewBox="0 0 24 24" fill="none" stroke="#2fe0c6" stroke-width="1.8"
  stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>"""
ICON_LINK = """<svg width="96" height="96" viewBox="0 0 24 24" fill="none" stroke="#2fe0c6" stroke-width="2.2"
  stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/>
  <path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>"""


def nrow(i, top, word):
    return f"""
    <div class="nrow" id="n{i}" style="top:{top}px;">
      <div class="nolab">NO</div>
      <div class="nwrap"><span class="nword" id="nw{i}">{html.escape(word)}</span><div class="strike" id="st{i}"></div></div>
    </div>"""


page = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Deeksharambh 2026 recap</title></head>
<body>
<div id="stage" data-composition-id="reel" data-start="0" data-duration="{TOTAL:.3f}"
     data-width="1080" data-height="1920" data-fps="30">
  <style>
{FONTS}
    :root {{ --navy0: #030a2e; --navy1: #071a6b; --royal: #1640d6; --electric: #3b7bff; --teal: #2fe0c6; }}
    #stage {{ background: var(--navy0); font-family: 'Montserrat', sans-serif; color: #fff; overflow: hidden;
      width: 1080px; height: 1920px; position: relative; }}
    .abs, .scene, .row, .nrow {{ position: absolute; }}
    .scene {{ left: 0; top: 0; width: 1080px; height: 1920px; overflow: hidden; }}
    .full {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; }}
    .row {{ left: 60px; width: 900px; text-align: center; line-height: 1; white-space: nowrap; }}
    .ch, .w {{ display: inline-block; will-change: transform, opacity; }}
    .teal {{ color: var(--teal); }}
    .it {{ font-style: italic; }}

    /* background */
    #bg-base {{ background: linear-gradient(180deg, #030a2e 0%, #061565 48%, #0b2aa6 100%); }}
    .orb {{ position: absolute; width: 1100px; height: 1100px; border-radius: 50%;
      background: radial-gradient(circle, rgba(59,123,255,0.55) 0%, rgba(59,123,255,0) 65%); }}
    #orb2 {{ background: radial-gradient(circle, rgba(47,224,198,0.22) 0%, rgba(47,224,198,0) 62%); }}
    #pulse {{ background: radial-gradient(ellipse at 50% 55%, rgba(120,170,255,0.55) 0%, rgba(120,170,255,0) 70%); opacity: 0; }}
    .pt {{ position: absolute; border-radius: 50%; background: #bcd3ff; box-shadow: 0 0 10px #7fa8ff; }}
    #vignette {{ background: radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,10,0.55) 100%); }}
    #flash {{ background: #eaf6ff; opacity: 0; }}

    /* S1 */
    .ghost {{ position: absolute; left: 0; white-space: nowrap; font-size: 210px; font-weight: 900;
      color: transparent; -webkit-text-stroke: 2px rgba(150,190,255,0.16); letter-spacing: -4px; opacity: 0; }}
    #s1-kicker {{ top: 600px; font-size: 34px; font-weight: 800; letter-spacing: 12px; color: var(--teal); }}
    #s1-numwrap {{ top: 660px; font-size: 176px; font-weight: 900; letter-spacing: -5px; opacity: 0;
      text-shadow: 0 0 60px rgba(80,140,255,0.55); }}
    #s1-plus {{ color: var(--teal); display: inline-block; }}
    #s1-sub {{ top: 870px; font-size: 64px; font-weight: 800; letter-spacing: 10px; }}
    #s1-day, #s1-screen {{ font-size: 124px; font-weight: 900; letter-spacing: -3px; }}
    #s1-day {{ top: 820px; }}
    #s1-screen {{ top: 1000px; }}
    #s1-zoom {{ transform-origin: 510px 1062px; }}

    /* S2 */
    #wall-cam {{ perspective: 1900px; }}
    #wall-plane {{ position: absolute; left: -564px; top: 276px; width: 2208px; height: 1368px; }}
    .strip {{ position: absolute; top: 0; width: 720px; height: 1368px; border-radius: 28px; overflow: hidden;
      box-shadow: 0 0 0 3px rgba(150,190,255,0.18), 0 40px 90px rgba(0,0,20,0.6); background: #000; }}
    .strip video {{ width: 720px; height: 1368px; display: block; }}
    #s2-shade {{ background: linear-gradient(180deg, rgba(3,10,46,0.94) 0%, rgba(3,10,46,0.8) 30%, rgba(3,10,46,0) 52%,
      rgba(3,10,46,0) 76%, rgba(3,10,46,0.75) 100%); }}
    #s2-a {{ top: 290px; font-size: 54px; font-weight: 800; letter-spacing: 8px; }}
    #s2-b {{ top: 370px; font-size: 180px; font-weight: 900; letter-spacing: -5px;
      text-shadow: 0 0 50px rgba(80,140,255,0.6); }}
    #s2-c {{ top: 575px; font-size: 104px; font-weight: 900; font-style: italic; color: var(--teal); }}
    #s2-d {{ top: 695px; font-size: 104px; font-weight: 900; }}
    .chip {{ display: inline-block; padding: 18px 34px; border-radius: 999px; background: rgba(3,10,46,0.82);
      border: 2px solid rgba(47,224,198,0.7); font-size: 44px; font-weight: 800; letter-spacing: 6px; }}
    #s2-e {{ top: 300px; }}
    #s2-f {{ top: 1430px; font-size: 50px; font-weight: 800; letter-spacing: 4px; }}

    /* S3 */
    #s3-logo, #s3-glint {{ position: absolute; left: 80px; top: 460px; width: 860px; height: 286px; }}
    #s3-glint {{ -webkit-mask-image: url('assets/img/deeksharambh.png'); -webkit-mask-size: 860px 286px;
      mask-image: url('assets/img/deeksharambh.png'); mask-size: 860px 286px;
      background: linear-gradient(105deg, rgba(255,255,255,0) 40%, rgba(255,255,255,0.95) 50%, rgba(255,255,255,0) 60%);
      background-size: 300% 100%; background-position: 120% 0; }}
    .pill {{ display: inline-flex; align-items: center; gap: 20px; padding: 20px 38px; border-radius: 28px;
      background: rgba(255,255,255,0.07); border: 2px solid rgba(120,170,255,0.45);
      box-shadow: inset 0 0 30px rgba(80,140,255,0.18); font-size: 46px; font-weight: 800; }}
    #s3-p1 {{ top: 840px; }}
    #s3-p2 {{ top: 970px; }}
    #s3-hours {{ top: 1130px; font-size: 130px; font-weight: 900; letter-spacing: -2px; }}
    #s3-live {{ top: 1310px; }}
    .live {{ display: inline-flex; align-items: center; gap: 18px; padding: 14px 34px; border-radius: 999px;
      background: #ff2d55; font-size: 46px; font-weight: 900; letter-spacing: 8px; }}
    #s3-dot {{ width: 22px; height: 22px; border-radius: 50%; background: #fff; display: inline-block; }}

    /* S4 */
    .nrow {{ left: 60px; width: 900px; text-align: center; }}
    .nolab {{ font-size: 50px; font-weight: 900; letter-spacing: 14px; color: var(--teal); margin-bottom: 8px; }}
    .nwrap {{ position: relative; display: inline-block; }}
    .nword {{ font-size: 92px; font-weight: 900; font-style: italic; line-height: 1.05; white-space: nowrap; }}
    .strike {{ position: absolute; left: -16px; right: -16px; top: 50%; height: 14px; margin-top: -7px;
      background: var(--teal); border-radius: 7px; transform: scaleX(0); transform-origin: 0 50%;
      box-shadow: 0 0 24px rgba(47,224,198,0.8); }}
    #laptop {{ position: absolute; left: 230px; top: 420px; width: 560px; height: 380px; }}
    #lap-screen {{ position: absolute; left: 62px; top: 22px; width: 436px; height: 270px; border-radius: 10px;
      overflow: hidden; }}
    #lap-screen img {{ width: 436px; height: 436px; margin-top: -60px; display: block; }}
    #s4-just {{ top: 860px; font-size: 84px; font-weight: 900; }}
    #s4-link {{ top: 990px; font-size: 112px; font-weight: 900; font-style: italic; color: var(--teal); }}
    #s4-linkicon {{ position: absolute; left: 462px; top: 1150px; width: 96px; height: 96px; }}

    /* S5 */
    .deva {{ font-family: 'Noto Sans Devanagari', sans-serif; font-weight: 800; line-height: 1.2; }}
    .mword {{ position: absolute; top: 600px; width: 440px; text-align: center; font-size: 150px; }}
    .mlab {{ position: absolute; top: 850px; width: 440px; text-align: center; font-size: 36px; font-weight: 800;
      letter-spacing: 8px; color: var(--teal); }}
    #m-l, #m-ll {{ left: 30px; }}
    #m-r, #m-rl {{ left: 550px; }}
    #m-plus {{ position: absolute; left: 455px; top: 615px; width: 110px; text-align: center; font-size: 150px;
      font-weight: 900; color: var(--teal); }}
    #m-merged {{ top: 600px; font-size: 160px; }}
    #m-under {{ position: absolute; left: 210px; top: 845px; width: 600px; height: 10px; border-radius: 5px;
      background: var(--teal); transform: scaleX(0); box-shadow: 0 0 24px rgba(47,224,198,0.8); }}
    #m-a {{ top: 900px; font-size: 80px; font-weight: 900; }}
    #m-b {{ top: 1005px; font-size: 64px; font-weight: 800; font-style: italic; color: var(--teal); }}
    #s5-zoom {{ transform-origin: 510px 860px; }}

    /* S6 */
    #s6-bgwrap {{ position: absolute; left: 0; top: -66px; width: 1080px; height: 2052px; overflow: hidden; }}
    #s6-bgwrap video {{ width: 720px; height: 1368px; display: block; }}
    #s6-tint {{ background: linear-gradient(180deg, rgba(3,10,46,0.86) 0%, rgba(5,18,90,0.78) 50%, rgba(3,10,46,0.9) 100%); }}
    #w-welcome {{ top: 450px; font-size: 150px; font-weight: 900; letter-spacing: -2px; perspective: 800px; }}
    #w-to {{ top: 640px; font-size: 70px; font-weight: 800; }}
    #w-2026 {{ top: 740px; font-size: 300px; font-weight: 900; letter-spacing: -8px; color: transparent;
      background: linear-gradient(90deg, #2fe0c6 50%, #ffffff 50%);
      background-size: 200% 100%; background-position: 100% 0; -webkit-background-clip: text; background-clip: text; }}
    #w-batch {{ top: 1070px; font-size: 124px; font-weight: 900; font-style: italic; }}
    #c-tag {{ top: 440px; font-size: 92px; font-weight: 900; }}
    #c-class {{ top: 545px; font-size: 116px; font-weight: 900; font-style: italic; color: var(--teal); }}
    #c-met {{ top: 720px; font-size: 60px; font-weight: 800; letter-spacing: 2px; }}
    #c-dk {{ top: 800px; font-size: 88px; font-weight: 900; }}
    #c-handle {{ top: 1010px; }}
    .handle {{ display: inline-flex; align-items: center; gap: 18px; padding: 22px 44px 22px 22px; border-radius: 999px;
      background: rgba(255,255,255,0.1); border: 2px solid rgba(47,224,198,0.75); font-size: 56px; font-weight: 800; }}
    .at {{ width: 84px; height: 84px; border-radius: 50%; background: var(--teal); color: #031040; display: inline-flex;
      align-items: center; justify-content: center; font-size: 54px; font-weight: 900; }}
    #c-cursor {{ display: inline-block; width: 5px; height: 58px; background: #fff; margin-left: 4px; }}

    /* S7 */
    #e-logo, #e-glint {{ position: absolute; left: 80px; top: 480px; width: 860px; height: 286px; }}
    #e-glint {{ -webkit-mask-image: url('assets/img/deeksharambh.png'); -webkit-mask-size: 860px 286px;
      mask-image: url('assets/img/deeksharambh.png'); mask-size: 860px 286px;
      background: linear-gradient(105deg, rgba(255,255,255,0) 40%, rgba(255,255,255,0.95) 50%, rgba(255,255,255,0) 60%);
      background-size: 300% 100%; background-position: 120% 0; }}
    #e-line1, #e-line2 {{ font-size: 46px; font-weight: 500; }}
    #e-line1 {{ top: 840px; }}
    #e-line2 {{ top: 905px; }}
    #e-div {{ position: absolute; left: 210px; top: 1020px; width: 600px; height: 2px;
      background: linear-gradient(90deg, rgba(150,190,255,0), rgba(150,190,255,0.8), rgba(150,190,255,0)); }}
    #e-jo {{ position: absolute; left: 250px; top: 1070px; width: 520px; }}
    #e-cdoe {{ position: absolute; left: 240px; top: 1220px; width: 540px; }}
  </style>

  <!-- track 0: living background -->
  <div id="bg" class="clip full" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="0">
    <div id="bg-base" class="full"></div>
    <div id="orb1" class="orb" style="left:-380px; top:-200px;"></div>
    <div id="orb2" class="orb" style="left:300px; top:1100px;"></div>
    <div id="swoosh" class="full">
      <svg width="1080" height="1920" viewBox="0 0 1080 1920">
        <defs>
          <linearGradient id="sw" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stop-color="#3b7bff" stop-opacity="0"/><stop offset="0.5" stop-color="#7fb0ff" stop-opacity="0.9"/>
            <stop offset="1" stop-color="#3b7bff" stop-opacity="0"/>
          </linearGradient>
          <filter id="glow" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="22"/></filter>
        </defs>
        <path d="M-220 1720 C 200 1560, 640 1500, 1300 1180" stroke="url(#sw)" stroke-width="70" fill="none" opacity="0.35" filter="url(#glow)"/>
        <path d="M-220 1720 C 200 1560, 640 1500, 1300 1180" stroke="url(#sw)" stroke-width="3" fill="none"/>
        <path d="M-220 1810 C 260 1640, 700 1610, 1300 1330" stroke="url(#sw)" stroke-width="2" fill="none" opacity="0.7"/>
        <path d="M-220 330 C 300 250, 700 120, 1300 -60" stroke="url(#sw)" stroke-width="2" fill="none" opacity="0.45"/>
        <path d="M-220 330 C 300 250, 700 120, 1300 -60" stroke="url(#sw)" stroke-width="50" fill="none" opacity="0.18" filter="url(#glow)"/>
      </svg>
    </div>
    {"".join(particles)}
    <div id="pulse" class="full"></div>
  </div>

  <!-- S1 hook -->
  <div id="s1" class="clip scene" data-start="0" data-duration="6.150" data-track-index="1">
    <div class="ghost" id="g1" style="top:180px;">{GHOST}</div>
    <div class="ghost" id="g2" style="top:1320px;">{GHOST}</div>
    <div id="s1-kicker" class="row">{chars("DEEKSHARAMBH 2026")}</div>
    <div id="s1-numwrap" class="row"><span id="s1-num">9,000</span><span id="s1-plus">+</span></div>
    <div id="s1-sub" class="row">{chars("NEW LEARNERS")}</div>
    <div id="s1-day" class="row"><span class="w">ONE</span> <span class="w teal it">DAY.</span></div>
    <div id="s1-zoom" class="full">
      <svg class="abs" style="left:0; top:0;" width="1080" height="1920" viewBox="0 0 1080 1920">
        <rect id="s1-rect" x="40" y="975" width="940" height="175" rx="40" fill="none" stroke="#2fe0c6"
              stroke-width="6" stroke-dasharray="2400" stroke-dashoffset="2400"/>
      </svg>
      <div id="s1-screen" class="row"><span class="w">ONE</span> <span class="w teal it">SCREEN.</span></div>
    </div>
  </div>

  <!-- S2 scale wall: the wall itself is an untimed wrapper (videos time themselves;
       a timed wrapper would offset the frame extractor), its overlay is track 3 -->
  <div id="wall" class="full">
    <div id="wall-cam" class="full">
    <div id="wall-plane">
      <div class="strip" style="left:0px;"><video id="wall-a" class="clip" src="assets/footage/scroll-a.mp4" muted playsinline
        data-start="6.000" data-duration="6.250" data-track-index="2"></video></div>
      <div class="strip" style="left:744px;"><video id="wall-b" class="clip" src="assets/footage/scroll-b.mp4" muted playsinline
        data-start="6.000" data-duration="6.250" data-track-index="2"></video></div>
      <div class="strip" style="left:1488px;"><video id="wall-c" class="clip" src="assets/footage/scroll-c.mp4" muted playsinline
        data-start="6.000" data-duration="6.250" data-track-index="2"></video></div>
    </div>
  </div>
  </div>
  <div id="s2" class="clip scene" data-start="6.000" data-duration="6.250" data-track-index="3">
    <div id="s2-shade" class="full"></div>
    <div id="s2-a" class="row">{chars("THIS IS WHAT")}</div>
    <div id="s2-b" class="row">{chars("11,500")}</div>
    <div id="s2-c" class="row">{words("FIRST DAYS")}</div>
    <div id="s2-d" class="row">{words("LOOK LIKE.")}</div>
    <div id="s2-e" class="row"><span class="chip">THE <span class="teal">2026</span> BATCH</span></div>
    <div id="s2-f" class="row">{words("11,500+ NEW LEARNERS")}</div>
  </div>

  <!-- S3 the event -->
  <div id="s3" class="clip scene" data-start="12.000" data-duration="4.150" data-track-index="1">
    <div id="s3-inner" class="full">
      <img id="s3-logo" src="assets/img/deeksharambh.png" alt="">
      <div id="s3-glint"></div>
      <div id="s3-p1" class="row"><span class="pill">{ICON_CAL}<span>03 OCTOBER 2026</span></span></div>
      <div id="s3-p2" class="row"><span class="pill">{ICON_CLOCK}<span>10:30 AM – 3:30 PM</span></span></div>
      <div id="s3-hours" class="row">{chars("5 HOURS.")}</div>
      <div id="s3-live" class="row"><span class="live"><span id="s3-dot"></span>LIVE</span></div>
    </div>
  </div>

  <!-- S4 contrast -->
  <div id="s4" class="clip scene" data-start="16.000" data-duration="8.100" data-track-index="1">
    <div id="s4-inner" class="full">
      {nrow(1, 430, "HOSTEL MOVE")}
      {nrow(2, 690, "TRAIN TICKET")}
      {nrow(3, 950, "GETTING LOST")}
      <div id="laptop">
        <svg width="560" height="380" viewBox="0 0 560 380">
          <rect id="lap-frame" x="50" y="10" width="460" height="294" rx="20" fill="rgba(3,10,46,0.6)" stroke="#fff"
                stroke-width="6" stroke-dasharray="1600" stroke-dashoffset="1600"/>
          <path id="lap-base" d="M10 318 H550 L520 362 Q516 370 506 370 H54 Q44 370 40 362 Z" fill="none" stroke="#fff"
                stroke-width="6" stroke-linejoin="round" stroke-dasharray="1300" stroke-dashoffset="1300"/>
        </svg>
        <div id="lap-screen"><img src="assets/img/poster.png" alt=""></div>
      </div>
      <div id="s4-just" class="row">{words("JUST A LAPTOP")}</div>
      <div id="s4-link" class="row">{words("+ A LINK.")}</div>
      <div id="s4-linkicon">{ICON_LINK}</div>
    </div>
  </div>

  <!-- S5 meaning -->
  <div id="s5" class="clip scene" data-start="24.000" data-duration="4.150" data-track-index="1">
    <div id="s5-zoom" class="full">
      <div id="m-l" class="mword deva">दीक्षा</div>
      <div id="m-ll" class="mlab">INITIATION</div>
      <div id="m-plus">+</div>
      <div id="m-r" class="mword deva">आरंभ</div>
      <div id="m-rl" class="mlab">BEGINNING</div>
      <div id="m-merged" class="row deva">दीक्षारंभ</div>
      <div id="m-under"></div>
      <div id="m-a" class="row">{chars("THE BEGINNING")}</div>
      <div id="m-b" class="row">{words("OF YOUR JOURNEY.")}</div>
    </div>
  </div>

  <!-- S6 welcome + CTA (callback video untimed-wrapped, overlay on track 3) -->
  <div id="s6-bgwrap"><video id="welcome-bg" class="clip" src="assets/footage/scroll-c.mp4" muted playsinline
    data-start="28.000" data-duration="7.000" data-track-index="2"></video></div>
  <div id="s6" class="clip scene" data-start="28.000" data-duration="8.150" data-track-index="3">
    <div id="s6-tint" class="full"></div>
    <div id="s6-a" class="full">
      <div id="w-welcome" class="row">{chars("WELCOME")}</div>
      <div id="w-to" class="row">{words("TO JAIN ONLINE,")}</div>
      <div id="w-2026" class="row">2026</div>
      <div id="w-batch" class="row">{chars("BATCH.")}</div>
    </div>
    <div id="s6-b" class="full">
      <div id="c-tag" class="row">{words("TAG A")}</div>
      <div id="c-class" class="row">{chars("CLASSMATE")}</div>
      <div id="c-met" class="row">{words("YOU MET AT")}</div>
      <div id="c-dk" class="row">{chars("DEEKSHARAMBH")}</div>
      <div id="c-handle" class="row"><span class="handle"><span class="at">@</span><span>{chars("classmate", "tc")}</span><span id="c-cursor"></span></span></div>
    </div>
  </div>

  <!-- S7 end card -->
  <div id="s7" class="clip scene" data-start="36.000" data-duration="{TOTAL - 36:.3f}" data-track-index="1">
    <img id="e-logo" src="assets/img/deeksharambh.png" alt="">
    <div id="e-glint"></div>
    <div id="e-line1" class="row">{words("Welcome to your")}</div>
    <div id="e-line2" class="row">{words("online learning journey")}</div>
    <div id="e-div"></div>
    <img id="e-jo" src="assets/img/jain-online.png" alt="">
    <img id="e-cdoe" src="assets/img/jain-cdoe.png" alt="">
  </div>

  <!-- track 3: overlays -->
  <div id="vignette" class="clip full" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="4"></div>
  <div id="flash" class="clip full" data-start="0" data-duration="{TOTAL:.3f}" data-track-index="4"></div>

  <audio id="music-bed" class="clip" src="assets/audio/music.wav" data-start="0" data-duration="{TOTAL:.3f}"
         data-track-index="5" data-volume="1"></audio>

  <script src="assets/gsap.min.js"></script>
  <script>
__TIMELINE__
  </script>
</div>
</body>
</html>
"""

TIMELINE = r"""
    const TOTAL = __TOTAL__;
    const tl = gsap.timeline({ paused: true });
    const $ = (s) => document.querySelector(s);
    const $$ = (s) => Array.from(document.querySelectorAll(s));
    const IR = { immediateRender: false };
    // cued entrance: hidden until t, then from -> to
    const enter = (target, t, from, to) => tl.fromTo(target, from, Object.assign({}, IR, to), t);
    const leave = (target, t, to) => tl.to(target, Object.assign({ overwrite: false }, to), t);
    const slam = (target, t, stagger) => enter(target, t,
      { opacity: 0, scale: 2.3, filter: "blur(12px)" },
      { opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.32, ease: "power4.out", stagger: stagger || 0.1 });
    const rise = (target, t, stagger) => enter(target, t,
      { opacity: 0, y: 90, rotationX: -80 },
      { opacity: 1, y: 0, rotationX: 0, duration: 0.5, ease: "back.out(1.7)", stagger: stagger || 0.03 });
    const flash = (t, peak) => enter("#flash", t, { opacity: peak || 0.85 }, { opacity: 0, duration: 0.4, ease: "power2.out" });

    // ---------- background: always moving ----------
    tl.fromTo("#orb1", { x: 0, y: 0 }, { x: 520, y: 380, duration: TOTAL, ease: "sine.inOut" }, 0);
    tl.fromTo("#orb2", { x: 0, y: 0 }, { x: -480, y: -620, duration: TOTAL, ease: "sine.inOut" }, 0);
    tl.fromTo("#swoosh", { x: -70, rotation: -2 }, { x: 70, rotation: 2, duration: 8, ease: "sine.inOut",
      repeat: 4, yoyo: true, transformOrigin: "540px 960px" }, 0);
    $$(".pt").forEach((el, i) => {
      tl.fromTo(el, { y: 0 }, { y: -Number(el.dataset.rise), duration: TOTAL, ease: "none" }, 0);
    });
    // beat pulse in the two drops (6-12, 28-36)
    const beats = [];
    for (let t = 6; t < 12; t += 0.5) beats.push(t);
    for (let t = 28; t < 36; t += 0.5) beats.push(t);
    beats.forEach((t) => {
      tl.fromTo("#pulse", { opacity: 0 }, { immediateRender: false, opacity: 0.32, duration: 0.03 }, t);
      tl.to("#pulse", { opacity: 0, duration: 0.4, ease: "power2.out" }, t + 0.03);
    });
    tl.set("#pulse", { opacity: 0 }, 12);
    tl.set("#pulse", { opacity: 0 }, 36);

    // ---------- S1 hook (0-6) ----------
    tl.fromTo(".ghost", { opacity: 0 }, { opacity: 1, duration: 0.6 }, 0);
    tl.fromTo("#g1", { x: -900 }, { x: -200, duration: 6.15, ease: "none" }, 0);
    tl.fromTo("#g2", { x: -100 }, { x: -800, duration: 6.15, ease: "none" }, 0);
    tl.fromTo("#s1-kicker .ch", { opacity: 0, y: -30 }, { opacity: 1, y: 0, duration: 0.3, stagger: 0.012, ease: "power3.out" }, 0);
    tl.fromTo("#s1-numwrap", { opacity: 0, scale: 1.5, filter: "blur(14px)" },
      { opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.55, ease: "expo.out" }, 0);
    const counter = { v: 9000 };
    const numEl = $("#s1-num");
    tl.fromTo(counter, { v: 9000 }, { v: 11500, duration: 1.1, ease: "expo.out",
      onUpdate: () => { numEl.textContent = Math.round(counter.v).toLocaleString("en-IN"); } }, 0);
    enter("#s1-plus", 1.0, { scale: 1.8, rotation: -90 }, { scale: 1, rotation: 0, duration: 0.45, ease: "back.out(2.4)" });
    rise("#s1-sub .ch", 1.0, 0.03);
    leave("#s1-kicker", 1.85, { opacity: 0, y: -40, duration: 0.2 });
    leave(["#s1-numwrap", "#s1-sub"], 1.85, { y: -330, scale: 0.84, duration: 0.35, ease: "power3.out" });
    slam("#s1-day .w", 2.0, 0.12);
    tl.fromTo("#s1", { x: -14 }, { immediateRender: false, x: 0, duration: 0.3, ease: "elastic.out(1, 0.3)" }, 2.0);
    slam("#s1-screen .w", 3.0, 0.12);
    tl.fromTo("#s1", { x: 14 }, { immediateRender: false, x: 0, duration: 0.3, ease: "elastic.out(1, 0.3)" }, 3.0);
    enter("#s1-rect", 4.0, { attr: { "stroke-dashoffset": 2400 } }, { attr: { "stroke-dashoffset": 0 }, duration: 0.9, ease: "power2.inOut" });
    leave(["#s1-numwrap", "#s1-sub", "#s1-day", ".ghost"], 4.9, { opacity: 0, y: "-=60", duration: 0.35, ease: "power2.in" });
    enter("#s1-zoom", 5.1, { scale: 1 }, { scale: 9, duration: 0.9, ease: "power3.in" });
    leave("#s1-screen", 5.6, { opacity: 0, duration: 0.35 });
    flash(6.0, 0.9);

    // ---------- S2 scale wall (6-12) ----------
    tl.set(["#wall", "#s6-bgwrap"], { opacity: 0 }, 0);
    tl.set("#wall", { opacity: 1 }, 6.0);
    tl.set("#wall", { opacity: 0 }, 12.25);
    tl.set("#s6-bgwrap", { opacity: 1 }, 28.0);
    tl.fromTo("#wall-plane", { scale: 1.64, rotation: 1, rotationX: 0, y: 0, opacity: 1, transformOrigin: "1104px 684px" },
      { scale: 1.5, rotation: -1.5, duration: 3.0, ease: "power1.out" }, 6.0);
    tl.fromTo("#wall-plane", { scale: 1.5, rotation: -1.5, rotationX: 0, y: 0 },
      { immediateRender: false, scale: 0.6, rotation: -7, rotationX: 22, y: 30, duration: 1.4, ease: "power3.inOut" }, 9.0);
    tl.fromTo("#wall-plane", { scale: 0.6 }, { immediateRender: false, scale: 0.65, duration: 1.2, ease: "none" }, 10.4);
    tl.fromTo("#wall-plane", { opacity: 1 }, { immediateRender: false, scale: 2.8, opacity: 0, duration: 0.6, ease: "power3.in" }, 11.6);
    tl.set("#wall-plane", { opacity: 0 }, 12.2);
    tl.fromTo("#s2-shade", { opacity: 1 }, { immediateRender: false, opacity: 0.35, duration: 1.0 }, 9.0);
    rise("#s2-a .ch", 6.1, 0.02);
    enter("#s2-b .ch", 6.5, { opacity: 0, scale: 0.3, y: 40 }, { opacity: 1, scale: 1, y: 0, duration: 0.4, stagger: 0.04, ease: "back.out(2)" });
    slam("#s2-c .w", 7.0, 0.12);
    slam("#s2-d .w", 7.5, 0.12);
    leave(["#s2-a", "#s2-b", "#s2-c", "#s2-d"], 8.9, { opacity: 0, y: -80, duration: 0.3, stagger: 0.05, ease: "power2.in" });
    enter("#s2-e", 9.6, { opacity: 0, y: -40, scale: 0.8 }, { opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "back.out(2)" });
    rise("#s2-f .w", 10.0, 0.1);
    leave(["#s2-e", "#s2-f"], 11.5, { opacity: 0, duration: 0.3 });
    flash(12.0, 0.8);

    // ---------- S3 the event (12-16) ----------
    tl.fromTo("#s3-logo", { clipPath: "inset(0% 100% 0% 0%)", scale: 1.08, y: 30 },
      { clipPath: "inset(0% 0% 0% 0%)", scale: 1, y: 0, duration: 0.8, ease: "power3.inOut" }, 12.05);
    tl.fromTo("#s3-glint", { backgroundPosition: "120% 0" }, { backgroundPosition: "-20% 0", duration: 0.7, ease: "power2.inOut" }, 12.85);
    enter("#s3-p1", 13.0, { opacity: 0, x: -260, filter: "blur(10px)" }, { opacity: 1, x: 0, filter: "blur(0px)", duration: 0.5, ease: "expo.out" });
    enter("#s3-p2", 13.5, { opacity: 0, x: 260, filter: "blur(10px)" }, { opacity: 1, x: 0, filter: "blur(0px)", duration: 0.5, ease: "expo.out" });
    slam("#s3-hours .ch", 14.0, 0.035);
    enter("#s3-live", 14.5, { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2.6)" });
    tl.fromTo("#s3-dot", { scale: 1, opacity: 1 }, { scale: 0.55, opacity: 0.35, duration: 0.25, repeat: 5, yoyo: true, ease: "sine.inOut" }, 14.6);
    tl.fromTo("#s3-inner", { x: 0, skewX: 0, filter: "blur(0px)" },
      { immediateRender: false, x: -1300, skewX: 12, filter: "blur(18px)", duration: 0.45, ease: "power3.in" }, 15.6);

    // ---------- S4 contrast (16-24) ----------
    tl.fromTo("#s4-inner", { y: 20 }, { y: -40, duration: 6, ease: "none" }, 16.0);
    [[1, 16.0], [2, 18.0], [3, 20.0]].forEach(([i, t]) => {
      enter("#n" + i, t, { opacity: 0, x: 320, skewX: -16, filter: "blur(12px)" },
        { opacity: 1, x: 0, skewX: 0, filter: "blur(0px)", duration: 0.45, ease: "expo.out" });
      enter("#st" + i, t + 1.0, { scaleX: 0 }, { scaleX: 1, duration: 0.28, ease: "power4.out" });
      tl.fromTo("#nw" + i, { color: "rgba(255,255,255,1)" }, { immediateRender: false, color: "rgba(255,255,255,0.38)", duration: 0.25 }, t + 1.05);
      tl.fromTo("#s4-inner", { x: -10 }, { immediateRender: false, x: 0, duration: 0.3, ease: "elastic.out(1, 0.3)" }, t + 1.0);
    });
    leave(["#n1", "#n2", "#n3"], 22.0, { opacity: 0, y: -70, duration: 0.3, stagger: 0.06, ease: "power2.in" });
    enter("#laptop", 22.15, { opacity: 0, scale: 0.85, y: 40 }, { opacity: 1, scale: 1, y: 0, duration: 0.5, ease: "back.out(1.6)" });
    enter("#lap-frame", 22.15, { attr: { "stroke-dashoffset": 1600 } }, { attr: { "stroke-dashoffset": 0 }, duration: 0.6, ease: "power2.inOut" });
    enter("#lap-base", 22.35, { attr: { "stroke-dashoffset": 1300 } }, { attr: { "stroke-dashoffset": 0 }, duration: 0.5, ease: "power2.inOut" });
    enter("#lap-screen", 22.6, { opacity: 0, scale: 1.15 }, { opacity: 1, scale: 1, duration: 0.4, ease: "power2.out" });
    slam("#s4-just .w", 22.5, 0.1);
    slam("#s4-link .w", 23.0, 0.1);
    enter("#s4-linkicon", 23.2, { opacity: 0, rotation: -120, scale: 0.3 }, { opacity: 1, rotation: 0, scale: 1, duration: 0.45, ease: "back.out(2.2)" });
    tl.fromTo("#s4-inner", { scale: 1, opacity: 1, filter: "blur(0px)", transformOrigin: "510px 900px" },
      { immediateRender: false, scale: 1.5, opacity: 0, filter: "blur(16px)", duration: 0.4, ease: "power3.in" }, 23.65);
    tl.set("#s4-inner", { opacity: 0 }, 24.05);

    // ---------- S5 meaning (24-28) ----------
    enter(["#m-l", "#m-ll"], 24.05, { opacity: 0, x: -220, filter: "blur(12px)" }, { opacity: 1, x: 0, filter: "blur(0px)", duration: 0.5, ease: "expo.out" });
    enter("#m-plus", 25.0, { opacity: 0, scale: 0.2, rotation: -180 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.4, ease: "back.out(2.5)" });
    enter(["#m-r", "#m-rl"], 25.05, { opacity: 0, x: 220, filter: "blur(12px)" }, { opacity: 1, x: 0, filter: "blur(0px)", duration: 0.5, ease: "expo.out" });
    leave(["#m-l", "#m-ll"], 26.0, { x: 140, opacity: 0, duration: 0.3, ease: "power3.in" });
    leave(["#m-r", "#m-rl"], 26.0, { x: -140, opacity: 0, duration: 0.3, ease: "power3.in" });
    leave("#m-plus", 26.0, { scale: 0, opacity: 0, duration: 0.25 });
    enter("#m-merged", 26.2, { opacity: 0, scale: 1.4, filter: "blur(14px)" }, { opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.45, ease: "expo.out" });
    enter("#m-under", 26.45, { scaleX: 0 }, { scaleX: 1, duration: 0.4, ease: "power3.out" });
    rise("#m-a .ch", 26.5, 0.025);
    slam("#m-b .w", 27.0, 0.1);
    enter("#s5-zoom", 27.55, { scale: 1, opacity: 1 }, { scale: 3, opacity: 0, duration: 0.45, ease: "power3.in" });
    tl.set("#s5-zoom", { opacity: 0 }, 28.0);
    flash(28.0, 0.9);

    // ---------- S6 welcome + CTA (28-36) ----------
    tl.fromTo("#welcome-bg", { scale: 1.5, opacity: 0.24, transformOrigin: "0px 0px" }, { scale: 1.6, duration: 7, ease: "none" }, 28.0);
    leave("#welcome-bg", 34.6, { opacity: 0, duration: 0.4 });
    tl.set("#s6-bgwrap", { opacity: 0 }, 35.0);
    rise("#w-welcome .ch", 28.0, 0.045);
    slam("#w-to .w", 28.8, 0.1);
    enter("#w-2026", 29.5, { opacity: 0, scale: 0.55 }, { opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.8)" });
    enter("#w-2026", 30.05, { backgroundPosition: "100% 0" }, { backgroundPosition: "0% 0", duration: 0.5, ease: "power2.inOut" });
    slam("#w-batch .ch", 30.5, 0.04);
    tl.fromTo("#s6-a", { y: 0 }, { y: -30, duration: 3.5, ease: "none" }, 28.0);
    leave(["#w-welcome", "#w-to", "#w-2026", "#w-batch"], 31.55, { opacity: 0, y: "-=110", duration: 0.35, stagger: 0.05, ease: "power2.in" });
    slam("#c-tag .w", 32.0, 0.12);
    rise("#c-class .ch", 32.25, 0.035);
    slam("#c-met .w", 32.8, 0.08);
    enter("#c-dk .ch", 33.1, { opacity: 0, y: 50 }, { opacity: 1, y: 0, duration: 0.3, stagger: 0.025, ease: "power3.out" });
    enter("#c-handle", 33.6, { opacity: 0, scale: 0.6, y: 40 }, { opacity: 1, scale: 1, y: 0, duration: 0.45, ease: "back.out(2)" });
    $$("#c-handle .tc").forEach((el, i) => tl.fromTo(el, { opacity: 0 }, { immediateRender: false, opacity: 1, duration: 0.01 }, 33.9 + i * 0.07));
    tl.set(".tc", { opacity: 0 }, 0);
    tl.fromTo("#c-cursor", { opacity: 1 }, { opacity: 0, duration: 0.25, repeat: 9, yoyo: true, ease: "steps(1)" }, 33.6);
    tl.fromTo("#c-handle", { y: 0 }, { immediateRender: false, y: -12, duration: 0.5, repeat: 2, yoyo: true, ease: "sine.inOut" }, 34.6);
    leave("#s6-b", 35.6, { opacity: 0, scale: 0.92, duration: 0.4, ease: "power2.in" });
    tl.set("#s6-b", { opacity: 0 }, 36.0);
    flash(36.0, 0.7);

    // ---------- S7 end card (36-40) ----------
    enter("#e-logo", 36.0, { opacity: 0, scale: 0.86 }, { opacity: 1, scale: 1, duration: 0.8, ease: "expo.out" });
    tl.fromTo("#e-glint", { backgroundPosition: "120% 0" }, { backgroundPosition: "-20% 0", duration: 0.8, ease: "power2.inOut" }, 36.7);
    enter("#e-line1 .w", 36.5, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.4, stagger: 0.07, ease: "power3.out" });
    enter("#e-line2 .w", 36.75, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.4, stagger: 0.07, ease: "power3.out" });
    enter("#e-div", 37.1, { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: "power3.out" });
    enter("#e-jo", 37.3, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" });
    enter("#e-cdoe", 37.5, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" });
    tl.fromTo("#s7", { scale: 1 }, { scale: 1.03, duration: 4, ease: "none", transformOrigin: "540px 900px" }, 36.0);

    window.__timelines = window.__timelines || {};
    window.__timelines.reel = tl;
"""

hidden = """
    /* cued elements start hidden; their fromTo tweens reveal them */
    #s1-kicker .ch, #s1-sub .ch, #s1-day .w, #s1-screen .w, #s2-a .ch, #s2-b .ch, #s2-c .w, #s2-d .w, #s2-e, #s2-f .w,
    #s3-p1, #s3-p2, #s3-hours .ch, #s3-live, #n1, #n2, #n3, #laptop, #lap-screen, #s4-just .w, #s4-link .w, #s4-linkicon,
    #m-l, #m-ll, #m-plus, #m-r, #m-rl, #m-merged, #m-a .ch, #m-b .w, #w-welcome .ch, #w-to .w, #w-2026, #w-batch .ch,
    #c-tag .w, #c-class .ch, #c-met .w, #c-dk .ch, #c-handle, .tc, #e-logo, #e-line1 .w, #e-line2 .w, #e-jo, #e-cdoe {
      opacity: 0; }
    #s3-logo { clip-path: inset(0% 100% 0% 0%); }
    #e-div { transform: scaleX(0); }
  </style>"""
page = page.replace("\n  </style>", hidden, 1)
page = page.replace("__TIMELINE__", TIMELINE.replace("__TOTAL__", f"{TOTAL:.3f}"))
(project / "index.html").write_text(page, encoding="utf-8")
print(f"composed Deeksharambh 2026 recap: {TOTAL:.1f}s -> {project / 'index.html'}")
