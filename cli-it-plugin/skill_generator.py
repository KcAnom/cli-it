#!/usr/bin/env python3
"""Generate SKILL.md files for CLI-It harnesses (phase 6.5 of HARNESS.md).

Parses a harness's Click CLI module (regex-based — no import of the harness),
its setup.py version, and its README intro, then renders
templates/SKILL.md.template into:

  1. `<repo>/skills/cli-it-<software>/SKILL.md` (canonical, npx-skills layout)
  2. `<harness>/cli_it/<software>/skills/SKILL.md` (packaged copy for wheels)

Usage:
  python skill_generator.py <target-project>/agent-harness [--repo-root PATH]

The harness argument must lexically name the direct ``agent-harness`` child of
its target project. Relative and absolute paths are accepted; escaping
harness or nested symlinks are rejected.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "SKILL.md.template"


@dataclass
class CommandInfo:
    name: str
    help: str = ""
    group: str = "root"


@dataclass
class CommandGroup:
    name: str
    help: str = ""
    commands: list[CommandInfo] = field(default_factory=list)


@dataclass
class Example:
    title: str
    command: str


@dataclass
class SkillMetadata:
    software: str
    display_name: str
    version: str
    description: str
    entry_point: str
    skill_name: str
    install_cmd: str
    groups: list[CommandGroup] = field(default_factory=list)
    examples: list[Example] = field(default_factory=list)


# --- extraction --------------------------------------------------------------

_DECORATOR_RE = re.compile(
    r"^@(?P<parent>\w+)\.(?P<kind>group|command)\s*\((?:\s*[\"'](?P<name>[^\"']+)[\"'])?"
)
_DEF_RE = re.compile(r"^def\s+(?P<func>\w+)\s*\(")
_DOCSTRING_RE = re.compile(r'"""(.*?)(?:"""|$)', re.DOTALL)


def resolve_harness_path(path: str | Path) -> Path:
    """Validate and resolve a direct ``<target-project>/agent-harness`` path.

    The lexical basename is significant. Resolving the parent separately allows
    symlinked project ancestors while rejecting a top-level harness symlink that
    redirects outside the resolved target project.
    """
    submitted = Path(path)
    if submitted.name != "agent-harness":
        raise ValueError(
            f"invalid harness path {submitted!s}: basename must be 'agent-harness'; "
            "required form is <target-project>/agent-harness"
        )
    target_project = submitted.parent.resolve()
    harness = submitted.resolve()
    expected = target_project / "agent-harness"
    if harness != expected:
        raise ValueError(
            f"invalid harness path {submitted!s}: resolved path is not the direct "
            "agent-harness child of its resolved target project; required form is "
            "<target-project>/agent-harness"
        )
    return harness


def _resolve_within(path: Path, root: Path, label: str) -> Path:
    """Resolve *path* and reject symlink traversal outside resolved *root*."""
    resolved_root = root.resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(
            f"{label} escapes its allowed root: {path} resolves outside "
            f"{resolved_root}"
        )
    return resolved


def _resolve_file_if_present(path: Path, root: Path, label: str) -> Path:
    """Resolve an optional file safely, including a dangling symlink."""
    if path.exists() or path.is_symlink():
        return _resolve_within(path, root, label)
    return path


def _find_software_dir(harness_path: Path) -> Path:
    namespace_path = harness_path / "cli_it"
    if not namespace_path.is_dir():
        raise FileNotFoundError(f"no cli_it/ namespace dir under {harness_path}")
    namespace = _resolve_within(namespace_path, harness_path, "cli_it namespace")
    candidates = []
    for candidate in namespace.iterdir():
        if candidate.is_dir() and candidate.name != "__pycache__":
            candidates.append(
                _resolve_within(candidate, namespace, "software package")
            )
    if len(candidates) != 1:
        raise ValueError(
            f"expected exactly one software package under {namespace}, "
            f"found: {[d.name for d in candidates]}"
        )
    return candidates[0]


def _docstring_after(lines: list[str], start: int) -> str:
    """First line of the docstring following a `def` at lines[start]."""
    window = "\n".join(lines[start : start + 12])
    # A def signature can span lines but never contains a triple-quoted
    # string, so the first docstring in the window is the right one.
    match = _DOCSTRING_RE.search(window)
    if not match:
        return ""
    return match.group(1).strip().splitlines()[0].strip() if match.group(1).strip() else ""


def _parse_click_module(source: str) -> list[CommandGroup]:
    lines = source.splitlines()
    groups: dict[str, CommandGroup] = {}
    order: list[str] = []
    pending: list[dict] = []

    i = -1
    while i + 1 < len(lines):
        i += 1
        stripped = lines[i].strip()
        if stripped.startswith("@"):
            match = _DECORATOR_RE.match(stripped)
            if match:
                pending.append(match.groupdict())
            # swallow multiline decorator calls so continuations don't reset state
            depth = stripped.count("(") - stripped.count(")")
            while depth > 0 and i + 1 < len(lines):
                i += 1
                depth += lines[i].count("(") - lines[i].count(")")
            continue
        def_match = _DEF_RE.match(stripped)
        if def_match:
            for deco in pending:
                name = deco["name"] or def_match.group("func").replace("_", "-")
                name = re.sub(r"-?cmd$", "", name)
                doc = _docstring_after(lines, i)
                if deco["kind"] == "group" and deco["parent"] != "click":
                    key = def_match.group("func")
                    if key not in groups:
                        groups[key] = CommandGroup(name=name, help=doc)
                        order.append(key)
                elif deco["kind"] == "command":
                    parent = deco["parent"]
                    if parent not in groups:
                        groups[parent] = CommandGroup(
                            name="root" if parent in ("cli", "main") else parent
                        )
                        order.append(parent)
                    groups[parent].commands.append(
                        CommandInfo(name=name, help=doc, group=groups[parent].name)
                    )
            pending = []
        elif stripped:
            pending = []

    return [groups[key] for key in order]


def extract_cli_metadata(harness_path: str | Path) -> SkillMetadata:
    """Extract metadata from a validated direct ``agent-harness`` child."""
    return _extract_cli_metadata(resolve_harness_path(harness_path))


def _extract_cli_metadata(harness_path: Path) -> SkillMetadata:
    software_dir = _find_software_dir(harness_path)
    software = software_dir.name

    cli_module = _resolve_file_if_present(
        software_dir / f"{software}_cli.py", software_dir, "CLI module"
    )
    if not cli_module.is_file():
        candidates = [
            _resolve_within(candidate, software_dir, "CLI module")
            for candidate in software_dir.glob("*_cli.py")
        ]
        if not candidates:
            raise FileNotFoundError(f"no *_cli.py module in {software_dir}")
        cli_module = candidates[0]
    groups = _parse_click_module(cli_module.read_text(encoding="utf-8"))

    version = "0.1.0"
    setup_py = _resolve_file_if_present(
        harness_path / "setup.py", harness_path, "setup.py metadata file"
    )
    if setup_py.is_file():
        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', setup_py.read_text())
        if match:
            version = match.group(1)

    description = f"Agent-native CLI harness for {software}"
    readme = _resolve_file_if_present(
        software_dir / "README.md", software_dir, "README metadata file"
    )
    if readme.is_file():
        for line in readme.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith(("#", ">", "!", "[")):
                description = line
                break

    skill_name = f"cli-it-{software.replace('_', '-')}"
    entry_point = skill_name
    display_name = software.replace("_", " ").replace("-", " ").title()

    examples = [Example("Show all commands", f"{entry_point} --help")]
    for group in groups:
        for command in group.commands[:1]:
            invocation = (
                f"{entry_point} {command.name}"
                if group.name == "root"
                else f"{entry_point} {group.name} {command.name}"
            )
            examples.append(Example(command.help or command.name, invocation))
    examples.append(
        Example("Machine-readable output", f"{entry_point} --json <group> <command>")
    )

    return SkillMetadata(
        software=software,
        display_name=display_name,
        version=version,
        description=description,
        entry_point=entry_point,
        skill_name=skill_name,
        install_cmd=f"pip install -e {harness_path}",
        groups=groups,
        examples=examples,
    )


# --- rendering ---------------------------------------------------------------


def _render_template(template: str, variables: dict[str, str]) -> str:
    def substitute(match: re.Match) -> str:
        return variables.get(match.group(1), match.group(0))

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", substitute, template)


def _groups_table(groups: list[CommandGroup]) -> str:
    rows = ["| Group | Command | Description |", "|-------|---------|-------------|"]
    for group in groups:
        for command in group.commands:
            rows.append(f"| `{group.name}` | `{command.name}` | {command.help} |")
        if not group.commands:
            rows.append(f"| `{group.name}` | — | {group.help} |")
    return "\n".join(rows)


def _examples_block(examples: list[Example]) -> str:
    parts = []
    for example in examples:
        parts.append(f"**{example.title}**\n\n```bash\n{example.command}\n```")
    return "\n\n".join(parts)


def generate_skill_md(meta: SkillMetadata) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return _render_template(
        template,
        {
            "skill_name": meta.skill_name,
            "description": meta.description,
            "version": meta.version,
            "display_name": meta.display_name,
            "entry_point": meta.entry_point,
            "install_cmd": meta.install_cmd,
            "command_groups_table": _groups_table(meta.groups),
            "examples": _examples_block(meta.examples),
        },
    )


def _find_repo_root(start: Path) -> Path | None:
    for parent in [start, *start.parents]:
        if (parent / "registry.json").is_file() and (parent / "skills").is_dir():
            return parent
    return None


def _resolve_explicit_repo_root(repo_root: str | Path) -> Path:
    """Require an explicit root to be an existing CLI-It repository."""
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise ValueError(f"invalid CLI-It repository root {repo_root!s}: directory does not exist")
    registry = root / "registry.json"
    skills = root / "skills"
    if not registry.is_file() or not skills.is_dir():
        raise ValueError(
            f"invalid CLI-It repository root {repo_root!s}: requires registry.json "
            "file and skills/ directory markers"
        )
    _resolve_within(registry, root, "repository registry marker")
    _resolve_within(skills, root, "repository skills marker")
    return root


def generate_skill_file(
    harness_path: str | Path, repo_root: str | Path | None = None
) -> list[Path]:
    """Render and dual-write SKILL.md after preflighting every destination."""
    harness = resolve_harness_path(harness_path)
    root = (
        _resolve_explicit_repo_root(repo_root)
        if repo_root is not None
        else _find_repo_root(harness)
    )
    meta = _extract_cli_metadata(harness)
    content = generate_skill_md(meta)

    packaged = _resolve_within(
        _find_software_dir(harness) / "skills" / "SKILL.md",
        harness,
        "packaged skill destination",
    )
    canonical = None
    if root is not None:
        canonical = _resolve_within(
            root / "skills" / meta.skill_name / "SKILL.md",
            root,
            "canonical skill destination",
        )

    # All destinations have passed boundary checks before the first mkdir/write.
    written: list[Path] = []
    if canonical is not None:
        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.write_text(content, encoding="utf-8")
        written.append(canonical)
    packaged.parent.mkdir(parents=True, exist_ok=True)
    packaged.write_text(content, encoding="utf-8")
    written.append(packaged)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "harness_path",
        help="direct <target-project>/agent-harness child (not a project/repo root)",
    )
    parser.add_argument(
        "--repo-root", default=None, help="CLI-It repository root override"
    )
    args = parser.parse_args()
    for path in generate_skill_file(args.harness_path, repo_root=args.repo_root):
        print(path)


if __name__ == "__main__":
    main()
