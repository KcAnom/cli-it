"""DemoApp project data layer: the native project format is JSON on disk."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

PROJECT_FORMAT = "demoapp/v1"


class ProjectError(RuntimeError):
    pass


@dataclass
class Project:
    name: str
    created_at: str
    items: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        doc = asdict(self)
        doc["format"] = PROJECT_FORMAT
        return doc

    def next_item_id(self) -> int:
        return max((item.get("id", 0) for item in self.items), default=0) + 1


def new_project(name: str) -> Project:
    return Project(name=name, created_at=time.strftime("%Y-%m-%dT%H:%M:%S"))


def load_project(path: str | Path) -> Project:
    path = Path(path)
    if not path.is_file():
        raise ProjectError(f"project file not found: {path}")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ProjectError(f"invalid project JSON in {path}: {exc}") from exc
    if doc.get("format") != PROJECT_FORMAT:
        raise ProjectError(
            f"{path} is not a demoapp project (format={doc.get('format')!r})"
        )
    return Project(
        name=doc.get("name", path.stem),
        created_at=doc.get("created_at", ""),
        items=list(doc.get("items", [])),
        metadata=dict(doc.get("metadata", {})),
    )


def save_project(project: Project, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")
    return path


def project_info(project: Project, path: Path) -> dict:
    return {
        "path": str(path),
        "format": PROJECT_FORMAT,
        "name": project.name,
        "created_at": project.created_at,
        "items": len(project.items),
        "metadata": project.metadata,
    }


# --- undoable actions --------------------------------------------------------


def apply_action(project: Project, action: dict, invert: bool = False) -> Project:
    """Apply (or invert) a journal action to a project in memory.

    Supported ops: item.add, item.remove. Each action carries the full item so
    it is self-inverting.
    """
    op = action.get("op")
    item = action.get("item") or {}
    adding = (op == "item.add") != invert
    if op not in ("item.add", "item.remove"):
        raise ProjectError(f"unknown action op: {op!r}")
    if adding:
        if all(existing.get("id") != item.get("id") for existing in project.items):
            project.items.append(dict(item))
    else:
        project.items = [
            existing for existing in project.items if existing.get("id") != item.get("id")
        ]
    return project
