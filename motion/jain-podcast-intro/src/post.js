// Post chain: MSAA HDR scene -> depth-aware background blur (distant geometry only) ->
// shutter accumulation for motion blur -> shoulder tone map, vignette, fade, dither -> canvas.
import * as THREE from 'three';

const FS_VERT = /* glsl */ `varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`;

const DOF_FRAG = /* glsl */ `
precision highp float;
varying vec2 vUv;
uniform sampler2D tColor; uniform sampler2D tDepth;
uniform vec2 resolution; uniform float near, far, focus, aperture, maxBlur, startRatio, weight;
float viewZ(float d){ float z = d * 2.0 - 1.0; return 2.0 * near * far / (far + near - z * (far - near)); }
float coc(float d){
  float z = viewZ(d);
  float s = focus * startRatio;
  return maxBlur * clamp(aperture * (z - s) / max(z, 1e-3), 0.0, 1.0);
}
void main(){
  vec4 base = texture2D(tColor, vUv);
  float c0 = coc(texture2D(tDepth, vUv).x);
  vec3 acc = base.rgb; float wsum = 1.0;
  if (c0 > 0.35) {
    const int TAPS = 20;
    for (int i = 1; i <= TAPS; i++) {
      float fi = float(i);
      float r = sqrt(fi / float(TAPS)) * c0;
      float a = fi * 2.39996323;
      vec2 off = vec2(cos(a), sin(a)) * r / resolution;
      float ct = coc(texture2D(tDepth, vUv + off).x);
      float w = smoothstep(r - 1.0, r + 0.5, ct);
      acc += texture2D(tColor, vUv + off).rgb * w; wsum += w;
    }
  }
  gl_FragColor = vec4(acc / wsum * weight, weight);
}`;

const FINAL_FRAG = /* glsl */ `
precision highp float;
varying vec2 vUv;
uniform sampler2D tAccum; uniform vec2 resolution;
uniform float exposure, vignette, fade;
// Hue-preserving shoulder: identity below 0.9 (brand colours land exactly), soft roll-off
// above, with a touch of desaturation so bright speculars on cyan go gently whiter.
vec3 shoulder(vec3 color){
  color *= exposure;
  const float k = 0.9;
  float peak = max(color.r, max(color.g, color.b));
  if (peak <= k) return color;
  float np = k + (1.0 - k) * (1.0 - exp(-(peak - k) / (1.0 - k)));
  color *= np / peak;
  float g = 1.0 - 1.0 / (0.5 * (peak - np) + 1.0);
  return mix(color, vec3(np), g);
}
vec3 srgb(vec3 c){ return mix(c * 12.92, 1.055 * pow(c, vec3(1.0/2.4)) - 0.055, step(0.0031308, c)); }
float ign(vec2 p){ return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715)))); }
void main(){
  vec3 c = texture2D(tAccum, vUv).rgb;
  c = shoulder(max(c, 0.0));
  vec2 q = vUv - 0.5; q.x *= resolution.x / resolution.y;
  c *= 1.0 - vignette * smoothstep(0.35, 1.05, length(q));
  c *= 1.0 - fade;
  c = srgb(clamp(c, 0.0, 1.0));
  c += (ign(gl_FragCoord.xy) - 0.5) / 255.0; // static dither against banding
  gl_FragColor = vec4(c, 1.0);
}`;

export class Post {
  constructor(renderer, width, height, { samples = 4 } = {}) {
    this.renderer = renderer;
    this.width = width;
    this.height = height;
    const depthTexture = new THREE.DepthTexture(width, height);
    depthTexture.type = THREE.UnsignedIntType;
    this.rtScene = new THREE.WebGLRenderTarget(width, height, {
      type: THREE.HalfFloatType, samples, depthTexture, depthBuffer: true,
    });
    this.rtAccum = new THREE.WebGLRenderTarget(width, height, { type: THREE.HalfFloatType, depthBuffer: false });
    this.quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const geo = new THREE.PlaneGeometry(2, 2);
    this.dofMat = new THREE.ShaderMaterial({
      vertexShader: FS_VERT, fragmentShader: DOF_FRAG, depthTest: false, depthWrite: false,
      uniforms: {
        tColor: { value: this.rtScene.texture }, tDepth: { value: depthTexture },
        resolution: { value: new THREE.Vector2(width, height) },
        near: { value: 0.1 }, far: { value: 100 }, focus: { value: 10 },
        aperture: { value: 0.8 }, maxBlur: { value: 6 }, startRatio: { value: 1.6 }, weight: { value: 1 },
      },
      blending: THREE.CustomBlending, blendEquation: THREE.AddEquation,
      blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor,
    });
    this.finalMat = new THREE.ShaderMaterial({
      vertexShader: FS_VERT, fragmentShader: FINAL_FRAG, depthTest: false, depthWrite: false,
      uniforms: {
        tAccum: { value: this.rtAccum.texture }, resolution: { value: new THREE.Vector2(width, height) },
        exposure: { value: 1 }, vignette: { value: 0.2 }, fade: { value: 0 },
      },
    });
    this.dofScene = new THREE.Scene();
    this.dofScene.add(new THREE.Mesh(geo, this.dofMat));
    this.finalScene = new THREE.Scene();
    this.finalScene.add(new THREE.Mesh(geo, this.finalMat));
  }

  // subframes: array of callbacks that pose the scene for each shutter sample
  render(scene, camera, subframes, { focus, aperture, maxBlur, startRatio, exposure, vignette, fade }) {
    const r = this.renderer;
    const n = subframes.length;
    Object.assign(this.dofMat.uniforms, {});
    const u = this.dofMat.uniforms;
    u.near.value = camera.near; u.far.value = camera.far;
    u.aperture.value = aperture; u.maxBlur.value = maxBlur; u.startRatio.value = startRatio;
    u.weight.value = 1 / n;
    r.setRenderTarget(this.rtAccum);
    r.setClearColor(0x000000, 0);
    r.clear(true, false, false);
    for (let i = 0; i < n; i++) {
      const f = subframes[i]();
      u.focus.value = f ?? focus;
      r.setRenderTarget(this.rtScene);
      r.setClearColor(0x000000, 1);
      r.clear(true, true, true);
      r.render(scene, camera);
      r.setRenderTarget(this.rtAccum);
      r.render(this.dofScene, this.quadCam);
    }
    const fu = this.finalMat.uniforms;
    fu.exposure.value = exposure; fu.vignette.value = vignette; fu.fade.value = fade;
    r.setRenderTarget(null);
    r.render(this.finalScene, this.quadCam);
  }
}
