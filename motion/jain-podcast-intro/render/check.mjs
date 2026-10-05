// Path QA: camera clearance against every solid, speed / yaw-rate / jerk report, and a
// top-down plan view (renders/plan.svg) of camera, target and star paths.
import fs from 'node:fs';
import path from 'node:path';

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const len = (a) => Math.hypot(a[0], a[1], a[2]);
function qInvRotate(q, v) { // rotate v by conjugate of q
  const [x, y, z, w] = [-q[0], -q[1], -q[2], q[3]];
  const ix = w * v[0] + y * v[2] - z * v[1], iy = w * v[1] + z * v[0] - x * v[2], iz = w * v[2] + x * v[1] - y * v[0], iw = -x * v[0] - y * v[1] - z * v[2];
  return [ix * w + iw * -x + iy * -z - iz * -y, iy * w + iw * -y + iz * -x - ix * -z, iz * w + iw * -z + ix * -y - iy * -x];
}
function qRotate(q, v) { return qInvRotate([-q[0], -q[1], -q[2], q[3]], v); }
function obbDist(p, c, q, half) {
  const l = qInvRotate(q, sub(p, c));
  const d = l.map((v, i) => Math.max(0, Math.abs(v) - half[i]));
  return len(d);
}

export function checkPath({ out, layout }, dir) {
  const phases = [[0, 2.4], [2.4, 4.8], [4.8, 7.2], [7.2, 9.6], [9.6, 12]];
  let worst = { d: 1e9 };
  const perObj = {};
  for (const s of out) {
    const c = s.cam;
    const check = (name, d) => {
      if (!perObj[name] || d < perObj[name].d) perObj[name] = { d: +d.toFixed(3), t: s.t };
      if (d < worst.d) worst = { d, t: s.t, name };
    };
    for (const L of s.letters) check('letter ' + L.ch, obbDist(c, L.p, L.q, L.half));
    s.word2.letters.forEach((l, i) => {
      const wp = qRotate(s.word2.q, l.p);
      check('PODCAST[' + i + ']', obbDist(c, [s.word2.p[0] + wp[0], s.word2.p[1] + wp[1], s.word2.p[2] + wp[2]], s.word2.q, l.half));
    });
    check('star', len(sub(c, s.star)) - 1.5 * s.starScale);
    for (const [x, z, r] of layout.columns) check('column', Math.hypot(c[0] - x, c[2] - z) - r);
  }
  // column coverage: frames where the column fills the whole horizontal field of view
  const hfov = 2 * Math.atan(18 / 50);
  const covered = [];
  for (const s of out) for (const [x, z, r] of layout.columns) {
    const dx = x - s.cam[0], dz = z - s.cam[2], d = Math.hypot(dx, dz);
    const ang = Math.atan2(dx, -dz) - Math.atan2(s.fwd[0], -s.fwd[2]);
    const half = Math.asin(Math.min(1, r / d));
    if (Math.abs(Math.atan2(Math.sin(ang), Math.cos(ang))) + hfov / 2 <= half) covered.push(s.t);
  }
  console.log('column fully covers frame at t =', covered.length ? `${covered[0]}..${covered[covered.length - 1]} (${covered.length} frames)` : 'never');
  // star apparent size (fraction of frame height) peaks per phase
  const vslope = 0.2025;
  const big = out.map((s) => ({ t: s.t, f: (3.0 * s.starScale) / (2 * vslope * Math.max(0.01, len(sub(s.star, s.cam)))) }));
  console.log('star apparent height (frame fractions) max per phase:', [[0, 2.4], [2.4, 4.8], [4.8, 7.2], [7.2, 9.6], [9.6, 12]].map(([a, b]) => { const m = big.filter((x) => x.t >= a && x.t < b).reduce((m, x) => (x.f > m.f ? x : m), { f: 0 }); return `${m.f.toFixed(2)}@${m.t}`; }).join('  '));
  console.log('PODCAST first in frame at t =', podcastFirstSeen(out));
  console.log('min clearance per object (units; near plane 0.04):');
  for (const [k, v] of Object.entries(perObj)) console.log(`  ${k.padEnd(14)} ${String(v.d).padStart(7)} at t=${v.t}`);

  // speed, acceleration, jerk, yaw rate
  const dt = out[1].t - out[0].t;
  const speed = out.map((s) => s.speed);
  const acc = speed.map((v, i) => (i ? (v - speed[i - 1]) / dt : 0));
  const yaw = out.map((s) => Math.atan2(s.fwd[0], -s.fwd[2]) * 180 / Math.PI);
  const pitch = out.map((s) => Math.asin(Math.max(-1, Math.min(1, s.fwd[1]))) * 180 / Math.PI);
  const yawRate = yaw.map((v, i) => { if (!i) return 0; let d = v - yaw[i - 1]; if (d > 180) d -= 360; if (d < -180) d += 360; return d / dt; });
  console.log('\nphase   speed min/max (u/s)   |accel| max   |yaw rate| max (deg/s)');
  for (const [a, b] of phases) {
    const idx = out.map((s, i) => i).filter((i) => out[i].t >= a && out[i].t < b);
    const sp = idx.map((i) => speed[i]), ac = idx.map((i) => Math.abs(acc[i])), yr = idx.map((i) => Math.abs(yawRate[i]));
    console.log(`${a.toFixed(1)}-${b.toFixed(1)}   ${Math.min(...sp).toFixed(2).padStart(6)} / ${Math.max(...sp).toFixed(2).padStart(6)}      ${Math.max(...ac).toFixed(1).padStart(6)}       ${Math.max(...yr).toFixed(1).padStart(6)}`);
  }
  const peak = out.reduce((m, s, i) => (s.t > 4.8 && s.t < 7.2 && speed[i] > m.v ? { v: speed[i], t: s.t } : m), { v: 0 });
  console.log(`fly-through peak speed ${peak.v.toFixed(2)} u/s at t=${peak.t}`);

  // plan view
  const S = 22, ox = 380, oz = 420;
  const X = (x) => (ox + x * S).toFixed(1), Z = (z) => (oz - z * S).toFixed(1);
  const cols = ['#00DAC4', '#7dd3fc', '#fbbf24', '#f472b6', '#a3e635'];
  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="900" height="760" viewBox="0 0 900 760" style="background:#0b0b0b;font:11px Inter,sans-serif">`;
  svg += `<text x="10" y="16" fill="#aaa">plan view (x right, -z up). camera colour by phase; ticks = look direction every 0.2 s</text>`;
  for (const [x, z, r] of layout.columns) svg += `<circle cx="${X(x)}" cy="${Z(z)}" r="${r * S}" fill="#333"/>`;
  phases.forEach(([a, b], k) => {
    const pts = out.filter((s) => s.t >= a && s.t <= b + 1e-6);
    svg += `<polyline fill="none" stroke="${cols[k]}" stroke-width="2" points="${pts.map((s) => `${X(s.cam[0])},${Z(s.cam[2])}`).join(' ')}"/>`;
    svg += `<polyline fill="none" stroke="${cols[k]}" stroke-width="1" stroke-dasharray="3 3" opacity="0.6" points="${pts.map((s) => `${X(s.star[0])},${Z(s.star[2])}`).join(' ')}"/>`;
  });
  out.forEach((s, i) => {
    if (i % 12) return;
    svg += `<line x1="${X(s.cam[0])}" y1="${Z(s.cam[2])}" x2="${X(s.cam[0] + s.fwd[0] * 1.6)}" y2="${Z(s.cam[2] + s.fwd[2] * 1.6)}" stroke="#fff" stroke-width="0.7" opacity="0.7"/>`;
    if (i % 60 === 0) svg += `<text x="${+X(s.cam[0]) + 4}" y="${+Z(s.cam[2]) - 4}" fill="#ddd">${s.t.toFixed(0)}s</text>`;
  });
  const snap = (t) => out.reduce((m, s) => (Math.abs(s.t - t) < Math.abs(m.t - t) ? s : m), out[0]);
  for (const [t, col] of [[6.0, '#fff'], [12, '#888']]) {
    const s = snap(t);
    for (const L of s.letters) svg += `<rect x="${X(L.p[0] - L.half[0])}" y="${Z(L.p[2] + 0.1)}" width="${L.half[0] * 2 * S}" height="${0.2 * S}" fill="none" stroke="${col}" transform="rotate(${(-Math.atan2(2 * (L.q[3] * L.q[1]), 1 - 2 * L.q[1] * L.q[1]) * 180 / Math.PI).toFixed(1)} ${X(L.p[0])} ${Z(L.p[2])})"/><text x="${X(L.p[0])}" y="${+Z(L.p[2]) + 14}" fill="${col}">${L.ch}</text>`;
    svg += `<rect x="${X(s.word2.p[0] - 4.8)}" y="${Z(s.word2.p[2] + 0.1)}" width="${9.6 * S}" height="${0.2 * S}" fill="none" stroke="${col}" stroke-dasharray="4 2"/>`;
  }
  svg += `</svg>`;
  fs.writeFileSync(path.join(dir, 'plan.svg'), svg);
  console.log('\nwrote', path.join(dir, 'plan.svg'));
}

// When does any PODCAST corner first enter the frame? (ignores the <=3 deg bank)
export function podcastFirstSeen(out, from = 4.5) {
  const vs = 0.2025, hs = 0.36;
  for (const s of out) {
    if (s.t < from) continue;
    const f = s.fwd, r = norm([-f[2], 0, f[0]]), u = cross(r, f);
    for (const l of s.word2.letters) for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
      const lp = [l.p[0] + sx * l.half[0], l.p[1] + sy * l.half[1], 0];
      const wp = qRotate(s.word2.q, lp);
      const d = sub([s.word2.p[0] + wp[0], s.word2.p[1] + wp[1], s.word2.p[2] + wp[2]], s.cam);
      const z = dot(d, f);
      if (z > 0.05 && Math.abs(dot(d, r) / z) < hs && Math.abs(dot(d, u) / z) < vs) return s.t;
    }
  }
  return null;
}
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a) => { const l = len(a); return a.map((v) => v / l); };
