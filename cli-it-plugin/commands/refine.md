---
description: Gap analysis and coverage refinement for an existing CLI-It harness
argument-hint: "[focus-area]"
---

# /cli-it:refine — improve an existing harness

Read `HARNESS.md` first. Then locate the harness in the current project
(`*/agent-harness/` directory, or ask which one if several).

## 1. Inventory coverage

Build a table of what the harness exposes today: command groups, commands,
`--json` support, preview recipes, tests per command.

## 2. Gap analysis

Compare against the software's actual capability surface (Phase 1 analysis in
`<SOFTWARE>.md` — refresh it if stale):

- GUI features with no CLI equivalent yet
- Commands lacking `--json`, error handling, or tests
- Missing undo journal coverage for mutations
- Backend calls leaking outside `utils/<software>_backend.py`
- SKILL.md drift (regenerate with `skill_generator.py` if commands changed)

## 3. Focus

If the user passed a focus area argument (e.g. "export", "filters",
"previews"), prioritize gaps in that area; otherwise rank by agent value:
probe commands > mutations > export > previews.

## 4. Implement

Close the highest-value gaps following HARNESS.md phases 3–6.5 (implement →
test plan → tests → docs → regenerate skills). Keep changes consistent with
existing command naming and JSON shapes.

Finish with a before/after coverage summary.
