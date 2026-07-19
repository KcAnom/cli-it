# Recreation Prompt: CLI-It (Core Framework)

> **Project name:** CLI-It (rebrand of the scanned CLI-Anything core architecture).  
> **Implement this project at:** `/Users/kc/cli-it`  
> **Inspired by upstream architecture:** HKUDS/CLI-Anything (do not copy branding, assets, or registry contents verbatim; rebuild the core system under the CLI-It name).


> Build a faithful recreation of the **core architecture** inspired by [HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything), rebranded as **CLI-It**: the agent harness methodology plugin, the `cli-it` package manager, registries, preview protocol, matrix skill packs, agent adapters (Claude/Pi/Codex/…), docs hub shell, and CI.  
> **Do not** recreate all ~69 per-app `*/agent-harness/` packages. Instead, implement **one exemplar harness skeleton** (e.g. `demoapp`) so the pattern is real and testable, plus registry entries that can point at it.

---

## (a) Project Overview

### What to build
A monorepo ecosystem that makes GUI/desktop/SaaS software **agent-native** by:

1. **Generation methodology + agent plugin** (`cli-it-plugin/`, `.pi-extension/`, thin adapter skills) — a 7-phase SOP (`HARNESS.md`) that coding agents follow to produce a new CLI harness under `<software>/agent-harness/`.
2. **CLI-It Hub package manager** (PyPI name `cli-it-hub`, console entry `cli-it`) — browse/search/install/update/uninstall harness CLIs and public CLIs; capability-based **matrices**; generic **preview viewer** for preview bundles/live sessions.
3. **Registries + static hub site** — `registry.json`, `public_registry.json`, `matrix_registry.json` published via GitHub Pages (or local static server) with OpenAPI, `llms.txt`, and matrix skill content.

### Primary users
- AI coding agents (Claude Code, Pi, Codex, Hermes, Reasonix, OpenCode, Cursor, etc.)
- Humans who want agents to drive real tools (Blender, FreeCAD, GIMP, n8n, …) via stateful CLIs

### Product principles (non-negotiable)
- **Real software only** — harnesses generate intermediate native formats and invoke the real app for render/export; never reimplement the engine as a toy.
- **Agent-first UX** — dual human/JSON output (`--json`), REPL default when no subcommand, discoverable `SKILL.md`.
- **PEP 420 namespace** — all harness packages live under `cli_it.<software>` with **no** `__init__.py` in `cli_it/`.
- **Registry is the hub API** — merging registry JSON is enough for the hub to list/install CLIs.

### Non-goals for this recreation
- Porting every community harness (blender, freecad, gimp, …).
- Full marketing hub HTML/JS demos and large GIF assets.
- Live production PostHog/Umami/DO Spaces accounts (stub/opt-out analytics; optional secrets).
- Recreating arXiv paper content or multi-language README translations (optional later).

---

## (b) Tech Stack & Versions

| Layer | Choice | Notes |
|-------|--------|-------|
| Language (hub + harnesses) | **Python ≥ 3.10** | Primary runtime |
| CLI framework | **Click ≥ 8.0** | All CLIs |
| HTTP client | **requests ≥ 2.28** | Registry fetch |
| Packaging | **setuptools** | Nested `cli-it-hub/setup.py`; harness `setup.py` with `find_namespace_packages` |
| Hub package name | `cli-it-hub` version **0.4.1** (or start `0.1.0` and keep APIs) | Entry: `cli-it=cli_it_hub.cli:main` |
| Tests | **pytest** | Unit without backends; e2e optional |
| Pi extension | **TypeScript** | `@mariozechner/pi-coding-agent` ExtensionAPI |
| Claude plugin | Markdown command specs + `plugin.json` / marketplace JSON | No heavy runtime |
| Hub site | Static files + optional **Jekyll** under `docs/hub` | GitHub Pages deploy |
| Preview protocol | `preview-bundle/v1`, `preview-trajectory/v1` | Shared producer/consumer contract |
| License | Prefer **Apache-2.0** at repo root; hub setup may say MIT — pick one and be consistent (recommend Apache-2.0) |

**No** monorepo-root `package.json` / `pyproject.toml` required. Hub is a nested package; each harness has its own `setup.py`.

Optional tools the installer should detect: `pip`, `uv`, `npm`.

---

## (c) Complete Directory Tree

Create this tree (core recreation). Omit `node_modules`, venvs, lockfile bodies, binaries.

