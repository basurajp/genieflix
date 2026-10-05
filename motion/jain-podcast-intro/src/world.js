// Lighting environment, background layers and glass materials.
import * as THREE from 'three';
import { PALETTE, GLASS } from './config.js';
import { rng } from './math.js';

const lin = (hex) => new THREE.Color(hex); // THREE.Color converts sRGB hex to linear working space

// --- Reflection environment -------------------------------------------------
// Black room with designed emitters: broad soft boxes for readable surfaces,
// narrow strips for moving highlights, a restrained cyan strip for tinted
// glints. Baked once into a PMREM cube.
export function buildEnvironment(renderer) {
  const env = new THREE.Scene();
  env.background = new THREE.Color(0x000000);
  const panel = (w, h, pos, color, intensity, rot = [0, 0, 0]) => {
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(intensity), side: THREE.DoubleSide }),
    );
    m.position.set(...pos);
    m.lookAt(0, 0, 0);
    m.rotateZ(rot[2]);
    env.add(m);
  };
  // broad soft key, top front left
  panel(11, 6, [-7, 9, 7], 0xffffff, 1.25);
  // broad soft fill, right
  panel(5, 9, [11, 1, 4], 0xffffff, 0.38);
  // narrow strips (the moving highlights)
  panel(0.32, 18, [-10, 1, -7], 0xffffff, 4.2);
  panel(20, 0.26, [0, 10, -3], 0xffffff, 3.2);
  panel(0.28, 14, [7, 4, 9], 0xffffff, 4.0, [0, 0, 0.6]);
  panel(0.22, 12, [-4, -2, 11], 0xffffff, 2.2, [0, 0, -0.35]);
  // rim source behind the subject
  panel(9, 0.4, [2, 3, -12], 0xffffff, 2.6, [0, 0, 0.12]);
  // restrained cyan strip, low back right
  panel(0.3, 11, [9, -5, -8], PALETTE.cyan, 2.0, [0, 0, 0.3]);
  // faint floor bounce so surfaces never go fully dead
  panel(30, 30, [0, -14, 0], 0xffffff, 0.035);
  const pmrem = new THREE.PMREMGenerator(renderer);
  const rt = pmrem.fromScene(env, 0, 0.1, 200, { size: 512 });
  pmrem.dispose();
  return rt.texture;
}

export function addLights(scene) {
  // Neutral key for typography sides; rim from behind for glass silhouettes.
  const key = new THREE.DirectionalLight(0xffffff, 0.9);
  key.position.set(-4, 6, 8);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xffffff, 1.1);
  rim.position.set(3, 4, -8);
  scene.add(rim);
  const amb = new THREE.HemisphereLight(0xffffff, 0x000000, 0.08);
  scene.add(amb);
}

// --- Glass materials --------------------------------------------------------
// Physical transmission (opacity stays 1), with three controlled changes to
// three.js's volume refraction:
//  * the screen-space ray offset and the absorption path are decoupled, and the
//    offset is clamped, so close-ups never sample off-screen (controlled distortion);
//  * edgeBoost lengthens the absorption path at grazing angles, so bevels and
//    silhouettes read as richer cyan while the face stays clear;
//  * a restrained internal-scatter term keeps thick edges faintly alive against black.
// Tier-2 glass (ribbon, panel) samples a full-scene buffer that already contains
// the star, so glass-behind-glass never vanishes.
const REFRACTION_GLSL = /* glsl */ `
uniform float edgeBoost;
uniform float rayScale;
uniform float maxOffset;
uniform vec3 scatterColor;
uniform float scatterStrength;
vec4 glassRefraction( const in vec3 n, const in vec3 v, const in float roughness, const in vec3 diffuseColor,
    const in vec3 specularColor, const in float specularF90, const in vec3 position, const in mat4 modelMatrix,
    const in mat4 viewMatrix, const in mat4 projMatrix, const in float ior, const in float thickness,
    const in vec3 attenuationColor, const in float attenuationDistance ) {
  float ndv = clamp( abs( dot( n, v ) ), 0.0, 1.0 );
  float edgeK = pow( 1.0 - ndv, 2.0 );
  vec3 ray = getVolumeTransmissionRay( n, v, thickness * rayScale, ior, modelMatrix );
  vec4 ndcPos = projMatrix * viewMatrix * vec4( position + ray, 1.0 );
  vec2 uv = ( ndcPos.xy / ndcPos.w + 1.0 ) * 0.5;
  vec2 uv0 = gl_FragCoord.xy / transmissionSamplerSize;
  vec2 off = uv - uv0;
  float len = length( off );
  if ( len > maxOffset ) off *= maxOffset / len;
  uv = clamp( uv0 + off, vec2( 0.001 ), vec2( 0.999 ) );
  vec4 light = getTransmissionSample( uv, roughness, ior );
  vec3 modelScale = vec3( length( modelMatrix[ 0 ].xyz ), length( modelMatrix[ 1 ].xyz ), length( modelMatrix[ 2 ].xyz ) );
  float absorbLen = thickness * ( modelScale.x + modelScale.y + modelScale.z ) / 3.0 * ( 1.0 + edgeBoost * edgeK );
  vec3 transmittance = diffuseColor * volumeAttenuation( absorbLen, attenuationColor, attenuationDistance );
  vec3 F = EnvironmentBRDF( n, v, specularColor, specularF90, roughness );
  vec3 scatter = scatterColor * scatterStrength * ( 0.15 + edgeK );
  float tf = ( transmittance.r + transmittance.g + transmittance.b ) / 3.0;
  return vec4( ( 1.0 - F ) * ( transmittance * light.rgb + scatter ), 1.0 - ( 1.0 - light.a ) * tf );
}
`;

