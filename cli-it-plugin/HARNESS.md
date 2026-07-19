# HARNESS.md — The CLI-It Harness Generation Methodology

**This document is the source of truth.** Agents building a CLI-It harness
must read it fully before writing any code, then follow the phases in order.
The output of the pipeline is a stateful, agent-native CLI wrapped around a
piece of *real* software, packaged as `cli_it.<software>` and installable as
`cli-it-<software>`.

## Non-negotiable principles

1. **Real software only.** The harness builds intermediate native formats
   in-process, but final rendering/export always invokes the real application
   (its binary, Python API, or MCP server). Never reimplement the engine as a
   toy.
2. **Agent-first UX.** Dual output: human text by default, machine JSON with a
   root `--json` flag. REPL when invoked without a subcommand. A discoverable
   `SKILL.md` documents everything an agent needs.
3. **PEP 420 namespace.** Packages live under `cli_it.<software>` and there is
   **never** an `__init__.py` directly inside `cli_it/`.
4. **Plan tests before writing them.** `TEST.md` precedes `test_*.py`.

## Mandatory directory structure

```text
<software>/agent-harness/
  <SOFTWARE>.md                 # analysis + architecture record (phase 1–2)
  setup.py                      # find_namespace_packages(include=["cli_it.*"])
  cli_it/                       # NO __init__.py here (PEP 420)
    <software>/
      __init__.py
      __main__.py               # python -m cli_it.<software>
      README.md
      <software>_cli.py         # Click surface
      core/                     # data model, project + session state
      utils/<software>_backend.py   # ALL real-software invocation lives here
      utils/repl_skin.py        # copied verbatim from cli-it-plugin/repl_skin.py
      skills/SKILL.md           # packaged compatibility copy
      tests/TEST.md
      tests/test_core.py        # unit — must pass without the real software
      tests/test_full_e2e.py    # e2e — may skip when backend missing
```

---

## Phase 0 — Source acquisition *(command layer)*

Input is a **local path** or a **GitHub URL** — never a bare software name.

- Local path: verify it exists and looks like the software's source/install.
- GitHub URL: `git clone --depth 1` into a working directory.
- Record the resolved source location; everything later cites files from it.

## Phase 1 — Codebase analysis

Produce the analysis section of `<SOFTWARE>.md` answering:

- **Backend engine**: how does the software actually do work? (CLI binary,
  Python API like `bpy`, scripting console, headless flag, HTTP/MCP API?)
- **GUI → API map**: for each major GUI action an agent would want, what is
  the programmatic equivalent?
- **Data model**: native project/file formats, what is safely writable
  out-of-process vs. only via the app.
- **Existing CLIs**: does the app ship command-line entry points already?
  Wrap, don't duplicate.
- **Undo system**: how the app models history; how the harness will expose
  undo/redo (own journal vs. app-native).

## Phase 2 — CLI architecture design

Design before code, in `<SOFTWARE>.md`:

- **Command groups** (e.g. `project`, `scene`, `export`, `session`,
  `preview`) and every subcommand with args.
- **State model**: what lives in the project file vs. the session file; where
  files go; how concurrent access is prevented (see
  `guides/session-locking.md`).
- **Dual output**: root-level `--json` flag design; stable JSON shapes.
- **REPL**: `invoke_without_command=True` drops into a ReplSkin-powered REPL.
- **Preview**: which recipes produce preview bundles
  (`guides/preview-methodology.md`).

## Phase 3 — Implementation

Order of work:

1. **Data layer** (`core/`): project model, load/save, validation.
2. **Probe commands**: read-only commands (`info`, `status`, `list`) first —
   they prove the data layer without risk.
3. **Mutations**: create/modify commands, each recorded in the session
   journal for undo/redo.
4. **Backend module** (`utils/<software>_backend.py`): the *only* place that
   locates and invokes the real software. Detect the binary/API, fail with an
   install hint when missing.
5. **Export/render commands**: call the backend; verify the output file exists
   before reporting success.
6. **Session + file locking**: exclusive lock around every session write
   (`guides/session-locking.md`).
7. **ReplSkin + default REPL**: copy `cli-it-plugin/repl_skin.py` into
   `utils/repl_skin.py`; wire banner, prompt loop, and help.

## Phase 4 — Test planning

Write `tests/TEST.md` **before any test code**: enumerate every command, the
unit cases (no backend), the e2e cases (real software), edge cases (missing
files, locked sessions, malformed JSON), and expected exit codes.

## Phase 5 — Test implementation

- `test_core.py`: pure unit tests — data layer, session journal, CLI via
  `click.testing.CliRunner`. Must pass on a machine without the software.
- `test_full_e2e.py`: drives the installed entry point via `subprocess`
  (resolve `cli-it-<software>` from PATH or fall back to
  `python -m cli_it.<software>`), exercises a real render/export. Skip
  cleanly (`pytest.importorskip` / `pytest.mark.skipif`) when the backend is
  absent.

## Phase 6 — Test documentation

Run `pytest` and append the actual results (counts, skips, failures and their
resolution) to `TEST.md`. Honest numbers only.

## Phase 6.5 — SKILL.md generation

Run the generator — do not hand-write skills:

```bash
python cli-it-plugin/skill_generator.py <software>/agent-harness
```

This dual-writes the canonical `skills/cli-it-<software>/SKILL.md` at the repo
root and the packaged `cli_it/<software>/skills/SKILL.md` copy.

## Phase 7 — Packaging

`setup.py` must use the namespace pattern:

```python
from setuptools import find_namespace_packages, setup

setup(
    name="cli-it-<software>",
    version="0.1.0",
    packages=find_namespace_packages(include=["cli_it.*"]),
    include_package_data=True,
    package_data={"cli_it.<software>": ["skills/SKILL.md", "tests/TEST.md"]},
    python_requires=">=3.10",
    install_requires=["click>=8.0"],
    entry_points={
        "console_scripts": [
            "cli-it-<software>=cli_it.<software>.<software>_cli:cli",
        ]
    },
)
```

Verify: `pip install -e <software>/agent-harness && cli-it-<software> --help`,
then add the registry entry (see CONTRIBUTING.md field table).

---

## Cross-cutting rules

- **Session locking**: open state files `r+`, take an exclusive lock,
  truncate, write JSON, release (`guides/session-locking.md`).
- **Preview split**: harnesses *produce* bundles with
  `cli-it-plugin/preview_bundle.py` conventions; only `cli-it previews`
  consumes/views them (`docs/PREVIEW_PROTOCOL.md`).
- **ReplSkin**: copy, don't diverge. All harness REPLs must look the same.
- **Errors**: readable messages; when a binary is missing, print the install
  hint. Exit non-zero on failure; agents check return codes.
- **Absolute paths** in examples and skills; agents must not rely on cwd.
- **MCP backends**: when the software exposes MCP instead of a CLI/API, see
  `guides/mcp-backend.md`.

## Completion checklist (used by /cli-it:validate)

- [ ] Directory structure matches exactly; no `cli_it/__init__.py`
- [ ] REPL starts when no subcommand; `--json` works on root
- [ ] Backend isolation: real-software calls only in `utils/<software>_backend.py`
- [ ] Session writes are lock-protected
- [ ] `TEST.md` written before tests; results appended after
- [ ] Unit tests pass without the software; e2e skips cleanly without it
- [ ] SKILL.md generated (both copies, in sync)
- [ ] `pip install -e` + entry point verified
- [ ] Registry entry added and valid per CONTRIBUTING.md
