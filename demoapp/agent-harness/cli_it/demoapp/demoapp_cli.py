"""DemoApp harness CLI — the reference CLI-It command surface.

Dual mode: `cli-it-demoapp` with no subcommand starts a ReplSkin REPL; any
subcommand runs one-shot. The root `--json` flag switches output to
machine-readable JSON on stdout.
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path

import click

from cli_it.demoapp import __version__
from cli_it.demoapp.core import project as _project
from cli_it.demoapp.core import session as _session
from cli_it.demoapp.utils import demoapp_backend as _backend
from cli_it.demoapp.utils import preview_bundle as _preview
from cli_it.demoapp.utils.repl_skin import ReplSkin

_project_option = click.option(
    "-p",
    "--project",
    "project_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Path to the project JSON file.",
)


def _emit(ctx: click.Context, data: dict, human: list[str]) -> None:
    if (ctx.obj or {}).get("json"):
        click.echo(json.dumps(data, indent=2))
    else:
        for line in human:
            click.echo(line)


def _load(project_path: Path) -> _project.Project:
    try:
        return _project.load_project(project_path)
    except _project.ProjectError as exc:
        raise click.ClickException(str(exc))


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="cli-it-demoapp")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@click.pass_context
def cli(ctx: click.Context, as_json: bool) -> None:
    """DemoApp — exemplar CLI-It harness (REPL when no subcommand)."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = as_json
    if ctx.invoked_subcommand is None:
        _run_repl()


# --- project ----------------------------------------------------------------


@cli.group()
def project() -> None:
    """Create, open, save, and inspect DemoApp projects."""


@project.command("new")
@click.option("-n", "--name", default="untitled", help="Project name.")
@click.option(
    "-o",
    "--output",
    "output_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Where to write the project JSON.",
)
@click.pass_context
def project_new(ctx: click.Context, name: str, output_path: Path) -> None:
    """Create a new project file."""
    if output_path.exists():
        raise click.ClickException(f"refusing to overwrite existing file: {output_path}")
    proj = _project.new_project(name)
    _project.save_project(proj, output_path)
    _session.update_session(output_path, lambda s: s)  # initialize session file
    info = _project.project_info(proj, output_path)
    _emit(ctx, info, [f"created project '{name}' at {output_path}"])


@project.command("open")
@_project_option
@click.pass_context
def project_open(ctx: click.Context, project_path: Path) -> None:
    """Validate a project and ensure its session exists."""
    proj = _load(project_path)
    _session.update_session(project_path, lambda s: s)
    info = _project.project_info(proj, project_path)
    info["session"] = _session.session_status(project_path)
    _emit(
        ctx,
        info,
        [
            f"opened '{proj.name}' ({len(proj.items)} items)",
            f"session: {info['session']['session_file']}",
        ],
    )


@project.command("info")
@_project_option
@click.pass_context
def project_info_cmd(ctx: click.Context, project_path: Path) -> None:
    """Show project details."""
    proj = _load(project_path)
    info = _project.project_info(proj, project_path)
    _emit(
        ctx,
        info,
        [f"{key}: {value}" for key, value in info.items()],
    )


@project.command("save")
@_project_option
@click.pass_context
def project_save(ctx: click.Context, project_path: Path) -> None:
    """Re-save a project canonically (validates + normalizes formatting)."""
    proj = _load(project_path)
    _project.save_project(proj, project_path)
    _emit(
        ctx,
        {"path": str(project_path), "saved": True},
        [f"saved {project_path}"],
    )


# --- item (mutations, journaled for undo/redo) -------------------------------


@cli.group()
def item() -> None:
    """Add, list, and remove project items (undoable mutations)."""


@item.command("add")
@_project_option
@click.option("-n", "--name", required=True, help="Item name.")
@click.option("-k", "--kind", default="note", show_default=True, help="Item kind.")
@click.pass_context
def item_add(ctx: click.Context, project_path: Path, name: str, kind: str) -> None:
    """Add an item to the project (auto-saves, journaled)."""
    proj = _load(project_path)
    new_item = {"id": proj.next_item_id(), "name": name, "kind": kind}
    action = {"op": "item.add", "item": new_item}
    _project.apply_action(proj, action)
    _project.save_project(proj, project_path)
    _session.record_action(project_path, action)
    _emit(
        ctx,
        {"added": new_item, "items": len(proj.items)},
        [f"added item [{new_item['id']}] {kind}: {name}"],
    )


@item.command("list")
@_project_option
@click.pass_context
def item_list(ctx: click.Context, project_path: Path) -> None:
    """List project items."""
    proj = _load(project_path)
    _emit(
        ctx,
        {"items": proj.items},
        [f"[{i.get('id')}] {i.get('kind')}: {i.get('name')}" for i in proj.items]
        or ["(no items)"],
    )


@item.command("remove")
@_project_option
@click.option("-i", "--id", "item_id", required=True, type=int, help="Item id.")
@click.pass_context
def item_remove(ctx: click.Context, project_path: Path, item_id: int) -> None:
    """Remove an item by id (auto-saves, journaled)."""
    proj = _load(project_path)
    target = next((i for i in proj.items if i.get("id") == item_id), None)
    if target is None:
        raise click.ClickException(f"no item with id {item_id}")
    action = {"op": "item.remove", "item": target}
    _project.apply_action(proj, action)
    _project.save_project(proj, project_path)
    _session.record_action(project_path, action)
    _emit(
        ctx,
        {"removed": target, "items": len(proj.items)},
        [f"removed item [{item_id}] {target.get('name')}"],
    )


