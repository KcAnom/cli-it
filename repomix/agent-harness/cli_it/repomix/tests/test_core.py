"""Unit tests for the repomix harness — no repomix installation required.

Every backend call is either stubbed or avoided; the parsing tests are fed
text captured from a real repomix 1.17.0 run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli_it.repomix.core import profile as _profile
from cli_it.repomix.core import session as _session
from cli_it.repomix.repomix_cli import cli
from cli_it.repomix.utils import repomix_backend as _backend

# Captured from `repomix --token-count-tree` on a two-file fixture (v1.17.0).
REAL_STDOUT = """
🔢 Token Count Tree:
────────────────────
├── README.md (4 tokens)
└── src/ (11 tokens)
    └── a.js (11 tokens)

🔎 Security Check:
──────────────────
✔ No suspicious files detected.


📊 Pack Summary:
────────────────
  Total Files: 2 files
 Total Tokens: 396 tokens
  Total Chars: 1,840 chars
       Output: repomix-output.xml
     Security: ✔ No suspicious files detected

🎉 All Done!
"""

DIRTY_SECURITY = """
🔎 Security Check:
──────────────────
2 suspicious file(s) detected and excluded:
1. src/secrets.env
2. config/keys.json

📊 Pack Summary:
────────────────
  Total Files: 3 files
