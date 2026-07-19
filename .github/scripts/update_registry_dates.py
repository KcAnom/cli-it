#!/usr/bin/env python3
"""Write registry-dates.json: last-updated dates per registry entry.

Best-effort from git history (last commit touching the entry's harness
directory, or the registry file itself); falls back to the registry meta date
when git is unavailable. Run from the repo root; output lands in docs/hub/.

Usage: python .github/scripts/update_registry_dates.py [--output PATH]
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def git_last_date(path: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", path],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        date = result.stdout.strip()
        return date or None
    except (OSError, subprocess.SubprocessError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "docs" / "hub" / "registry-dates.json",
    )
    args = parser.parse_args()

    dates: dict[str, str] = {}
    for registry_name in ("registry.json", "public_registry.json", "matrix_registry.json"):
        registry_path = REPO_ROOT / registry_name
        doc = json.loads(registry_path.read_text(encoding="utf-8"))
        fallback = (
            git_last_date(registry_name)
            or doc.get("meta", {}).get("updated", "unknown")
        )
        for entry in doc.get("clis", doc.get("matrices", [])):
            name = entry.get("name")
            if not name:
                continue
            harness_dir = REPO_ROOT / name / "agent-harness"
            entry_date = (
                git_last_date(f"{name}/agent-harness") if harness_dir.is_dir() else None
            )
            dates[name] = entry_date or fallback

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dates, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {args.output} ({len(dates)} entries)")


if __name__ == "__main__":
    main()
