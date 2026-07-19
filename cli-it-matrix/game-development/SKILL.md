---
name: cli-it-matrix-game-development
description: Capability matrix for game development asset pipelines.
version: 0.1.0
---

# Game Development matrix

```bash
cli-it matrix preflight game-development --json
```

## Capabilities

- `audio.sfx.convert` — convert/normalize sound effects (provider: ffmpeg).

## Workflow

1. Preflight; `brew install ffmpeg` closes the only bundled gap.
2. Batch-convert SFX:
   `ffmpeg -i in.wav -ar 44100 -ac 1 out.ogg` — verify each output exists.
3. Keep converted assets alongside a manifest so re-runs are idempotent.

## Known gaps

Engine harnesses (Godot, Unity headless, …) are not ported here; build them
with `/cli-it` per `cli-it-plugin/HARNESS.md` and register them so this
matrix can offer them as `harness-cli` providers.

<!-- MATRIX_SKILL_PATHS:START -->
(rendered locally by `cli-it matrix skill game-development`)
<!-- MATRIX_SKILL_PATHS:END -->
