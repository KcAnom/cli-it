---
name: cli-it
description: Build agent-native CLI harnesses for real software with the CLI-It 7-phase methodology.
---

# CLI-It for Hermes

When asked to make software agent-native or build a CLI harness:

1. Obtain the CLI-It repo (`git clone https://github.com/KcAnom/cli-it`
   if needed) and read `cli-it-plugin/HARNESS.md` fully — it is the source of
   truth; do not improvise the pipeline.
2. The target must be a local path or GitHub URL (never a bare name).
3. Run the equivalent of `/cli-it` per `cli-it-plugin/commands/cli-it.md`:
   phases 0–7 in order, tests planned in TEST.md before written, SKILL.md
   generated with `skill_generator.py`, packaged as PEP 420 namespace
   `cli_it.<software>` with entry point `cli-it-<software>`.
4. Verify install + REPL + `--json` before reporting done.

Hub usage: `pip install cli-it-hub`, then `cli-it list/search/install`,
`cli-it can "<intent>" --json`, and `cli-it matrix preflight <matrix>`
(exit 3 = capability gaps, continue with what's ready).
