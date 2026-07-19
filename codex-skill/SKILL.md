---
name: cli-it
description: Build agent-native CLI harnesses for real software using the CLI-It 7-phase methodology. Trigger on "make X agent-native", "build a CLI harness for X", or "/cli-it".
---

# CLI-It for Codex

To build a harness, follow the CLI-It methodology exactly:

1. Read `cli-it-plugin/HARNESS.md` in the CLI-It repo (clone
   `https://github.com/elev8tion/cli-it` if not present) — it is the source
   of truth.
2. Require a **local path or GitHub URL** for the target software; reject
   bare names.
3. Execute the phases 0–7 as specified in
   `cli-it-plugin/commands/cli-it.md`: analysis → CLI design →
   implementation (backend module, locked sessions, ReplSkin copy) →
   TEST.md → tests → results → SKILL.md via
   `python cli-it-plugin/skill_generator.py <harness>` → namespace packaging.
4. Verify: `pip install -e <harness>` then run the entry point, the REPL, and
   `--json` output.

For refinement/testing/validation of an existing harness, follow
`commands/refine.md`, `commands/test.md`, or `commands/validate.md`
respectively. To discover installed CLI-It tooling: `pip install cli-it-hub`
then `cli-it list --json`.
