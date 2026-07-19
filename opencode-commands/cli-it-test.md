---
description: Run a CLI-It harness test suite and update TEST.md with real results
---

Execute `cli-it-plugin/commands/test.md`: locate the harness, install it
editable if needed, run `pytest` (unit first, then e2e; missing-backend skips
are fine), fix failures, and append the exact pytest summary to
`tests/TEST.md`. Never report numbers pytest did not print.
