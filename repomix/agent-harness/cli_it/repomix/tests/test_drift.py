"""Upstream-drift regression tests, driven through a stub `repomix`.

These exercise the full chain — argv construction, subprocess, output parsing,
exit code — with `$REPOMIX_BIN` pointed at a script that behaves like a *future*
repomix: it succeeds, writes its output file, and prints a summary this harness
cannot parse.

That is the scenario these tests exist for. Under 0.1.0 the same stub made
`security check` print "no suspicious files detected" and exit 0 — a confident
false clean produced purely by an upstream formatting change. The unit tests in
test_core.py cover the parsers in isolation and the CLI with a monkeypatched
backend; nothing else covers the wiring between them.

No real repomix is needed: the stub is the binary.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from cli_it.repomix.core import profile as _profile

pytestmark = pytest.mark.skipif(
    os.name != "posix", reason="the stub relies on a POSIX shebang to be executable"
)

STUB = """#!{python}
\"\"\"Stands in for a future repomix that still works but reformatted its output.\"\"\"
import sys

argv = sys.argv[1:]
if "--version" in argv:
    print("9.0.0")
    sys.exit(0)

if "-o" in argv:
    target = argv[argv.index("-o") + 1]
    with open(target, "w", encoding="utf-8") as handle:
        handle.write("packed\\n")

print("Repomix v9.0.0")
print("Everything packed. Nothing to report.")
sys.exit(0)
"""


@pytest.fixture()
def stub_bin(tmp_path: Path) -> Path:
    path = tmp_path / "stub-repomix"
    path.write_text(STUB.format(python=sys.executable), encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture()
def profile_path(tmp_path: Path) -> Path:
    profile = _profile.new_profile("drift")
    profile.output = str(tmp_path / "out.xml")
    path = tmp_path / "drift.profile.json"
    _profile.save_profile(profile, path)
    return path


def run(stub_bin: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "REPOMIX_BIN": str(stub_bin)}
    return subprocess.run(
        [sys.executable, "-m", "cli_it.repomix", *args],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def test_probe_flags_untested_version(stub_bin: Path):
    result = run(stub_bin, "--json", "backend")
    assert result.returncode == 0, result.stderr
    info = json.loads(result.stdout)
    assert info["version"] == "9.0.0"
    assert info["version_tested"] is False
    assert "1.17.x" in info["warning"]


def test_pack_run_refuses_to_invent_numbers(stub_bin: Path, profile_path: Path):
    """The stub writes a real output file, so only the summary scrape can fail."""
    result = run(stub_bin, "pack", "run", "-p", str(profile_path))
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "could not parse the pack summary" in combined
    assert "1.17.x" in combined
    assert "Everything packed" in combined, "the error must echo what repomix printed"


def test_security_check_never_reports_unconfirmed_clean(stub_bin: Path, profile_path: Path):
    """The 0.1.0 regression: this printed 'no suspicious files detected', exit 0."""
    result = run(stub_bin, "security", "check", "-p", str(profile_path))
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "no suspicious files detected" not in combined.lower()


def test_analyze_tokens_refuses_an_empty_tree(stub_bin: Path, profile_path: Path):
    result = run(stub_bin, "analyze", "tokens", "-p", str(profile_path))
    assert result.returncode != 0
    assert "could not parse" in (result.stdout + result.stderr)


def test_analyze_files_rejects_non_json_output(stub_bin: Path, profile_path: Path):
    """analyze files reads JSON, so the stub's prose must be rejected, not parsed."""
    result = run(stub_bin, "analyze", "files", "-p", str(profile_path))
    assert result.returncode != 0
    assert "could not parse" in (result.stdout + result.stderr)


def test_profile_commands_still_work_against_a_broken_backend(
    stub_bin: Path, profile_path: Path
):
    """Drift must not take down the commands that never touch repomix."""
    result = run(stub_bin, "--json", "profile", "info", "-p", str(profile_path))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["name"] == "drift"
