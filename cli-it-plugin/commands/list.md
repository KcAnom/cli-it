---
description: List CLI-It harnesses in this project and installed CLI-It tools
---

# /cli-it:list — inventory

1. **In-repo harnesses**: find `*/agent-harness/` directories; for each,
   report software name, entry point, version (from `setup.py`), command
   groups (from the CLI module), and whether tests + SKILL.md exist.
2. **Installed tools**: check `cli-it` itself (`cli-it --version`), then
   `cli-it list` if available; also probe PATH for `cli-it-*` entry points.
3. **Registries**: if the repo has `registry.json`, cross-check that every
   in-repo harness has an entry and a root skill under
   `skills/cli-it-<name>/`.

Output one table for harnesses, one for installed tools, plus any
inconsistencies found (missing registry entries, missing skills).
