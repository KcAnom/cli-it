"""End-to-end tests against the **real** repomix binary.

Drives the installed entry point through subprocess. The whole module skips
cleanly when repomix cannot be reached.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cli_it.repomix.utils import repomix_backend as _backend

pytestmark = pytest.mark.skipif(
    not _backend.available(),
    reason="repomix binary not found (npm install -g repomix, or set $REPOMIX_BIN)",
)

TIMEOUT = 600


def harness_argv() -> list[str]:
    found = shutil.which("cli-it-repomix")
    return [found] if found else [sys.executable, "-m", "cli_it.repomix"]


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        harness_argv() + list(args),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )


@pytest.fixture()
def fixture_repo(tmp_path: Path) -> Path:
    """A tiny but real source tree for repomix to pack."""
    root = tmp_path / "fixture"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.js").write_text(
        'export function hi(name) {\n  return "hi " + name;\n}\n', encoding="utf-8"
    )
    (root / "README.md").write_text("# Fixture\n\nA sample project.\n", encoding="utf-8")
    return root


@pytest.fixture()
def profile(tmp_path: Path, fixture_repo: Path) -> Path:
    path = tmp_path / "e2e.profile.json"
    result = run(
        "profile", "new", "-n", "e2e", "-t", str(fixture_repo), "-o", str(path)
    )
    assert result.returncode == 0, result.stderr or result.stdout
    out = tmp_path / "packed.xml"
    assert run("option", "set", "-p", str(path), "output", str(out)).returncode == 0
    return path


def test_version():
    result = run("--version")
    assert result.returncode == 0, result.stderr
    assert "cli-it-repomix" in result.stdout


def test_backend_probe_reports_real_version():
    result = run("--json", "backend")
    assert result.returncode == 0, result.stderr
    info = json.loads(result.stdout)
    assert info["available"] is True
    assert info["version"]


def test_pack_run_produces_verified_output(profile: Path, tmp_path: Path):
    result = run("--json", "pack", "run", "-p", str(profile))
    assert result.returncode == 0, result.stderr or result.stdout
    data = json.loads(result.stdout)
    assert data["exists"] is True
    assert Path(data["output_path"]).is_file()
    assert data["total_files"] == 2
    assert data["total_tokens"] > 0
    assert data["security"]["clean"] is True


def test_analyze_tokens_and_metrics(profile: Path):
    tokens = run("--json", "analyze", "tokens", "-p", str(profile))
    assert tokens.returncode == 0, tokens.stderr or tokens.stdout
    tree = json.loads(tokens.stdout)
    assert tree["tree"], "expected a non-empty token tree"
    assert tree["summary"]["total_tokens"] > 0

    metrics = run("--json", "analyze", "metrics", "-p", str(profile))
    assert metrics.returncode == 0, metrics.stderr or metrics.stdout
    assert json.loads(metrics.stdout)["summary"]["total_files"] == 2


def test_analyze_files_uses_real_json_output(profile: Path):
    """The inventory comes from repomix's JSON, so it must match the fixture exactly."""
    result = run("--json", "analyze", "files", "-p", str(profile))
    assert result.returncode == 0, result.stderr or result.stdout
    data = json.loads(result.stdout)
    assert data["source"] == "repomix --style json --stdout"
    assert data["total_files"] == 2
    paths = {row["path"] for row in data["files"]}
    assert paths == {"src/a.js", "README.md"}
    assert all(row["chars"] > 0 for row in data["files"])
    assert data["total_chars"] == sum(row["chars"] for row in data["files"])


def test_backend_probe_reports_version_tested(profile: Path):
    info = json.loads(run("--json", "backend").stdout)
    assert info["tested_versions"] == "1.17.x"
    assert info["version_tested"] in (True, False)
    if info["version_tested"] is False:
        assert "warning" in info, "an untested version must be flagged"


def test_security_check_clean_fixture(profile: Path):
    result = run("--json", "security", "check", "-p", str(profile))
    assert result.returncode == 0, result.stderr or result.stdout
    assert json.loads(result.stdout)["clean"] is True


def test_token_budget_is_really_enforced(profile: Path):
    assert run("option", "set", "-p", str(profile), "token_budget", "1").returncode == 0
    result = run("pack", "run", "-p", str(profile))
    assert result.returncode != 0
    assert "budget" in (result.stdout + result.stderr).lower()


def test_skill_generate_writes_real_skill(fixture_repo: Path, tmp_path: Path):
    out = tmp_path / "skillout"
    result = run(
        "--json",
        "skill",
        "generate",
        "-d",
        str(fixture_repo),
        "-n",
        "fixture-skill",
        "-o",
        str(out),
    )
    assert result.returncode == 0, result.stderr or result.stdout
    files = json.loads(result.stdout)["files"]
    assert (out / "SKILL.md").is_file()
    for reference in ("summary.md", "project-structure.md", "files.md"):
        assert (out / "references" / reference).is_file(), f"missing {reference}"
    assert files


def test_exported_config_is_accepted_by_real_repomix(
    profile: Path, fixture_repo: Path, tmp_path: Path
):
    """The config the harness writes must be one repomix actually reads."""
    config_file = tmp_path / "repomix.config.json"
    export = run("--json", "config", "export", "-p", str(profile), "-f", str(config_file))
    assert export.returncode == 0, export.stderr or export.stdout
    assert config_file.is_file()

    show = run("--json", "config", "show", "-f", str(config_file))
    assert show.returncode == 0, show.stderr or show.stdout
    assert isinstance(json.loads(show.stdout), dict)

    direct = subprocess.run(
        _backend.resolve_bin() + ["-c", str(config_file), "--stdout", str(fixture_repo)],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    assert direct.returncode == 0, direct.stderr
    assert "a.js" in direct.stdout


def test_preview_capture_after_real_pack(profile: Path, tmp_path: Path):
    assert run("pack", "run", "-p", str(profile)).returncode == 0
    root = tmp_path / "previews"
    result = run("--json", "preview", "capture", "-p", str(profile), "--root", str(root))
    assert result.returncode == 0, result.stderr or result.stdout
    bundle = Path(json.loads(result.stdout)["bundle"])
    assert (bundle / "manifest.json").is_file()
    assert (bundle / "artifacts" / "report.json").is_file()
