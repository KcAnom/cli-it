"""`cli-it` — the CLI-It Hub command-line interface.

Exit codes (matrix family): 0 success, 1 failure/not found, 2 usage error,
3 partial success / capability gaps (agents may continue with partial tooling).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import click

from . import __version__, analytics
from . import installer as _installer
from . import matrix as _matrix
from . import matrix_skill as _matrix_skill
from . import preview as _preview
from . import registry as _registry

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_GAPS = 3


def _echo_json(data) -> None:
    click.echo(json.dumps(data, indent=2))


def _cli_row(entry: dict) -> str:
    installed = "✓" if entry["name"] in _installer.get_installed() else " "
    return (
        f"{installed} {entry.get('name', ''):<18} "
        f"{entry.get('version', ''):<10} "
        f"[{entry.get('_source', '?'):<7}] "
        f"{entry.get('category', ''):<18} "
        f"{entry.get('description', '')[:70]}"
    )


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="cli-it")
@click.pass_context
def main(ctx: click.Context) -> None:
    """CLI-It Hub — browse, install, and launch agent-native CLI harnesses."""
    if ctx.invoked_subcommand is None:
        analytics.track_visit()
        click.echo(ctx.get_help())


# --- registry commands -------------------------------------------------------


@main.command("list")
@click.option("-c", "--category", default=None, help="Filter by category.")
@click.option(
    "-s",
    "--source",
    type=click.Choice(["harness", "public", "npm", "all"]),
    default="all",
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
def list_cmd(category: str | None, source: str, as_json: bool) -> None:
    """List CLIs from the harness and public registries."""
    entries = _registry.fetch_all_clis()
    if category:
        entries = [e for e in entries if e.get("category") == category]
    if source == "npm":
        entries = [e for e in entries if e.get("package_manager") == "npm"]
    elif source != "all":
        entries = [e for e in entries if e.get("_source") == source]
    if as_json:
        _echo_json(entries)
        return
    if not entries:
        click.echo("No CLIs matched.")
        return
    for entry in entries:
        click.echo(_cli_row(entry))
    click.echo(f"\n{len(entries)} CLIs. Install with: cli-it install <name>")


@main.command()
@click.argument("query")
@click.option("--json", "as_json", is_flag=True)
def search(query: str, as_json: bool) -> None:
    """Search CLIs by name, description, or category."""
    hits = _registry.search_clis(query)
    if as_json:
        _echo_json(hits)
        return
    if not hits:
        click.echo(f"No CLIs match '{query}'.")
        sys.exit(EXIT_FAIL)
    for entry in hits:
        click.echo(_cli_row(entry))


@main.command()
@click.argument("name")
def info(name: str) -> None:
    """Show full registry details for one CLI."""
    entry = _registry.get_cli(name)
    if entry is None:
        click.echo(f"'{name}' not found in any registry.", err=True)
        sys.exit(EXIT_FAIL)
    _echo_json(entry)


@main.command()
@click.argument("name")
def install(name: str) -> None:
    """Install a CLI using its registry install command."""
    try:
        result = _installer.install_cli(name)
    except _installer.InstallError as exc:
        analytics.track_install(name, ok=False)
        click.echo(f"error: {exc}", err=True)
        sys.exit(EXIT_FAIL)
    analytics.track_install(name, ok=True)
    click.echo(f"Installed '{name}' via: {result['command']}")


@main.command()
@click.argument("name")
def uninstall(name: str) -> None:
    """Uninstall a hub-installed CLI."""
    result = _installer.uninstall_cli(name)
    analytics.track_uninstall(name)
    if result.get("note"):
        click.echo(result["note"])
    elif result["ok"]:
        click.echo(f"Uninstalled '{name}'.")
    else:
        click.echo(f"Uninstall command failed for '{name}'.", err=True)
        sys.exit(EXIT_FAIL)


@main.command()
@click.argument("name")
def update(name: str) -> None:
    """Update a CLI to the latest registry version."""
    try:
        result = _installer.update_cli(name)
    except _installer.InstallError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(EXIT_FAIL)
    click.echo(f"Updated '{name}' via: {result['command']}")


@main.command(context_settings={"ignore_unknown_options": True})
@click.argument("name")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def launch(name: str, args: tuple[str, ...]) -> None:
    """Launch an installed CLI by registry name, passing through ARGS."""
    entry = _registry.get_cli(name)
    entry_point = (entry or {}).get("entry_point") or name
    if shutil.which(entry_point) is None:
        click.echo(
            f"'{entry_point}' is not on PATH. Try: cli-it install {name}", err=True
        )
        sys.exit(EXIT_FAIL)
    analytics.track_launch(name)
    sys.exit(subprocess.run([entry_point, *args]).returncode)


@main.command()
@click.argument("query")
@click.option("--json", "as_json", is_flag=True)
def can(query: str, as_json: bool) -> None:
    """Ask the matrices: which capability answers QUERY, and with what tools?"""
    hits = _matrix.search_capabilities(query)
    results = []
    for hit in hits:
        providers = []
        for provider in hit.get("providers", []):
            check = _matrix.check_provider_requirements(provider)
            providers.append(
                {
                    "name": provider.get("name"),
                    "kind": provider.get("kind"),
                    "ready": check["ok"],
                    "install_hint": _matrix.provider_install_hint(provider),
                }
            )
        results.append(
            {
                "matrix": hit["_matrix"],
                "capability": hit.get("id"),
                "intent": hit.get("intent"),
                "providers": providers,
            }
        )
    if as_json:
        _echo_json(results)
        return
    if not results:
        click.echo(f"No capability matches '{query}'. Try: cli-it matrix list")
        sys.exit(EXIT_FAIL)
    for res in results:
        click.echo(f"{res['matrix']} :: {res['capability']} — {res['intent']}")
        for provider in res["providers"]:
            mark = "✓" if provider["ready"] else "✗"
            hint = (
                f"  (install: {provider['install_hint']})"
                if not provider["ready"] and provider["install_hint"]
                else ""
            )
            click.echo(f"  {mark} {provider['name']} [{provider['kind']}]{hint}")


# --- previews (consumer) -----------------------------------------------------


@main.group()
def previews() -> None:
    """Inspect and view preview bundles / live sessions (consumer only)."""


@previews.command("inspect")
@click.argument("ref")
@click.option("--json", "as_json", is_flag=True, default=True, hidden=True)
def previews_inspect(ref: str, as_json: bool) -> None:
    """Print structured info about a bundle or live session."""
    try:
        try:
            _echo_json(_preview.inspect_bundle(ref))
        except _preview.PreviewError:
            _echo_json(_preview.inspect_session(ref))
    except _preview.PreviewError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(EXIT_FAIL)


@previews.command("html")
@click.argument("ref")
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write HTML here (default: <bundle>/preview.html).",
)
def previews_html(ref: str, output: Path | None) -> None:
    """Render a bundle to a standalone HTML page."""
    try:
        bundle = _preview.resolve_bundle(ref)
        page = _preview.render_html(ref)
    except _preview.PreviewError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(EXIT_FAIL)
    target = output or bundle / "preview.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
    click.echo(str(target))


@previews.command("watch")
@click.argument("ref")
@click.option("--poll", default=2, show_default=True, help="Refresh seconds.")
@click.option("--no-browser", is_flag=True, help="Don't open a browser.")
def previews_watch(ref: str, poll: int, no_browser: bool) -> None:
    """Serve a live session with auto-refreshing HTML until interrupted."""
    try:
        session_dir = _preview.resolve_session(ref)
    except _preview.PreviewError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(EXIT_FAIL)
    page_path = session_dir / "live.html"
    page_path.write_text(_preview.render_live_html(ref, poll), encoding="utf-8")
    server, url = _preview.start_static_server(session_dir)
    full_url = url + "live.html"
    click.echo(f"Watching {session_dir}\nServing {full_url} (Ctrl+C to stop)")
    if not no_browser:
        _preview.open_in_browser(full_url)
    try:
        while True:
            time.sleep(poll)
            page_path.write_text(
                _preview.render_live_html(ref, poll), encoding="utf-8"
            )
    except KeyboardInterrupt:
        server.shutdown()


@previews.command("open")
@click.argument("ref")
@click.option("--no-browser", is_flag=True, help="Print the URL only.")
def previews_open(ref: str, no_browser: bool) -> None:
    """Render a bundle and open it in the default browser."""
    try:
        bundle = _preview.resolve_bundle(ref)
        page = _preview.render_html(ref)
    except _preview.PreviewError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(EXIT_FAIL)
    page_path = bundle / "preview.html"
    page_path.write_text(page, encoding="utf-8")
    server, url = _preview.start_static_server(bundle)
    full_url = url + "preview.html"
    click.echo(full_url)
    if not no_browser:
        _preview.open_in_browser(full_url)
        try:
            time.sleep(30)  # keep the server alive long enough to load
        except KeyboardInterrupt:
            pass
    server.shutdown()


# --- matrices ----------------------------------------------------------------


@main.group()
def matrix() -> None:
    """Capability matrices: list, preflight, install, doctor, recipes."""


def _require_matrix(name: str) -> dict:
    item = _matrix.get_matrix(name)
    if item is None:
        click.echo(f"matrix '{name}' not found. Try: cli-it matrix list", err=True)
        sys.exit(EXIT_FAIL)
    return item


@matrix.command("list")
@click.option("--json", "as_json", is_flag=True)
def matrix_list(as_json: bool) -> None:
    """List available matrices."""
    matrices = _matrix.fetch_all_matrices()
    if as_json:
        _echo_json(matrices)
        return
    for item in matrices:
        click.echo(
            f"{item.get('name', ''):<22} v{item.get('version', '?'):<8} "
            f"{len(item.get('capabilities', [])):>2} caps  "
            f"{item.get('description', '')[:70]}"
        )


@matrix.command("search")
@click.argument("query")
@click.option("--json", "as_json", is_flag=True)
def matrix_search(query: str, as_json: bool) -> None:
    """Search matrices by name/description/category."""
    hits = _matrix.search_matrices(query)
    if as_json:
        _echo_json(hits)
        return
    if not hits:
        click.echo(f"No matrices match '{query}'.")
        sys.exit(EXIT_FAIL)
    for item in hits:
        click.echo(f"{item.get('name')} — {item.get('description', '')}")


@matrix.command("info")
@click.argument("name")
def matrix_info(name: str) -> None:
    """Show a matrix's full definition."""
    _echo_json(_require_matrix(name))


