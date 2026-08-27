# voice-samples/

Put your voice reference here as **`voice-sample.wav`**. It is the one recording the
clone learns from — every generated line copies what it hears in this file, flaws
included. Record it once, well, and you never record narration again.

## What to record

- **1–2 minutes** of you talking normally, the way you'd narrate a reel.
  Clean matters more than long.
- **No background hum, no music, no room echo.** A quiet room, phone or laptop mic
  close to your mouth, is fine. AC rumble and reverb end up in every video.
- Talk, don't read stiffly. The clone inherits your energy along with your voice.
- Trim the file to the clearest continuous stretch — cut the throat-clearing,
  the pauses, the part where the chair squeaked.
- **The first ~10 seconds do most of the work** for the Chatterbox backend (it
  crops the rest), so lead with your best, most expressive stretch. Your accent
  is part of the voice: an Indian-English or Hindi reference gives an Indian
  voice in every language (`chatterbox_cfg_weight: 0.0` preserves it fully).

## File requirements

- Name: `voice-sample.wav` (this exact name is the default `voice_reference` in
  `pipeline/config.json`; change the config if you name it differently).
- Format: WAV. Any sample rate is fine — the pipeline converts internally.

## Privacy

This folder is gitignored (everything except this README). Your voice reference
stays on your machine and is never committed. The whole point of the local
pipeline is that nothing — script, voice, footage — leaves your disk.
