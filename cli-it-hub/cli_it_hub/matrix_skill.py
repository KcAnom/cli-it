"""Resolve and render matrix skill packs onto the local machine.

Matrix SKILL.md content is looked up in order:

1. Repo checkout: ``<repo>/cli-it-matrix/<name>/``
2. Bundled wheel data: ``cli_it_hub/_matrix_data/<name>/`` (vendored at build)
3. Published hub site: ``https://…/matrix/<name>/SKILL.md``

Rendered skills land in ``~/.cli-it-hub/matrix/<name>/`` with an
installed-tooling section injected between the
``<!-- MATRIX_SKILL_PATHS:START -->`` / ``:END`` markers.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import requests

from . import matrix as _matrix
from . import registry as _registry

MARKER_START = "<!-- MATRIX_SKILL_PATHS:START -->"
MARKER_END = "<!-- MATRIX_SKILL_PATHS:END -->"

RENDER_ROOT = Path.home() / ".cli-it-hub" / "matrix"
_ASSET_DIRS = ("references", "scripts")


def _bundled_dir(name: str) -> Path:
    return Path(__file__).resolve().parent / "_matrix_data" / name


def _checkout_dir(name: str) -> Path | None:
    root = _registry.find_repo_root()
    if root is None:
        return None
    candidate = root / "cli-it-matrix" / name
    return candidate if candidate.is_dir() else None


def find_matrix_skill_source(name: str) -> tuple[str, Path | str] | None:
    """Return ("checkout"|"bundled"|"url", location) or None."""
    checkout = _checkout_dir(name)
    if checkout is not None and (checkout / "SKILL.md").is_file():
        return ("checkout", checkout)
    bundled = _bundled_dir(name)
    if (bundled / "SKILL.md").is_file():
        return ("bundled", bundled)
    return ("url", f"{_registry._base_url()}/matrix/{name}/SKILL.md")


def load_matrix_skill_md(name: str) -> str:
    source = find_matrix_skill_source(name)
    if source is None:
        raise FileNotFoundError(f"no skill content for matrix '{name}'")
    kind, location = source
    if kind == "url":
        resp = requests.get(str(location), timeout=15)
        resp.raise_for_status()
        return resp.text
    return (Path(location) / "SKILL.md").read_text(encoding="utf-8")


def _installed_tooling_section(matrix_item: dict, installed: dict | None) -> str:
    """Markdown block describing locally-usable providers, per capability."""
    preflight = _matrix.preflight_matrix(matrix_item)
    lines = ["", "## Installed tooling on this machine", ""]
    for cap in preflight["capabilities"]:
        ready = [p["name"] for p in cap["providers"] if p.get("ok")]
        if ready:
            lines.append(f"- `{cap['capability']}` — ready via: {', '.join(ready)}")
        else:
            hints = sorted(
                {p["install_hint"] for p in cap["providers"] if p.get("install_hint")}
            )
            hint = f" (install: {'; '.join(hints)})" if hints else ""
            lines.append(f"- `{cap['capability']}` — **gap**{hint}")
    if installed:
        lines += ["", "Hub-installed CLIs: " + ", ".join(sorted(installed))]
    lines.append("")
    return "\n".join(lines)


def _inject_between_markers(content: str, section: str) -> str:
    block = f"{MARKER_START}\n{section}\n{MARKER_END}"
    if MARKER_START in content and MARKER_END in content:
        head, _, rest = content.partition(MARKER_START)
        _, _, tail = rest.partition(MARKER_END)
        return head + block + tail
    return content.rstrip() + "\n\n" + block + "\n"


def render_matrix_skill_file(matrix_item: dict, installed: dict | None = None) -> Path:
    """Write the rendered SKILL.md (plus reference/script assets) locally."""
    name = matrix_item.get("name", "unknown")
    content = load_matrix_skill_md(name)
    content = _inject_between_markers(
        content, _installed_tooling_section(matrix_item, installed)
    )

    target_dir = RENDER_ROOT / name
    target_dir.mkdir(parents=True, exist_ok=True)
    skill_path = target_dir / "SKILL.md"
    skill_path.write_text(content, encoding="utf-8")

    source = find_matrix_skill_source(name)
    if source is not None and source[0] in ("checkout", "bundled"):
        source_dir = Path(source[1])
        for asset in _ASSET_DIRS:
            src = source_dir / asset
            if src.is_dir():
                shutil.copytree(src, target_dir / asset, dirs_exist_ok=True)
    return skill_path
