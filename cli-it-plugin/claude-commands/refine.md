---
description: Gap analysis and coverage refinement for an existing CLI-It harness
argument-hint: "[focus-area]"
---

# /cli-it:refine — improve an existing harness

## Asset root

Read `${CLAUDE_PLUGIN_ROOT}/HARNESS.md` first, then execute
`${CLAUDE_PLUGIN_ROOT}/commands/refine.md`. Both were written against a CLI-It
checkout: read every `cli-it-plugin/<file>`, `guides/<file>`, and
`templates/<file>` reference as `${CLAUDE_PLUGIN_ROOT}/<file>`.
`CLI_IT_REPO_ROOT` still means a real CLI-It checkout and is required only for
canonical skill or registry regeneration — if none is present, regenerate the
packaged copy only and say so.

## Focus

`$ARGUMENTS`, when given, is the focus area (e.g. "export", "filters",
"previews"): prioritize gaps there. With no argument, rank by agent value —
probe commands > mutations > export > previews.

## Guardrails

- Discover candidate `*/agent-harness/` directories; if several, ask which.
- Before any inventory or edit, require the exact `agent-harness` basename and
  prove the candidate resolves to the direct child of its `TARGET_PROJECT`.
  Reject invalid candidates rather than repairing them.
- Regenerate the skill with
  `python "${CLAUDE_PLUGIN_ROOT}/skill_generator.py" "$HARNESS_PATH"` whenever
  commands changed.

Finish with a before/after coverage summary.
