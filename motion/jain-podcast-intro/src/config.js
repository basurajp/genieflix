// JAIN PODCAST intro: every tunable lives here.
//
// World units: 1 unit = 100 px on the title plane in the final frame. The final camera sits
// 26.667 units back with a 50 mm lens (36 mm film gauge), so 1080 px of frame height covers
// exactly 10.8 units at z = 0. Every "px" note below refers to that 1920 x 1080 design size.

export const BRAND = {
  cyan: '#00DAC4',
  black: '#000000',
  white: '#FFFFFF',
  charcoal: '#262626',
};

export const FORMAT = { width: 1920, height: 1080, fps: 60, duration: 12.0 };

// 100 BPM, 4/4: one beat = 0.6 s, one bar = 2.4 s, five bars = 12 s. Phases sit on bar lines.
export const TIMING = {
  bpm: 100,
  beat: 0.6,
  bar: 2.4,
  phases: {
    discover: [0.0, 2.4],
    orbit: [2.4, 4.8],
    flyThrough: [4.8, 7.2],
    pullback: [7.2, 9.6],
    hold: [9.6, 12.0],
  },
  cues: {
    openAccent: 0.0, // highlight starts tracing the star edge
    occlusion: 4.62, // centre of the charcoal column wipe
    flyAccent: 6.0, // fastest point of the fly-through (bar 3, beat 3)
    strokeWipe: 6.38, // letter stroke passes the lens, PODCAST revealed
    titleLock: 9.3, // typography finished aligning
    finalAccent: 9.6, // bar 5 downbeat: chime + star pulse
  },
  fadeOut: 0.35, // fade to black over the last 0.35 s
};

export const LENS = { focalLength: 50, filmGauge: 36, near: 0.04, far: 400 };

export const TYPE = {
  fontUrl: 'assets/fonts/Inter-Medium.ttf', // Inter Medium, weight 500
  title: { line1: 'JAIN', line2: 'PODCAST' },
  fontSize: 2.0, // 200 px; PODCAST measures ~937 px wide, block ~333 px tall
  tracking: -0.02, // -2 px letter spacing
  lineGap: 0.42, // JAIN baseline to PODCAST cap-top, 42 px
  depth: 0.15, // shallow extrusion
  bevelThickness: 0.018,
  bevelSize: 0.012,
  bevelSegments: 4,
  curveSegments: 18,
  frontColor: BRAND.white,
  sideColor: BRAND.charcoal,
  groupCenterY: 0.0, // vertical centre of title + credit group
};

// Brand credit under the title. `kind: 'image'` uses the official JAIN Online logo file
// (SVG is rasterised at 4x before upload, PNG works too); `kind: 'text'` falls back to plain
// "JAIN Online" in Inter Medium 46 px. Size, position and reveal are shared by both.
export const CREDIT = {
  kind: 'image',
  text: 'JAIN Online',
  fontSize: 0.46, // 46 px
  gapBelowTitle: 0.58, // PODCAST baseline to top of the credit, 58 px
  color: BRAND.white,
  opacity: 0.78,
  image: { src: 'assets/brand/jain-online-logo.svg', height: 0.6, boost: 1.15 }, // 60 px tall
  reveal: [8.55, 9.35], // clean upward mask + positional settle
  settleOffset: -0.16,
};

// Rounded four-point star. Normalised plane: tips at (0,±1), (±1,0). The outline is a closed
// run of circular arcs: a round cap on each tip and a broad concave arc on each flank, tangent
// to the cap and perpendicular to the diagonal at the valley. With these values the valleys
// land at (±0.339, ±0.339); pushing them to 0.28 needs tip caps under 0 radius or pinched arms.
export const STAR = {
  tipRadius: 0.11, // rounded tip cap radius (normalised)
  tipCapAngle: 90, // degrees either side of the tip axis covered by the cap arc
  heroWidth: 3.0, // world units, tip to tip
  depthRatio: 0.1, // total thickness = 10 % of width
  bevelRatio: 0.035, // rounded bevel = 3.5 % of width
  bevelSegments: 14,
  curveSegments: 72,
  material: {
    color: BRAND.cyan,
    roughness: 0.4,
    metalness: 0.06,
    clearcoat: 0.2,
    clearcoatRoughness: 0.16,
    emissiveIntensity: 0.07,
    envMapIntensity: 0.5,
    microBump: 0.016, // object-space micro texture strength
    microScale: 22.0,
  },
  finalWidth: 1.12, // ~112 px beside the title
  finalGap: 0.58, // gap from PODCAST right edge to star tip
  finalAnchor: 'block', // 'block' = centred on the two-line block, 'line1' = beside JAIN
  pulse: { at: 9.6, amount: 0.028, light: 0.9 },
};

