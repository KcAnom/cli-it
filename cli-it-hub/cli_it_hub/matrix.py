"""Capability matrices: fetch, preflight, and install-scope resolution.

A matrix declares *capabilities* (what an agent may need to do) and, per
capability, a ranked list of *providers* (concrete ways to do it). Preflight
answers "which capabilities are usable right now on this machine?" without
installing anything.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
from pathlib import Path

from . import registry as _registry
from .registry import _fetch_json

MATRIX_REGISTRY_URL = f"{_registry._base_url()}/matrix_registry.json"

HUB_STATE_DIR = Path.home() / ".cli-it-hub"
MATRIX_CACHE_FILE = HUB_STATE_DIR / "matrix_registry_cache.json"

INSTALLABLE_KINDS = {"harness-cli", "public-cli"}
AGENT_INSTALLABLE_KINDS = {"agent-skill"}
HARNESS_PREFIX = "cli-it-"


def fetch_matrix_registry(force_refresh: bool = False) -> dict:
    return _fetch_json(
        MATRIX_REGISTRY_URL,
        MATRIX_CACHE_FILE,
        force_refresh=force_refresh,
        local_name="matrix_registry.json",
    )


def fetch_all_matrices(force_refresh: bool = False) -> list[dict]:
    return list(fetch_matrix_registry(force_refresh=force_refresh).get("matrices", []))


def get_matrix(name: str, force_refresh: bool = False) -> dict | None:
    name = name.lower()
    for matrix in fetch_all_matrices(force_refresh=force_refresh):
        if matrix.get("name", "").lower() == name:
            return matrix
    return None


def search_matrices(query: str) -> list[dict]:
    query = query.lower()
    hits = []
    for matrix in fetch_all_matrices():
        haystack = " ".join(
            str(matrix.get(f, ""))
            for f in ("name", "display_name", "description", "category")
        ).lower()
        if query in haystack:
            hits.append(matrix)
    return hits


def check_provider_requirements(provider: dict) -> dict:
    """Check a provider's `requires` on this machine.

    `requires` is null (nothing needed) or a dict with any of:
      binary: [names checked via shutil.which]
      package: [import names checked via importlib]
      env: [environment variable names]

    Returns {"ok": bool, "missing": {"binary": [...], "package": [...], "env": [...]}}.
    """
    missing: dict[str, list[str]] = {"binary": [], "package": [], "env": []}
    requires = provider.get("requires") or {}
    for binary in requires.get("binary", []):
        if shutil.which(binary) is None:
            missing["binary"].append(binary)
    for package in requires.get("package", []):
        try:
            found = importlib.util.find_spec(package) is not None
        except (ImportError, ValueError):
            found = False
        if not found:
            missing["package"].append(package)
    for env_var in requires.get("env", []):
        if not os.environ.get(env_var):
            missing["env"].append(env_var)
    return {"ok": not any(missing.values()), "missing": missing}


def provider_install_hint(provider: dict) -> str | None:
    """Best install hint for a provider, deriving one for harness CLIs."""
    hint = provider.get("install_hint")
    if hint:
        return hint
    if provider.get("kind") == "harness-cli":
        return f"cli-it install {provider.get('name')}"
    return None


def preflight_matrix(
    matrix_item: dict,
    capability_id: str | None = None,
    offline: bool = False,
) -> dict:
    """Evaluate provider availability for a matrix (or one capability).

    A capability is `ready` when at least one provider's requirements are
    satisfied. With offline=True, providers marked `"offline": false` are
    excluded. Result carries `ok` (no gaps) and `gaps` (capability ids with no
    usable provider) — CLI maps gaps to exit code 3, not a hard failure.
    """
    capabilities = matrix_item.get("capabilities", [])
    if capability_id is not None:
        capabilities = [c for c in capabilities if c.get("id") == capability_id]
        if not capabilities:
            raise KeyError(
                f"capability '{capability_id}' not found in matrix "
                f"'{matrix_item.get('name')}'"
            )

    report: list[dict] = []
    gaps: list[str] = []
    for capability in capabilities:
        providers_report = []
        ready = False
        for provider in capability.get("providers", []):
            if offline and provider.get("offline") is False:
                providers_report.append(
                    {
                        "name": provider.get("name"),
                        "kind": provider.get("kind"),
                        "ok": False,
                        "skipped": "requires network (offline mode)",
                        "install_hint": provider_install_hint(provider),
                    }
                )
                continue
            check = check_provider_requirements(provider)
            providers_report.append(
                {
                    "name": provider.get("name"),
                    "kind": provider.get("kind"),
                    "ok": check["ok"],
                    "missing": check["missing"],
                    "install_hint": provider_install_hint(provider),
                }
            )
            ready = ready or check["ok"]
        report.append(
            {
                "capability": capability.get("id"),
                "intent": capability.get("intent"),
                "ready": ready,
                "providers": providers_report,
            }
        )
        if not ready:
            gaps.append(capability.get("id"))

    return {
        "matrix": matrix_item.get("name"),
        "ok": not gaps,
        "gaps": gaps,
        "capabilities": report,
    }


def resolve_install_scope(
    matrix_item: dict,
    capability: str | None = None,
    recipe: str | None = None,
    only: list[str] | None = None,
) -> list[dict]:
    """Resolve which providers an install run should cover.

    Scope narrows by recipe (its capability list), then capability id, then an
    explicit `only` provider-name allowlist. Returns unique installable
    providers (hub-installable kinds plus agent-installable skills), tagged
    with the capability that pulled them in.
    """
    capability_ids: set[str] | None = None
    if recipe is not None:
        match = next(
            (r for r in matrix_item.get("recipes", []) if r.get("name") == recipe),
            None,
        )
        if match is None:
            raise KeyError(
                f"recipe '{recipe}' not found in matrix '{matrix_item.get('name')}'"
            )
        capability_ids = set(match.get("capabilities", []))
    if capability is not None:
        capability_ids = (capability_ids or set()) | {capability}

    scope: list[dict] = []
    seen: set[str] = set()
    for cap in matrix_item.get("capabilities", []):
        if capability_ids is not None and cap.get("id") not in capability_ids:
            continue
        for provider in cap.get("providers", []):
            kind = provider.get("kind")
            name = provider.get("name", "")
            if kind not in INSTALLABLE_KINDS | AGENT_INSTALLABLE_KINDS:
                continue
            if only is not None and name not in only:
                continue
            if name in seen:
                continue
            seen.add(name)
            item = dict(provider)
            item["_capability"] = cap.get("id")
            item["_agent_installable"] = kind in AGENT_INSTALLABLE_KINDS
            scope.append(item)
    return scope


def search_capabilities(query: str) -> list[dict]:
    """Search capability intents/hints across all matrices (powers `cli-it can`)."""
    query = query.lower()
    hits = []
    for matrix in fetch_all_matrices():
        for capability in matrix.get("capabilities", []):
            haystack = " ".join(
                [
                    str(capability.get("id", "")),
                    str(capability.get("intent", "")),
                    " ".join(capability.get("skill_search_hints", []) or []),
                ]
            ).lower()
            if all(term in haystack for term in query.split()):
                hit = dict(capability)
                hit["_matrix"] = matrix.get("name")
                hits.append(hit)
    return hits


def all_recipes() -> list[dict]:
    recipes = []
    for matrix in fetch_all_matrices():
        for recipe in matrix.get("recipes", []) or []:
            tagged = dict(recipe)
            tagged["_matrix"] = matrix.get("name")
            recipes.append(tagged)
    return recipes
