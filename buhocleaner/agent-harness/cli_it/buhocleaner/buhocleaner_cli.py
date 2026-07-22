"""BuhoCleaner harness CLI — agent-native command surface.

Dual mode: `cli-it-buhocleaner` with no subcommand starts a ReplSkin REPL;
any subcommand runs one-shot. The root `--json` flag switches output to
machine-readable JSON on stdout.

Safety: the harness never deletes files. Scans are read-only probes; actual
cleaning always happens inside the real BuhoCleaner app.
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path

import click

from cli_it.buhocleaner import __version__
from cli_it.buhocleaner.core import plan as _plan
from cli_it.buhocleaner.core import scanner as _scanner
from cli_it.buhocleaner.core import session as _session
from cli_it.buhocleaner.utils import buhocleaner_backend as _backend
from cli_it.buhocleaner.utils import preview_bundle as _preview
from cli_it.buhocleaner.utils.repl_skin import ReplSkin

_plan_option = click.option(
    "-p",
    "--plan",
    "plan_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Path to the cleanup-plan JSON file.",
)


def _emit(ctx: click.Context, data: dict, human: list[str]) -> None:
    if (ctx.obj or {}).get("json"):
        click.echo(json.dumps(data, indent=2))
    else:
        for line in human:
            click.echo(line)


def _load(plan_path: Path) -> _plan.Plan:
    try:
        return _plan.load_plan(plan_path)
    except _plan.PlanError as exc:
        raise click.ClickException(str(exc))


def _backend_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except _backend.BackendError as exc:
        raise click.ClickException(str(exc))


def _mutate(ctx: click.Context, plan_path: Path, action: dict, human: list[str]) -> None:
    """Apply a plan action, save, journal, emit."""
    plan = _load(plan_path)
    try:
        _plan.apply_action(plan, action)
    except _plan.PlanError as exc:
        raise click.ClickException(str(exc))
    _plan.save_plan(plan, plan_path)
    _session.record_action(plan_path, action)
    _emit(ctx, {"action": action}, human)


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="cli-it-buhocleaner")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@click.pass_context
def cli(ctx: click.Context, as_json: bool) -> None:
    """BuhoCleaner agent harness (REPL when no subcommand)."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = as_json
    if ctx.invoked_subcommand is None:
        _run_repl()


@cli.command("backend")
@click.pass_context
def backend_cmd(ctx: click.Context) -> None:
    """Probe the BuhoCleaner installation."""
    info = _backend.probe()
    _emit(ctx, info, [f"{key}: {value}" for key, value in info.items()])


# --- app ---------------------------------------------------------------------


@cli.group()
def app() -> None:
    """Inspect and control the real BuhoCleaner application."""


@app.command("info")
@click.pass_context
def app_info(ctx: click.Context) -> None:
    """Show bundle version, helper, and running state."""
    info = _backend.probe()
    _emit(ctx, info, [f"{key}: {value}" for key, value in info.items()])


@app.command("launch")
@click.pass_context
def app_launch(ctx: click.Context) -> None:
    """Launch (or activate) BuhoCleaner."""
    _backend_call(_backend.launch)
    _emit(ctx, {"launched": True}, ["launched BuhoCleaner"])


@app.command("quit")
@click.pass_context
def app_quit(ctx: click.Context) -> None:
    """Ask BuhoCleaner to quit (may prompt for Automation permission)."""
    was_running = _backend_call(_backend.quit_app)
    _emit(
        ctx,
        {"quit": was_running},
        ["asked BuhoCleaner to quit" if was_running else "BuhoCleaner is not running"],
    )


@app.command("update-check")
@click.pass_context
def app_update_check(ctx: click.Context) -> None:
    """Compare the installed version against the Sparkle appcast."""
    info = _backend_call(_backend.update_check)
    _emit(ctx, info, [f"{key}: {value}" for key, value in info.items()])


# --- plan --------------------------------------------------------------------