function glassMaterial(p, { tier2Texture = null } = {}) {
  const m = new THREE.MeshPhysicalMaterial({
    color: lin(p.color),
    metalness: 0,
    roughness: p.roughness,
    transmission: 1,
    ior: p.ior,
    thickness: p.thickness,
    attenuationColor: lin(p.attenuationColor),
    attenuationDistance: p.attenuationDistance,
    specularIntensity: p.specularIntensity ?? 1,
    envMapIntensity: p.envMapIntensity,
  });
  const u = {
    edgeBoost: { value: p.edgeBoost },
    rayScale: { value: p.rayScale ?? 1 },
    maxOffset: { value: p.maxOffset ?? 0.08 },
    scatterColor: { value: lin(p.scatterColor ?? PALETTE.cyan) },
    scatterStrength: { value: p.scatter ?? 0 },
  };
  m.userData.uniforms = u;
  m.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, u);
    let fs = shader.fragmentShader;
    fs = fs.replace('void main() {', REFRACTION_GLSL + '\nvoid main() {');
    const call = /vec4 transmitted = getIBLVolumeRefraction\([\s\S]*?\);/;
    if (!call.test(fs)) throw new Error('three.js transmission chunk changed; update REFRACTION_GLSL hook');
    fs = fs.replace(
      call,
      `vec4 transmitted = glassRefraction( n, v, material.roughness, material.diffuseContribution, material.specularColorBlended,
        material.specularF90, pos, modelMatrix, viewMatrix, projectionMatrix, material.ior, material.thickness,
        material.attenuationColor, material.attenuationDistance );`,
    );
    if (tier2Texture) {
      fs = fs.replaceAll('transmissionSamplerMap', 'tier2Map');
      shader.uniforms.tier2Map = { value: tier2Texture };
    }
    shader.fragmentShader = fs;
  };
  m.customProgramCacheKey = () => (tier2Texture ? 'glass-tier2' : 'glass-tier1');
  return m;
}

export function starMaterial() {
  return glassMaterial(GLASS.star);
}

export function frostedMaterial(tier2Texture) {
  return glassMaterial(GLASS.frosted, { tier2Texture });
}

export function ribbonMaterial(tier2Texture) {
  return glassMaterial(GLASS.ribbon, { tier2Texture });
}

