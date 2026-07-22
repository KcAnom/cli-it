"""Repomix harness CLI — agent-native command surface.

Dual mode: `cli-it-repomix` with no subcommand starts a ReplSkin REPL; any
subcommand runs one-shot. The root `--json` flag switches output to
machine-readable JSON on stdout.

The harness never packs anything itself: every pack, token count, security
scan, and skill generation is performed by the real repomix binary through
`utils/repomix_backend.py`. What the harness adds is persistent pack profiles,
an undo journal, verified artifacts, and stable JSON.
"""

from __future__ import annotations

import json
import shlex
import tempfile
from pathlib import Path

import click

from cli_it.repomix import __version__
from cli_it.repomix.core import profile as _profile
from cli_it.repomix.core import session as _session
from cli_it.repomix.utils import preview_bundle as _preview
from cli_it.repomix.utils import repomix_backend as _backend
from cli_it.repomix.utils.repl_skin import ReplSkin

_profile_option = click.option(
    "-p",
    "--profile",
    "profile_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Path to the pack-profile JSON file.",
)

_cwd_option = click.option(
    "--cwd",
    "cwd",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help="Directory to run repomix from (default: current directory).",
)


def _emit(ctx: click.Context, data: dict, human: list[str]) -> None:
    if (ctx.obj or {}).get("json"):
        click.echo(json.dumps(data, indent=2))
    else:
        for line in human:
            click.echo(line)


def _load(profile_path: Path) -> _profile.Profile:
    try:
        return _profile.load_profile(profile_path)
    except _profile.ProfileError as exc:
        raise click.ClickException(str(exc))


def _backend_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except _backend.BackendError as exc:
        raise click.ClickException(str(exc))


def _mutate(ctx: click.Context, profile_path: Path, action: dict, human: list[str]) -> None:
    """Apply a profile action, save, journal, emit (auto-save by default)."""
    profile = _load(profile_path)
    try:
        _profile.apply_action(profile, action)
    except _profile.ProfileError as exc:
        raise click.ClickException(str(exc))
    _profile.save_profile(profile, profile_path)
    _session.record_action(profile_path, action)
    _emit(ctx, {"action": action}, human)


