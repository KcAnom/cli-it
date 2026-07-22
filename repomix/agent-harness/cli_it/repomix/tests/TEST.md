# TEST.md — cli-it-repomix

Written **before** the test code (HARNESS.md phase 4). Two suites:

- `test_core.py` — pure unit tests. Must pass on a machine with **no repomix
  installed**: the data layer, the locked session journal, argv construction,
  output parsing (fed captured repomix text), and the CLI via
  `click.testing.CliRunner`.
- `test_full_e2e.py` — drives the installed entry point through `subprocess`
  against the **real repomix**, and skips cleanly when the binary is absent.

## Command inventory

| Group | Commands | Backend needed |
|---|---|---|
| root | `--version`, `--json`, REPL fallback | no |
| `backend` | probe | no (reports unavailable) |
| `profile` | `new`, `info`, `save` | no |
| `target` | `show`, `set` | no |
| `filter` | `list`, `add`, `remove` | no |
| `option` | `list`, `set` | no |
| `pack` | `argv`, `run`, `run --dry-run` | yes (except `argv` / `--dry-run`) |
| `analyze` | `tokens`, `metrics` | yes |
| `security` | `check` | yes |
| `skill` | `generate`, `generate --dry-run` | yes (except `--dry-run`) |
| `config` | `init`, `show` | `init` yes, `show` no |
| `session` | `status`, `undo`, `redo` | no |
| `preview` | `recipes`, `capture`, `latest` | no (needs a prior real pack) |

## Unit cases — `test_core.py`

**Profile model**
1. `new_profile` defaults: targets `["."]`, style `xml`, output `repomix-output.xml`.
2. `save_profile` → `load_profile` round-trips every field.
3. `load_profile` on a missing path → `ProfileError`.
4. `load_profile` on non-JSON → `ProfileError`.
5. `load_profile` on a wrong/absent `format` key → `ProfileError`.
6. `validate` rejects an unknown style and a non-positive token budget.

**Mutations**
7. `filter.add` appends; adding the same pattern twice → `ProfileError`.
8. `filter.remove` on an absent pattern → `ProfileError`.
9. `option.set` on a boolean key stores a bool; on `style` validates the value.
10. `option.set token_budget "abc"` → `ProfileError`; `0` → `ProfileError`.
11. `option.set` on an unknown key → `ProfileError`.
12. `target.set` with neither targets nor remote → `ProfileError`.
13. `invert_action` round-trips each op: apply → invert → apply restores state.

**Session journal**
14. `record_action` pushes onto undo and clears redo.
15. `pop_undo` moves the entry to redo; `pop_redo` moves it back.
16. `pop_undo` on an empty journal returns `None`.
17. A corrupt (non-JSON) session file is replaced with a default, not raised.
18. `update_session` is re-entrant across sequential calls and leaves valid
    JSON on disk (lock acquired and released each time).
19. `session_path_for` puts the session **beside** the profile, never global.

**argv construction (no subprocess)**
20. Default profile → `[".", "--style", "xml", "-o", "repomix-output.xml", ...]`.
21. Include/ignore patterns are comma-joined into `--include` / `-i`.
22. Every enabled boolean option appears as its documented flag; disabled ones
    do not appear.
23. A remote profile emits `--remote <url> --remote-branch <ref>` and no
    directory arguments.
24. `token_budget` emits `--token-budget N`; absent budget emits nothing.

**Output parsing (captured repomix text, no subprocess)**
25. `parse_summary` extracts files/tokens/chars/output from a real Pack Summary
    block, stripping thousands separators and ANSI escapes.
26. `parse_token_tree` returns ordered rows with names, token counts, depth.
27. `parse_security` returns `clean=True` for "No suspicious files detected".
28. `parse_security` returns the file list when findings are present.
29. `read_config` parses JSONC (line comments + trailing commas) — repomix's
    own shipped config uses both.
30. `read_config` on a missing file → `BackendError` naming the path.

**CLI (CliRunner, backend stubbed or unused)**
31. `profile new` writes the file and initializes the session.
32. `profile new` refuses to overwrite an existing file (non-zero exit).
33. `--json profile info` emits parseable JSON with the expected keys.
34. `filter add` then `session undo` restores the original pattern list.
35. `option set` on an unknown key exits non-zero and lists known options.
36. `pack run --dry-run` prints the argv and does **not** invoke the backend.
37. `pack argv` output matches `backend.full_command`.
38. `session undo` with an empty journal exits non-zero with "nothing to undo".
39. `security check` reports non-zero exit (2) when findings are returned
    (backend monkeypatched — no real scan).
40. `preview capture` without a prior pack exits non-zero.
41. `backend` command succeeds and reports `available: false` when
    `REPOMIX_BIN` points at nothing and PATH/npx lookup is stubbed out.

