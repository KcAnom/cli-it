---
name: cli-it-matrix-3d-cad
description: Capability matrix for 3D and CAD work — mesh conversion patterns; parametric-modeling harnesses buildable via HARNESS.md.
version: 0.1.0
---

# 3D & CAD matrix

```bash
cli-it matrix preflight 3d-cad --json
```

## Capabilities

- `mesh.convert` — convert meshes between formats (provider: `trimesh`,
  `pip install trimesh`).

## Workflow

1. Preflight; install `trimesh` if `mesh.convert` shows a gap.
2. Convert with a short Python invocation
   (`python -c "import trimesh; trimesh.load('in.stl').export('out.obj')"`).
3. Verify the output file exists and has non-zero size.

## Known gaps

Blender/FreeCAD harnesses are not ported in this core recreation. To drive
those apps, build a harness with `/cli-it <path-to-app>` following
`cli-it-plugin/HARNESS.md`, then register it — this matrix will pick it up as
a `harness-cli` provider.

<!-- MATRIX_SKILL_PATHS:START -->
(rendered locally by `cli-it matrix skill 3d-cad`)
<!-- MATRIX_SKILL_PATHS:END -->
