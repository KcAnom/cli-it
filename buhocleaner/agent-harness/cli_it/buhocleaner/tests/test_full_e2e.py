"""E2E tests: drive the installed cli-it-buhocleaner entry point via subprocess.

Tests that need the real app skip cleanly when /Applications/BuhoCleaner.app
is absent. No test launches the GUI, quits the app, or writes its defaults
domain.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

APP_INSTALLED = Path("/Applications/BuhoCleaner.app/Contents/Info.plist").is_file()
needs_app = pytest.mark.skipif(not APP_INSTALLED, reason="BuhoCleaner.app not installed")


def _entry() -> list[str]:
    exe = shutil.which("cli-it-buhocleaner")
    if exe:
        return [exe]
    return [sys.executable, "-m", "cli_it.buhocleaner"]


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([*_entry(), *args], capture_output=True, text=True, timeout=120)


def test_help_lists_groups():  # E1
    result = run_cli("--help")
    assert result.returncode == 0
    for group in ("app", "plan", "category", "scan", "prefs", "session", "preview"):
        assert group in result.stdout


def test_version():  # E2
    result = run_cli("--version")
    assert result.returncode == 0
    assert "0.2.0" in result.stdout


def test_plan_scan_report_flow(tmp_path):  # E3
    plan = tmp_path / "plan.json"
    assert run_cli("plan", "new", "-n", "e2e", "-o", str(plan)).returncode == 0

    empty = tmp_path / "empty"
    empty.mkdir()
    caches = tmp_path / "caches"
    caches.mkdir()
    (caches / "blob.bin").write_bytes(b"e" * 4096)

    known = json.loads(run_cli("--json", "category", "list", "-p", str(plan)).stdout)
    for row in known["categories"]:
        root = caches if row["name"] == "user-caches" else empty
        assert run_cli("category", "root", "-p", str(plan), row["name"], str(root)).returncode == 0

    result = run_cli("--json", "scan", "run", "-p", str(plan))
    assert result.returncode == 0, result.stderr
    doc = json.loads(result.stdout)
    assert doc["categories"]["user-caches"]["bytes"] == 4096
    assert doc["total_bytes"] == 4096

    report = json.loads(run_cli("--json", "scan", "report", "-p", str(plan)).stdout)
    assert report["total_bytes"] == 4096


def test_undo_redo_round_trip(tmp_path):  # E4
    plan = tmp_path / "plan.json"
    run_cli("plan", "new", "-o", str(plan))
    assert run_cli("category", "disable", "-p", str(plan), "trash").returncode == 0
    assert run_cli("session", "undo", "-p", str(plan)).returncode == 0
    doc = json.loads(run_cli("--json", "category", "list", "-p", str(plan)).stdout)
    trash = next(r for r in doc["categories"] if r["name"] == "trash")
    assert trash["enabled"] is True
    assert run_cli("session", "redo", "-p", str(plan)).returncode == 0
    doc = json.loads(run_cli("--json", "category", "list", "-p", str(plan)).stdout)
    trash = next(r for r in doc["categories"] if r["name"] == "trash")
    assert trash["enabled"] is False


@needs_app
def test_backend_probe_real_app():  # E5
    result = run_cli("--json", "app", "info")
    assert result.returncode == 0, result.stderr
    doc = json.loads(result.stdout)
    assert doc["available"] is True
    assert doc["bundle_id"] == "com.drbuho.BuhoCleaner"
    assert doc["version"]
    assert isinstance(doc["helper_installed"], bool)
    assert isinstance(doc["running"], bool)


@needs_app
def test_prefs_show_real_domain():  # E6
    result = run_cli("--json", "prefs", "show")
    assert result.returncode == 0, result.stderr
    doc = json.loads(result.stdout)
    assert doc["domain"] == "com.drbuho.BuhoCleaner"
    assert doc["keys"]


def test_unknown_command_usage_error():  # E7
    result = run_cli("frobnicate")
    assert result.returncode == 2


@pytest.mark.skipif(
    os.environ.get("BUHO_E2E_GUI") != "1",
    reason="GUI accessibility e2e is opt-in (set BUHO_E2E_GUI=1)",
)
@needs_app
def test_clean_status_live_window():  # E8 — reads the window, clicks nothing
    result = run_cli("--json", "clean", "status")
    assert result.returncode == 0, result.stderr
    doc = json.loads(result.stdout)
    assert isinstance(doc["buttons"], list)
    assert isinstance(doc["texts"], list)
