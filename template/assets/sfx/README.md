# Sound effects

Short accent sounds (whoosh, pop, ding) live here. Local files only.

- Wire them in the project's `project.json`, with `at` in timeline seconds:

  ```json
  "sfx": [{"file": "assets/sfx/whoosh.wav", "at": 2.0}]
  ```

- Volume is fixed at 0.22 by the build (config key `sfx_volume`) — enough to
  register, never enough to fight the voice.
- Maximum one effect per visual beat, never stacked. `build_index.py` keeps
  the first effect that lands in each scene and warns about the rest.
