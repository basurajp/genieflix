#!/usr/bin/env node
// Export driver: serves the project, drives headless Chromium (WebGL via SwiftShader or a GPU),
// streams raw frames into ffmpeg, renders the score offline and muxes the MP4.
//
//   node render/render.mjs video  [--workers 2] [--scale 1]   full 1920x1080 60 fps MP4
//   node render/render.mjs stills 0.5,2.4,7.0 [--scale 0.5] [--nomb] [--out renders/stills]
//   node render/render.mjs audio                               score WAV + loudness report
//   node render/render.mjs check                               camera clearance + plan view
//   node render/render.mjs qa [file.mp4]                       cyan coverage + levels per 0.5 s
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn, execSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, 'renders');
const FPS = 60, DURATION = 12, FRAMES = FPS * DURATION;

const args = process.argv.slice(2);
const cmd = args[0] || 'video';
const opt = (name, def) => { const i = args.indexOf('--' + name); return i < 0 ? def : (args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true); };

async function loadPlaywright() {
  try { return await import('playwright'); } catch {}
  const g = execSync('npm root -g').toString().trim();
  return import(pathToFileURL(path.join(g, 'playwright', 'index.mjs')).href);
}

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.ttf': 'font/ttf', '.png': 'image/png', '.svg': 'image/svg+xml', '.wav': 'audio/wav' };

function ffmpeg(argv) {
  const p = spawn('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', ...argv], { stdio: ['pipe', 'inherit', 'inherit'] });
  p.done = new Promise((res, rej) => p.on('close', (c) => (c === 0 ? res() : rej(new Error('ffmpeg exited ' + c)))));
  return p;
}
const YUV = ['-vf', 'vflip,scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p',
  '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv'];

function readBody(req) {
  return new Promise((res) => { const chunks = []; req.on('data', (c) => chunks.push(c)); req.on('end', () => res(Buffer.concat(chunks))); });
}

function startServer(handlers) {
  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, 'http://x');
    if (req.method === 'POST') {
      const body = await readBody(req);
      try { await handlers.post(url, body); res.writeHead(200).end('ok'); } catch (e) { console.error(e); res.writeHead(500).end(String(e)); }
      return;
    }
    const file = path.join(ROOT, decodeURIComponent(url.pathname));
    if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404).end(); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise((res) => server.listen(0, '127.0.0.1', () => res(server)));
}

async function openPage(browser, port, scale) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('[page]', m.text()); });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await page.goto(`http://127.0.0.1:${port}/render/export.html?scale=${scale}`);
  await page.waitForFunction('window.__ready === true', null, { timeout: 120000 });
  return page;
}

async function launch(pw) {
  return pw.chromium.launch({
    headless: true,
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-gpu-sandbox'],
  });
}

