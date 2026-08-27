#!/usr/bin/env node
/**
 * Factory runner: watches queue/, runs the voice + render pipeline on each job,
 * and serves the live dashboard. Usage: node factory/runner.mjs
 *
 * Folders are the state machine: building/ -> queue/ -> work/ -> done/|failed/.
 * One-writer rule: once a job is in queue/ or beyond, THIS process is the only
 * writer of its job.json. Creators (humans, scripts) own it only in building/.
 */

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';

const FACTORY_DIR = import.meta.dirname;
const REPO_ROOT = path.dirname(FACTORY_DIR);
const STATE_DIRS = ['building', 'queue', 'work', 'done', 'failed'];

const PORT = Number(process.env.PORT) || 4300;
const RENDER_CONCURRENCY = Math.max(1, Number(process.env.FACTORY_RENDER_CONCURRENCY) || 3);
const VOICE_CONCURRENCY = 1; // the local voice model wants the machine to itself
const SCAN_INTERVAL_MS = 3000;
const ERROR_TAIL_LINES = 40;
const TAIL_BUFFER_LINES = 200;

// ---------------------------------------------------------------- utilities

const nowIso = () => new Date().toISOString();

function log(msg) {
  console.log(`${nowIso()} ${msg}`);
}

function stateDir(state, slug = '') {
  return path.join(FACTORY_DIR, state, slug);
}

function nameOk(name) {
  return Boolean(name) && !name.startsWith('.') && !name.includes('..') && !/[/\\]/.test(name);
}

function listJobDirs(state) {
  let entries;
  try {
    entries = fs.readdirSync(stateDir(state), { withFileTypes: true });
  } catch {
    return [];
  }
  return entries
    .filter((e) => e.isDirectory() && nameOk(e.name) && !e.name.includes('.stale-'))
    .filter((e) => fs.existsSync(path.join(stateDir(state), e.name, 'job.json')))
    .map((e) => e.name)
    .sort();
}

function readJob(jobDir) {
  try {
    return JSON.parse(fs.readFileSync(path.join(jobDir, 'job.json'), 'utf8'));
  } catch {
    return null;
  }
}

function baseJob(slug) {
  return { slug, title: slug, status: 'queued', created: nowIso(), updated: nowIso(), error: null, output: null, attempts: 0 };
}

/** Write job.json atomically, in the canonical key order, bumping `updated`. */
function writeJob(jobDir, job) {
  const { slug, title, status, created, error, output, attempts, updated: _drop, ...rest } = job;
  const normalized = {
    slug,
    title: title ?? slug,
    status,
    created: created ?? nowIso(),
    updated: nowIso(),
    error: error ?? null,
    output: output ?? null,
    attempts: attempts ?? 0,
    ...rest,
  };
  const file = path.join(jobDir, 'job.json');
  const tmp = `${file}.tmp`;
  fs.writeFileSync(tmp, `${JSON.stringify(normalized, null, 2)}\n`);
  fs.renameSync(tmp, file);
  return normalized;
}

/** Move a job dir to another state folder; shunts a conflicting leftover aside. */
function moveJobDir(src, targetState, slug) {
  const dst = stateDir(targetState, slug);
  if (fs.existsSync(dst)) {
    const aside = `${dst}.stale-${Date.now()}`;
    fs.renameSync(dst, aside);
    log(`WARN ${targetState}/${slug} already existed — moved aside to ${path.basename(aside)}`);
  }
  fs.renameSync(src, dst);
  return dst;
}

/** ready-to-post destination from pipeline config (config.json, else example). */
function readyToPostDir() {
  let cfg = {};
  for (const name of ['config.json', 'config.example.json']) {
    const p = path.join(REPO_ROOT, 'pipeline', name);
    if (fs.existsSync(p)) {
      try { cfg = JSON.parse(fs.readFileSync(p, 'utf8')); } catch { /* fall back to default */ }
      break;
    }
  }
  let p = typeof cfg.ready_to_post_dir === 'string' && cfg.ready_to_post_dir ? cfg.ready_to_post_dir : 'factory/ready-to-post';
  if (p === '~' || p.startsWith('~/') || p.startsWith('~\\')) {
    const home = process.env.HOME || process.env.USERPROFILE || '';
    p = path.join(home, p.slice(1).replace(/^[/\\]/, ''));
  }
  return path.isAbsolute(p) ? p : path.join(REPO_ROOT, p);
}