@matrix.command("preflight")
@click.argument("name")
@click.option("-c", "--capability", default=None, help="Check one capability id.")
@click.option("--offline", is_flag=True, help="Exclude network-only providers.")
@click.option("--json", "as_json", is_flag=True)
def matrix_preflight(
    name: str, capability: str | None, offline: bool, as_json: bool
) -> None:
    """Check which capabilities are usable right now (exit 3 = gaps)."""
    item = _require_matrix(name)
    try:
        report = _matrix.preflight_matrix(
            item, capability_id=capability, offline=offline
        )
    except KeyError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(EXIT_FAIL)
    analytics.track_matrix("preflight", name, ok=report["ok"])
    if as_json:
        _echo_json(report)
    else:
        for cap in report["capabilities"]:
            mark = "✓" if cap["ready"] else "✗"
            click.echo(f"{mark} {cap['capability']} — {cap['intent']}")
            for provider in cap["providers"]:
                pmark = "✓" if provider.get("ok") else "✗"
                extra = ""
                if provider.get("skipped"):
                    extra = f" [{provider['skipped']}]"
                elif not provider.get("ok") and provider.get("install_hint"):
                    extra = f" (install: {provider['install_hint']})"
                click.echo(
                    f"    {pmark} {provider['name']} [{provider['kind']}]{extra}"
                )
        if report["gaps"]:
            click.echo(f"\nGaps: {', '.join(report['gaps'])}")
    sys.exit(EXIT_OK if report["ok"] else EXIT_GAPS)


