"""Tests for matrix skill resolution/rendering across distribution modes."""

import json

import pytest

from cli_it_hub import installer, matrix, matrix_skill, registry


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("CLI_HUB_NO_ANALYTICS", "1")
    monkeypatch.setattr(matrix_skill, "RENDER_ROOT", tmp_path / "rendered")
    monkeypatch.setattr(installer, "INSTALLED_FILE", tmp_path / "installed.json")


def _image_design():
    item = matrix.get_matrix("image-design")
    assert item is not None
    return item


def test_source_prefers_repo_checkout():
    kind, location = matrix_skill.find_matrix_skill_source("image-design")
    assert kind == "checkout"
    assert (location / "SKILL.md").is_file()


def test_source_falls_back_to_bundled_then_url(tmp_path, monkeypatch):
    monkeypatch.setattr(matrix_skill, "_checkout_dir", lambda name: None)

    bundled = tmp_path / "bundled" / "some-matrix"
    bundled.mkdir(parents=True)
    (bundled / "SKILL.md").write_text("# bundled skill")
    monkeypatch.setattr(matrix_skill, "_bundled_dir", lambda name: bundled)
    assert matrix_skill.find_matrix_skill_source("some-matrix")[0] == "bundled"
    assert matrix_skill.load_matrix_skill_md("some-matrix") == "# bundled skill"

    monkeypatch.setattr(matrix_skill, "_bundled_dir", lambda name: tmp_path / "missing")
    kind, location = matrix_skill.find_matrix_skill_source("some-matrix")
    assert kind == "url"
    assert str(location).endswith("/matrix/some-matrix/SKILL.md")


def test_render_injects_tooling_between_markers():
    path = matrix_skill.render_matrix_skill_file(_image_design(), installed={"demoapp": {}})
    content = path.read_text(encoding="utf-8")
    assert content.count(matrix_skill.MARKER_START) == 1
    assert content.count(matrix_skill.MARKER_END) == 1
    assert "Installed tooling on this machine" in content
    assert "demoapp" in content

    # re-rendering replaces the section instead of appending a second block
    again = matrix_skill.render_matrix_skill_file(_image_design()).read_text()
    assert again.count(matrix_skill.MARKER_START) == 1


def test_render_copies_reference_assets():
    item = matrix.get_matrix("video-creation")
    assert item is not None
    path = matrix_skill.render_matrix_skill_file(item)
    target_dir = path.parent
    assert (target_dir / "references").is_dir()
    assert any(target_dir.joinpath("references").iterdir())
    assert (target_dir / "scripts" / "video_doctor.py").is_file()


def test_vendoring_layout_matches_package_data():
    """Every matrix in the registry must have a skill pack that setup.py's
    package_data globs (`_matrix_data/*/SKILL.md`) would capture."""
    root = registry.find_repo_root()
    assert root is not None
    doc = json.loads((root / "matrix_registry.json").read_text())
    for item in doc["matrices"]:
        assert (root / "cli-it-matrix" / item["name"] / "SKILL.md").is_file(), item["name"]
