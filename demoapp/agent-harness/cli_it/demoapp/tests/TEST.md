# DemoApp harness — test plan (Phase 4, written before test code)

## Scope

Two suites, per HARNESS.md:

- `test_core.py` — **unit**: data layer, session journal + locking, and the
  Click surface via `CliRunner`. Must pass with no engine involvement.
- `test_full_e2e.py` — **e2e**: drives the installed `cli-it-demoapp` entry
  point (fallback `python -m cli_it.demoapp`) as a subprocess with the real
  engine; skips cleanly if the engine runtime is unavailable.

## Unit cases (test_core.py)

| Area | Case | Expected |
|------|------|----------|
| project | new/save/load round-trip | fields preserved; format `demoapp/v1` |
| project | load missing / malformed / wrong-format file | `ProjectError` |
| project | `apply_action` add/remove + inversion | items list correct, idempotent add |
| session | record → status | undo depth 1, redo 0; lock file valid JSON |
| session | undo/redo stack movement | pop_undo → redo grows; pop_redo → back |
| session | undo empty journal | returns None |
| session | concurrent writers (threads) | all actions journaled, file valid |
| cli | `project new` refuses overwrite | exit 1 |
| cli | `project new/info/open/save` | exit 0, JSON parses with `--json` |
| cli | `item add/list/remove` | journaled, auto-saved |
| cli | `session undo/redo` end-to-end via CliRunner | project file reflects change |
| cli | unknown item id remove | exit 1, readable message |
| cli | usage error (missing required opt) | exit 2 |

## e2e cases (test_full_e2e.py)

| Case | Expected |
|------|----------|
| entry point `--help` and `--version` | exit 0 |
| full workflow: new → add ×2 → info --json → undo → item list | counts correct at each step |
| `export run` text + json | output files exist, engine content matches items |
| `preview capture` | bundle with manifest.json/summary.json/artifacts; protocol `preview-bundle/v1` |
| REPL smoke: pipe `help\nexit\n` | banner printed, exit 0 |

## Exit-code contract

0 success · 1 command failure (ClickException) · 2 usage error.

---

## Results (Phase 6 — appended after runs)

### 2026-07-19 — initial implementation

- Environment: macOS (arm64), CPython 3.13.13 (uv-managed venv), engine
  backend available (external python process).
- `pytest demoapp/agent-harness` → **18 passed in 0.97s**
  (test_core.py 12 unit + test_full_e2e.py 5 e2e via installed
  `cli-it-demoapp` entry point + 1 backend probe; 0 skipped — engine present).
- Related suites the same day: `cli-it-hub/tests` 32 passed ·
  `cli-it-plugin/tests` 8 passed · `skill_generation/tests` 3 passed.
- Fix during bring-up: none needed in the harness; the plugin's
  `skill_generator.py` Click parser was corrected to survive multiline
  `@click.option(...)` decorators (caught by
  `cli-it-plugin/tests/test_skill_generator.py`).