// Star stage (phases 1-2). Camera positions there are given relative to this anchor.
export const STAR_STAGE = {
  center: [15.0, 1.2, 5.0],
  yaw0: -2, // degrees, star facing at t = 0
};

// Camera keys. `p` = world position. `orbit` = [azimuthDeg, radius, height] around the star
// stage centre (azimuth from +Z toward +X). `local` = position in the star's t = 0 frame.
// Arc length between keys is retimed with a monotone spline, then lightly smoothed, so speed
// stays continuous through every phase boundary.
export const CAMERA = {
  keys: [
    { t: 0.0, local: [1.02, 0.98, 0.78] },
    { t: 0.8, local: [1.38, 1.22, 1.65] },
    { t: 1.6, orbit: [37, 6.4, 1.7] },
    { t: 2.4, orbit: [23, 10.6, 1.5] },
    { t: 3.0, orbit: [7, 10.9, 0.95] },
    { t: 3.6, orbit: [-9, 10.9, 0.35] },
    { t: 4.2, orbit: [-27, 10.6, -0.3] },
    { t: 4.62, p: [7.9, 0.55, 12.15] },
    { t: 5.15, p: [6.0, 0.62, 9.3] },
    { t: 5.7, p: [3.35, 0.72, 4.75] },
    { t: 6.2, p: [1.9, 0.4, 3.2] },
    { t: 6.6, p: [0.0, -0.2, 2.2] },
    { t: 7.2, p: [-1.3, -0.7, 0.9] },
    { t: 7.75, p: [-2.0, -0.45, 3.6] },
    { t: 8.3, p: [-1.7, -0.15, 11.0] },
    { t: 8.8, p: [-1.0, 0.08, 19.5] },
    { t: 9.25, p: [-0.35, 0.03, 25.2] },
    { t: 9.6, p: [-0.16, 0.02, 26.55] },
    { t: 12.0, p: [0.16, 0.0, 26.68] },
  ],
  // Look-at target keys, same notation plus `star` (follow the star centre).
  targetKeys: [
    { t: 0.0, local: [0.42, 0.4, 0.1] },
    { t: 0.9, local: [0.3, 0.28, 0.0] },
    { t: 2.0, star: true },
    { t: 4.0, star: true },
    { t: 4.62, p: [8.6, 0.8, 2.2] },
    { t: 5.15, p: [3.2, 0.7, 2.0] },
    { t: 5.7, p: [2.3, 0.55, -0.9] },
    { t: 6.2, p: [0.7, -0.6, -2.4] },
    { t: 6.6, p: [-0.4, -4.2, -5.8] },
    { t: 7.2, p: [-0.5, -4.4, -5.8] },
    { t: 7.75, p: [-0.4, -3.0, -3.8] },
    { t: 8.3, p: [-0.3, -1.1, -1.4] },
    { t: 9.6, p: [-0.05, 0.0, 0.0] },
    { t: 12.0, p: [0.05, 0.0, 0.0] },
  ],
  smoothing: 0.09, // seconds (Gaussian sigma) applied to arc-length timing and orientation
  bankMaxDeg: 3,
  bankGain: 0.05, // degrees per unit/s² of lateral acceleration
};