// Cyan coverage / level report straight from the encoded MP4 (no browser needed).
function qa(file) {
  const W = 480, H = 270;
  for (let t = 0.25; t < DURATION; t += 0.5) {
    const raw = execSync(`ffmpeg -hide_banner -loglevel error -ss ${t} -i "${file}" -frames:v 1 -vf scale=${W}:${H} -f rawvideo -pix_fmt rgb24 -`, { maxBuffer: 1 << 24 });
    let cyan = 0, dark = 0, sum = 0;
    for (let i = 0; i < raw.length; i += 3) {
      const r = raw[i], g = raw[i + 1], b = raw[i + 2];
      const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
      sum += (r + g + b) / 3;
      if (mx < 12) dark++;
      if (mx > 90 && g >= b && b > r && (mx - mn) / mx > 0.45) cyan++;
    }
    const n = raw.length / 3;
    console.log(`t=${t.toFixed(2).padStart(5)}  cyan ${(100 * cyan / n).toFixed(1).padStart(5)}%   near-black ${(100 * dark / n).toFixed(0).padStart(3)}%   mean ${(sum / n).toFixed(1)}`);
  }
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  if (cmd === 'qa') return qa(path.resolve(args[1] || path.join(OUT, 'jain-podcast-intro_1080p60.mp4')));
  const pw = await loadPlaywright();
  const scale = Number(opt('scale', 1));
  const writers = new Map();
  let audioDone = null;
  const server = await startServer({
    async post(url, body) {
      const parts = url.pathname.split('/').filter(Boolean);
      if (parts[0] === 'still') {
        const w = url.searchParams.get('w'), h = url.searchParams.get('h');
        const dir = path.resolve(ROOT, opt('out', 'renders/stills'));
        fs.mkdirSync(dir, { recursive: true });
        const p = ffmpeg(['-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${w}x${h}`, '-i', '-', '-vf', 'vflip', path.join(dir, decodeURIComponent(parts[1]) + '.png')]);
        p.stdin.end(body);
        await p.done;
      } else if (parts[0] === 'frame') {
        const w = writers.get(parts[1]);
        if (!w.stdin.write(body)) await new Promise((r) => w.stdin.once('drain', r));
      } else if (parts[0] === 'audio') {
        fs.writeFileSync(path.join(OUT, 'score.wav'), body);
        audioDone?.();
      }
    },
  });
  const port = server.address().port;
  const browser = await launch(pw);

  try {
    if (cmd === 'stills') {
      const times = String(args[1]).split(',').map(Number);
      const page = await openPage(browser, port, scale);
      for (const t of times) {
        const t0 = Date.now();
        const info = await page.evaluate(([t, mb]) => window.__exp.still(t, 't' + t.toFixed(3).padStart(6, '0'), mb), [t, !opt('nomb', false)]);
        console.log(`still t=${t} samples=${info.samples} ${Date.now() - t0}ms`);
      }
    } else if (cmd === 'audio') {
      const page = await openPage(browser, port, 0.25);
      const info = await page.evaluate(() => window.__exp.audio());
      console.log('score rendered', info);
      const r = execSync(`ffmpeg -hide_banner -nostats -i "${path.join(OUT, 'score.wav')}" -af ebur128=peak=true -f null - 2>&1 | tail -14`).toString();
      console.log(r);
    } else if (cmd === 'budget') {
      const page = await openPage(browser, port, 0.25);
      const n = await page.evaluate(() => window.__exp.budget());
      const sum = n.reduce((a, b) => a + b, 0);
      console.log(`subframes: ${sum} for ${n.length} frames (avg ${(sum / n.length).toFixed(2)})`);
      for (let s = 0; s < 12; s++) console.log(`${String(s).padStart(2)}s ${n.slice(s * 60, s * 60 + 60).join('')}`);
    } else if (cmd === 'check') {
      const page = await openPage(browser, port, 0.25);
      const data = await page.evaluate(() => window.__exp.samples(1 / 60));
      fs.writeFileSync(path.join(OUT, 'samples.json'), JSON.stringify(data));
      const { checkPath } = await import('./check.mjs');
      checkPath(data, OUT);
    } else if (cmd === 'video') {
      const workers = Number(opt('workers', 2));
      const range = String(opt('range', `0:${FRAMES}`)).split(':').map(Number);
      const n = range[1] - range[0];
      const W = Math.round(1920 * scale), H = Math.round(1080 * scale);
      const segs = [];
      const pages = [];
      for (let k = 0; k < workers; k++) {
        const a = range[0] + Math.floor((n * k) / workers), b = range[0] + Math.floor((n * (k + 1)) / workers);
        const seg = path.join(OUT, `seg${k}.mp4`);
        segs.push(seg);
        const p = ffmpeg(['-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${W}x${H}`, '-r', String(FPS), '-i', '-', ...YUV,
          '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-profile:v', 'high', '-g', '60', '-bf', '2', seg]);
        writers.set(String(k), p);
        pages.push({ k, a, b, p });
      }
      // separate browser per worker so SwiftShader threads spread across cores
      const t0 = Date.now();
      await Promise.all(pages.map(async (w) => {
        const br = w.k === 0 ? browser : await launch(pw);
        const page = await openPage(br, port, scale);
        const step = 30;
        for (let i = w.a; i < w.b; i += step) {
          const log = await page.evaluate(([k, i0, i1]) => window.__exp.frames(String(k), i0, i1, true), [w.k, i, Math.min(w.b, i + step)]);
          const ms = log.reduce((s, l) => s + l[2], 0) / log.length;
          console.log(`worker ${w.k}: frames ${i}-${Math.min(w.b, i + step) - 1} avg ${ms.toFixed(0)}ms, samples ${log.map((l) => l[1]).join('')}  [${((Date.now() - t0) / 1000).toFixed(0)}s]`);
        }
        w.p.stdin.end();
        await w.p.done;
        if (br !== browser) await br.close();
      }));
      // score
      const ap = await openPage(browser, port, 0.25);
      const done = new Promise((r) => (audioDone = r));
      const ainfo = await ap.evaluate(() => window.__exp.audio());
      await done;
      console.log('audio peak', ainfo.peak.toFixed(3));
      const list = path.join(OUT, 'segments.txt');
      fs.writeFileSync(list, segs.map((s) => `file '${s}'`).join('\n'));
      const out = path.join(OUT, String(opt('name', 'jain-podcast-intro_1080p60.mp4')));
      const mux = ffmpeg(['-f', 'concat', '-safe', '0', '-i', list, '-i', path.join(OUT, 'score.wav'),
        '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-t', String(n / FPS),
        '-movflags', '+faststart', out]);
      mux.stdin.end();
      await mux.done;
      for (const s of segs) fs.unlinkSync(s);
      fs.unlinkSync(list);
      console.log('wrote', out, `in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
  } finally {
    await browser.close();
    server.close();
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
