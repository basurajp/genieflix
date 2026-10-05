// Full export: 720 frames (1920x1080, 60 fps, adaptive motion blur) + the
// synthesised cue -> H.264/AAC MP4.
//
//   node render/export.mjs                 # render everything, then encode
//   node render/export.mjs --workers 2     # split frames across browsers
//   node render/export.mjs --encode-only   # re-mux from existing frames/
//   node render/export.mjs --gpu           # use the host GPU instead of SwiftShader
//
// Frames already on disk are skipped, so an interrupted export resumes.
import fs from 'node:fs';
import path from 'node:path';
import { spawn, execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { openRenderer, grabPNG, ROOT } from './browser.mjs';

const argv = process.argv.slice(2);
const flag = (k) => argv.includes(k);
const val = (k, d) => (argv.includes(k) ? argv[argv.indexOf(k) + 1] : d);

const FRAMES = 720;
const outDir = path.resolve(val('--out', path.join(ROOT, 'out')));
const frameDir = path.join(outDir, 'frames');
const wavPath = path.join(outDir, 'jain-podcast-intro.wav');
const mp4Path = path.join(outDir, 'jain-podcast-intro.mp4');
fs.mkdirSync(frameDir, { recursive: true });

const framePath = (i) => path.join(frameDir, `f${String(i).padStart(4, '0')}.png`);

async function worker(indices, label) {
  const { page, close } = await openRenderer({ gpu: flag('--gpu') });
  const t0 = Date.now();
  let done = 0;
  for (const i of indices) {
    const k = await page.evaluate((f) => window.__intro.renderFrame(f), i);
    fs.writeFileSync(framePath(i), await grabPNG(page));
    done++;
    if (done % 10 === 0 || done === indices.length) {
      const per = (Date.now() - t0) / done / 1000;
      console.log(`[${label}] frame ${i} (sub ${k})  ${done}/${indices.length}  ${per.toFixed(2)} s/frame  eta ${((indices.length - done) * per / 60).toFixed(1)} min`);
    }
  }
  await close();
}

async function writeAudio() {
  const { page, close } = await openRenderer({ gpu: flag('--gpu') });
  const b64 = await page.evaluate(() => window.__intro.wavBase64());
  fs.writeFileSync(wavPath, Buffer.from(b64, 'base64'));
  await close();
  console.log('audio ->', path.relative(ROOT, wavPath));
}

if (process.env.EXPORT_WORKER) {
  // child process: render the frame list given on argv
  const list = JSON.parse(process.env.EXPORT_WORKER);
  await worker(list, `w${process.env.EXPORT_WORKER_ID}`);
  process.exit(0);
}

if (!flag('--encode-only')) {
  const todo = [];
  for (let i = 0; i < FRAMES; i++) if (!fs.existsSync(framePath(i))) todo.push(i);
  console.log(`${FRAMES - todo.length} frames on disk, ${todo.length} to render`);
  const n = Math.max(1, Number(val('--workers', 1)));
  if (todo.length) {
    const lists = Array.from({ length: n }, () => []);
    todo.forEach((f, i) => lists[i % n].push(f)); // interleave: heavy shots spread evenly
    const self = fileURLToPath(import.meta.url);
    await Promise.all(
      lists.map(
        (list, w) =>
          new Promise((resolve, reject) => {
            const p = spawn(process.execPath, [self, ...argv], {
              env: { ...process.env, EXPORT_WORKER: JSON.stringify(list), EXPORT_WORKER_ID: String(w) },
              stdio: 'inherit',
            });
            p.on('exit', (code) => (code === 0 ? resolve() : reject(new Error(`worker ${w} exited ${code}`))));
          }),
      ),
    );
  }
  await writeAudio();
}

for (let i = 0; i < FRAMES; i++) if (!fs.existsSync(framePath(i))) throw new Error(`missing frame ${i}`);

execFileSync(
  'ffmpeg',
  [
    '-y', '-hide_banner', '-loglevel', 'error',
    '-framerate', '60', '-i', path.join(frameDir, 'f%04d.png'),
    '-i', wavPath,
    '-map', '0:v', '-map', '1:a',
    '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-profile:v', 'high', '-level', '4.2',
    '-tune', 'film', '-g', '120', '-bf', '2',
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
    '-c:a', 'aac', '-b:a', '320k', '-ar', '48000',
    '-t', '12', '-movflags', '+faststart',
    mp4Path,
  ],
  { stdio: 'inherit' },
);
console.log('video ->', path.relative(ROOT, mp4Path));