// Star path after it leaves the stage: it leads the camera into the type, weaves behind the
// letters, then docks beside the title. Times in seconds; scale is relative to heroWidth.
export const STAR_PATH = {
  keys: [
    { t: 0.0, stage: true, scale: 1.0 },
    { t: 3.9, stage: true, scale: 1.0 },
    { t: 4.62, p: [11.2, 1.05, 3.4], scale: 0.8 },
    { t: 5.3, p: [3.0, 0.95, 2.6], scale: 0.48 }, // slips behind the N
    { t: 5.75, p: [1.0, 0.8, 1.2], scale: 0.4 },
    { t: 6.2, p: [0.0, -0.9, -1.8], scale: 0.38 },
    { t: 6.8, p: [1.4, -3.0, -7.2], scale: 0.35 },
    { t: 7.4, p: [3.3, -1.8, -5.0], scale: 0.355 },
    { t: 8.4, p: [5.0, 0.4, -1.4], scale: 0.365 },
    { t: 9.3, final: true },
    { t: 12.0, final: true },
  ],
  // Rotation keys in degrees [yaw, pitch, roll]; final pose is frontal.
  rotKeys: [
    { t: 0.0, r: [-2, 3, 0] },
    { t: 2.4, r: [-2, 3, 0] },
    { t: 4.6, r: [10, -3, 2] },
    { t: 6.2, r: [-24, 6, -4] },
    { t: 8.2, r: [8, -2, 1] },
    { t: 9.3, r: [0, 0, 0] },
    { t: 12.0, r: [0, 0, 0] },
  ],
};

// Exploded typography for the fly-through. Offsets/rotations are relative to the final layout.
// Letters blend to their final pose across `assemble`.
export const LETTERS = {
  assemble: [7.25, 9.3],
  line1: {
    // per-letter world position of the letter centre while exploded + [yaw, pitch] degrees
    J: { p: [-3.8, 1.0, 4.6], r: [16, 0] },
    A: { p: [1.5, 0.12, 2.0], r: [14, 0] }, // the wipe: crosses the lens at ~6.2 s
    I: { p: [2.0, 0.85, 4.9], r: [-8, 0] },
    N: { p: [4.4, 0.9, 4.75], r: [-20, 0] },
  },
  // PODCAST waits on a lower plane, tilted back like a floor, revealed as the camera dips
  line2: { p: [-0.6, -4.8, -6.0], r: [8, -38] },
  revealAt: 4.585, // typography switches on behind the column occlusion
};

// Background: barely visible charcoal grid, sparse curved contours, cyan atmosphere.
export const ENVIRONMENT = {
  cycloramaRadius: 70,
  gridOpacity: 0.09,
  // [cx, cy, cz, radius, yawDeg, pitchDeg, color, opacity]
  contours: [
    [27, 2, -9, 7.5, -38, 0, 'charcoal', 0.32],
    [33, 4, -2, 4.2, -55, 0, 'cyan', 0.16],
    [0.6, 0.4, -18, 10.5, 0, 0, 'charcoal', 0.4],
    [7.5, 2.0, -26, 15, 0, 0, 'charcoal', 0.26],
    [-9, -3, -12, 6, 10, 0, 'cyan', 0.14],
  ],
  // Rounded charcoal column the camera passes behind at the end of the orbit. It is placed
  // `ahead` units in front of the lens at time `at`, so the frame is fully covered then.
  columns: [{ at: 4.62, ahead: 1.05, offset: 0.35, radius: 1.1, yMin: -30, yMax: 30 }],
  glow: [
    // [x, y, z, size, opacity] soft cyan atmosphere planes (face +Z), kept to the edges
    [13, -7.5, -26, 22, 0.075],
    [27, -4, -15, 16, 0.05],
  ],
};

export const LIGHTS = {
  key: { dir: [-0.55, 0.75, 0.6], intensity: 1.0 },
  rim: { dir: [0.7, 0.35, -0.75], intensity: 2.6 },
  fill: { intensity: 0.2 },
  starGlow: { intensity: 2.2, distance: 9 }, // cyan bounce from the star onto nearby charcoal
  exposure: 1.0,
};

export const POST = {
  dof: { aperture: 0.9, maxBlurPx: 7, startRatio: 1.6 }, // blur only beyond 1.6x focus distance
  holdDofScale: 0.0, // final hold: everything sharp
  motionBlur: { shutter: 0.36, maxSamples: 6, pxPerSample: 4.5 }, // 130 degree shutter
  vignette: 0.22,
};

// Audio cue sheet (seconds). The score itself lives in src/audio/score.js.
export const AUDIO = {
  sampleRate: 48000,
  masterGain: 0.65,
  sfx: {
    openTone: 0.02,
    riseStart: 2.4,
    riseEnd: 4.6,
    whoosh: 4.62, // centre of the column pass, panned with the wipe
    flyAccent: 6.0,
    strokeAir: 6.38,
    chime: 9.6,
  },
  sfxGain: 0.55, // effects sit under the music
};
