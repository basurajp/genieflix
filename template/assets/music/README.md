# Music

Background beds live here. Local files only — renders run fully offline.

- Drop a bed as `bed.wav` (any `.wav`/`.mp3` name works) and point the
  project's `project.json` at it, relative to the project folder:

  ```json
  "music": "assets/music/bed.wav"
  ```

  Leave the field empty (`""`) for no music.
- Do not pre-mix the level. `build_index.py` measures the track with ffmpeg
  `volumedetect` and computes the clip's `data-volume` so the bed sits at
  about -31 dB mean under the narration (target range -33..-30 dB).
- Use a bed at least as long as the reel (~40 s covers a five-line reel);
  a shorter file simply ends early.
- Only use tracks you are licensed to publish.