@cli.group("plan")
def plan_group() -> None:
    """Create and inspect cleanup-plan files."""


@plan_group.command("new")
@click.option("-n", "--name", default="cleanup", help="Plan name.")
@click.option(
    "-o",
    "--output",
    "output_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Where to write the plan JSON.",
)
@click.pass_context
def plan_new(ctx: click.Context, name: str, output_path: Path) -> None:
    """Create a new cleanup plan with all categories enabled."""
    if output_path.exists():
        raise click.ClickException(f"refusing to overwrite existing file: {output_path}")
    plan = _plan.new_plan(name)
    _plan.save_plan(plan, output_path)
    _session.update_session(output_path, lambda s: s)  # initialize session file
    _emit(ctx, _plan.plan_info(plan, output_path), [f"created plan '{name}' at {output_path}"])


@plan_group.command("info")
@_plan_option
@click.pass_context
def plan_info_cmd(ctx: click.Context, plan_path: Path) -> None:
    """Show plan details."""
    plan = _load(plan_path)
    info = _plan.plan_info(plan, plan_path)
    _emit(ctx, info, [f"{key}: {value}" for key, value in info.items()])


@plan_group.command("save")
@_plan_option
@click.pass_context
def plan_save(ctx: click.Context, plan_path: Path) -> None:
    """Re-save a plan canonically (validates + normalizes formatting)."""
    plan = _load(plan_path)
    _plan.save_plan(plan, plan_path)
    _emit(ctx, {"path": str(plan_path), "saved": True}, [f"saved {plan_path}"])


# --- category (journaled mutations) ------------------------------------------


@cli.group()
def category() -> None:
    """Enable/disable scan categories and set roots (undoable)."""


@category.command("list")
@_plan_option
@click.pass_context
def category_list(ctx: click.Context, plan_path: Path) -> None:
    """List categories with enabled state and scan roots."""
    plan = _load(plan_path)
    rows = []
    for name in _plan.CATEGORIES:
        state = plan.categories.get(name, {"enabled": True, "root": None})
        last = ((plan.last_scan or {}).get("categories", {}).get(name) or {})
        rows.append(
            {
                "name": name,
                "enabled": state.get("enabled", True),
                "root": str(plan.root_for(name)),
                "last_bytes": last.get("bytes"),
            }
        )
    _emit(
        ctx,
        {"categories": rows, "threshold_mb": plan.threshold_mb},
        [
            f"[{'x' if r['enabled'] else ' '}] {r['name']:<16} {r['root']}"
            + (f"  ({_scanner.human_bytes(r['last_bytes'])})" if r["last_bytes"] is not None else "")
            for r in rows
        ],
    )


def _toggle_action(plan: _plan.Plan, name: str, enabled: bool) -> dict:
    before = plan.category(name).get("enabled", True)
    return {"op": "category.enabled", "category": name, "before": before, "after": enabled}


@category.command("enable")
@_plan_option
@click.argument("name")
@click.pass_context
def category_enable(ctx: click.Context, plan_path: Path, name: str) -> None:
    """Enable a category (journaled)."""
    plan = _load(plan_path)
    try:
        action = _toggle_action(plan, name, True)
    except _plan.PlanError as exc:
        raise click.ClickException(str(exc))
    _mutate(ctx, plan_path, action, [f"enabled {name}"])


@category.command("disable")
@_plan_option
@click.argument("name")
@click.pass_context
def category_disable(ctx: click.Context, plan_path: Path, name: str) -> None:
    """Disable a category (journaled)."""
    plan = _load(plan_path)
    try:
        action = _toggle_action(plan, name, False)
    except _plan.PlanError as exc:
        raise click.ClickException(str(exc))
    _mutate(ctx, plan_path, action, [f"disabled {name}"])