/** python3 on posix; `py -3` then `python` on Windows. */
function pickPython() {
  if (process.platform !== 'win32') return { cmd: 'python3', pre: [] };
  for (const [cmd, pre] of [['py', ['-3']], ['python', []]]) {
    const r = spawnSync(cmd, [...pre, '--version'], { stdio: 'ignore', shell: false });
    if (!r.error && r.status === 0) return { cmd, pre };
  }
  return { cmd: 'python', pre: [] };
}
const PYTHON = pickPython();

class Semaphore {
  constructor(slots) {
    this.slots = slots;
    this.active = 0;
    this.waiters = [];
  }

  async acquire() {
    if (this.active < this.slots) {
      this.active += 1;
      return;
    }
    await new Promise((resolve) => this.waiters.push(resolve)); // slot handed over in release()
  }

  release() {
    const next = this.waiters.shift();
    if (next) next();
    else this.active = Math.max(0, this.active - 1);
  }
}

// ---------------------------------------------------------------- job engine

const voiceSem = new Semaphore(VOICE_CONCURRENCY);
const renderSem = new Semaphore(RENDER_CONCURRENCY);
const jobs = new Map(); // slug -> { slug, dir, child, running, cancelled, handled }
let paused = false;

/** Crash safety: anything left in work/ was interrupted mid-run — requeue it. */
function requeueStuckWork() {
  for (const slug of listJobDirs('work')) {
    const src = stateDir('work', slug);
    try {
      const job = readJob(src) ?? baseJob(slug);
      const was = job.status;
      job.status = 'queued';
      job.output = null;
      job.error = `requeued at startup: runner stopped while this job was ${was} in work/`;
      writeJob(src, job);
      moveJobDir(src, 'queue', slug);
      log(`requeued ${slug} (found in work/ at startup, was ${was})`);
    } catch (err) {
      log(`WARN could not requeue ${slug} from work/: ${err.message}`);
    }
  }
}

function scanQueue() {
  if (paused) return;
  const found = listJobDirs('queue')
    .map((slug) => ({ slug, job: readJob(stateDir('queue', slug)) }))
    .filter((e) => e.job)
    .sort((a, b) => String(a.job.created ?? '').localeCompare(String(b.job.created ?? '')));
  for (const { slug } of found) {
    if (jobs.has(slug)) continue;
    const state = { slug, dir: stateDir('queue', slug), child: null, running: null, cancelled: false, handled: false };
    jobs.set(slug, state);
    runJob(state)
      .catch((err) => log(`ERROR ${slug}: ${err.message}`))
      .finally(() => jobs.delete(slug));
  }
}

async function runJob(state) {
  const { slug } = state;
  const tail = [];

  await voiceSem.acquire();
  try {
    if (state.cancelled) return finishCancelled(state, tail);
    if (!fs.existsSync(path.join(state.dir, 'job.json'))) return; // removed by hand while waiting
    state.dir = moveJobDir(state.dir, 'work', slug);
    const job = readJob(state.dir) ?? baseJob(slug);
    job.status = 'voicing';
    job.error = null;
    job.output = null;
    writeJob(state.dir, job);
    log(`${slug}: voicing`);
    const code = await runPhase(state, 'voice', tail);
    if (state.cancelled) return finishCancelled(state, tail);
    if (code !== 0) return finishFailed(state, tail, `voice phase exited with code ${code}`);
  } finally {
    voiceSem.release();
  }

  const job = readJob(state.dir) ?? baseJob(slug);
  job.status = 'rendering';
  writeJob(state.dir, job);
  log(`${slug}: rendering`);

  await renderSem.acquire();
  try {
    if (state.cancelled) return finishCancelled(state, tail);
    const code = await runPhase(state, 'render', tail);
    if (state.cancelled) return finishCancelled(state, tail);
    if (code !== 0) return finishFailed(state, tail, `render phase exited with code ${code}`);
  } finally {
    renderSem.release();
  }

  finishDone(state, tail);
}

