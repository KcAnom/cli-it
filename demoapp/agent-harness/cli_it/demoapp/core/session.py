"""DemoApp session state: undo/redo journal with exclusive file locking.

The lock pattern follows cli-it-plugin/guides/session-locking.md: open `r+`
(create first), take an exclusive lock on the handle, read, mutate, truncate,
write, release. Portable across POSIX (fcntl) and Windows (msvcrt).
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

SESSION_FORMAT = "demoapp-session/v1"

try:
    import fcntl

    def _lock(fh):
        fcntl.flock(fh, fcntl.LOCK_EX)

    def _unlock(fh):
        fcntl.flock(fh, fcntl.LOCK_UN)

except ImportError:  # Windows
    import msvcrt

    def _lock(fh):
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)

    def _unlock(fh):
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)


def session_path_for(project_path: str | Path) -> Path:
    project_path = Path(project_path)
    return project_path.with_name(project_path.name + ".session.json")


def _default_session(project_path: Path) -> dict:
    return {
        "format": SESSION_FORMAT,
        "project": str(project_path),
        "undo": [],
        "redo": [],
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


@contextmanager
def _locked_handle(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    with open(path, "r+", encoding="utf-8") as fh:
        _lock(fh)
        try:
            yield fh
        finally:
            _unlock(fh)


def update_session(project_path: str | Path, mutate: Callable[[dict], dict]) -> dict:
    """Atomically read-modify-write the session under an exclusive lock."""
    project_path = Path(project_path)
    path = session_path_for(project_path)
    with _locked_handle(path) as fh:
        raw = fh.read()
        try:
            state = json.loads(raw) if raw.strip() else _default_session(project_path)
        except ValueError:
            state = _default_session(project_path)
        state = mutate(state)
        state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        fh.seek(0)
        fh.truncate()
        fh.write(json.dumps(state, indent=2))
        fh.flush()
        os.fsync(fh.fileno())
    return state


def load_session(project_path: str | Path) -> dict:
    path = session_path_for(project_path)
    if not path.is_file():
        return _default_session(Path(project_path))
    try:
        raw = path.read_text(encoding="utf-8")
        return json.loads(raw) if raw.strip() else _default_session(Path(project_path))
    except ValueError:
        return _default_session(Path(project_path))


def record_action(project_path: str | Path, action: dict) -> dict:
    """Journal a new mutation: push onto undo, clear redo."""

    def mutate(state: dict) -> dict:
        state.setdefault("undo", []).append(action)
        state["redo"] = []
        return state

    return update_session(project_path, mutate)


def pop_undo(project_path: str | Path) -> dict | None:
    """Move the newest undo entry to the redo stack and return it."""
    popped: dict = {}

    def mutate(state: dict) -> dict:
        if state.get("undo"):
            action = state["undo"].pop()
            state.setdefault("redo", []).append(action)
            popped["action"] = action
        return state

    update_session(project_path, mutate)
    return popped.get("action")


def pop_redo(project_path: str | Path) -> dict | None:
    """Move the newest redo entry back to the undo stack and return it."""
    popped: dict = {}

    def mutate(state: dict) -> dict:
        if state.get("redo"):
            action = state["redo"].pop()
            state.setdefault("undo", []).append(action)
            popped["action"] = action
        return state

    update_session(project_path, mutate)
    return popped.get("action")


def session_status(project_path: str | Path) -> dict:
    state = load_session(project_path)
    return {
        "project": state.get("project"),
        "session_file": str(session_path_for(project_path)),
        "undo_depth": len(state.get("undo", [])),
        "redo_depth": len(state.get("redo", [])),
        "updated_at": state.get("updated_at"),
    }
