// Original instrumental cue + sound design, synthesised offline with WebAudio.
// 100 BPM, 4/4, five bars = 12.0 s. Fully deterministic (seeded noise), so the
// preview and the exported WAV are bit-for-bit the same render.
import { TIMING, AUDIO } from './config.js';
import { rng } from './math.js';

const B = TIMING.beat; // 0.6 s
const S16 = B / 4;
const bar = (n) => n * TIMING.bar; // bar index -> seconds
const at = (b, beat = 0, six = 0) => bar(b) + beat * B + six * S16;

const NOTE = { C: 0, 'C#': 1, D: 2, 'D#': 3, E: 4, F: 5, 'F#': 6, G: 7, 'G#': 8, A: 9, 'A#': 10, B: 11 };
export function hz(name) {
  const m = name.match(/^([A-G]#?)(-?\d)$/);
  const midi = (Number(m[2]) + 1) * 12 + NOTE[m[1]];
  return 440 * Math.pow(2, (midi - 69) / 12);
}

// ---------------------------------------------------------------------------
// The score. Times in seconds. Everything the picture syncs to lives in TIMING.cues.
export const SCORE = (() => {
  const C = TIMING.cues;
  const pads = [
    { t0: 0.0, t1: 2.55, notes: ['B2', 'F#3', 'A3', 'C#4', 'D4'], level: 0.5, cutoff: [500, 1400] },
    { t0: 2.4, t1: 4.95, notes: ['G2', 'D3', 'F#3', 'A3', 'B3'], level: 0.55, cutoff: [900, 1800] },
    { t0: 4.8, t1: 6.05, notes: ['D3', 'F#3', 'A3', 'E4'], level: 0.6, cutoff: [1400, 2600] },
    { t0: 6.0, t1: 7.35, notes: ['A2', 'E3', 'A3', 'C#4', 'D4'], level: 0.6, cutoff: [1600, 2800] },
    { t0: 7.2, t1: 8.45, notes: ['E3', 'G3', 'B3', 'D4', 'F#4'], level: 0.55, cutoff: [1500, 2400] },
    { t0: 8.4, t1: 9.75, notes: ['A2', 'D3', 'G3', 'B3', 'E4'], level: 0.55, cutoff: [1500, 2600] },
    { t0: 9.6, t1: 12.6, notes: ['D3', 'A3', 'C#4', 'E4', 'F#4'], level: 0.6, cutoff: [2200, 900] },
  ];

  const kicks = [];
  const claps = [];
  const hats = [];
  const bass = [];
  // bar 1: tonal pulse only (soft sub pulse on each beat)
  for (let b = 0; b < 4; b++) bass.push({ t: at(0, b), dur: 0.42, note: 'B1', level: 0.32 + 0.06 * b });
  // bars 2-4: groove
  for (let b = 1; b <= 3; b++) {
    kicks.push(at(b, 0), at(b, 2));
    if (b >= 2) kicks.push(at(b, 3, 2)); // extra push from bar 3
    claps.push(at(b, 1), at(b, 3));
    const sub = b >= 2 ? 1 : 2; // 8ths in bar 2, 16ths from bar 3
    for (let s = 0; s < 16; s += sub) {
      if (b === 3 && s >= 12) continue; // drop the hats for the turnaround
      hats.push({ t: at(b, 0, s), accent: s % 4 === 2 ? 1 : 0.55 });
    }
  }
  const bassLine = {
    1: [['G1', 0, 0.5], ['G1', 1.5, 0.4], ['G2', 2.5, 0.22], ['G1', 3, 0.5]],
    2: [['D2', 0, 0.45], ['D2', 1.5, 0.25], ['F#2', 2, 0.4], ['A1', 2.75, 0.3], ['A1', 3.5, 0.4]],
    3: [['E2', 0, 0.45], ['E2', 1.5, 0.3], ['A1', 2, 0.5], ['A1', 3, 0.25], ['C#2', 3.5, 0.3]],
  };
  for (const [b, notes] of Object.entries(bassLine)) {
    for (const [n, beat, dur] of notes) bass.push({ t: at(Number(b), beat), dur: dur * 1.5, note: n, level: 0.6 });
  }
  // bar 5: resolution
  kicks.push(at(4, 0));
  bass.push({ t: at(4, 0), dur: 2.2, note: 'D1', level: 0.75 });

  // The motif: F#-A-B, answered; resolves to D on the title lock.
  const motif = [
    ['F#5', at(2, 0), 0.3], ['A5', at(2, 0.5), 0.3], ['B5', at(2, 1), 0.55], ['A5', at(2, 2), 0.25], ['E5', at(2, 2.5), 0.8],
    ['F#5', at(3, 0), 0.3], ['A5', at(3, 0.5), 0.3], ['B5', at(3, 1), 0.5], ['C#6', at(3, 2), 0.3], ['A5', at(3, 2.5), 0.3], ['E5', at(3, 3), 0.5],
  ];
  // Sonic signature on the title lock: motif tag in glass bells.
  const bells = [
    { t: C.firstHighlight, notes: ['B5', 'F#6'], level: 0.55, dur: 2.6 }, // opening glass accent
    { t: at(1, 0), notes: ['D6'], level: 0.18, dur: 1.4 },
    { t: C.titleLock, notes: ['F#5'], level: 0.5, dur: 2.4 },
    { t: C.titleLock + B * 0.5, notes: ['A5'], level: 0.45, dur: 2.2 },
    { t: C.titleLock + B * 1.0, notes: ['D6'], level: 0.5, dur: 2.4 },
  ];
  const sfx = {
    riser: { t0: 2.4, t1: 4.75 },
    whoosh: { t: C.ribbonSweep, dur: 0.75, pan: [0.7, -0.7] },
    accent: { t: C.letterPass, dur: 0.38 },
    reverseSwell: { t0: 8.85, t1: C.titleLock },
    shimmer: { t: C.finalHighlight },
  };
  return { pads, kicks, claps, hats, bass, motif, bells, sfx };
})();

// Deterministic visual envelope derived from the same score (0..1).
export function musicEnvelope(t) {
  let e = 0;
  for (const k of SCORE.kicks) if (t >= k) e += Math.exp(-(t - k) / 0.16) * 0.7;
  for (const b of SCORE.bass) if (t >= b.t) e += Math.exp(-(t - b.t) / 0.3) * 0.25 * b.level;
  for (const b of SCORE.bells) if (t >= b.t) e += Math.exp(-(t - b.t) / 0.5) * 0.4;
  const fade = t > 11.0 ? Math.max(0, 1 - (t - 11.0) / 1.0) : 1;
  return Math.min(1, e) * fade;
}

// ---------------------------------------------------------------------------
function noiseBuffer(ctx, seconds, seed) {
  const r = rng(seed);
  const n = Math.ceil(seconds * ctx.sampleRate);
  const buf = ctx.createBuffer(1, n, ctx.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = r() * 2 - 1;
  return buf;
}

function impulseResponse(ctx, seconds, decay, seed) {
  const r = rng(seed);
  const n = Math.ceil(seconds * ctx.sampleRate);
  const buf = ctx.createBuffer(2, n, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = buf.getChannelData(c);
    let lp = 0;
    for (let i = 0; i < n; i++) {
      const x = r() * 2 - 1;
      lp += (x - lp) * (0.35 - 0.25 * (i / n)); // darker tail
      d[i] = lp * Math.pow(1 - i / n, decay);
    }
  }
  return buf;
}

export async function renderCue() {
  const sr = AUDIO.sampleRate;
  const dur = 12.0;
  const ctx = new OfflineAudioContext(2, Math.ceil(dur * sr), sr);

  const master = ctx.createGain();
  master.gain.value = 0.9;
  const comp = ctx.createDynamicsCompressor();
  comp.threshold.value = -16;
  comp.knee.value = 8;
  comp.ratio.value = 3;
  comp.attack.value = 0.008;
  comp.release.value = 0.22;
  master.connect(comp).connect(ctx.destination);

  const music = ctx.createGain();
  music.gain.value = 1.0;
  music.connect(master);
  const sfxBus = ctx.createGain();
  sfxBus.gain.value = 0.55; // sound design sits beneath the music
  sfxBus.connect(master);

  const reverb = ctx.createConvolver();
  reverb.buffer = impulseResponse(ctx, 2.6, 2.4, 11);
  const revRet = ctx.createGain();
  revRet.gain.value = 0.55;
  reverb.connect(revRet).connect(master);

  const delay = ctx.createDelay(1.0);
  delay.delayTime.value = B * 0.75; // dotted eighth
  const fb = ctx.createGain();
  fb.gain.value = 0.32;
  const dlp = ctx.createBiquadFilter();
  dlp.type = 'lowpass';
  dlp.frequency.value = 3800;
  delay.connect(dlp).connect(fb).connect(delay);
  const dRet = ctx.createGain();
  dRet.gain.value = 0.35;
  dlp.connect(dRet).connect(master);

  const noise = noiseBuffer(ctx, 3, 3);
  let seed = 100;

  const send = (node, dry, wet, dly = 0, bus = music) => {
    const g = ctx.createGain();
    g.gain.value = dry;
    node.connect(g).connect(bus);
    const w = ctx.createGain();
    w.gain.value = wet;
    node.connect(w).connect(reverb);
    if (dly) {
      const d = ctx.createGain();
      d.gain.value = dly;
      node.connect(d).connect(delay);
    }
  };

  // --- pads: detuned saws, slow filter motion, wide
  for (const p of SCORE.pads) {
    const out = ctx.createGain();
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.Q.value = 0.7;
    lp.frequency.setValueAtTime(p.cutoff[0], p.t0);
    lp.frequency.linearRampToValueAtTime(p.cutoff[1], p.t1);
    const env = ctx.createGain();
    const atk = p.t0 === 0 ? 0.9 : 0.25;
    env.gain.setValueAtTime(0, p.t0);
    env.gain.linearRampToValueAtTime(p.level * 0.06, p.t0 + atk);
    env.gain.setValueAtTime(p.level * 0.06, p.t1 - 0.3);
    env.gain.linearRampToValueAtTime(0, p.t1 + (p.t1 > 12 ? 0 : 0.35));
    lp.connect(env).connect(out);
    p.notes.forEach((n, i) => {
      for (const det of [-7, 0, 7]) {
        const o = ctx.createOscillator();
        o.type = 'sawtooth';
        o.frequency.value = hz(n);
        o.detune.value = det + (i % 2 ? 2 : -2);
        const pan = ctx.createStereoPanner();
        pan.pan.value = Math.max(-0.8, Math.min(0.8, det / 9 + (i - p.notes.length / 2) * 0.08));
        o.connect(pan).connect(lp);
        o.start(p.t0);
        o.stop(p.t1 + 0.5);
      }
    });
    send(out, 0.8, 0.5);
  }

  // --- kick: round, restrained
  for (const t of SCORE.kicks) {
    const o = ctx.createOscillator();
    o.type = 'sine';
    o.frequency.setValueAtTime(130, t);
    o.frequency.exponentialRampToValueAtTime(46, t + 0.11);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.75, t + 0.004);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.42);
    o.connect(g);
    send(g, 1.0, 0.05);
    o.start(t);
    o.stop(t + 0.45);
  }

  // --- clap/rim: short filtered noise, crisp but quiet
  for (const t of SCORE.claps) {
    const src = ctx.createBufferSource();
    src.buffer = noise;
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.frequency.value = 1900;
    bp.Q.value = 1.4;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(0.22, t + 0.003);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.16);
    src.connect(bp).connect(g);
    send(g, 0.8, 0.3);
    src.start(t, (seed++ % 20) * 0.1, 0.2);
  }

  // --- hats
  for (const h of SCORE.hats) {
    const src = ctx.createBufferSource();
    src.buffer = noise;
    const hp = ctx.createBiquadFilter();
    hp.type = 'highpass';
    hp.frequency.value = 8200;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, h.t);
    g.gain.linearRampToValueAtTime(0.07 * h.accent, h.t + 0.002);
    g.gain.exponentialRampToValueAtTime(0.0001, h.t + 0.045);
    const pan = ctx.createStereoPanner();
    pan.pan.value = 0.25;
    src.connect(hp).connect(g).connect(pan);
    send(pan, 0.8, 0.12);
    src.start(h.t, (seed++ % 25) * 0.1, 0.08);
  }

  // --- warm bass: sine + filtered saw
  for (const n of SCORE.bass) {
    const f = hz(n.note);
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.setValueAtTime(900, n.t);
    lp.frequency.exponentialRampToValueAtTime(220, n.t + Math.min(0.4, n.dur));
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, n.t);
    g.gain.exponentialRampToValueAtTime(0.32 * n.level, n.t + 0.01);
    g.gain.setValueAtTime(0.32 * n.level, n.t + n.dur * 0.6);
    g.gain.exponentialRampToValueAtTime(0.0001, n.t + n.dur);
    for (const [type, mul, lvl] of [['sine', 1, 1], ['sawtooth', 1, 0.35], ['sine', 2, 0.18]]) {
      const o = ctx.createOscillator();
      o.type = type;
      o.frequency.value = f * mul;
      const og = ctx.createGain();
      og.gain.value = lvl;
      o.connect(og).connect(lp);
      o.start(n.t);
      o.stop(n.t + n.dur + 0.05);
    }
    lp.connect(g);
    send(g, 1.0, 0.04);
  }

  // --- motif: soft pluck (triangle + sine), echoes into the dotted-eighth delay
  for (const [n, t, d] of SCORE.motif) {
    const f = hz(n);
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.setValueAtTime(5200, t);
    lp.frequency.exponentialRampToValueAtTime(1300, t + 0.35);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.16, t + 0.006);
    g.gain.exponentialRampToValueAtTime(0.0001, t + d + 0.5);
    for (const [type, mul, lvl] of [['triangle', 1, 1], ['sine', 2, 0.25], ['sine', 3.01, 0.06]]) {
      const o = ctx.createOscillator();
      o.type = type;
      o.frequency.value = f * mul;
      const og = ctx.createGain();
      og.gain.value = lvl;
      o.connect(og).connect(lp);
      o.start(t);
      o.stop(t + d + 0.6);
    }
    lp.connect(g);
    send(g, 0.9, 0.35, 0.5);
  }

  // --- crystalline bells: two-operator FM, inharmonic partial for "glass"
  const bell = (note, t, level, dur, bus = music) => {
    const f = hz(note);
    const out = ctx.createGain();
    out.gain.setValueAtTime(0.0001, t);
    out.gain.exponentialRampToValueAtTime(level * 0.2, t + 0.004);
    out.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    const car = ctx.createOscillator();
    car.frequency.value = f;
    const mod = ctx.createOscillator();
    mod.frequency.value = f * 3.5;
    const idx = ctx.createGain();
    idx.gain.setValueAtTime(f * 1.6, t);
    idx.gain.exponentialRampToValueAtTime(f * 0.05, t + 0.9);
    mod.connect(idx).connect(car.frequency);
    const p2 = ctx.createOscillator();
    p2.frequency.value = f * 2.756;
    const p2g = ctx.createGain();
    p2g.gain.setValueAtTime(0.18, t);
    p2g.gain.exponentialRampToValueAtTime(0.0001, t + dur * 0.5);
    p2.connect(p2g).connect(out);
    car.connect(out);
    for (const o of [car, mod, p2]) {
      o.start(t);
      o.stop(t + dur + 0.05);
    }
    send(out, 0.85, 0.6, 0.4, bus);
  };
  for (const b of SCORE.bells) b.notes.forEach((n, i) => bell(n, b.t + i * 0.012, b.level, b.dur));

  // --- sound design ------------------------------------------------------
  const fx = SCORE.sfx;
  // rising texture during the orbit
  {
    const { t0, t1 } = fx.riser;
    const src = ctx.createBufferSource();
    src.buffer = noise;
    src.loop = true;
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.Q.value = 2.2;
    bp.frequency.setValueAtTime(300, t0);
    bp.frequency.exponentialRampToValueAtTime(5200, t1);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(0.12, t1 - 0.05);
    g.gain.exponentialRampToValueAtTime(0.0001, t1 + 0.2);
    src.connect(bp).connect(g);
    send(g, 0.9, 0.4, 0, sfxBus);
    src.start(t0);
    src.stop(t1 + 0.25);
    const o = ctx.createOscillator();
    o.type = 'sine';
    o.frequency.setValueAtTime(hz('B4'), t0);
    o.frequency.exponentialRampToValueAtTime(hz('B5'), t1);
    const og = ctx.createGain();
    og.gain.setValueAtTime(0.0001, t0);
    og.gain.exponentialRampToValueAtTime(0.025, t1 - 0.1);
    og.gain.exponentialRampToValueAtTime(0.0001, t1 + 0.1);
    o.connect(og);
    send(og, 0.6, 0.6, 0, sfxBus);
    o.start(t0);
    o.stop(t1 + 0.15);
  }
  // rounded stereo whoosh for the ribbon sweep (pans with the glass)
  {
    const { t, dur, pan } = fx.whoosh;
    const t0 = t - dur * 0.6;
    const t1 = t + dur * 0.4;
    const src = ctx.createBufferSource();
    src.buffer = noise;
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.Q.value = 0.9;
    bp.frequency.setValueAtTime(380, t0);
    bp.frequency.exponentialRampToValueAtTime(2400, t);
    bp.frequency.exponentialRampToValueAtTime(700, t1);
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 5200;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(0.5, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t1);
    const p = ctx.createStereoPanner();
    p.pan.setValueAtTime(pan[0], t0);
    p.pan.linearRampToValueAtTime(pan[1], t1);
    src.connect(bp).connect(lp).connect(g).connect(p);
    send(p, 1.0, 0.35, 0, sfxBus);
    src.start(t0, 0.7, dur + 0.1);
  }
  // brief movement accent for the letter pass: short tonal swish + tick
  {
    const { t, dur } = fx.accent;
    const src = ctx.createBufferSource();
    src.buffer = noise;
    const hp = ctx.createBiquadFilter();
    hp.type = 'highpass';
    hp.frequency.setValueAtTime(1200, t - dur * 0.5);
    hp.frequency.exponentialRampToValueAtTime(5000, t + dur * 0.5);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t - dur * 0.5);
    g.gain.exponentialRampToValueAtTime(0.22, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur * 0.5);
    const p = ctx.createStereoPanner();
    p.pan.setValueAtTime(-0.4, t - dur * 0.5);
    p.pan.linearRampToValueAtTime(0.4, t + dur * 0.5);
    src.connect(hp).connect(g).connect(p);
    send(p, 1.0, 0.3, 0, sfxBus);
    src.start(t - dur * 0.5, 1.4, dur + 0.05);
    bell('E6', t, 0.12, 0.6, sfxBus);
  }
  // reverse swell into the title lock
  {
    const { t0, t1 } = fx.reverseSwell;
    const src = ctx.createBufferSource();
    src.buffer = noise;
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.Q.value = 1.2;
    bp.frequency.setValueAtTime(900, t0);
    bp.frequency.exponentialRampToValueAtTime(6000, t1);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(0.16, t1 - 0.01);
    g.gain.linearRampToValueAtTime(0.0, t1);
    src.connect(bp).connect(g);
    send(g, 0.8, 0.5, 0, sfxBus);
    src.start(t0, 2.0, t1 - t0 + 0.02);
  }
  // soft crystalline resolution for the final star highlight
  {
    const { t } = fx.shimmer;
    ['D7', 'A6', 'F#7', 'E7'].forEach((n, i) => {
      const tt = t + i * 0.055;
      const o = ctx.createOscillator();
      o.type = 'sine';
      o.frequency.value = hz(n) * (1 + (i - 1.5) * 0.0015);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, tt);
      g.gain.exponentialRampToValueAtTime(0.045, tt + 0.01);
      g.gain.exponentialRampToValueAtTime(0.0001, tt + 1.6);
      const p = ctx.createStereoPanner();
      p.pan.value = (i - 1.5) * 0.35;
      o.connect(g).connect(p);
      send(p, 0.7, 0.8, 0.35, sfxBus);
      o.start(tt);
      o.stop(tt + 1.7);
    });
  }

  const buf = await ctx.startRendering();

  // Peak-normalise to the configured ceiling and apply the final fade.
  let peak = 0;
  for (let c = 0; c < buf.numberOfChannels; c++) {
    const d = buf.getChannelData(c);
    for (let i = 0; i < d.length; i++) peak = Math.max(peak, Math.abs(d[i]));
  }
  const target = Math.pow(10, AUDIO.masterPeakDb / 20);
  const gain = peak > 0 ? target / peak : 1;
  const fadeStart = Math.floor((12.0 - TIMING.fadeOut) * sr);
  for (let c = 0; c < buf.numberOfChannels; c++) {
    const d = buf.getChannelData(c);
    for (let i = 0; i < d.length; i++) {
      let g = gain;
      if (i >= fadeStart) {
        const x = (i - fadeStart) / (d.length - fadeStart);
        g *= Math.cos((x * Math.PI) / 2) ** 2;
      }
      d[i] *= g;
    }
  }
  return buf;
}

export function encodeWav(buf) {
  const ch = buf.numberOfChannels;
  const n = buf.length;
  const sr = buf.sampleRate;
  const bytes = new ArrayBuffer(44 + n * ch * 2);
  const v = new DataView(bytes);
  const str = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  str(0, 'RIFF');
  v.setUint32(4, 36 + n * ch * 2, true);
  str(8, 'WAVE');
  str(12, 'fmt ');
  v.setUint32(16, 16, true);
  v.setUint16(20, 1, true);
  v.setUint16(22, ch, true);
  v.setUint32(24, sr, true);
  v.setUint32(28, sr * ch * 2, true);
  v.setUint16(32, ch * 2, true);
  v.setUint16(34, 16, true);
  str(36, 'data');
  v.setUint32(40, n * ch * 2, true);
  const chans = [...Array(ch)].map((_, c) => buf.getChannelData(c));
  let o = 44;
  for (let i = 0; i < n; i++) {
    for (let c = 0; c < ch; c++) {
      const s = Math.max(-1, Math.min(1, chans[c][i]));
      v.setInt16(o, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      o += 2;
    }
  }
  return new Uint8Array(bytes);
}
