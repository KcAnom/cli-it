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


# --- self-healing ------------------------------------------------------------

#: A future repomix that renamed its summary labels but still emits valid JSON.
#: "Files packed" / "Characters" are learnable because the JSON gives the true
#: counts to check them against; "Tokens used" is only matched by wording.
RENAMED_STUB = """#!{python}
import json
import sys

argv = sys.argv[1:]
if "--version" in argv:
    print("9.0.0")
    sys.exit(0)

FILES = {{"src/one.txt": "aaaa\\n", "two.txt": "bb\\n"}}

if "--stdout" in argv:
    json.dump({{"directoryStructure": "src/\\n  one.txt\\ntwo.txt", "files": FILES}}, sys.stdout)
    sys.exit(0)

if "-o" in argv:
    with open(argv[argv.index("-o") + 1], "w", encoding="utf-8") as handle:
        handle.write("packed\\n")

total_chars = sum(len(v) for v in FILES.values())
if "--token-count-tree" in argv:
    print("Token Count Tree:")
    print("- one.txt (3 tokens)")

print("Pack Summary:")
print("  Files packed: {{}}".format(len(FILES)))
print("  Characters: {{}}".format(total_chars))
print("  Tokens used: 99")
print("  Security: no problems found")
sys.exit(0)
"""


@pytest.fixture()
def renamed_bin(tmp_path: Path) -> Path:
    path = tmp_path / "renamed-repomix"
    path.write_text(RENAMED_STUB.format(python=sys.executable), encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture()
def knowledge_home(tmp_path: Path) -> Path:
    """Keep learned formats out of the real ~/.cli-it during tests."""
    return tmp_path / "knowledge"


def run_learning(binary: Path, home: Path, *args: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "REPOMIX_BIN": str(binary),
        "CLI_IT_REPOMIX_HOME": str(home),
    }
    return subprocess.run(
        [sys.executable, "-m", "cli_it.repomix", *args],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def test_doctor_reports_a_renamed_summary_as_degraded(renamed_bin: Path, knowledge_home: Path):
    result = run_learning(renamed_bin, knowledge_home, "--json", "doctor")
    assert result.returncode != 0, "a broken summary parser is not a healthy state"
    report = json.loads(result.stdout)
    assert report["verdict"] == "degraded"
    assert "summary" in report["failing"]
    assert report["checks"]["json_inventory"]["ok"] is True, "JSON is the ground truth"
    assert report["healed"] is False


def test_doctor_heal_learns_verified_labels(renamed_bin: Path, knowledge_home: Path):
    result = run_learning(renamed_bin, knowledge_home, "--json", "doctor", "--heal")
    report = json.loads(result.stdout)
    assert report["healed"] is True
    assert report["checks"]["summary"]["ok"] is True
    assert report["checks"]["summary"]["after_healing"] is True

    # Healing fixes what it can prove. This stub's security line is also
    # unrecognized, and that is deliberately not healable — so the overall
    # verdict stays degraded and the exit code stays non-zero.
    assert report["verdict"] == "degraded"
    assert report["failing"] == ["security"]
    assert result.returncode != 0

    learned = report["learned"]
    assert learned["Files packed"]["field"] == "total_files"
    assert learned["Files packed"]["provenance"] == "verified-against-json-output"
    assert learned["Characters"]["field"] == "total_chars"
    # Token counts have no independent source, so the match is only wording.
    assert learned["Tokens used"]["provenance"] == "label-wording-heuristic"


def test_healing_persists_and_unblocks_pack_run(
    renamed_bin: Path, knowledge_home: Path, tmp_path: Path
):
    """The point of the exercise: a command that failed now works, next run."""
    profile = _profile.new_profile("healed")
    profile.output = str(tmp_path / "out.xml")
    path = tmp_path / "healed.profile.json"
    _profile.save_profile(profile, path)

    before = run_learning(renamed_bin, knowledge_home, "pack", "run", "-p", str(path))
    assert before.returncode != 0
    assert "could not parse the pack summary" in before.stdout + before.stderr

    run_learning(renamed_bin, knowledge_home, "doctor", "--heal")

    after = run_learning(renamed_bin, knowledge_home, "--json", "pack", "run", "-p", str(path))
    assert after.returncode == 0, after.stdout + after.stderr
    assert json.loads(after.stdout)["total_files"] == 2


def test_learned_labels_are_inspectable_and_forgettable(
    renamed_bin: Path, knowledge_home: Path
):
    run_learning(renamed_bin, knowledge_home, "doctor", "--heal")
    shown = run_learning(renamed_bin, knowledge_home, "learned")
    assert "Files packed" in shown.stdout
    assert "verified-against-json-output" in shown.stdout

    run_learning(renamed_bin, knowledge_home, "doctor", "--forget")
    after = run_learning(renamed_bin, knowledge_home, "learned")
    assert "nothing learned" in after.stdout


def test_security_is_never_healed(renamed_bin: Path, knowledge_home: Path):
    """The stub says 'no problems found' — a phrase the harness must not adopt."""
    result = run_learning(renamed_bin, knowledge_home, "--json", "doctor", "--heal")
    report = json.loads(result.stdout)
    assert report["checks"]["security"]["healable"] is False
    assert report["checks"]["security"]["status"] == "unknown"

    learned = json.loads(
        run_learning(renamed_bin, knowledge_home, "--json", "learned").stdout
    )
    every_field = [
        fact["field"]
        for entry in learned.get("versions", {}).values()
        for fact in (entry.get("labels") or {}).values()
    ]
    assert "security" not in every_field, "a secrets verdict must never be learned"
