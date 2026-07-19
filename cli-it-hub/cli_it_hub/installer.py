"""Install/uninstall/update CLIs and matrix tooling.

Install commands always come from the CLI-It registries (trusted content),
never from raw user input. Plain commands run without a shell; a shell is used
only when a registry command contains shell operators (pipes, `&&`, …).
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import matrix as _matrix
from . import registry as _registry

STATE_DIR = Path.home() / ".cli-it-hub"
INSTALLED_FILE = STATE_DIR / "installed.json"
MATRIX_STATE_FILE = STATE_DIR / "matrix_state.json"

_SHELL_OPERATORS = ("|", "&&", "||", ";", ">", "<", "$(")


class InstallError(RuntimeError):
    pass


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _run_registry_command(cmd: str) -> subprocess.CompletedProcess:
    """Run a registry-trusted install command.

    Shell execution is allowed only when the trusted command actually needs it
    (contains shell operators); otherwise the command is exec'd directly.
    """
    if any(op in cmd for op in _SHELL_OPERATORS):
        return subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return subprocess.run(shlex.split(cmd), capture_output=True, text=True)


def build_install_command(entry: dict) -> str:
    """Normalize an entry's install command by package-manager strategy."""
    install_cmd = (entry.get("install_cmd") or "").strip()
    pm = entry.get("package_manager")
    if pm is None and install_cmd.startswith("pip install"):
        pm = "pip"

    if pm == "pip" or install_cmd.startswith("pip install"):
        args = install_cmd.removeprefix("pip install").strip() or entry.get("name", "")
        if shutil.which("uv"):
            return f"uv pip install {args}"
        return f"{sys.executable} -m pip install {args}"
    if pm == "npm":
        if install_cmd:
            return install_cmd
        pkg = entry.get("npm_package") or entry.get("name")
        return f"npm install -g {pkg}"
    if not install_cmd:
        raise InstallError(
            f"registry entry '{entry.get('name')}' has no install_cmd"
        )
    return install_cmd  # brew / bundled / generic — run as published


def get_installed() -> dict:
    return _load_json(INSTALLED_FILE, {})


