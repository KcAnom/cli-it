# REPOMIX — CLI-It harness analysis & architecture

Source analyzed: `/Users/kcdacre8tor/repomix` (git clone of `yamadashy/repomix`,
version **1.17.0**), plus the installed binary at `/opt/homebrew/bin/repomix`
and the registered MCP server (`repomix --mcp`, stdio) in `~/.claude.json`.

---

## Phase 1 — Codebase analysis

### Backend engine

Repomix is a **Node CLI binary**, not a library-with-GUI. Work is done by
invoking the `repomix` executable; there is no daemon and no persistent app
state. Three surfaces exist, all fronted by the same core:

| Surface | Entry | Notes |
|---|---|---|
| CLI binary | `bin/repomix.cjs` → `src/cli/cliRun.ts` | primary; what this harness drives |
| MCP server | `repomix --mcp` → `src/cli/actions/mcpAction.ts`, `src/mcp/` | tools: `pack_codebase`, `pack_remote_repository`, `generate_skill`, `read_repomix_output`, `grep_repomix_output`, `attach_packed_output`, `file_system_read_file`, `file_system_read_directory` |
| Node API | `src/index.ts` | not used — would require bundling Node into the harness |

Decision: drive the **CLI binary** via `subprocess`. It exposes every MCP
capability (including skill generation) and needs no MCP client dependency.
Per `guides/mcp-backend.md`, an MCP path would have to live in the same backend
module anyway; the binary is simpler and has no session/hang risk.

Actions dispatch from `src/cli/actions/`: `defaultAction.ts` (pack local),
`remoteAction.ts` (`--remote`, clones then packs), `initAction.ts` (`--init`),
`mcpAction.ts` (`--mcp`), `watchAction.ts` (`-w`), `migrationAction.ts`,
`versionAction.ts`.

### GUI → API map

Repomix has no GUI. The equivalent mapping is *intent → flag*:

| Intent | repomix invocation |
|---|---|
| Pack a directory | `repomix [dirs...] -o <file> --style <xml\|markdown\|json\|plain>` |
| Pack to stdout | `repomix --stdout .` (suppresses all logging — the machine path) |
| Pack a GitHub repo | `repomix --remote <url> [--remote-branch <ref>]` |
| Shrink output | `--compress` (Tree-sitter signatures), `--remove-comments`, `--remove-empty-lines`, `--truncate-base64` |
| Select files | `--include <globs>`, `-i/--ignore <globs>`, `--no-gitignore`, `--no-default-patterns` |
| Add git context | `--include-diffs`, `--include-logs`, `--include-logs-count N` |
| Measure cost | `--token-count-tree [threshold]`, `--token-count-encoding <enc>` |
| Guard cost | `--token-budget N` (non-zero exit when exceeded) |
| Metadata only | `--no-files` (structure + metrics, no contents) |
| Secret scan | on by default (secretlint); `--no-security-check` disables |
| Split large output | `--split-output <size>` → `repomix-output.1.xml`, … |
| Generate a Claude skill | `--skill-generate [name] --skill-output <dir> [-f]` |
| Create config | `--init` — **interactive wizard, unusable headlessly** (see below) |

### Data model

- **Config**: `repomix.config.json` (JSONC — the repo's own config contains
  `//` comments, so the harness must parse tolerantly). Schema in
  `src/config/configSchema.ts`; loader `src/config/configLoad.ts`. Sections:
  `input`, `output`, `include`, `ignore`, `security`, `tokenCount`.
- **Ignore files**: `.repomixignore`, `.gitignore`, `.ignore`, plus built-in
  default patterns (`src/config/defaultIgnore.ts`).
- **Output**: a single generated artifact (`repomix-output.xml` by default).
  Styles in `src/core/output/outputStyles/`. JSON style shape, verified by
  probe: `{ fileSummary: {...}, directoryStructure: "<tree string>", files: { "<path>": "<content>" } }`.
- **Skill output**: `SKILL.md` + `references/{summary,project-structure,files}.md`
  and `references/tech-stacks.md` when a stack is detected
  (`src/core/skill/`). Verified by probe.
- Everything repomix writes is a plain file, safely writable and readable
  out-of-process. There is no lock-bearing app state to respect.

### Existing CLIs — wrap, don't duplicate

Repomix *is* a CLI, so the harness adds no packing logic of its own. What it
adds is what repomix deliberately lacks:

- **Persistent, reusable pack profiles.** Repomix state lives in one
  `repomix.config.json` per directory; an agent juggling several pack recipes
  over the same tree has nowhere to put them.
- **An undo journal** over profile edits.
- **Stable JSON on every command**, including ones repomix only prints as
  decorated human text (token tree, metrics, security findings).
- **Verified execution**: confirm the output file exists and report its real
  size/token count rather than trusting exit status.

### Undo system

Repomix has none — every run is a fresh, stateless pack. The harness therefore
owns its own journal (`core/session.py`, the standard CLI-It pattern): each
profile mutation is recorded with enough detail to invert. Pack runs are *not*
journaled as undoable (they write a derived artifact, not state) but the last
run's result is stored on the profile as `last_pack`.

---

## Phase 2 — CLI architecture design

Package `cli_it.repomix`, entry point `cli-it-repomix`, REPL when invoked with
no subcommand, root `--json` for machine output.

### Command groups

