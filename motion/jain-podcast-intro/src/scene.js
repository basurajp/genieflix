// Scene assembly + choreography. `pose(t)` places every object and the camera
// for an absolute time t (seconds). No state carries between frames.
import * as THREE from 'three';
import { FORMAT, TIMING, LENS, FINAL, TYPE, BRAND_CREDIT, STAR, GLASS } from './config.js';
import { Rail, VecTrack, EulerTrack, Hermite, smootherstep, smoothstep, clamp, deg } from './math.js';
import { buildStarGeometry, buildPanelGeometry, buildRibbonGeometry } from './geometry.js';
import { loadFont, layoutLine, buildLetter, typeMaterials, buildCredit } from './type.js';
import { buildEnvironment, addLights, starMaterial, frostedMaterial, ribbonMaterial, buildBackground } from './world.js';
import { musicEnvelope } from './audio.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);

export async function buildScene(renderer, pipeline) {
  const font = await loadFont(TYPE.fontUrl);
  const scene = new THREE.Scene();
  scene.environment = buildEnvironment(renderer);
  addLights(scene);
  const bg = buildBackground(scene);

  const camera = new THREE.PerspectiveCamera(30, FORMAT.width / FORMAT.height, LENS.near, LENS.far);
  camera.filmGauge = LENS.filmGauge;
  camera.setFocalLength(LENS.focalLength);

  // --- Title layout (final composition) ---------------------------------
  const D = FINAL.cameraDistance;
  const tracking = TYPE.trackingPx / 100;
  const unit = layoutLine(font, 'PODCAST', 1, 0);
  let size = (TYPE.titleWidthPx / 100) / unit.width;
  size = (TYPE.titleWidthPx / 100) / (layoutLine(font, 'PODCAST', size, tracking).width / size);
  const capH = (font.tables.os2.sCapHeight / font.unitsPerEm) * size;
  const lineGap = TYPE.leading * size;
  const credit = await buildCredit();
  const creditCapH =
    BRAND_CREDIT.kind === 'image' ? credit.hUnits : (font.tables.os2.sCapHeight / font.unitsPerEm) * (BRAND_CREDIT.fontSizePx / 100);
  // Centre the whole group (title + credit) on the frame.
  const groupH = capH + lineGap + BRAND_CREDIT.gapPx / 100 + creditCapH;
  const yb1 = groupH / 2 - capH; // baseline, line 1
  const yb2 = yb1 - lineGap; // baseline, line 2
  const creditTop = yb2 - BRAND_CREDIT.gapPx / 100;

  const mats = typeMaterials();
  const lineJ = layoutLine(font, 'JAIN', size, tracking);
  const lineP = layoutLine(font, 'PODCAST', size, tracking);
  const centreJ = (lineJ.inkL + lineJ.inkR) / 2;
  const centreP = (lineP.inkL + lineP.inkR) / 2;

  // JAIN: one pivot per letter so letters can travel and turn independently.
  const jain = lineJ.glyphs.map((g) => {
    const mesh = buildLetter(font, g.glyph, size, mats);
    const pivot = new THREE.Group();
    const cx = (g.inkL + g.inkR) / 2;
    mesh.position.set(g.x - cx, -capH / 2, 0);
    pivot.add(mesh);
    scene.add(pivot);
    return { pivot, final: V(cx - centreJ, yb1 + capH / 2, 0), char: g.char, width: g.inkR - g.inkL };
  });

  // PODCAST: a rigid word on its own plane, depth-compensated so it lands
  // exactly under JAIN from the final camera.
  const podcast = new THREE.Group();
  for (const g of lineP.glyphs) {
    const mesh = buildLetter(font, g.glyph, size, mats);
    mesh.position.set(g.x - centreP, 0, 0);
    podcast.add(mesh);
  }
  scene.add(podcast);
  const podS = (D - TYPE.podcastDepth) / D;
  const podFinal = V(0, yb2 * podS, TYPE.podcastDepth);

  // Credit
  scene.add(credit.mesh);
  const creditFinalY = creditTop - credit.hUnits / 2 + credit.inkTopFrac * credit.hUnits;
  const creditMaskY = creditFinalY - credit.hUnits / 2 + credit.inkTopFrac * credit.hUnits; // ink bottom (pad mirrored)
  credit.mesh.position.set(0, creditFinalY, 0.0);

  // --- Glass objects ------------------------------------------------------
  const star = new THREE.Mesh(buildStarGeometry(STAR), starMaterial());
  star.scale.setScalar(STAR.finalScale);
  scene.add(star);

  const titleRight = Math.max(lineP.width, lineJ.width) / 2;
  const starFinal = V(titleRight + 1.02, yb1 + capH * 0.42, 0.55);

  // Frosted panel (blur-to-clarity during the pullback).
  const panel = new THREE.Mesh(buildPanelGeometry(5.4, 3.3, 0.16), frostedMaterial(pipeline.tier2Texture));
  scene.add(panel);

  // Ribbon: built in a camera-relative frame and placed at the occlusion beat.
  const ribbonCurve = new THREE.CatmullRomCurve3(
    [V(0.18, -1.6, -0.25), V(-0.05, -0.8, 0.02), V(0.0, 0.0, 0.0), V(0.06, 0.8, -0.05), V(-0.12, 1.6, -0.35)],
    false,
    'centripetal',
  );
  const ribbonW = 0.62;
  const ribbonBead = 0.13;
  const ribbon = new THREE.Mesh(
    buildRibbonGeometry({
      curve: ribbonCurve,
      width: ribbonW,
      thickness: 0.035,
      bead: ribbonBead,
      up: [0, 0, -1],
      twist: (u) => deg(10) * Math.sin(u * Math.PI * 1.2),
    }),
    ribbonMaterial(pipeline.tier2Texture),
  );
  scene.add(ribbon);
  const beadOffset = ribbonW / 2 + Math.sqrt(ribbonBead ** 2 - 0.0175 ** 2); // bead centre from ribbon origin (local x)

  // --- Choreography -------------------------------------------------------
  const A = V(0.6, 2.0, 7.0); // where the star is discovered
  const a = (x, y, z) => [A.x + x, A.y + y, A.z + z];
  const orbit = (thetaDeg, h, r = 4.6) => a(r * Math.sin(deg(thetaDeg)), h, r * Math.cos(deg(thetaDeg)));

  // Exploded JAIN (journey pose): spread, lifted, staggered in depth, turned.
  const explode = [
    { dx: -0.25, dy: 0.55, z: -0.6, rot: [0, 16, 0] },
    { dx: 0.0, dy: 0.5, z: 1.0, rot: [0, -12, 0] },
    { dx: 0.15, dy: 0.45, z: -0.9, rot: [0, 64, 0] },
    { dx: 0.35, dy: 0.5, z: 0.55, rot: [3, -18, 0] },
  ];
  jain.forEach((L, i) => {
    const e = explode[i];
    L.journey = V(L.final.x * 1.75 + e.dx, L.final.y + e.dy, e.z);
    L.qJourney = new THREE.Quaternion().setFromEuler(new THREE.Euler(...e.rot.map(deg)));
    L.qFinal = new THREE.Quaternion();
    L.window = [7.25 + i * 0.1, 9.05 + i * 0.08];
  });
  const gapX = (jain[1].journey.x + jain[1].width * 0.5 + jain[2].journey.x - 0.15) / 2;

  const cam = new Rail(
    [
      { t: 0.0, p: orbit(100, 0.7, 0.95) },
      { p: orbit(90, 0.55, 1.9) },
      { t: 2.4, p: orbit(72, 0.32, 4.6) },
      { p: orbit(57, 0.15, 4.6) },
      { p: orbit(42, -0.02, 4.6) },
      { p: orbit(27, -0.2, 4.6) },
      { t: 4.8, p: orbit(12, -0.38, 4.6) },
      { p: [1.45, 1.8, 9.6] },
      { t: TIMING.cues.ribbonSweep, p: [1.2, 2.0, 7.4] },
      { p: [gapX + 0.55, 2.15, 3.2] },
      { t: TIMING.cues.letterPass, p: [gapX + 0.05, 2.05, 0.0] },
      { p: [gapX - 0.45, 1.7, -1.8] },
      { t: 7.2, p: [gapX - 0.75, 1.55, -3.0] },
      { p: [-0.6, 2.55, -3.25] },
      { p: [-0.6, 3.9, -2.0] },
      { p: [-0.5, 4.55, 0.8] },
      { p: [-0.4, 3.7, 6.0] },
      { p: [-0.3, 1.9, 13.0] },
      { p: [-0.2, 0.5, 20.0] },
      { t: 9.6, p: [-FINAL.drift, 0.0, D] },
      { t: 12.0, p: [FINAL.drift, 0.0, D] },
    ],
    { startSpeed: 0.5 },
  );

  const look = new Rail(
    [
      { t: 0.0, p: a(0.0, 0.68, 0.0) },
      { t: 1.2, p: a(0.0, 0.32, 0.0) },
      { t: 2.4, p: a(0, 0, 0) },
      { t: 3.6, p: a(-0.1, -0.02, -0.2) },
      { t: 4.8, p: a(-0.2, 0.05, -1.6) },
      { t: TIMING.cues.ribbonSweep, p: [gapX + 0.1, 2.15, 0.5] },
      { t: 6.0, p: [gapX - 0.2, 0.2, -6.5] },
      { t: TIMING.cues.letterPass, p: [-0.45, -2.0, -9.6] },
      { t: 7.0, p: [-0.6, -3.1, -10.6] },
      { t: 7.6, p: [-0.45, -1.9, -7.4] },
      { t: 8.3, p: [-0.2, -0.8, -4.0] },
      { t: 9.0, p: [0.0, -0.12, -1.0] },
      { t: 9.6, p: [0.0, 0.0, 0.0] },
      { t: 12.0, p: [0.0, 0.0, -0.0001] },
    ],
    { startSpeed: 0.08 },
  );

  const bank = new Hermite([
    [0, 0], [1.2, -1.0], [2.4, -0.8], [3.6, 1.4], [4.8, 0.6], [5.4, -2.2], [6.4, -1.6], [7.2, 0.4], [8.2, 2.0], [9.6, 0], [12, 0],
  ]);
  const aperture = new Hermite([
    [0, 6.5], [2.0, 4.0], [2.4, 3.6], [4.8, 2.6], [6.4, 2.4], [7.2, 2.0], [8.6, 0.8], [9.35, 0], [12, 0],
  ]);
  // reflections bloom in with the opening glass note
  const envRamp = (t) => 0.12 + 0.88 * smoothstep(0.0, 0.55, t);

  const starPath = new VecTrack([
    [0.0, [A.x, A.y, A.z]],
    [2.4, [A.x, A.y + 0.02, A.z]],
    [4.8, [A.x + 0.12, A.y + 0.06, A.z - 0.1]],
    [TIMING.cues.ribbonSweep, [2.5, 2.9, 5.7]],
    [6.0, [4.2, 3.0, 3.5]],
    [6.8, [5.6, 2.55, 2.0]],
    [7.6, [6.6, 1.9, 1.2]],
    [8.6, [starFinal.x + 0.2, starFinal.y + 0.12, starFinal.z + 0.1]],
    [9.6, [starFinal.x, starFinal.y, starFinal.z]],
    [12.0, [starFinal.x, starFinal.y, starFinal.z]],
  ]);
  const starRot = new EulerTrack([
    [0.0, [4, 64, 3]],
    [2.4, [2, 55, 1]],
    [4.8, [0, 52, 0]],
    [5.4, [-4, 40, -6]],
    [6.4, [-6, 28, -8]],
    [7.6, [-4, 22, -4]],
    [9.6, [-3, 16, 0]],
    [9.9, [-3, 16, 0]],
    [10.9, [-3, 3, 0]],
    [12.0, [-3, 2, 0]],
  ]);

  const podJourney = { p: V(-0.6, -3.9, -10.2), q: new THREE.Quaternion().setFromEuler(new THREE.Euler(deg(-74), deg(4), 0)) };
  const podWindow = [7.05, 9.35];

  // Ribbon motion, expressed in the camera frame at the sweep cue.
  const occ = (() => {
    const t = TIMING.cues.ribbonSweep;
    const c = cam.at(t);
    const l = look.at(t);
    const m = new THREE.Matrix4().lookAt(c, l, V(0, 1, 0));
    const q = new THREE.Quaternion().setFromRotationMatrix(m);
    return { pos: c, quat: q };
  })();
  const beadX = new Hermite([
    [4.75, 2.1], [5.05, 1.05], [5.27, 0.33], [TIMING.cues.ribbonSweep, 0.0], [5.5, -0.42], [5.85, -1.6],
  ], { extrapolate: true });
  const ribbonWindow = [4.75, 5.9];

  const panelPos = new VecTrack([
    [7.3, [-16, 0.3, 5.0]],
    [8.35, [-3.35, 0.05, 5.0]],
    [8.75, [-3.2, 0.05, 5.0]],
    [9.5, [-12.5, 0.4, 5.0]],
    [9.6, [-13.0, 0.4, 5.0]],
  ]);
  const panelWindow = [7.3, 9.6];

  // --- pose(t) -------------------------------------------------------------
  const L0 = new THREE.Quaternion(); // PODCAST final orientation (identity)
  const tmpQ = new THREE.Quaternion();
  const tmpV = new THREE.Vector3();
  const up = V(0, 1, 0);
  const lookM = new THREE.Matrix4();

  function poseCamera(t, out = camera) {
    cam.at(t, out.position);
    const target = look.at(t, tmpV);
    lookM.lookAt(out.position, target, up);
    out.quaternion.setFromRotationMatrix(lookM);
    out.quaternion.multiply(tmpQ.setFromAxisAngle(V(0, 0, 1), deg(bank.at(t))));
    out.updateMatrixWorld(true);
    return target;
  }

  function pose(t) {
    const target = poseCamera(t).clone();

    // star
    starPath.at(t, star.position);
    starRot.at(t, star.quaternion);
    star.material.envMapIntensity = GLASS.star.envMapIntensity * envRamp(t);

    // JAIN letters: exploded -> aligned (quaternion slerp, C2 ease)
    for (const L of jain) {
      const k = smootherstep(L.window[0], L.window[1], t);
      const breathe = (1 - k) * 0.04 * Math.sin(t * 1.3 + L.final.x);
      L.pivot.position.lerpVectors(L.journey, L.final, k);
      L.pivot.position.y += breathe;
      L.pivot.quaternion.slerpQuaternions(L.qJourney, L.qFinal, k);
    }

    // PODCAST: second plane -> aligned plane (rises and stands up)
    {
      const k = smootherstep(podWindow[0], podWindow[1], t);
      podcast.position.lerpVectors(podJourney.p, podFinal, k);
      podcast.position.y += Math.sin(Math.PI * k) * 0.6; // gentle arc
      podcast.quaternion.slerpQuaternions(podJourney.q, L0, k);
      podcast.scale.setScalar(podS);
    }

    // credit: rises through a fixed mask line
    {
      const k = smootherstep(8.95, 9.6, t);
      credit.mesh.position.y = creditFinalY - (1 - k) * (credit.hUnits * 0.9);
      credit.mesh.material.uniforms.maskY.value = creditMaskY - 0.002;
      credit.mesh.visible = t > 8.9;
    }

    // ribbon
    ribbon.visible = t >= ribbonWindow[0] && t <= ribbonWindow[1];
    if (ribbon.visible) {
      const local = V(beadX.at(t) - beadOffset, 0.0, -0.62);
      ribbon.position.copy(local.applyQuaternion(occ.quat).add(occ.pos));
      ribbon.quaternion.copy(occ.quat).multiply(tmpQ.setFromEuler(new THREE.Euler(0, deg(-8), deg(-14))));
    }

    // frosted panel
    panel.visible = t >= panelWindow[0] && t <= panelWindow[1];
    if (panel.visible) {
      panelPos.at(t, panel.position);
      panel.quaternion.setFromEuler(new THREE.Euler(deg(-4), deg(14), 0));
    }

    bg.updateSound(t, musicEnvelope);

    // depth of field: focus on whatever the camera is aimed at
    const focusDist = camera.position.distanceTo(target);
    return {
      tier2Objects: [ribbon, panel],
      focusDist,
      aperturePx: aperture.at(t),
    };
  }

  // Screen-space motion probe for adaptive motion-blur sub-frames.
  const probeCam = camera.clone();
  function motionPx(t, dt) {
    const pts = [];
    const sample = (tt) => {
      poseCamera(tt, probeCam);
      probeCam.updateProjectionMatrix();
      const r = [];
      const objs = [starPath.at(tt), look.at(tt), V(0, 0, 0)];
      if (tt >= ribbonWindow[0] && tt <= ribbonWindow[1]) {
        objs.push(V(beadX.at(tt), 0, -0.62).applyQuaternion(occ.quat).add(occ.pos));
      }
      for (const p of objs) {
        const v = p.clone().project(probeCam);
        r.push(v.z < 1 && v.z > -1 ? v : null);
      }
      return r;
    };
    const a0 = sample(t - dt / 2);
    const a1 = sample(t + dt / 2);
    let m = 0;
    a0.forEach((p, i) => {
      const q = a1[i];
      if (!p || !q) return;
      const dx = ((q.x - p.x) * FORMAT.width) / 2;
      const dy = ((q.y - p.y) * FORMAT.height) / 2;
      m = Math.max(m, Math.hypot(dx, dy));
    });
    return Math.min(m, 4000);
  }

  // Geometry clearance report (QA): minimum camera distance to every mesh.
  function clearance(t) {
    pose(t);
    const out = {};
    const check = (name, obj) => {
      if (!obj.visible) return;
      obj.updateMatrixWorld(true);
      let best = Infinity;
      obj.traverse((m) => {
        if (!m.isMesh) return;
        const pos = m.geometry.attributes.position;
        const v = new THREE.Vector3();
        const step = Math.max(1, Math.floor(pos.count / 4000));
        for (let i = 0; i < pos.count; i += step) {
          v.fromBufferAttribute(pos, i).applyMatrix4(m.matrixWorld);
          best = Math.min(best, v.distanceTo(camera.position));
        }
      });
      out[name] = best;
    };
    check('star', star);
    jain.forEach((L) => check('letter ' + L.char, L.pivot));
    check('PODCAST', podcast);
    check('ribbon', ribbon);
    check('panel', panel);
    return out;
  }

  const info = {
    fontSize: size,
    capHeightPx: capH * 100,
    titleWidthPx: lineP.width * 100,
    jainWidthPx: lineJ.width * 100,
    blockHeightPx: (capH + lineGap) * 100,
    creditGapPx: BRAND_CREDIT.gapPx,
    starFinal: starFinal.toArray(),
    camLength: cam.length,
  };

  return { scene, camera, pose, motionPx, clearance, info };
}
