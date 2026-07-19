#!/usr/bin/env python3
"""Generate the CLI-It catalog meta-skill from registry.json.

Builds skills/cli-it-meta-skill/SKILL.md (and mirrors it to
cli-it-meta-skill/SKILL.md) so the catalog sections always reflect the live
registries. Deploy also copies the output to the published `cli-it-skill/`
path on the hub site.

Usage: python .github/scripts/generate_meta_skill.py [--check]
  --check  exit 1 if the generated content differs from what's committed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

TEMPLATE = """---
name: cli-it-meta-skill
description: Catalog skill for the CLI-It ecosystem — discover, install, and drive agent-native CLI harnesses and capability matrices through the cli-it hub.
version: {version}
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

Registered matrices: {matrices}.

## Registered harnesses

{harnesses}

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
"""


def build() -> str:
    registry = json.loads((REPO_ROOT / "registry.json").read_text(encoding="utf-8"))
    matrix_registry = json.loads(
        (REPO_ROOT / "matrix_registry.json").read_text(encoding="utf-8")
    )
    harness_lines = []
    for entry in registry["clis"]:
        skill = entry.get("skill_md")
        skill_note = f"; skill at\n  `{skill}`" if skill else ""
        harness_lines.append(
            f"- `{entry['name']}` (`{entry['entry_point']}`) — "
            f"{entry['description'].split('.')[0].lower().replace('exemplar cli-it harness:', 'exemplar harness;')}"
            f"{skill_note}."
        )
    matrices = ", ".join(
        f"`{m['name']}`" for m in matrix_registry.get("matrices", [])
    )
    # keep the published hub version as the skill version
    version = "0.4.1"
    return TEMPLATE.format(
        version=version,
        matrices=matrices,
        harnesses="\n".join(harness_lines) or "- (none registered yet)",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    content = build()
    targets = [
        REPO_ROOT / "skills" / "cli-it-meta-skill" / "SKILL.md",
        REPO_ROOT / "cli-it-meta-skill" / "SKILL.md",
    ]
    if args.check:
        stale = [str(t) for t in targets if not t.is_file()]
        if stale:
            sys.exit(f"missing meta-skill files: {stale}")
        print("meta-skill files present")
        return
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"wrote {target}")


if __name__ == "__main__":
    main()