```text
cli-it/                          # /Users/kc/cli-it
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── SECURITY.md
├── CITATION.cff
├── .gitignore
├── registry.json
├── public_registry.json
├── matrix_registry.json
│
├── .claude-plugin/
│   └── marketplace.json
│
├── .pi-extension/
│   └── cli-it/
│       ├── README.md
│       ├── index.ts
│       ├── install.sh
│       └── tests/                    # optional TS tests
│
├── .github/
│   ├── CODEOWNERS                    # optional
│   ├── PULL_REQUEST_TEMPLATE.md      # optional
│   ├── ISSUE_TEMPLATE/               # optional yml templates
│   ├── labeler.yml                   # optional
│   ├── scripts/
│   │   ├── generate_meta_skill.py
│   │   ├── sync_root_skills.py
│   │   ├── validate_root_skills.py
│   │   ├── update_registry_dates.py
│   │   └── tests/                    # optional
│   └── workflows/
│       ├── publish-cli-it.yml
│       ├── deploy-pages.yml
│       ├── check-root-skills.yml
│       └── check-codex-skill.yml     # optional
│
├── cli-it-plugin/
│   ├── README.md
│   ├── QUICKSTART.md
│   ├── PUBLISHING.md
│   ├── HARNESS.md                    # SOURCE OF TRUTH methodology
│   ├── LICENSE                       # optional copy
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── commands/
│   │   ├── cli-it.md
│   │   ├── refine.md
│   │   ├── test.md
│   │   ├── validate.md
│   │   └── list.md
│   ├── guides/
│   │   ├── session-locking.md
│   │   ├── preview-methodology.md
│   │   ├── skill-generation.md
│   │   ├── pypi-publishing.md
│   │   ├── mcp-backend.md
│   │   ├── filter-translation.md
│   │   ├── timecode-precision.md
│   │   └── auto-save-dry-run.md
│   ├── templates/
│   │   └── SKILL.md.template
│   ├── scripts/
│   │   └── setup-cli-it.sh
│   ├── skill_generator.py
│   ├── preview_bundle.py
│   ├── repl_skin.py
│   └── tests/
│       └── test_skill_generator.py   # recommended
│
├── cli-it-hub/
│   ├── README.md
│   ├── setup.py
│   ├── MANIFEST.in
│   ├── cli_it_hub/
│   │   ├── __init__.py               # __version__ = "0.4.1"
│   │   ├── cli.py
│   │   ├── registry.py
│   │   ├── installer.py
│   │   ├── matrix.py
│   │   ├── matrix_skill.py
│   │   ├── preview.py
│   │   └── analytics.py
│   └── tests/
│       ├── __init__.py
│       ├── test_cli_it_hub.py           # can start smaller than upstream
│       └── test_matrix_skill_dist.py
│
├── cli-it-matrix/
│   ├── 3d-cad/SKILL.md
│   ├── game-development/SKILL.md
│   ├── image-design/SKILL.md
│   ├── knowledge-research/SKILL.md
│   └── video-creation/
│       ├── SKILL.md
│       ├── references/               # optional deep refs (can be stubs)
│       │   ├── art-direction-review.md
│       │   ├── captions.md
│       │   ├── nle-shotcut-kdenlive.md
│       │   ├── render-doctor.md
│       │   ├── sound-design.md
│       │   ├── source-triage.md
│       │   └── story-structure-audio.md
│       └── scripts/
│           └── video_doctor.py       # optional helper
│
├── cli-it-meta-skill/
│   └── SKILL.md
│
├── skills/
│   ├── README.md
│   ├── cli-it-meta-skill/SKILL.md   # may mirror root meta skill
│   └── cli-it-demoapp/SKILL.md # for exemplar harness
│
├── skill_generation/
│   └── tests/
│       └── test_skill_path.py        # optional path-resolution tests
│
├── docs/
│   ├── PREVIEW_PROTOCOL.md
│   ├── PREVIEW_MECHANISM_PROGRESS.md # optional
│   ├── PREVIEW_PROGRESS.md           # optional
│   ├── FREECAD_VIDEO_REFERENCE.md    # optional / omit
│   └── hub/
│       ├── _config.yml
│       ├── index.md
│       ├── llms.txt
│       ├── llms-full.txt
│       ├── openapi.json
│       ├── pricing.md
│       ├── robots.txt                # optional
│       └── sitemap.xml               # optional
│
├── codex-skill/
│   ├── SKILL.md
│   ├── agents/openai.yaml            # optional metadata
│   └── scripts/install.sh            # optional
├── hermes-skill/
│   └── SKILL.md
├── reasonix-skill/
│   └── SKILL.md
├── opencode-commands/
│   ├── cli-it.md
│   ├── cli-it-list.md
│   ├── cli-it-refine.md
│   ├── cli-it-test.md
│   └── cli-it-validate.md
│
└── demoapp/                          # EXEMPLAR only (stands in for 69 apps)
    └── agent-harness/
        ├── DEMOAPP.md
        ├── setup.py
        ├── pytest.ini                # optional
        └── cli_it/
            └── demoapp/
                ├── __init__.py
                ├── __main__.py
                ├── README.md
                ├── demoapp_cli.py
                ├── core/
                │   ├── __init__.py
                │   ├── project.py
                │   └── session.py
                ├── utils/
                │   ├── __init__.py
                │   ├── demoapp_backend.py
                │   └── repl_skin.py  # copy from plugin
                ├── skills/
                │   └── SKILL.md      # packaged compatibility copy
                └── tests/
                    ├── TEST.md
                    ├── test_core.py
                    └── test_full_e2e.py
```

