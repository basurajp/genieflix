#!/usr/bin/env node
/**
 * Create a new video project in factory/building/<slug>/ from template/.
 * Usage: node factory/new.mjs <slug> [title ...] [--style <name>]
 *
 * --style picks a look from styles/ (swiss-editorial, kinetic-punch, cine-doc,
 * neo-brutal, ...); without it the project uses the classic template.
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

const argv = process.argv.slice(2);
let style = '';
const styleAt = argv.indexOf('--style');
if (styleAt !== -1) {
  style = argv[styleAt + 1] || '';
  argv.splice(styleAt, 2);
}
const [slug, ...titleWords] = argv;
const stylesDir = path.join(path.dirname(import.meta.dirname), 'styles');
const knownStyles = fs.existsSync(stylesDir)
  ? fs.readdirSync(stylesDir).filter((d) => fs.existsSync(path.join(stylesDir, d, 'index.html')))
  : [];
if (!slug || slug === '-h' || slug === '--help') {
  console.log('usage: node factory/new.mjs <slug> [title ...] [--style <name>]');
  console.log('creates factory/building/<slug>/ from template/ with job.json + BRIEF.md');
  console.log(`styles: classic, ${knownStyles.join(', ')}`);
  process.exit(slug ? 0 : 1);
}
if (styleAt !== -1 && style !== 'classic' && !knownStyles.includes(style)) {
  die(`unknown style "${style}" — available: classic, ${knownStyles.join(', ')}`);
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
if (style && style !== 'classic') project.style = style;
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
- [ ] assets/slides/slide01.png ... — one visual per line, or footage staged with
      python3 pipeline/footage.py --project factory/building/${slug} --src-dir <clips>
      (after the voice phase each clip is trimmed to its line; before it, kept up to 12 s)
- [ ] project.json — lang, music, cta_keyword
- [ ] node factory/enqueue.mjs ${slug}
`;
fs.writeFileSync(path.join(dest, 'BRIEF.md'), brief);

console.log(`created factory/building/${slug}/  ("${title}")${style && style !== 'classic' ? `  style: ${style}` : ''}`);
console.log('next:');
console.log(`  1. write the five lines in factory/building/${slug}/lines.txt`);
console.log(`  2. drop one slide per line into factory/building/${slug}/assets/slides/`);
console.log(`  3. put instructions in factory/building/${slug}/BRIEF.md`);
console.log(`  4. node factory/enqueue.mjs ${slug}`);
