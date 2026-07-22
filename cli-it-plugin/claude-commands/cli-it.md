---
description: Build a full CLI-It agent harness for the given software (7-phase pipeline)
argument-hint: <local-path-or-github-url>
---

# /cli-it — build an agent harness

## Asset root

Every CLI-It asset ships inside this plugin. Resolve them from
`${CLAUDE_PLUGIN_ROOT}` — never relative to the user's working directory:

- methodology: `${CLAUDE_PLUGIN_ROOT}/HARNESS.md`
- procedure: `${CLAUDE_PLUGIN_ROOT}/commands/cli-it.md`
- REPL skin: `${CLAUDE_PLUGIN_ROOT}/repl_skin.py`
- skill generator: `${CLAUDE_PLUGIN_ROOT}/skill_generator.py`
- preview bundler: `${CLAUDE_PLUGIN_ROOT}/preview_bundle.py`
- guides + templates: `${CLAUDE_PLUGIN_ROOT}/guides/`, `${CLAUDE_PLUGIN_ROOT}/templates/`

Those documents were written against a CLI-It checkout, so they spell asset
paths as `cli-it-plugin/<file>`, `guides/<file>`, and `templates/<file>`.
**Read every one of those as `${CLAUDE_PLUGIN_ROOT}/<file>`.** The sole
exception is `CLI_IT_REPO_ROOT`, which stays what the methodology says it is:
a real CLI-It checkout, required only for canonical skill and registry writes.
If canonical output is requested and no such checkout is present, say so and
write the packaged copy only — do not invent a repo root.

## Input validation

`$ARGUMENTS` must be a **local filesystem path** or a **GitHub URL**.

- No argument → print usage and stop.
- A bare software name ("blender", "gimp") → stop and ask for a path or URL.
  The methodology needs real source; it cannot be run from a name.
- Anything else that is neither an existing path nor `https://github.com/…`
  → stop and say why.

## Execute

Read `${CLAUDE_PLUGIN_ROOT}/HARNESS.md` in full, then execute
`${CLAUDE_PLUGIN_ROOT}/commands/cli-it.md` against `$ARGUMENTS`, applying the
path remapping above. Run phases 0–7 in order; do not skip or reorder them.

Non-negotiables from the methodology, restated so they are not lost:

- `HARNESS_PATH` must be the resolved direct child `TARGET_PROJECT/agent-harness`,
  with the exact `agent-harness` basename. Reject a mismatch; never auto-correct it.
- `tests/TEST.md` is written **before** any test code.
- Only `utils/<software>_backend.py` touches the real software.
- Copy `${CLAUDE_PLUGIN_ROOT}/repl_skin.py` verbatim to `utils/repl_skin.py`.
- Generate the skill with
  `python "${CLAUDE_PLUGIN_ROOT}/skill_generator.py" "$HARNESS_PATH"`, adding
  `--repo-root "$CLI_IT_REPO_ROOT"` only when a real checkout owns the
  canonical copy.
- Package as PEP 420 namespace `cli_it.<software>` with entry point
  `cli-it-<software>`; verify `pip install -e .`, `--help`, the REPL, and
  `--json` before reporting done.

## Report

Finish with: what was built, the command-group inventory, test counts taken
verbatim from pytest output, skill paths, and how to install and run it.