def _scratch_output(profile: _profile.Profile) -> str:
    """A throwaway output path for read-only analyses that still must write."""
    suffix = Path(profile.output).suffix or ".xml"
    handle = tempfile.NamedTemporaryFile(prefix="cli-it-repomix-", suffix=suffix, delete=False)
    handle.close()
    return handle.name


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="cli-it-repomix")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
@click.pass_context
def cli(ctx: click.Context, as_json: bool) -> None:
    """Repomix agent harness (REPL when no subcommand)."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = as_json
    if ctx.invoked_subcommand is None:
        _run_repl()


@cli.command("backend")
@click.pass_context
def backend_cmd(ctx: click.Context) -> None:
    """Probe the real repomix installation."""
    info = _backend.probe()
    _emit(ctx, info, [f"{key}: {value}" for key, value in info.items()])


# --- profile -----------------------------------------------------------------


@cli.group("profile")
def profile_group() -> None:
    """Create and inspect pack-profile files."""


@profile_group.command("new")
@click.option("-n", "--name", default="pack", help="Profile name.")
@click.option(
    "-t",
    "--target",
    "targets",
    multiple=True,
    help="Directory to pack (repeatable; default '.').",
)
@click.option(
    "-o",
    "--output",
    "output_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Where to write the profile JSON.",
)
@click.pass_context
def profile_new(ctx: click.Context, name: str, targets: tuple[str, ...], output_path: Path) -> None:
    """Create a new pack profile with repomix defaults."""
    if output_path.exists():
        raise click.ClickException(f"refusing to overwrite existing file: {output_path}")
    profile = _profile.new_profile(name, list(targets) or None)
    _profile.save_profile(profile, output_path)
    _session.update_session(output_path, lambda s: s)  # initialize session file
    _emit(
        ctx,
        _profile.profile_info(profile, output_path),
        [f"created profile '{name}' at {output_path}"],
    )


@profile_group.command("info")
@_profile_option
@click.pass_context
def profile_info_cmd(ctx: click.Context, profile_path: Path) -> None:
    """Show profile details."""
    profile = _load(profile_path)
    info = _profile.profile_info(profile, profile_path)
    _emit(ctx, info, [f"{key}: {value}" for key, value in info.items()])


@profile_group.command("save")
@_profile_option
@click.pass_context
def profile_save(ctx: click.Context, profile_path: Path) -> None:
    """Re-save a profile canonically (validates + normalizes formatting)."""
    profile = _load(profile_path)
    _profile.save_profile(profile, profile_path)
    _emit(ctx, {"path": str(profile_path), "saved": True}, [f"saved {profile_path}"])


# --- target (journaled) ------------------------------------------------------


@cli.group()
def target() -> None:
    """Set what gets packed: local directories or a remote repository."""


@target.command("show")
@_profile_option
@click.pass_context
def target_show(ctx: click.Context, profile_path: Path) -> None:
    """Show the current pack target."""
    profile = _load(profile_path)
    data = {
        "targets": profile.targets,
        "remote": profile.remote,
        "remote_branch": profile.remote_branch,
    }
    human = (
        [f"remote: {profile.remote}" + (f" @ {profile.remote_branch}" if profile.remote_branch else "")]
        if profile.remote
        else [f"targets: {', '.join(profile.targets)}"]
    )
    _emit(ctx, data, human)


@target.command("set")
@_profile_option
@click.option("-t", "--target", "targets", multiple=True, help="Local directory (repeatable).")
@click.option("-r", "--remote", default=None, help="GitHub URL or user/repo to pack instead.")
@click.option("-b", "--branch", default=None, help="Remote branch, tag, or commit.")
@click.pass_context
def target_set(
    ctx: click.Context,
    profile_path: Path,
    targets: tuple[str, ...],
    remote: str | None,
    branch: str | None,
) -> None:
    """Point the profile at directories or a remote repo (undoable)."""
    if not targets and not remote:
        raise click.ClickException("give at least one --target or a --remote")
    if targets and remote:
        raise click.ClickException("--target and --remote are mutually exclusive")
    action = {
        "op": "target.set",
        "targets": list(targets),
        "remote": remote,
        "remote_branch": branch if remote else None,
    }
    described = remote or ", ".join(targets)
    _mutate(ctx, profile_path, action, [f"target set to {described}"])


# --- filter (journaled) ------------------------------------------------------


# `filter` shadows a builtin, so the function is `filter_` and the group is
# named explicitly.
@cli.group("filter")
def filter_() -> None:
    """Manage include/ignore glob patterns."""


@filter_.command("list")
@_profile_option
@click.pass_context
def filter_list(ctx: click.Context, profile_path: Path) -> None:
    """List include and ignore patterns."""
    profile = _load(profile_path)
    data = {"include": profile.include, "ignore": profile.ignore}
    human = [f"include: {p}" for p in profile.include] + [
        f"ignore:  {p}" for p in profile.ignore
    ] or ["no patterns set (repomix defaults + .gitignore apply)"]
    _emit(ctx, data, human)


@filter_.command("add")
@_profile_option
@click.option(
    "-k",
    "--kind",
    type=click.Choice(_profile.FILTER_KINDS),
    default="include",
    show_default=True,
)
@click.argument("pattern")
@click.pass_context
def filter_add(ctx: click.Context, profile_path: Path, kind: str, pattern: str) -> None:
    """Add a glob PATTERN to the include or ignore list (undoable)."""
    action = {"op": "filter.add", "kind": kind, "pattern": pattern}
    _mutate(ctx, profile_path, action, [f"added {kind} pattern: {pattern}"])


@filter_.command("remove")
@_profile_option
@click.option(
    "-k",
    "--kind",
    type=click.Choice(_profile.FILTER_KINDS),
    default="include",
    show_default=True,
)
@click.argument("pattern")
@click.pass_context
def filter_remove(ctx: click.Context, profile_path: Path, kind: str, pattern: str) -> None:
    """Remove a glob PATTERN from the include or ignore list (undoable)."""
    action = {"op": "filter.remove", "kind": kind, "pattern": pattern}
    _mutate(ctx, profile_path, action, [f"removed {kind} pattern: {pattern}"])


# --- option (journaled) ------------------------------------------------------


@cli.group()
def option() -> None:
    """Set output style, compression, and cost-guard settings."""


@option.command("list")
@_profile_option
@click.pass_context
def option_list(ctx: click.Context, profile_path: Path) -> None:
    """List every settable option with its current value."""
    profile = _load(profile_path)
    data = {
        "booleans": {key: bool(profile.options.get(key)) for key in _profile.BOOL_OPTIONS},
        "scalars": {key: getattr(profile, key) for key in _profile.SCALAR_OPTIONS},
    }
    human = [f"{key:<34} {value}" for key, value in data["booleans"].items()]
    human += [f"{key:<34} {value}" for key, value in data["scalars"].items()]
    _emit(ctx, data, human)


@option.command("set")
@_profile_option
@click.argument("key")
@click.argument("value")
@click.pass_context
def option_set(ctx: click.Context, profile_path: Path, key: str, value: str) -> None:
    """Set option KEY to VALUE (undoable).

    Booleans accept true/false; scalars take their literal value.
    """
    if key in _profile.BOOL_OPTIONS:
        lowered = value.strip().lower()
        if lowered not in ("true", "false", "1", "0", "yes", "no", "on", "off"):
            raise click.ClickException(f"{key} is a boolean — use true or false")
        parsed: object = lowered in ("true", "1", "yes", "on")
    elif key in _profile.SCALAR_OPTIONS:
        parsed = value
    else:
        known = ", ".join(sorted([*_profile.BOOL_OPTIONS, *_profile.SCALAR_OPTIONS]))
        raise click.ClickException(f"unknown option {key!r}. Known options: {known}")
    action = {"op": "option.set", "key": key, "value": parsed}
    _mutate(ctx, profile_path, action, [f"{key} = {parsed}"])


# --- pack (real repomix) -----------------------------------------------------


@cli.group()
def pack() -> None:
    """Run the real repomix and verify what it produced."""


@pack.command("argv")
@_profile_option
@click.pass_context
def pack_argv(ctx: click.Context, profile_path: Path) -> None:
    """Print the exact repomix command this profile would run."""
    profile = _load(profile_path)
    argv = _backend.full_command(profile)
    _emit(ctx, {"argv": argv, "command": " ".join(argv)}, [" ".join(argv)])


@pack.command("run")
@_profile_option
@_cwd_option
@click.option("--dry-run", is_flag=True, help="Show the plan and exit without packing.")
@click.option("--no-save", is_flag=True, help="Do not record the result on the profile.")
@click.option("--timeout", default=_backend.DEFAULT_TIMEOUT, show_default=True,
              help="Seconds before the repomix call is abandoned.")
@click.pass_context
def pack_run(
    ctx: click.Context,
    profile_path: Path,
    cwd: Path | None,
    dry_run: bool,
    no_save: bool,
    timeout: int,
) -> None:
    """Pack the target with the real repomix (verifies the artifact exists)."""
    profile = _load(profile_path)
    argv = _backend.full_command(profile)
    if dry_run:
        plan = {
            "dry_run": True,
            "argv": argv,
            "command": " ".join(argv),
            "cwd": str(cwd.resolve()) if cwd else str(Path.cwd()),
            "output": profile.output,
        }
        _emit(ctx, plan, ["would run:", " ".join(argv), f"cwd: {plan['cwd']}"])
        return

    result = _backend_call(_backend.run_pack, profile, cwd=cwd, timeout=timeout)
    if not no_save:
        profile.last_pack = result
        _profile.save_profile(profile, profile_path)

    security = result["security"]
    human = [
        f"packed {result['total_files']} file(s), {result['total_tokens']} token(s)",
        f"output: {result['output_path']} ({result['bytes']} bytes)",
        "security: clean"
        if security["clean"]
        else f"security: {len(security['suspicious_files'])} suspicious file(s)",
    ]
    _emit(ctx, result, human)


# --- analyze -----------------------------------------------------------------


@cli.group()
def analyze() -> None:
    """Measure a codebase without shipping its contents anywhere."""


@analyze.command("tokens")
@_profile_option
@_cwd_option
@click.option("--threshold", type=int, default=None, help="Only show files with >= N tokens.")
@click.pass_context
def analyze_tokens(
    ctx: click.Context, profile_path: Path, cwd: Path | None, threshold: int | None
) -> None:
    """Token-count tree for the profile's file selection."""
    profile = _load(profile_path)
    result = _backend_call(
        _backend.run_token_tree,
        profile,
        cwd=cwd,
        threshold=threshold,
        output=_scratch_output(profile),
    )
    human = [f"{'  ' * row['depth']}{row['name']}: {row['tokens']} tokens" for row in result["tree"]]
    human.append(f"total: {result['summary'].get('total_tokens')} tokens")
    _emit(ctx, result, human)


