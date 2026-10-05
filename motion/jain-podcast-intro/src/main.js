// Browser preview: real-time playback of the same deterministic engine, with the offline-
// rendered score played in sync. Controls live outside the canvas, so they never reach a frame.
import { createEngine } from './engine.js';
import { renderScore } from './audio/score.js';
import { FORMAT } from './config.js';

const $ = (id) => document.getElementById(id);
const canvas = $('c');
const ui = { play: $('play'), replay: $('replay'), sound: $('sound'), scrub: $('scrub'), time: $('time'), loading: $('loading') };

const params = new URLSearchParams(location.search);
const scale = Math.min(1, Number(params.get('scale') || (canvas.clientWidth * devicePixelRatio) / FORMAT.width));
const engine = await createEngine(canvas, { width: FORMAT.width, height: FORMAT.height, pixelRatio: Math.max(0.5, scale) });
canvas.style.width = '100%';
canvas.style.height = '100%';

let actx = null, buffer = null, src = null, gain = null;
let playing = false, soundOn = true, t = 0, startWall = 0, startT = 0;

async function ensureAudio() {
  if (!buffer) buffer = await renderScore();
  if (!actx) {
    actx = new AudioContext({ sampleRate: buffer.sampleRate });
    gain = actx.createGain();
    gain.connect(actx.destination);
  }
  if (actx.state === 'suspended') await actx.resume();
}

function startAudio(at) {
  stopAudio();
  if (!actx || !buffer) return;
  src = actx.createBufferSource();
  src.buffer = buffer;
  src.connect(gain);
  gain.gain.value = soundOn ? 1 : 0;
  src.start(0, Math.min(at, buffer.duration - 0.01));
}
function stopAudio() { if (src) { try { src.stop(); } catch {} src.disconnect(); src = null; } }

function clock() {
  return actx && src ? startT + (actx.currentTime - startWall) : startT + (performance.now() / 1000 - startWall);
}

async function play(from = t) {
  await ensureAudio();
  t = from >= FORMAT.duration - 0.02 ? 0 : from;
  startT = t;
  startWall = actx ? actx.currentTime : performance.now() / 1000;
  startAudio(t);
  playing = true;
  ui.play.textContent = 'Pause';
}
function pause() { playing = false; t = clock(); stopAudio(); ui.play.textContent = 'Play'; }

function frame() {
  if (playing) {
    t = clock();
    if (t >= FORMAT.duration) { t = FORMAT.duration; pause(); }
    ui.scrub.value = t;
  }
  engine.renderFrame(Math.min(t, FORMAT.duration - 1 / FORMAT.fps));
  ui.time.textContent = `${t.toFixed(2)} / ${FORMAT.duration.toFixed(2)}`;
  requestAnimationFrame(frame);
}

ui.play.onclick = () => (playing ? pause() : play());
ui.replay.onclick = () => play(0);
ui.sound.onclick = () => {
  soundOn = !soundOn;
  ui.sound.setAttribute('aria-pressed', String(soundOn));
  ui.sound.textContent = soundOn ? 'Sound on' : 'Sound off';
  if (gain) gain.gain.value = soundOn ? 1 : 0;
};
ui.scrub.oninput = () => { const was = playing; if (was) pause(); t = Number(ui.scrub.value); if (was) play(t); };

for (const k of Object.values(ui)) if (k.disabled !== undefined) k.disabled = false;
ui.loading.remove();
requestAnimationFrame(frame);
