// Deterministic motion helpers: monotone cubic retiming, arc-length paths, quaternion tables.
import * as THREE from 'three';

export const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
export const smoothstep = (a, b, x) => {
  const t = clamp((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};
export const smootherstep = (a, b, x) => {
  const t = clamp((x - a) / (b - a), 0, 1);
  return t * t * t * (t * (t * 6 - 15) + 10);
};

// Fritsch-Carlson monotone cubic through (xs, ys). Returns f(x) with C1 continuity.
export function pchip(xs, ys) {
  const n = xs.length;
  const h = [], d = [], m = new Array(n).fill(0);
  for (let i = 0; i < n - 1; i++) {
    h[i] = xs[i + 1] - xs[i];
    d[i] = (ys[i + 1] - ys[i]) / h[i];
  }
  m[0] = d[0];
  m[n - 1] = d[n - 2];
  for (let i = 1; i < n - 1; i++) {
    if (d[i - 1] * d[i] <= 0) m[i] = 0;
    else {
      const w1 = 2 * h[i] + h[i - 1], w2 = h[i] + 2 * h[i - 1];
      m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i]);
    }
  }
  return (x) => {
    if (x <= xs[0]) return ys[0] + m[0] * (x - xs[0]);
    if (x >= xs[n - 1]) return ys[n - 1] + m[n - 1] * (x - xs[n - 1]);
    let i = 0;
    while (x > xs[i + 1]) i++;
    const t = (x - xs[i]) / h[i], t2 = t * t, t3 = t2 * t;
    return (2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i] +
      (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1];
  };
}

// Gaussian-smooth a uniformly sampled series. Ends are padded by linear extrapolation so the
// start and end velocities survive.
export function gaussianSmooth(values, sigmaSamples) {
  if (sigmaSamples < 0.5) return values.slice();
  const r = Math.ceil(sigmaSamples * 3), n = values.length;
  const k = [];
  let ks = 0;
  for (let i = -r; i <= r; i++) { const w = Math.exp(-0.5 * (i / sigmaSamples) ** 2); k.push(w); ks += w; }
  const at = (i) => {
    if (i < 0) return values[0] + (values[0] - values[Math.min(n - 1, -i)]);
    if (i >= n) return values[n - 1] + (values[n - 1] - values[Math.max(0, 2 * (n - 1) - i)]);
    return values[i];
  };
  const out = new Array(n);
  for (let i = 0; i < n; i++) {
    let s = 0;
    for (let j = -r; j <= r; j++) s += k[j + r] * at(i + j);
    out[i] = s / ks;
  }
  return out;
}

// A path through timed points: centripetal Catmull-Rom for shape, monotone-cubic retiming of
// arc length for speed, then Gaussian smoothing of distance(t) so acceleration has no kinks.
export class TimedPath {
  constructor(keys, { smoothing = 0.08, rate = 240, duration = 12 } = {}) {
    this.keys = keys;
    this.rate = rate;
    this.duration = duration;
    // Consecutive keys at the same spot are holds: they share one curve point.
    const pts = [], idx = [];
    for (const k of keys) {
      if (pts.length && pts[pts.length - 1].distanceTo(k.p) < 1e-4) idx.push(pts.length - 1);
      else { pts.push(k.p.clone()); idx.push(pts.length - 1); }
    }
    if (pts.length === 1) pts.push(pts[0].clone().add(new THREE.Vector3(0, 0, 1e-6)));
    this.curve = new THREE.CatmullRomCurve3(pts, false, 'centripetal', 0.5);
    const div = 4000;
    const lengths = this.curve.getLengths(div);
    this.total = lengths[div];
    // arc length at each key: unique point i sits at curve parameter i/(n-1)
    const n = pts.length;
    const keyLen = idx.map((i) => {
      const f = (i / (n - 1)) * div, i0 = Math.floor(f), i1 = Math.min(div, i0 + 1);
      return lengths[i0] + (lengths[i1] - lengths[i0]) * (f - i0);
    });
    const dist = pchip(keys.map((k) => k.t), keyLen);
    const samples = [];
    const N = Math.round(duration * rate);
    for (let i = 0; i <= N; i++) samples.push(dist(i / rate));
    this.dist = gaussianSmooth(samples, smoothing * rate).map((v) => clamp(v, 0, this.total));
    this.keyLen = keyLen;
  }
  distanceAt(t) {
    const f = clamp(t, 0, this.duration) * this.rate;
    const i0 = Math.floor(f), i1 = Math.min(this.dist.length - 1, i0 + 1);
    return this.dist[i0] + (this.dist[i1] - this.dist[i0]) * (f - i0);
  }
  pointAt(t, target = new THREE.Vector3()) {
    const u = this.total > 0 ? this.distanceAt(t) / this.total : 0;
    return this.curve.getPointAt(clamp(u, 0, 1), target);
  }
  speedAt(t, dt = 1 / 240) {
    return (this.distanceAt(t + dt) - this.distanceAt(t - dt)) / (2 * dt);
  }
}