@analyze.command("files")
@_profile_option
@_cwd_option
@click.option("--top", type=int, default=0, help="Show only the N largest files (0 = all).")
@click.pass_context
def analyze_files(ctx: click.Context, profile_path: Path, cwd: Path | None, top: int) -> None:
    """Per-file inventory read from repomix's JSON output (no text scraping)."""
    profile = _load(profile_path)
    result = _backend_call(_backend.run_file_inventory, profile, cwd=cwd)
    rows = result["files"][:top] if top else result["files"]
    human = [f"{row['chars']:>9}  {row['path']}" for row in rows]
    human.append(f"{result['total_files']} file(s), {result['total_chars']} chars")
    _emit(ctx, {**result, "files": rows}, human)


@analyze.command("metrics")
@_profile_option
@_cwd_option
@click.pass_context
def analyze_metrics(ctx: click.Context, profile_path: Path, cwd: Path | None) -> None:
    """File/token/char counts via a metadata-only pack (`--no-files`)."""
    profile = _load(profile_path)
    result = _backend_call(
        _backend.run_metrics, profile, cwd=cwd, output=_scratch_output(profile)
    )
    human = [f"{key}: {value}" for key, value in result["summary"].items()]
    _emit(ctx, result, human)


# --- security ----------------------------------------------------------------


