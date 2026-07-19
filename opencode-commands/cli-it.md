---
description: Build a CLI-It agent harness for a local path or GitHub URL
---

Read `cli-it-plugin/HARNESS.md` fully, then execute
`cli-it-plugin/commands/cli-it.md` with the argument `$ARGUMENTS`.

Rules: the argument must be a local path or GitHub URL (reject bare software
names); follow phases 0–7 in order; TEST.md before tests; generate SKILL.md
with `python cli-it-plugin/skill_generator.py <harness>`; package as PEP 420
namespace `cli_it.<software>` with entry point `cli-it-<software>`; verify
`pip install -e` + REPL + `--json` before reporting done.
