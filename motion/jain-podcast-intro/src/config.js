// Single source of truth for the JAIN PODCAST intro.
// World units: 1 unit = 100 px on the title plane (z = 0) as seen from the final camera.

export const FORMAT = {
  width: 1920,
  height: 1080,
  fps: 60,
  duration: 12.0,
  frames: 720,
};

export const PALETTE = {
  cyan: '#00DAC4',
  black: '#000000',
  white: '#FFFFFF',
  charcoal: '#262626',
};

// 100 BPM, 4/4, five bars. Phase boundaries sit on bar lines.
export const TIMING = {
  bpm: 100,
  beat: 0.6,
  bar: 2.4,
  phases: {
    discover: [0.0, 2.4],
    orbit: [2.4, 4.8],
    flythrough: [4.8, 7.2],
    pullback: [7.2, 9.6],
    hold: [9.6, 12.0],
  },
  fadeOut: 0.35, // final fade to black
  // Named sync points shared by picture and sound.
  cues: {
    firstHighlight: 0.0, // opening glass accent + first reflected strip
    grooveIn: 2.4,
    ribbonSweep: 5.38, // whoosh centre; dark ribbon edge crosses the lens
    letterPass: 6.42, // movement accent; letter-edge wipe reveals PODCAST
    titleLock: 9.6, // sonic signature downbeat
    finalHighlight: 10.2, // specular glint on the star + crystalline resolution
  },
};

// Lens: 50 mm on a 36 mm-wide gate, cropped to 16:9 => ~22.9 deg vertical FOV.
export const LENS = {
  focalLength: 50,
  filmGauge: 36,
  near: 0.02,
  far: 400,
};

// Final framing. The camera sits on +z looking at the origin.
export const FINAL = {
  cameraDistance: 26.67, // 1080 px tall frame == 10.8 units at z = 0
  drift: 0.1, // tiny lateral drift during the hold (units)
};

export const TYPE = {
  fontUrl: 'vendor/fonts/Inter-Medium.ttf',
  fontFamily: 'Inter',
  fontWeight: 500,
  // Title sizing targets at 1920x1080.
  titleWidthPx: 980, // width of the PODCAST line
  trackingPx: -2, // headline letter spacing
  leading: 0.86, // baseline-to-baseline, in em
  extrude: 0.2, // shallow extrusion depth (units)
  bevelThickness: 0.012,
  bevelSize: 0.009,
  lines: ['JAIN', 'PODCAST'],
  // PODCAST lives on a second spatial plane; it is depth-compensated so it
  // aligns perfectly with line one from the final camera.
  podcastDepth: -5.0,
};

// Replaceable brand credit. Swap kind to 'image' and point src at an official
// logo file (PNG/SVG with transparency) when one is supplied.
export const BRAND_CREDIT = {
  kind: 'text', // 'text' | 'image'
  text: 'JAIN Online',
  fontSizePx: 34,
  trackingPx: 0,
  opacity: 0.82,
  src: null, // e.g. 'assets/jain-online-logo.svg'
  heightPx: 40, // used when kind === 'image'
  gapPx: 46, // distance from the PODCAST baseline to the credit's cap top
};

// Rounded four-point star (normalised: tips at (0,±1), (±1,0)).
export const STAR = {
  tipRadius: 0.11,
  shoulderAngle: 0.45, // rad; flank leaves each round tip already tapering
  valley: 0.28, // diagonal valley recess (+-0.28, +-0.28)
  flankA: 0.25, // tangent handle leaving each tip shoulder
  flankB: 0.18, // tangent handle into each valley
  samplesPerFlank: 72,
  samplesPerCap: 24,
  // Thickness ~12% of width, bevel ~3.5% of width (width = 2 in normalised space).
  depth: 0.11,
  bevelThickness: 0.065,
  bevelSize: 0.07,
  bevelOffset: -0.025,
  bevelSegments: 12,
  finalScale: 0.75,
};

export const GLASS = {
  star: {
    color: '#f6fffe',
    roughness: 0.1,
    ior: 1.47,
    thickness: 0.5, // absorption path (object units, scaled by the mesh)
    rayScale: 0.45, // share of that path used for the screen-space refraction offset
    maxOffset: 0.06, // clamp on refraction offset (fraction of frame)
    attenuationColor: '#86ece2', // #00DAC4 lifted toward white; longer paths deepen it
    attenuationDistance: 0.3,
    edgeBoost: 3.5, // extra optical path at grazing angles (thick edges read richer cyan)
    scatter: 0.11, // restrained internal scattering, cyan
    envMapIntensity: 1.7,
    specularIntensity: 1.0,
  },
  frosted: {
    color: '#f2fbfa',
    roughness: 0.36,
    ior: 1.45,
    thickness: 0.3,
    rayScale: 0.5,
    maxOffset: 0.03,
    attenuationColor: '#d6efec',
    attenuationDistance: 2.5,
    edgeBoost: 2.0,
    scatter: 0.012,
    scatterColor: '#bfe9e4',
    envMapIntensity: 0.75,
  },
  ribbon: {
    color: '#f2fbfa',
    roughness: 0.27,
    ior: 1.46,
    thickness: 0.3,
    rayScale: 0.6,
    maxOffset: 0.05,
    attenuationColor: '#5fb8ae', // the thick bead absorbs strongly and reads dark
    attenuationDistance: 0.35,
    edgeBoost: 4.0,
    scatter: 0.02,
    envMapIntensity: 0.9,
  },
};

export const POST = {
  msaa: 4,
  shutter: 0.4, // fraction of a frame (144 deg shutter, restrained)
  maxSubframes: 5,
  blurPxPerSubframe: 8.0,
  vignette: 0.12,
  dither: true,
};

export const AUDIO = {
  sampleRate: 48000,
  masterPeakDb: -1.0,
};
