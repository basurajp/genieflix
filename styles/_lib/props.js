/* Shared prop library for drawing styles (blueprint, papercut, ...).
 *
 * Loaded after reel.js; a template calls REEL_PROPS(tl, {ease}) and gets
 *   PROPS  — one builder per prop name in project.json beats "draw":
 *            PROPS[name](spec, scene, layer) adds DOM to the scene layer and
 *            schedules its own tweens on tl. Word anchors arrive resolved to
 *            absolute seconds (spec.t, spec.t_end, spec.cue_times, spec.<x>_t).
 *   H      — the drawing helpers (svg, draw-on, mask reveals, sizing).
 * Everything is seek-safe (no timers, no Math.random — R.rng). Look is CSS:
 * colours come from the template's role variables --bg --ink --acc --hot
 * --leaf, line weights and prop boxes from its classes (.ln .thin .acc .wrn
 * .grn .cl .tx, .polaroid .tag .receipt .sticker .stamp .card .plate .row-chk
 * .tile .cutout .clip-card). SVG sub-elements rotate/scale with svgOrigin only.
 */
(function () {
  "use strict";
  window.REEL_PROPS = function (tl, opts) {
    const R = window.REEL, esc = R.esc;
    // entrance ease: a style can make every prop move its way ("steps(7)" = stop-motion)
    const IN = (opts && opts.ease) || "expo.out";
    const rnd = R.rng(11);

    /* ---------- drawing helpers ---------- */
    // stroke draw-on: pathLength 1 with a 1-on/2-off dash, offset 1 -> 0 (no end-cap dot)
    const DR = 'pathLength="1" stroke-dasharray="1 2" stroke-dashoffset="1"';
    const svg = (inner, vb, cls) => {
      const [w, h] = (vb || "1080 1920").split(" ");
      return `<svg class="art ${cls || ""}" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">${inner}</svg>`;
    };
    function drawOn(els, t, dur, stagger, ease) {
      const list = Array.from(els);
      if (!list.length) return t;
      tl.fromTo(list, { attr: { "stroke-dashoffset": 1 } },
        { attr: { "stroke-dashoffset": 0 }, duration: dur, ease: ease || "power2.inOut", stagger: stagger || 0 }, t);
      return t + dur + (stagger || 0) * (list.length - 1);
    }
    function drawnAt(els, t) {
      const list = Array.from(els);
      if (list.length) tl.set(list, { attr: { "stroke-dashoffset": 0 } }, t);
    }
    function fadeIn(els, t, dur, stagger) {
      const list = Array.from(els);
      if (list.length) tl.fromTo(list, { opacity: 0 }, { opacity: 1, duration: dur || 0.3, ease: "none", stagger: stagger || 0 }, t);
    }
    function maskIn(el, t, stagger) {
      tl.fromTo(el.querySelectorAll(".mi"), { yPercent: 105 }, { yPercent: 0, duration: 0.6, ease: IN, stagger: stagger || 0.05 }, t);
    }
    const words = (text) => String(text).split(/\s+/).filter(Boolean).map((w) =>
      `<span class="m"><span class="mi${R.isEmphasis(w) ? " em" : ""}">${esc(w)}</span></span>`).join(" ");
    // "MARS OASIS · 2001": one line when it fits at this size, else one segment
    // per line with the separator dropped (never a dot dangling at a line end)
    const stacked = (text, size) => {
      const segs = String(text).split(/\s+·\s+/);
      if (segs.length < 2 || 0.62 * size * String(text).length <= 840) return words(text);
      return segs.map((sg) => `<div>${words(sg)}</div>`).join("");
    };
    const sizeFor = (text, big) => {
      const len = String(text).length;
      return big ? (len <= 14 ? 150 : len <= 26 ? 118 : len <= 40 ? 92 : 74)
                 : (len <= 14 ? 132 : len <= 26 ? 100 : len <= 40 ? 80 : 64);
    };
    const reps = (span, period) => Math.max(0, Math.floor(span / period) - 1);

    /* ---------- props: each builds into the scene layer and schedules itself ---------- */
    const PROPS = {
      // shipping label being filled in, the address field blinking empty
      label(sp, s, L) {
        const t0 = sp.t != null ? sp.t : s.start + 0.12;
        const x = 150, y = 560, w = 780, h = 520;
        let bars = "";
        for (let k = 0, bx = x + w - 300; bx < x + w - 40; k++) {
          const bw = 3 + Math.floor(rnd() * 3) * 3;
          bars += `<line class="ln thin d" ${DR} x1="${bx}" y1="${y + h - 150}" x2="${bx}" y2="${y + h - 50}" style="stroke-width:${bw}"/>`;
          bx += bw + 6 + Math.floor(rnd() * 3) * 4;
        }
        const g = R.node("div", "pw", svg(`<g transform="rotate(-3 540 820)">
          <rect class="ln d" ${DR} x="${x}" y="${y}" width="${w}" height="${h}" rx="18"/>
          <line class="ln thin d" ${DR} x1="${x}" y1="${y + 112}" x2="${x + w}" y2="${y + 112}"/>
          <text class="tx" x="${x + 36}" y="${y + 74}" font-size="44">${esc(sp.text || "DELIVER TO:")}</text>
          <text class="tx c" x="${x + w - 36}" y="${y + 70}" font-size="24" text-anchor="end">PRIORITY · FRAGILE</text>
          <line class="ln thin d" ${DR} x1="${x + 36}" y1="${y + 232}" x2="${x + w - 36}" y2="${y + 232}"/>
          <line class="ln thin d" ${DR} x1="${x + 36}" y1="${y + 300}" x2="${x + w - 36}" y2="${y + 300}"/>
          <line class="ln thin d" ${DR} x1="${x + 36}" y1="${y + 368}" x2="${x + w * 0.5}" y2="${y + 368}"/>
          <rect class="cur" x="${x + 40}" y="${y + 168}" width="26" height="56" fill="var(--acc)"/>
          <text class="tx" x="${x + 36}" y="${y + h - 60}" font-size="22">CONTENTS: 1 GREENHOUSE</text>
          <text class="tx" x="${x + 36}" y="${y + h - 26}" font-size="22">(LIVE PLANTS)</text>
          ${bars}</g>`), L);
        drawOn(g.querySelectorAll(".d"), t0, 0.9, 0.02);
        fadeIn(g.querySelectorAll(".tx"), t0 + 0.35, 0.3, 0.06);
        const cur = g.querySelector(".cur"), end = R.sceneEnd(s);
        tl.fromTo(cur, { opacity: 0 }, { opacity: 1, duration: 0.01 }, t0 + 0.7);
        tl.to(cur, { opacity: 0, duration: 0.28, ease: "steps(1)", repeat: reps(end - t0 - 0.9, 0.28), yoyo: true }, t0 + 0.9);
      },

      // a photo of green on red, dropped into frame (the beat's image, else drawn)
      polaroid(sp, s, L) {
        const t0 = sp.t != null ? sp.t : s.start + 0.08;
        const drawn = svg(`<rect x="0" y="360" width="524" height="180" fill="#8a3b22"/>
          <path class="ln grn d" ${DR} d="M262 380 C 262 330, 262 300, 262 250"/>
          <path class="ln grn d" ${DR} d="M262 300 C 230 260, 190 260, 170 280 C 200 300, 240 305, 262 300"/>
          <path class="ln grn d" ${DR} d="M262 270 C 290 225, 335 220, 360 238 C 330 262, 290 270, 262 270"/>`, "524 540");
        const card = R.node("div", "polaroid",
          `<div class="ph">${sp.image ? `<img src="${esc(sp.image)}" alt="">` : drawn}</div>
           <div class="pc mono">${esc(sp.caption || "PLANTS. ON MARS.")}</div>`, L);
        const end = R.sceneEnd(s);
        tl.fromTo(card, { y: -1400, rotation: -16 }, { y: 0, rotation: -4, duration: 0.7, ease: "back.out(1.3)" }, t0);
        drawOn(card.querySelectorAll(".d"), t0 + 0.5, 0.9, 0.2);
        tl.to(card, { rotation: -1.5, duration: 1.4, ease: "sine.inOut", yoyo: true, repeat: reps(end - t0 - 0.7, 1.4) }, t0 + 0.7);
      },

      // a price tag on a string, swinging to rest
      pricetag(sp, s, L) {
        const t0 = sp.t != null ? sp.t : s.start + 0.3;
        const tag = R.node("div", "tag", svg(`<line class="ln thin" x1="180" y1="0" x2="180" y2="150"/>
          <path d="M110 150 L250 150 L325 232 L325 540 L35 540 L35 232 Z" fill="var(--hot)" stroke="var(--ink)" stroke-width="5" stroke-linejoin="round"/>
          <circle cx="180" cy="214" r="20" fill="var(--bg)" stroke="var(--ink)" stroke-width="4"/>
          <text class="tx big" x="180" y="390" font-size="116" text-anchor="middle" style="fill:var(--bg)">${esc(sp.text || "$50M")}</text>
          <text class="tx" x="180" y="470" font-size="24" text-anchor="middle" style="fill:var(--bg)">${esc(sp.note || "ONE LAUNCH")}</text>`, "360 560"), L);
        tl.fromTo(tag, { y: -760 }, { y: 0, duration: 0.42, ease: "power3.out" }, t0);
        let t = t0 + 0.2;
        [15, -10, 6.5, -4, 2.5, -1.4, 0.7, 0].forEach((a) => { tl.to(tag, { rotation: a, duration: 0.44, ease: "sine.inOut" }, t); t += 0.44; });
        if (sp.t_end != null) R.fadeOutAt(tl, tag, sp.t_end, 0.2);
      },

      // a receipt printing out; the delivery row lights up, the price gets circled
      receipt(sp, s, L) {
        const t0 = sp.t != null ? sp.t : s.start + 0.1;
        const items = sp.items || [];
        const cues = sp.cue_times || [];
        const lastPrice = items.length ? items[items.length - 1][1] : "";
        const slot = R.node("div", "receipt-slot", `<div class="receipt">
            <div class="rh mono">${esc(sp.title || "MARS OASIS PROJECT")}</div>
            <div class="rs mono">${esc(sp.subtitle || "RECEIPT")}</div>
            <div class="rr"></div>
            ${items.map((it) => `<div class="row mono"><i class="hl"></i><span>${esc(it[0])}</span><span>${esc(it[1] || "")}</span></div>`).join("")}
            <div class="rr"></div>
            <div class="row total mono"><span>TOTAL</span><span class="tp">${esc(sp.total || lastPrice)}</span>
              <svg class="circ" viewBox="0 0 520 110" width="520" height="110"><ellipse class="ln wrn d" ${DR} cx="370" cy="55" rx="160" ry="46" transform="rotate(-4 370 55)"/></svg></div>
          </div><div class="slot"></div>`, L);
        const paper = slot.querySelector(".receipt");
        tl.fromTo(paper, { yPercent: -102 }, { yPercent: 0, duration: 1.1, ease: "steps(14)" }, t0);
        const hls = slot.querySelectorAll(".row .hl");
        const hl = hls[hls.length - 1];
        if (hl) tl.fromTo(hl, { opacity: 0 }, { opacity: 0.55, duration: 0.2, ease: "none" }, cues[0] != null ? cues[0] : t0 + 1.3);
        drawOn(slot.querySelectorAll(".d"), cues[1] != null ? cues[1] : t0 + 2.0, 0.5, 0, "power1.inOut");
      },

      // a sticker slapped onto the shot
      sticker(sp, s, L) {
        const t0 = sp.t != null ? sp.t : s.start + 0.3;
        const st = R.node("div", "sticker", esc(sp.text || "(NO WARHEADS)"), L);
        tl.fromTo(st, { scale: 2.3, rotation: 16, opacity: 0 }, { scale: 1, rotation: -6, opacity: 1, duration: 0.2, ease: "power4.in" }, t0);
        tl.to(st, { rotation: -4, duration: 0.6, ease: "elastic.out(1, 0.4)" }, t0 + 0.2);
        if (sp.t_end != null) R.fadeOutAt(tl, st, sp.t_end, 0.2);
      },

      // drain the colour out of the footage underneath (a saturation blend over the media)
      desaturate(sp, s) {
        const t0 = sp.t != null ? sp.t : s.start;
        const g = R.clip({ cls: "desat", start: s.start, dur: s.duration, track: 2 });
        tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: 0.7, ease: "power1.inOut" }, t0);
      },

      // a stamp slammed across the frame
      stamp(sp, s, L) {
        const t0 = sp.t != null ? sp.t : s.start + 0.3;
        const st = R.node("div", "stamp", svg(`<circle cx="260" cy="260" r="236" fill="none" stroke="var(--hot)" stroke-width="12"/>
          <circle cx="260" cy="260" r="206" fill="none" stroke="var(--hot)" stroke-width="4"/>
          <path d="M150 150 L370 370 M370 150 L150 370" fill="none" stroke="var(--hot)" stroke-width="30" stroke-linecap="round"/>`, "520 520")
          + `<div class="band mono">${esc(sp.text || "NO DEAL")}</div>`, L);
        tl.fromTo(st, { scale: 2.6, rotation: -28, opacity: 0 }, { scale: 1, rotation: -12, opacity: 0.96, duration: 0.17, ease: "power4.in" }, t0);
        for (let q = 0; q < 4; q++) tl.to(L, { x: (rnd() - 0.5) * 24, y: (rnd() - 0.5) * 16, duration: 0.04, ease: "none" }, t0 + 0.17 + q * 0.04);
        tl.to(L, { x: 0, y: 0, duration: 0.05, ease: "none" }, t0 + 0.33);
        if (sp.t_end != null) R.fadeOutAt(tl, st, sp.t_end, 0.25);
      },

      // a line-drawn rocket: draws over the footage ("morph"), or stands drawn and lifts off
      rocket(sp, s, L) {
        const end = R.sceneEnd(s);
        const pre = sp.lift && !sp.morph;          // continues a drawing from the scene before
        const tDraw = pre ? s.start : (sp.t != null ? sp.t : s.start + 0.2);
        const liftT = sp.lift_t != null ? sp.lift_t : sp.lift ? (sp.t != null ? sp.t : s.start + s.duration * 0.45) : null;
        const fit = (inner) => svg(`<g transform="translate(54 110) scale(0.9)">${inner}</g>`);
        const dims = R.node("div", "rk", fit(`
          <line class="cl" x1="540" y1="360" x2="540" y2="1320"/>
          <line class="ln thin acc d" ${DR} x1="760" y1="420" x2="760" y2="1232"/>
          <line class="ln thin acc d" ${DR} x1="740" y1="420" x2="780" y2="420"/>
          <line class="ln thin acc d" ${DR} x1="740" y1="1232" x2="780" y2="1232"/>
          <text class="tx c" x="790" y="836" font-size="26">H</text>
          <line class="ln thin acc d" ${DR} x1="640" y1="730" x2="840" y2="640"/>
          <text class="tx" x="848" y="636" font-size="24">STAGE 2</text>
          <line class="ln thin acc d" ${DR} x1="640" y1="1000" x2="840" y2="1080"/>
          <text class="tx" x="848" y="1090" font-size="24">STAGE 1</text>
          <line class="ln thin acc d" ${DR} x1="430" y1="1200" x2="250" y2="1290"/>
          <text class="tx" x="120" y="1322" font-size="24">ENGINE</text>`), L);
        const body = R.node("div", "rk", fit(`
          <path class="ln d" ${DR} d="M540 420 C 598 470, 626 560, 628 640 L 452 640 C 454 560, 482 470, 540 420 Z"/>
          <rect class="ln d" ${DR} x="452" y="640" width="176" height="520"/>
          <line class="ln thin d" ${DR} x1="452" y1="820" x2="628" y2="820"/>
          <circle class="ln thin d" ${DR} cx="540" cy="725" r="26"/>
          <path class="ln d" ${DR} d="M452 1040 L 372 1180 L 372 1234 L 452 1160"/>
          <path class="ln d" ${DR} d="M628 1040 L 708 1180 L 708 1234 L 628 1160"/>
          <path class="ln d" ${DR} d="M500 1160 L 482 1232 L 598 1232 L 580 1160"/>
          <path class="ln wrn fl" ${DR} d="M496 1240 C 510 1330, 530 1400, 540 1470 C 550 1400, 570 1330, 584 1240"/>
          <path class="ln wrn fl" ${DR} d="M516 1240 C 524 1300, 534 1340, 540 1380 C 546 1340, 556 1300, 564 1240"/>`), L);
        const lines = [...body.querySelectorAll(".d"), ...dims.querySelectorAll(".d")];
        if (pre) {
          drawnAt(lines, s.start);
          fadeIn(L.querySelectorAll(".tx, .cl"), s.start, 0.01);
        } else {
          drawOn(body.querySelectorAll(".d"), tDraw, 1.5, 0.12);
          drawOn(dims.querySelectorAll(".d"), tDraw + 0.9, 0.7, 0.05);
          fadeIn(dims.querySelectorAll(".tx, .cl"), tDraw + 1.1, 0.3, 0.05);
        }
        if (sp.morph && s.media_id) {
          // the footage under the drawing gives way to the sheet, behind a scan line
          const media = document.getElementById(s.media_id);
          if (media) tl.to(media, { opacity: 0, duration: 1.2, ease: "power1.inOut" }, tDraw + 0.3);
          const scan = R.clip({ cls: "scan", start: tDraw + 0.2, dur: 1.4, track: 2 });
          tl.fromTo(scan, { y: 1500 }, { y: 300, duration: 1.4, ease: "power1.inOut" }, tDraw + 0.2);
          R.fadeOutAt(tl, scan, tDraw + 1.6, 0.2);
        }
        if (liftT != null && liftT < end - 0.2) {
          const fl = body.querySelectorAll(".fl");
          drawOn(fl, liftT, 0.25, 0.05, "power1.out");
          tl.to(fl, { opacity: 0.55, duration: 0.07, ease: "steps(1)", yoyo: true, repeat: reps(end - liftT, 0.07) }, liftT + 0.3);
          tl.to(dims, { opacity: 0, duration: 0.3, ease: "none" }, liftT);
          tl.fromTo(body, { y: 0 }, { y: -1700, duration: Math.min(1.8, end - liftT), ease: "power2.in" }, liftT + 0.15);
        }
      },

      // construction circles, then a question mark drawn over them
      question(sp, s, L) {
        const t0 = sp.t != null ? sp.t : s.start + 0.1;
        const g = R.node("div", "pw", svg(`<g class="cons">
            <circle class="ln thin acc d" ${DR} cx="540" cy="860" r="320"/>
            <circle class="ln thin acc d" ${DR} cx="540" cy="860" r="205"/>
            <line class="ln thin acc d" ${DR} x1="170" y1="860" x2="910" y2="860"/>
            <line class="ln thin acc d" ${DR} x1="540" y1="500" x2="540" y2="1220"/></g>
          <path class="ln q d" ${DR} style="stroke-width:34" d="M400 750 C 400 580, 680 580, 680 750 C 680 860, 540 870, 540 990 L 540 1050"/>
          <circle class="dot" cx="540" cy="1150" r="26" fill="var(--ink)"/>
          <text class="tx c" x="120" y="1300" font-size="26">${esc(sp.label || "Q.01")}</text>`), L);
        const end = drawOn(g.querySelectorAll(".cons .d"), t0, 0.8, 0.1);
        drawOn(g.querySelectorAll(".q"), t0 + 0.5, 0.9, 0, "power2.out");
        tl.fromTo(g.querySelector(".dot"), { scale: 0, svgOrigin: "540 1150" }, { scale: 1, svgOrigin: "540 1150", duration: 0.3, ease: "back.out(3)" }, t0 + 1.3);
        fadeIn(g.querySelectorAll(".tx"), t0 + 0.6, 0.3);
        tl.fromTo(g.querySelector(".cons"), { rotation: 0, svgOrigin: "540 860" }, { rotation: 25, svgOrigin: "540 860", duration: R.sceneEnd(s) - t0, ease: "none" }, t0);
      },

      // three option cards, each on its spoken word
      cards(sp, s, L) {
        const items = sp.items || [];
        const cues = sp.cue_times || [];
        const base = sp.t != null ? sp.t : s.start + 0.2;
        const icons = [
          // cart
          `<path class="ln d" ${DR} d="M40 70 L 78 70 L 104 168 L 196 168 L 214 98 L 88 98"/><circle class="ln d" ${DR} cx="116" cy="196" r="12"/><circle class="ln d" ${DR} cx="184" cy="196" r="12"/>`,
          // wrench
          `<path class="ln d" ${DR} d="M188 64 C 160 56, 132 72, 128 102 C 126 112, 128 120, 132 128 L 60 200 L 84 224 L 156 152 C 182 162, 214 146, 220 116 L 196 124 L 180 108 L 188 64 Z"/>`,
          // rethink: a loop of arrows
          `<path class="ln d" ${DR} d="M196 130 C 196 178, 160 210, 124 210 C 88 210, 56 182, 52 146"/><path class="ln d" ${DR} d="M52 110 C 52 62, 88 34, 124 34 C 160 34, 192 60, 196 94"/><path class="ln d" ${DR} d="M180 80 L 196 100 L 214 80"/><path class="ln d" ${DR} d="M34 160 L 52 140 L 68 160"/>`,
        ];
        const els = items.map((label, k) => {
          const card = R.node("div", "card", svg(`<rect class="ln thin d" ${DR} x="4" y="4" width="812" height="232" rx="20"/>
            <g transform="translate(14 0)">${icons[k % icons.length]}</g>`, "820 240") +
            `<div class="lab">${words(label)}</div>`, L);
          card.style.top = (430 + k * 300) + "px";
          const t = cues[k] != null ? cues[k] - 0.05 : base + k * 0.8;
          tl.fromTo(card, { x: 280, opacity: 0 }, { x: 0, opacity: 1, duration: 0.4, ease: IN }, t);
          drawOn(card.querySelectorAll(".d"), t, 0.6, 0.04);
          maskIn(card, t + 0.08);
          return card;
        });
        if (sp.t_end != null) els.forEach((c) => R.fadeOutAt(tl, c, sp.t_end, 0.25));
      },

      // labels locking into place, one per spoken word
      lockup(sp, s, L) {
        const items = sp.items || [];
        const cues = sp.cue_times || [];
        const base = sp.t != null ? sp.t : s.start + 0.2;
        const sizes = [120, 170, 66, 66];
        let y = 470;
        items.forEach((label, k) => {
          // one line per plate: shrink long labels to the content width (~0.6 em per letter)
          const size = Math.min(sizes[k] || 66, Math.floor(800 / (0.6 * Math.max(1, label.length))));
          const pl = R.node("div", "plate", `<i class="br l"></i><span class="txt">${words(label)}</span>`, L);
          pl.style.top = y + "px";
          pl.style.fontSize = size + "px";
          if (k === 1) pl.querySelectorAll(".mi").forEach((m) => m.classList.add("em"));
          y += size * 1.1 + 90;
          const t = Math.max(base, cues[k] != null ? cues[k] - 0.05 : base + k * 0.7);
          maskIn(pl, t, 0.04);
          tl.fromTo(pl.querySelector(".br"), { x: -60, opacity: 0 }, { x: 0, opacity: 1, duration: 0.25, ease: "back.out(2.5)" }, t + 0.25);
        });
      },

      // a checklist ticked off phrase by phrase
      checklist(sp, s, L) {
        const items = sp.items || [];
        const cues = sp.cue_times || [];
        const t0 = sp.t != null ? sp.t : s.start + 0.1;
        items.forEach((label, k) => {
          const y = 500 + k * 250;
          const box = R.node("div", "pw", svg(`<rect class="ln d" ${DR} x="140" y="${y}" width="112" height="112" rx="10"/>
            <path class="ln acc tick" ${DR} style="stroke-width:12" d="M160 ${y + 58} L 190 ${y + 90} L 238 ${y + 24}"/>`), L);
          const row = R.node("div", "row-chk", words(label), L);
          const size = label.length <= 14 ? 76 : 58;
          row.style.top = (y + (112 - size) / 2 - 4) + "px";
          row.style.fontSize = size + "px";
          drawOn(box.querySelectorAll(".d"), t0 + k * 0.12, 0.45);
          maskIn(row, t0 + k * 0.12 + 0.1, 0.03);
          const tc = cues[k] != null ? cues[k] : t0 + 0.8 + k * 1.2;
          drawOn(box.querySelectorAll(".tick"), tc, 0.25, 0, "power2.out");
          tl.to(row, { opacity: 1, duration: 0.15, ease: "none" }, tc);
        });
      },

      // a balance scale that tips, then settles level
      scale(sp, s, L) {
        const cues = sp.cue_times || [];
        const t0 = sp.t != null ? sp.t : s.start + 0.1;
        const tTip = cues[0] != null ? cues[0] : t0 + 1.2;
        const tLevel = cues[1] != null ? cues[1] : tTip + 2.0;
        const labels = sp.items || ["BUILD", "BUY"];
        const pan = (cx, label) => `<line class="ln thin d" ${DR} x1="${cx}" y1="640" x2="${cx - 110}" y2="880"/>
          <line class="ln thin d" ${DR} x1="${cx}" y1="640" x2="${cx + 110}" y2="880"/>
          <path class="ln d" ${DR} d="M${cx - 130} 880 C ${cx - 110} 960, ${cx + 110} 960, ${cx + 130} 880 Z"/>
          <text class="tx" x="${cx}" y="1010" font-size="36" text-anchor="middle">${esc(label)}</text>`;
        const g = R.node("div", "pw", svg(`<g class="post">
            <line class="ln d" ${DR} x1="540" y1="640" x2="540" y2="1180"/>
            <path class="ln d" ${DR} d="M400 1180 L 680 1180 L 640 1130 L 440 1130 Z"/>
            <circle class="ln thin acc d" ${DR} cx="540" cy="640" r="18"/></g>
          <g class="beam"><line class="ln d" ${DR} x1="260" y1="640" x2="820" y2="640"/></g>
          <g class="pan l">${pan(260, labels[0])}</g>
          <g class="pan r">${pan(820, labels[1])}</g>
          <path class="ln acc ok" ${DR} style="stroke-width:10" d="M505 560 L 532 590 L 580 520"/>`), L);
        drawOn(g.querySelectorAll(".post .d, .beam .d, .pan .d"), t0, 1.0, 0.03);
        fadeIn(g.querySelectorAll(".tx"), t0 + 0.6, 0.3);
        const beam = g.querySelector(".beam"), pl = g.querySelector(".pan.l"), pr = g.querySelector(".pan.r");
        const tip = -13, dy = 280 * Math.sin(-tip * Math.PI / 180);
        tl.fromTo(beam, { rotation: 0, svgOrigin: "540 640" }, { rotation: tip, svgOrigin: "540 640", duration: 0.7, ease: "back.out(2)" }, tTip);
        tl.fromTo(pl, { y: 0 }, { y: dy, duration: 0.7, ease: "back.out(2)" }, tTip);
        tl.fromTo(pr, { y: 0 }, { y: -dy, duration: 0.7, ease: "back.out(2)" }, tTip);
        tl.to(beam, { rotation: 0, svgOrigin: "540 640", duration: 1.1, ease: "elastic.out(1, 0.45)" }, tLevel);
        tl.to(pl, { y: 0, duration: 1.1, ease: "elastic.out(1, 0.45)" }, tLevel);
        tl.to(pr, { y: 0, duration: 1.1, ease: "elastic.out(1, 0.45)" }, tLevel);
        drawOn(g.querySelectorAll(".ok"), tLevel + 0.3, 0.3, 0, "power2.out");
      },

      // everyday costs, drawn one by one
      icons(sp, s, L) {
        const items = sp.items || [];
        const cues = sp.cue_times || [];
        const base = sp.t != null ? sp.t : s.start + 0.2;
        const art = {
          SOFTWARE: `<rect class="ln d" ${DR} x="30" y="30" width="200" height="140" rx="10"/><line class="ln thin d" ${DR} x1="30" y1="62" x2="230" y2="62"/><path class="ln thin acc d" ${DR} d="M70 100 L 54 116 L 70 132 M190 100 L 206 116 L 190 132 M140 92 L 120 140"/><line class="ln d" ${DR} x1="100" y1="200" x2="160" y2="200"/>`,
          PACKAGING: `<path class="ln d" ${DR} d="M130 30 L 220 72 L 220 172 L 130 214 L 40 172 L 40 72 Z"/><path class="ln thin d" ${DR} d="M40 72 L 130 114 L 220 72 M130 114 L 130 214"/><path class="ln thin acc d" ${DR} d="M85 51 L 175 93"/>`,
          DELIVERY: `<rect class="ln d" ${DR} x="20" y="60" width="140" height="110" rx="6"/><path class="ln d" ${DR} d="M160 90 L 206 90 L 236 128 L 236 170 L 160 170"/><circle class="ln d" ${DR} cx="62" cy="184" r="20"/><circle class="ln d" ${DR} cx="194" cy="184" r="20"/>`,
        };
        items.forEach((label, k) => {
          const tile = R.node("div", "tile", svg(`<rect class="ln thin acc d" ${DR} x="4" y="4" width="812" height="222" rx="18"/>
            <g transform="translate(18 4)">${art[String(label).toUpperCase()] || art.SOFTWARE}</g>`, "820 230") +
            `<div class="lab">${words(label)}</div><div class="per mono">${esc(sp.per || "EVERY MONTH")}</div>`, L);
          tile.style.top = (440 + k * 290) + "px";
          const t = cues[k] != null ? cues[k] - 0.05 : base + k * 0.6;
          tl.fromTo(tile, { scale: 0.85, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2)" }, t);
          drawOn(tile.querySelectorAll(".d"), t, 0.6, 0.03);
          maskIn(tile, t + 0.1);
          fadeIn(tile.querySelectorAll(".per"), t + 0.35, 0.2);
        });
      },
    };

    /* ---------- collage props: photos and clippings from the project's assets ---------- */

    // a person or object as a paper cut-out: a transparent PNG gets a paper
    // outline (class "png"), any other photo a torn-edged print ("photo").
    // spec: image, side left|right|center, h (px, default 900), y (top, px),
    // caption (a name tag), at / until. No image staged: the prop is skipped.
    PROPS.cutout = function (sp, s, L) {
      if (!sp.image) { console.warn("cutout: no image staged, skipped"); return; }
      const t0 = sp.t != null ? sp.t : s.start + 0.1;
      const h = sp.h || 900;
      const png = /\.png$/i.test(sp.image) && sp.kind !== "photo";
      const side = sp.side || "right";
      const el = R.node("div", `cutout ${png ? "png" : "photo"} ${side}`,
        `<img src="${esc(sp.image)}" alt="" style="height:${h}px">` +
        (sp.caption ? `<div class="tagline mono">${esc(sp.caption)}</div>` : ""), L);
      el.style.top = (sp.y != null ? sp.y : 1340 - h) + "px";
      const from = side === "left" ? -900 : side === "right" ? 900 : 0;
      const tilt = sp.tilt != null ? sp.tilt : side === "left" ? -2.5 : side === "right" ? 2.5 : 0;
      if (from) tl.fromTo(el, { x: from, rotation: tilt * 3 }, { x: 0, rotation: tilt, duration: 0.5, ease: IN }, t0);
      else tl.fromTo(el, { y: 700, rotation: -6 }, { y: 0, rotation: tilt, duration: 0.5, ease: IN }, t0);
      const end = sp.t_end != null ? sp.t_end : R.sceneEnd(s);
      tl.to(el, { rotation: tilt + 0.8, duration: 0.5, ease: "steps(2)", yoyo: true, repeat: reps(end - t0 - 0.6, 0.5) }, t0 + 0.6);
      if (sp.t_end != null) tl.to(el, { x: from ? from * 1.1 : 0, y: from ? 0 : 800, duration: 0.35, ease: "power3.in" }, sp.t_end - 0.35);
      if (sp.caption) tl.fromTo(el.querySelector(".tagline"), { scale: 0, rotation: -12 },
        { scale: 1, rotation: -3, duration: 0.3, ease: "back.out(2.5)" }, t0 + 0.45);
    };

    // a clipping from a news story or a paper: the screenshot you staged
    // (spec.image) with highlighter boxes and a marker circle in percent of the
    // image, or — with no screenshot — a note card in the reel's own type that
    // names its source (never a mock-up of a real masthead).
    // spec: image, source, highlights [[x,y,w,h], ...] (percent), circle [x,y,w,h],
    //       or lines [...] + highlight (line index); cues = highlight times, then
    //       the circle; at / until; tilt.
    PROPS.clipping = function (sp, s, L) {
      const t0 = sp.t != null ? sp.t : s.start + 0.15;
      const cues = sp.cue_times || [];
      const tilt = sp.tilt != null ? sp.tilt : -2;
      let inner;
      if (sp.image) {
        const boxes = (sp.highlights || []).map((b) =>
          `<i class="hlbox" style="left:${b[0]}%;top:${b[1]}%;width:${b[2]}%;height:${b[3]}%"></i>`).join("");
        const circ = sp.circle ? `<svg class="mark" viewBox="0 0 100 100" preserveAspectRatio="none" style="left:${sp.circle[0]}%;top:${sp.circle[1]}%;width:${sp.circle[2]}%;height:${sp.circle[3]}%">
            <ellipse class="ln wrn d" ${DR} cx="50" cy="50" rx="48" ry="44" vector-effect="non-scaling-stroke"/></svg>` : "";
        inner = `<div class="clipimg"><img src="${esc(sp.image)}" alt="">${boxes}${circ}</div>`;
      } else {
        const lines = sp.lines || [];
        inner = `<div class="note">${lines.map((ln, k) =>
          `<div class="nl${k === sp.highlight ? " hot" : ""}"><i class="hlbox"></i><span>${esc(ln)}</span></div>`).join("")}</div>`;
      }
      const card = R.node("div", "clip-card",
        inner + (sp.source ? `<div class="src mono">${esc(sp.source)}</div>` : ""), L);
      if (sp.y != null) card.style.top = sp.y + "px";
      tl.fromTo(card, { y: 900, rotation: tilt - 8 }, { y: 0, rotation: tilt, duration: 0.55, ease: IN }, t0);
      const hls = sp.image ? card.querySelectorAll(".hlbox") : card.querySelectorAll(".nl.hot .hlbox");
      Array.from(hls).forEach((hb, k) => {
        const t = cues[k] != null ? cues[k] : t0 + 0.8 + k * 0.5;
        tl.fromTo(hb, { scaleX: 0 }, { scaleX: 1, duration: 0.35, ease: "power2.out" }, t);
      });
      const tc = cues[hls.length] != null ? cues[hls.length] : t0 + 1.4 + hls.length * 0.5;
      drawOn(card.querySelectorAll(".mark .d"), tc, 0.45, 0, "power1.inOut");
      if (sp.t_end != null) tl.to(card, { y: 1000, rotation: tilt + 6, duration: 0.35, ease: "power3.in" }, sp.t_end - 0.35);
    };

    return { PROPS, H: { svg, DR, drawOn, drawnAt, fadeIn, maskIn, words, stacked, sizeFor, reps, IN } };
  };
})();
