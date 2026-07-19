"""Path-resolution tests for the dual-skill convention.

Verifies the repo keeps the canonical/package skill pairing intact for every
in-repo harness, and that ReplSkin's skill discovery finds the canonical copy
from inside a checkout.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _in_repo_harnesses():
    registry = json.loads((REPO_ROOT / "registry.json").read_text())
    return [e["name"] for e in registry["clis"] if e.get("source_url") is None]


def test_every_in_repo_harness_has_canonical_and_package_skill():
    for name in _in_repo_harnesses():
        canonical = REPO_ROOT / "skills" / f"cli-it-{name}" / "SKILL.md"
        packaged = (
            REPO_ROOT / name / "agent-harness" / "cli_it" / name / "skills" / "SKILL.md"
        )
        assert canonical.is_file(), f"missing canonical skill for {name}"
        assert packaged.is_file(), f"missing packaged skill for {name}"
        assert canonical.read_text() == packaged.read_text(), f"skill drift for {name}"


def test_no_pep420_violation():
    for name in _in_repo_harnesses():
        namespace_init = REPO_ROOT / name / "agent-harness" / "cli_it" / "__init__.py"
        assert not namespace_init.exists(), "cli_it/__init__.py breaks PEP 420"


def test_repl_skin_finds_canonical_skill_from_checkout():
    harness_utils = (
        REPO_ROOT / "demoapp" / "agent-harness" / "cli_it" / "demoapp" / "utils"
    )
    sys.path.insert(0, str(harness_utils))
    try:
        import importlib

        repl_skin = importlib.import_module("repl_skin")
        skin = repl_skin.ReplSkin("demoapp", "0.1.0")
        found = skin.skill_path()
        assert found is not None
        assert found == REPO_ROOT / "skills" / "cli-it-demoapp" / "SKILL.md"
    finally:
        sys.path.remove(str(harness_utils))
