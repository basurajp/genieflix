// Frame pipeline:
//   [tier-2 prepass] -> scene (MSAA, HDR, depth) -> depth of field
//   -> sub-frame accumulation (motion blur) -> output (soft shoulder, sRGB,
//      vignette, fade, dither) to the canvas.
import * as THREE from 'three';
import { POST } from './config.js';

class Quad {
  constructor(material) {
    this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.mesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
    this.scene = new THREE.Scene();
    this.scene.add(this.mesh);
  }
  render(renderer, target) {
    renderer.setRenderTarget(target);
    renderer.render(this.scene, this.camera);
  }
}

const FS_VERT = /* glsl */ `varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`;

export class Pipeline {
  constructor(renderer, width, height) {
    this.renderer = renderer;
    this.w = width;
    this.h = height;
    const hdr = { type: THREE.HalfFloatType, colorSpace: THREE.LinearSRGBColorSpace };
    this.sceneRT = new THREE.WebGLRenderTarget(width, height, {
      ...hdr,
      samples: POST.msaa,
      depthTexture: new THREE.DepthTexture(width, height, THREE.FloatType),
    });
    this.tier2RT = new THREE.WebGLRenderTarget(width, height, {
      ...hdr,
      samples: POST.msaa,
      generateMipmaps: true,
      minFilter: THREE.LinearMipmapLinearFilter,
    });
    this.dofRT = new THREE.WebGLRenderTarget(width, height, hdr);
    this.accumRT = new THREE.WebGLRenderTarget(width, height, { ...hdr, type: THREE.FloatType });

    this.dof = new Quad(
      new THREE.ShaderMaterial({
        uniforms: {
          tColor: { value: null },
          tDepth: { value: null },
          focusDist: { value: 10 },
          aperturePx: { value: 0 },
          maxBlurPx: { value: 10 },
          cameraNear: { value: 0.02 },
          cameraFar: { value: 400 },
          resolution: { value: new THREE.Vector2(width, height) },
        },
        vertexShader: FS_VERT,
        fragmentShader: /* glsl */ `
          #include <packing>
          uniform sampler2D tColor; uniform sampler2D tDepth;
          uniform float focusDist, aperturePx, maxBlurPx, cameraNear, cameraFar;
          uniform vec2 resolution;
          varying vec2 vUv;
          float coc(vec2 uv) {
            float z = -perspectiveDepthToViewZ(texture2D(tDepth, uv).x, cameraNear, cameraFar);
            return clamp(aperturePx * abs(1.0 - focusDist / max(z, 1e-3)), 0.0, maxBlurPx);
          }
          void main() {
            float c0 = coc(vUv);
            vec3 base = texture2D(tColor, vUv).rgb;
            if (c0 < 0.35) { gl_FragColor = vec4(base, 1.0); return; }
            vec3 acc = base; float wsum = 1.0;
            const int N = 40;
            for (int i = 0; i < N; i++) {
              float r = sqrt((float(i) + 0.5) / float(N)) * c0;
              float a = float(i) * 2.39996323;
              vec2 o = vec2(cos(a), sin(a)) * r / resolution;
              vec2 uv = vUv + o;
              float cs = coc(uv);
              // a sample only contributes if its own blur reaches this pixel
              float w = smoothstep(r - 1.0, r + 1.0, max(cs, c0 * 0.5));
              acc += texture2D(tColor, uv).rgb * w; wsum += w;
            }
            gl_FragColor = vec4(acc / wsum, 1.0);
          }`,
        depthTest: false,
        depthWrite: false,
      }),
    );

    this.accum = new Quad(
      new THREE.ShaderMaterial({
        uniforms: { tColor: { value: null }, weight: { value: 1 } },
        vertexShader: FS_VERT,
        fragmentShader: /* glsl */ `uniform sampler2D tColor; uniform float weight; varying vec2 vUv;
          void main(){ gl_FragColor = vec4(texture2D(tColor, vUv).rgb * weight, 1.0); }`,
        blending: THREE.CustomBlending,
        blendEquation: THREE.AddEquation,
        blendSrc: THREE.OneFactor,
        blendDst: THREE.OneFactor,
        depthTest: false,
        depthWrite: false,
      }),
    );

    this.output = new Quad(
      new THREE.ShaderMaterial({
        uniforms: {
          tColor: { value: null },
          fade: { value: 1 },
          vignette: { value: POST.vignette },
          frame: { value: 0 },
          dither: { value: POST.dither ? 1 : 0 },
          resolution: { value: new THREE.Vector2(width, height) },
        },
        vertexShader: FS_VERT,
        fragmentShader: /* glsl */ `
          uniform sampler2D tColor; uniform float fade, vignette, frame, dither; uniform vec2 resolution;
          varying vec2 vUv;
          // identity below 0.92, smooth shoulder above: keeps #FFFFFF type and
          // #00DAC4 glass honest while taming narrow specular peaks
          vec3 shoulder(vec3 x) {
            vec3 k = vec3(0.92);
            return mix(x, k + (1.0 - k) * (1.0 - exp(-(x - k) / (1.0 - k))), step(k, x));
          }
          vec3 toSRGB(vec3 c) {
            c = clamp(c, 0.0, 1.0);
            return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c));
          }
          float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233)) + frame * 0.618) * 43758.5453); }
          void main() {
            vec3 c = texture2D(tColor, vUv).rgb;
            vec2 q = vUv - 0.5; q.x *= resolution.x / resolution.y;
            c *= 1.0 - vignette * smoothstep(0.35, 1.05, length(q));
            c = shoulder(max(c, 0.0)) * fade;
            vec3 s = toSRGB(c);
            s += dither * (hash(gl_FragCoord.xy) + hash(gl_FragCoord.yx + 3.1) - 1.0) / 255.0;
            gl_FragColor = vec4(s, 1.0);
          }`,
        depthTest: false,
        depthWrite: false,
      }),
    );
  }

