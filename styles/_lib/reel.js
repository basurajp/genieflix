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

  const scenes = D.scenes;
  const last = scenes[scenes.length - 1];
  window.REEL = {
    D, stage, scenes, captions: D.captions, params: D.params || {},
    first: scenes[0], last, total: D.total, ctaStart: D.cta_start,
    clip, node, esc, maskWords, charSpans, trackOffsets, isEmphasis, rng, fadeOutAt, captionsFor, pad2, r3,
    sceneEnd: (s) => r3(s.start + s.duration),
  };
})();
