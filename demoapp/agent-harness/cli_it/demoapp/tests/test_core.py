"""DemoApp unit tests — no engine subprocess needed (pure data + Click layer)."""

import json
import threading

import pytest
from click.testing import CliRunner

from cli_it.demoapp.core import project as _project
from cli_it.demoapp.core import session as _session
from cli_it.demoapp.demoapp_cli import cli


# --- project data layer ------------------------------------------------------


def test_project_round_trip(tmp_path):
    proj = _project.new_project("roundtrip")
    proj.items.append({"id": 1, "name": "a", "kind": "note"})
    path = _project.save_project(proj, tmp_path / "p.json")
    loaded = _project.load_project(path)
    assert loaded.name == "roundtrip"
    assert loaded.items == [{"id": 1, "name": "a", "kind": "note"}]
    assert json.loads(path.read_text())["format"] == "demoapp/v1"


def test_project_load_errors(tmp_path):
    with pytest.raises(_project.ProjectError):
        _project.load_project(tmp_path / "missing.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(_project.ProjectError):
        _project.load_project(bad)
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"format": "other/v9"}))
    with pytest.raises(_project.ProjectError):
        _project.load_project(wrong)


def test_apply_action_and_inversion():
    proj = _project.new_project("actions")
    action = {"op": "item.add", "item": {"id": 1, "name": "x", "kind": "note"}}
    _project.apply_action(proj, action)
    _project.apply_action(proj, action)  # idempotent by id
    assert len(proj.items) == 1
    _project.apply_action(proj, action, invert=True)
    assert proj.items == []
    with pytest.raises(_project.ProjectError):
        _project.apply_action(proj, {"op": "bogus"})


def test_next_item_id():
    proj = _project.new_project("ids")
    assert proj.next_item_id() == 1
    proj.items = [{"id": 7}]
    assert proj.next_item_id() == 8


# --- session journal + locking ----------------------------------------------


def test_record_and_status(tmp_path):
    project_path = tmp_path / "p.json"
    _session.record_action(project_path, {"op": "item.add", "item": {"id": 1}})
    status = _session.session_status(project_path)
    assert status["undo_depth"] == 1 and status["redo_depth"] == 0
    session_file = _session.session_path_for(project_path)
    assert json.loads(session_file.read_text())["format"] == "demoapp-session/v1"


def test_undo_redo_stack_movement(tmp_path):
    project_path = tmp_path / "p.json"
    first = {"op": "item.add", "item": {"id": 1}}
    second = {"op": "item.add", "item": {"id": 2}}
    _session.record_action(project_path, first)
    _session.record_action(project_path, second)

    assert _session.pop_undo(project_path) == second
    status = _session.session_status(project_path)
    assert status["undo_depth"] == 1 and status["redo_depth"] == 1

    assert _session.pop_redo(project_path) == second
    assert _session.session_status(project_path)["redo_depth"] == 0

    # a new mutation clears redo
    _session.pop_undo(project_path)
    _session.record_action(project_path, {"op": "item.add", "item": {"id": 3}})
    assert _session.session_status(project_path)["redo_depth"] == 0


def test_pop_empty_returns_none(tmp_path):
    project_path = tmp_path / "p.json"
    assert _session.pop_undo(project_path) is None
    assert _session.pop_redo(project_path) is None


def test_concurrent_journal_writes_stay_consistent(tmp_path):
    project_path = tmp_path / "p.json"

    def worker(n):
        _session.record_action(project_path, {"op": "item.add", "item": {"id": n}})

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    state = _session.load_session(project_path)
    assert len(state["undo"]) == 12  # no lost updates, file never torn


# --- Click surface -----------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


def _new_project(runner, tmp_path, name="demo"):
    path = tmp_path / f"{name}.json"
    result = runner.invoke(cli, ["project", "new", "-n", name, "-o", str(path)])
    assert result.exit_code == 0, result.output
    return path


def test_cli_project_new_info_json(runner, tmp_path):
    path = _new_project(runner, tmp_path)
    info = runner.invoke(cli, ["--json", "project", "info", "-p", str(path)])
    assert info.exit_code == 0
    doc = json.loads(info.output)
    assert doc["name"] == "demo" and doc["items"] == 0

    again = runner.invoke(cli, ["project", "new", "-n", "x", "-o", str(path)])
    assert again.exit_code == 1  # refuses overwrite


def test_cli_open_and_save(runner, tmp_path):
    path = _new_project(runner, tmp_path)
    opened = runner.invoke(cli, ["--json", "project", "open", "-p", str(path)])
    assert opened.exit_code == 0
    assert json.loads(opened.output)["session"]["undo_depth"] == 0
    saved = runner.invoke(cli, ["project", "save", "-p", str(path)])
    assert saved.exit_code == 0


def test_cli_item_mutations_and_undo_redo(runner, tmp_path):
    path = _new_project(runner, tmp_path)
    for name in ("alpha", "beta"):
        added = runner.invoke(cli, ["item", "add", "-p", str(path), "-n", name])
        assert added.exit_code == 0, added.output

    listed = runner.invoke(cli, ["--json", "item", "list", "-p", str(path)])
    items = json.loads(listed.output)["items"]
    assert [i["name"] for i in items] == ["alpha", "beta"]

    undone = runner.invoke(cli, ["--json", "session", "undo", "-p", str(path)])
    assert undone.exit_code == 0
    assert json.loads(undone.output)["items"] == 1

    redone = runner.invoke(cli, ["--json", "session", "redo", "-p", str(path)])
    assert json.loads(redone.output)["items"] == 2

    removed = runner.invoke(cli, ["item", "remove", "-p", str(path), "-i", "1"])
    assert removed.exit_code == 0
    status = runner.invoke(cli, ["--json", "session", "status", "-p", str(path)])
    assert json.loads(status.output)["undo_depth"] == 3  # add, redo(add), remove


def test_cli_error_paths(runner, tmp_path):
    path = _new_project(runner, tmp_path)
    missing_item = runner.invoke(cli, ["item", "remove", "-p", str(path), "-i", "99"])
    assert missing_item.exit_code == 1 and "no item" in missing_item.output

    empty_undo = runner.invoke(cli, ["session", "undo", "-p", str(tmp_path / 'p2.json')])
    assert empty_undo.exit_code == 1

    usage = runner.invoke(cli, ["item", "add", "-p", str(path)])  # missing -n
    assert usage.exit_code == 2


def test_cli_backend_probe_json(runner):
    result = runner.invoke(cli, ["--json", "backend"])
    assert result.exit_code == 0
    doc = json.loads(result.output)
    assert doc["available"] is True and doc["engine"]