@category.command("threshold")
@_plan_option
@click.option("--mb", "mb", required=True, type=int, help="Large-file threshold in MB.")
@click.pass_context
def category_threshold(ctx: click.Context, plan_path: Path, mb: int) -> None:
    """Set the large-files scan threshold in MB (journaled)."""
    if mb < 1:
        raise click.ClickException("threshold must be >= 1 MB")
    plan = _load(plan_path)
    action = {"op": "plan.threshold", "before": plan.threshold_mb, "after": mb}
    _mutate(ctx, plan_path, action, [f"large-files threshold set to {mb} MB"])


@category.command("root")
@_plan_option
@click.argument("name")
@click.argument("path", type=click.Path(path_type=Path))
@click.pass_context
def category_root(ctx: click.Context, plan_path: Path, name: str, path: Path) -> None:
    """Override a category's scan root (journaled)."""
    plan = _load(plan_path)
    try:
        before = plan.category(name).get("root")
    except _plan.PlanError as exc:
        raise click.ClickException(str(exc))
    action = {"op": "category.root", "category": name, "before": before, "after": str(path)}
    _mutate(ctx, plan_path, action, [f"{name} root set to {path}"])


# --- scan (read-only probes) --------------------------------------------------


@cli.group()
def scan() -> None:
    """Read-only size probes of the plan's categories (never deletes)."""


@scan.command("run")
@_plan_option
@click.option("-c", "--category", "only", default=None, help="Scan one category only.")
@click.pass_context
def scan_run(ctx: click.Context, plan_path: Path, only: str | None) -> None:
    """Probe enabled categories and snapshot sizes into the plan (journaled)."""
    plan = _load(plan_path)
    try:
        snapshot = _scanner.run_scan(plan, only=only)
    except _plan.PlanError as exc:
        raise click.ClickException(str(exc))
    action = {"op": "scan.run", "before": plan.last_scan, "after": snapshot}
    _plan.apply_action(plan, action)
    _plan.save_plan(plan, plan_path)
    _session.record_action(plan_path, action)
    human = [
        f"{name:<16} {_scanner.human_bytes(c['bytes']):>10}  "
        f"{c['files']} file(s)" + (f", {c['skipped']} skipped" if c["skipped"] else "")
        for name, c in snapshot["categories"].items()
    ]
    human.append(f"total: {_scanner.human_bytes(snapshot['total_bytes'])}")
    _emit(ctx, snapshot, human)


@scan.command("report")
@_plan_option
@click.pass_context
def scan_report(ctx: click.Context, plan_path: Path) -> None:
    """Show the plan's last scan snapshot."""
    plan = _load(plan_path)
    if not plan.last_scan:
        raise click.ClickException("no scan recorded yet (run: scan run)")
    snapshot = plan.last_scan
    human = [f"scanned_at: {snapshot.get('scanned_at')}"]
    for name, c in snapshot.get("categories", {}).items():
        human.append(f"{name:<16} {_scanner.human_bytes(c['bytes']):>10}  {c['files']} file(s)")
    human.append(f"total: {_scanner.human_bytes(snapshot.get('total_bytes', 0))}")
    _emit(ctx, snapshot, human)


# --- prefs (live app defaults domain) ----------------------------------------


@cli.group()
def prefs() -> None:
    """Read/write BuhoCleaner's live preference domain."""


@prefs.command("show")
@click.pass_context
def prefs_show(ctx: click.Context) -> None:
    """Dump the com.drbuho.BuhoCleaner defaults domain."""
    values = _backend_call(_backend.read_prefs)
    _emit(
        ctx,
        {"domain": _backend.BUNDLE_ID, "keys": values},
        [f"{key}: {value}" for key, value in values.items()],
    )


@prefs.command("set")
@_plan_option
@click.argument("key")
@click.argument("value")
@click.option("--type", "value_type", default="bool", show_default=True,
              type=click.Choice(["bool", "int", "string"]))
