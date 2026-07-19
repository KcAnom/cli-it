#!/usr/bin/env python3
"""Validate the dual-skill convention across the monorepo.

Checks, for every in-repo harness in registry.json (source_url == null):
  1. a canonical root skill exists at skills/cli-it-<name>/SKILL.md
  2. the packaged copy exists at <name>/agent-harness/cli_it/<name>/skills/SKILL.md
  3. the two are byte-identical (no drift)
  4. no PEP 420 violation (<name>/agent-harness/cli_it/__init__.py must not exist)
Also verifies every matrix in matrix_registry.json has cli-it-matrix/<name>/SKILL.md.

Exit 0 when clean; exit 1 with a report otherwise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    problems: list[str] = []

    registry = json.loads((REPO_ROOT / "registry.json").read_text(encoding="utf-8"))
    for entry in registry.get("clis", []):
        if entry.get("source_url") is not None:
            continue  # external harness; skill may live in its own repo
        name = entry["name"]
        canonical = REPO_ROOT / "skills" / f"cli-it-{name}" / "SKILL.md"
        packaged = (
            REPO_ROOT / name / "agent-harness" / "cli_it" / name / "skills" / "SKILL.md"
        )
        if not canonical.is_file():
            problems.append(f"{name}: missing canonical skill {canonical}")
        if not packaged.is_file():
            problems.append(f"{name}: missing packaged skill {packaged}")
        if (
            canonical.is_file()
            and packaged.is_file()
            and canonical.read_bytes() != packaged.read_bytes()
        ):
            problems.append(
                f"{name}: skill drift — regenerate with "
                f"`python cli-it-plugin/skill_generator.py {name}/agent-harness`"
            )
        namespace_init = REPO_ROOT / name / "agent-harness" / "cli_it" / "__init__.py"
        if namespace_init.exists():
            problems.append(f"{name}: PEP 420 violation — {namespace_init} must not exist")

    matrix_registry = json.loads(
        (REPO_ROOT / "matrix_registry.json").read_text(encoding="utf-8")
    )
    for matrix in matrix_registry.get("matrices", []):
        skill = REPO_ROOT / "cli-it-matrix" / matrix["name"] / "SKILL.md"
        if not skill.is_file():
            problems.append(f"matrix {matrix['name']}: missing {skill}")

    meta_skill = REPO_ROOT / "skills" / "cli-it-meta-skill" / "SKILL.md"
    if not meta_skill.is_file():
        problems.append(f"missing meta skill {meta_skill}")

    if problems:
        print("root-skill validation FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("root-skill validation OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