# --- session ----------------------------------------------------------------


@cli.group()
def session() -> None:
    """Undo/redo journal and session status."""


@session.command("status")
@_project_option
@click.pass_context
def session_status_cmd(ctx: click.Context, project_path: Path) -> None:
    """Show undo/redo depths and session file location."""
    status = _session.session_status(project_path)
    _emit(ctx, status, [f"{key}: {value}" for key, value in status.items()])


@session.command("undo")
@_project_option
@click.pass_context
def session_undo(ctx: click.Context, project_path: Path) -> None:
    """Undo the most recent journaled mutation."""
    action = _session.pop_undo(project_path)
    if action is None:
        raise click.ClickException("nothing to undo")
    proj = _load(project_path)
    _project.apply_action(proj, action, invert=True)
    _project.save_project(proj, project_path)
    _emit(
        ctx,
        {"undone": action, "items": len(proj.items)},
        [f"undid {action['op']} ({action['item'].get('name')})"],
    )


@session.command("redo")
@_project_option
@click.pass_context
def session_redo(ctx: click.Context, project_path: Path) -> None:
    """Redo the most recently undone mutation."""
    action = _session.pop_redo(project_path)
    if action is None:
        raise click.ClickException("nothing to redo")
    proj = _load(project_path)
    _project.apply_action(proj, action)
    _project.save_project(proj, project_path)
    _emit(
        ctx,
        {"redone": action, "items": len(proj.items)},
        [f"redid {action['op']} ({action['item'].get('name')})"],
    )


# --- export (real engine) ----------------------------------------------------


@cli.group()
def export() -> None:
    """Render the project with the real DemoApp engine."""


@export.command("run")
@_project_option
@click.option(
    "-o",
    "--output",
    "output_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Rendered output file.",
)
@click.option(
    "-f",
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
@click.pass_context
def export_run(ctx: click.Context, project_path: Path, output_path: Path, fmt: str) -> None:
    """Render the project to a file via the external engine process."""
    _load(project_path)  # validate before invoking the engine
    try:
        rendered = _backend.render_project(project_path, output_path, fmt=fmt)
    except _backend.BackendError as exc:
        raise click.ClickException(str(exc))
    _emit(
        ctx,
        {"output": str(rendered), "format": fmt, "bytes": rendered.stat().st_size},
        [f"rendered {fmt} → {rendered}"],
    )


@cli.command("backend")
@click.pass_context
def backend_cmd(ctx: click.Context) -> None:
    """Probe the DemoApp engine backend."""
    info = _backend.probe()
    _emit(ctx, info, [f"{key}: {value}" for key, value in info.items()])


# --- preview (producer) ------------------------------------------------------


@cli.group()
def preview() -> None:
    """Produce preview bundles (view them with `cli-it previews`)."""


@preview.command("recipes")
@click.pass_context
def preview_recipes(ctx: click.Context) -> None:
    """List available preview recipes."""
    recipes = [{"name": "render", "description": "Full text+json render of the project"}]
    _emit(ctx, {"recipes": recipes}, [f"{r['name']} — {r['description']}" for r in recipes])


@preview.command("capture")
@_project_option
@click.option("-r", "--recipe", default="render", show_default=True)
@click.option(
    "--root",
    "root_dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Override the previews root (default ~/.cli-it/previews).",
)
@click.pass_context
def preview_capture(
    ctx: click.Context, project_path: Path, recipe: str, root_dir: Path | None
) -> None:
    """Render the project into a preview bundle and print its path."""
    if recipe != "render":
        raise click.ClickException(f"unknown recipe '{recipe}' (try: preview recipes)")
    proj = _load(project_path)
    bundle = _preview.prepare_bundle(
        "demoapp",
        recipe,
        inputs={"project": str(project_path.resolve()), "items": len(proj.items)},
        root_dir=root_dir,
    )
    try:
        _backend.render_project(project_path, bundle / "artifacts" / "render.txt", "text")
        _backend.render_project(project_path, bundle / "artifacts" / "render.json", "json")
    except _backend.BackendError as exc:
        raise click.ClickException(str(exc))
    _preview.finalize_bundle(
        bundle, summary={"project": proj.name, "items": len(proj.items)}
    )
    _emit(ctx, {"bundle": str(bundle)}, [str(bundle)])


@preview.command("latest")
@click.option("-r", "--recipe", default="render", show_default=True)
@click.option("--root", "root_dir", type=click.Path(path_type=Path), default=None)
@click.pass_context
def preview_latest(ctx: click.Context, recipe: str, root_dir: Path | None) -> None:
    """Print the newest bundle path for a recipe."""
    bundle = _preview.bundle_root("demoapp", recipe, root_dir=root_dir)
    if not (bundle / "manifest.json").is_file():
        raise click.ClickException(f"no bundle captured yet for recipe '{recipe}'")
    _emit(ctx, {"bundle": str(bundle)}, [str(bundle)])


# --- REPL -------------------------------------------------------------------

_REPL_COMMANDS = {
    "project new|open|info|save": "manage project files",
    "item add|list|remove": "undoable item mutations",
    "session status|undo|redo": "journal control",
    "export run": "render via the real engine",
    "preview capture|recipes|latest": "produce preview bundles",
    "help / exit": "this help / leave the REPL",
}


def _run_repl() -> None:
    skin = ReplSkin("demoapp", __version__)
    skin.print_banner()
    prompt = skin.create_prompt_session()
    while True:
        try:
            line = prompt("demoapp> ").strip()
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
                prog_name="cli-it-demoapp",
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
