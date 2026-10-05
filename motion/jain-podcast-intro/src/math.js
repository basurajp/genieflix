// Deterministic motion helpers. Everything is a pure function of time.
import * as THREE from 'three';

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const smoothstep = (a, b, x) => {
  const t = clamp((x - a) / (b - a));
  return t * t * (3 - 2 * t);
};
// C2-continuous ease (zero velocity and acceleration at both ends).
export const smootherstep = (a, b, x) => {
  const t = clamp((x - a) / (b - a));
  return t * t * t * (t * (t * 6 - 15) + 10);
};
export const easeOutCubic = (t) => 1 - Math.pow(1 - clamp(t), 3);
export const deg = (d) => (d * Math.PI) / 180;

// Seeded PRNG (mulberry32) so procedural details never change between renders.
export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Monotone cubic Hermite through (t_i, v_i). C1 continuous, never overshoots.
// Optional fixed end slopes.
export class Hermite {
  constructor(keys, { startSlope = null, endSlope = null, extrapolate = false } = {}) {
    this.t = keys.map((k) => k[0]);
    this.v = keys.map((k) => k[1]);
    this.extrapolate = extrapolate;
    const n = keys.length;
    const d = [];
    for (let i = 0; i < n - 1; i++) d.push((this.v[i + 1] - this.v[i]) / (this.t[i + 1] - this.t[i]));
    const m = new Array(n).fill(0);
    for (let i = 1; i < n - 1; i++) {
      if (d[i - 1] * d[i] <= 0) m[i] = 0;
      else {
        // weighted harmonic mean (Fritsch–Butland), respects uneven spacing
        const h0 = this.t[i] - this.t[i - 1];
        const h1 = this.t[i + 1] - this.t[i];
        const w1 = 2 * h1 + h0;
        const w2 = h1 + 2 * h0;
        m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i]);
      }
    }
    m[0] = startSlope ?? (n > 1 ? d[0] : 0);
    m[n - 1] = endSlope ?? (n > 1 ? d[n - 2] : 0);
    this.m = m;
  }
  at(x) {
    const { t, v, m } = this;
    const n = t.length;
    if (x <= t[0]) return this.extrapolate ? v[0] + m[0] * (x - t[0]) : v[0];
    if (x >= t[n - 1]) return this.extrapolate ? v[n - 1] + m[n - 1] * (x - t[n - 1]) : v[n - 1];
    let i = 0;
    while (i < n - 2 && x > t[i + 1]) i++;
    const h = t[i + 1] - t[i];
    const s = (x - t[i]) / h;
    const s2 = s * s;
    const s3 = s2 * s;
    return (
      (2 * s3 - 3 * s2 + 1) * v[i] +
      (s3 - 2 * s2 + s) * h * m[i] +
      (-2 * s3 + 3 * s2) * v[i + 1] +
      (s3 - s2) * h * m[i + 1]
    );
  }
}

// A spatial path (centripetal Catmull–Rom) travelled at a speed profile that is
// defined in arc length. Some control points carry a time anchor `t`; between
// anchors the arc-length parameter follows a monotone C1 Hermite curve, so
// position and velocity are continuous everywhere, including phase boundaries.
export class Rail {
  constructor(points, { startSpeed = null, endSpeed = null, extrapolate = false } = {}) {
    this.curve = new THREE.CatmullRomCurve3(
      points.map((p) => new THREE.Vector3(...p.p)),
      false,
      'centripetal',
    );
    this.curve.arcLengthDivisions = 4000;
    const N = 4000;
    const lengths = this.curve.getLengths(N);
    this.length = lengths[N];
    const n = points.length;
    const keys = [];
    points.forEach((p, i) => {
      if (p.t === undefined) return;
      const idx = Math.round((i / (n - 1)) * N);
      keys.push([p.t, lengths[idx] / this.length]);
    });
    this.timing = new Hermite(keys, {
      startSlope: startSpeed === null ? null : startSpeed / this.length,
      endSlope: endSpeed === null ? null : endSpeed / this.length,
      extrapolate,
    });
    this.tStart = keys[0][0];
    this.tEnd = keys[keys.length - 1][0];
  }
  u(time) {
    return clamp(this.timing.at(time));
  }
  at(time, target = new THREE.Vector3()) {
    return this.curve.getPointAt(this.u(time), target);
  }
}

// Vector keyframes with monotone Hermite per component (C1).
export class VecTrack {
  constructor(keys, opts) {
    this.x = new Hermite(keys.map((k) => [k[0], k[1][0]]), opts);
    this.y = new Hermite(keys.map((k) => [k[0], k[1][1]]), opts);
    this.z = new Hermite(keys.map((k) => [k[0], k[1][2]]), opts);
  }
  at(t, target = new THREE.Vector3()) {
    return target.set(this.x.at(t), this.y.at(t), this.z.at(t));
  }
}

// Orientation keys given as small Euler angles (degrees, XYZ); components are
// interpolated with C1 Hermite curves and converted to a quaternion each frame.
export class EulerTrack {
  constructor(keys) {
    this.track = new VecTrack(keys.map(([t, e]) => [t, e.map(deg)]));
    this._v = new THREE.Vector3();
    this._e = new THREE.Euler();
  }
  at(t, q = new THREE.Quaternion()) {
    const v = this.track.at(t, this._v);
    return q.setFromEuler(this._e.set(v.x, v.y, v.z, 'XYZ'));
  }
}