// --- Background layers ------------------------------------------------------
// Distant: an inner sphere with very subdued cyan atmosphere.
// Middle: barely visible charcoal grid + sparse curved contours at several depths.
// Thin cyan "sound lines" pulse with the music (deterministic envelope).
export function buildBackground(scene) {
  const group = new THREE.Group();
  scene.add(group);

  const sky = new THREE.Mesh(
    new THREE.SphereGeometry(180, 64, 32),
    new THREE.ShaderMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      uniforms: { cyan: { value: lin(PALETTE.cyan) } },
      vertexShader: /* glsl */ `
        varying vec3 vDir;
        void main() { vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
      fragmentShader: /* glsl */ `
        uniform vec3 cyan; varying vec3 vDir;
        void main() {
          // two soft pools of teal haze: lower right, and a fainter one upper left behind
          float a = pow(max(dot(vDir, normalize(vec3(0.55, -0.42, -0.72))), 0.0), 9.0);
          float b = pow(max(dot(vDir, normalize(vec3(-0.6, 0.35, -0.72))), 0.0), 14.0);
          float c = pow(max(dot(vDir, normalize(vec3(0.0, -0.2, 1.0))), 0.0), 6.0);
          vec3 col = cyan * (0.013 * a + 0.006 * b + 0.004 * c);
          gl_FragColor = vec4(col, 1.0);
        }`,
    }),
  );
  sky.renderOrder = -10;
  group.add(sky);

  const lineMat = (shade) =>
    new THREE.MeshBasicMaterial({ color: lin(PALETTE.charcoal).multiplyScalar(shade) });

  // Grid on a distant plane.
  const grid = new THREE.Group();
  const gz = -26;
  const gMat = lineMat(0.75);
  const spacing = 3.2;
  for (let i = -20; i <= 20; i++) {
    const v = new THREE.Mesh(new THREE.PlaneGeometry(0.035, 90), gMat);
    v.position.set(i * spacing, 0, gz);
    grid.add(v);
  }
  for (let j = -12; j <= 12; j++) {
    const h = new THREE.Mesh(new THREE.PlaneGeometry(130, 0.035), gMat);
    h.position.set(0, j * spacing, gz);
    grid.add(h);
  }
  group.add(grid);
  // Side wall grid (seen through the glass in the opening, which looks along -x).
  const side = new THREE.Group();
  for (let i = -14; i <= 14; i++) {
    const v = new THREE.Mesh(new THREE.PlaneGeometry(0.035, 70), gMat);
    v.position.set(0, 0, i * spacing);
    v.rotation.y = Math.PI / 2;
    side.add(v);
  }
  for (let j = -10; j <= 10; j++) {
    const h = new THREE.Mesh(new THREE.PlaneGeometry(90, 0.035), gMat);
    h.position.set(0, j * spacing, 0);
    h.rotation.y = Math.PI / 2;
    side.add(h);
  }
  side.position.set(-26, 0, 0);
  group.add(side);

  // Mid-ground vertical rules (parallax against the grid).
  const r = rng(7);
  const midMat = lineMat(0.85);
  for (let i = 0; i < 9; i++) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(0.02, 40), midMat);
    m.position.set(-14 + i * 3.6 + r() * 1.2, 0, -11 - r() * 3);
    group.add(m);
  }

  // Sparse curved contours (circle motif) at different depths.
  const ringMat = lineMat(1.25);
  const ring = (radius, width, pos, a0 = 0, a1 = Math.PI * 2) => {
    const m = new THREE.Mesh(new THREE.RingGeometry(radius - width / 2, radius + width / 2, 360, 1, a0, a1 - a0), ringMat);
    m.position.set(...pos);
    group.add(m);
    return m;
  };
  ring(11, 0.05, [12, 6.5, -18]);
  ring(19, 0.07, [-17, -11, -34], 0, Math.PI * 0.9);
  ring(6.5, 0.035, [-9, 7, -9], Math.PI * 1.1, Math.PI * 1.85);
  ring(4.2, 0.025, [8.5, -6.5, -6], Math.PI * 0.2, Math.PI * 1.05);

  // Sound lines: three thin cyan waveforms, low in the distance.
  const sound = new THREE.Group();
  const waves = [];
  const cyanDim = lin(PALETTE.cyan);
  for (let k = 0; k < 3; k++) {
    const N = 420;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array((N + 1) * 2 * 3), 3));
    const idx = [];
    for (let i = 0; i < N; i++) {
      const a = i * 2;
      idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
    geo.setIndex(idx);
    const mat = new THREE.MeshBasicMaterial({ color: cyanDim.clone().multiplyScalar([0.38, 0.2, 0.12][k]), side: THREE.DoubleSide });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.frustumCulled = false;
    sound.add(mesh);
    waves.push({ mesh, N, phase: k * 1.7, freq: [1.15, 1.6, 0.8][k], amp: [1, 0.7, 0.55][k], width: [0.05, 0.035, 0.03][k] });
  }
  sound.position.set(0, -8.2, -16);
  group.add(sound);

  // envelope(t) supplied by the audio module's beat map; returns 0..1
  function updateSound(t, envelope) {
    const e = envelope(t);
    for (const w of waves) {
      const pos = w.mesh.geometry.attributes.position.array;
      const L = 30;
      for (let i = 0; i <= w.N; i++) {
        const x = -L / 2 + (L * i) / w.N;
        const win = Math.pow(Math.sin((Math.PI * i) / w.N), 2.0);
        const y =
          win * w.amp * (0.12 + 0.55 * e) *
          (Math.sin(x * w.freq + t * 2.1 + w.phase) * 0.6 + Math.sin(x * w.freq * 2.7 - t * 3.3 + w.phase * 2.0) * 0.4);
        const hw = w.width / 2;
        pos[i * 6 + 0] = x; pos[i * 6 + 1] = y + hw; pos[i * 6 + 2] = 0;
        pos[i * 6 + 3] = x; pos[i * 6 + 4] = y - hw; pos[i * 6 + 5] = 0;
      }
      w.mesh.geometry.attributes.position.needsUpdate = true;
    }
  }
  return { group, updateSound };
}
