// Typography: Inter Medium outlines -> shallow extruded letters, plus the
// replaceable "JAIN Online" credit plane.
import * as THREE from 'three';
import { toCreasedNormals } from 'three/addons/utils/BufferGeometryUtils.js';
import opentype from '../vendor/opentype.module.js';
import { TYPE, BRAND_CREDIT } from './config.js';

export async function loadFont(url) {
  const buf = await (await fetch(url)).arrayBuffer();
  const font = opentype.parse(buf);
  // Same file for the canvas-drawn credit, so both share the exact face.
  const face = new FontFace(TYPE.fontFamily, buf, { weight: String(TYPE.fontWeight) });
  await face.load();
  document.fonts.add(face);
  return font;
}

// Glyph outline (font units, y-up) -> THREE.Shape[] scaled to `size` units per em.
function glyphShapes(font, glyph, size) {
  const k = size / font.unitsPerEm;
  const path = new THREE.ShapePath();
  for (const c of glyph.path.commands) {
    if (c.type === 'M') path.moveTo(c.x * k, c.y * k);
    else if (c.type === 'L') path.lineTo(c.x * k, c.y * k);
    else if (c.type === 'Q') path.quadraticCurveTo(c.x1 * k, c.y1 * k, c.x * k, c.y * k);
    else if (c.type === 'C') path.bezierCurveTo(c.x1 * k, c.y1 * k, c.x2 * k, c.y2 * k, c.x * k, c.y * k);
  }
  // TrueType outers are clockwise in y-up space -> isCCW = false.
  return path.toShapes(false);
}

// Lays out one line with kerning and fixed tracking. Returns per-glyph pen
// positions and the ink bounds of the whole line (units).
export function layoutLine(font, text, size, tracking) {
  const k = size / font.unitsPerEm;
  const glyphs = font.stringToGlyphs(text);
  let pen = 0;
  const out = [];
  let inkL = Infinity;
  let inkR = -Infinity;
  glyphs.forEach((g, i) => {
    const bb = g.getBoundingBox();
    out.push({ char: text[i], glyph: g, x: pen, inkL: pen + bb.x1 * k, inkR: pen + bb.x2 * k });
    inkL = Math.min(inkL, pen + bb.x1 * k);
    inkR = Math.max(inkR, pen + bb.x2 * k);
    pen += g.advanceWidth * k + tracking;
    if (i < glyphs.length - 1) pen += font.getKerningValue(g, glyphs[i + 1]) * k;
  });
  return { glyphs: out, inkL, inkR, width: inkR - inkL };
}

// Extruded letter: white front face, charcoal back face and sides (subtle bevel).
export function buildLetter(font, glyph, size, materials) {
  const shapes = glyphShapes(font, glyph, size);
  if (!shapes.length) return null;
  let geo = new THREE.ExtrudeGeometry(shapes, {
    depth: TYPE.extrude - 2 * TYPE.bevelThickness,
    bevelEnabled: true,
    bevelThickness: TYPE.bevelThickness,
    bevelSize: TYPE.bevelSize,
    bevelSegments: 3,
    curveSegments: 14,
  });
  // ExtrudeGeometry emits, per shape: [lid group (back half, front half)], [side group].
  // Split each lid group so the back cap can be charcoal.
  const groups = [];
  for (const g of geo.groups) {
    if (g.materialIndex === 0) {
      const half = g.count / 2;
      groups.push({ start: g.start, count: half, materialIndex: 1 });
      groups.push({ start: g.start + half, count: half, materialIndex: 0 });
    } else groups.push({ start: g.start, count: g.count, materialIndex: 1 });
  }
  geo.clearGroups();
  groups.forEach((g) => geo.addGroup(g.start, g.count, g.materialIndex));
  // Front face at z = 0 so letters sit exactly on their plane.
  geo.translate(0, 0, -(TYPE.extrude - TYPE.bevelThickness));
  geo = toCreasedNormals(geo, THREE.MathUtils.degToRad(35));
  return new THREE.Mesh(geo, materials);
}

export function typeMaterials() {
  const front = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    emissive: 0xffffff,
    emissiveIntensity: 1.02,
    roughness: 0.42,
    metalness: 0,
    envMapIntensity: 0.25,
  });
  const side = new THREE.MeshStandardMaterial({
    color: 0x262626,
    roughness: 0.38,
    metalness: 0,
    envMapIntensity: 0.9,
  });
  return [front, side];
}

// --- Brand credit -----------------------------------------------------------
// A textured plane so an official logo can replace the text without touching
// the choreography. The reveal is a hard horizontal mask with the plane
// rising through it.
export async function buildCredit() {
  let tex;
  let wUnits;
  let hUnits;
  let inkTopFrac = 0; // fraction of plane height above the cap top (text mode)
  if (BRAND_CREDIT.kind === 'image' && BRAND_CREDIT.src) {
    tex = await new THREE.TextureLoader().loadAsync(BRAND_CREDIT.src);
    hUnits = BRAND_CREDIT.heightPx / 100;
    wUnits = (hUnits * tex.image.width) / tex.image.height;
  } else {
    const S = 4; // supersample the canvas for crisp edges
    const px = BRAND_CREDIT.fontSizePx * S;
    const font = `${TYPE.fontWeight} ${px}px ${TYPE.fontFamily}`;
    const c = document.createElement('canvas');
    const ctx = c.getContext('2d');
    ctx.font = font;
    if ('letterSpacing' in ctx) ctx.letterSpacing = `${BRAND_CREDIT.trackingPx * S}px`;
    const m = ctx.measureText(BRAND_CREDIT.text);
    const pad = 8 * S;
    const asc = Math.ceil(m.actualBoundingBoxAscent);
    const desc = Math.ceil(m.actualBoundingBoxDescent);
    c.width = Math.ceil(m.actualBoundingBoxLeft + m.actualBoundingBoxRight) + pad * 2;
    c.height = asc + desc + pad * 2;
    ctx.font = font;
    if ('letterSpacing' in ctx) ctx.letterSpacing = `${BRAND_CREDIT.trackingPx * S}px`;
    ctx.fillStyle = '#ffffff';
    ctx.textBaseline = 'alphabetic';
    ctx.fillText(BRAND_CREDIT.text, pad + m.actualBoundingBoxLeft, pad + asc);
    tex = new THREE.CanvasTexture(c);
    wUnits = c.width / S / 100;
    hUnits = c.height / S / 100;
    inkTopFrac = pad / c.height;
  }
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  tex.generateMipmaps = true;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      map: { value: tex },
      opacity: { value: BRAND_CREDIT.opacity },
      maskY: { value: 0 },
    },
    vertexShader: /* glsl */ `
      varying vec2 vUv; varying float vWorldY;
      void main() {
        vUv = uv;
        vec4 wp = modelMatrix * vec4(position, 1.0);
        vWorldY = wp.y;
        gl_Position = projectionMatrix * viewMatrix * wp;
      }`,
    fragmentShader: /* glsl */ `
      uniform sampler2D map; uniform float opacity; uniform float maskY;
      varying vec2 vUv; varying float vWorldY;
      void main() {
        vec4 c = texture2D(map, vUv);
        float m = step(maskY, vWorldY);
        gl_FragColor = vec4(c.rgb, c.a * opacity * m);
      }`,
    transparent: true,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(wUnits, hUnits), mat);
  mesh.renderOrder = 10;
  return { mesh, wUnits, hUnits, inkTopFrac };
}