/** Spawn `make_reel.py --phase <phase>` for the job; resolves with the exit code. */
function runPhase(state, phase, tail) {
  return new Promise((resolve) => {
    const script = path.join(REPO_ROOT, 'pipeline', 'make_reel.py');
    const args = [...PYTHON.pre, script, '--project', state.dir, '--phase', phase];
    const child = spawn(PYTHON.cmd, args, {
      cwd: REPO_ROOT,
      stdio: ['ignore', 'pipe', 'pipe'],
      detached: process.platform !== 'win32', // own process group, so cancel kills ffmpeg/npx too
    });
    state.child = child;
    state.running = phase === 'voice' ? 'voicing' : 'rendering';

    const onData = (chunk) => {
      for (const line of chunk.toString().split(/\r?\n/)) {
        if (!line.trim()) continue;
        tail.push(line);
        if (tail.length > TAIL_BUFFER_LINES) tail.shift();
        process.stdout.write(`  [${state.slug}] ${line}\n`);
      }
    };
    child.stdout.on('data', onData);
    child.stderr.on('data', onData);

    const settle = (code) => {
      state.child = null;
      state.running = null;
      resolve(code);
    };
    child.on('error', (err) => {
      tail.push(`spawn error: ${err.message}`);
      settle(1);
    });
    child.on('close', (code, signal) => settle(signal ? 1 : (code ?? 1)));
  });
}

/** Kill a job's child process (and its whole process group where possible). */
function killChild(state) {
  const child = state.child;
  if (!child || child.exitCode !== null) return;
  try {
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], { stdio: 'ignore' });
    } else {
      process.kill(-child.pid, 'SIGTERM');
    }
  } catch {
    try { child.kill('SIGTERM'); } catch { /* already gone */ }
  }
  const hardKill = setTimeout(() => {
    try {
      if (process.platform === 'win32') child.kill('SIGKILL');
      else process.kill(-child.pid, 'SIGKILL');
    } catch { /* already gone */ }
  }, 5000);
  hardKill.unref?.();
  child.once('close', () => clearTimeout(hardKill));
}

function errorTail(tail, reason) {
  const lines = tail.slice(-ERROR_TAIL_LINES);
  return [reason, ...(lines.length ? ['', ...lines] : [])].join('\n').slice(-8000);
}

function finishFailed(state, tail, reason) {
  if (state.handled) return;
  state.handled = true;
  const job = readJob(state.dir) ?? baseJob(state.slug);
  job.status = 'failed';
  job.output = null;
  job.error = errorTail(tail, reason);
  writeJob(state.dir, job);
  state.dir = moveJobDir(state.dir, 'failed', state.slug);
  log(`${state.slug}: FAILED — ${reason}`);
}

function finishCancelled(state, tail, reason = 'cancelled by user') {
  if (state.handled) return;
  state.handled = true;
  const job = readJob(state.dir) ?? baseJob(state.slug);
  job.status = 'cancelled';
  job.output = null;
  job.error = errorTail(tail, reason);
  writeJob(state.dir, job);
  state.dir = moveJobDir(state.dir, 'failed', state.slug);
  log(`${state.slug}: cancelled`);
}

function finishDone(state, tail) {
  if (state.handled) return;
  const { slug } = state;
  const finalSrc = path.join(state.dir, 'final', `${slug}.mp4`);
  if (!fs.existsSync(finalSrc)) {
    return finishFailed(state, tail, `render reported success but final/${slug}.mp4 is missing`);
  }
  try {
    fs.mkdirSync(stateDir('output'), { recursive: true });
    fs.copyFileSync(finalSrc, stateDir('output', `${slug}.mp4`));
  } catch (err) {
    return finishFailed(state, tail, `could not copy final MP4 to output/: ${err.message}`);
  }
  try {
    const rtp = readyToPostDir();
    fs.mkdirSync(rtp, { recursive: true });
    fs.copyFileSync(finalSrc, path.join(rtp, `${slug}.mp4`));
  } catch (err) {
    log(`WARN ${slug}: could not copy to ready-to-post dir: ${err.message}`);
  }
  state.handled = true;
  const job = readJob(state.dir) ?? baseJob(slug);
  job.status = 'done';
  job.error = null;
  job.output = `output/${slug}.mp4`;
  writeJob(state.dir, job);
  state.dir = moveJobDir(state.dir, 'done', slug);
  log(`${slug}: done -> output/${slug}.mp4`);
}

// ---------------------------------------------------------------- HTTP API

function sendJson(res, status, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
  });
  res.end(body);
}

