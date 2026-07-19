"""The DemoApp backend boundary.

This is the ONLY module that invokes the "real" DemoApp engine. DemoApp's
engine is a standalone Python renderer executed as a separate OS process —
a deliberately trivial but *real* external tool, so the harness demonstrates
the exact pattern used for Blender/GIMP/FFmpeg backends: detect the binary,
invoke it out-of-process, verify its output exists.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


class BackendError(RuntimeError):
    pass


# The external render engine, run via `python -c`. It reads a project JSON
# and writes a rendered document — the harness never renders in-process.
_RENDER_ENGINE = r"""
import json, sys
project_path, output_path, fmt = sys.argv[1], sys.argv[2], sys.argv[3]
doc = json.load(open(project_path, encoding="utf-8"))
items = doc.get("items", [])
if fmt == "json":
    out = json.dumps({
        "renderer": "demoapp-engine/1.0",
        "project": doc.get("name"),
        "items": items,
        "item_count": len(items),
    }, indent=2)
else:
    lines = [f"DemoApp render — project: {doc.get('name')}", "=" * 40]
    for item in items:
        lines.append(f"[{item.get('id')}] {item.get('kind', 'item')}: {item.get('name')}")
    lines.append(f"-- {len(items)} item(s) rendered --")
    out = "\n".join(lines) + "\n"
open(output_path, "w", encoding="utf-8").write(out)
"""


def engine_executable() -> str:
    """Locate the engine runtime (the Python interpreter running us)."""
    return sys.executable


def backend_available() -> bool:
    exe = engine_executable()
    return bool(exe) and (Path(exe).exists() or shutil.which(exe) is not None)


def require_backend() -> None:
    if not backend_available():
        raise BackendError(
            "DemoApp engine not found. Install Python 3.10+ so the engine "
            "runtime is available (this harness renders via an external "
            "python process)."
        )


def render_project(
    project_path: str | Path, output_path: str | Path, fmt: str = "text"
) -> Path:
    """Render a project file with the real engine; returns the output path."""
    require_backend()
    project_path = Path(project_path)
    output_path = Path(output_path)
    if not project_path.is_file():
        raise BackendError(f"project file not found: {project_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [engine_executable(), "-c", _RENDER_ENGINE, str(project_path), str(output_path), fmt],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise BackendError(
            f"engine render failed (rc={result.returncode}): {result.stderr.strip()}"
        )
    if not output_path.is_file():
        raise BackendError(f"engine reported success but {output_path} does not exist")
    return output_path


def engine_version() -> str:
    require_backend()
    result = subprocess.run(
        [engine_executable(), "--version"], capture_output=True, text=True
    )
    return (result.stdout or result.stderr).strip()


def probe() -> dict:
    """Structured backend health info for `--json` consumers."""
    available = backend_available()
    info = {"available": available, "engine": engine_executable()}
    if available:
        info["version"] = engine_version()
    else:
        info["install_hint"] = "Install Python 3.10+ (https://python.org)"
    return info