---

## (d) File-by-File Build Instructions

### d.1 Root docs & registries

#### `README.md`
Explain: vision (agent-native software), quick start for (1) `pip install cli-it-hub`, (2) Claude/Pi plugin install, (3) building a harness with `/cli-it`. Link hub site, registries, HARNESS.md, demos (can be textual). Document plugin commands table and project structure at a high level.

#### `CONTRIBUTING.md`
Document three contribution types: new in-repo harness, standalone registry-only CLI, features/bugs. **Registry field table** (required):

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | lowercase unique id |
| `display_name` | Yes | human name |
| `version` | Yes | semver |
| `description` | Yes | one line |
| `requires` | Yes | runtime deps or null |
| `homepage` | Yes | target software homepage |
| `source_url` | Yes | external repo URL or `null` for in-repo |
| `install_cmd` | Yes | full install command |
| `entry_point` | Yes | e.g. `cli-it-demoapp` |
| `skill_md` | Yes | `skills/cli-it-<name>/SKILL.md` or URL or null |
| `category` | Yes | category string |
| `contributors` | Yes | `[{"name","url"}]` |

#### `registry.json`
Shape:
```json
{
  "meta": {
    "repo": "https://github.com/<you>/CLI-It",
    "description": "CLI-It Hub — Agent-native stateful CLI interfaces…",
    "updated": "YYYY-MM-DD"
  },
  "clis": [ /* harness entries */ ]
}
```
Ship at least 1–3 sample harness entries including `demoapp`. Use install_cmd like:
`pip install git+https://github.com/<you>/CLI-It.git#subdirectory=demoapp/agent-harness`
(or local path docs for offline).

#### `public_registry.json`
Same `meta` + `clis[]`, but entries may include `package_manager` (`npm`, `pip`, `brew`, `bundled`, …), `npm_package`, `npx_cmd`. Start with 1–2 examples (e.g. a fictional or real public CLI).

#### `matrix_registry.json`
```json
{
  "meta": {
    "repo": "…",
    "description": "Curated CLI Matrix registry…",
    "updated": "YYYY-MM-DD",
    "schema_doc": "docs/cli-matrix/matrix_registry.schema.md"
  },
  "matrices": [ /* 1–5 matrices */ ]
}
```
Each matrix:
- `name`, `display_name`, `version`, `schema_version` (use `"2"`), `description`, `category`
- `clis`: string ids
- `capabilities[]`: `{id, intent, inputs, outputs, skill_search_hints?, providers[]}`
- Provider: `{kind, name, requires, cost_tier?, quality_tier?, offline?, install_hint?, notes?}`
- `kind` values used upstream: `harness-cli`, `public-cli`, `python`, `native`, `api`, `agent-skill`, `agent-native`, `web-search`, `bundled-script`
- Optional: `recipes[]`, `known_gaps`, `skill_md`, `suggest_to_user_template`

Implement at least **one** full matrix (e.g. simplified `image-design` or `video-creation`) with ≥3 capabilities and mixed provider kinds so preflight/install can be tested.

---

### d.2 `cli-it` package (critical)

#### `cli-it-hub/setup.py`
- `name="cli-it-hub"`, `version` synced with `cli_it_hub/__init__.py`
- `python_requires=">=3.10"`
- `install_requires=["click>=8.0", "requests>=2.28"]`
- `entry_points={"console_scripts": ["cli-it=cli_it_hub.cli:main"]}`
- At `build_py` / `sdist` time, **vendor** `../cli-it-matrix` into `cli_it_hub/_matrix_data/` (copytree; ignore `__pycache__`). Editable installs may skip vendoring if runtime resolves repo checkout first.
- `package_data` for `_matrix_data/*/SKILL.md`, `references/*`, `scripts/*`
- `MANIFEST.in`: `recursive-include cli_it_hub/_matrix_data *`