```text
backend                                  probe repomix binary, version, node
profile new|info|save                    pack-profile JSON files
target set|show                          local dirs or --remote repo (journaled)
filter add|remove|list                   include/ignore glob patterns (journaled)
option set|list                          style, compress, budget, git flags (journaled)
pack run [--dry-run] [--no-save]         REAL repomix invocation → verified output
pack argv                                print the exact command line that would run
analyze tokens|metrics|files             token tree / metrics / JSON file inventory
security check                           secretlint scan via a --no-files pack
skill generate                           repomix --skill-generate (real skill output)
config export|show                       write/read repomix.config.json
session status|undo|redo                 journal control
preview recipes|capture|latest           preview bundles for `cli-it previews`
```

### State model

- **Profile file** (`<name>.repomix-profile.json`, path given by `--profile`):
  targets, remote, style, output path, include/ignore patterns, boolean
  options, token budget/encoding, and `last_pack` (result of the most recent
  real run).
- **Session file**: `<profile>.session.json` beside the profile, holding
  `undo`/`redo` stacks. Never global.
- **Locking**: every session write goes through `update_session()` — open
  `r+`, exclusive lock on the handle, read, mutate, truncate, write, fsync,
  unlock (`guides/session-locking.md`). Portable via `fcntl`/`msvcrt`. The
  backend is never invoked while the lock is held.
- **Auto-save**: mutations persist immediately; `--no-save` available on
  `pack run` for the artifact-free case.

### Dual output

Root `--json` sets `ctx.obj["json"]`; every command emits through `_emit()`.
Stable shapes: `{"action": {...}}` for mutations, `{"profile": ..., ...}` for
info, `{"argv": [...], "dry_run": true}` for planned runs,
`{"output": {...}, "metrics": {...}}` for completed packs.

### Dry-run

`pack run --dry-run` builds the argv through the *same* function the real run
uses (`backend.build_argv`), prints it, and exits 0 without invoking repomix.

### Preview

One recipe, `pack-report`: writes `report.txt` + `report.json` from the last
real pack (files, tokens, chars, output path, security findings) into a bundle
via `preview_bundle.prepare_bundle` / `finalize_bundle`. Fails with an install
hint if no real pack has happened — never fabricated.

### Backend isolation

`utils/repomix_backend.py` is the only module that touches repomix. It
resolves the binary (`REPOMIX_BIN` env → `shutil.which("repomix")` → `npx -y
repomix` fallback), applies a timeout to every call, parses repomix's decorated
stdout into structured metrics, and raises `BackendError` with an install hint
(`npm install -g repomix`) when nothing is found.


---

## Addendum — findings from implementation

**`repomix --init` cannot be scripted.** It is a multi-step @clack/prompts
wizard. With non-TTY stdin it prints the first prompt, exits 0, and writes
nothing; `-f` does not bypass it. The planned `config init` command was
therefore replaced by `config export`, which writes `repomix.config.json`
directly from profile state using the schema in `src/config/configSchema.ts`.
That is config data the harness already owns, not engine work — and the e2e
test proves the result by feeding it back to the real binary with `-c`.

**Undo needs a `previous` snapshot.** Overwriting ops (`option.set`,
`target.set`) cannot be inverted from the post-change profile, because the old
value is saved over. `apply_action` now records `previous` on those ops and
`invert_action` replays it. See TEST.md for the regression case.

**Console output is not an API (0.2.0).** The summary, token-tree, and security
parsers scrape repomix's decorated stdout. That is unavoidable — repomix emits
those numbers nowhere else — but it means an upstream formatting change can
break them. The harness therefore:

- never returns a plausible-looking empty result from a scrape: `run_pack`,
  `run_metrics`, and `run_token_tree` raise a drift error naming the tested
  version range and echoing what repomix actually printed;
- treats an unrecognized security block as `status: unknown`, never `clean`.
  `security check` exits non-zero instead of issuing a verdict it cannot
  support. Under 0.1.0 the same situation produced a confident false clean;
- reports `version_tested` from `backend`, warning when the installed repomix
  is outside `TESTED_VERSIONS`;
- offers `analyze files`, which derives its inventory from
  `--style json --stdout` — repomix's documented JSON shape, immune to console
  reformatting. Prefer it over `analyze metrics` where the per-file data suffices.

## Self-healing (0.3.0)

Failing loudly is the floor. Where a claim can be **checked against independent
ground truth**, the harness re-learns the format instead of just erroring.

`doctor` packs a fixture whose true contents it knows. `--style json --stdout`
yields the real file and character counts; the console summary is then compared
against them. With `--heal`, a renamed label is accepted only when its number
*equals* the count already known from the JSON — verification, not guesswork.
Learned labels are written to `~/.cli-it/repomix/learned-formats.json`, keyed by
repomix version, each carrying its provenance and the evidence behind it, and
every scraper consults them on subsequent runs. Built-in labels always take
precedence, so a learned entry can never mask one that still works.

Two honest limits, both surfaced rather than hidden:

- **Token counts have no independent source** — the number comes from repomix's
  own tokenizer. A token label is matched by wording alone and recorded as
  `label-wording-heuristic`, distinct from `verified-against-json-output`.
- **The security verdict is never healed.** There is no second source for "does
  this repository leak credentials", so a learned "clean" phrase would be a
  guess about secrets. `doctor` reports the security parser as `healable: false`
  and the command keeps failing closed. This is the one place where erroring
  forever is the correct behavior.
