// The whole intro as a deterministic function of time: renderFrame(t) poses every object from
// config keys and renders. Shared by the browser preview and the frame exporter.
import * as THREE from 'three';
import { RoomEnvironment } from '../vendor/three/addons/RoomEnvironment.js';
import {
  BRAND, FORMAT, TIMING, LENS, TYPE, CREDIT, STAR, STAR_STAGE, CAMERA, STAR_PATH,
  LETTERS, ENVIRONMENT, LIGHTS, POST,
} from './config.js';
import { TimedPath, ScalarTrack, OrientationTable, smootherstep, smoothstep, clamp } from './motion.js';
import { starGeometry } from './star.js';
import { loadFont, layoutLine, letterGeometry, flatTextGeometry } from './type.js';
import { createStarMaterial, createLetterMaterial, createCharcoalMaterial, createLineMaterial } from './materials.js';
import { Post } from './post.js';

const D2R = THREE.MathUtils.degToRad;
const V = (a) => new THREE.Vector3(a[0], a[1], a[2]);

export async function createEngine(canvas, { width = FORMAT.width, height = FORMAT.height, pixelRatio = 1, baseUrl = './' } = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(pixelRatio);
  renderer.setSize(width, height, false);
  renderer.autoClear = false;
  renderer.localClippingEnabled = true;
  const W = Math.round(width * pixelRatio), H = Math.round(height * pixelRatio);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(BRAND.black);
  const pmrem = new THREE.PMREMGenerator(renderer);
  // Studio reflections are assigned per material (scene.environment would override each
  // material's envMapIntensity with one global value).
  const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  const camera = new THREE.PerspectiveCamera(30, width / height, LENS.near, LENS.far);
  camera.filmGauge = LENS.filmGauge;
  camera.setFocalLength(LENS.focalLength);

  // ---------- typography ----------
  const font = await loadFont(baseUrl + TYPE.fontUrl);
  await document.fonts?.load?.(`500 46px Inter`).catch(() => {});
  const lay1 = layoutLine(font, TYPE.title.line1, TYPE.fontSize, TYPE.tracking);
  const lay2 = layoutLine(font, TYPE.title.line2, TYPE.fontSize, TYPE.tracking);
  const capH = lay1.capHeight;
  const creditCap = CREDIT.kind === 'image' ? CREDIT.image.height : capH * (CREDIT.fontSize / TYPE.fontSize);
  const groupH = capH * 2 + TYPE.lineGap + CREDIT.gapBelowTitle + creditCap;
  const top = TYPE.groupCenterY + groupH / 2;
  const base1 = top - capH;
  const base2 = base1 - TYPE.lineGap - capH;
  const creditBase = base2 - CREDIT.gapBelowTitle - creditCap;
  const layout = { lay1, lay2, capH, top, base1, base2, creditBase, creditCap };

  const letterMat = createLetterMaterial();
  const letters = [];
  const line1 = new THREE.Group();
  scene.add(line1);
  for (const it of lay1.items) {
    const geo = letterGeometry(font, it, TYPE.fontSize);
    const mesh = new THREE.Mesh(geo, letterMat);
    const c = geo.userData.center;
    const ex = LETTERS.line1[it.ch];
    letters.push({
      mesh, ch: it.ch,
      final: new THREE.Vector3(c.x, base1 + c.y, 0),
      exploded: V(ex.p),
      exRot: new THREE.Quaternion().setFromEuler(new THREE.Euler(D2R(ex.r[1]), D2R(ex.r[0]), 0, 'YXZ')),
      size: geo.boundingBox.getSize(new THREE.Vector3()),
    });
    line1.add(mesh);
  }
  const word2 = new THREE.Group();
  scene.add(word2);
  const word2Final = new THREE.Vector3(0, base2 + capH / 2, 0);
  const word2Letters = [];
  for (const it of lay2.items) {
    const geo = letterGeometry(font, it, TYPE.fontSize);
    const mesh = new THREE.Mesh(geo, letterMat);
    const c = geo.userData.center;
    mesh.position.set(c.x, c.y - capH / 2, 0);
    word2.add(mesh);
    word2Letters.push({ mesh, base: mesh.position.clone(), size: geo.boundingBox.getSize(new THREE.Vector3()) });
  }
  const w2 = LETTERS.line2;
  const word2Ex = V(w2.p);
  const word2ExRot = new THREE.Quaternion().setFromEuler(new THREE.Euler(D2R(w2.r[1]), D2R(w2.r[0]), 0, 'YXZ'));

  // ---------- brand credit (replaceable) ----------
  const creditPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -(creditBase - 0.02));
  let credit;
  if (CREDIT.kind === 'image') {
    const img = new Image();
    img.src = baseUrl + CREDIT.image.src;
    await img.decode();
    const aspect = (img.naturalWidth || img.width) / (img.naturalHeight || img.height);
    const h = CREDIT.image.height, w = h * aspect;
    // rasterise at 4x the final on-screen size so the vector logo stays crisp
    const cv = document.createElement('canvas');
    cv.height = Math.round(h * 100 * 4);
    cv.width = Math.round(cv.height * aspect);
    cv.getContext('2d').drawImage(img, 0, 0, cv.width, cv.height);
    const tex = new THREE.CanvasTexture(cv);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 8;
    const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, clippingPlanes: [creditPlane] });
    mat.color.setScalar(CREDIT.image.boost ?? 1);
    credit = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
    credit.userData.height = h;
    credit.userData.finalY = base2 - CREDIT.gapBelowTitle - h / 2;
  } else {
    const { geometry } = flatTextGeometry(font, CREDIT.text, CREDIT.fontSize, 0);
    credit = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ color: new THREE.Color(CREDIT.color), transparent: true, opacity: CREDIT.opacity, depthWrite: false, clippingPlanes: [creditPlane], side: THREE.DoubleSide }));
    credit.userData.finalY = creditBase;
  }
  credit.position.set(0, credit.userData.finalY, TYPE.depth / 2 + 0.002);
  scene.add(credit);

  // ---------- star ----------
  const starMat = createStarMaterial();
  const star = new THREE.Group();
  const starMesh = new THREE.Mesh(starGeometry(STAR), starMat);
  star.add(starMesh);
  scene.add(star);
  const starLight = new THREE.PointLight(new THREE.Color(BRAND.cyan), LIGHTS.starGlow.intensity, LIGHTS.starGlow.distance, 2);
  scene.add(starLight);
  // sound rings: fine cyan lines that ripple from the star on musical accents
  const ringGeo = new THREE.RingGeometry(0.994, 1.0, 256, 1);
  const rings = [2.4, 3.6, 9.6].map((at) => {
    const m = new THREE.Mesh(ringGeo, createLineMaterial(BRAND.cyan, 0));
    m.material.blending = THREE.AdditiveBlending;
    m.userData.at = at;
    star.add(m);
    return m;
  });

  const stageC = V(STAR_STAGE.center);
  const stageQ0 = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, D2R(STAR_STAGE.yaw0), 0));
  const finalStarScale = STAR.finalWidth / STAR.heroWidth;
  const starFinal = new THREE.Vector3(
    lay2.width / 2 + STAR.finalGap + STAR.finalWidth / 2,
    STAR.finalAnchor === 'line1' ? base1 + capH / 2 : (top + base2) / 2,
    0.0,
  );
  layout.starFinal = starFinal;

  // ---------- environment (columns are placed after the camera path exists) ----------
  buildEnvironment(scene);

  // ---------- lights ----------
  const key = new THREE.DirectionalLight(0xffffff, LIGHTS.key.intensity);
  key.position.copy(V(LIGHTS.key.dir)).multiplyScalar(50);
  const rim = new THREE.DirectionalLight(0xf2fffd, LIGHTS.rim.intensity);
  rim.position.copy(V(LIGHTS.rim.dir)).multiplyScalar(50);
  const fill = new THREE.HemisphereLight(0xdfe8ea, 0x000000, LIGHTS.fill.intensity);
  scene.add(key, rim, fill);

  scene.traverse((o) => { if (o.material && o.material.isMeshStandardMaterial) o.material.envMap = envTex; });

  // ---------- resolve keys into tracks ----------
  const dur = FORMAT.duration;
  const starKeys = STAR_PATH.keys.map((k) => ({ t: k.t, p: k.stage ? stageC.clone() : k.final ? starFinal.clone() : V(k.p) }));
  const starPath = new TimedPath(starKeys, { smoothing: 0.08, duration: dur });
  const starScale = new ScalarTrack(STAR_PATH.keys.map((k) => [k.t, k.final ? finalStarScale : k.scale]), { smoothing: 0.08, duration: dur });
  const rotTracks = [0, 1, 2].map((j) => new ScalarTrack(STAR_PATH.rotKeys.map((k) => [k.t, k.r[j]]), { smoothing: 0.1, duration: dur }));
  const starPos = (t, out = new THREE.Vector3()) => starPath.pointAt(t, out);

  const resolve = (k) => {
    if (k.p) return V(k.p);
    if (k.orbit) {
      const [az, r, h] = k.orbit;
      return stageC.clone().add(new THREE.Vector3(Math.sin(D2R(az)) * r, h, Math.cos(D2R(az)) * r));
    }
    if (k.local) return V(k.local).multiplyScalar(STAR.heroWidth / 2).applyQuaternion(stageQ0).add(stageC);
    if (k.star) return starPos(k.t);
    throw new Error('bad key');
  };
  const camPath = new TimedPath(CAMERA.keys.map((k) => ({ t: k.t, p: resolve(k) })), { smoothing: CAMERA.smoothing, duration: dur });
  const tgtPath = new TimedPath(CAMERA.targetKeys.map((k) => ({ t: k.t, p: resolve(k) })), { smoothing: CAMERA.smoothing * 1.4, duration: dur });
  const orient = new OrientationTable((t, o) => camPath.pointAt(t, o), (t, o) => tgtPath.pointAt(t, o), {
    duration: dur, smoothing: CAMERA.smoothing, bankMaxDeg: CAMERA.bankMaxDeg, bankGain: CAMERA.bankGain,
  });

  const charMat = createCharcoalMaterial();
  const columns = ENVIRONMENT.columns.map((c) => {
    const p = camPath.pointAt(c.at), q = orient.at(c.at);
    const f = new THREE.Vector3(0, 0, -1).applyQuaternion(q).setY(0).normalize();
    const side = new THREE.Vector3(-f.z, 0, f.x);
    const pos = p.clone().addScaledVector(f, c.ahead + c.radius).addScaledVector(side, c.offset);
    charMat.envMap = envTex;
    const m = new THREE.Mesh(new THREE.CylinderGeometry(c.radius, c.radius, c.yMax - c.yMin, 128, 1, true), charMat);
    m.position.set(pos.x, (c.yMin + c.yMax) / 2, pos.z);
    scene.add(m);
    return [pos.x, pos.z, c.radius];
  });

  // ---------- pose everything at time t ----------
  const tmpQ = new THREE.Quaternion();
  const tmpV = new THREE.Vector3();
  function pose(t) {
    camPath.pointAt(t, camera.position);
    orient.at(t, camera.quaternion);
    camera.updateMatrixWorld();

    // star
    starPos(t, star.position);
    const rx = rotTracks[1].at(t), ry = rotTracks[0].at(t), rz = rotTracks[2].at(t);
    star.quaternion.setFromEuler(new THREE.Euler(D2R(rx), D2R(ry), D2R(rz), 'YXZ'));
    const pulseEnv = Math.exp(-((t - STAR.pulse.at - 0.12) ** 2) / (2 * 0.09 ** 2));
    const sc = starScale.at(t) * (1 + STAR.pulse.amount * pulseEnv);
    starMesh.scale.setScalar((STAR.heroWidth / 2) * sc);
    const su = starMat.userData.uniforms;
    // opening highlight: sweeps along the visible flank with the first accent
    su.uSweepAngle.value = D2R(118 - 105 * smootherstep(0.0, 1.5, t));
    su.uSweepAmount.value = smoothstep(0.0, 0.25, t) * (1 - smoothstep(1.2, 1.9, t));
    su.uPulse.value = STAR.pulse.light * pulseEnv;
    starLight.position.copy(star.position);
    starLight.intensity = LIGHTS.starGlow.intensity * sc;
    starLight.distance = LIGHTS.starGlow.distance * Math.max(0.35, sc);
    for (const ring of rings) {
      const a = (t - ring.userData.at) / 1.4;
      const on = a > 0 && a < 1;
      ring.visible = on;
      if (on) {
        const s = (STAR.heroWidth / 2) * sc * (0.95 + 0.85 * (1 - (1 - a) ** 2.2));
        ring.scale.setScalar(s);
        ring.material.opacity = 0.55 * (1 - a) ** 1.6 * smoothstep(0, 0.06, a);
      }
    }

    // typography assembly
    const [a0, a1] = LETTERS.assemble;
    letters.forEach((L, i) => {
      const b = smootherstep(a0 + i * 0.06, a1 - (3 - i) * 0.05, t);
      L.mesh.position.lerpVectors(L.exploded, L.final, b);
      L.mesh.quaternion.copy(L.exRot).slerp(tmpQ.identity(), b);
    });
    const typeOn = t >= LETTERS.revealAt;
    line1.visible = typeOn;
    word2.visible = typeOn;
    const b2 = smootherstep(a0 - 0.1, a1, t);
    word2.position.lerpVectors(word2Ex, word2Final, b2);
    word2.quaternion.copy(word2ExRot).slerp(tmpQ.identity(), b2);

    // credit reveal: rises through a fixed mask line and settles
    const cr = smootherstep(CREDIT.reveal[0], CREDIT.reveal[1], t);
    credit.position.y = credit.userData.finalY + (1 - cr) * (CREDIT.settleOffset - creditCap * 1.1);
    credit.visible = t > CREDIT.reveal[0] - 0.01;

    // focus follows the look target; background blur fades out for the final hold
    return tgtPath.pointAt(t, tmpV).distanceTo(camera.position);
  }

  // ---------- motion blur sample count from projected motion ----------
  const probes = [];
  function screenMotion(t, half) {
    const pts = [];
    pose(t);
    // probes: star, letter centres, and frustum corners at 3 units (captures camera rotation)
    pts.push(star.position.clone());
    for (const L of letters) pts.push(L.mesh.position.clone());
    pts.push(word2.position.clone());
    for (const [x, y] of [[-1, -1], [1, -1], [-1, 1], [1, 1], [0, 0]]) pts.push(new THREE.Vector3(x * 0.8, y * 0.8, 0.5).unproject(camera).sub(camera.position).normalize().multiplyScalar(3).add(camera.position));
    const proj = (p) => { const v = p.clone().project(camera); return v.z < 1 && Math.abs(v.x) < 1.2 && Math.abs(v.y) < 1.2 ? new THREE.Vector2(v.x * W / 2, v.y * H / 2) : null; };
    pose(t - half);
    const A = pts.map(proj);
    pose(t + half);
    const B = pts.map(proj);
    let m = 0;
    for (let i = 0; i < pts.length; i++) if (A[i] && B[i]) m = Math.max(m, A[i].distanceTo(B[i]));
    return m;
  }

  const post = new Post(renderer, W, H, { samples: 4 });

  function shutterSamples(t) {
    const mb = POST.motionBlur;
    const px = screenMotion(t, mb.shutter / FORMAT.fps / 2);
    return clamp(Math.ceil(px / mb.pxPerSample), 1, mb.maxSamples);
  }

  function renderFrame(t, { motionBlur = false } = {}) {
    const shutter = POST.motionBlur.shutter / FORMAT.fps;
    const n = motionBlur ? shutterSamples(t) : 1;
    const subs = [];
    for (let i = 0; i < n; i++) {
      const ts = n === 1 ? t : t - shutter / 2 + (shutter * (i + 0.5)) / n;
      subs.push(() => pose(ts));
    }
    const holdBlend = smoothstep(9.3, 9.8, t);
    const fadeIn = 1 - smoothstep(0.0, 0.22, t);
    const fadeOut = smoothstep(dur - TIMING.fadeOut, dur - 0.01, t);
    post.render(scene, camera, subs, {
      aperture: POST.dof.aperture * (1 - holdBlend * (1 - POST.holdDofScale)),
      maxBlur: POST.dof.maxBlurPx * pixelRatio,
      startRatio: POST.dof.startRatio,
      exposure: LIGHTS.exposure,
      vignette: POST.vignette,
      fade: Math.max(fadeIn, fadeOut),
    });
    return { samples: n };
  }

  // Diagnostics for path checks and plan views.
  function sample(t) {
    pose(t);
    return {
      cam: camera.position.toArray(),
      fwd: new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion).toArray(),
      target: tgtPath.pointAt(t).toArray(),
      star: star.position.toArray(),
      starScale: starScale.at(t),
      speed: camPath.speedAt(t),
      letters: letters.map((L) => ({ ch: L.ch, p: L.mesh.position.toArray(), half: L.size.clone().multiplyScalar(0.5).toArray(), q: L.mesh.quaternion.toArray() })),
      word2: { p: word2.position.toArray(), q: word2.quaternion.toArray(), letters: word2Letters.map((l) => ({ p: l.base.toArray(), half: l.size.clone().multiplyScalar(0.5).toArray() })) },
    };
  }

  return { renderer, scene, camera, renderFrame, shutterSamples, pose, sample, layout, duration: dur, envColumns: columns };
}

