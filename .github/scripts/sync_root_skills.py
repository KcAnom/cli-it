#!/usr/bin/env python3
"""Sync root skills from harness packages (repair tool for validate failures).

For every in-repo harness, regenerate both SKILL.md copies via the plugin's
skill_generator (source of truth = the harness CLI code), then re-validate.

Usage: python .github/scripts/sync_root_skills.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GENERATOR = REPO_ROOT / "cli-it-plugin" / "skill_generator.py"


def main() -> int:
    registry = json.loads((REPO_ROOT / "registry.json").read_text(encoding="utf-8"))
    failed = False
    for entry in registry.get("clis", []):
        if entry.get("source_url") is not None:
            continue
        harness = REPO_ROOT / entry["name"] / "agent-harness"
        if not harness.is_dir():
            print(f"skip {entry['name']}: no harness dir at {harness}")
            continue
        result = subprocess.run(
            [sys.executable, str(GENERATOR), str(harness), "--repo-root", str(REPO_ROOT)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"FAILED {entry['name']}: {result.stderr.strip()}")
            failed = True
        else:
            for line in result.stdout.strip().splitlines():
                print(f"synced {line}")

    validate = subprocess.run(
        [sys.executable, str(REPO_ROOT / ".github" / "scripts" / "validate_root_skills.py")]
    )
    return 1 if failed or validate.returncode != 0 else 0


if __name__ == "__main__":
    sys.exit(main())
