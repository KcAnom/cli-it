---
description: Build a full CLI-It agent harness for the given software (7-phase pipeline)
argument-hint: <local-path-or-github-url>
---

# /cli-it — build an agent harness

You are about to build a CLI-It harness. **First, read `HARNESS.md` in the
cli-it-plugin directory completely.** It is the source of truth; this command
file only sequences the work.

## Input validation

The argument must be a **local filesystem path** or a **GitHub URL**.

- Bare software names ("blender", "gimp") are invalid — stop and ask the user
  for a path or URL. The methodology requires analyzing real code.
- If no argument was given, show usage and stop.

## Execute the phases, in order

**Phase 0 — Source acquisition and path validation.** Resolve the local path,
or `git clone --depth 1 <url>` into a working directory. Report that location
as `TARGET_PROJECT`, derive `HARNESS_PATH = TARGET_PROJECT/agent-harness`, and
identify `CLI_IT_REPO_ROOT` separately when canonical skill or registry output
is required. Before creating `<SOFTWARE>.md` or any directory, require the
lexical basename `agent-harness` and require the separately resolved harness
to equal `resolved(TARGET_PROJECT)/agent-harness`. Allow symlinked project
ancestors, but stop on a wrong basename or escaping harness/nested symlink; do
not auto-correct it. Confirm how the software is invoked (binary, API, or MCP).
Use resolved `HARNESS_PATH` for all harness-local phases below and
`CLI_IT_REPO_ROOT` only for canonical skills and registry operations.

**Phase 1 — Codebase analysis.** Investigate the source/install: backend
engine, GUI→API map, data model & file formats, existing CLI entry points,
undo system. Record findings in `<software>/agent-harness/<SOFTWARE>.md`.

**Phase 2 — CLI architecture design.** Design command groups, state model,
`--json` shapes, REPL behavior, and preview recipes. Append the design to
`<SOFTWARE>.md` before writing code.

**Phase 3 — Implementation.** Build in this order: data layer (`core/`),
probe commands, mutations with session journal, `utils/<software>_backend.py`
(the only module that touches the real software), export/render, session
file locking (`guides/session-locking.md`), and the REPL. Copy
`cli-it-plugin/repl_skin.py` verbatim to `utils/repl_skin.py`.

**Phase 4 — Test planning.** Write `tests/TEST.md` before any test code.

**Phase 5 — Test implementation.** `test_core.py` (no backend needed) and
`test_full_e2e.py` (subprocess against the installed entry point; skip
cleanly when the backend is missing).

**Phase 6 — Test documentation.** Run pytest; append real results to TEST.md.

**Phase 6.5 — SKILL.md.** Run
`python "$CLI_IT_REPO_ROOT/cli-it-plugin/skill_generator.py" "$HARNESS_PATH" --repo-root "$CLI_IT_REPO_ROOT"`.
The generator must boundary-check both destinations before dual-writing them.

**Phase 7 — Packaging.** Namespace `setup.py`
(`find_namespace_packages(include=["cli_it.*"])`, entry point
`cli-it-<software>`), then `pip install -e .` and verify `--help`, the REPL,
and `--json` output. Add the registry entry only beneath `CLI_IT_REPO_ROOT`.

## Report

Finish with: what was built, command-group inventory, test counts (honest),
skill paths, and how to install/run it.
