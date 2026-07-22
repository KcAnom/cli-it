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


def test_harness_path_accepts_str_relative_dotdot_and_symlinked_ancestor(
    harness_copy, tmp_path, monkeypatch
):
    assert skill_generator.extract_cli_metadata(str(harness_copy)).software == "demoapp"

    monkeypatch.chdir(tmp_path)
    relative = Path("demoapp") / "ignored" / ".." / "agent-harness"
    assert skill_generator.extract_cli_metadata(relative).software == "demoapp"

    link = tmp_path / "linked-project"
    _symlink_or_skip(link, harness_copy.parent)
    resolved = skill_generator.resolve_harness_path(link / "agent-harness")
    assert resolved == harness_copy.resolve()


def test_harness_path_rejects_project_root_and_wrong_basename(harness_copy, tmp_path):
    with pytest.raises(ValueError, match="basename must be 'agent-harness'"):
        skill_generator.extract_cli_metadata(harness_copy.parent)

    wrong = tmp_path / "wrong-name"
    shutil.copytree(harness_copy, wrong)
    with pytest.raises(ValueError, match="required form is"):
        skill_generator.extract_cli_metadata(wrong)


def test_named_but_incomplete_harness_preserves_structural_error(tmp_path):
    harness = tmp_path / "project" / "agent-harness"
    harness.mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="no cli_it"):
        skill_generator.extract_cli_metadata(harness)


def _symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")


def _file_symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"file symlinks unavailable: {exc}")


def _repo_with_sentinel(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    canonical = root / "skills" / "cli-it-demoapp" / "SKILL.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_bytes(b"canonical sentinel\n")
    (root / "registry.json").write_text("{}")
    return root, canonical


def test_invalid_generation_creates_no_fresh_outputs(harness_copy, tmp_path):
    wrong = tmp_path / "wrong-name"
    shutil.copytree(harness_copy, wrong)
    shutil.rmtree(wrong / "cli_it" / "demoapp" / "skills")
    root = tmp_path / "fresh-repo"
    (root / "skills").mkdir(parents=True)

    with pytest.raises(ValueError, match="basename"):
        skill_generator.generate_skill_file(wrong, repo_root=root)
    assert not (root / "skills" / "cli-it-demoapp" / "SKILL.md").exists()
    assert not (wrong / "cli_it" / "demoapp" / "skills" / "SKILL.md").exists()


def test_top_level_harness_symlink_rejected_before_writes(harness_copy, tmp_path):
    project = tmp_path / "other-project"
    project.mkdir()
    linked_harness = project / "agent-harness"
    _symlink_or_skip(linked_harness, harness_copy)
    root, canonical = _repo_with_sentinel(tmp_path)
    packaged = harness_copy / "cli_it" / "demoapp" / "skills" / "SKILL.md"
    before = packaged.read_bytes()

    with pytest.raises(ValueError, match="resolved path is not the direct"):
        skill_generator.generate_skill_file(linked_harness, repo_root=root)
    assert canonical.read_bytes() == b"canonical sentinel\n"
    assert packaged.read_bytes() == before


@pytest.mark.parametrize("escape", ["namespace", "package"])
def test_metadata_rejects_escaping_nested_symlink(harness_copy, tmp_path, escape):
    external = tmp_path / "external"
    if escape == "namespace":
        shutil.copytree(harness_copy / "cli_it", external)
        shutil.rmtree(harness_copy / "cli_it")
        _symlink_or_skip(harness_copy / "cli_it", external)
        match = "cli_it namespace escapes"
    else:
        source = harness_copy / "cli_it" / "demoapp"
        shutil.copytree(source, external)
        shutil.rmtree(source)
        _symlink_or_skip(source, external)
        match = "software package escapes"

    with pytest.raises(ValueError, match=match):
        skill_generator.extract_cli_metadata(harness_copy)


@pytest.mark.parametrize(
    ("relative_path", "match"),
    [
        (Path("cli_it/demoapp/demoapp_cli.py"), "CLI module escapes"),
        (Path("setup.py"), "setup.py metadata file escapes"),
        (Path("cli_it/demoapp/README.md"), "README metadata file escapes"),
    ],
)
def test_metadata_file_symlink_escape_rejected_before_writes(
    harness_copy, tmp_path, relative_path, match
):
    source = harness_copy / relative_path
    external = tmp_path / f"external-{source.name}"
    external.write_bytes(source.read_bytes())
    source.unlink()
    _file_symlink_or_skip(source, external)
    root, canonical = _repo_with_sentinel(tmp_path)
    packaged = harness_copy / "cli_it" / "demoapp" / "skills" / "SKILL.md"
    packaged_before = packaged.read_bytes()

    with pytest.raises(ValueError, match=match):
        skill_generator.generate_skill_file(harness_copy, repo_root=root)
    assert canonical.read_bytes() == b"canonical sentinel\n"
    assert packaged.read_bytes() == packaged_before


@pytest.mark.parametrize("invalid_kind", ["nonexistent", "missing_registry", "missing_skills"])
def test_invalid_explicit_repo_root_rejected_without_writes(
    harness_copy, tmp_path, invalid_kind
):
    root = tmp_path / f"repo-{invalid_kind}"
    canonical = root / "skills" / "cli-it-demoapp" / "SKILL.md"
    if invalid_kind != "nonexistent":
        root.mkdir()
    if invalid_kind == "missing_registry":
        canonical.parent.mkdir(parents=True)
        canonical.write_bytes(b"canonical sentinel\n")
    elif invalid_kind == "missing_skills":
        (root / "registry.json").write_text("{}")

    packaged = harness_copy / "cli_it" / "demoapp" / "skills" / "SKILL.md"
    packaged_before = packaged.read_bytes()
    with pytest.raises(ValueError, match="invalid CLI-It repository root"):
        skill_generator.generate_skill_file(harness_copy, repo_root=root)

    assert packaged.read_bytes() == packaged_before
    if invalid_kind == "missing_registry":
        assert canonical.read_bytes() == b"canonical sentinel\n"
    else:
        assert not canonical.exists()


def test_packaged_skills_escape_rejected_before_either_write(harness_copy, tmp_path):
    root, canonical = _repo_with_sentinel(tmp_path)
    skills = harness_copy / "cli_it" / "demoapp" / "skills"
    packaged_before = (skills / "SKILL.md").read_bytes()
    shutil.rmtree(skills)
    external = tmp_path / "external-skills"
    external.mkdir()
    external_file = external / "SKILL.md"
    external_file.write_bytes(packaged_before)
    _symlink_or_skip(skills, external)

    with pytest.raises(ValueError, match="packaged skill destination escapes"):
        skill_generator.generate_skill_file(harness_copy, repo_root=root)
    assert canonical.read_bytes() == b"canonical sentinel\n"
    assert external_file.read_bytes() == packaged_before


def test_canonical_skills_escape_rejected_before_either_write(harness_copy, tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "registry.json").write_text("{}")
    external = tmp_path / "external-skills"
    canonical = external / "cli-it-demoapp" / "SKILL.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_bytes(b"canonical sentinel\n")
    _symlink_or_skip(root / "skills", external)
    packaged = harness_copy / "cli_it" / "demoapp" / "skills" / "SKILL.md"
    packaged_before = packaged.read_bytes()

    with pytest.raises(ValueError, match="repository skills marker escapes"):
        skill_generator.generate_skill_file(harness_copy, repo_root=root)
    assert canonical.read_bytes() == b"canonical sentinel\n"
    assert packaged.read_bytes() == packaged_before


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