@matrix.command("install")
@click.argument("name")
@click.option("-c", "--capability", default=None, help="Limit to a capability id.")
@click.option("-r", "--recipe", default=None, help="Limit to a recipe's capabilities.")
@click.option(
    "--only", multiple=True, help="Limit to specific provider names (repeatable)."
)
@click.option("--dry-run", is_flag=True, help="Print the plan; run nothing.")
@click.option("--resume", is_flag=True, help="Skip steps completed previously.")
@click.option("--json", "as_json", is_flag=True)
def matrix_install(
    name: str,
    capability: str | None,
    recipe: str | None,
    only: tuple[str, ...],
    dry_run: bool,
    resume: bool,
    as_json: bool,
) -> None:
    """Install a matrix's installable tooling (exit 3 = agent actions remain)."""
    item = _require_matrix(name)
    try:
        summary = _installer.install_matrix(
            item,
            capability=capability,
            recipe=recipe,
            only=list(only) or None,
            dry_run=dry_run,
            resume=resume,
        )
    except KeyError as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(EXIT_FAIL)
    analytics.track_matrix("install", name, ok=summary["ok"])
    if as_json:
        _echo_json(summary)
    else:
        for step in summary["installed"]:
            verb = "would run" if step.get("dry_run") else "ran"
            click.echo(f"+ {step['name']}: {verb} `{step['command']}`")
        for step_name in summary["skipped"]:
            click.echo(f"= {step_name}: already satisfied")
        for action in summary["agent_actions"]:
            click.echo(f"! {action['name']}: agent action — {action['hint']}")
        for failure in summary["failed"]:
            click.echo(
                f"x {failure['name']}: rc={failure['rc']} `{failure['command']}`",
                err=True,
            )
    if summary["failed"]:
        sys.exit(EXIT_FAIL)
    sys.exit(EXIT_GAPS if summary["agent_actions"] else EXIT_OK)


