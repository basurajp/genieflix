// Typography: parse the real Inter Medium TTF with opentype.js, lay out glyphs with -2 px
// tracking, and extrude each letter on its own so letters can move independently.
import * as THREE from 'three';
import opentype from '../vendor/opentype/opentype.module.js';
import { toCreasedNormals } from '../vendor/three/addons/BufferGeometryUtils.js';
import { TYPE } from './config.js';

export async function loadFont(url) {
  const buf = await (await fetch(url)).arrayBuffer();
  return opentype.parse(buf);
}

function glyphShapes(font, glyph, size) {
  const s = size / font.unitsPerEm;
  const sp = new THREE.ShapePath();
  for (const c of glyph.path.commands) {
    if (c.type === 'M') sp.moveTo(c.x * s, c.y * s);
    else if (c.type === 'L') sp.lineTo(c.x * s, c.y * s);
    else if (c.type === 'Q') sp.quadraticCurveTo(c.x1 * s, c.y1 * s, c.x * s, c.y * s);
    else if (c.type === 'C') sp.bezierCurveTo(c.x1 * s, c.y1 * s, c.x2 * s, c.y2 * s, c.x * s, c.y * s);
  }
  return sp.toShapes(false);
}

// Lays out one line, centred on x = 0, baseline at y = 0. Returns per-glyph info.
export function layoutLine(font, text, size, tracking) {
  const s = size / font.unitsPerEm;
  const glyphs = [...text].map((ch) => font.charToGlyph(ch));
  let x = 0;
  const items = glyphs.map((g, i) => {
    const kern = i > 0 ? font.getKerningValue(glyphs[i - 1], g) * s : 0;
    x += kern;
    const bb = g.getBoundingBox();
    const it = { ch: text[i], glyph: g, x, x1: x + bb.x1 * s, x2: x + bb.x2 * s, y1: bb.y1 * s, y2: bb.y2 * s };
    x += g.advanceWidth * s + (i < glyphs.length - 1 ? tracking : 0);
    return it;
  });
  const left = items[0].x1, right = items[items.length - 1].x2;
  const shift = -(left + right) / 2;
  for (const it of items) { it.x += shift; it.x1 += shift; it.x2 += shift; }
  return { items, width: right - left, capHeight: (font.tables.os2.sCapHeight || 0.7275 * font.unitsPerEm) * s };
}

// Extruded letter geometry, recentred so the mesh origin is the glyph's bbox centre.
export function letterGeometry(font, item, size, o = TYPE) {
  const shapes = glyphShapes(font, item.glyph, size);
  const geo = new THREE.ExtrudeGeometry(shapes, {
    depth: o.depth - 2 * o.bevelThickness,
    bevelEnabled: true,
    bevelThickness: o.bevelThickness,
    bevelSize: o.bevelSize,
    bevelOffset: -o.bevelSize,
    bevelSegments: o.bevelSegments,
    curveSegments: o.curveSegments,
  });
  const cx = (item.x1 - item.x + (item.x2 - item.x)) / 2, cy = (item.y1 + item.y2) / 2;
  geo.translate(-cx, -cy, -(o.depth - 2 * o.bevelThickness) / 2);
  geo.deleteAttribute('uv');
  const out = toCreasedNormals(geo, THREE.MathUtils.degToRad(35));
  out.computeBoundingBox();
  out.userData.center = new THREE.Vector3(item.x + cx, cy, 0);
  return out;
}

// Flat (non-extruded) text for the brand credit.
export function flatTextGeometry(font, text, size, tracking = 0) {
  const lay = layoutLine(font, text, size, tracking);
  const geos = [];
  for (const it of lay.items) {
    const shapes = glyphShapes(font, it.glyph, size);
    if (!shapes.length) continue;
    const g = new THREE.ShapeGeometry(shapes, 10);
    g.translate(it.x, 0, 0);
    geos.push(g);
  }
  const merged = mergeSimple(geos);
  return { geometry: merged, layout: lay };
}

function mergeSimple(geos) {
  let count = 0;
  for (const g of geos) count += (g.index ? g.index.count : g.attributes.position.count);
  const pos = new Float32Array(count * 3);
  let o = 0;
  for (const g of geos) {
    const ng = g.index ? g.toNonIndexed() : g;
    pos.set(ng.attributes.position.array, o);
    o += ng.attributes.position.array.length;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  out.computeVertexNormals();
  return out;
}