#### `cli_it_hub/registry.py`
Constants (make base URL configurable via env optional; default Pages URL):
- `REGISTRY_URL = "https://hkuds.github.io/CLI-It/registry.json"` (or your deploy URL)
- `PUBLIC_REGISTRY_URL = "…/public_registry.json"`
- `CACHE_DIR = Path.home() / ".cli-it"`
- `CACHE_TTL = 3600`

Functions:
- `_fetch_json(url, cache_file, force_refresh=False)` — cache envelope `{"_cached_at": ts, "data": …}`; on network failure fall back to stale cache
- `fetch_registry`, `fetch_public_registry`
- `fetch_all_clis` — merge lists; tag `_source` = `"harness"` | `"public"` (**copy** dicts before tagging so cache objects are not mutated)
- `get_cli(name)`, `search_clis(query)`, `list_categories()`

Also support loading **local** `registry.json` / `public_registry.json` from repo root when offline (walk parents from `__file__`) for development.

#### `cli_it_hub/matrix.py`
- `MATRIX_REGISTRY_URL`, cache file under `~/.cli-it-hub/`
- `INSTALLABLE_KINDS = {"harness-cli", "public-cli"}`
- `AGENT_INSTALLABLE_KINDS = {"agent-skill"}`
- `HARNESS_PREFIX = "cli-it-"`
- `fetch_matrix_registry`, `fetch_all_matrices`, `get_matrix`, `search_matrices`
- `check_provider_requirements(provider)` — check `requires.binary` via `shutil.which`, `requires.package` via importlib, `requires.env` via `os.environ`
- `preflight_matrix(matrix_item, capability_id=None, offline=False, …)`
- `resolve_install_scope(matrix_item, capability=None, recipe=None, only=None)`
- `search_capabilities`, `all_recipes`, `provider_install_hint`

#### `cli_it_hub/installer.py`
State files:
- `~/.cli-it-hub/installed.json`
- `~/.cli-it-hub/matrix_state.json`

Strategies based on entry fields / `package_manager`:
- pip: `python -m pip install …`
- uv if available
- npm global install
- bundled / generic: run `install_cmd` string; allow shell only when trusted operators (`|`, `&&`, …) present (commands come from registry, not raw user input)

API:
- `install_cli`, `uninstall_cli`, `update_cli`, `get_installed`
- `plan_matrix_install`, `install_matrix` (support `--dry-run`, `--resume`, capability/recipe/only scope)
- `doctor_matrix`

#### `cli_it_hub/matrix_skill.py`
Lookup order for matrix skill content:
1. Repo checkout `cli-it-matrix/<name>/`
2. Bundled `cli_it_hub/_matrix_data/<name>/`
3. Published URL `https://…/matrix/<name>/SKILL.md`

`render_matrix_skill_file(matrix_item, installed=None)` → write `~/.cli-it-hub/matrix/<name>/SKILL.md` and copy `references/` + `scripts/` assets; inject installed-tooling section between HTML comment markers `<!-- MATRIX_SKILL_PATHS:START/END -->`.

#### `cli_it_hub/preview.py` (consumer only)
- Resolve bundle ref → directory with `manifest.json` + `summary.json`
- Resolve live session ref → `session.json` + optional `trajectory.json`
- `inspect_bundle` / `inspect_session` → structured dict
- `render_html` / `render_live_html` (polling meta for live)
- `start_static_server(directory, host="127.0.0.1", port=0)`
- `open_in_browser`
- Normalize trajectory events for display
- **Never** call app renderers; only read artifacts

#### `cli_it_hub/analytics.py`
- Default provider PostHog; Umami fallback
- Gate with `CLI_HUB_NO_ANALYTICS` in (`1`,`true`,`yes`)
- Env overrides: `CLI_HUB_ANALYTICS_PROVIDER`, `CLI_HUB_ANALYTICS_DISTINCT_ID`, `CLI_HUB_POSTHOG_API_HOST`, `CLI_HUB_POSTHOG_PROJECT_TOKEN`
- **Do not** hardcode production secrets; use empty defaults or placeholder public tokens and document override
- Fire-and-forget events: install/uninstall/launch/visit/matrix_*; detect agent context heuristically from parent process / env — best effort
- No-op cleanly when disabled or network fails

