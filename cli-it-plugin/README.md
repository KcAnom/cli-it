# cli-it-plugin

The CLI-It generation plugin: a methodology (`HARNESS.md`) plus agent command
specs and helper scripts that turn any real software into an agent-native
stateful CLI harness.

**The commands here are prompts, not programs.** Claude Code / Pi / Codex /
OpenCode inject these markdown SOPs into the agent's context; the agent then
does the work, using the Python helpers in this directory.

## Contents

| Path | Purpose |
|------|---------|
| `HARNESS.md` | **Source of truth** — the 7-phase harness pipeline |
| `commands/` | Canonical agent command specs (`/cli-it`, `:refine`, `:test`, `:validate`, `:list`) |
| `claude-commands/` | Claude Code entry points — thin wrappers that bind `commands/` to `${CLAUDE_PLUGIN_ROOT}` |
| `guides/` | Deep-dives: session locking, previews, skills, packaging, MCP, … |
| `templates/SKILL.md.template` | Template consumed by the skill generator |
| `skill_generator.py` | Phase 6.5 — generates dual SKILL.md files from a harness |
| `preview_bundle.py` | Producer helpers for the preview-bundle/v1 protocol |
| `repl_skin.py` | Shared REPL look & feel — copied into every harness |
| `scripts/setup-cli-it.sh` | Convenience dev setup |

## Install

Claude Code:

```text
/plugin marketplace add KcAnom/cli-it
/plugin install cli-it
```

Pi: `bash ../.pi-extension/cli-it/install.sh`

### Why each host gets its own entry layer

`commands/` is the canonical SOP and is host-neutral: it spells asset paths as
`cli-it-plugin/<file>`, relative to a CLI-It checkout. Every host rebinds those
to wherever it installed the assets, and does so in its own way:

- **Pi** — `.pi-extension/cli-it/index.ts` rewrites them at runtime
  (`remapPaths()`) to absolute paths under the extension directory.
- **Claude Code** — `claude-commands/*.md` instruct the agent to read them as
  `${CLAUDE_PLUGIN_ROOT}/<file>`, since an installed plugin lives in the
  plugin cache, not in the user's working directory.
- **OpenCode** — `opencode-commands/` reference them from the checkout.

Consequence: **do not put host-specific text into `commands/`.** Pi copies
those files verbatim, so a `${CLAUDE_PLUGIN_ROOT}` reference there would both
leak into Pi's prompts and defeat its remap regex. Host-specific behavior
belongs in that host's own layer.

## Use

```text
/cli-it /path/to/software        # or a GitHub URL — never a bare name
/cli-it:refine export            # gap analysis, optional focus area
/cli-it:test                     # run pytest, update TEST.md
/cli-it:validate                 # checklist against HARNESS.md
/cli-it:list                     # find harnesses + installed tools
```

See [QUICKSTART.md](QUICKSTART.md) for an end-to-end walkthrough and
[PUBLISHING.md](PUBLISHING.md) for shipping a harness to PyPI + registry.