@click.pass_context
def prefs_set(ctx: click.Context, plan_path: Path, key: str, value: str, value_type: str) -> None:
    """Write one whitelisted toggle key (journaled; undo restores it)."""
    before = _backend_call(_backend.read_pref, key)
    _backend_call(_backend.write_pref, key, value, value_type)
    action = {"op": "prefs.set", "key": key, "type": value_type,
              "before": before, "after": value}
    _session.record_action(plan_path, action)
    _emit(ctx, {"action": action}, [f"{key} = {value} ({value_type})"])


@prefs.command("sync")
@_plan_option
@click.pass_context
def prefs_sync(ctx: click.Context, plan_path: Path) -> None:
    """Push the plan's category toggles into the app's defaults (journaled)."""
    plan = _load(plan_path)
    writes = []
    for name, spec in _plan.CATEGORIES.items():
        key = spec["defaults_key"]
        if key is None:
            continue
        enabled = plan.categories.get(name, {}).get("enabled", True)
        before = _backend_call(_backend.read_pref, key)
        _backend_call(_backend.write_pref, key, "true" if enabled else "false", "bool")
        writes.append({"key": key, "before": before, "after": enabled})
    action = {"op": "prefs.sync", "writes": writes}
    _session.record_action(plan_path, action)
    _emit(
        ctx,
        {"synced": writes},
        [f"{w['key']} -> {w['after']}" for w in writes] + [f"{len(writes)} key(s) synced"],
    )


# --- clean / uninstall (real app hand-off) -----------------------------------


@cli.group()
def clean() -> None:
    """Hand cleaning to the real BuhoCleaner app (human confirms there)."""


@clean.command("open")
@_plan_option
@click.option("--sync/--no-sync", default=True, show_default=True,
              help="Push plan toggles into app prefs before launching.")
@click.pass_context
def clean_open(ctx: click.Context, plan_path: Path, sync: bool) -> None:
    """Optionally sync prefs from the plan, then launch BuhoCleaner."""
    plan = _load(plan_path)
    synced = 0
    if sync:
        for name, spec in _plan.CATEGORIES.items():
            key = spec["defaults_key"]
            if key is None:
                continue
            enabled = plan.categories.get(name, {}).get("enabled", True)
            _backend_call(_backend.write_pref, key, "true" if enabled else "false", "bool")
            synced += 1
    _backend_call(_backend.launch)
    _emit(
        ctx,
        {"launched": True, "prefs_synced": synced},
        [f"synced {synced} toggle(s), launched BuhoCleaner — confirm cleaning in the app"],
    )


@clean.command("status")
@click.pass_context
def clean_status(ctx: click.Context) -> None:
    """Read the live BuhoCleaner window (buttons, found-junk summary)."""
    snap = _backend_call(_backend.ui_snapshot)
    human = [f"found_junk: {snap['found_junk'] or '(no scan visible)'}"]
    human.append("buttons: " + (", ".join(snap["buttons"]) or "(none)"))
    _emit(ctx, snap, human)


@clean.command("scan")
@click.pass_context
def clean_scan(ctx: click.Context) -> None:
    """Drive a Flash Clean scan in the real app and report found junk.

    Non-destructive: never presses Remove.
    """
    result = _backend_call(_backend.flash_clean, confirm=False)
    _emit(
        ctx,
        result,
        [f"found junk: {result['found_junk'] or 'unknown — check the app window'}"],
    )


@clean.command("run")
@click.option("--confirm", is_flag=True,
              help="Actually press Remove. Without this flag only a scan runs.")
@click.option("-p", "--plan", "plan_path", default=None,
              type=click.Path(path_type=Path),
              help="Optional plan file to record the outcome in (journaled).")
