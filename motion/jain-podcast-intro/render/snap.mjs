// Dev/QA: render stills at given times (seconds) and a contact sheet.
//   node render/snap.mjs 0 1.2 2.4 ... [--blur] [--out dir] [--clearance]
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { openRenderer, grabPNG, ROOT } from './browser.mjs';

const argv = process.argv.slice(2);
const opt = (k) => argv.includes(k);
const outIdx = argv.indexOf('--out');
const out = outIdx >= 0 ? argv[outIdx + 1] : path.join(ROOT, 'snapshots');
const times = argv.filter((a, i) => !a.startsWith('--') && argv[i - 1] !== '--out').map(Number);
fs.mkdirSync(out, { recursive: true });

const { page, close } = await openRenderer();
console.log('layout', JSON.stringify(await page.evaluate(() => window.__intro.info)));
const files = [];
for (const t of times) {
  const t0 = Date.now();
  let k = 1;
  if (opt('--blur')) k = await page.evaluate((f) => window.__intro.renderFrame(f), Math.round(t * 60));
  else await page.evaluate((tt) => window.__intro.renderTime(tt), t);
  const f = path.join(out, `t${t.toFixed(2).padStart(5, '0')}.png`);
  fs.writeFileSync(f, await grabPNG(page));
  files.push(f);
  console.log(`t=${t.toFixed(2)} sub=${k} ${Date.now() - t0}ms`);
}
if (opt('--clearance')) {
  let worst = {};
  for (let f = 0; f <= 720; f += 2) {
    const c = await page.evaluate((t) => window.__intro.clearance(t), f / 60);
    for (const [k, v] of Object.entries(c)) if (!(k in worst) || v < worst[k].d) worst[k] = { d: v, t: f / 60 };
  }
  console.log('min camera clearance (units):');
  for (const [k, v] of Object.entries(worst)) console.log(`  ${k.padEnd(10)} ${v.d.toFixed(3)} at t=${v.t.toFixed(2)}`);
}
await close();
if (files.length > 1) {
  const cols = Math.min(4, files.length);
  const inputs = files.flatMap((f) => ['-i', f]);
  const n = files.length;
  const filter =
    files.map((_, i) => `[${i}:v]scale=480:-1,drawtext=text='${times[i].toFixed(2)}':x=8:y=8:fontcolor=white:fontsize=18[v${i}]`).join(';') +
    ';' + files.map((_, i) => `[v${i}]`).join('') + `xstack=inputs=${n}:layout=` +
    files.map((_, i) => `${(i % cols) ? Array.from({ length: i % cols }, () => 'w0').join('+') : '0'}_${Math.floor(i / cols) ? Array.from({ length: Math.floor(i / cols) }, () => 'h0').join('+') : '0'}`).join('|') +
    (n < cols * Math.ceil(n / cols) ? ':fill=black' : '') + '[out]';
  execFileSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', ...inputs, '-filter_complex', filter, '-map', '[out]', path.join(out, 'sheet.png')]);
  console.log('sheet', path.join(out, 'sheet.png'));
}