#### `cli_it_hub/cli.py` — Click surface
```text
cli-it [--version]
cli-it install|uninstall|update <name>
cli-it list [-c category] [-s harness|public|npm|all] [--json]
cli-it search <query> [--json]
cli-it info <name>
cli-it launch <name> [args...]
cli-it can <query> [--json]
cli-it previews inspect|html|watch|open <ref> [options]
cli-it matrix list|search|info|preflight|install|doctor|recipes ...
```
Matrix family exit codes:
- `0` success
- `1` failure / not found
- `2` usage error
- `3` partial / capability gaps (preflight)

On root invoke without subcommand: print help. Track visit/first_run via analytics (no-op if disabled).

---

### d.3 `cli-it-plugin` (critical)

#### `HARNESS.md` (write as complete SOP)
Must include:

**Phases**
0. Source acquisition (local path or clone GitHub URL) — *command layer*
1. Codebase analysis — backend engine, GUI→API map, data model, existing CLIs, undo system
2. CLI architecture design — REPL + subcommands, command groups, state model, `--json`
3. Implementation — data layer, probe cmds, mutations, `utils/<sw>_backend.py`, export, session + **file locking**, ReplSkin, default REPL
4. Test planning — write `TEST.md` **before** tests
5. Test implementation — `test_core.py` (no backend), `test_full_e2e.py` (real software), subprocess tests resolving installed entrypoint
6. Test documentation — append pytest results to TEST.md
6.5 SKILL.md generation via `skill_generator.py` → canonical `skills/cli-it-<sw>/SKILL.md` + package copy
7. Packaging — `setup.py` with `find_namespace_packages(include=["cli_it.*"])`, console_scripts, `pip install -e .`

**Directory structure** (mandatory):
```text
<software>/agent-harness/
  <SOFTWARE>.md
  setup.py
  cli_it/          # NO __init__.py here (PEP 420)
    <software>/
      __init__.py
      __main__.py
      README.md
      <software>_cli.py
      core/
      utils/<software>_backend.py
      utils/repl_skin.py
      skills/SKILL.md
      tests/TEST.md, test_core.py, test_full_e2e.py
```

**Rules**
- Use real software for render
- Session lock pattern (see guides)
- Preview producer vs `cli-it previews` consumer split
- Copy `repl_skin.py` from plugin into harness utils

#### `skill_generator.py`
Implement:
- Dataclasses: `CommandInfo`, `CommandGroup`, `Example`, `SkillMetadata`
- `extract_cli_metadata(harness_path)` — find `cli_it/<sw>/`, parse CLI module Click decorators (regex OK), `setup.py` version, README intro
- `generate_skill_md` / `generate_skill_file` — fill `templates/SKILL.md.template` (simple `{{ var }}` / loop placeholders; implement a tiny renderer or use string templates)
- Canonical skill name: `cli-it-<software-dir-with-hyphens>`
- Write both root `skills/…` and package `skills/SKILL.md`

#### `preview_bundle.py`
- `PROTOCOL_VERSION = "preview-bundle/v1"`
- `TRAJECTORY_PROTOCOL_VERSION = "preview-trajectory/v1"`
- `bundle_root(software, recipe, project_path=None, root_dir=None)` → `~/.cli-it/previews/<sw>/<recipe>` or project-local `.cli-it/previews`
- Fingerprints `sha256:…` via canonical JSON
- `prepare_bundle` / `finalize_bundle` writing `manifest.json`, `summary.json`, `artifacts/`
- Live trajectory: `append_live_trajectory`, `load_live_trajectory`, `summarize_trajectory`

#### `repl_skin.py`
Class `ReplSkin(name, version)` with:
- `print_banner()` — show skill path: prefer repo-root `skills/cli-it-<name>/SKILL.md` if exists else package skill
- `create_prompt_session()` — prompt_toolkit if available, else fallback `input()`
- `success` / `error` / `warning` / `info` / `status` / `table` / `help` / `progress` / `print_goodbye`

Optional dependency: `prompt_toolkit` (soft).

#### `commands/*.md`
Agent instruction docs (not executable code):
- `cli-it.md` — full build phases 0–7; require reading HARNESS.md first; accept local path or GitHub URL only (not bare names)
- `refine.md` — inventory coverage, gap analysis, optional focus area
- `test.md` — run pytest, update TEST.md
- `validate.md` — checklist against HARNESS
- `list.md` — scan for harnesses / installed tools