def _record_installed(entry: dict) -> None:
    installed = get_installed()
    installed[entry["name"]] = {
        "version": entry.get("version"),
        "entry_point": entry.get("entry_point"),
        "source": entry.get("_source", "harness"),
        "package_manager": entry.get("package_manager"),
        "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    _save_json(INSTALLED_FILE, installed)


def install_cli(name: str, dry_run: bool = False) -> dict:
    entry = _registry.get_cli(name)
    if entry is None:
        raise InstallError(f"'{name}' not found in any registry")
    cmd = build_install_command(entry)
    if dry_run:
        return {"name": name, "command": cmd, "dry_run": True, "ok": True}
    result = _run_registry_command(cmd)
    if result.returncode != 0:
        raise InstallError(
            f"install of '{name}' failed (rc={result.returncode}):\n"
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    _record_installed(entry)
    return {"name": name, "command": cmd, "ok": True}


def uninstall_cli(name: str) -> dict:
    entry = _registry.get_cli(name) or {"name": name}
    installed = get_installed()
    record = installed.get(name, {})
    pm = record.get("package_manager") or entry.get("package_manager")

    if pm == "npm":
        pkg = entry.get("npm_package") or name
        cmd = f"npm uninstall -g {pkg}"
    elif pm in (None, "pip"):
        # Harness packages install under the distribution name cli-it-<name>
        # unless the entry points elsewhere.
        dist = name if entry.get("_source") == "public" else f"cli-it-{name}"
        cmd = f"{sys.executable} -m pip uninstall -y {dist}"
    else:
        installed.pop(name, None)
        _save_json(INSTALLED_FILE, installed)
        return {
            "name": name,
            "ok": True,
            "note": f"'{name}' was installed via {pm}; remove it with that tool.",
        }

    result = _run_registry_command(cmd)
    installed.pop(name, None)
    _save_json(INSTALLED_FILE, installed)
    return {"name": name, "command": cmd, "ok": result.returncode == 0}


def update_cli(name: str) -> dict:
    entry = _registry.get_cli(name, force_refresh=True)
    if entry is None:
        raise InstallError(f"'{name}' not found in any registry")
    cmd = build_install_command(entry)
    if cmd.startswith((f"{sys.executable} -m pip install", "uv pip install")):
        head, _, tail = cmd.partition(" install ")
        cmd = f"{head} install --upgrade {tail}"
    result = _run_registry_command(cmd)
    if result.returncode != 0:
        raise InstallError(
            f"update of '{name}' failed (rc={result.returncode}):\n"
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    _record_installed(entry)
    return {"name": name, "command": cmd, "ok": True}


# --- matrix installs ---------------------------------------------------------


def plan_matrix_install(
    matrix_item: dict,
    capability: str | None = None,
    recipe: str | None = None,
    only: list[str] | None = None,
) -> list[dict]:
    """Build an ordered step plan for installing a matrix's tooling.

    Step actions: `skip` (already satisfied), `run` (hub executes a command),
    `agent` (the agent/user must act, e.g. install a skill or export a key).
    """
    scope = _matrix.resolve_install_scope(
        matrix_item, capability=capability, recipe=recipe, only=only
    )
    steps: list[dict] = []
    for provider in scope:
        check = _matrix.check_provider_requirements(provider)
        step = {
            "name": provider.get("name"),
            "kind": provider.get("kind"),
            "capability": provider.get("_capability"),
            "satisfied": check["ok"],
            "missing": check["missing"],
        }
        if check["ok"]:
            step["action"] = "skip"
        elif provider.get("_agent_installable"):
            step["action"] = "agent"
            step["hint"] = _matrix.provider_install_hint(provider)
        elif provider.get("kind") == "harness-cli":
            entry = _registry.get_cli(provider.get("name", ""))
            if entry is not None:
                step["action"] = "run"
                step["command"] = build_install_command(entry)
            else:
                step["action"] = "agent"
                step["hint"] = _matrix.provider_install_hint(provider)
        else:  # public-cli — trust the matrix install hint as the command
            hint = _matrix.provider_install_hint(provider)
            if hint:
                step["action"] = "run"
                step["command"] = hint
            else:
                step["action"] = "agent"
                step["hint"] = None
        steps.append(step)
    return steps


def _matrix_state() -> dict:
    return _load_json(MATRIX_STATE_FILE, {})


def install_matrix(
    matrix_item: dict,
    capability: str | None = None,
    recipe: str | None = None,
    only: list[str] | None = None,
    dry_run: bool = False,
    resume: bool = False,
) -> dict:
    """Execute (or preview) a matrix install plan.

    With resume=True, steps recorded as completed in matrix_state.json are
    skipped. State is keyed by matrix name.
    """
    name = matrix_item.get("name", "unknown")
    plan = plan_matrix_install(
        matrix_item, capability=capability, recipe=recipe, only=only
    )
    state = _matrix_state()
    completed: list[str] = list(state.get(name, {}).get("completed", []))

    summary = {
        "matrix": name,
        "dry_run": dry_run,
        "installed": [],
        "skipped": [],
        "agent_actions": [],
        "failed": [],
        "plan": plan,
    }

    for step in plan:
        step_name = step["name"]
        if step["action"] == "skip" or (resume and step_name in completed):
            summary["skipped"].append(step_name)
            continue
        if step["action"] == "agent":
            summary["agent_actions"].append(
                {"name": step_name, "hint": step.get("hint")}
            )
            continue
        if dry_run:
            summary["installed"].append(
                {"name": step_name, "command": step["command"], "dry_run": True}
            )
            continue
        result = _run_registry_command(step["command"])
        if result.returncode == 0:
            summary["installed"].append(
                {"name": step_name, "command": step["command"]}
            )
            if step_name not in completed:
                completed.append(step_name)
        else:
            summary["failed"].append(
                {
                    "name": step_name,
                    "command": step["command"],
                    "rc": result.returncode,
                    "stderr": (result.stderr or "").strip()[-2000:],
                }
            )

    if not dry_run:
        state[name] = {
            "completed": completed,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        _save_json(MATRIX_STATE_FILE, state)

    summary["ok"] = not summary["failed"]
    return summary


def doctor_matrix(matrix_item: dict) -> dict:
    """Diagnose a matrix: preflight + recorded state + remediation hints."""
    preflight = _matrix.preflight_matrix(matrix_item)
    name = matrix_item.get("name", "unknown")
    state = _matrix_state().get(name, {})
    remedies = []
    for cap in preflight["capabilities"]:
        if cap["ready"]:
            continue
        for provider in cap["providers"]:
            if provider.get("install_hint"):
                remedies.append(
                    {
                        "capability": cap["capability"],
                        "provider": provider["name"],
                        "hint": provider["install_hint"],
                    }
                )
    return {
        "matrix": name,
        "ok": preflight["ok"],
        "gaps": preflight["gaps"],
        "state": state,
        "remedies": remedies,
        "preflight": preflight,
    }
