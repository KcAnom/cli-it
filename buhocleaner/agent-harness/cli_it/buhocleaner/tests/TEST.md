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

## v0.2.0 additions — GUI-driven clean (planned before test code)

Unit (backend mocked; no GUI, no deletions):

| # | Case | Expect |
|---|------|--------|
| U29 | `clean run` without `--confirm` never passes confirm=True | backend mock sees confirm=False; output says "re-run with --confirm" |
| U30 | `clean run --confirm -p` records result; undo restores metadata | plan.metadata last_clean set, undo reverts to previous value |
| U31 | `clean scan` reports found junk from mocked backend | exit 0, size string in output |
| U32 | `parse_snapshot` pure parser | buttons/texts split, "Found Junk 41.72 GB" → found_junk |
| U33 | `ui_click` rejects quote/backslash in names | BackendError |
| U34 | `clean status` with app not running (mocked) | non-zero, "not running" |

E2E: GUI cases are **opt-in only** via `BUHO_E2E_GUI=1` (E8: `clean status`
against the live window). Default runs never script the GUI and never press
Remove.

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

## Results v0.2.0 (2026-07-20, GUI-driven clean)

```
$ python -m pytest
41 passed, 1 skipped in 2.00s        # skip = E8, opt-in GUI case
$ BUHO_E2E_GUI=1 pytest ...::test_clean_status_live_window
1 passed in 1.62s                    # against the live window
```

Live manual verification: `clean scan` drove the real Flash Clean view via
accessibility scripting and reported `found_junk: 41.72 GB` with the Remove
button present — nothing was deleted (`removed: false`). `clean run
--confirm` (the destructive path) was intentionally NOT exercised by the
test suite; its gating logic is covered by U29/U30 with a mocked backend.


## 0.3.0 — doctor and the death of the appcast regex

**Appcast parsing (U35–U40).** `update_check` matched
`sparkle:shortVersionString="([^"]+)"` with a regex over raw markup. That finds a
version-looking string *anywhere* — including inside release-notes prose or a
commented-out item — and returns whichever matched first. Replaced with real XML
parsing: first channel item, version read from the item or its `<enclosure>`.
U36 is the case that proves the difference: an appcast whose description mentions
`sparkle:shortVersionString="9.9.9"` in prose. The old regex returned 9.9.9; the
parser returns the real 1.13.0. Input is size-capped (`APPCAST_MAX_BYTES`) and
`curl` is given `--max-filesize` to match.

**doctor (U41–U46).** Checks every assumption the harness makes: Info.plist and
SUFeedURL, the privileged helper, the writable defaults keys, the appcast, and —
with `--ui` — the GUI controls the cleaning flow clicks.

It reports drift and **never repairs it**. The repomix harness can re-learn a
renamed output label because repomix's JSON output supplies an independent count
to verify the new label against. Nothing here has that property: a renamed
button in a cleaning app cannot be checked against any second source, so
adopting a guessed name would mean clicking an unknown control in an app that
deletes files. U44 asserts exactly this — after seeing a snapshot containing
"Clean Now", `UI_CONTRACT` is unchanged.

**A false positive found by running it.** The first `--ui` run against the live
app reported `missing controls: Scan` on a perfectly healthy install. "Scan" and
"Remove" are mutually exclusive: Scan shows before a scan runs, Remove after it
finds something. Demanding both at once flags drift on every app that has just
scanned. The contract now carries a `requirement` — `always`, or a group name
meaning *at least one* member must be present — and Scan/Remove share the
`scan_action` group. U44b covers both being gone (real drift, fails); U44c
covers the always-required pane being gone.

### Results

```
55 passed, 1 skipped in 1.72s
```

Live against BuhoCleaner 1.16.2: `doctor --ui` → healthy, all six checks ok.
`app update-check` now also returns `latest_build` and the item title.