function buildEnvironment(scene) {
  const E = ENVIRONMENT;
  const cyan = new THREE.Color(BRAND.cyan), charcoal = new THREE.Color(BRAND.charcoal);

  // cyclorama: barely visible charcoal grid on a distant sphere
  const cyc = new THREE.Mesh(
    new THREE.SphereGeometry(E.cycloramaRadius, 128, 64),
    new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false,
      uniforms: { uColor: { value: charcoal }, uOpacity: { value: E.gridOpacity } },
      vertexShader: `varying vec3 vP; void main(){ vP = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
      fragmentShader: `varying vec3 vP; uniform vec3 uColor; uniform float uOpacity;
        float line(float c){ float w = fwidth(c); return 1.0 - smoothstep(0.0, w * 1.2, abs(fract(c - 0.5) - 0.5)); }
        void main(){
          float az = atan(vP.x, vP.z) / 6.2831853 * 72.0;
          float y = vP.y / 4.0;
          float l = max(line(az), line(y));
          float band = 1.0 - smoothstep(10.0, 34.0, abs(vP.y));
          gl_FragColor = vec4(uColor * l * uOpacity * band * 3.0, 1.0);
        }`,
    }),
  );
  scene.add(cyc);

  // sparse curved contours
  for (const [x, y, z, r, yaw, pitch, col, op] of E.contours) {
    const tube = 0.018 + r * 0.0022;
    const m = new THREE.Mesh(new THREE.TorusGeometry(r, tube, 8, 320), createLineMaterial(col === 'cyan' ? cyan : new THREE.Color('#3a3a3a'), op));
    m.position.set(x, y, z);
    m.rotation.set(D2R(pitch), D2R(yaw), 0, 'YXZ');
    scene.add(m);
  }

  // soft cyan atmosphere near selected edges
  for (const [x, y, z, s, op] of E.glow) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(s, s), new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      uniforms: { uColor: { value: cyan }, uOpacity: { value: op } },
      vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
      fragmentShader: `varying vec2 vUv; uniform vec3 uColor; uniform float uOpacity;
        void main(){ float d = length(vUv - 0.5) * 2.0; float a = pow(max(0.0, 1.0 - d), 2.2); gl_FragColor = vec4(uColor * a * uOpacity, 1.0); }`,
    }));
    m.position.set(x, y, z);
    scene.add(m);
  }
}