#### Guides
Write practical short guides:
- `session-locking.md` — open `r+`, lock, truncate, write JSON
- `preview-methodology.md` — producer CLI surface + honesty rules
- `skill-generation.md` — how to run skill_generator
- `pypi-publishing.md` — setup.py namespace packaging
- `mcp-backend.md` — when software exposes MCP instead of CLI
- others can be short stubs with the right titles

#### `templates/SKILL.md.template`
YAML frontmatter + installation + command groups table + examples + agent guidance (`--json`, exit codes, absolute paths) as in upstream.

---

### d.4 Agent adapters

#### `.pi-extension/cli-it/index.ts`
- Export default function `(pi: ExtensionAPI)`
- Register commands: `cli-it`, `cli-it:refine`, `cli-it:test`, `cli-it:validate`, `cli-it:list`
- On run: read local `HARNESS.md` + `commands/<cmd>.md` assets (install.sh should copy plugin assets beside extension) and `pi.sendUserMessage` with path remapping rules:
  - hardcoded `/root/cli-it/...` → cwd
  - `cli-it-plugin/repl_skin.py` → extension `scripts/repl_skin.py`
  - guides/templates/scripts resolve under extension dir
- Validate args; notify usage on empty args

#### `.claude-plugin/marketplace.json` + `cli-it-plugin/.claude-plugin/plugin.json`
Minimal JSON metadata naming plugin `cli-it` with source `./cli-it-plugin`.

#### `codex-skill/`, `hermes-skill/`, `reasonix-skill/`, `opencode-commands/`
Thin wrappers: instruct agent to follow HARNESS.md / run equivalent of `/cli-it` workflow. Keep short.

---

### d.5 Preview protocol doc

#### `docs/PREVIEW_PROTOCOL.md`
Document:
- Preview Bundle directory layout (`manifest.json`, `summary.json`, `artifacts/`)
- Live Session (`session.json` + append-only `trajectory.json`)
- Producer CLI surface: `preview recipes|capture|latest|diff|live start|push|status|stop`
- Consumer: `cli-it previews …`
- Caching/fingerprint rules, artifact roles, headless requirement
- Explicit non-goals (no remote framebuffer)

---

### d.6 Hub site (`docs/hub`)

- `_config.yml` — basic Jekyll title/description
- `index.md` — hub landing pointing to registries and install instructions
- `llms.txt` / `llms-full.txt` — agent-oriented product summary + commands + registry URLs
- `openapi.json` — OpenAPI 3.1 read-only paths: `/registry.json`, `/public_registry.json`, `/registry-dates.json`, `/llms.txt`, `/llms-full.txt`, `/pricing.md`; schema `Registry` with `meta` + `clis[]`
- `pricing.md` — free/open-source note (upstream is open)

CI `deploy-pages.yml` should: copy registries into `docs/hub/`, generate dates/meta-skill scripts, build pages, publish matrix skills under `/matrix/<name>/`.

For local dev without Pages: `python -m http.server` from `docs/hub` after copying JSON, and point registry URLs via env or local fallback in `registry.py`.

---

### d.7 CI scripts & workflows

#### Scripts
- `update_registry_dates.py` — write `registry-dates.json` or update meta dates (best-effort from git history)
- `generate_meta_skill.py` — build a catalog meta-skill markdown from `registry.json`
- `validate_root_skills.py` / `sync_root_skills.py` — ensure `skills/cli-it-*` exists for in-repo harnesses and matches package skills

#### Workflows
- `publish-cli-it.yml` — on `cli-it-hub/**` push to main: build wheel, PyPI trusted publish if version not exists
- `deploy-pages.yml` — copy registries, jekyll build, matrix rsync, deploy
- `check-root-skills.yml` — run validate script on PRs touching harnesses/skills

Stub secrets: `DO_SPACES_*` optional; skip upload if unset.

---

### d.8 Exemplar harness `demoapp`

Implement a **minimal but real** harness that:
- Uses Click group `invoke_without_command=True` → REPL
- Command groups: `project` (new/open/save/info), `session` (undo/redo/status), maybe `export`
- State file JSON with locking
- `utils/demoapp_backend.py` — either call a trivial real tool (`python`, `echo`, `ffmpeg` if present) or a documented “demo backend” that writes a verifiable output file (still follow pattern of backend module)
- `--json` flag on root
- `setup.py` namespace package, entry `cli-it-demoapp=cli_it.demoapp.demoapp_cli:cli`
- Unit tests without backend; e2e tests that create project file and verify structure
- Dual SKILL.md paths
- Registry entry + root skill

This proves the monorepo conventions without cloning Blender.

---

### d.9 Matrix skill packs

