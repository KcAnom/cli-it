# TEST.md — cli-it-buhocleaner test plan

Written before any test code (HARNESS.md phase 4).

## Ground rules

- `test_core.py` must pass on a machine **without** BuhoCleaner installed:
  it exercises the data layer, scanner (against temp dirs), session journal,
  and the Click surface via `CliRunner`, with the backend monkeypatched
  wherever a command would touch the real app.
- `test_full_e2e.py` drives the installed entry point via `subprocess`
  (resolve `cli-it-buhocleaner` from PATH, fall back to
  `python -m cli_it.buhocleaner`). Tests that need the real app
  `skipif` when `/Applications/BuhoCleaner.app` is missing. **No e2e test
  launches the GUI, quits the app, or writes its defaults domain** — GUI
  side effects are opt-in manual checks, and pref-writing is only exercised
  through the monkeypatched unit path.
- Exit codes: 0 ok, non-zero on ClickException, 2 on usage errors.

## Unit cases (no backend)

| # | Area | Case | Expect |
|---|------|------|--------|
| U1 | plan | `new_plan` enables all known categories | every CATEGORIES key present, enabled |
| U2 | plan | save → load round-trip preserves fields | equal name/categories/threshold |
| U3 | plan | load missing file | PlanError |
| U4 | plan | load wrong-format JSON | PlanError |
| U5 | plan | `apply_action` category.enabled forwards + invert | enabled flips both ways |
| U6 | plan | `apply_action` plan.threshold invert restores before | threshold_mb == before |
| U7 | plan | unknown op | PlanError |
| U8 | scanner | scan temp root with known files | exact byte total, file count |
| U9 | scanner | large-files respects threshold_mb | small file excluded |
| U10 | scanner | glob category counts only matching top-level files | .dmg counted, others not |
| U11 | scanner | missing root | exists=False, 0 bytes |
| U12 | session | record → undo → redo stack depths | 1/0 → 0/1 → 1/0 |
| U13 | session | concurrent-ish writes keep valid JSON | session file parses |
| U14 | cli | `plan new` then `plan info` | exit 0, name in output |
| U15 | cli | `plan new` refuses overwrite | non-zero, "refusing" |
| U16 | cli | `category disable` + `list --json` | enabled=false in JSON |
| U17 | cli | `category enable` unknown name | non-zero, "unknown category" |
| U18 | cli | `category threshold --mb 0` | non-zero |
| U19 | cli | `scan run` on temp roots (`category root` overrides) | JSON totals match fixture |
| U20 | cli | `session undo` after disable restores enabled | list shows enabled=true |
| U21 | cli | `session undo` with empty journal | non-zero, "nothing to undo" |
| U22 | cli | `scan report` before any scan | non-zero |
| U23 | cli | `preview capture` after scan | bundle dir + manifest + 2 artifacts |
| U24 | cli | `preview latest` before capture (fresh root) | non-zero |
| U25 | cli | `--json backend` with backend monkeypatched unavailable | available=false, install_hint |
| U26 | cli | `prefs set` journals before-value (backend mocked) | undo writes the old value back |
| U27 | backend | `write_pref` rejects non-whitelisted key | BackendError |
| U28 | backend | `open_uninstaller` rejects non-.app path | BackendError |

## E2E cases (installed entry point; real app where noted)

| # | Case | Needs app? | Expect |
|---|------|-----------|--------|
| E1 | `--help` exits 0 and lists groups | no | app/plan/category/scan/prefs listed |
| E2 | `--version` | no | 0.1.0 |
| E3 | plan new → category root overrides → scan run → report, all `--json` | no | stable JSON shapes, totals match fixture files |
| E4 | undo/redo across a disable via subprocess | no | state round-trips |
| E5 | `backend` / `app info` `--json` | yes (skipif) | available=true, version 1.16.x, helper_installed bool |
| E6 | `prefs show --json` | yes (skipif) | domain key present, keys dict non-empty |
| E7 | unknown command | no | exit 2 |

Edge cases folded in: malformed plan JSON (U4), locked-session integrity
(U13), missing scan roots (U11), missing bundle (U24).

## Results (2026-07-20, Phase 6)

Environment: macOS (Darwin 25.2.0), Python 3.13.12 venv, BuhoCleaner 1.16.2
installed at /Applications/BuhoCleaner.app (so the `needs_app` e2e cases ran
for real instead of skipping).

```
$ python -m pytest
35 passed in 2.06s
```

- test_core.py: 28/28 passed (backend monkeypatched; no real-app calls).
- test_full_e2e.py: 7/7 passed via the installed `cli-it-buhocleaner` entry
  point, including E5/E6 against the real app (probe reported version 1.16.2,
  helper_installed=true). 0 skipped, 0 failed on this machine; E5/E6 skip
  by design where the app is absent.
- Note: Homebrew Python 3.14 on this machine is broken (pyexpat dlopen
  failure); the suite was run under Python 3.13.
