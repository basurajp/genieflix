# LTX-2 integration — photoreal talking avatar, locally

[LTX-2](https://github.com/Lightricks/LTX-2) (Lightricks) is an open-weights
audio-video foundation model: it generates video **with synchronized audio**,
including a person speaking scripted lines with matching lip movement. Paired
with this repo it closes the one gap the local pipeline has — a photoreal
presenter — without a hosted avatar subscription.

Two ways to use it here:

1. **A2Vid (the good one).** LTX-2's audio-to-video pipeline generates a person
   speaking, conditioned on an audio file you supply. Your pipeline already
   produces that audio: the cloned-voice, loudness-normalized line WAVs in each
   project's `audio/` folder. Export them with `export_a2vid.py`, generate one
   clip per line, and the avatar speaks **in your voice**.
2. **Text-to-video b-roll.** The Distilled/DFR pipelines turn a cinematographer-
   style prompt into a clip with sound — spectacle footage for hooks.

## Hardware reality (read first)

LTX-2.5 is a 22B transformer plus a 12B text encoder — roughly **66 GB of
weights, NVIDIA CUDA only**. It does not run on a Mac. Realistic setups:

- A desktop/server NVIDIA GPU (24 GB+ VRAM using `--quantization fp8-cast
  --offload cpu`; comfortable at 48 GB+).
- A rented GPU box (RunPod, Vast, Lambda) for batch sessions — per-hour cost,
  still no per-video vendor fee and nothing uploaded to an avatar service.
- [ComfyUI-LTXVideo](https://github.com/Lightricks/ComfyUI-LTXVideo) if you
  prefer a graph UI over the CLI.

Everything else in this repo stays Mac-friendly; LTX-2 is an optional hero lane.

## Setup (on the GPU machine)

```bash
git clone https://github.com/Lightricks/LTX-2.git
cd LTX-2
uv sync --extra natten
hf auth login    # accept the model terms on the LTX-2.5 Hugging Face page first
hf download Lightricks/LTX-2.5 \
    diffusion_models/ltx-2.5-22b-distilled-transformer-bf16.safetensors \
    text_encoders/gemma4-12b-with-proj-ltx-2.5-bf16.safetensors \
    vae/ltx-2.5-video-vae-bf16.safetensors \
    vae/ltx-2.5-audio-vae-bf16.safetensors \
    latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors \
    --local-dir models/ltx-2.5
```

A2Vid additionally uses the full (dev) transformer and the distilled LoRA — see
"Available Pipelines" in the LTX-2 README for the exact files its
`A2VidPipelineTwoStage` expects; flags move between releases, so treat the LTX-2
docs as the authority on the generation command itself.

## Workflow: your voice → photoreal avatar reel

On this machine (any OS):

```bash
# after a project's voice phase has run (audio/lineNN.wav exists):
python3 integrations/ltx2/export_a2vid.py --project factory/building/<slug> \
    --presenter "a young woman with shoulder-length dark hair, warm smile, plain studio background"
```

This writes `<project>/a2vid/`: one 48 kHz conditioning WAV per line, one
prompt file per line (presenter description + delivery notes, cinematographer
style), and `manifest.json` with the suggested frame count per clip
(8n+1 at 24 fps — the model's native shape). Lines are exported *per line*, not
as one long file: LTX-2 clips are strongest under ~10 seconds, and one clip per
line maps exactly onto this pipeline's scene structure.

On the GPU machine, generate one clip per line with the A2Vid pipeline, using
each line's WAV as the conditioning audio and its prompt file as the prompt.
Copy the resulting `lineNN.mp4` files back into the project, then:

```bash
python3 integrations/ltx2/stage_footage.py --project factory/building/<slug> --clips path/to/clips
```

This re-encodes every clip with dense keyframes (`-g 30 -keyint_min 30` — seeks
freeze without this, see PLAYBOOK.md), strips its audio track (the composition
plays your processed voice WAVs; keeping both would double the narration), and
installs them as `assets/footage/lineNN.mp4`.

Rebuild and render as usual:

```bash
python3 pipeline/build_index.py --project factory/building/<slug>
python3 pipeline/make_reel.py --project factory/building/<slug> --phase render
```

`build_index.py` uses `assets/footage/lineNN.mp4` for any scene that has one
(muted `<video>` clips, opacity/transform animation only) and falls back to the
scene's slide image otherwise — so a project can mix avatar scenes with slide
scenes freely.

## Notes

- The composition, captions, safe zones, QA gates, and the 10% finish pass are
  unchanged — LTX-2 only replaces what fills the scene visual.
- Keep generated clips at least as long as the line's audio (the manifest's
  frame counts already include headroom); `stage_footage.py` warns when a clip
  runs short.
- Weights are gated on Hugging Face (free — accept the terms once). Check the
  model license for your commercial context.
