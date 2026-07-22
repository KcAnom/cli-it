---
description: Run a CLI-It harness test suite and update TEST.md with real results
---

# /cli-it:test — run and document tests

1. Locate a candidate harness (`*/agent-harness/`). If several, ask which.
   Before reading files or making changes, derive `TARGET_PROJECT` from its
   lexical parent, require the exact `agent-harness` basename, and resolve
   parent and child separately to require a direct-child match. Reject rather
   than silently repair an invalid candidate. Reject nested `cli_it`, package,
   test, or output paths that resolve outside the validated harness. Use the
   resulting resolved `HARNESS_PATH` below.
2. Ensure it is installed: `pip install -e "$HARNESS_PATH"` if the entry point
   is missing.
3. Run the suite:

   ```bash
   pytest -q "$HARNESS_PATH/cli_it/<software>/tests"
   ```

   Run unit tests first; then e2e. Note which e2e tests skipped and why
   (missing backend is a valid skip, not a failure).
4. If tests fail: fix the code or the test (whichever is wrong), re-run until
   green or the failure is understood and documented.
5. Update `$HARNESS_PATH/cli_it/<software>/tests/TEST.md`: append a dated results section with the exact
   pytest summary line (passed/failed/skipped), environment notes (backend
   version or "not installed"), and any fixes made. **Never** report numbers
   that pytest did not print.
