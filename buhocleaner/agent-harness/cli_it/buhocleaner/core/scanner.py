"""Read-only size probes for cleanup-plan categories.

This module NEVER deletes, moves, or writes anything under the scanned
roots — it only stats files. Permission errors and races are skipped and
counted, so scans work under sandboxing/TCC without special grants.
Deletion is exclusively the real BuhoCleaner app's job.
"""

from __future__ import annotations

import fnmatch
import os
import time
from pathlib import Path

from cli_it.buhocleaner.core import plan as _plan


def _iter_glob_files(root: Path, globs: list[str]):
    """Yield (path, size) for top-level files of root matching any glob."""
    try:
        entries = list(os.scandir(root))
    except OSError:
        return
    for entry in entries:
        if any(fnmatch.fnmatch(entry.name, g) for g in globs):
            try:
                if entry.is_file(follow_symlinks=False):
                    yield entry.path, entry.stat(follow_symlinks=False).st_size
            except OSError:
                continue


def scan_category(plan: _plan.Plan, name: str) -> dict:
    """Probe one category; returns {root, bytes, files, skipped, exists}."""
    spec = _plan.CATEGORIES[name]
    root = plan.root_for(name)
    result = {
        "root": str(root),
        "bytes": 0,
        "files": 0,
        "skipped": 0,
        "exists": root.exists(),
    }
    if not result["exists"]:
        return result
    threshold = plan.threshold_mb * 1024 * 1024 if name == "large-files" else 0

    if spec["glob"] is not None:
        for _, size in _iter_glob_files(root, spec["glob"]):
            result["files"] += 1
            result["bytes"] += size
        return result

    stack = [str(root)]
    while stack:
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            result["skipped"] += 1
            continue
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    size = entry.stat(follow_symlinks=False).st_size
                    if size >= threshold:
                        result["files"] += 1
                        result["bytes"] += size
            except OSError:
                result["skipped"] += 1
    return result


def run_scan(plan: _plan.Plan, only: str | None = None) -> dict:
    """Probe enabled categories (or one); returns the snapshot dict."""
    names = [only] if only else plan.enabled_categories()
    for name in names:
        if name not in _plan.CATEGORIES:
            raise _plan.PlanError(f"unknown category {name!r}")
    categories = {name: scan_category(plan, name) for name in names}
    return {
        "plan": plan.name,
        "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_bytes": sum(c["bytes"] for c in categories.values()),
        "categories": categories,
    }


def human_bytes(count: int) -> str:
    value = float(count)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{count} B"
