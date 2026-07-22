---
description: Run a CLI-It harness test suite and update TEST.md with real results
---

# /cli-it:test — run and document tests

## Asset root

Execute `${CLAUDE_PLUGIN_ROOT}/commands/test.md`, reading every
`cli-it-plugin/<file>` reference in it as `${CLAUDE_PLUGIN_ROOT}/<file>`.
Consult `${CLAUDE_PLUGIN_ROOT}/HARNESS.md` if the harness layout is unclear.

## Guardrails

- Locate a candidate `*/agent-harness/`; if several, ask which. Validate the
  path contract (exact `agent-harness` basename, resolved direct child of
  `TARGET_PROJECT`) before reading or writing anything. Reject, do not repair.
- Install if the entry point is missing: `pip install -e "$HARNESS_PATH"`.
- Unit tests first, then e2e. A missing backend is a legitimate **skip**, not
  a failure — record which tests skipped and why.
- If tests fail, fix whichever is wrong (code or test) and re-run until green,
  or document the failure precisely.
- Append a dated results section to
  `$HARNESS_PATH/cli_it/<software>/tests/TEST.md` containing the exact pytest
  summary line and environment notes. **Never report a number pytest did not
  print.**
