---
description: Gap analysis and coverage refinement for an existing CLI-It harness
argument-hint: "[focus-area]"
---

# /cli-it:refine — improve an existing harness

Read `HARNESS.md` first. Discover candidate `*/agent-harness/` directories (or
ask which one if several), then derive each candidate's `TARGET_PROJECT` from
its lexical parent. Before inventory or edits, require the exact
`agent-harness` basename and separately resolve parent and child to prove the
candidate is the resolved direct child. Reject rather than repair invalid
candidates, including escaping `cli_it`, package, or output symlinks. Use the
validated resolved `HARNESS_PATH` for every harness-local read and change.
Identify `CLI_IT_REPO_ROOT` separately if canonical output is regenerated.

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
existing command naming and JSON shapes. Regenerate packaged output beneath
`HARNESS_PATH`; regenerate canonical output only through the separately
validated `CLI_IT_REPO_ROOT`, with both destinations preflighted.

Finish with a before/after coverage summary.
