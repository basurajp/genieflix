// Rounded four-point star: closed arc-spline silhouette, shallow extrusion, rounded bevel,
// creased normals (smooth everywhere because every joint is tangent-continuous).
import * as THREE from 'three';
import { toCreasedNormals } from '../vendor/three/addons/BufferGeometryUtils.js';
import { STAR } from './config.js';

// Returns the outline as a THREE.Shape on the normalised plane (tips at distance 1).
// Each tip is a circular cap; each concave flank is a circular arc tangent to the cap and
// perpendicular to the diagonal at the valley, so every joint is tangent-continuous.
export function starGeometryParams(o = STAR) {
  const r = o.tipRadius, a = THREE.MathUtils.degToRad(o.tipCapAngle);
  const R = (1 - r) / (Math.sin(a) - Math.cos(a)) - r; // flank arc radius
  const cx = (r + R) * Math.sin(a), cy = 1 - r + (r + R) * Math.cos(a); // flank centre (on the diagonal)
  return { r, a, R, cx, cy, valley: cx - R / Math.SQRT2 };
}

export function starShape(o = STAR) {
  const { r, a, R, cx, cy } = starGeometryParams(o);
  const shape = new THREE.Shape();
  const rot = (x, y, k) => { // rotate clockwise by k quarter turns
    const c = Math.cos(-k * Math.PI / 2), s = Math.sin(-k * Math.PI / 2);
    return [x * c - y * s, x * s + y * c];
  };
  const q = Math.PI / 2;
  for (let k = 0; k < 4; k++) {
    const tip = rot(0, 1 - r, k);
    if (k === 0) shape.moveTo(-r * Math.sin(a), 1 - r + r * Math.cos(a));
    shape.absarc(tip[0], tip[1], r, q + a - k * q, q - a - k * q, true);
    // flank into the valley (centre cx,cy), then its mirror out to the next tip
    const c1 = rot(cx, cy, k), c2 = rot(cy, cx, k);
    const s1 = Math.atan2(-Math.cos(a), -Math.sin(a)) - k * q;
    shape.absarc(c1[0], c1[1], R, s1, 1.25 * Math.PI - k * q, false);
    shape.absarc(c2[0], c2[1], R, 1.25 * Math.PI - k * q, Math.PI / 2 - Math.atan2(-Math.cos(a), -Math.sin(a)) - k * q, false);
  }
  return shape;
}

// SVG path string (for docs / 2D checks)
export function starSvgPath(o = STAR, scale = 100) {
  const pts = starShape(o).getSpacedPoints(400);
  return 'M' + pts.map((p) => `${(p.x * scale).toFixed(2)},${(-p.y * scale).toFixed(2)}`).join('L') + 'Z';
}

// Extruded geometry, centred on the origin in z, sized so tip-to-tip width = 2 units
// (the mesh is scaled to heroWidth / 2 by the caller).
export function starGeometry(o = STAR) {
  const halfW = 1.0;
  const W = 2 * halfW;
  const depth = o.depthRatio * W;
  const bevel = o.bevelRatio * W;
  const bevelThickness = Math.min(depth * 0.48, bevel * 0.95);
  const geo = new THREE.ExtrudeGeometry(starShape(o), {
    depth: Math.max(0.001, depth - 2 * bevelThickness),
    bevelEnabled: true,
    bevelThickness,
    bevelSize: bevel,
    bevelOffset: -bevel,
    bevelSegments: o.bevelSegments,
    curveSegments: o.curveSegments,
    steps: 1,
  });
  geo.translate(0, 0, -(depth - 2 * bevelThickness) / 2);
  geo.deleteAttribute('uv');
  const smooth = toCreasedNormals(geo, THREE.MathUtils.degToRad(50));
  smooth.computeBoundingSphere();
  return smooth;
}