@click.pass_context
def clean_run(ctx: click.Context, confirm: bool, plan_path: Path | None) -> None:
    """Run Flash Clean in the real app via GUI automation.

    DESTRUCTIVE with --confirm: BuhoCleaner deletes the files selected in
    its window. Without --confirm this scans and reports, then stops.
    """
    result = _backend_call(_backend.flash_clean, confirm=confirm)
    if plan_path is not None:
        plan = _load(plan_path)
        action = {
            "op": "clean.result",
            "before": plan.metadata.get("last_clean"),
            "after": result,
        }
        _plan.apply_action(plan, action)
        _plan.save_plan(plan, plan_path)
        _session.record_action(plan_path, action)
    if result["removed"]:
        human = [f"cleaned: removed {result['found_junk'] or 'selected junk'} via BuhoCleaner"]
    else:
        human = [
            f"scan only: found {result['found_junk'] or 'unknown'} — "
            "re-run with --confirm to remove",
        ]
    _emit(ctx, result, human)


@cli.group()
def uninstall() -> None:
    """Hand an app bundle to BuhoCleaner's uninstaller."""


@uninstall.command("open")
@click.argument("app_path", type=click.Path(path_type=Path))
@click.pass_context
def uninstall_open(ctx: click.Context, app_path: Path) -> None:
    """Open APP_PATH in BuhoCleaner's uninstaller (human confirms there)."""
    _backend_call(_backend.open_uninstaller, app_path)
    _emit(
        ctx,
        {"handed_off": str(app_path)},
        [f"handed {app_path} to BuhoCleaner's uninstaller"],
    )


# --- session -----------------------------------------------------------------


@cli.group()
def session() -> None:
    """Undo/redo journal and session status."""


@session.command("status")
@_plan_option
@click.pass_context
def session_status_cmd(ctx: click.Context, plan_path: Path) -> None:
    """Show undo/redo depths and session file location."""
    status = _session.session_status(plan_path)
    _emit(ctx, status, [f"{key}: {value}" for key, value in status.items()])


def _revert_action(plan_path: Path, action: dict, invert: bool) -> str:
    """Apply a journaled action forwards (redo) or backwards (undo)."""
    op = action.get("op", "")
    if op == "prefs.set":
        value = action["before"] if invert else action["after"]
        if value is None:
            value = "false" if action["type"] == "bool" else ("0" if action["type"] == "int" else "")
        _backend_call(_backend.write_pref, action["key"], value, action["type"])
        return f"{action['key']} restored to {value}"
    if op == "prefs.sync":
        for write in action.get("writes", []):
            if invert:
                value = write["before"] if write["before"] is not None else "false"
            else:
                value = "true" if write["after"] else "false"
            _backend_call(_backend.write_pref, write["key"], value, "bool")
        return f"{len(action.get('writes', []))} pref key(s) {'restored' if invert else 're-applied'}"
    plan = _load(plan_path)
    try:
        _plan.apply_action(plan, action, invert=invert)
    except _plan.PlanError as exc:
        raise click.ClickException(str(exc))
    _plan.save_plan(plan, plan_path)
    return f"{op}"


@session.command("undo")
@_plan_option
@click.pass_context
def session_undo(ctx: click.Context, plan_path: Path) -> None:
    """Undo the most recent journaled mutation."""
    action = _session.pop_undo(plan_path)
    if action is None:
        raise click.ClickException("nothing to undo")
    detail = _revert_action(plan_path, action, invert=True)
    _emit(ctx, {"undone": action}, [f"undid {action['op']} ({detail})"])


@session.command("redo")
@_plan_option
@click.pass_context
def session_redo(ctx: click.Context, plan_path: Path) -> None:
    """Redo the most recently undone mutation."""
    action = _session.pop_redo(plan_path)
    if action is None:
        raise click.ClickException("nothing to redo")
    detail = _revert_action(plan_path, action, invert=False)
    _emit(ctx, {"redone": action}, [f"redid {action['op']} ({detail})"])


# --- preview (producer) ------------------------------------------------------


@cli.group()
def preview() -> None:
    """Produce preview bundles (view them with `cli-it previews`)."""


@preview.command("recipes")
@click.pass_context
def preview_recipes(ctx: click.Context) -> None:
    """List available preview recipes."""
    recipes = [{"name": "scan-report", "description": "Text+JSON report of the last scan snapshot"}]
    _emit(ctx, {"recipes": recipes}, [f"{r['name']} — {r['description']}" for r in recipes])


