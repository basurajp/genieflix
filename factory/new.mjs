#!/usr/bin/env node
/**
 * Create a new video project in factory/building/<slug>/ from template/.
 * Usage: node factory/new.mjs <slug> [title ...]
 *
 * Capture is instant, building is async: this puts the idea on the dashboard
 * immediately; fill in lines.txt + slides, then enqueue when it is ready.
 */

import fs from 'node:fs';
import path from 'node:path';

const FACTORY_DIR = import.meta.dirname;
const REPO_ROOT = path.dirname(FACTORY_DIR);
const STATE_DIRS = ['building', 'queue', 'work', 'done', 'failed'];
const SLUG_RE = /^[a-z0-9][a-z0-9-]*$/;

function die(msg) {
  console.error(`error: ${msg}`);
  process.exit(1);
}

const [slug, ...titleWords] = process.argv.slice(2);
if (!slug || slug === '-h' || slug === '--help') {
  console.log('usage: node factory/new.mjs <slug> [title ...]');
  console.log('creates factory/building/<slug>/ from template/ with job.json + BRIEF.md');
  process.exit(slug ? 0 : 1);
}
if (!SLUG_RE.test(slug)) die('slug must be lowercase letters, digits and hyphens (e.g. magicslides-vs-gamma)');

// A slug must be unique across the whole state machine, not just building/.
for (const state of STATE_DIRS) {
  if (fs.existsSync(path.join(FACTORY_DIR, state, slug))) {
    die(`"${slug}" already exists in factory/${state}/ — pick another slug or remove it first`);
  }
}

const templateDir = path.join(REPO_ROOT, 'template');
if (!fs.existsSync(path.join(templateDir, 'project.json'))) {
  die(`template/project.json not found (looked in ${templateDir})`);
}

const title = titleWords.join(' ').trim()
  || slug.split('-').filter(Boolean).map((w) => w[0].toUpperCase() + w.slice(1)).join(' ');

const dest = path.join(FACTORY_DIR, 'building', slug);
fs.mkdirSync(path.dirname(dest), { recursive: true });
fs.cpSync(templateDir, dest, { recursive: true });

// project.json: keep template defaults, stamp this project's identity.
const projectFile = path.join(dest, 'project.json');
let project = {};
try {
  project = JSON.parse(fs.readFileSync(projectFile, 'utf8'));
} catch {
  project = { topic: '', audience: '', lang: 'en', music: '', sfx: [], cta_keyword: 'LINK' };
}
project.slug = slug;
project.title = title;
fs.writeFileSync(projectFile, `${JSON.stringify(project, null, 2)}\n`);

const now = new Date().toISOString();
const job = { slug, title, status: 'building', created: now, updated: now, error: null, output: null, attempts: 0 };
fs.writeFileSync(path.join(dest, 'job.json'), `${JSON.stringify(job, null, 2)}\n`);

const brief = `# ${title}

Topic:
Audience:
Angle:

## Instructions

(Free-form brief for this reel: what it should say, numbers to cite, the CTA.
This file and lines.txt are the plan — everything generated from them is
disposable and can be rebuilt.)

## Checklist before enqueueing

- [ ] lines.txt — five lines: hook, action, proof, contrast, CTA
- [ ] assets/slides/slide01.png ... — one visual per line
- [ ] project.json — lang, music, cta_keyword
- [ ] node factory/enqueue.mjs ${slug}
`;
fs.writeFileSync(path.join(dest, 'BRIEF.md'), brief);

console.log(`created factory/building/${slug}/  ("${title}")`);
console.log('next:');
console.log(`  1. write the five lines in factory/building/${slug}/lines.txt`);
console.log(`  2. drop one slide per line into factory/building/${slug}/assets/slides/`);
console.log(`  3. put instructions in factory/building/${slug}/BRIEF.md`);
console.log(`  4. node factory/enqueue.mjs ${slug}`);
