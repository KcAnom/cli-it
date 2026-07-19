# Contributing to CLI-It

Thanks for helping make real software agent-native. There are three ways to
contribute:

## 1. A new in-repo harness

Use the plugin: run `/cli-it <path-or-GitHub-URL>` in your agent, which follows
[`cli-it-plugin/HARNESS.md`](cli-it-plugin/HARNESS.md). The result must land at:

```text
<software>/agent-harness/
  <SOFTWARE>.md
  setup.py                      # find_namespace_packages(include=["cli_it.*"])
  cli_it/<software>/...         # NO cli_it/__init__.py (PEP 420)
```

Requirements before opening a PR:

- `pip install -e <software>/agent-harness` works and installs
  `cli-it-<software>`.
- Unit tests (`test_core.py`) pass without the target software installed;
  e2e tests skip cleanly when the backend is missing.
- `TEST.md` written *before* tests, updated with results after.
- SKILL.md generated via `cli-it-plugin/skill_generator.py` into both
  `skills/cli-it-<software>/SKILL.md` (canonical) and the package copy.
- A `registry.json` entry (see field table below).
- `python .github/scripts/validate_root_skills.py` passes.

## 2. A standalone, registry-only CLI

Keep your harness in your own repository and submit **only** a registry entry
(to `registry.json`, or `public_registry.json` for general-purpose public
CLIs). Set `source_url` to your repo and `install_cmd` to the full install
command.

## 3. Features and bug fixes

Regular PRs against `cli-it-hub/`, `cli-it-plugin/`, matrices, adapters, docs,
or CI. Please:

- Keep the `cli-it` CLI surface and exit codes stable (`0` ok, `1` failure,
  `2` usage, `3` capability gaps for matrix commands).
- Run `pytest -q cli-it-hub/tests cli-it-plugin/tests demoapp/agent-harness`.
- Never commit credentials; analytics tokens must remain placeholders.

## Registry entry fields

Every entry in `registry.json` / `public_registry.json` must provide:

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

`public_registry.json` entries may additionally set `package_manager`
(`pip`, `npm`, `brew`, `bundled`, …), `npm_package`, and `npx_cmd`.

## Matrix contributions

Matrices live in `matrix_registry.json` with a skill pack under
`cli-it-matrix/<name>/SKILL.md`. Use `schema_version: "2"`; each capability
declares `id`, `intent`, `inputs`, `outputs`, and a `providers[]` list with
`kind` in: `harness-cli`, `public-cli`, `python`, `native`, `api`,
`agent-skill`, `agent-native`, `web-search`, `bundled-script`. Verify with:

```bash
cli-it matrix preflight <name>
cli-it matrix install <name> --dry-run
```

## Code style

Python ≥ 3.10, Click for CLIs, `pathlib` over `os.path`, type hints where they
help, readable error messages that include install hints when a binary is
missing.

## License

By contributing you agree your work is licensed under the repository's
[Apache-2.0 license](LICENSE).