// Scalar keyframes (monotone cubic + smoothing), for scales, angles and blends.
export class ScalarTrack {
  constructor(keys, { smoothing = 0.06, rate = 240, duration = 12 } = {}) {
    const f = pchip(keys.map((k) => k[0]), keys.map((k) => k[1]));
    const N = Math.round(duration * rate);
    const s = [];
    for (let i = 0; i <= N; i++) s.push(f(i / rate));
    this.v = gaussianSmooth(s, smoothing * rate);
    this.rate = rate;
    this.duration = duration;
  }
  at(t) {
    const f = clamp(t, 0, this.duration) * this.rate;
    const i0 = Math.floor(f), i1 = Math.min(this.v.length - 1, i0 + 1);
    return this.v[i0] + (this.v[i1] - this.v[i0]) * (f - i0);
  }
}

// Orientation table: look-at quaternions with bank, smoothed in quaternion space, sampled
// with slerp at render time.
export class OrientationTable {
  constructor(posFn, targetFn, { rate = 240, duration = 12, smoothing = 0.08, bankMaxDeg = 3, bankGain = 0.05 } = {}) {
    this.rate = rate;
    this.duration = duration;
    const N = Math.round(duration * rate);
    const m = new THREE.Matrix4(), up = new THREE.Vector3(0, 1, 0);
    const P = [], raw = [];
    for (let i = 0; i <= N; i++) P.push(posFn(i / rate, new THREE.Vector3()));
    const bankRaw = [];
    for (let i = 0; i <= N; i++) {
      const t = i / rate;
      const p = P[i], tg = targetFn(t, new THREE.Vector3());
      m.lookAt(p, tg, up);
      const q = new THREE.Quaternion().setFromRotationMatrix(m);
      raw.push(q);
      // lateral acceleration in camera space -> bank (lean into the turn)
      const a = P[Math.max(0, i - 1)].clone().add(P[Math.min(N, i + 1)]).sub(p.clone().multiplyScalar(2)).multiplyScalar(rate * rate);
      const right = new THREE.Vector3(1, 0, 0).applyQuaternion(q);
      bankRaw.push(clamp(-a.dot(right) * bankGain, -bankMaxDeg, bankMaxDeg));
    }
    const bank = gaussianSmooth(bankRaw, 0.25 * rate);
    // align hemispheres, then Gaussian-weighted quaternion average
    for (let i = 1; i < raw.length; i++) if (raw[i].dot(raw[i - 1]) < 0) raw[i].set(-raw[i].x, -raw[i].y, -raw[i].z, -raw[i].w);
    const comps = ['x', 'y', 'z', 'w'].map((c) => gaussianSmooth(raw.map((q) => q[c]), smoothing * rate));
    const fwd = new THREE.Vector3();
    this.q = raw.map((_, i) => {
      const q = new THREE.Quaternion(comps[0][i], comps[1][i], comps[2][i], comps[3][i]).normalize();
      fwd.set(0, 0, -1).applyQuaternion(q);
      const roll = new THREE.Quaternion().setFromAxisAngle(fwd, THREE.MathUtils.degToRad(bank[i]));
      return roll.multiply(q);
    });
    this.bank = bank;
  }
  at(t, out = new THREE.Quaternion()) {
    const f = clamp(t, 0, this.duration) * this.rate;
    const i0 = Math.floor(f), i1 = Math.min(this.q.length - 1, i0 + 1);
    return out.copy(this.q[i0]).slerp(this.q[i1], f - i0);
  }
}