function collectJobs() {
  const out = [];
  const now = Date.now();
  for (const state of STATE_DIRS) {
    for (const name of listJobDirs(state)) {
      const job = readJob(stateDir(state, name));
      if (!job) continue;
      const updatedMs = Date.parse(job.updated ?? job.created ?? '');
      out.push({
        slug: job.slug ?? name,
        title: job.title ?? name,
        status: job.status ?? state,
        created: job.created ?? null,
        updated: job.updated ?? null,
        error: job.error ?? null,
        output: job.output ?? null,
        attempts: job.attempts ?? 0,
        folder: state,
        // seconds since the last status change (dashboard timers tick on top of this)
        elapsed: Number.isNaN(updatedMs) ? 0 : Math.max(0, Math.round((now - updatedMs) / 1000)),
      });
    }
  }
  out.sort((a, b) => String(a.created ?? '').localeCompare(String(b.created ?? '')));
  return out;
}

function currentState() {
  let voicing = 0;
  let rendering = 0;
  for (const s of jobs.values()) {
    if (s.running === 'voicing') voicing += 1;
    else if (s.running === 'rendering') rendering += 1;
  }
  return { paused, active: { voicing, rendering }, renderConcurrency: RENDER_CONCURRENCY };
}

function apiRetry(res, slug) {
  if (!nameOk(slug)) return sendJson(res, 400, { ok: false, error: 'bad slug' });
  for (const state of ['failed', 'done']) {
    const src = stateDir(state, slug);
    if (!fs.existsSync(path.join(src, 'job.json'))) continue;
    const job = readJob(src) ?? baseJob(slug);
    job.status = 'queued';
    job.error = null;
    job.output = null;
    job.attempts = (job.attempts ?? 0) + 1;
    writeJob(src, job);
    moveJobDir(src, 'queue', slug);
    log(`${slug}: retry from ${state}/ (attempt ${job.attempts + 1})`);
    return sendJson(res, 200, { ok: true, slug, status: 'queued' });
  }
  return sendJson(res, 404, { ok: false, error: `${slug} not found in failed/ or done/` });
}

function apiCancel(res, slug) {
  if (!nameOk(slug)) return sendJson(res, 400, { ok: false, error: 'bad slug' });
  const state = jobs.get(slug);
  if (state && !state.handled) {
    state.cancelled = true;
    if (state.child) {
      killChild(state); // runJob observes the exit and finishes the bookkeeping
      return sendJson(res, 200, { ok: true, slug, status: 'cancelling' });
    }
    finishCancelled(state, [], 'cancelled while waiting for a slot');
    return sendJson(res, 200, { ok: true, slug, status: 'cancelled' });
  }
  const src = stateDir('queue', slug);
  if (fs.existsSync(path.join(src, 'job.json'))) {
    const job = readJob(src) ?? baseJob(slug);
    job.status = 'cancelled';
    job.output = null;
    job.error = 'cancelled before start';
    writeJob(src, job);
    moveJobDir(src, 'failed', slug);
    log(`${slug}: cancelled (was queued)`);
    return sendJson(res, 200, { ok: true, slug, status: 'cancelled' });
  }
  return sendJson(res, 409, { ok: false, error: `${slug} is not queued or running` });
}

function serveDashboard(req, res) {
  const file = path.join(FACTORY_DIR, 'dashboard.html');
  let body;
  try {
    body = fs.readFileSync(file);
  } catch {
    res.writeHead(500, { 'Content-Type': 'text/plain' });
    return res.end('dashboard.html is missing next to runner.mjs');
  }
  res.writeHead(200, {
    'Content-Type': 'text/html; charset=utf-8',
    'Content-Length': body.length,
    'Cache-Control': 'no-store',
  });
  if (req.method === 'HEAD') return res.end();
  res.end(body);
}

