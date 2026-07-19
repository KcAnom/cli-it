# DEMOAPP.md — analysis & architecture record

The Phase 1–2 record required by HARNESS.md. DemoApp is the monorepo's
exemplar: its engine is intentionally tiny, but every harness convention is
exercised for real.

## Phase 1 — Codebase analysis

- **Backend engine**: an external renderer process. The engine is invoked as
  `python -c <engine> <project.json> <output> <format>` — a separate OS
  process, discovered and health-checked like any binary backend. All
  invocation lives in `utils/demoapp_backend.py`.
- **GUI → API map**: DemoApp has no GUI; its "actions" map directly:
  create project → project file write; add/remove item → journaled JSON
  mutation; render/export → engine process.
- **Data model**: native format `demoapp/v1` — JSON with `name`,
  `created_at`, `items[]` (`{id, name, kind}`), `metadata{}`. Safely
  writable out-of-process; rendering is engine-only.
- **Existing CLIs**: none; the harness *is* the CLI.
- **Undo system**: the app has none, so the harness owns a journal:
  `<project>.session.json` with `undo[]`/`redo[]` stacks of self-inverting
  actions (`item.add` / `item.remove` carrying the full item).

## Phase 2 — CLI architecture

- **Command groups**
  - `project` — `new`, `open`, `save`, `info`
  - `item` — `add`, `list`, `remove` (journaled mutations, auto-save)
  - `session` — `status`, `undo`, `redo`
  - `export` — `run` (engine render; text/json)
  - `preview` — `recipes`, `capture`, `latest` (preview-bundle/v1 producer)
  - root: `backend` probe, `--json`, `--version`
- **State model**: project file = document; session file = journal, written
  only under an exclusive lock (`core/session.py`, per
  `guides/session-locking.md`). One session per project, sibling file.
- **Dual output**: root `--json` flag; every command emits a stable dict via
  `_emit`.
- **REPL**: `invoke_without_command=True` → ReplSkin banner (shows skill
  path), line loop dispatching back into the Click group.
- **Exit codes**: 0 ok; Click errors 1; usage errors 2.

## Phase 7 — Packaging

Namespace package `cli_it.demoapp` (no `cli_it/__init__.py`), entry point
`cli-it-demoapp`, packaged SKILL.md + TEST.md via `package_data`.