@preview.command("capture")
@_plan_option
@click.option("-r", "--recipe", default="scan-report", show_default=True)
@click.option("--root", "root_dir", type=click.Path(path_type=Path), default=None,
              help="Override the previews root (default ~/.cli-it/previews).")
@click.pass_context
def preview_capture(ctx: click.Context, plan_path: Path, recipe: str, root_dir: Path | None) -> None:
    """Write the last scan snapshot into a preview bundle and print its path."""
    if recipe != "scan-report":
        raise click.ClickException(f"unknown recipe '{recipe}' (try: preview recipes)")
    plan = _load(plan_path)
    if not plan.last_scan:
        raise click.ClickException("no scan recorded yet (run: scan run)")
    snapshot = plan.last_scan
    bundle = _preview.prepare_bundle(
        "buhocleaner",
        recipe,
        inputs={"plan": str(plan_path.resolve()), "scanned_at": snapshot.get("scanned_at")},
        root_dir=root_dir,
    )
    lines = [f"BuhoCleaner scan report — plan: {plan.name}", "=" * 44]
    for name, c in snapshot.get("categories", {}).items():
        lines.append(f"{name:<16} {_scanner.human_bytes(c['bytes']):>10}  {c['files']} file(s)")
    lines.append(f"total: {_scanner.human_bytes(snapshot.get('total_bytes', 0))}")
    (bundle / "artifacts" / "report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (bundle / "artifacts" / "report.json").write_text(
        json.dumps(snapshot, indent=2), encoding="utf-8"
    )
    _preview.finalize_bundle(
        bundle,
        summary={"plan": plan.name, "total_bytes": snapshot.get("total_bytes", 0)},
    )
    _emit(ctx, {"bundle": str(bundle)}, [str(bundle)])


@preview.command("latest")
@click.option("-r", "--recipe", default="scan-report", show_default=True)
@click.option("--root", "root_dir", type=click.Path(path_type=Path), default=None)
@click.pass_context
def preview_latest(ctx: click.Context, recipe: str, root_dir: Path | None) -> None:
    """Print the newest bundle path for a recipe."""
    bundle = _preview.bundle_root("buhocleaner", recipe, root_dir=root_dir)
    if not (bundle / "manifest.json").is_file():
        raise click.ClickException(f"no bundle captured yet for recipe '{recipe}'")
    _emit(ctx, {"bundle": str(bundle)}, [str(bundle)])


# --- REPL --------------------------------------------------------------------

_REPL_COMMANDS = {
    "backend / app info|launch|quit|update-check": "probe & control the real app",
    "plan new|info|save": "manage cleanup-plan files",
    "category list|enable|disable|threshold|root": "undoable plan mutations",
    "scan run|report": "read-only size probes",
    "prefs show|set|sync": "live app defaults domain",
    "clean status|scan|run [--confirm]": "GUI-driven clean (destructive w/ --confirm)",
    "clean open / uninstall open": "hand off to the real BuhoCleaner",
    "session status|undo|redo": "journal control",
    "preview capture|recipes|latest": "produce preview bundles",
    "help / exit": "this help / leave the REPL",
}


def _run_repl() -> None:
    skin = ReplSkin("buhocleaner", __version__)
    skin.print_banner()
    prompt = skin.create_prompt_session()
    while True:
        try:
            line = prompt("buhocleaner> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line in ("exit", "quit"):
            break
        if line == "help":
            skin.help(_REPL_COMMANDS)
            continue
        try:
            cli.main(
                args=shlex.split(line),
                prog_name="cli-it-buhocleaner",
                standalone_mode=False,
            )
        except click.ClickException as exc:
            skin.error(exc.format_message())
        except click.exceptions.Abort:
            skin.warning("aborted")
        except ValueError as exc:
            skin.error(str(exc))
    skin.print_goodbye()


if __name__ == "__main__":
    cli()
