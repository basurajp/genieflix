// Procedural geometry: the four-point star, rounded glass panels, the swept ribbon.
import * as THREE from 'three';
import { toCreasedNormals } from 'three/addons/utils/BufferGeometryUtils.js';

// --- Star silhouette ------------------------------------------------------
// One quadrant runs from the top tip to the right tip (clockwise):
//   top cap (semicircle half, centre (0, 1-r)) -> concave cubic into the valley
//   (v, v) -> mirrored cubic out to the right cap -> right cap half.
// Tangents are continuous at every joint: the flank leaves each cap shoulder
// along the cap's own tangent and crosses the valley perpendicular to the diagonal.
export function starOutline(cfg) {
  const r = cfg.tipRadius;
  const v = cfg.valley;
  const phi = cfg.shoulderAngle; // where the flank leaves the round tip (rad from +x)
  const diag = new THREE.Vector2(1, -1).normalize();
  const S = new THREE.Vector2(r * Math.cos(phi), 1 - r + r * Math.sin(phi));
  const tS = new THREE.Vector2(Math.sin(phi), -Math.cos(phi)); // cap tangent at the shoulder
  const V = new THREE.Vector2(v, v);
  const flank = new THREE.CubicBezierCurve(
    S,
    S.clone().addScaledVector(tS, cfg.flankA),
    V.clone().addScaledVector(diag, -cfg.flankB),
    V,
  );
  const half = [];
  const capN = cfg.samplesPerCap;
  for (let i = 0; i < capN; i++) {
    const ang = Math.PI / 2 - (i / capN) * (Math.PI / 2 - phi);
    half.push(new THREE.Vector2(r * Math.cos(ang), 1 - r + r * Math.sin(ang)));
  }
  const fN = cfg.samplesPerFlank;
  for (let i = 0; i < fN; i++) half.push(flank.getPoint(i / fN));
  // Mirror across y = x (reversed) for the right tip's half: tangents stay continuous.
  const quadrant = [...half, V.clone()];
  // The mirrored apex is skipped: it is the next quadrant's first point.
  for (let i = half.length - 1; i >= 1; i--) quadrant.push(new THREE.Vector2(half[i].y, half[i].x));
  // Rotate the quadrant by -90deg three times to close the loop (clockwise).
  const pts = [];
  for (let q = 0; q < 4; q++) {
    const c = Math.cos((-q * Math.PI) / 2);
    const s = Math.sin((-q * Math.PI) / 2);
    for (const p of quadrant) pts.push(new THREE.Vector2(p.x * c - p.y * s, p.x * s + p.y * c));
  }
  return pts;
}

export function buildStarGeometry(cfg) {
  const shape = new THREE.Shape(starOutline(cfg));
  let geo = new THREE.ExtrudeGeometry(shape, {
    depth: cfg.depth,
    bevelEnabled: true,
    bevelThickness: cfg.bevelThickness,
    bevelSize: cfg.bevelSize,
    bevelSegments: cfg.bevelSegments,
    bevelOffset: cfg.bevelOffset,
    curveSegments: 1,
    steps: 1,
  });
  geo.translate(0, 0, -cfg.depth / 2);
  // Normalise so the outermost tips (bevel included) sit at +-1.
  geo.computeBoundingBox();
  const ext = Math.max(geo.boundingBox.max.x, geo.boundingBox.max.y);
  geo.scale(1 / ext, 1 / ext, 1 / ext);
  geo.clearGroups();
  geo = toCreasedNormals(geo, THREE.MathUtils.degToRad(75));
  geo.computeBoundingSphere();
  return geo;
}

// --- Rounded rectangle panel ---------------------------------------------
export function roundedRectShape(w, h, r) {
  const s = new THREE.Shape();
  const x = -w / 2;
  const y = -h / 2;
  s.moveTo(x + r, y);
  s.lineTo(x + w - r, y);
  s.absarc(x + w - r, y + r, r, -Math.PI / 2, 0, false);
  s.lineTo(x + w, y + h - r);
  s.absarc(x + w - r, y + h - r, r, 0, Math.PI / 2, false);
  s.lineTo(x + r, y + h);
  s.absarc(x + r, y + h - r, r, Math.PI / 2, Math.PI, false);
  s.lineTo(x, y + r);
  s.absarc(x + r, y + r, r, Math.PI, Math.PI * 1.5, false);
  return s;
}

export function buildPanelGeometry(w, h, thickness) {
  const r = 0.09 * Math.min(w, h); // corner radius: 9% of the smaller side
  const bevel = Math.min(thickness * 0.45, 0.05);
  const depth = Math.max(0.001, thickness - 2 * bevel);
  let geo = new THREE.ExtrudeGeometry(roundedRectShape(w - 2 * bevel, h - 2 * bevel, r - bevel), {
    depth,
    bevelEnabled: true,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: 8,
    curveSegments: 24,
  });
  geo.translate(0, 0, -depth / 2);
  geo.clearGroups();
  geo = toCreasedNormals(geo, THREE.MathUtils.degToRad(70));
  return geo;
}