/** Stream a file from output/ with HTTP Range support so <video> can seek. */
function serveOutput(req, res, rawName) {
  let name;
  try {
    name = decodeURIComponent(rawName);
  } catch {
    res.writeHead(400);
    return res.end('bad filename');
  }
  if (!nameOk(name)) {
    res.writeHead(400);
    return res.end('bad filename');
  }
  const file = path.join(stateDir('output'), name);
  let st;
  try {
    st = fs.statSync(file);
  } catch {
    res.writeHead(404);
    return res.end('not found');
  }
  if (!st.isFile()) {
    res.writeHead(404);
    return res.end('not found');
  }
  const type = name.endsWith('.mp4') ? 'video/mp4' : 'application/octet-stream';
  const base = { 'Content-Type': type, 'Accept-Ranges': 'bytes', 'Cache-Control': 'no-cache' };

  const range = req.headers.range;
  if (range) {
    const m = /^bytes=(\d*)-(\d*)$/.exec(range);
    let start;
    let end;
    if (m && (m[1] !== '' || m[2] !== '')) {
      if (m[1] !== '') {
        start = Number(m[1]);
        end = m[2] !== '' ? Math.min(Number(m[2]), st.size - 1) : st.size - 1;
      } else {
        const suffix = Math.min(Number(m[2]), st.size);
        start = st.size - suffix;
        end = st.size - 1;
      }
    }
    if (start === undefined || Number.isNaN(start) || Number.isNaN(end) || start > end || start >= st.size) {
      res.writeHead(416, { 'Content-Range': `bytes */${st.size}` });
      return res.end();
    }
    res.writeHead(206, { ...base, 'Content-Range': `bytes ${start}-${end}/${st.size}`, 'Content-Length': end - start + 1 });
    if (req.method === 'HEAD') return res.end();
    return fs.createReadStream(file, { start, end }).pipe(res);
  }

  res.writeHead(200, { ...base, 'Content-Length': st.size });
  if (req.method === 'HEAD') return res.end();
  fs.createReadStream(file).pipe(res);
}

function route(req, res) {
  const { pathname } = new URL(req.url, 'http://localhost');

  if (req.method === 'GET' || req.method === 'HEAD') {
    if (pathname === '/') {
      res.writeHead(302, { Location: '/dashboard.html' });
      return res.end();
    }
    if (pathname === '/dashboard.html') return serveDashboard(req, res);
    if (pathname === '/favicon.ico') {
      res.writeHead(204);
      return res.end();
    }
    if (pathname === '/api/jobs') return sendJson(res, 200, collectJobs());
    if (pathname === '/api/state') return sendJson(res, 200, currentState());
    if (pathname.startsWith('/output/')) return serveOutput(req, res, pathname.slice('/output/'.length));
    return sendJson(res, 404, { ok: false, error: 'not found' });
  }

  if (req.method === 'POST') {
    if (pathname === '/api/pause') {
      paused = !paused;
      log(paused ? 'paused — running jobs will finish, nothing new starts' : 'resumed');
      return sendJson(res, 200, { ok: true, paused });
    }
    let m = /^\/api\/retry\/([^/]+)$/.exec(pathname);
    if (m) return apiRetry(res, decodeURIComponent(m[1]));
    m = /^\/api\/cancel\/([^/]+)$/.exec(pathname);
    if (m) return apiCancel(res, decodeURIComponent(m[1]));
    return sendJson(res, 404, { ok: false, error: 'not found' });
  }

  res.writeHead(405, { Allow: 'GET, HEAD, POST' });
  res.end();
}

// ---------------------------------------------------------------- startup

for (const d of [...STATE_DIRS, 'output']) fs.mkdirSync(stateDir(d), { recursive: true });
requeueStuckWork();

const server = http.createServer((req, res) => {
  try {
    route(req, res);
  } catch (err) {
    log(`HTTP error on ${req.method} ${req.url}: ${err.message}`);
    if (!res.headersSent) sendJson(res, 500, { ok: false, error: err.message });
    else res.end();
  }
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`error: port ${PORT} is already in use — is another runner running? (PORT=<n> overrides)`);
  } else {
    console.error(`error: ${err.message}`);
  }
  process.exit(1);
});

server.listen(PORT, () => {
  log(`video factory up — dashboard: http://localhost:${PORT}/dashboard.html`);
  log(`concurrency: voice=${VOICE_CONCURRENCY} render=${RENDER_CONCURRENCY} · scanning queue/ every ${SCAN_INTERVAL_MS / 1000}s`);
});

setInterval(scanQueue, SCAN_INTERVAL_MS);
scanQueue();

function shutdown(signal) {
  log(`${signal} received — stopping (running jobs will be requeued on next start)`);
  for (const state of jobs.values()) killChild(state);
  server.close();
  // Give the kill signals a beat to land, then exit.
  setTimeout(() => process.exit(0), 300).unref();
}
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
