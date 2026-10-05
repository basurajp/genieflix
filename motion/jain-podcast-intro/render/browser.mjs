// Shared: tiny static server + headless Chromium page running index.html?render=1.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.ttf': 'font/ttf', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml' };

export function serve(port = 0) {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      const rel = decodeURIComponent(req.url.split('?')[0]);
      const file = path.join(ROOT, rel === '/' ? 'index.html' : rel);
      if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
        res.writeHead(404);
        return res.end();
      }
      res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream' });
      fs.createReadStream(file).pipe(res);
    });
    srv.listen(port, '127.0.0.1', () => resolve(srv));
  });
}

async function loadPlaywright() {
  try {
    return await import('playwright');
  } catch {
    // fall back to a global install (npm i -g playwright)
    const require = createRequire(import.meta.url);
    const { execSync } = await import('node:child_process');
    const globalRoot = execSync('npm root -g').toString().trim();
    return require(path.join(globalRoot, 'playwright'));
  }
}

export async function openRenderer({ gpu = false } = {}) {
  const srv = await serve();
  const port = srv.address().port;
  const { chromium } = await loadPlaywright();
  const args = gpu
    ? ['--ignore-gpu-blocklist', '--enable-gpu-rasterization']
    : ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
  const browser = await chromium.launch({ args });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('pageerror', (e) => console.error('[page error]', e.message));
  page.on('console', (m) => {
    if (m.type() === 'error' || m.type() === 'warning') console.error('[page]', m.text());
  });
  await page.goto(`http://127.0.0.1:${port}/index.html?render=1`);
  // fail fast if the page throws while building the scene
  const failed = new Promise((_, reject) => page.once('pageerror', reject));
  await Promise.race([page.waitForFunction(() => window.__ready === true, null, { timeout: 300000 }), failed]).catch(async (e) => {
    await browser.close();
    srv.close();
    throw e;
  });
  const close = async () => {
    await browser.close();
    srv.close();
  };
  return { page, close };
}

export async function grabPNG(page) {
  const url = await page.evaluate(() => document.getElementById('stage').toDataURL('image/png'));
  return Buffer.from(url.slice(url.indexOf(',') + 1), 'base64');
}
