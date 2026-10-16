/* Shared runtime for style templates (styles/<style>/index.html).
 *
 * build_index.py inlines a DATA blob (#hf-data) and copies this file to
 * assets/style/reel.js. A template's own script reads window.REEL, creates its
 * timed elements, and registers ONE paused GSAP timeline. Everything here is
 * seek-safe: no timers, no wall clock, no Math.random — the renderer seeks to
 * arbitrary frames across parallel workers, so every value must be a pure
 * function of the data.
 *
 * Elements created here are real clips (class "clip", data-start/-duration):
 * the runtime shows them only inside their window, so a template never has to
 * hide anything by hand after its clip ends.
 */
(function () {
  "use strict";
  const D = JSON.parse(document.getElementById("hf-data").textContent);
  const stage = document.getElementById("stage");
  const r3 = (t) => Math.round(t * 1000) / 1000;

  function esc(s) {
    return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  }

  /* A timed clip element appended to the stage (or opts.parent). */
  function clip(opts) {
    const el = document.createElement(opts.tag || "div");
    if (opts.id) el.id = opts.id;
    el.className = ("clip " + (opts.cls || "")).trim();
    el.dataset.start = String(r3(Math.max(0, opts.start)));
    el.dataset.duration = String(r3(Math.max(0.04, opts.dur)));
    el.dataset.trackIndex = String(opts.track == null ? 2 : opts.track);
    if (opts.html != null) el.innerHTML = opts.html;
    else if (opts.text != null) el.textContent = opts.text;
    if (opts.style) Object.assign(el.style, opts.style);
    (opts.parent || stage).appendChild(el);
    return el;
  }

  /* A plain (untimed) child element, for building inside a clip. */
  function node(tag, cls, html, parent) {
    const el = document.createElement(tag || "div");
    if (cls) el.className = cls;
    if (html != null) el.innerHTML = html;
    if (parent) parent.appendChild(el);
    return el;
  }

  /* Words wrapped for mask reveals: <span class="m"><span class="mi">w</span></span>. */
  function maskWords(text, extra) {
    return String(text).split(/\s+/).filter(Boolean)
      .map((w) => `<span class="m"><span class="mi ${extra || ""}">${esc(w)}</span></span>`)
      .join(" ");
  }

  /* Letters as transformable spans, words kept unbreakable:
   * <span class="wd"><span class="ch">a</span>...</span>. For tracking-in and
   * per-letter motion — animate x/opacity on .ch, never letter-spacing (layout
   * properties snap to whole pixels and jitter in the render). */
  function charSpans(text, emph) {
    return String(text).split(/\s+/).filter(Boolean).map((w) => {
      const cls = emph && emph(w) ? "wd em" : "wd";
      return `<span class="${cls}">` + Array.from(w).map((c) => `<span class="ch">${esc(c)}</span>`).join("") + "</span>";
    }).join(" ");
  }

  /* Spread offsets for a tracking-in: each letter starts pushed away from the
   * line's centre by `px` per letter of distance. */
  function trackOffsets(chars, px) {
    const mid = (chars.length - 1) / 2;
    return (i) => (i - mid) * px;
  }

  /* Money numbers and digits stop thumbs (PLAYBOOK §3): templates emphasise them. */
  function isEmphasis(word) {
    return /[0-9₹$€£%]/.test(word);
  }

  /* Deterministic PRNG (mulberry32) for shakes and jitter. */
  function rng(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  /* A fade that ends exactly on a clip boundary also gets a hard set at that
   * instant, or the last frame can flicker back (CLAUDE.md renderer rules). */
  function fadeOutAt(tl, target, tEnd, dur, ease) {
    tl.to(target, { opacity: 0, duration: dur, ease: ease || "power1.in" }, Math.max(0, tEnd - dur));
    tl.set(target, { opacity: 0 }, tEnd);
  }

  /* Captions belonging to a scene (by line index, falling back to time). */
  function captionsFor(scene) {
    return D.captions.filter((c) =>
      c.line != null ? c.line === scene.index
        : c.start >= scene.start - 0.01 && c.start < scene.start + scene.duration);
  }

  function pad2(n) {
    return String(n).padStart(2, "0");
  }

  /* ---- beats (project.json "beats", resolved by build_index.py) ----------
   * scene.beat: { text, text_t, transition, continue, draw: [...], inserts: [...] }
   * with every word anchor already turned into absolute seconds. */
  function beat(s) {
    return (s && s.beat) || {};
  }

  function insertsFor(s) {
    return (beat(s).inserts || []).map((i) => document.getElementById(i.id)).filter(Boolean);
  }

  /* Media a template should move during scene s: the scene's own clip plus its
   * inserts. A scene that continues the previous shot gets [] — size the owning
   * scene's hold move with mediaSpan(s) so it keeps running underneath. */
  function mediaFor(s) {
    const own = s.own_media ? document.getElementById(s.id) : null;
    return (own ? [own] : []).concat(insertsFor(s));
  }

  /* Whatever is on screen during s, own or continued (for per-beat jolts). */
  function screenMedia(s) {
    const el = s.media_id ? document.getElementById(s.media_id) : null;
    return (el ? [el] : []).concat(insertsFor(s));
  }

  function mediaSpan(s) {
    return s.media_span || s.duration;
  }

  /* False when the scene carries the previous shot on, or its beat says
   * "transition": "none" — a template's default cut accent should stay away. */
  function hasCut(s) {
    return !s.continues && beat(s).transition !== "none";
  }

  const FULL = { position: "absolute", left: "0px", top: "0px", width: "1080px", height: "1920px" };

  /* On-screen text from each scene's beat, as one timed clip per beat (class
   * "beat-text" + opts.cls). Line 1 is skipped: its text is already the title,
   * so the template's hook headline carries it. opts.mode: "mask" (words rise
   * through their baseline), "chars" (tracking-in letters) or "plain" (pop);
   * opts.wrap(innerHtml, scene) adds the template's own markup; opts.enter
   * overrides the entrance. Leaves at the scene end. Returns [{scene, el, start, end}]. */
  const ENTER = {
    mask: (tl, el, t) => tl.fromTo(el.querySelectorAll(".mi"), { yPercent: 105 },
      { yPercent: 0, duration: 0.6, ease: "expo.out", stagger: 0.05 }, t),
    chars: (tl, el, t) => {
      const ch = el.querySelectorAll(".ch");
      tl.fromTo(ch, { opacity: 0, x: trackOffsets(ch, 8) }, { opacity: 1, x: 0, duration: 1.2, ease: "power3.out" }, t);
    },
    plain: (tl, el, t) => tl.fromTo(el, { opacity: 0, scale: 0.7 },
      { opacity: 1, scale: 1, duration: 0.32, ease: "back.out(2)" }, t),
  };
  function beatTexts(tl, opts) {
    opts = opts || {};
    const mode = opts.mode || "mask";
    const out = [];
    scenes.forEach((s, i) => {
      const b = beat(s);
      if (!b.text || i === 0 || (opts.skip && opts.skip(s))) return;
      // a pause_before scene lands its text with the voice, not in the silence
      const start = r3(b.text_t != null ? b.text_t
        : s.pause_before ? s.voice_start : s.start + (opts.delay || 0));
      const end = r3(s.start + s.duration);
      if (end - start < 0.2) return;
      const inner = mode === "chars" ? charSpans(b.text, isEmphasis)
        : mode === "plain" ? esc(b.text) : maskWords(b.text);
      const el = clip({ cls: ("beat-text " + (opts.cls || "")).trim(), start, dur: end - start,
        track: opts.track == null ? 2 : opts.track, html: opts.wrap ? opts.wrap(inner, s) : inner });
      (opts.enter || ENTER[mode])(tl, el, start, s);
      fadeOutAt(tl, el, end, opts.out || 0.25);
      out.push({ scene: s, el, start, end });
    });
    return out;
  }

  /* Word-anchored inserts are real media clips that cut in on their own (a
   * smash cut). This adds the optional accent over each cut: opts.flash
   * seconds of white (0 = none). Returns [{scene, el, ins}]. */
  function insertCuts(tl, opts) {
    opts = opts || {};
    const out = [];
    scenes.forEach((s) => (beat(s).inserts || []).forEach((ins) => {
      const el = document.getElementById(ins.id);
      if (!el) return;
      if (opts.flash) {
        const f = clip({ start: ins.start, dur: opts.flash, track: 2,
          style: Object.assign({ background: opts.color || "#fff", zIndex: String(opts.z || 8) }, FULL) });
        tl.fromTo(f, { opacity: 0.9 }, { opacity: 0, duration: opts.flash, ease: "power2.out" }, ins.start);
        tl.set(f, { opacity: 0 }, r3(ins.start + opts.flash));
      }
      out.push({ scene: s, el, ins });
    }));
    return out;
  }

  /* A scene's entrance plus its hold move, as one sequence on opts.targets
   * (default mediaFor(s)), named by the beat's "transition" (else opts.kind):
   *   cut | none   nothing over the boundary
   *   dip          to black and up again (stretches into a pause_before)
   *   flash        a white frame-burst
   *   dissolve     targets fade in (needs scene_overlap underneath)
   *   punch | zoom targets scale down into place, then the hold move continues
   *   push         targets slide in from the right
   * The hold move is a scale drift opts.drift [from, to] over opts.span
   * (default mediaSpan(s)). Transforms and opacity only. Returns the kind. */
  function cutIn(tl, s, opts) {
    opts = opts || {};
    const kind = beat(s).transition || opts.kind || "cut";
    const targets = opts.targets || mediaFor(s);
    const t0 = s.start;
    const span = opts.span || mediaSpan(s);
    const drift = opts.drift || [1.06, 1.0];
    let tMove = t0;
    if (kind === "dip" || kind === "flash") {
      const dIn = kind === "dip" ? (opts.dipIn || 0.35) : 0;
      const dOut = kind === "dip" ? Math.max(0.35, Math.min(0.7, s.pause_before || 0.45)) : 0.22;
      const f = clip({ start: t0 - dIn, dur: dIn + dOut, track: 2,
        style: Object.assign({ background: kind === "dip" ? "#000" : "#fff", zIndex: String(opts.z || 8) }, FULL) });
      if (dIn) tl.fromTo(f, { opacity: 0 }, { opacity: 1, duration: dIn, ease: "power1.in" }, t0 - dIn);
      tl.fromTo(f, { opacity: 1 }, { opacity: 0, duration: dOut, ease: "power1.out", immediateRender: !dIn }, t0);
      tl.set(f, { opacity: 0 }, r3(t0 + dOut));
    } else if (kind === "dissolve" && targets.length) {
      tl.fromTo(targets, { opacity: 0 }, { opacity: 1, duration: opts.dissolve || 0.6, ease: "sine.inOut" }, t0);
    } else if ((kind === "punch" || kind === "zoom") && targets.length) {
      const d = kind === "punch" ? 0.28 : 0.55;
      tl.fromTo(targets, { scale: kind === "punch" ? 1.24 : 1.6 }, { scale: drift[0], duration: d, ease: "expo.out" }, t0);
      tMove = t0 + d;
    } else if (kind === "push" && targets.length) {
      tl.fromTo(targets, { x: 1080 }, { x: 0, duration: 0.45, ease: "expo.out" }, t0);
    }
    const rest = span - (tMove - t0);
    if (targets.length && rest > 0.05 && drift[0] !== drift[1]) {
      tl.fromTo(targets, { scale: drift[0] }, { scale: drift[1], duration: rest, ease: "sine.out",
        immediateRender: tMove === t0 }, tMove);
    }
    return kind;
  }

  const scenes = D.scenes;
  const last = scenes[scenes.length - 1];
  window.REEL = {
    D, stage, scenes, captions: D.captions, params: D.params || {},
    first: scenes[0], last, total: D.total, ctaStart: D.cta_start,
    clip, node, esc, maskWords, charSpans, trackOffsets, isEmphasis, rng, fadeOutAt, captionsFor, pad2, r3,
    beat, insertsFor, mediaFor, screenMedia, mediaSpan, hasCut, beatTexts, insertCuts, cutIn, FULL,
    sceneEnd: (s) => r3(s.start + s.duration),
  };
})();
