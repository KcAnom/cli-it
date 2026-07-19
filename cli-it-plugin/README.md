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
| `commands/` | Agent command specs (`/cli-it`, `:refine`, `:test`, `:validate`, `:list`) |
| `guides/` | Deep-dives: session locking, previews, skills, packaging, MCP, … |
| `templates/SKILL.md.template` | Template consumed by the skill generator |
| `skill_generator.py` | Phase 6.5 — generates dual SKILL.md files from a harness |
| `preview_bundle.py` | Producer helpers for the preview-bundle/v1 protocol |
| `repl_skin.py` | Shared REPL look & feel — copied into every harness |
| `scripts/setup-cli-it.sh` | Convenience dev setup |

## Install

Claude Code:

```text
/plugin marketplace add elev8tion/cli-it
/plugin install cli-it
```

Pi: `bash ../.pi-extension/cli-it/install.sh`

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
