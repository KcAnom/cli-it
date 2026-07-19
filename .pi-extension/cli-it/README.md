# CLI-It Pi extension

Registers the CLI-It harness-generation commands inside
[Pi](https://github.com/badlogic/pi-monorepo) (`@mariozechner/pi-coding-agent`).

## Install

```bash
bash install.sh
```

`install.sh` copies this extension plus the plugin assets it needs
(`HARNESS.md`, `commands/`, `guides/`, `templates/`, `skill_generator.py`,
`preview_bundle.py`, `scripts/repl_skin.py`) into
`~/.pi/agent/extensions/cli-it/`.

## Commands

| Command | Purpose |
|---------|---------|
| `cli-it <path-or-url>` | Build a full harness (7 phases) |
| `cli-it:refine [focus]` | Gap analysis / coverage refinement |
| `cli-it:test` | Run tests, update TEST.md |
| `cli-it:validate` | HARNESS.md conformance checklist |
| `cli-it:list` | Inventory harnesses + installed tools |

On invocation the extension reads the local markdown SOP, remaps paths for
your working directory, and injects it as a user message — the agent does the
rest.