## e2e cases — `test_full_e2e.py`

Resolve `cli-it-repomix` from PATH, else `python -m cli_it.repomix`. Skip the
whole module when `repomix_backend.available()` is False, with the reason
naming repomix.

E1. `--version` exits 0.
E2. `backend` reports `available: true` and a version string.
E3. Build a small real fixture tree, create a profile, `pack run` → exit 0,
    the output file exists, `total_files` matches the fixture, tokens > 0.
E4. `--json pack run` output parses and carries `output_path`, `total_tokens`,
    `security.clean`.
E5. `analyze tokens` returns a non-empty tree whose total matches the pack.
E6. `analyze metrics` succeeds with `--no-files` and writes no fixture output.
E7. `security check` on a clean fixture exits 0 and reports `clean: true`.
E8. `option set token_budget 1` then `pack run` exits non-zero with a budget
    error (proves the guard is really enforced by repomix, not simulated).
E9. `skill generate` produces `SKILL.md` plus `references/summary.md`,
    `references/project-structure.md`, `references/files.md`.
E10. `config init` in a temp dir creates `repomix.config.json`; `config show`
     parses it.
E11. `pack run` then `preview capture` writes a bundle with `manifest.json`
     and `artifacts/report.json`.

## Edge cases

- Missing profile path → exit non-zero, message names the path.
- Malformed profile JSON → exit non-zero, no traceback.
- Unknown preview recipe → exit non-zero.
- `--target` and `--remote` together → exit non-zero (mutually exclusive).
- Backend missing → every backend-touching command exits non-zero with the
  `npm install -g repomix` hint, and never with a traceback.

## Expected exit codes

| Situation | Code |
|---|---|
| success | 0 |
| usage error (Click) | 2 |
| harness error (`ClickException`) | 1 |
| security findings present | 2 |
| repomix failure / missing binary / token budget exceeded | 1 |

---

## Results

Run on macOS 25.2.0 (darwin), Python 3.13.7, click 8.3.1, pytest 9.1.1,
repomix 1.17.0 (`/opt/homebrew/bin/repomix`), Node v24.7.0.

**With repomix installed** — `python -m pytest`:

```
59 passed in 6.90s
```

**With repomix unreachable** — `env -i PATH=<venv>:/usr/bin:/bin python -m pytest -rs`:

```
50 passed, 9 skipped in 0.07s
```

All 9 skips are the e2e module, reason: *"repomix binary not found (npm install
-g repomix, or set $REPOMIX_BIN)"*. The unit suite needs no repomix, as required.

### Failures found and resolved

The first full run was **3 failed, 53 passed**. Both failures were real
harness defects, not test bugs:

1. **`test_invert_action_round_trips[action2, action3]` — undo silently did
   nothing for overwriting ops.** `invert_action` derived the inverse from the
   *current* profile, so for `option.set` and `target.set` it produced an
   action that re-applied the value it was meant to revert. The replaced value
   was gone by then — saved over. Fixed by having `apply_action` record a
   `previous` snapshot on overwriting ops (`setdefault`, so redo re-applying an
   action does not clobber it) and having `invert_action` replay that snapshot.
   `test_cli_option_set_undo_restores_previous` was added as the regression
   test: set style → undo → back to `xml` → redo → `markdown` again.

2. **`test_config_init_and_show` — `config init` created nothing.** `repomix
   --init` is a multi-step interactive wizard (@clack/prompts). With a non-TTY
   stdin it prints the first prompt, exits **0**, and writes no file; `-f` does
   not bypass it (that flag covers skill-overwrite and remote-config-trust
   prompts only). An agent could never drive it. Verified by hand:

   ```
   $ repomix --init < /dev/null ; echo $?
   ◆  Do you want to create a repomix.config.json file?
   0
   $ ls repomix.config.json → No such file
   ```

   Fixed by removing the unusable command. `config export -p <profile>` now
   writes the config file directly from profile state, in the schema from
   `src/config/configSchema.ts`. The e2e test was rewritten to prove the file
   is one repomix genuinely accepts: it runs the real binary with
   `-c <exported config> --stdout` and asserts the pack succeeds — not merely
   that the JSON round-trips.

### Coverage notes

- Cases 1–41 from the unit plan are implemented; case 13 became the
  parametrized `test_invert_action_round_trips` over four ops.
- Case E10 (`config init`) was replaced by
  `test_exported_config_is_accepted_by_real_repomix`, per the defect above.
- Concurrent (multi-process) lock contention is **not** covered — the tests
  exercise sequential locked writes and corrupt-file recovery only. Real
  contention needs a multi-process harness; the lock itself follows
  `guides/session-locking.md` verbatim.