  get tier2Texture() {
    return this.tier2RT.texture;
  }

  // Renders one sub-frame into a linear HDR texture and returns it.
  renderSub(scene, camera, { tier2Objects = [], focusDist = 10, aperturePx = 0 }) {
    const r = this.renderer;
    const anyTier2 = tier2Objects.some((o) => o.visible);
    if (anyTier2) {
      const vis = tier2Objects.map((o) => o.visible);
      tier2Objects.forEach((o) => (o.visible = false));
      r.setRenderTarget(this.tier2RT);
      r.clear();
      r.render(scene, camera);
      tier2Objects.forEach((o, i) => (o.visible = vis[i]));
    }
    r.setRenderTarget(this.sceneRT);
    r.clear();
    r.render(scene, camera);
    if (aperturePx < 0.35) return this.sceneRT.texture;
    const u = this.dof.mesh.material.uniforms;
    u.tColor.value = this.sceneRT.texture;
    u.tDepth.value = this.sceneRT.depthTexture;
    u.focusDist.value = focusDist;
    u.aperturePx.value = aperturePx;
    u.cameraNear.value = camera.near;
    u.cameraFar.value = camera.far;
    this.dof.render(r, this.dofRT);
    return this.dofRT.texture;
  }

  // `renderAt(t)` must pose the scene and return the per-subframe options.
  frame(scene, camera, t, { subframes = 1, shutter = 0, fps = 60, fade = 1, frameIndex = 0, renderAt }) {
    const r = this.renderer;
    let tex;
    if (subframes <= 1) {
      tex = this.renderSub(scene, camera, renderAt(t));
    } else {
      r.setRenderTarget(this.accumRT);
      r.setClearColor(0x000000, 1);
      r.clear();
      const u = this.accum.mesh.material.uniforms;
      for (let k = 0; k < subframes; k++) {
        const tk = t + (shutter / fps) * ((k + 0.5) / subframes - 0.5);
        const sub = this.renderSub(scene, camera, renderAt(tk));
        u.tColor.value = sub;
        u.weight.value = 1 / subframes;
        r.autoClear = false;
        this.accum.render(r, this.accumRT);
        r.autoClear = true;
      }
      renderAt(t); // leave the scene posed at the frame's own time
      tex = this.accumRT.texture;
    }
    const o = this.output.mesh.material.uniforms;
    o.tColor.value = tex;
    o.fade.value = fade;
    o.frame.value = frameIndex % 1024;
    this.output.render(r, null);
  }
}