@cli.group()
def security() -> None:
    """Run repomix's secretlint scan over the selection."""


@security.command("check")
@_profile_option
@_cwd_option
@click.pass_context
def security_check(ctx: click.Context, profile_path: Path, cwd: Path | None) -> None:
    """Scan for credentials and secrets; exit non-zero when any are found.

    Exits 1 rather than reporting a clean scan if repomix's security output
    could not be understood — an unconfirmed "clean" is worse than an error.
    """
    profile = _load(profile_path)
    result = _backend_call(
        _backend.run_security_check, profile, cwd=cwd, output=_scratch_output(profile)
    )
    if result["clean"]:
        _emit(ctx, result, ["no suspicious files detected"])
        return
    _emit(
        ctx,
        result,
        [f"{len(result['suspicious_files'])} suspicious file(s):"]
        + [f"  {entry}" for entry in result["suspicious_files"]],
    )
    ctx.exit(2)


# --- skill -------------------------------------------------------------------


@cli.group()
def skill() -> None:
    """Generate Claude Agent Skills with repomix's own skill generator."""


@skill.command("generate")
@click.option(
    "-d",
    "--directory",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Codebase to turn into a skill.",
)
@click.option("-n", "--name", default=None, help="Skill name (kebab-case).")
@click.option(
    "-o",
    "--skill-output",
    "skill_output",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory to write SKILL.md and references/ into.",
)
@click.option("--compress", is_flag=True, help="Tree-sitter signatures instead of full bodies.")
@click.option("--include", default=None, help="Comma-separated include globs.")
@click.option("--ignore", default=None, help="Comma-separated ignore globs.")
@click.option("--dry-run", is_flag=True, help="Show what would be generated and exit.")
@click.pass_context
def skill_generate(
    ctx: click.Context,
    directory: Path,
    name: str | None,
    skill_output: Path,
    compress: bool,
    include: str | None,
    ignore: str | None,
    dry_run: bool,
) -> None:
    """Run `repomix --skill-generate` and verify the skill files exist."""
    if dry_run:
        plan = {
            "dry_run": True,
            "directory": str(directory.resolve()),
            "skill_output": str(skill_output.resolve()),
            "name": name,
            "compress": compress,
        }
        _emit(ctx, plan, [f"would generate a skill from {directory} into {skill_output}"])
        return
    result = _backend_call(
        _backend.generate_skill,
        directory.resolve(),
        name=name,
        skill_output=skill_output.resolve(),
        compress=compress,
        include=include,
        ignore=ignore,
    )
    _emit(
        ctx,
        result,
        [f"skill written to {result['skill_dir']}"] + [f"  {f}" for f in result["files"]],
    )