For each matrix name in `matrix_registry.json`, provide `cli-it-matrix/<name>/SKILL.md` describing workflow stages and pointing agents at `cli-it matrix preflight/install` and capability ids. Video-creation can be simplified vs upstream (upstream is huge).

---

## (e) Dependencies & Installation

### Hub runtime
```text
click>=8.0
requests>=2.28
```
Optional soft deps:
```text
prompt_toolkit>=3.0   # nicer REPL
pytest>=7.0           # tests
build                 # packaging
```

### Install (dev)
```bash
mkdir -p /Users/kc/cli-it && cd /Users/kc/cli-it  # implement in place
# or: git init in /Users/kc/cli-it
python3 -m venv .venv && source .venv/bin/activate
pip install -e ./cli-it
pip install -e ./demoapp/agent-harness
pip install pytest
```

### Install (users, after publish)
```bash
pip install cli-it-hub
cli-it install demoapp
```

### Agent skill discovery (optional)
```bash
npx skills add <owner>/CLI-It --skill cli-it-meta-skill -g -y
npx skills add <owner>/CLI-It --skill cli-it-demoapp -g -y
```

### Pi extension
```bash
bash .pi-extension/cli-it/install.sh   # copy assets into Pi extensions dir
```

---

## (f) Environment Setup

| Name | Required | Purpose |
|------|----------|---------|
| `CLI_HUB_NO_ANALYTICS` | No | Set `1` to disable telemetry |
| `CLI_HUB_ANALYTICS_PROVIDER` | No | `posthog` or `umami` |
| `CLI_HUB_ANALYTICS_DISTINCT_ID` | No | Override distinct id |
| `CLI_HUB_POSTHOG_API_HOST` | No | Override API host |
| `CLI_HUB_POSTHOG_PROJECT_TOKEN` | No | Override token |
| `CLI_HUB_REGISTRY_BASE_URL` | No (recommended addition) | Override Pages base for local registries |
| Matrix provider envs | No | e.g. `OPENAI_API_KEY`, `ELEVENLABS_API_KEY` — only if matrices reference them |
| `DO_SPACES_KEY` / `DO_SPACES_SECRET` / `DO_SPACES_BUCKET` / `DO_SPACES_ENDPOINT` | CI only | Optional catalog upload |

Local state (auto-created, not env):
- `~/.cli-it-hub/` — caches, `installed.json`, `matrix_state.json`, rendered matrix skills
- `~/.cli-it/previews/` — preview bundles
- project `.cli-it/previews/` when project_path set

**Never commit real secrets.** Analytics tokens in code must be placeholders.

---

## (g) Run & Test Instructions

### Smoke hub
```bash
export CLI_HUB_NO_ANALYTICS=1
cli-it --version
cli-it list --json
cli-it search demo --json
cli-it info demoapp
cli-it install demoapp          # or pip install -e demoapp/agent-harness
cli-it can "create project" --json
cli-it matrix list --json
cli-it matrix preflight <matrix-name> --json
```

### Smoke harness
```bash
cli-it-demoapp --help
cli-it-demoapp project new -o /tmp/demo.json
cli-it-demoapp --json project info -p /tmp/demo.json
# REPL:
cli-it-demoapp
```

### Preview (if implemented on demoapp)
```bash
cli-it-demoapp preview capture ... --json
cli-it previews inspect <bundle-path>
cli-it previews html <bundle-path> -o /tmp/preview.html
```

### Tests
```bash
pytest -q cli-it-hub/tests
pytest -q demoapp/agent-harness
pytest -q cli-it-plugin/tests
python .github/scripts/validate_root_skills.py
```

### Skill generator
```bash
python cli-it-plugin/skill_generator.py demoapp/agent-harness
# or python -c 'from skill_generator import generate_skill_file; ...'
```

### Local hub static
```bash
cp registry.json public_registry.json matrix_registry.json docs/hub/
cd docs/hub && python -m http.server 8080
# point client at http://127.0.0.1:8080/… via local fallback or env
```

---

## (h) Design Decisions & Conventions

