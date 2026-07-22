"""Learned facts about the installed repomix, persisted between runs.

The harness reads repomix's console output, which is not a stable API. Rather
than only failing when that format changes, it can *learn* the new format —
but only where a claim can be checked against independent ground truth.

What is stored: a map from repomix's summary labels to the harness's field
names, keyed by repomix version, with the evidence that justified each entry.
Nothing is stored on faith; see `provenance` on every learned label.

What is deliberately **not** stored: anything about the security-check block.
See `utils/repomix_backend.parse_security` for why.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from cli_it.repomix.core.session import _locked_handle

KNOWLEDGE_FORMAT = "repomix-knowledge/v1"

#: How a learned label was justified. Verified entries were confirmed against a
#: count derived from repomix's own JSON output; heuristic entries were only
#: matched by label wording and are reported as such.
VERIFIED = "verified-against-json-output"
HEURISTIC = "label-wording-heuristic"


def knowledge_home() -> Path:
    """Where learned formats live (overridable so tests never touch $HOME)."""
    override = os.environ.get("CLI_IT_REPOMIX_HOME")
    base = Path(override) if override else Path.home() / ".cli-it" / "repomix"
    return base


def knowledge_path() -> Path:
    return knowledge_home() / "learned-formats.json"


def _default() -> dict:
    return {"format": KNOWLEDGE_FORMAT, "versions": {}}


def load() -> dict:
    path = knowledge_path()
    if not path.is_file():
        return _default()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return _default()
    if not isinstance(data, dict) or data.get("format") != KNOWLEDGE_FORMAT:
        return _default()
    return data


def learned_labels(version: str | None) -> dict[str, str]:
    """Label → field map learned for this repomix version (empty when none)."""
    if not version:
        return {}
    entry = load().get("versions", {}).get(version) or {}
    return {label: fact["field"] for label, fact in (entry.get("labels") or {}).items()}


def record_labels(version: str, labels: dict[str, dict]) -> dict:
    """Persist learned labels for `version` under an exclusive lock.

    `labels` maps a repomix label to `{"field": ..., "provenance": ..., "evidence": ...}`.
    """
    path = knowledge_path()
    with _locked_handle(path) as handle:
        raw = handle.read()
        try:
            state = json.loads(raw) if raw.strip() else _default()
        except ValueError:
            state = _default()
        if state.get("format") != KNOWLEDGE_FORMAT:
            state = _default()

        entry = state.setdefault("versions", {}).setdefault(version, {})
        entry.setdefault("labels", {}).update(labels)
        entry["learned_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(state, indent=2))
        handle.flush()
        os.fsync(handle.fileno())
    return state


def forget(version: str | None = None) -> dict:
    """Drop learned labels for one version, or all of them."""
    path = knowledge_path()
    if not path.is_file():
        return _default()
    with _locked_handle(path) as handle:
        raw = handle.read()
        try:
            state = json.loads(raw) if raw.strip() else _default()
        except ValueError:
            state = _default()
        if version is None:
            state = _default()
        else:
            state.get("versions", {}).pop(version, None)
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(state, indent=2))
        handle.flush()
        os.fsync(handle.fileno())
    return state