# --- config ------------------------------------------------------------------


@cli.group()
def config() -> None:
    """Work with repomix.config.json files."""


@config.command("export")
@_profile_option
@click.option(
    "-f",
    "--file",
    "config_file",
    type=click.Path(path_type=Path),
    default=Path("repomix.config.json"),
    show_default=True,
)
@click.option("--overwrite", is_flag=True, help="Replace an existing config file.")
@click.pass_context
def config_export(
    ctx: click.Context, profile_path: Path, config_file: Path, overwrite: bool
) -> None:
    """Write a repomix.config.json equivalent to the profile.

    Repomix's own `--init` is an interactive wizard and cannot be scripted, so
    the harness writes the config file directly from the profile.
    """
    profile = _load(profile_path)
    result = _backend_call(_backend.export_config, profile, config_file, overwrite=overwrite)
    _emit(ctx, result, [f"wrote {result['path']}"])


@config.command("show")
@click.option(
    "-f",
    "--file",
    "config_file",
    type=click.Path(path_type=Path),
    default=Path("repomix.config.json"),
    show_default=True,
)
@click.pass_context
def config_show(ctx: click.Context, config_file: Path) -> None:
    """Print a repomix config (JSONC comments tolerated)."""
    data = _backend_call(_backend.read_config, config_file)
    _emit(ctx, data, [json.dumps(data, indent=2)])


# --- session -----------------------------------------------------------------


def _revert_action(profile_path: Path, action: dict, invert: bool) -> str:
    """Apply `action` (or its inverse) to the profile file, without journaling."""
    profile = _load(profile_path)
    try:
        applied = _profile.invert_action(profile, action) if invert else action
        _profile.apply_action(profile, applied)
    except _profile.ProfileError as exc:
        raise click.ClickException(str(exc))
    _profile.save_profile(profile, profile_path)
    return applied.get("op", "?")


@cli.group("session")
def session_group() -> None:
    """Inspect and rewind the mutation journal."""


@session_group.command("status")
@_profile_option
@click.pass_context
def session_status(ctx: click.Context, profile_path: Path) -> None:
    """Show journal depth and the session file path."""
    status = _session.session_status(profile_path)
    _emit(ctx, status, [f"{key}: {value}" for key, value in status.items()])


@session_group.command("undo")
@_profile_option
@click.pass_context
def session_undo(ctx: click.Context, profile_path: Path) -> None:
    """Undo the most recent profile mutation."""
    action = _session.pop_undo(profile_path)
    if action is None:
        raise click.ClickException("nothing to undo")
    detail = _revert_action(profile_path, action, invert=True)
    _emit(ctx, {"undone": action}, [f"undid {action['op']} (applied {detail})"])


@session_group.command("redo")
@_profile_option
@click.pass_context
def session_redo(ctx: click.Context, profile_path: Path) -> None:
    """Redo the most recently undone mutation."""
    action = _session.pop_redo(profile_path)
    if action is None:
        raise click.ClickException("nothing to redo")
    detail = _revert_action(profile_path, action, invert=False)
    _emit(ctx, {"redone": action}, [f"redid {action['op']} (applied {detail})"])


# --- preview (producer) ------------------------------------------------------


@cli.group()
def preview() -> None:
    """Produce preview bundles (view them with `cli-it previews`)."""


