---
description: Validate a harness against the HARNESS.md checklist
---

# /cli-it:validate — conformance check

Read `HARNESS.md` and locate the candidate, but perform no file reads,
installation, or checks until its path contract passes. Derive
`TARGET_PROJECT` from the candidate's lexical parent and require its basename
to be exactly `agent-harness`; resolve parent and child separately and require
the child to equal `resolved(TARGET_PROJECT)/agent-harness`. Do not repair an
invalid path. Resolve `cli_it/`, the software package, and packaged output and
reject any escape from the harness. Identify `CLI_IT_REPO_ROOT` separately and
reject canonical skill/registry destination escapes. Then verify every item
and print a pass/fail checklist with evidence (file paths, command output):

## Structure
- [ ] Validated `HARNESS_PATH` is the resolved direct child of `TARGET_PROJECT`
- [ ] Nested namespace, package, and output paths stay inside intended roots
- [ ] `<software>/agent-harness/` layout matches HARNESS.md exactly
- [ ] `cli_it/` has **no** `__init__.py` (PEP 420); `cli_it/<software>/` does
- [ ] `<SOFTWARE>.md` records analysis + architecture
- [ ] `utils/repl_skin.py` present and identical to `cli-it-plugin/repl_skin.py`

## Behavior
- [ ] No subcommand → REPL with ReplSkin banner showing the skill path
- [ ] Root `--json` produces valid JSON on probe commands
- [ ] Real-software invocation confined to `utils/<software>_backend.py`
- [ ] Missing backend produces a readable error with an install hint
- [ ] Session writes use exclusive file locking

## Tests & docs
- [ ] `TEST.md` exists with a plan section AND an appended results section
- [ ] `test_core.py` passes with the backend absent
- [ ] `test_full_e2e.py` skips cleanly (not errors) without the backend

## Skills & packaging
- [ ] `skills/cli-it-<software>/SKILL.md` (repo root) and package
      `skills/SKILL.md` exist and match
- [ ] `setup.py` uses `find_namespace_packages(include=["cli_it.*"])` and the
      `cli-it-<software>` entry point
- [ ] `pip install -e .` succeeds; entry point and `python -m cli_it.<software>` run
- [ ] Registry entry present with all required CONTRIBUTING.md fields

Report failures with the specific fix needed; offer to apply fixes.