### Intentional divergences from upstream (CLI-Anything)
- **Name:** product, packages, entrypoints, skills, and state dirs use **CLI-It / cli-it**, not CLI-Anything / cli-anything.
- **Hub CLI binary:** `cli-it` (PyPI/distribution name `cli-it-hub`, import package `cli_it_hub`).
- **Harness entrypoints:** `cli-it-<software>` and namespace `cli_it.<software>`.
- **Plugin directory:** `cli-it-plugin/`; Pi extension `.pi-extension/cli-it/`.
- **State dirs:** `~/.cli-it-hub/`, `~/.cli-it/previews/`, project `.cli-it/previews/`.
- **Implement root:** `/Users/kc/cli-it` only (not a fork path of HKUDS/CLI-Anything).
- **Registries:** ship small sample JSON for demoapp/matrices; do not scrape or copy upstream live registry contents as a product catalog.
- Fidelity is to **architecture and contracts**, not trademarks, demos, or community harness corpus.


1. **Real backend boundary** — intermediate files in-process; final fidelity via external binary/MCP.
2. **Namespace packages** — never add `cli_it/__init__.py`.
3. **Naming** — `cli-it-<software>` for package, entrypoint, and skill id; path `<software>/agent-harness/`.
4. **Click dual mode** — `invoke_without_command=True` → REPL; global `--json`.
5. **Shared ReplSkin** — copy, don’t diverge per harness without reason.
6. **Session locking** — exclusive lock around session JSON writes.
7. **Skills dual-write** — root `skills/` canonical for monorepo/`npx skills`; package copy for installed wheels.
8. **Preview split** — harnesses produce bundles; `cli-it previews` only consumes.
9. **Registry-driven installs** — hub does not hardcode software list; JSON is source of truth.
10. **Copy-before-tag** when merging registry entries with `_source`.
11. **Matrix exit code 3** means gaps, not hard crash — agents can continue with partial tooling.
12. **Tests: plan then code** — TEST.md before tests; unit pure; e2e may skip if backend missing (`pytest.importorskip` / skip markers).
13. **Agent contract** — absolute paths, check RC, parse JSON stdout, verify outputs exist.
14. **Analytics off by default in dev** via `CLI_HUB_NO_ANALYTICS=1` in docs.
15. **Plugin commands are prompts** — Claude/Pi inject markdown SOP; they are not Python CLIs themselves.

Code style: Python 3.10+ type hints where helpful, Click for CLIs, stdlib pathlib, focused modules, readable errors with install hints when binaries missing.

---

## (i) Out of Scope / Do Not Invent

### Explicitly out of scope (do not invent full ports)
- **Do not reuse CLI-Anything branding**, logos, Trendshift badges, or claim to be HKUDS/CLI-Anything.
- Do not bulk-copy upstream registry entries as your product catalog (samples only).

- Full implementations of the ~69 upstream harnesses (Blender, FreeCAD, GIMP, n8n, …). Provide **pattern + one demoapp only**.
- Bit-identical hub marketing HTML, demo GIFs, multi-language READMEs.
- Production PostHog/Umami/DigitalOcean configuration and real tokens.
- Formal matrix JSON Schema file if not written (`docs/cli-matrix/…`) — optional.
- Full upstream test volume (2461 tests) — aim for solid unit coverage of hub + demoapp + skill_generator.

### Unknowns / low confidence (stub or ask)
- Exact full HTML structure of `docs/hub/index.html` (not deep-read) — static markdown hub is enough.
- Exact body of every guide beyond titles/intent — write correct, concise versions.
- Exact `cli-it-skill/` path used in DO Spaces upload (upstream deploy references it; may be generated) — generate meta-skill into a known path and document it.
- Exact public client tokens — use placeholders.
- Per-harness domain commands (bpy, script-fu, MLT, …) — not required for core recreation.

### Safety
- Do not copy any live credentials.
- Do not shell-execute untrusted user strings as install commands; only registry-trusted `install_cmd` with clear docs.
- Path traversal: when handling skill/token file paths in any harness, resolve and restrict to safe roots.

### Success criteria (recreation done when)
All of the following under `/Users/kc/cli-it`:
1. `pip install -e ./cli-it-hub` yields working `cli-it list/search/info` against local or remote registries.
2. `demoapp` installs and runs with REPL + `--json` + unit tests green.
3. `HARNESS.md` + plugin commands + Pi extension exist and describe the 7-phase pipeline.
4. `skill_generator` produces valid SKILL.md for demoapp into `skills/` + package.
5. Preview helper can write a minimal bundle; `cli-it previews inspect` reads it.
6. At least one matrix preflight/install dry-run works.
7. CI workflow YAML exists for pages + hub publish + skills validate (may be dry-runnable locally).

---

## Optional Phase-4 knobs (for later refinement)
- Collapse monorepo → single package
- Drop analytics entirely
- Drop Pi/Claude adapters; keep hub only
- Add more exemplar harnesses
- Swap Click → Typer
- Offline-first registries only (no network)