@matrix.command("doctor")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True)
def matrix_doctor(name: str, as_json: bool) -> None:
    """Diagnose matrix health and print remediation hints (exit 3 = gaps)."""
    item = _require_matrix(name)
    report = _installer.doctor_matrix(item)
    analytics.track_matrix("doctor", name, ok=report["ok"])
    if as_json:
        _echo_json(report)
    else:
        status = "healthy" if report["ok"] else f"gaps: {', '.join(report['gaps'])}"
        click.echo(f"{name}: {status}")
        for remedy in report["remedies"]:
            click.echo(
                f"  {remedy['capability']} → {remedy['provider']}: {remedy['hint']}"
            )
    sys.exit(EXIT_OK if report["ok"] else EXIT_GAPS)


@matrix.command("recipes")
@click.option("--json", "as_json", is_flag=True)
def matrix_recipes(as_json: bool) -> None:
    """List recipes across all matrices."""
    recipes = _matrix.all_recipes()
    if as_json:
        _echo_json(recipes)
        return
    for recipe in recipes:
        click.echo(
            f"{recipe['_matrix']} :: {recipe.get('name')} — "
            f"{recipe.get('description', '')} "
            f"[{', '.join(recipe.get('capabilities', []))}]"
        )


@matrix.command("skill")
@click.argument("name")
def matrix_skill_cmd(name: str) -> None:
    """Render a matrix's SKILL.md (with local tooling status) to ~/.cli-it-hub."""
    item = _require_matrix(name)
    try:
        path = _matrix_skill.render_matrix_skill_file(
            item, installed=_installer.get_installed()
        )
    except (FileNotFoundError, OSError) as exc:
        click.echo(f"error: {exc}", err=True)
        sys.exit(EXIT_FAIL)
    analytics.track_matrix("skill", name)
    click.echo(str(path))


if __name__ == "__main__":
    main()
