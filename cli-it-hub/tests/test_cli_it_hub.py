"""Unit tests for cli_it_hub — no network, no real installs.

Registry resolution falls back to the repo checkout, so these tests run fully
offline. State/cache paths are redirected into tmp_path.
"""

import json
import time

import pytest
from click.testing import CliRunner

from cli_it_hub import __version__, analytics, cli, installer, matrix, preview, registry


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path, monkeypatch):
    monkeypatch.setenv("CLI_HUB_NO_ANALYTICS", "1")
    monkeypatch.setattr(registry, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(matrix, "MATRIX_CACHE_FILE", tmp_path / "matrix_cache.json")
    monkeypatch.setattr(installer, "INSTALLED_FILE", tmp_path / "installed.json")
    monkeypatch.setattr(installer, "MATRIX_STATE_FILE", tmp_path / "matrix_state.json")


# --- registry ----------------------------------------------------------------


def test_version_string():
    assert __version__.count(".") == 2


def test_fetch_registry_uses_local_checkout():
    doc = registry.fetch_registry()
    names = [entry["name"] for entry in doc["clis"]]
    assert "demoapp" in names
    assert doc["meta"]["repo"].startswith("https://")


def test_fetch_all_clis_tags_without_mutating_source():
    merged = registry.fetch_all_clis()
    assert merged, "expected at least the demoapp + public entries"
    assert {entry["_source"] for entry in merged} <= {"harness", "public"}
    # copy-before-tag: re-fetching the raw registries shows no _source leakage
    for doc in (registry.fetch_registry(), registry.fetch_public_registry()):
        assert all("_source" not in entry for entry in doc["clis"])


def test_get_cli_and_search_and_categories():
    entry = registry.get_cli("demoapp")
    assert entry is not None and entry["entry_point"] == "cli-it-demoapp"
    assert registry.get_cli("no-such-cli") is None
    assert any(e["name"] == "demoapp" for e in registry.search_clis("exemplar"))
    assert "demo" in registry.list_categories()


def test_cache_envelope_fresh_and_stale(tmp_path):
    cache_file = tmp_path / "c.json"
    payload = {"clis": [{"name": "cached"}]}

    cache_file.write_text(json.dumps({"_cached_at": time.time(), "data": payload}))
    assert registry._fetch_json("http://invalid.invalid/x.json", cache_file) == payload

    # stale cache still wins over a dead network
    cache_file.write_text(json.dumps({"_cached_at": 1.0, "data": payload}))
    assert registry._fetch_json("http://invalid.invalid/x.json", cache_file) == payload


def test_fetch_json_raises_without_any_source(tmp_path):
    with pytest.raises(registry.RegistryError):
        registry._fetch_json("http://invalid.invalid/x.json", tmp_path / "none.json")


# --- matrix ------------------------------------------------------------------

SYNTHETIC_MATRIX = {
    "name": "synthetic",
    "capabilities": [
        {
            "id": "cap.ready",
            "intent": "always satisfiable",
            "providers": [
                {"kind": "native", "name": "python3", "requires": {"binary": ["python3"]}}
            ],
        },
        {
            "id": "cap.gap",
            "intent": "never satisfiable",
            "providers": [
                {
                    "kind": "public-cli",
                    "name": "ghost",
                    "requires": {"binary": ["definitely-not-a-binary-xyz"]},
                    "install_hint": "brew install ghost",
                },
                {
                    "kind": "api",
                    "name": "ghost-api",
                    "requires": {"env": ["CLI_IT_TEST_GHOST_KEY"]},
                    "offline": False,
                },
            ],
        },
    ],
    "recipes": [{"name": "only-ready", "capabilities": ["cap.ready"]}],
}


def test_check_provider_requirements(monkeypatch):
    ok = matrix.check_provider_requirements(
        {"requires": {"binary": ["python3"], "package": ["json"]}}
    )
    assert ok["ok"]

    monkeypatch.delenv("CLI_IT_TEST_MISSING_ENV", raising=False)
    bad = matrix.check_provider_requirements(
        {
            "requires": {
                "binary": ["definitely-not-a-binary-xyz"],
                "package": ["definitely_not_a_module_xyz"],
                "env": ["CLI_IT_TEST_MISSING_ENV"],
            }
        }
    )
    assert not bad["ok"]
    assert bad["missing"]["binary"] == ["definitely-not-a-binary-xyz"]
    assert bad["missing"]["package"] == ["definitely_not_a_module_xyz"]
    assert bad["missing"]["env"] == ["CLI_IT_TEST_MISSING_ENV"]

    assert matrix.check_provider_requirements({"requires": None})["ok"]


def test_preflight_matrix_reports_gaps(monkeypatch):
    monkeypatch.delenv("CLI_IT_TEST_GHOST_KEY", raising=False)
    report = matrix.preflight_matrix(SYNTHETIC_MATRIX)
    assert not report["ok"]
    assert report["gaps"] == ["cap.gap"]
    ready = {c["capability"]: c["ready"] for c in report["capabilities"]}
    assert ready == {"cap.ready": True, "cap.gap": False}


def test_preflight_offline_skips_network_providers():
    report = matrix.preflight_matrix(
        SYNTHETIC_MATRIX, capability_id="cap.gap", offline=True
    )
    skipped = [p for p in report["capabilities"][0]["providers"] if p.get("skipped")]
    assert [p["name"] for p in skipped] == ["ghost-api"]


def test_preflight_unknown_capability_raises():
    with pytest.raises(KeyError):
        matrix.preflight_matrix(SYNTHETIC_MATRIX, capability_id="nope")


def test_resolve_install_scope_recipe_and_only():
    full = matrix.resolve_install_scope(SYNTHETIC_MATRIX)
    assert [p["name"] for p in full] == ["ghost"]  # only installable kinds

    scoped = matrix.resolve_install_scope(SYNTHETIC_MATRIX, recipe="only-ready")
    assert scoped == []

    assert matrix.resolve_install_scope(SYNTHETIC_MATRIX, only=["nothing"]) == []
    with pytest.raises(KeyError):
        matrix.resolve_install_scope(SYNTHETIC_MATRIX, recipe="missing")


def test_search_capabilities_from_local_registry():
    hits = matrix.search_capabilities("create project")
    assert any(h["id"] == "project.scaffold" for h in hits)
    assert all("_matrix" in h for h in hits)


def test_provider_install_hint_for_harness():
    hint = matrix.provider_install_hint({"kind": "harness-cli", "name": "demoapp"})
    assert hint == "cli-it install demoapp"


# --- installer ---------------------------------------------------------------


def test_build_install_command_pip_normalized(monkeypatch):
    monkeypatch.setattr(installer.shutil, "which", lambda name: None)
    cmd = installer.build_install_command(
        {"name": "x", "install_cmd": "pip install some-pkg"}
    )
    assert cmd.endswith("-m pip install some-pkg")
    assert "pip install some-pkg" in cmd


def test_build_install_command_npm_and_generic():
    npm = installer.build_install_command(
        {"name": "m", "package_manager": "npm", "npm_package": "@scope/m", "install_cmd": ""}
    )
    assert npm == "npm install -g @scope/m"
    generic = installer.build_install_command(
        {"name": "b", "package_manager": "brew", "install_cmd": "brew install b"}
    )
    assert generic == "brew install b"
    with pytest.raises(installer.InstallError):
        installer.build_install_command({"name": "empty", "install_cmd": ""})


def test_install_cli_dry_run_and_missing():
    result = installer.install_cli("demoapp", dry_run=True)
    assert result["dry_run"] and "demoapp" in result["command"]
    with pytest.raises(installer.InstallError):
        installer.install_cli("no-such-cli", dry_run=True)


def test_plan_and_install_matrix_dry_run(monkeypatch):
    monkeypatch.delenv("CLI_IT_TEST_GHOST_KEY", raising=False)
    plan = installer.plan_matrix_install(SYNTHETIC_MATRIX)
    assert [s["name"] for s in plan] == ["ghost"]
    assert plan[0]["action"] == "run"
    assert plan[0]["command"] == "brew install ghost"

    summary = installer.install_matrix(SYNTHETIC_MATRIX, dry_run=True)
    assert summary["ok"] and summary["dry_run"]
    assert summary["installed"][0]["dry_run"]
    assert not installer.MATRIX_STATE_FILE.exists()  # dry runs never write state


def test_install_matrix_records_state_and_resume(monkeypatch):
    calls = []

    class FakeResult:
        returncode = 0
        stdout = stderr = ""

    monkeypatch.setattr(
        installer,
        "_run_registry_command",
        lambda cmd: calls.append(cmd) or FakeResult(),
    )
    summary = installer.install_matrix(SYNTHETIC_MATRIX)
    assert summary["ok"] and calls == ["brew install ghost"]
    state = json.loads(installer.MATRIX_STATE_FILE.read_text())
    assert state["synthetic"]["completed"] == ["ghost"]

    calls.clear()
    resumed = installer.install_matrix(SYNTHETIC_MATRIX, resume=True)
    assert calls == [] and "ghost" in resumed["skipped"]


def test_doctor_matrix_remedies(monkeypatch):
    monkeypatch.delenv("CLI_IT_TEST_GHOST_KEY", raising=False)
    report = installer.doctor_matrix(SYNTHETIC_MATRIX)
    assert not report["ok"] and report["gaps"] == ["cap.gap"]
    assert any(r["hint"] == "brew install ghost" for r in report["remedies"])


# --- preview consumer --------------------------------------------------------


def _write_bundle(root):
    bundle = root / "demoapp" / "render"
    (bundle / "artifacts").mkdir(parents=True)
    (bundle / "artifacts" / "out.txt").write_text("rendered")
    (bundle / "manifest.json").write_text(
        json.dumps(
            {
                "protocol": "preview-bundle/v1",
                "software": "demoapp",
                "recipe": "render",
                "fingerprint": "sha256:abc",
                "created_at": "2026-07-19T00:00:00",
            }
        )
    )
    (bundle / "summary.json").write_text(json.dumps({"status": "ok", "artifacts": 1}))
    return bundle


def test_inspect_and_render_bundle(tmp_path):
    bundle = _write_bundle(tmp_path)
    info = preview.inspect_bundle(str(bundle))
    assert info["protocol"] == "preview-bundle/v1"
    assert info["artifacts"] == [{"path": "artifacts/out.txt", "bytes": 8}]

    # manifest path and directory path both resolve
    assert preview.resolve_bundle(str(bundle / "manifest.json")) == bundle.resolve()

    page = preview.render_html(str(bundle))
    assert "sha256:abc" in page and "artifacts/out.txt" in page


def test_inspect_bundle_rejects_non_bundle(tmp_path):
    with pytest.raises(preview.PreviewError):
        preview.inspect_bundle(str(tmp_path))


def test_inspect_session_and_normalize(tmp_path):
    session = tmp_path / "live"
    session.mkdir()
    (session / "session.json").write_text(
        json.dumps(
            {"protocol": "preview-trajectory/v1", "software": "demoapp", "status": "running"}
        )
    )
    (session / "trajectory.json").write_text(
        json.dumps({"events": [{"type": "step", "message": "opened", "extra": 1}, "plain"]})
    )
    info = preview.inspect_session(str(session))
    assert info["event_count"] == 2
    assert info["events"][0]["data"] == {"extra": 1}
    assert info["events"][1]["message"] == "plain"
    page = preview.render_live_html(str(session))
    assert "http-equiv=\"refresh\"" in page


# --- analytics ---------------------------------------------------------------


def test_analytics_disabled_is_noop(monkeypatch):
    monkeypatch.setenv("CLI_HUB_NO_ANALYTICS", "true")

    def boom(*a, **k):  # would fail the test if any network call were attempted
        raise AssertionError("analytics attempted a network call while disabled")

    monkeypatch.setattr(analytics, "_post", boom)
    analytics.capture("install", {"cli": "demoapp"})
    assert analytics.analytics_disabled()


def test_analytics_noop_without_token(monkeypatch):
    monkeypatch.delenv("CLI_HUB_NO_ANALYTICS", raising=False)
    monkeypatch.delenv("CLI_HUB_POSTHOG_PROJECT_TOKEN", raising=False)
    monkeypatch.setattr(
        analytics,
        "_post",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no token, no post")),
    )
    analytics.capture("visit")  # placeholder token is empty ⇒ silently no-op


# --- click surface -----------------------------------------------------------


def test_cli_root_shows_help_and_version():
    runner = CliRunner()
    root = runner.invoke(cli.main, [])
    assert root.exit_code == 0 and "install" in root.output
    version = runner.invoke(cli.main, ["--version"])
    assert __version__ in version.output


def test_cli_list_search_info_json():
    runner = CliRunner()
    listed = runner.invoke(cli.main, ["list", "--json"])
    assert listed.exit_code == 0
    names = [e["name"] for e in json.loads(listed.output)]
    assert "demoapp" in names

    searched = runner.invoke(cli.main, ["search", "demo", "--json"])
    assert searched.exit_code == 0 and json.loads(searched.output)

    info_res = runner.invoke(cli.main, ["info", "demoapp"])
    assert info_res.exit_code == 0
    assert json.loads(info_res.output)["entry_point"] == "cli-it-demoapp"

    missing = runner.invoke(cli.main, ["info", "no-such-cli"])
    assert missing.exit_code == 1


def test_cli_can_and_matrix_family():
    runner = CliRunner()
    can = runner.invoke(cli.main, ["can", "create project", "--json"])
    assert can.exit_code == 0
    assert any(r["capability"] == "project.scaffold" for r in json.loads(can.output))

    mlist = runner.invoke(cli.main, ["matrix", "list", "--json"])
    assert mlist.exit_code == 0
    assert any(m["name"] == "image-design" for m in json.loads(mlist.output))

    preflight = runner.invoke(cli.main, ["matrix", "preflight", "image-design", "--json"])
    assert preflight.exit_code in (0, 3)  # 3 = gaps, still a valid report
    report = json.loads(preflight.output)
    assert report["matrix"] == "image-design" and report["capabilities"]

    dry = runner.invoke(cli.main, ["matrix", "install", "image-design", "--dry-run", "--json"])
    assert dry.exit_code in (0, 3)
    assert json.loads(dry.output)["dry_run"]

    unknown = runner.invoke(cli.main, ["matrix", "preflight", "nope"])
    assert unknown.exit_code == 1

    recipes = runner.invoke(cli.main, ["matrix", "recipes", "--json"])
    assert recipes.exit_code == 0
    assert any(r["name"] == "diagram-to-png" for r in json.loads(recipes.output))
