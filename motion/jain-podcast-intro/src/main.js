// Player + offline render hooks.
//   index.html            interactive preview (Play / Replay / Sound / scrub)
//   index.html?render=1   deterministic frame server used by render/export.mjs
import * as THREE from 'three';
import { FORMAT, TIMING, POST } from './config.js';
import { Pipeline } from './post.js';
import { buildScene } from './scene.js';
import { renderCue, encodeWav } from './audio.js';
import { smoothstep } from './math.js';

const params = new URLSearchParams(location.search);
const RENDER = params.has('render');
const HALF = params.get('q') === 'half';

const W = HALF ? FORMAT.width / 2 : FORMAT.width;
const H = HALF ? FORMAT.height / 2 : FORMAT.height;

const canvas = document.getElementById('stage');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, preserveDrawingBuffer: RENDER, powerPreference: 'high-performance' });
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
renderer.toneMapping = THREE.NoToneMapping;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.setClearColor(0x000000, 1);

const pipeline = new Pipeline(renderer, W, H);
const status = document.getElementById('status');
const setStatus = (s) => status && (status.textContent = s);

setStatus('Loading font and building scene…');
const world = await buildScene(renderer, pipeline);
const { scene, camera, pose } = world;

const fadeAt = (t) => 1 - smoothstep(FORMAT.duration - TIMING.fadeOut, FORMAT.duration, t);

function draw(t, { subframes = 1, frameIndex = 0 } = {}) {
  pipeline.frame(scene, camera, t, {
    subframes,
    shutter: POST.shutter,
    fps: FORMAT.fps,
    fade: fadeAt(t),
    frameIndex,
    renderAt: pose,
  });
}

// Warm up shaders (glass programs compile lazily).
pose(0);
renderer.compile(scene, camera);
draw(0);

if (RENDER) {
  let cueBuf = null;
  window.__intro = {
    info: world.info,
    // Render frame i (0..719) with adaptive motion blur. Returns the sub-frame count.
    renderFrame(i, { motionBlur = true } = {}) {
      const t = i / FORMAT.fps;
      let k = 1;
      if (motionBlur) {
        const px = world.motionPx(t, POST.shutter / FORMAT.fps);
        k = Math.min(POST.maxSubframes, Math.max(1, Math.ceil(px / POST.blurPxPerSubframe)));
      }
      draw(t, { subframes: k, frameIndex: i });
      return k;
    },
    renderTime(t) {
      draw(t, { subframes: 1 });
    },
    clearance: (t) => world.clearance(t),
    async wavBase64() {
      cueBuf = cueBuf || (await renderCue());
      const bytes = encodeWav(cueBuf);
      let s = '';
      for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
      return btoa(s);
    },
  };
  window.__ready = true;
} else {
  // ---------------- interactive preview -----------------
  const btnPlay = document.getElementById('play');
  const btnReplay = document.getElementById('replay');
  const btnSound = document.getElementById('sound');
  const scrub = document.getElementById('scrub');
  const clock = document.getElementById('clock');

  setStatus('Synthesising the music cue…');
  const cue = await renderCue();
  const ac = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: cue.sampleRate });
  const out = ac.createGain();
  out.connect(ac.destination);
  let soundOn = true;
  let playing = false;
  let src = null;
  let startAt = 0; // ac time at which t = 0
  let pausedT = 0;

  const now = () => (playing ? ac.currentTime - startAt : pausedT);
  const fmt = (t) => t.toFixed(2).padStart(5, '0') + ' s';

  function startFrom(t) {
    if (src) {
      src.onended = null;
      src.stop();
    }
    src = ac.createBufferSource();
    src.buffer = cue;
    src.connect(out);
    startAt = ac.currentTime - t;
    src.start(ac.currentTime, Math.min(t, cue.duration - 0.001));
    playing = true;
    btnPlay.textContent = 'Pause';
  }
  function pause() {
    pausedT = Math.min(FORMAT.duration, now());
    if (src) {
      src.onended = null;
      src.stop();
      src = null;
    }
    playing = false;
    btnPlay.textContent = 'Play';
  }

  btnPlay.onclick = async () => {
    await ac.resume();
    if (playing) pause();
    else startFrom(pausedT >= FORMAT.duration - 0.01 ? 0 : pausedT);
  };
  btnReplay.onclick = async () => {
    await ac.resume();
    pausedT = 0;
    startFrom(0);
  };
  btnSound.onclick = () => {
    soundOn = !soundOn;
    out.gain.value = soundOn ? 1 : 0;
    btnSound.textContent = soundOn ? 'Sound: on' : 'Sound: off';
    btnSound.setAttribute('aria-pressed', String(soundOn));
  };
  scrub.oninput = () => {
    const t = (Number(scrub.value) / 1000) * FORMAT.duration;
    if (playing) pause();
    pausedT = t;
  };
  for (const b of [btnPlay, btnReplay, btnSound, scrub]) b.disabled = false;
  setStatus('');

  let lastDrawn = -1;
  function loop() {
    let t = now();
    if (playing && t >= FORMAT.duration) {
      pause();
      pausedT = FORMAT.duration;
      t = FORMAT.duration;
    }
    const tc = Math.min(t, FORMAT.duration - 1e-4);
    if (playing || tc !== lastDrawn) {
      draw(tc, { frameIndex: Math.floor(tc * FORMAT.fps) });
      lastDrawn = tc;
    }
    clock.textContent = fmt(Math.min(t, FORMAT.duration));
    if (playing) scrub.value = String(Math.round((tc / FORMAT.duration) * 1000));
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
}
