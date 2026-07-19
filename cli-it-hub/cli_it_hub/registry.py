"""Registry access for the CLI-It Hub.

The hub is registry-driven: JSON documents are the single source of truth for
what can be listed, searched, and installed. Resolution order for each
registry:

1. Local repo checkout (walking parents of this file) — dev/offline mode
2. Fresh cache (younger than ``CACHE_TTL`` seconds)
3. Network fetch from the published hub site
4. Stale cache as a last resort

``CLI_HUB_REGISTRY_BASE_URL`` overrides the published base URL.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests

DEFAULT_BASE_URL = "https://elev8tion.github.io/cli-it"


def _base_url() -> str:
    return os.environ.get("CLI_HUB_REGISTRY_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


REGISTRY_URL = f"{_base_url()}/registry.json"
PUBLIC_REGISTRY_URL = f"{_base_url()}/public_registry.json"

CACHE_DIR = Path.home() / ".cli-it"
CACHE_TTL = 3600  # seconds


class RegistryError(RuntimeError):
    """Raised when a registry cannot be resolved from any source."""


def find_repo_root() -> Path | None:
    """Walk parents of this file looking for a CLI-It repo checkout."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "registry.json").is_file() and (parent / "cli-it-hub").is_dir():
            return parent
    return None


def _local_registry_path(filename: str) -> Path | None:
    root = find_repo_root()
    if root is None:
        return None
    candidate = root / filename
    return candidate if candidate.is_file() else None


def _read_cache(cache_file: Path) -> tuple[float, Any] | None:
    try:
        envelope = json.loads(cache_file.read_text(encoding="utf-8"))
        return float(envelope["_cached_at"]), envelope["data"]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _write_cache(cache_file: Path, data: Any) -> None:
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps({"_cached_at": time.time(), "data": data}), encoding="utf-8"
        )
    except OSError:
        pass  # caching is best-effort


def _fetch_json(
    url: str,
    cache_file: Path,
    force_refresh: bool = False,
    local_name: str | None = None,
) -> Any:
    """Resolve a registry document. See module docstring for the order."""
    if not force_refresh and local_name:
        local = _local_registry_path(local_name)
        if local is not None:
            return json.loads(local.read_text(encoding="utf-8"))

    cached = _read_cache(cache_file)
    if not force_refresh and cached is not None:
        cached_at, data = cached
        if time.time() - cached_at < CACHE_TTL:
            return data

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        _write_cache(cache_file, data)
        return data
    except (requests.RequestException, ValueError):
        if cached is not None:  # stale cache beats nothing
            return cached[1]
        if local_name:
            local = _local_registry_path(local_name)
            if local is not None:
                return json.loads(local.read_text(encoding="utf-8"))
        raise RegistryError(
            f"Could not fetch {url} and no cached or local copy exists. "
            "Check your network, or run from a CLI-It checkout."
        )


def fetch_registry(force_refresh: bool = False) -> dict:
    return _fetch_json(
        REGISTRY_URL,
        CACHE_DIR / "registry_cache.json",
        force_refresh=force_refresh,
        local_name="registry.json",
    )


def fetch_public_registry(force_refresh: bool = False) -> dict:
    return _fetch_json(
        PUBLIC_REGISTRY_URL,
        CACHE_DIR / "public_registry_cache.json",
        force_refresh=force_refresh,
        local_name="public_registry.json",
    )


def fetch_all_clis(force_refresh: bool = False) -> list[dict]:
    """Merge harness + public registries, tagging each entry with `_source`.

    Entries are copied before tagging so cached registry objects are never
    mutated (copy-before-tag convention).
    """
    merged: list[dict] = []
    for fetcher, source in (
        (fetch_registry, "harness"),
        (fetch_public_registry, "public"),
    ):
        try:
            doc = fetcher(force_refresh=force_refresh)
        except RegistryError:
            continue
        for entry in doc.get("clis", []):
            tagged = dict(entry)
            tagged["_source"] = source
            merged.append(tagged)
    return merged


def get_cli(name: str, force_refresh: bool = False) -> dict | None:
    name = name.lower()
    for entry in fetch_all_clis(force_refresh=force_refresh):
        if entry.get("name", "").lower() == name:
            return entry
    return None


def search_clis(query: str) -> list[dict]:
    query = query.lower()
    hits = []
    for entry in fetch_all_clis():
        haystack = " ".join(
            str(entry.get(field, ""))
            for field in ("name", "display_name", "description", "category")
        ).lower()
        if query in haystack:
            hits.append(entry)
    return hits


def list_categories() -> list[str]:
    return sorted({e.get("category", "uncategorized") for e in fetch_all_clis()})
