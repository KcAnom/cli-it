# cli-it-repomix

Agent-native, stateful CLI harness for the real [repomix](https://repomix.com)
codebase packer: reusable pack profiles, an undo journal over profile edits,
verified artifacts, and stable JSON on every command.

Repomix is already an excellent CLI — this harness does not reimplement any of
it. Every pack, token count, secret scan, and skill generation is performed by
the repomix binary, invoked only from `utils/repomix_backend.py`. What the
harness adds is what a stateless one-shot CLI cannot give an agent:

- **Pack profiles** — named, reusable packing recipes stored as JSON. Repomix
  keeps one `repomix.config.json` per directory; a profile lets you hold
  several recipes over the same tree and pass them around by path.
- **An undo journal** — every profile mutation is journaled under an exclusive
  file lock and reversible with `session undo`.
- **Verified execution** — `pack run` confirms the artifact exists and reports
  its real size, file count, and token count rather than trusting exit status.
- **Stable JSON** — the token tree, pack summary, and security findings that
  repomix prints as decorated human text are parsed into fixed shapes.
- **Loud failure on upstream drift** — those parsers read console output, which
  is not a stable API. When repomix's format changes, commands fail with an
  error naming the tested version range instead of returning empty-looking
  results. `security check` will never report a clean scan it could not
  actually confirm. `analyze files` avoids scraping entirely by reading
  repomix's JSON output.

## Quick start

```bash
pip install -e /path/to/cli-it/repomix/agent-harness
cli-it-repomix backend                                     # is repomix reachable?

cli-it-repomix profile new -n api -t ./src -o /tmp/api.profile.json
cli-it-repomix filter add -p /tmp/api.profile.json '**/*.ts'
cli-it-repomix option set -p /tmp/api.profile.json style markdown
cli-it-repomix option set -p /tmp/api.profile.json token_budget 200000

cli-it-repomix pack run -p /tmp/api.profile.json --dry-run  # show the argv
cli-it-repomix --json pack run -p /tmp/api.profile.json      # real pack
cli-it-repomix session undo -p /tmp/api.profile.json
cli-it-repomix --json analyze files -p /tmp/api.profile.json --top 10
cli-it-repomix config export -p /tmp/api.profile.json -f ./repomix.config.json
```

Run with no subcommand for a REPL.

## Requirements

- Python 3.10+, `click`
- repomix on PATH (`npm install -g repomix`), or `$REPOMIX_BIN`, or `npx`.
  Tested against **repomix 1.17.x** — `cli-it-repomix backend` reports whether
  your installed version is inside that range.
  Profile, filter, option, and session commands work without it; `pack`,
  `analyze`, `security`, and `skill` need the real binary.
