#!/usr/bin/env node
/**
 * Hand a finished project to the runner: factory/building/<slug> -> factory/queue/<slug>.
 * Usage: node factory/enqueue.mjs <slug>
 *
 * This is the ownership handoff — after this move, the runner is the only
 * process allowed to write the project's job.json.
 */

import fs from 'node:fs';
import path from 'node:path';

const FACTORY_DIR = import.meta.dirname;

function die(msg) {
  console.error(`error: ${msg}`);
  process.exit(1);
}

const slug = process.argv[2];
if (!slug || slug === '-h' || slug === '--help') {
  console.log('usage: node factory/enqueue.mjs <slug>');
  console.log('moves factory/building/<slug> into factory/queue/ for the runner');
  process.exit(slug ? 0 : 1);
}
if (slug.startsWith('.') || slug.includes('..') || /[/\\]/.test(slug)) die('bad slug');

const src = path.join(FACTORY_DIR, 'building', slug);
if (!fs.existsSync(src)) die(`factory/building/${slug} does not exist — create it with: node factory/new.mjs ${slug}`);

// The plan must exist before the factory will touch a job.
const linesFile = path.join(src, 'lines.txt');
let lines = [];
try {
  lines = fs.readFileSync(linesFile, 'utf8')
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('#'));
} catch {
  die(`factory/building/${slug}/lines.txt is missing — write the five lines first`);
}
if (lines.length === 0) die(`factory/building/${slug}/lines.txt has no lines — write the five lines first`);

const dst = path.join(FACTORY_DIR, 'queue', slug);
if (fs.existsSync(dst)) die(`factory/queue/${slug} already exists`);

// Last write as the owner: stamp the job queued, then hand the folder over.
const jobFile = path.join(src, 'job.json');
let job = null;
try {
  job = JSON.parse(fs.readFileSync(jobFile, 'utf8'));
} catch {
  let title = slug;
  try {
    title = JSON.parse(fs.readFileSync(path.join(src, 'project.json'), 'utf8')).title || slug;
  } catch { /* keep slug as title */ }
  job = { slug, title, status: 'building', created: new Date().toISOString(), error: null, output: null, attempts: 0 };
}
job.status = 'queued';
job.error = null;
job.output = null;
job.updated = new Date().toISOString();
fs.writeFileSync(jobFile, `${JSON.stringify(job, null, 2)}\n`);

fs.mkdirSync(path.dirname(dst), { recursive: true });
fs.renameSync(src, dst);

console.log(`queued factory/queue/${slug} (${lines.length} line${lines.length === 1 ? '' : 's'})`);
const port = process.env.PORT || 4300;
console.log(`the runner picks it up within 3 s — watch it at http://localhost:${port}/dashboard.html`);
