---
description: Run a CLI-It harness test suite and update TEST.md with real results
---

# /cli-it:test — run and document tests

1. Locate the harness (`*/agent-harness/`). If several, ask which.
2. Ensure it is installed: `pip install -e <harness>` if the entry point is
   missing.
3. Run the suite:

   ```bash
   pytest -q <harness>/cli_it/<software>/tests
   ```

   Run unit tests first; then e2e. Note which e2e tests skipped and why
   (missing backend is a valid skip, not a failure).
4. If tests fail: fix the code or the test (whichever is wrong), re-run until
   green or the failure is understood and documented.
5. Update `tests/TEST.md`: append a dated results section with the exact
   pytest summary line (passed/failed/skipped), environment notes (backend
   version or "not installed"), and any fixes made. **Never** report numbers
   that pytest did not print.
