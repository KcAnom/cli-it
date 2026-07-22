"""Unit tests for cli-it-buhocleaner — must pass WITHOUT BuhoCleaner installed.

Backend calls are monkeypatched wherever a command would touch the real app.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from cli_it.buhocleaner.buhocleaner_cli import cli
from cli_it.buhocleaner.core import plan as _plan
from cli_it.buhocleaner.core import scanner as _scanner
from cli_it.buhocleaner.core import session as _session
from cli_it.buhocleaner.utils import buhocleaner_backend as _backend


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def plan_file(tmp_path):
    path = tmp_path / "plan.json"
    _plan.save_plan(_plan.new_plan("test"), path)
    return path


# --- plan data layer ---------------------------------------------------------


def test_new_plan_enables_all_categories():  # U1
    plan = _plan.new_plan("x")
    assert set(plan.categories) == set(_plan.CATEGORIES)
    assert all(c["enabled"] for c in plan.categories.values())


def test_plan_round_trip(tmp_path):  # U2
    plan = _plan.new_plan("rt")
    plan.threshold_mb = 42
    path = tmp_path / "p.json"
    _plan.save_plan(plan, path)
    loaded = _plan.load_plan(path)
    assert loaded.name == "rt"
    assert loaded.threshold_mb == 42
    assert loaded.categories == plan.categories


def test_load_missing_plan(tmp_path):  # U3
    with pytest.raises(_plan.PlanError):
        _plan.load_plan(tmp_path / "nope.json")


def test_load_wrong_format(tmp_path):  # U4
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"format": "other/v1"}))
    with pytest.raises(_plan.PlanError):
        _plan.load_plan(path)


def test_apply_action_enabled_invert():  # U5
    plan = _plan.new_plan("x")
    action = {"op": "category.enabled", "category": "trash", "before": True, "after": False}
    _plan.apply_action(plan, action)
    assert plan.categories["trash"]["enabled"] is False
    _plan.apply_action(plan, action, invert=True)
    assert plan.categories["trash"]["enabled"] is True


def test_apply_action_threshold_invert():  # U6
    plan = _plan.new_plan("x")
    action = {"op": "plan.threshold", "before": plan.threshold_mb, "after": 500}
    _plan.apply_action(plan, action)
    assert plan.threshold_mb == 500
    _plan.apply_action(plan, action, invert=True)
    assert plan.threshold_mb == _plan.DEFAULT_THRESHOLD_MB


def test_apply_action_unknown_op():  # U7
    with pytest.raises(_plan.PlanError):
        _plan.apply_action(_plan.new_plan("x"), {"op": "bogus"})


# --- scanner -----------------------------------------------------------------


def _plan_with_root(name: str, root) -> _plan.Plan:
    plan = _plan.new_plan("scan")
    plan.category(name)["root"] = str(root)
    return plan


def test_scan_counts_bytes(tmp_path):  # U8
    root = tmp_path / "caches"
    (root / "sub").mkdir(parents=True)
    (root / "a.bin").write_bytes(b"x" * 100)
    (root / "sub" / "b.bin").write_bytes(b"y" * 50)
    result = _scanner.scan_category(_plan_with_root("user-caches", root), "user-caches")
    assert result["bytes"] == 150
    assert result["files"] == 2
    assert result["exists"] is True


def test_large_files_threshold(tmp_path):  # U9
    root = tmp_path / "dl"
    root.mkdir()
    (root / "big.bin").write_bytes(b"x" * (2 * 1024 * 1024))
    (root / "small.bin").write_bytes(b"y" * 100)
    plan = _plan_with_root("large-files", root)
    plan.threshold_mb = 1
    result = _scanner.scan_category(plan, "large-files")
    assert result["files"] == 1
    assert result["bytes"] == 2 * 1024 * 1024


def test_glob_category(tmp_path):  # U10
    root = tmp_path / "dl"
    root.mkdir()
    (root / "installer.dmg").write_bytes(b"d" * 10)
    (root / "notes.txt").write_bytes(b"t" * 10)
    result = _scanner.scan_category(_plan_with_root("dmg-installers", root), "dmg-installers")
    assert result["files"] == 1
    assert result["bytes"] == 10


def test_missing_root(tmp_path):  # U11
    result = _scanner.scan_category(
        _plan_with_root("trash", tmp_path / "absent"), "trash"
    )
    assert result["exists"] is False
    assert result["bytes"] == 0


# --- session journal ---------------------------------------------------------


def test_journal_stacks(plan_file):  # U12
    action = {"op": "category.enabled", "category": "trash", "before": True, "after": False}
    _session.record_action(plan_file, action)
    status = _session.session_status(plan_file)
    assert (status["undo_depth"], status["redo_depth"]) == (1, 0)
    assert _session.pop_undo(plan_file) == action
    status = _session.session_status(plan_file)
    assert (status["undo_depth"], status["redo_depth"]) == (0, 1)
    assert _session.pop_redo(plan_file) == action
    status = _session.session_status(plan_file)
    assert (status["undo_depth"], status["redo_depth"]) == (1, 0)


def test_journal_file_stays_valid_json(plan_file):  # U13
    for i in range(20):
        _session.record_action(plan_file, {"op": "plan.threshold", "before": i, "after": i + 1})
    raw = _session.session_path_for(plan_file).read_text()
    state = json.loads(raw)
    assert len(state["undo"]) == 20


# --- CLI surface -------------------------------------------------------------


def test_plan_new_and_info(runner, tmp_path):  # U14
    out = tmp_path / "p.json"
    result = runner.invoke(cli, ["plan", "new", "-n", "weekly", "-o", str(out)])
    assert result.exit_code == 0, result.output
    result = runner.invoke(cli, ["plan", "info", "-p", str(out)])
    assert result.exit_code == 0
    assert "weekly" in result.output


def test_plan_new_refuses_overwrite(runner, plan_file):  # U15
    result = runner.invoke(cli, ["plan", "new", "-o", str(plan_file)])
    assert result.exit_code != 0
    assert "refusing" in result.output


def test_category_disable_json(runner, plan_file):  # U16
    result = runner.invoke(cli, ["category", "disable", "-p", str(plan_file), "trash"])
    assert result.exit_code == 0, result.output
    result = runner.invoke(cli, ["--json", "category", "list", "-p", str(plan_file)])
    doc = json.loads(result.output)
    trash = next(r for r in doc["categories"] if r["name"] == "trash")
    assert trash["enabled"] is False


def test_category_enable_unknown(runner, plan_file):  # U17
    result = runner.invoke(cli, ["category", "enable", "-p", str(plan_file), "bogus"])
    assert result.exit_code != 0
    assert "unknown category" in result.output


def test_threshold_rejects_zero(runner, plan_file):  # U18
    result = runner.invoke(cli, ["category", "threshold", "-p", str(plan_file), "--mb", "0"])
    assert result.exit_code != 0


def _point_all_roots_at(runner, plan_file, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir(exist_ok=True)
    for name in _plan.CATEGORIES:
        result = runner.invoke(
            cli, ["category", "root", "-p", str(plan_file), name, str(empty)]
        )
        assert result.exit_code == 0, result.output
    return empty


def test_scan_run_json_totals(runner, plan_file, tmp_path):  # U19
    empty = _point_all_roots_at(runner, plan_file, tmp_path)
    caches = tmp_path / "caches"
    caches.mkdir()
    (caches / "blob.bin").write_bytes(b"z" * 1234)
    result = runner.invoke(
        cli, ["category", "root", "-p", str(plan_file), "user-caches", str(caches)]
    )
    assert result.exit_code == 0
    result = runner.invoke(cli, ["--json", "scan", "run", "-p", str(plan_file)])
    assert result.exit_code == 0, result.output
    doc = json.loads(result.output)
    assert doc["categories"]["user-caches"]["bytes"] == 1234
    assert doc["total_bytes"] == 1234


def test_undo_restores_enabled(runner, plan_file):  # U20
    runner.invoke(cli, ["category", "disable", "-p", str(plan_file), "trash"])
    result = runner.invoke(cli, ["session", "undo", "-p", str(plan_file)])
    assert result.exit_code == 0, result.output
    doc = json.loads(
        runner.invoke(cli, ["--json", "category", "list", "-p", str(plan_file)]).output
    )
    trash = next(r for r in doc["categories"] if r["name"] == "trash")
    assert trash["enabled"] is True


def test_undo_empty_journal(runner, plan_file):  # U21
    result = runner.invoke(cli, ["session", "undo", "-p", str(plan_file)])
    assert result.exit_code != 0
    assert "nothing to undo" in result.output


def test_scan_report_before_scan(runner, plan_file):  # U22
    result = runner.invoke(cli, ["scan", "report", "-p", str(plan_file)])
    assert result.exit_code != 0


def test_preview_capture(runner, plan_file, tmp_path):  # U23
    _point_all_roots_at(runner, plan_file, tmp_path)
    runner.invoke(cli, ["scan", "run", "-p", str(plan_file)])
    root = tmp_path / "previews"
    result = runner.invoke(
        cli,
        ["--json", "preview", "capture", "-p", str(plan_file), "--root", str(root)],
    )
    assert result.exit_code == 0, result.output
    bundle = json.loads(result.output)["bundle"]
    from pathlib import Path

    assert (Path(bundle) / "manifest.json").is_file()
    assert (Path(bundle) / "artifacts" / "report.txt").is_file()
    assert (Path(bundle) / "artifacts" / "report.json").is_file()


def test_preview_latest_missing(runner, tmp_path):  # U24
    result = runner.invoke(
        cli, ["preview", "latest", "--root", str(tmp_path / "fresh")]
    )
    assert result.exit_code != 0


def test_backend_unavailable_json(runner, monkeypatch):  # U25
    monkeypatch.setattr(_backend, "backend_available", lambda: False)
    result = runner.invoke(cli, ["--json", "backend"])
    assert result.exit_code == 0
    doc = json.loads(result.output)
    assert doc["available"] is False
    assert "install_hint" in doc


def test_prefs_set_undo_restores(runner, plan_file, monkeypatch):  # U26
    store = {"trashCanSelected": "1"}
    monkeypatch.setattr(_backend, "read_pref", lambda key: store.get(key))
    monkeypatch.setattr(
        _backend,
        "write_pref",
        lambda key, value, value_type="bool": store.__setitem__(key, str(value)),
    )
    result = runner.invoke(
        cli, ["prefs", "set", "-p", str(plan_file), "trashCanSelected", "false"]
    )
    assert result.exit_code == 0, result.output
    assert store["trashCanSelected"] == "false"
    result = runner.invoke(cli, ["session", "undo", "-p", str(plan_file)])
    assert result.exit_code == 0, result.output
    assert store["trashCanSelected"] == "1"


def test_write_pref_whitelist():  # U27
    with pytest.raises(_backend.BackendError):
        _backend.write_pref("UserID", "hax", "string")


def test_open_uninstaller_rejects_non_app(tmp_path):  # U28
    with pytest.raises(_backend.BackendError):
        _backend.open_uninstaller(tmp_path / "not-an-app.txt")


# --- GUI-driven clean (v0.2.0, backend mocked) --------------------------------


def test_clean_run_without_confirm(runner, monkeypatch):  # U29
    calls = {}
    monkeypatch.setattr(
        _backend,
        "flash_clean",
        lambda confirm=False, **kw: calls.setdefault("confirm", confirm)
        or {"found_junk": "1.2 GB", "buttons": ["Remove"], "removed": False},
    )
    result = runner.invoke(cli, ["clean", "run"])
    assert result.exit_code == 0, result.output
    assert calls["confirm"] is False
    assert "--confirm" in result.output


def test_clean_run_confirm_records_and_undoes(runner, plan_file, monkeypatch):  # U30
    outcome = {"found_junk": "2.5 GB", "buttons": [], "removed": True}
    monkeypatch.setattr(_backend, "flash_clean", lambda confirm=False, **kw: outcome)
    result = runner.invoke(cli, ["clean", "run", "--confirm", "-p", str(plan_file)])
    assert result.exit_code == 0, result.output
    assert _plan.load_plan(plan_file).metadata["last_clean"] == outcome
    result = runner.invoke(cli, ["session", "undo", "-p", str(plan_file)])
    assert result.exit_code == 0, result.output
    assert _plan.load_plan(plan_file).metadata["last_clean"] is None


def test_clean_scan_reports(runner, monkeypatch):  # U31
    monkeypatch.setattr(
        _backend,
        "flash_clean",
        lambda confirm=False, **kw: {"found_junk": "41.72 GB", "buttons": [], "removed": False},
    )
    result = runner.invoke(cli, ["clean", "scan"])
    assert result.exit_code == 0, result.output
    assert "41.72 GB" in result.output


def test_parse_snapshot():  # U32
    raw = "button|Remove\nstatic text|Found Junk 41.72 GB\nstatic text|Flash Clean\ncheckbox|User Cache Files\nbad line\n"
    snap = _backend.parse_snapshot(raw)
    assert snap["buttons"] == ["Remove"]
    assert "Flash Clean" in snap["texts"]
    assert snap["found_junk"] == "41.72 GB"


def test_ui_click_rejects_quotes():  # U33
    with pytest.raises(_backend.BackendError):
        _backend.ui_click('evil" & quit & "')


def test_clean_status_not_running(runner, monkeypatch):  # U34
    monkeypatch.setattr(_backend, "backend_available", lambda: True)
    monkeypatch.setattr(_backend, "is_running", lambda: False)
    result = runner.invoke(cli, ["clean", "status"])
    assert result.exit_code != 0
    assert "not running" in result.output


# --- appcast parsing (U35–U40) ------------------------------------------------

APPCAST = """<?xml version="1.0" encoding="utf-8"?>
<rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle" version="2.0">
  <channel>
    <title>BuhoCleaner</title>
    <item>
      <title>Version 1.13.0</title>
      <enclosure url="https://example.invalid/BuhoCleaner-1.13.0.zip"
                 sparkle:shortVersionString="1.13.0" sparkle:version="1130"/>
    </item>
    <item>
      <title>Version 1.12.0</title>
      <enclosure url="https://example.invalid/BuhoCleaner-1.12.0.zip"
                 sparkle:shortVersionString="1.12.0" sparkle:version="1120"/>
    </item>
  </channel>
