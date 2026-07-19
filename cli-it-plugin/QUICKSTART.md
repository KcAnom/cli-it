# Quickstart: build your first harness

This walkthrough builds a harness for a hypothetical app in ~30 agent-minutes.

## 1. Install the plugin

Claude Code: `/plugin marketplace add elev8tion/cli-it` → `/plugin install cli-it`.
Pi: `bash .pi-extension/cli-it/install.sh` from the repo root.

## 2. Point the agent at real software

```text
/cli-it /Applications/MyApp.app          # local install
/cli-it https://github.com/org/myapp     # or source repo
```

Bare names are rejected on purpose — the methodology requires analyzing the
actual code/install (Phase 0–1).

## 3. What the agent does

1. Reads `HARNESS.md` end to end.
2. Analyzes the software: backend engine, GUI→API map, data model, undo.
3. Designs the CLI (`<SOFTWARE>.md`), then implements
   `myapp/agent-harness/cli_it/myapp/…` with core/, utils/myapp_backend.py,
   locked sessions, and the shared ReplSkin.
4. Writes `TEST.md`, then `test_core.py` + `test_full_e2e.py`, runs pytest,
   appends results.
5. Generates SKILL.md via `skill_generator.py` (root + package copies).
6. Packages with namespace `setup.py` and verifies
   `pip install -e . && cli-it-myapp --help`.

## 4. Try it

```bash
cli-it-myapp                     # REPL with banner + skill path
cli-it-myapp project new -o /tmp/proj.json
cli-it-myapp --json project info -p /tmp/proj.json
```

## 5. Ship it

Add a `registry.json` entry (CONTRIBUTING.md), then optionally publish to
PyPI (PUBLISHING.md). The `demoapp/agent-harness` in this repo is the living
reference for every convention above.
