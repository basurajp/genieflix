// Materials. Procedural detail is computed from object-space coordinates so it sticks to the
// geometry and never swims or flickers between frames.
import * as THREE from 'three';
import { BRAND, STAR, TYPE } from './config.js';

const NOISE_GLSL = /* glsl */ `
float jpHash(vec3 p){ p = fract(p*0.3183099+.1); p *= 17.0; return fract(p.x*p.y*p.z*(p.x+p.y+p.z)); }
float jpNoise(vec3 x){
  vec3 i = floor(x); vec3 f = fract(x); f = f*f*(3.0-2.0*f);
  return mix(mix(mix(jpHash(i+vec3(0,0,0)),jpHash(i+vec3(1,0,0)),f.x),
                 mix(jpHash(i+vec3(0,1,0)),jpHash(i+vec3(1,1,0)),f.x),f.y),
             mix(mix(jpHash(i+vec3(0,0,1)),jpHash(i+vec3(1,0,1)),f.x),
                 mix(jpHash(i+vec3(0,1,1)),jpHash(i+vec3(1,1,1)),f.x),f.y),f.z);
}
float jpFbm(vec3 p){ return 0.6*jpNoise(p) + 0.3*jpNoise(p*2.13+7.1) + 0.1*jpNoise(p*4.7+3.3); }
`;

export function createStarMaterial() {
  const m = STAR.material;
  const mat = new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(m.color),
    roughness: m.roughness,
    metalness: m.metalness,
    clearcoat: m.clearcoat,
    clearcoatRoughness: m.clearcoatRoughness,
    emissive: new THREE.Color(m.color),
    emissiveIntensity: m.emissiveIntensity,
    envMapIntensity: m.envMapIntensity,
  });
  const uniforms = {
    uSweepAngle: { value: 0 },
    uSweepAmount: { value: 0 },
    uPulse: { value: 0 },
    uMicro: { value: m.microBump },
    uMicroScale: { value: m.microScale },
  };
  mat.userData.uniforms = uniforms;
  mat.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vObjPos;\nvarying vec3 vObjN;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvObjPos = position;\nvObjN = normal;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>
varying vec3 vObjPos; varying vec3 vObjN;
uniform float uSweepAngle, uSweepAmount, uPulse, uMicro, uMicroScale;
uniform mat3 normalMatrix;
${NOISE_GLSL}`)
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
{
  // object-space micro texture: perturb the normal along the noise gradient
  vec3 p = vObjPos * uMicroScale; float e = 0.35;
  float n0 = jpFbm(p);
  vec3 g = vec3(jpFbm(p+vec3(e,0,0))-n0, jpFbm(p+vec3(0,e,0))-n0, jpFbm(p+vec3(0,0,e))-n0) / e;
  vec3 on = normalize(vObjN);
  g -= on * dot(g, on);
  normal = normalize(normal - normalize(normalMatrix * g) * length(g) * uMicro);
}`)
      .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
{
  // narrow highlight tracing the silhouette (opening accent)
  float ang = atan(vObjPos.y, vObjPos.x);
  float d = abs(mod(ang - uSweepAngle + PI, 2.0*PI) - PI);
  float edge = 1.0 - abs(normalize(vObjN).z);
  edge = smoothstep(0.15, 0.85, edge);
  float band = exp(-d*d/(2.0*0.05*0.05));
  totalEmissiveRadiance += vec3(0.75, 1.0, 0.96) * band * edge * uSweepAmount * 2.4;
  totalEmissiveRadiance += emissive * uPulse;
}`);
  };
  return mat;
}

export function createLetterMaterial() {
  const mat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.42,
    metalness: 0.0,
    envMapIntensity: 0.45,
  });
  const uniforms = {
    uFront: { value: new THREE.Color(TYPE.frontColor) },
    uSide: { value: new THREE.Color(TYPE.sideColor) },
    uFrontGlow: { value: 0.85 },
  };
  mat.userData.uniforms = uniforms;
  mat.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying float vFront;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvFront = smoothstep(0.55, 0.92, normal.z);');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying float vFront;\nuniform vec3 uFront, uSide;\nuniform float uFrontGlow;')
      .replace('#include <color_fragment>', '#include <color_fragment>\ndiffuseColor.rgb = mix(uSide, uFront, vFront);')
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += uFront * vFront * uFrontGlow;');
  };
  return mat;
}

export function createCharcoalMaterial(opts = {}) {
  return new THREE.MeshStandardMaterial({
    color: new THREE.Color(BRAND.charcoal),
    roughness: 0.62,
    metalness: 0.0,
    envMapIntensity: 0.12,
    ...opts,
  });
}

// Thin line material for contours and sound rings.
export function createLineMaterial(color, opacity) {
  return new THREE.MeshBasicMaterial({
    color: new THREE.Color(color),
    transparent: true,
    opacity,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
}