// --- Ribbon: a closed profile swept along a curve --------------------------
// Profile (in the ribbon's cross-section plane, coordinates (s, t)): a thin
// sheet of width `w` and thickness `t`, ending in a round bead of radius `rb`
// on the +s side. The bead is the "darker, thicker edge" used for the
// occlusion beat. The loop runs clockwise seen from +T.
function ribbonProfile(w, t, rb, n = 20) {
  const pts = [];
  const half = t / 2;
  const sL = -w / 2;
  const sR = w / 2;
  const top = 16;
  for (let i = 0; i <= top; i++) pts.push([sL + ((sR - sL) * i) / top, half]);
  const cx = sR + Math.sqrt(rb * rb - half * half);
  const a0 = Math.atan2(half, sR - cx); // upper-left point of the bead circle
  for (let i = 1; i < n * 2; i++) {
    const ang = a0 - (2 * a0 * i) / (n * 2);
    pts.push([cx + rb * Math.cos(ang), rb * Math.sin(ang)]);
  }
  for (let i = 0; i <= top; i++) pts.push([sR - ((sR - sL) * i) / top, -half]);
  for (let i = 1; i < n; i++) {
    const ang = -Math.PI / 2 - (Math.PI * i) / n;
    pts.push([sL + half * Math.cos(ang), half * Math.sin(ang)]);
  }
  return pts;
}

export function buildRibbonGeometry({ curve, width, thickness, bead, segments = 240, up = [0, 0, 1], twist = () => 0 }) {
  const prof = ribbonProfile(width, thickness, bead);
  const P = prof.length;
  const positions = [];
  const index = [];
  const upV = new THREE.Vector3(...up).normalize();
  const T = new THREE.Vector3();
  const p = new THREE.Vector3();
  const frames = [];
  const taper = (u) => 0.25 + 0.75 * Math.min(1, u / 0.07, (1 - u) / 0.07) ** 0.5;
  const emit = (f, k) => {
    for (const [ps, pt] of prof) {
      positions.push(
        f.p.x + (f.n.x * ps + f.b.x * pt) * k,
        f.p.y + (f.n.y * ps + f.b.y * pt) * k,
        f.p.z + (f.n.z * ps + f.b.z * pt) * k,
      );
    }
  };
  for (let i = 0; i <= segments; i++) {
    const u = i / segments;
    curve.getPointAt(u, p);
    curve.getTangentAt(u, T);
    const N = new THREE.Vector3().crossVectors(upV, T).normalize();
    const B = new THREE.Vector3().crossVectors(T, N).normalize();
    const tw = twist(u);
    const n2 = N.clone().multiplyScalar(Math.cos(tw)).addScaledVector(B, Math.sin(tw));
    const b2 = B.clone().multiplyScalar(Math.cos(tw)).addScaledVector(N, -Math.sin(tw));
    const f = { p: p.clone(), n: n2, b: b2, t: T.clone(), k: taper(u) };
    frames.push(f);
    emit(f, f.k);
  }
  for (let i = 0; i < segments; i++) {
    for (let j = 0; j < P; j++) {
      const a = i * P + j;
      const b = i * P + ((j + 1) % P);
      const c = (i + 1) * P + j;
      const d = (i + 1) * P + ((j + 1) % P);
      index.push(a, c, b, b, c, d);
    }
  }
  // Flat end caps on their own vertices; winding chosen from the geometry.
  const contour = prof.map(([x, y]) => new THREE.Vector2(x, y));
  const tris = THREE.ShapeUtils.triangulateShape(contour, []);
  const va = new THREE.Vector3();
  const vb = new THREE.Vector3();
  const vc = new THREE.Vector3();
  for (const [fi, sign] of [[0, -1], [segments, 1]]) {
    const f = frames[fi];
    const base = positions.length / 3;
    emit(f, f.k);
    for (const [a, b, c] of tris) {
      va.fromArray(positions, (base + a) * 3);
      vb.fromArray(positions, (base + b) * 3);
      vc.fromArray(positions, (base + c) * 3);
      const nrm = vb.clone().sub(va).cross(vc.clone().sub(va));
      if (nrm.dot(f.t) * sign >= 0) index.push(base + a, base + b, base + c);
      else index.push(base + a, base + c, base + b);
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geo.setIndex(index);
  geo.computeVertexNormals();
  geo.computeBoundingSphere();
  return geo;
}
