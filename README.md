# CLI-It

**Make real software agent-native.**

CLI-It turns GUI/desktop/SaaS software into stateful, discoverable command-line
harnesses that AI coding agents (Claude Code, Pi, Codex, Hermes, Reasonix,
OpenCode, Cursor, …) can drive directly — while the *real* application still does
the rendering, exporting, and heavy lifting.

> Architecture inspired by [HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything),
> rebuilt from scratch under the CLI-It name. CLI-It is not affiliated with, and
> does not reuse branding or registry contents from, the upstream project.

## What's in the box

1. **Generation methodology + agent plugin** ([`cli-it-plugin/`](cli-it-plugin/)) —
   a 7-phase SOP ([`HARNESS.md`](cli-it-plugin/HARNESS.md)) that coding agents
   follow to produce a new CLI harness under `<software>/agent-harness/`, plus
   the `skill_generator.py`, `preview_bundle.py`, and `repl_skin.py` helpers.
2. **CLI-It Hub package manager** ([`cli-it-hub/`](cli-it-hub/), PyPI name
   `cli-it-hub`, console command `cli-it`) — browse/search/install/update/
   uninstall harness CLIs and public CLIs, capability-based **matrices**, and a
   generic **preview viewer** for preview bundles and live sessions.
3. **Registries + static hub site** — [`registry.json`](registry.json),
   [`public_registry.json`](public_registry.json),
   [`matrix_registry.json`](matrix_registry.json) published via GitHub Pages
   from [`docs/hub/`](docs/hub/) with OpenAPI, `llms.txt`, and matrix skill
   content.

## Quick start

### 1. Install the hub

```bash
pip install cli-it-hub          # published
# or from a checkout:
pip install -e ./cli-it-hub

export CLI_HUB_NO_ANALYTICS=1   # recommended for dev
cli-it list
cli-it search demo
cli-it install demoapp
cli-it-demoapp                  # stateful REPL
```

### 2. Install the agent plugin

**Claude Code** (marketplace at repo root):

```text
/plugin marketplace add KcAnom/cli-it
/plugin install cli-it
```

**Pi:**

```bash
bash .pi-extension/cli-it/install.sh
```

Codex / Hermes / Reasonix / OpenCode adapters live in
[`codex-skill/`](codex-skill/), [`hermes-skill/`](hermes-skill/),
[`reasonix-skill/`](reasonix-skill/), and
[`opencode-commands/`](opencode-commands/).

### 3. Build a harness for your software

Inside your agent, run:

```text
/cli-it /path/to/local/software      # or a GitHub URL
```

The agent reads `HARNESS.md` and walks the 7-phase pipeline: analysis → CLI
design → implementation → test plan → tests → test docs → SKILL.md → packaging.

## Plugin commands

| Command | Purpose |
|---------|---------|
| `/cli-it <path-or-url>` | Build a full CLI harness for the given software |
| `/cli-it:refine [focus]` | Gap analysis + coverage improvements on an existing harness |
| `/cli-it:test` | Run the harness test suite and update `TEST.md` |
| `/cli-it:validate` | Check a harness against the HARNESS.md checklist |
| `/cli-it:list` | Scan for harnesses and installed CLI-It tools |

## Hub CLI surface

```text
cli-it [--version]
cli-it install|uninstall|update <name>
cli-it list [-c category] [-s harness|public|npm|all] [--json]
cli-it search <query> [--json]
cli-it info <name>
cli-it launch <name> [args...]
cli-it can <query> [--json]
cli-it previews inspect|html|watch|open <ref>
cli-it matrix list|search|info|preflight|install|doctor|recipes ...
```

Matrix commands use exit code `3` for "capability gaps" (partial tooling) — a
soft failure agents can work around.

## Project structure

```text
cli-it-hub/         # `cli-it` package manager (PyPI: cli-it-hub)
cli-it-plugin/      # HARNESS.md methodology + agent commands + helper scripts
cli-it-matrix/      # capability matrix skill packs (SKILL.md per matrix)
cli-it-meta-skill/  # catalog meta-skill for agents
skills/             # canonical root SKILL.md copies (npx skills compatible)
demoapp/            # exemplar harness proving the monorepo conventions
docs/               # preview protocol + static hub site (GitHub Pages)
.claude-plugin/     # Claude Code marketplace manifest
.pi-extension/      # Pi extension adapter
*-skill/, opencode-commands/   # thin agent adapters
registry.json / public_registry.json / matrix_registry.json
```

## Product principles

- **Real software only** — harnesses generate intermediate native formats and
  invoke the real app for render/export; never a toy reimplementation.
- **Agent-first UX** — dual human/JSON output (`--json`), REPL by default when
  no subcommand, discoverable `SKILL.md`.
- **PEP 420 namespace** — all harness packages live under `cli_it.<software>`
  with **no** `__init__.py` in `cli_it/`.
- **Registry is the hub API** — merging registry JSON is enough for the hub to
  list and install CLIs.

## Docs

- Methodology: [`cli-it-plugin/HARNESS.md`](cli-it-plugin/HARNESS.md)
- Preview protocol: [`docs/PREVIEW_PROTOCOL.md`](docs/PREVIEW_PROTOCOL.md)
- Hub site source: [`docs/hub/`](docs/hub/) (agents: see `llms.txt`)
- Contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md)

## License

[Apache-2.0](LICENSE)
