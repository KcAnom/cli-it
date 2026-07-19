"""DemoApp e2e tests — subprocess against the installed entry point with the
real engine. Skips cleanly when the backend is unavailable."""

import json
import shutil
import subprocess
import sys

import pytest

from cli_it.demoapp.utils import demoapp_backend

pytestmark = pytest.mark.skipif(
    not demoapp_backend.backend_available(), reason="DemoApp engine not available"
)


def _base_cmd() -> list[str]:
    exe = shutil.which("cli-it-demoapp")
    if exe:
        return [exe]
    return [sys.executable, "-m", "cli_it.demoapp"]


def run_cli(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [*_base_cmd(), *args], capture_output=True, text=True, input=input_text
    )


def test_help_and_version():
    assert run_cli("--help").returncode == 0
    version = run_cli("--version")
    assert version.returncode == 0 and "0.1.0" in version.stdout


def test_full_workflow_new_add_undo(tmp_path):
    project = tmp_path / "e2e.json"
    assert run_cli("project", "new", "-n", "e2e", "-o", str(project)).returncode == 0

    for name in ("one", "two"):
        assert run_cli("item", "add", "-p", str(project), "-n", name).returncode == 0

    info = run_cli("--json", "project", "info", "-p", str(project))
    assert info.returncode == 0
    assert json.loads(info.stdout)["items"] == 2

    assert run_cli("session", "undo", "-p", str(project)).returncode == 0
    listed = run_cli("--json", "item", "list", "-p", str(project))
    assert [i["name"] for i in json.loads(listed.stdout)["items"]] == ["one"]


def test_export_renders_via_real_engine(tmp_path):
    project = tmp_path / "render.json"
    run_cli("project", "new", "-n", "render", "-o", str(project))
    run_cli("item", "add", "-p", str(project), "-n", "hello", "-k", "note")

    text_out = tmp_path / "out.txt"
    result = run_cli("export", "run", "-p", str(project), "-o", str(text_out))
    assert result.returncode == 0, result.stderr
    content = text_out.read_text()
    assert "DemoApp render" in content and "hello" in content

    json_out = tmp_path / "out.json"
    result = run_cli(
        "export", "run", "-p", str(project), "-o", str(json_out), "-f", "json"
    )
    assert result.returncode == 0
    doc = json.loads(json_out.read_text())
    assert doc["renderer"] == "demoapp-engine/1.0" and doc["item_count"] == 1


def test_preview_capture_writes_protocol_bundle(tmp_path):
    project = tmp_path / "prev.json"
    run_cli("project", "new", "-n", "prev", "-o", str(project))
    run_cli("item", "add", "-p", str(project), "-n", "frame")

    previews_root = tmp_path / "previews"
    result = run_cli(
        "--json",
        "preview",
        "capture",
        "-p",
        str(project),
        "--root",
        str(previews_root),
    )
    assert result.returncode == 0, result.stderr
    bundle = json.loads(result.stdout)["bundle"]

    manifest = json.loads((previews_root / "demoapp" / "render" / "manifest.json").read_text())
    assert manifest["protocol"] == "preview-bundle/v1"
    assert manifest["status"] == "complete"
    assert manifest["fingerprint"].startswith("sha256:")
    summary = json.loads((previews_root / "demoapp" / "render" / "summary.json").read_text())
    assert summary["items"] == 1
    assert any(a["path"] == "artifacts/render.txt" for a in summary["artifacts"])
    assert bundle.endswith("demoapp/render")


def test_repl_smoke_banner_and_exit():
    result = run_cli(input_text="help\nexit\n")
    assert result.returncode == 0
    assert "CLI-It · demoapp" in result.stdout
    assert "bye" in result.stdout
