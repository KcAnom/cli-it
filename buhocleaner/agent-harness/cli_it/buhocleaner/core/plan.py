"""BuhoCleaner cleanup-plan data layer.

BuhoCleaner has no document format of its own, so the harness owns a
"cleanup plan" JSON project: which scan categories are enabled, per-category
root overrides, the large-file threshold, and the last read-only scan
snapshot. The plan never holds anything destructive — it is a scan/launch
configuration, not a deletion list.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

PLAN_FORMAT = "buhocleaner-plan/v1"


class PlanError(RuntimeError):
    pass


# name -> (BuhoCleaner defaults toggle key or None, default probe root,
#          glob restricted to the root's top level or None = whole tree)
CATEGORIES: dict[str, dict] = {
    "user-caches": {
        "defaults_key": "userCacheFilesSelected",
        "root": "~/Library/Caches",
        "glob": None,
    },
    "system-caches": {
        "defaults_key": "systemCacheFilesSelected",
        "root": "/Library/Caches",
        "glob": None,
    },
    "system-logs": {
        "defaults_key": "systemLogFilesSelected",
        "root": "~/Library/Logs",
        "glob": None,
    },
    "trash": {
        "defaults_key": "trashCanSelected",
        "root": "~/.Trash",
        "glob": None,
    },
    "screenshots": {
        "defaults_key": "screenshotFilesSelected",
        "root": "~/Desktop",
        "glob": ["Screenshot*", "Screen Shot*"],
    },
    "dmg-installers": {
        "defaults_key": "unusedDMGFilesSelected",
        "root": "~/Downloads",
        "glob": ["*.dmg"],
    },
    "mail-downloads": {
        "defaults_key": "mailDownloadsFilesSelected",
        "root": "~/Library/Containers/com.apple.mail/Data/Library/Mail Downloads",
        "glob": None,
    },
    "large-files": {
        "defaults_key": None,  # threshold-driven; Buho key `minimumFileSize` has app-private units
        "root": "~/Downloads",
        "glob": None,
    },
}

DEFAULT_THRESHOLD_MB = 100


@dataclass
class Plan:
    name: str
    created_at: str
    categories: dict = field(default_factory=dict)  # name -> {enabled, root}
    threshold_mb: int = DEFAULT_THRESHOLD_MB
    last_scan: dict | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "format": PLAN_FORMAT,
            "name": self.name,
            "created_at": self.created_at,
            "categories": self.categories,
            "threshold_mb": self.threshold_mb,
            "last_scan": self.last_scan,
            "metadata": self.metadata,
        }

    def category(self, name: str) -> dict:
        if name not in CATEGORIES:
            raise PlanError(
                f"unknown category {name!r} (known: {', '.join(sorted(CATEGORIES))})"
            )
        return self.categories.setdefault(name, {"enabled": True, "root": None})

    def enabled_categories(self) -> list[str]:
        return [
            name
            for name in CATEGORIES
            if self.categories.get(name, {}).get("enabled", True)
        ]

    def root_for(self, name: str) -> Path:
        override = self.categories.get(name, {}).get("root")
        root = override or CATEGORIES[name]["root"]
        return Path(root).expanduser()


def new_plan(name: str) -> Plan:
    plan = Plan(name=name, created_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
    plan.categories = {name_: {"enabled": True, "root": None} for name_ in CATEGORIES}
    return plan


def load_plan(path: str | Path) -> Plan:
    path = Path(path)
    if not path.is_file():
        raise PlanError(f"plan file not found: {path}")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise PlanError(f"invalid plan JSON in {path}: {exc}") from exc
    if doc.get("format") != PLAN_FORMAT:
        raise PlanError(
            f"{path} is not a buhocleaner plan (format={doc.get('format')!r})"
        )
    return Plan(
        name=doc.get("name", path.stem),
        created_at=doc.get("created_at", ""),
        categories=dict(doc.get("categories", {})),
        threshold_mb=int(doc.get("threshold_mb", DEFAULT_THRESHOLD_MB)),
        last_scan=doc.get("last_scan"),
        metadata=dict(doc.get("metadata", {})),
    )


def save_plan(plan: Plan, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")
    return path


def plan_info(plan: Plan, path: Path) -> dict:
    return {
        "path": str(path),
        "format": PLAN_FORMAT,
        "name": plan.name,
        "created_at": plan.created_at,
        "categories_enabled": plan.enabled_categories(),
        "threshold_mb": plan.threshold_mb,
        "last_scan_at": (plan.last_scan or {}).get("scanned_at"),
        "metadata": plan.metadata,
    }


# --- undoable actions --------------------------------------------------------


def apply_action(plan: Plan, action: dict, invert: bool = False) -> Plan:
    """Apply (or invert) a journaled plan mutation in memory.

    Every op carries `before`/`after`, so inversion is just swapping them.
    Prefs ops (`prefs.*`) touch the live app domain and are handled by the
    CLI via the backend, not here.
    """
    op = action.get("op")
    before, after = action.get("before"), action.get("after")
    if invert:
        before, after = after, before
    if op == "category.enabled":
        plan.category(action["category"])["enabled"] = bool(after)
    elif op == "category.root":
        plan.category(action["category"])["root"] = after
    elif op == "plan.threshold":
        plan.threshold_mb = int(after)
    elif op == "scan.run":
        plan.last_scan = after
    elif op == "clean.result":
        # Records the GUI clean outcome in metadata. Undo restores only the
        # recorded value — deleted files are gone regardless.
        plan.metadata["last_clean"] = after
    else:
        raise PlanError(f"unknown action op: {op!r}")
    return plan