</rss>
"""


def test_parse_appcast_reads_the_newest_item():  # U35
    parsed = _backend.parse_appcast(APPCAST)
    assert parsed["latest"] == "1.13.0"
    assert parsed["latest_build"] == "1130"
    assert parsed["title"] == "Version 1.13.0"


def test_parse_appcast_ignores_versions_in_prose():  # U36
    """The regex this replaced matched any occurrence anywhere in the markup."""
    noisy = APPCAST.replace(
        "<title>BuhoCleaner</title>",
        '<description>Upgrade notes: sparkle:shortVersionString="9.9.9" was '
        "used in older builds.</description>",
    )
    assert _backend.parse_appcast(noisy)["latest"] == "1.13.0"


def test_parse_appcast_version_on_the_item_itself():  # U37
    on_item = """<?xml version="1.0"?>
    <rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
      <channel><item sparkle:shortVersionString="2.0.1"><title>t</title></item></channel>
    </rss>"""
    assert _backend.parse_appcast(on_item)["latest"] == "2.0.1"


def test_parse_appcast_rejects_non_xml():  # U38
    with pytest.raises(_backend.BackendError, match="not valid XML"):
        _backend.parse_appcast("<<< not xml")


def test_parse_appcast_without_versions():  # U39
    empty = '<?xml version="1.0"?><rss><channel><item><title>t</title></item></channel></rss>'
    with pytest.raises(_backend.BackendError, match="no version found"):
        _backend.parse_appcast(empty)


def test_parse_appcast_rejects_well_formed_html_error_page():  # U41
    """An HTML error page parses as valid XML, so it must be caught here."""
    with pytest.raises(_backend.BackendError, match="no version found"):
        _backend.parse_appcast("<html><body>503 Service Unavailable</body></html>")


def test_parse_appcast_refuses_oversized_input():  # U40
    with pytest.raises(_backend.BackendError, match="larger than"):
        _backend.parse_appcast("<rss/>" + "x" * (_backend.APPCAST_MAX_BYTES + 1))
