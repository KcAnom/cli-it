---
name: cli-it-matrix-image-design
description: Capability matrix for image and design work — scaffold projects, convert imagery, render diagrams, generate images with real tools.
version: 0.2.0
---

# Image & Design matrix

This skill teaches an agent to do image/design work through **capabilities**,
not hardcoded tools. Before doing anything, learn what this machine can do:

```bash
cli-it matrix preflight image-design --json   # exit 3 = gaps, still usable
cli-it matrix install image-design --dry-run  # see what could be installed
cli-it can "convert image" --json             # capability lookup by intent
```

## Workflow stages

1. **Scaffold** (`project.scaffold`) — create a stateful project so every
   later mutation is undoable. Reference provider: `cli-it-demoapp`.
2. **Author** — produce or gather source assets. For text-described diagrams
   use `diagram.render` (mermaid-cli, or hand-authored SVG as the
   agent-native fallback). For novel raster imagery use `image.generate`
   (API-backed; requires `OPENAI_API_KEY`).
3. **Convert** (`image.convert`) — normalize formats/sizes with ffmpeg,
   Pillow, or macOS `sips`. Prefer whichever preflight marked ready.
4. **Verify** — after every render/convert, check the output file exists and
   is non-empty before reporting success.

## Recipes

- `diagram-to-png` — author mermaid → `diagram.render` → `image.convert`
- `design-project` — `project.scaffold`, then iterate with undo-safe edits

Install just one recipe's tooling:

```bash
cli-it matrix install image-design -r diagram-to-png --dry-run
```

## Agent guidance

- Preflight first; pick providers marked ready instead of installing eagerly.
- Exit code 3 from matrix commands means *gaps, not failure* — continue with
  the capabilities that are ready and tell the user what's missing.
- Use absolute paths for every asset; parse `--json` output rather than
  scraping human text.

<!-- MATRIX_SKILL_PATHS:START -->
(rendered locally by `cli-it matrix skill image-design`)
<!-- MATRIX_SKILL_PATHS:END -->