"""


@pytest.fixture()
def profile_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.profile.json"
    _profile.save_profile(_profile.new_profile("test"), path)
    return path


# --- profile model -----------------------------------------------------------


def test_new_profile_defaults():
    profile = _profile.new_profile()
    assert profile.targets == ["."]
    assert profile.style == "xml"
    assert profile.output == "repomix-output.xml"
    assert profile.token_encoding == "o200k_base"


def test_save_load_round_trip(tmp_path: Path):
    profile = _profile.new_profile("round", ["src", "docs"])
    profile.include = ["**/*.py"]
    profile.ignore = ["**/*.pyc"]
    profile.options = {"compress": True}
    profile.token_budget = 1000
    path = tmp_path / "p.json"
    _profile.save_profile(profile, path)
    loaded = _profile.load_profile(path)
    assert _profile.to_dict(loaded) == _profile.to_dict(profile)


def test_load_missing_profile(tmp_path: Path):
    with pytest.raises(_profile.ProfileError, match="not found"):
        _profile.load_profile(tmp_path / "nope.json")


def test_load_invalid_json(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(_profile.ProfileError, match="not valid JSON"):
        _profile.load_profile(path)


def test_load_wrong_format(tmp_path: Path):
    path = tmp_path / "wrong.json"
    path.write_text(json.dumps({"format": "other/v9"}), encoding="utf-8")
    with pytest.raises(_profile.ProfileError, match="unsupported profile format"):
        _profile.load_profile(path)


def test_validate_rejects_bad_style_and_budget():
    profile = _profile.new_profile()
    profile.style = "yaml"
    with pytest.raises(_profile.ProfileError, match="unknown style"):
        _profile.validate(profile)
    profile.style = "xml"
    profile.token_budget = 0
    with pytest.raises(_profile.ProfileError, match="positive integer"):
        _profile.validate(profile)


# --- mutations ---------------------------------------------------------------


def test_filter_add_and_duplicate():
    profile = _profile.new_profile()
    _profile.apply_action(profile, {"op": "filter.add", "kind": "include", "pattern": "*.py"})
    assert profile.include == ["*.py"]
    with pytest.raises(_profile.ProfileError, match="already present"):
        _profile.apply_action(profile, {"op": "filter.add", "kind": "include", "pattern": "*.py"})


def test_filter_remove_missing():
    profile = _profile.new_profile()
    with pytest.raises(_profile.ProfileError, match="no such ignore pattern"):
        _profile.apply_action(
            profile, {"op": "filter.remove", "kind": "ignore", "pattern": "*.log"}
        )


def test_option_set_bool_and_style():
    profile = _profile.new_profile()
    _profile.apply_action(profile, {"op": "option.set", "key": "compress", "value": True})
    assert profile.options["compress"] is True
    _profile.apply_action(profile, {"op": "option.set", "key": "style", "value": "markdown"})
    assert profile.style == "markdown"
    with pytest.raises(_profile.ProfileError, match="unknown style"):
        _profile.apply_action(profile, {"op": "option.set", "key": "style", "value": "yaml"})


def test_option_set_invalid_budget():
    profile = _profile.new_profile()
    with pytest.raises(_profile.ProfileError, match="must be an integer"):
        _profile.apply_action(profile, {"op": "option.set", "key": "token_budget", "value": "abc"})
    with pytest.raises(_profile.ProfileError, match="positive integer"):
        _profile.apply_action(profile, {"op": "option.set", "key": "token_budget", "value": "0"})


def test_option_set_unknown_key():
    profile = _profile.new_profile()
    with pytest.raises(_profile.ProfileError, match="unknown option"):
        _profile.apply_action(profile, {"op": "option.set", "key": "warp_drive", "value": True})


def test_target_set_requires_something():
    profile = _profile.new_profile()
    with pytest.raises(_profile.ProfileError, match="needs targets or a remote"):
        _profile.apply_action(profile, {"op": "target.set", "targets": [], "remote": None})


@pytest.mark.parametrize(
    "action",
    [
        {"op": "filter.add", "kind": "include", "pattern": "*.rs"},
        {"op": "option.set", "key": "compress", "value": True},
        {"op": "option.set", "key": "style", "value": "json"},
        {"op": "target.set", "targets": ["a", "b"], "remote": None},
    ],
)
def test_invert_action_round_trips(action):
    profile = _profile.new_profile()
    before = _profile.to_dict(profile)
    _profile.apply_action(profile, action)
    inverse = _profile.invert_action(profile, action)
    _profile.apply_action(profile, inverse)
    assert _profile.to_dict(profile) == before


# --- session journal ---------------------------------------------------------


def test_record_action_clears_redo(profile_path: Path):
    _session.record_action(profile_path, {"op": "filter.add", "kind": "include", "pattern": "a"})
    _session.pop_undo(profile_path)
    assert _session.session_status(profile_path)["redo_depth"] == 1
    _session.record_action(profile_path, {"op": "filter.add", "kind": "include", "pattern": "b"})
    status = _session.session_status(profile_path)
    assert status["undo_depth"] == 1
    assert status["redo_depth"] == 0


def test_undo_redo_move_between_stacks(profile_path: Path):
    action = {"op": "filter.add", "kind": "include", "pattern": "x"}
    _session.record_action(profile_path, action)
    assert _session.pop_undo(profile_path) == action
    assert _session.session_status(profile_path)["undo_depth"] == 0
    assert _session.pop_redo(profile_path) == action
    assert _session.session_status(profile_path)["undo_depth"] == 1


def test_pop_undo_empty(profile_path: Path):
    assert _session.pop_undo(profile_path) is None


def test_corrupt_session_recovers(profile_path: Path):
    _session.session_path_for(profile_path).write_text("}}garbage", encoding="utf-8")
    status = _session.session_status(profile_path)
    assert status["undo_depth"] == 0
    _session.record_action(profile_path, {"op": "filter.add", "kind": "ignore", "pattern": "z"})
    assert _session.session_status(profile_path)["undo_depth"] == 1


def test_sequential_writes_leave_valid_json(profile_path: Path):
    for index in range(5):
        _session.record_action(
            profile_path, {"op": "filter.add", "kind": "include", "pattern": f"p{index}"}
        )
    raw = _session.session_path_for(profile_path).read_text(encoding="utf-8")
    assert len(json.loads(raw)["undo"]) == 5


def test_session_file_sits_beside_profile(profile_path: Path):
    assert _session.session_path_for(profile_path).parent == profile_path.parent


# --- argv construction -------------------------------------------------------


def test_build_argv_defaults():
    argv = _backend.build_argv(_profile.new_profile())
    assert argv[:5] == [".", "--style", "xml", "-o", "repomix-output.xml"]
    assert "--token-count-encoding" in argv


def test_build_argv_patterns_are_comma_joined():
    profile = _profile.new_profile()
    profile.include = ["src/**", "docs/**"]
    profile.ignore = ["*.test.js"]
    argv = _backend.build_argv(profile)
    assert argv[argv.index("--include") + 1] == "src/**,docs/**"
    assert argv[argv.index("-i") + 1] == "*.test.js"


def test_build_argv_boolean_flags():
    profile = _profile.new_profile()
    profile.options = {"compress": True, "remove_comments": False}
    argv = _backend.build_argv(profile)
    assert "--compress" in argv
    assert "--remove-comments" not in argv


def test_build_argv_remote_has_no_directories():
    profile = _profile.new_profile()
    profile.targets = []
    profile.remote = "user/repo"
    profile.remote_branch = "dev"
    argv = _backend.build_argv(profile)
    assert argv[:4] == ["--remote", "user/repo", "--remote-branch", "dev"]
    assert "." not in argv


def test_build_argv_token_budget():
    profile = _profile.new_profile()
    assert "--token-budget" not in _backend.build_argv(profile)
    profile.token_budget = 5000
    argv = _backend.build_argv(profile)
    assert argv[argv.index("--token-budget") + 1] == "5000"


# --- output parsing ----------------------------------------------------------


def test_parse_summary():
    summary = _backend.parse_summary("\x1b[32m" + REAL_STDOUT + "\x1b[0m")
    assert summary["total_files"] == 2
    assert summary["total_tokens"] == 396
    assert summary["total_chars"] == 1840
    assert summary["output"] == "repomix-output.xml"


def test_parse_token_tree():
    rows = _backend.parse_token_tree(REAL_STDOUT)
    names = [row["name"] for row in rows]
    assert names == ["README.md", "src/", "a.js"]
    assert rows[0]["tokens"] == 4
    assert rows[2]["depth"] > rows[1]["depth"]


def test_parse_security_clean():
    assert _backend.parse_security(REAL_STDOUT) == {
        "status": "clean",
        "clean": True,
        "suspicious_files": [],
    }


def test_parse_security_findings():
    result = _backend.parse_security(DIRTY_SECURITY)
    assert result["status"] == "findings"
    assert result["clean"] is False
    assert any("secrets.env" in entry for entry in result["suspicious_files"])


def test_parse_security_unrecognized_is_never_clean():
    """A format change upstream must not read as 'no secrets here'."""
    result = _backend.parse_security("📦 Repomix v9.0.0\nsomething entirely new\n")
    assert result["status"] == "unknown"
    assert result["clean"] is None
    assert "1.17.x" in result["detail"]


def test_security_check_refuses_unconfirmed_clean(monkeypatch):
    monkeypatch.setattr(
        _backend,
        "run_metrics",
        lambda *a, **k: {
            "summary": {"total_files": 1},
            "security": _backend.parse_security("no recognizable block"),
        },
    )
    with pytest.raises(_backend.BackendError, match="not actually confirmed"):
        _backend.run_security_check(_profile.new_profile())


@pytest.mark.parametrize(
    "version,expected",
    [("1.17.0", True), ("v1.17.9", True), ("1.18.0", False), ("2.0.1", False),
     ("", None), ("unknown", None)],
)
def test_version_is_tested(version, expected):
    assert _backend.version_is_tested(version) is expected


def test_drift_error_names_the_tested_range():
    error = _backend._drift_error("the pack summary", "line one\nline two\n")
    assert "1.17.x" in str(error)
    assert "line two" in str(error)


def test_read_config_tolerates_jsonc(tmp_path: Path):
    path = tmp_path / "repomix.config.json"
    path.write_text(
        '{\n  // a comment\n  "output": {\n    "style": "xml",\n  },\n}\n', encoding="utf-8"
    )
    assert _backend.read_config(path)["output"]["style"] == "xml"


def test_export_config_shape(tmp_path: Path):
    profile = _profile.new_profile("cfg")
    profile.include = ["src/**"]
    profile.ignore = ["*.log"]
    profile.options = {"compress": True, "no_security_check": True}
    path = tmp_path / "repomix.config.json"
    result = _backend.export_config(profile, path)
    config = result["config"]
    assert config["output"]["compress"] is True
    assert config["output"]["style"] == "xml"
    assert config["include"] == ["src/**"]
    assert config["ignore"]["customPatterns"] == ["*.log"]
    assert config["security"]["enableSecurityCheck"] is False
    assert _backend.read_config(path) == config


def test_export_config_refuses_overwrite(tmp_path: Path):
    path = tmp_path / "repomix.config.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(_backend.BackendError, match="refusing to overwrite"):
        _backend.export_config(_profile.new_profile(), path)
    _backend.export_config(_profile.new_profile(), path, overwrite=True)
    assert "$schema" in _backend.read_config(path)


def test_read_config_missing(tmp_path: Path):
    with pytest.raises(_backend.BackendError, match="no repomix config"):
        _backend.read_config(tmp_path / "absent.json")


# --- CLI ---------------------------------------------------------------------


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def test_cli_profile_new_and_session_init(runner: CliRunner, tmp_path: Path):
    path = tmp_path / "new.profile.json"
    result = runner.invoke(cli, ["profile", "new", "-n", "demo", "-o", str(path)])
    assert result.exit_code == 0, result.output
    assert path.is_file()
    assert _session.session_path_for(path).is_file()


def test_cli_profile_new_refuses_overwrite(runner: CliRunner, profile_path: Path):
    result = runner.invoke(cli, ["profile", "new", "-o", str(profile_path)])
    assert result.exit_code != 0
    assert "refusing to overwrite" in result.output


def test_cli_json_profile_info(runner: CliRunner, profile_path: Path):
    result = runner.invoke(cli, ["--json", "profile", "info", "-p", str(profile_path)])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["name"] == "test"
    assert data["style"] == "xml"


def test_cli_filter_add_then_undo(runner: CliRunner, profile_path: Path):
    add = runner.invoke(cli, ["filter", "add", "-p", str(profile_path), "**/*.md"])
    assert add.exit_code == 0, add.output
    assert _profile.load_profile(profile_path).include == ["**/*.md"]

    undo = runner.invoke(cli, ["session", "undo", "-p", str(profile_path)])
    assert undo.exit_code == 0, undo.output
    assert _profile.load_profile(profile_path).include == []


def test_cli_option_set_undo_restores_previous(runner: CliRunner, profile_path: Path):
    """Regression: overwriting ops must journal the value they replaced."""
    assert runner.invoke(
        cli, ["option", "set", "-p", str(profile_path), "style", "markdown"]
    ).exit_code == 0
    assert _profile.load_profile(profile_path).style == "markdown"

    undo = runner.invoke(cli, ["session", "undo", "-p", str(profile_path)])
    assert undo.exit_code == 0, undo.output
    assert _profile.load_profile(profile_path).style == "xml"

    redo = runner.invoke(cli, ["session", "redo", "-p", str(profile_path)])
    assert redo.exit_code == 0, redo.output
    assert _profile.load_profile(profile_path).style == "markdown"


def test_cli_option_set_unknown_key(runner: CliRunner, profile_path: Path):
    result = runner.invoke(cli, ["option", "set", "-p", str(profile_path), "nope", "1"])
    assert result.exit_code != 0
    assert "Known options" in result.output


def test_cli_pack_dry_run_does_not_call_backend(
    runner: CliRunner, profile_path: Path, monkeypatch
):
    def explode(*args, **kwargs):
        raise AssertionError("backend must not be invoked during a dry run")

    monkeypatch.setattr(_backend, "run_pack", explode)
    result = runner.invoke(cli, ["--json", "pack", "run", "-p", str(profile_path), "--dry-run"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["dry_run"] is True
    assert data["argv"][-1] != ""


def test_cli_pack_argv_matches_backend(runner: CliRunner, profile_path: Path):
    result = runner.invoke(cli, ["--json", "pack", "argv", "-p", str(profile_path)])
    assert result.exit_code == 0, result.output
    expected = _backend.full_command(_profile.load_profile(profile_path))
    assert json.loads(result.output)["argv"] == expected


def test_cli_undo_empty_journal(runner: CliRunner, profile_path: Path):
    result = runner.invoke(cli, ["session", "undo", "-p", str(profile_path)])
    assert result.exit_code != 0
    assert "nothing to undo" in result.output


def test_cli_security_unknown_exits_non_zero(runner: CliRunner, profile_path: Path, monkeypatch):
    def refuse(*args, **kwargs):
        raise _backend.BackendError("could not recognize repomix's security-check output")

    monkeypatch.setattr(_backend, "run_security_check", refuse)
    result = runner.invoke(cli, ["security", "check", "-p", str(profile_path)])
    assert result.exit_code != 0
    assert "clean" not in result.output.lower() or "could not recognize" in result.output


def test_cli_security_findings_exit_two(runner: CliRunner, profile_path: Path, monkeypatch):
    monkeypatch.setattr(
        _backend,
        "run_security_check",
        lambda *a, **k: {
            "status": "findings",
            "clean": False,
            "suspicious_files": ["src/secrets.env"],
        },
    )
    result = runner.invoke(cli, ["security", "check", "-p", str(profile_path)])
    assert result.exit_code == 2
    assert "secrets.env" in result.output


def test_cli_preview_capture_without_pack(runner: CliRunner, profile_path: Path):
    result = runner.invoke(cli, ["preview", "capture", "-p", str(profile_path)])
    assert result.exit_code != 0
    assert "no pack recorded yet" in result.output


def test_cli_target_mutually_exclusive(runner: CliRunner, profile_path: Path):
    result = runner.invoke(
        cli, ["target", "set", "-p", str(profile_path), "-t", "src", "-r", "user/repo"]
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_cli_missing_profile_names_the_path(runner: CliRunner, tmp_path: Path):
    missing = tmp_path / "absent.profile.json"
    result = runner.invoke(cli, ["profile", "info", "-p", str(missing)])
    assert result.exit_code != 0
    assert str(missing) in result.output


def test_cli_backend_reports_unavailable(runner: CliRunner, monkeypatch):
    monkeypatch.delenv("REPOMIX_BIN", raising=False)
    monkeypatch.setattr(_backend.shutil, "which", lambda name: None)
    result = runner.invoke(cli, ["--json", "backend"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["available"] is False
    assert "npm install -g repomix" in data["hint"]


def test_backend_call_without_binary_raises_hint(monkeypatch):
    monkeypatch.delenv("REPOMIX_BIN", raising=False)
    monkeypatch.setattr(_backend.shutil, "which", lambda name: None)
    with pytest.raises(_backend.BackendError, match="npm install -g repomix"):
        _backend.require_bin()
