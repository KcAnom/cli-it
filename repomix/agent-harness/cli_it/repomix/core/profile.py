"""Pack-profile data model — the harness's own state, independent of repomix.

A profile is a reusable, named packing recipe: what to pack, how to filter it,
which output style, and what cost guard applies. Repomix itself keeps one
`repomix.config.json` per directory; a profile lets an agent hold several
recipes over the same tree and mutate them with undo.

Nothing in this module invokes repomix — it is pure data, so the unit tests
run on a machine without repomix installed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

PROFILE_FORMAT = "repomix-profile/v1"

STYLES = ("xml", "markdown", "json", "plain")

#: Boolean repomix flags the profile can toggle, mapped to their CLI flags.
BOOL_OPTIONS: dict[str, str] = {
    "compress": "--compress",
    "remove_comments": "--remove-comments",
    "remove_empty_lines": "--remove-empty-lines",
    "truncate_base64": "--truncate-base64",
    "output_show_line_numbers": "--output-show-line-numbers",
    "include_empty_directories": "--include-empty-directories",
    "include_full_directory_structure": "--include-full-directory-structure",
    "include_diffs": "--include-diffs",
    "include_logs": "--include-logs",
    "no_gitignore": "--no-gitignore",
    "no_default_patterns": "--no-default-patterns",
    "no_security_check": "--no-security-check",
    "parsable_style": "--parsable-style",
}

#: Scalar settings and their validators, applied by `option set`.
SCALAR_OPTIONS = (
    "style",
    "output",
    "token_budget",
    "token_encoding",
    "include_logs_count",
    "split_output",
    "remote",
    "remote_branch",
)

FILTER_KINDS = ("include", "ignore")


class ProfileError(Exception):
    """Raised for malformed profiles and invalid mutations."""


@dataclass
class Profile:
    name: str = "pack"
    targets: list[str] = field(default_factory=lambda: ["."])
    remote: str | None = None
    remote_branch: str | None = None
    style: str = "xml"
    output: str = "repomix-output.xml"
    include: list[str] = field(default_factory=list)
    ignore: list[str] = field(default_factory=list)
    options: dict[str, bool] = field(default_factory=dict)
    token_budget: int | None = None
    token_encoding: str = "o200k_base"
    include_logs_count: int | None = None
    split_output: str | None = None
    last_pack: dict | None = None
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))


def new_profile(name: str = "pack", targets: list[str] | None = None) -> Profile:
    return Profile(name=name, targets=list(targets) if targets else ["."])


def to_dict(profile: Profile) -> dict:
    return {
        "format": PROFILE_FORMAT,
        "name": profile.name,
        "targets": profile.targets,
        "remote": profile.remote,
        "remote_branch": profile.remote_branch,
        "style": profile.style,
        "output": profile.output,
        "include": profile.include,
        "ignore": profile.ignore,
        "options": profile.options,
        "token_budget": profile.token_budget,
        "token_encoding": profile.token_encoding,
        "include_logs_count": profile.include_logs_count,
        "split_output": profile.split_output,
        "last_pack": profile.last_pack,
        "created_at": profile.created_at,
    }


def from_dict(data: dict) -> Profile:
    if not isinstance(data, dict):
        raise ProfileError("profile must be a JSON object")
    fmt = data.get("format")
    if fmt != PROFILE_FORMAT:
        raise ProfileError(f"unsupported profile format: {fmt!r} (expected {PROFILE_FORMAT})")
    profile = Profile(
        name=data.get("name", "pack"),
        targets=list(data.get("targets") or ["."]),
        remote=data.get("remote"),
        remote_branch=data.get("remote_branch"),
        style=data.get("style", "xml"),
        output=data.get("output", "repomix-output.xml"),
        include=list(data.get("include") or []),
        ignore=list(data.get("ignore") or []),
        options=dict(data.get("options") or {}),
        token_budget=data.get("token_budget"),
        token_encoding=data.get("token_encoding", "o200k_base"),
        include_logs_count=data.get("include_logs_count"),
        split_output=data.get("split_output"),
        last_pack=data.get("last_pack"),
        created_at=data.get("created_at", time.strftime("%Y-%m-%dT%H:%M:%S")),
    )
    validate(profile)
    return profile


def validate(profile: Profile) -> None:
    if profile.style not in STYLES:
        raise ProfileError(f"unknown style {profile.style!r} (expected one of {', '.join(STYLES)})")
    if not profile.targets and not profile.remote:
        raise ProfileError("profile has neither targets nor a remote repository")
    for key in profile.options:
        if key not in BOOL_OPTIONS:
            raise ProfileError(f"unknown option {key!r}")
    if profile.token_budget is not None and profile.token_budget <= 0:
        raise ProfileError("token_budget must be a positive integer")


def load_profile(path: str | Path) -> Profile:
    path = Path(path)
    if not path.is_file():
        raise ProfileError(f"profile not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ProfileError(f"profile is not valid JSON: {path} ({exc})")
    return from_dict(data)


def save_profile(profile: Profile, path: str | Path) -> Path:
    validate(profile)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_dict(profile), indent=2) + "\n", encoding="utf-8")
    return path


def profile_info(profile: Profile, path: str | Path) -> dict:
    return {
        "name": profile.name,
        "path": str(Path(path).resolve()),
        "targets": profile.targets,
        "remote": profile.remote,
        "remote_branch": profile.remote_branch,
        "style": profile.style,
        "output": profile.output,
        "include": profile.include,
        "ignore": profile.ignore,
        "options": {k: v for k, v in profile.options.items() if v},
        "token_budget": profile.token_budget,
        "token_encoding": profile.token_encoding,
        "last_pack": profile.last_pack,
    }


# --- mutations ---------------------------------------------------------------


def _coerce_scalar(key: str, value):
    """Normalize a scalar option value, raising ProfileError when invalid."""
    if value in (None, "", "none", "null"):
        if key in ("style", "output", "token_encoding"):
            raise ProfileError(f"{key} cannot be cleared")
        return None
    if key == "style":
        if value not in STYLES:
            raise ProfileError(f"unknown style {value!r} (expected one of {', '.join(STYLES)})")
        return value
    if key in ("token_budget", "include_logs_count"):
        try:
            number = int(value)
        except (TypeError, ValueError):
            raise ProfileError(f"{key} must be an integer, got {value!r}")
        if number <= 0:
            raise ProfileError(f"{key} must be a positive integer")
        return number
    return str(value)


def apply_action(profile: Profile, action: dict) -> Profile:
    """Apply a journaled action in place. Raises ProfileError when invalid.

    Overwriting ops (`target.set`, `option.set`) record the value they replaced
    under `previous`, because the old value is otherwise unrecoverable once the
    profile is saved — `invert_action` needs it to undo. `setdefault` keeps the
    original snapshot when an action is re-applied by redo.
    """
    op = action.get("op")

    if op == "target.set":
        action.setdefault(
            "previous",
            {
                "targets": list(profile.targets),
                "remote": profile.remote,
                "remote_branch": profile.remote_branch,
            },
        )
        targets = action.get("targets")
        remote = action.get("remote")
        if not targets and not remote:
            raise ProfileError("target.set needs targets or a remote")
        profile.targets = list(targets or [])
        profile.remote = remote
        profile.remote_branch = action.get("remote_branch")
        if not profile.targets and not profile.remote:
            raise ProfileError("profile would have neither targets nor a remote")

    elif op == "filter.add":
        kind = action.get("kind")
        pattern = action.get("pattern")
        if kind not in FILTER_KINDS:
            raise ProfileError(f"filter kind must be one of {', '.join(FILTER_KINDS)}")
        if not pattern:
            raise ProfileError("filter.add needs a pattern")
        bucket = profile.include if kind == "include" else profile.ignore
        if pattern in bucket:
            raise ProfileError(f"{kind} pattern already present: {pattern}")
        bucket.append(pattern)

    elif op == "filter.remove":
        kind = action.get("kind")
        pattern = action.get("pattern")
        if kind not in FILTER_KINDS:
            raise ProfileError(f"filter kind must be one of {', '.join(FILTER_KINDS)}")
        bucket = profile.include if kind == "include" else profile.ignore
        if pattern not in bucket:
            raise ProfileError(f"no such {kind} pattern: {pattern}")
        bucket.remove(pattern)

    elif op == "option.set":
        key = action.get("key")
        value = action.get("value")
        if key in BOOL_OPTIONS:
            action.setdefault("previous", bool(profile.options.get(key, False)))
            profile.options[key] = bool(value)
        elif key in SCALAR_OPTIONS:
            action.setdefault("previous", getattr(profile, key))
            setattr(profile, key, _coerce_scalar(key, value))
        else:
            raise ProfileError(f"unknown option {key!r}")

    else:
        raise ProfileError(f"unknown action op: {op!r}")

    validate(profile)
    return profile


def invert_action(profile: Profile, action: dict) -> dict:
    """Build the action that reverses `action`.

    Add/remove pairs invert structurally; overwriting ops replay the `previous`
    snapshot that `apply_action` recorded.
    """
    op = action.get("op")
    if op == "filter.add":
        return {"op": "filter.remove", "kind": action["kind"], "pattern": action["pattern"]}
    if op == "filter.remove":
        return {"op": "filter.add", "kind": action["kind"], "pattern": action["pattern"]}

    if "previous" not in action:
        raise ProfileError(
            f"cannot invert {op!r}: the journal entry has no 'previous' snapshot "
            "(it predates this harness version)"
        )
    previous = action["previous"]

    if op == "target.set":
        return {
            "op": "target.set",
            "targets": list(previous.get("targets") or []),
            "remote": previous.get("remote"),
            "remote_branch": previous.get("remote_branch"),
        }
    if op == "option.set":
        return {"op": "option.set", "key": action["key"], "value": previous}
    raise ProfileError(f"cannot invert action op: {op!r}")