@preview.command("recipes")
@click.pass_context
def preview_recipes(ctx: click.Context) -> None:
    """List available preview recipes."""
    recipes = [
        {"name": "pack-report", "description": "Text+JSON report of the last real pack"}
    ]
    _emit(ctx, {"recipes": recipes}, [f"{r['name']} — {r['description']}" for r in recipes])


@preview.command("capture")
@_profile_option
@click.option("-r", "--recipe", default="pack-report", show_default=True)
@click.option(
    "--root",
    "root_dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Override the previews root (default ~/.cli-it/previews).",
)
@click.pass_context
def preview_capture(
    ctx: click.Context, profile_path: Path, recipe: str, root_dir: Path | None
) -> None:
    """Write the last real pack result into a preview bundle."""
    if recipe != "pack-report":
        raise click.ClickException(f"unknown recipe '{recipe}' (try: preview recipes)")
    profile = _load(profile_path)
    if not profile.last_pack:
        raise click.ClickException("no pack recorded yet (run: pack run)")
    snapshot = profile.last_pack
    bundle = _preview.prepare_bundle(
        "repomix",
        recipe,
        inputs={"profile": str(profile_path.resolve()), "output": snapshot.get("output_path")},
        root_dir=root_dir,
    )
    security = snapshot.get("security", {})
    lines = [
        f"Repomix pack report — profile: {profile.name}",
        "=" * 44,
        f"target:   {profile.remote or ', '.join(profile.targets)}",
        f"style:    {snapshot.get('style')}",
        f"output:   {snapshot.get('output_path')} ({snapshot.get('bytes')} bytes)",
        f"files:    {snapshot.get('total_files')}",
        f"tokens:   {snapshot.get('total_tokens')}",
        f"chars:    {snapshot.get('total_chars')}",
        f"security: {'clean' if security.get('clean') else security.get('suspicious_files')}",
    ]
    (bundle / "artifacts" / "report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (bundle / "artifacts" / "report.json").write_text(
        json.dumps(snapshot, indent=2), encoding="utf-8"
    )
    _preview.finalize_bundle(
        bundle,
        summary={
            "profile": profile.name,
            "total_files": snapshot.get("total_files"),
            "total_tokens": snapshot.get("total_tokens"),
        },
    )
    _emit(ctx, {"bundle": str(bundle)}, [str(bundle)])


@preview.command("latest")
@click.option("-r", "--recipe", default="pack-report", show_default=True)
@click.option("--root", "root_dir", type=click.Path(path_type=Path), default=None)
@click.pass_context
def preview_latest(ctx: click.Context, recipe: str, root_dir: Path | None) -> None:
    """Print the newest bundle path for a recipe."""
    bundle = _preview.bundle_root("repomix", recipe, root_dir=root_dir)
    if not (bundle / "manifest.json").is_file():
        raise click.ClickException(f"no bundle captured yet for recipe '{recipe}'")
    _emit(ctx, {"bundle": str(bundle)}, [str(bundle)])


# --- REPL --------------------------------------------------------------------

_REPL_COMMANDS = {
    "backend": "probe the real repomix binary",
    "profile new|info|save": "manage pack-profile files",
    "target show|set": "local dirs or a remote repo (undoable)",
    "filter list|add|remove": "include/ignore glob patterns (undoable)",
    "option list|set": "style, compress, token budget (undoable)",
    "pack argv|run [--dry-run]": "run the real repomix, verify the artifact",
    "analyze tokens|metrics|files": "measure cost without shipping contents",
    "security check": "secretlint scan (exit 2 when findings)",
    "skill generate": "repomix --skill-generate into a directory",
    "config export|show": "repomix.config.json handling",
    "session status|undo|redo": "journal control",
    "preview recipes|capture|latest": "produce preview bundles",
    "help / exit": "this help / leave the REPL",
}


def _run_repl() -> None:
    skin = ReplSkin("repomix", __version__)
    skin.print_banner()
    prompt = skin.create_prompt_session()
    while True:
        try:
            line = prompt("repomix> ").strip()
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
                prog_name="cli-it-repomix",
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
