"""Preview bundle *producer* helpers for CLI-It harnesses.

Harness CLIs import this module (or copy it) to write preview bundles and live
trajectory sessions in the shared format that `cli-it previews` consumes. See
docs/PREVIEW_PROTOCOL.md for the contract. Producers render with the real
application; this module only handles bundle bookkeeping.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

PROTOCOL_VERSION = "preview-bundle/v1"
TRAJECTORY_PROTOCOL_VERSION = "preview-trajectory/v1"

DEFAULT_ROOT = Path.home() / ".cli-it" / "previews"


def bundle_root(
    software: str,
    recipe: str,
    project_path: str | Path | None = None,
    root_dir: str | Path | None = None,
) -> Path:
    """Where a bundle for (software, recipe) lives.

    Project-local previews go under ``<project>/.cli-it/previews`` when a
    project path is given; otherwise the user-global previews root is used.
    """
    if root_dir is not None:
        base = Path(root_dir)
    elif project_path is not None:
        base = Path(project_path).resolve().parent / ".cli-it" / "previews"
    else:
        base = DEFAULT_ROOT
    return base / software / recipe


def fingerprint(payload: dict) -> str:
    """Stable content fingerprint over canonical JSON."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def prepare_bundle(
    software: str,
    recipe: str,
    inputs: dict | None = None,
    project_path: str | Path | None = None,
    root_dir: str | Path | None = None,
) -> Path:
    """Create (or reset) a bundle directory and stamp a draft manifest."""
    bundle = bundle_root(software, recipe, project_path=project_path, root_dir=root_dir)
    artifacts = bundle / "artifacts"
    if artifacts.exists():
        shutil.rmtree(artifacts)
    artifacts.mkdir(parents=True)
    manifest = {
        "protocol": PROTOCOL_VERSION,
        "software": software,
        "recipe": recipe,
        "inputs": inputs or {},
        "fingerprint": fingerprint({"software": software, "recipe": recipe, "inputs": inputs or {}}),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "preparing",
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return bundle


def finalize_bundle(bundle: str | Path, summary: dict | None = None) -> dict:
    """Mark a bundle complete: index artifacts, write summary, seal manifest."""
    bundle = Path(bundle)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    artifacts = []
    artifacts_dir = bundle / "artifacts"
    if artifacts_dir.is_dir():
        for artifact in sorted(artifacts_dir.rglob("*")):
            if artifact.is_file():
                artifacts.append(
                    {
                        "path": str(artifact.relative_to(bundle)),
                        "bytes": artifact.stat().st_size,
                    }
                )

    manifest["status"] = "complete"
    manifest["finalized_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    manifest["artifact_count"] = len(artifacts)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    summary_doc = dict(summary or {})
    summary_doc.setdefault("status", "ok")
    summary_doc["artifacts"] = artifacts
    (bundle / "summary.json").write_text(
        json.dumps(summary_doc, indent=2), encoding="utf-8"
    )
    return manifest


# --- live trajectory sessions ------------------------------------------------


def start_live_session(
    software: str,
    session_dir: str | Path,
    meta: dict | None = None,
) -> Path:
    """Initialize a live session directory with session.json."""
    session_dir = Path(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    session = {
        "protocol": TRAJECTORY_PROTOCOL_VERSION,
        "software": software,
        "status": "running",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        **(meta or {}),
    }
    (session_dir / "session.json").write_text(
        json.dumps(session, indent=2), encoding="utf-8"
    )
    (session_dir / "trajectory.json").write_text(
        json.dumps({"protocol": TRAJECTORY_PROTOCOL_VERSION, "events": []}),
        encoding="utf-8",
    )
    return session_dir


def append_live_trajectory(session_dir: str | Path, event: dict) -> int:
    """Append one event; returns the event's sequence number."""
    trajectory_path = Path(session_dir) / "trajectory.json"
    doc = (
        json.loads(trajectory_path.read_text(encoding="utf-8"))
        if trajectory_path.is_file()
        else {"protocol": TRAJECTORY_PROTOCOL_VERSION, "events": []}
    )
    seq = len(doc["events"])
    stamped = {"seq": seq, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **event}
    doc["events"].append(stamped)
    trajectory_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return seq


def load_live_trajectory(session_dir: str | Path) -> list[dict]:
    trajectory_path = Path(session_dir) / "trajectory.json"
    if not trajectory_path.is_file():
        return []
    return json.loads(trajectory_path.read_text(encoding="utf-8")).get("events", [])


def summarize_trajectory(session_dir: str | Path) -> dict:
    events = load_live_trajectory(session_dir)
    by_type: dict[str, int] = {}
    for event in events:
        by_type[event.get("type", "event")] = by_type.get(event.get("type", "event"), 0) + 1
    return {
        "events": len(events),
        "by_type": by_type,
        "first_ts": events[0].get("ts") if events else None,
        "last_ts": events[-1].get("ts") if events else None,
    }


def stop_live_session(session_dir: str | Path, status: str = "stopped") -> None:
    session_path = Path(session_dir) / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    session["status"] = status
    session["stopped_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    session_path.write_text(json.dumps(session, indent=2), encoding="utf-8")
