---
description: List CLI-It harnesses in this project and installed CLI-It tools
---

# /cli-it:list — inventory

Execute `${CLAUDE_PLUGIN_ROOT}/commands/list.md`, reading any
`cli-it-plugin/<file>` reference as `${CLAUDE_PLUGIN_ROOT}/<file>`.

Scope, in order:

1. **In-repo harnesses** — every `*/agent-harness/` under the working
   directory: software name, entry point, version from `setup.py`, command
   groups from the CLI module, and whether tests and SKILL.md exist.
2. **Installed tools** — `cli-it --version`, then `cli-it list` if available,
   then probe PATH for `cli-it-*` entry points.
3. **Registries** — if the working directory is a CLI-It checkout with
   `registry.json`, cross-check that every in-repo harness has both an entry
   and a root skill at `skills/cli-it-<name>/`. Skip this step outside a
   checkout instead of reporting phantom inconsistencies.

Output one table for harnesses and one for installed tools, followed by any
inconsistencies found.
