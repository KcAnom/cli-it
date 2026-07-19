# cli-it-hub

The CLI-It Hub package manager. Installs as the `cli-it` console command.

```bash
pip install cli-it-hub
export CLI_HUB_NO_ANALYTICS=1   # optional: disable telemetry

cli-it list                     # merged harness + public registries
cli-it search video --json
cli-it info demoapp
cli-it install demoapp
cli-it launch demoapp -- --help

cli-it can "convert image" --json
cli-it matrix list
cli-it matrix preflight image-design     # exit 3 = capability gaps
cli-it matrix install image-design --dry-run
cli-it matrix doctor image-design
cli-it matrix skill image-design         # render SKILL.md with local status

cli-it previews inspect ~/.cli-it/previews/demoapp/render
cli-it previews html <bundle> -o /tmp/preview.html
cli-it previews watch <session-dir>
```

## How it resolves registries

`registry.json`, `public_registry.json`, and `matrix_registry.json` are looked
up in order: local repo checkout (dev mode) → fresh cache (1 h TTL, envelope
`{"_cached_at", "data"}` under `~/.cli-it/` and `~/.cli-it-hub/`) → the
published hub site → stale cache. Override the site base URL with
`CLI_HUB_REGISTRY_BASE_URL`.

## Local state

- `~/.cli-it-hub/` — caches, `installed.json`, `matrix_state.json`, rendered
  matrix skills under `matrix/<name>/`
- `~/.cli-it/previews/` — preview bundles written by harness producers

## Analytics

Telemetry is fire-and-forget, contains no code or file contents, and is fully
disabled with `CLI_HUB_NO_ANALYTICS=1`. The source ships only placeholder
tokens; see `cli_it_hub/analytics.py` for the environment overrides.

## Development

```bash
pip install -e ./cli-it-hub
pytest -q cli-it-hub/tests
```
