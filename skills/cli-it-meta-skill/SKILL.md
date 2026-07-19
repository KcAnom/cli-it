---
name: cli-it-meta-skill
description: Catalog skill for the CLI-It ecosystem — discover, install, and drive agent-native CLI harnesses and capability matrices through the cli-it hub.
version: 0.4.1
---

# CLI-It meta-skill

CLI-It makes real software agent-native. This skill tells you how to discover
and use the ecosystem; per-harness skills document individual tools.

## Setup

```bash
pip install cli-it-hub
export CLI_HUB_NO_ANALYTICS=1   # optional
```

## Discover and install tools

```bash
cli-it list --json                 # all registered CLIs (harness + public)
cli-it search <query> --json
cli-it info <name>                 # full registry entry incl. skill_md path
cli-it install <name>              # runs the registry's install command
cli-it launch <name> [args...]
```

## Capability-first workflow (matrices)

When you know the *goal* but not the tool:

```bash
cli-it can "convert image" --json          # intent → capability → providers
cli-it matrix list --json
cli-it matrix preflight <matrix> --json    # what's usable NOW (exit 3 = gaps)
cli-it matrix install <matrix> --dry-run
cli-it matrix skill <matrix>               # render full matrix SKILL.md locally
```

Registered matrices: `image-design`, `video-creation`, `3d-cad`,
`game-development`, `knowledge-research`.

## Registered harnesses

- `demoapp` (`cli-it-demoapp`) — exemplar harness; skill at
  `skills/cli-it-demoapp/SKILL.md`.

## Previews

Harness CLIs produce preview bundles; view them without opening any GUI:

```bash
cli-it previews inspect <bundle-or-session>
cli-it previews html <bundle> -o preview.html
cli-it previews watch <session-dir>
```

## Agent contract

- Prefer `--json` everywhere; parse stdout, check return codes.
- Exit 3 from matrix commands = capability gaps, not failure — continue with
  ready providers and report what's missing.
- Absolute paths; verify output files exist after mutations/exports.
- To make new software agent-native, run `/cli-it <path-or-url>` (see
  `cli-it-plugin/HARNESS.md`).
