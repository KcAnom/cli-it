"""Tests for skill_generator.py and preview_bundle.py (plugin helpers)."""

import json
import shutil
from pathlib import Path

import pytest

import preview_bundle
import skill_generator

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEMOAPP_HARNESS = REPO_ROOT / "demoapp" / "agent-harness"


@pytest.fixture
def harness_copy(tmp_path):
    """Work on a copy so tests never mutate the real demoapp harness."""
    target = tmp_path / "demoapp" / "agent-harness"
    shutil.copytree(DEMOAPP_HARNESS, target, ignore=shutil.ignore_patterns("__pycache__"))
    return target


def test_extract_cli_metadata_from_demoapp(harness_copy):
    meta = skill_generator.extract_cli_metadata(harness_copy)
    assert meta.software == "demoapp"
    assert meta.skill_name == "cli-it-demoapp"
    assert meta.entry_point == "cli-it-demoapp"
    assert meta.version == "0.1.0"
    assert "harness" in meta.description.lower()

    groups = {g.name: [c.name for c in g.commands] for g in meta.groups}
    assert set(groups["project"]) == {"new", "open", "info", "save"}
    assert set(groups["session"]) == {"status", "undo", "redo"}
    assert "run" in groups["export"]
    assert "capture" in groups["preview"]


def test_generate_skill_md_content(harness_copy):
    meta = skill_generator.extract_cli_metadata(harness_copy)
    content = skill_generator.generate_skill_md(meta)
    assert content.startswith("---\nname: cli-it-demoapp")
    assert "version: 0.1.0" in content
    assert "| `project` | `new` |" in content
    assert "cli-it-demoapp --help" in content
    assert "{{" not in content  # every placeholder substituted


def test_generate_skill_file_dual_write(harness_copy, tmp_path):
    fake_root = tmp_path / "repo"
    (fake_root / "skills").mkdir(parents=True)
    (fake_root / "registry.json").write_text("{}")

    written = skill_generator.generate_skill_file(harness_copy, repo_root=fake_root)
    canonical = fake_root / "skills" / "cli-it-demoapp" / "SKILL.md"
    packaged = harness_copy / "cli_it" / "demoapp" / "skills" / "SKILL.md"
    assert set(written) == {canonical, packaged}
    assert canonical.read_text() == packaged.read_text()


def test_parser_handles_synthetic_module(tmp_path):
    harness = tmp_path / "toy" / "agent-harness"
    package = harness / "cli_it" / "toy"
    package.mkdir(parents=True)
    (package / "toy_cli.py").write_text(
        '''
import click

@click.group(invoke_without_command=True)
def cli():
    """Toy root."""

@cli.group()
def scene():
    """Scene ops."""

@scene.command("render")
def scene_render():
    """Render the scene."""

@cli.command()
def status_cmd():
    """Show status."""
'''
    )
    (harness / "setup.py").write_text('setup(version="2.3.4")')
    meta = skill_generator.extract_cli_metadata(harness)
    assert meta.version == "2.3.4"
    groups = {g.name: {c.name: c.help for c in g.commands} for g in meta.groups}
    assert groups["scene"] == {"render": "Render the scene."}
    assert groups["root"] == {"status": "Show status."}


# --- preview_bundle producer -------------------------------------------------


def test_bundle_prepare_finalize_round_trip(tmp_path):
    bundle = preview_bundle.prepare_bundle(
        "demoapp", "render", inputs={"seed": 1}, root_dir=tmp_path
    )
    assert bundle == tmp_path / "demoapp" / "render"
    (bundle / "artifacts" / "frame.txt").write_text("pixels")

    manifest = preview_bundle.finalize_bundle(bundle, summary={"frames": 1})
    assert manifest["protocol"] == "preview-bundle/v1"
    assert manifest["status"] == "complete" and manifest["artifact_count"] == 1

    summary = json.loads((bundle / "summary.json").read_text())
    assert summary["frames"] == 1
    assert summary["artifacts"][0]["path"] == "artifacts/frame.txt"


def test_fingerprint_stability():
    a = preview_bundle.fingerprint({"b": 2, "a": 1})
    b = preview_bundle.fingerprint({"a": 1, "b": 2})
    assert a == b and a.startswith("sha256:")
    assert a != preview_bundle.fingerprint({"a": 1, "b": 3})


def test_bundle_root_project_local(tmp_path):
    project = tmp_path / "work" / "proj.json"
    root = preview_bundle.bundle_root("demoapp", "render", project_path=project)
    assert root == tmp_path / "work" / ".cli-it" / "previews" / "demoapp" / "render"


def test_live_trajectory_lifecycle(tmp_path):
    session = preview_bundle.start_live_session(
        "demoapp", tmp_path / "live", meta={"recipe": "render"}
    )
    assert preview_bundle.append_live_trajectory(session, {"type": "step", "message": "a"}) == 0
    assert preview_bundle.append_live_trajectory(session, {"type": "render", "message": "b"}) == 1

    events = preview_bundle.load_live_trajectory(session)
    assert [e["seq"] for e in events] == [0, 1]

    summary = preview_bundle.summarize_trajectory(session)
    assert summary["events"] == 2 and summary["by_type"] == {"step": 1, "render": 1}

    preview_bundle.stop_live_session(session)
    doc = json.loads((session / "session.json").read_text())
    assert doc["status"] == "stopped" and doc["protocol"] == "preview-trajectory/v1"
