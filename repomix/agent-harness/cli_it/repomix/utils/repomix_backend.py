"""The only module that invokes the real repomix.

Every subprocess call to repomix lives here (HARNESS.md: backend isolation).
The CLI layer never builds an argv or reads repomix output directly — it calls
these functions and handles `BackendError`.

Resolution order for the executable:
1. `$REPOMIX_BIN` — explicit override (also lets tests point at a stub)
2. `repomix` on PATH — the normal `npm install -g repomix` case
3. `npx -y repomix` — fallback when npx exists but repomix is not installed
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

INSTALL_HINT = (
    "repomix was not found. Install it with `npm install -g repomix` "
    "(or `brew install repomix`), or set $REPOMIX_BIN to its path."
)

DEFAULT_TIMEOUT = 900

#: repomix releases this harness has actually been exercised against. The
#: summary, token-tree, and security parsers read repomix's *decorated human
#: output*, which is not a stable API — a formatting change upstream can break
#: them. Everything that scrapes therefore fails loudly rather than returning a
#: plausible-looking empty result, and `probe()` reports whether the installed
#: version is one that was tested.
TESTED_VERSIONS = "1.17.x"
TESTED_MAJOR_MINOR = (1, 17)

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_SUMMARY_FIELDS = {
    "Total Files": "total_files",
    "Total Tokens": "total_tokens",
    "Total Chars": "total_chars",
    "Output": "output",
    "Security": "security",
}


class BackendError(Exception):
    """Raised when repomix is missing, fails, or returns something unusable."""


# --- executable resolution ---------------------------------------------------


def resolve_bin() -> list[str] | None:
    """Return the argv prefix that runs repomix, or None when unavailable."""
    override = os.environ.get("REPOMIX_BIN")
    if override:
        return [override]
    found = shutil.which("repomix")
    if found:
        return [found]
    if shutil.which("npx"):
        return ["npx", "-y", "repomix"]
    return None


def require_bin() -> list[str]:
    argv = resolve_bin()
    if argv is None:
        raise BackendError(INSTALL_HINT)
    return argv


def available() -> bool:
    return resolve_bin() is not None


def version_is_tested(version: str | None) -> bool | None:
    """True/False when the version parses, None when it cannot be determined."""
    if not version:
        return None
    match = re.search(r"(\d+)\.(\d+)", version)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2))) == TESTED_MAJOR_MINOR


def _drift_error(what: str, stdout: str) -> BackendError:
    """Raised when repomix ran fine but its output could not be understood."""
    tail = "\n".join(_clean(stdout).strip().splitlines()[-12:])
    return BackendError(
        f"could not parse {what} from repomix's output. This harness is tested "
        f"against repomix {TESTED_VERSIONS}; a newer release may have changed its "
        f"output format. Try `cli-it-repomix doctor --heal`, which re-learns the "
        f"summary labels by checking them against repomix's own JSON output. "
        f"Last lines of what repomix printed:\n{tail}"
    )


def _installed_version() -> str | None:
    """Version of the repomix actually on this machine, or None."""
    try:
        result = _run(["--version"], timeout=120)
    except BackendError:
        return None
    return _clean(result.stdout).strip() or None if result.returncode == 0 else None


def _learned_labels() -> dict[str, str]:
    """Summary labels previously learned for the installed repomix version."""
    from cli_it.repomix.core.knowledge import learned_labels

    try:
        return learned_labels(_installed_version())
    except OSError:
        return {}


def _run(args: list[str], cwd: Path | None = None, timeout: int = DEFAULT_TIMEOUT):
    argv = require_bin() + args
    try:
        return subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise BackendError(INSTALL_HINT)
    except subprocess.TimeoutExpired:
        raise BackendError(f"repomix timed out after {timeout}s: {' '.join(argv)}")


def probe() -> dict:
    """Report how (and whether) the real repomix can be reached."""
    argv = resolve_bin()
    info: dict = {
        "available": argv is not None,
        "command": " ".join(argv) if argv else None,
        "source": (
            "REPOMIX_BIN"
            if os.environ.get("REPOMIX_BIN")
            else "PATH"
            if argv and len(argv) == 1
            else "npx"
            if argv
            else None
        ),
        "version": None,
        "node": None,
    }
    if argv is None:
        info["hint"] = INSTALL_HINT
        return info
    result = _run(["--version"], timeout=120)
    if result.returncode == 0:
        info["version"] = _clean(result.stdout).strip() or None
    else:
        info["error"] = _clean(result.stderr).strip()[:400]

    info["tested_versions"] = TESTED_VERSIONS
    info["version_tested"] = version_is_tested(info["version"])
    if info["version"] and not info["version_tested"]:
        info["warning"] = (
            f"repomix {info['version']} is outside the tested range {TESTED_VERSIONS}; "
            "commands that parse repomix's human output may need updating"
        )
    node = shutil.which("node")
    if node:
        node_result = subprocess.run([node, "--version"], capture_output=True, text=True)
        info["node"] = node_result.stdout.strip() or None
    return info


# --- argv construction -------------------------------------------------------


def build_argv(profile, *, output: str | None = None, extra: list[str] | None = None) -> list[str]:
    """Translate a profile into repomix arguments (no executable prefix).

    Shared by dry-run and real execution so `pack run --dry-run` always shows
    the command that would actually be issued.
    """
    from cli_it.repomix.core.profile import BOOL_OPTIONS

    args: list[str] = []
    if profile.remote:
        args += ["--remote", profile.remote]
        if profile.remote_branch:
            args += ["--remote-branch", profile.remote_branch]
    else:
        args += list(profile.targets)

    args += ["--style", profile.style]
    args += ["-o", output if output is not None else profile.output]

    if profile.include:
        args += ["--include", ",".join(profile.include)]
    if profile.ignore:
        args += ["-i", ",".join(profile.ignore)]

    for key, flag in BOOL_OPTIONS.items():
        if profile.options.get(key):
            args.append(flag)

    if profile.options.get("include_logs") and profile.include_logs_count:
        args += ["--include-logs-count", str(profile.include_logs_count)]
    if profile.split_output:
        args += ["--split-output", profile.split_output]
    if profile.token_encoding:
        args += ["--token-count-encoding", profile.token_encoding]
    if profile.token_budget:
        args += ["--token-budget", str(profile.token_budget)]

    args += list(extra or [])
    return args


def full_command(profile, *, output: str | None = None, extra: list[str] | None = None) -> list[str]:
    """The complete argv including the resolved executable (for dry-run display)."""
    prefix = resolve_bin() or ["repomix"]
    return prefix + build_argv(profile, output=output, extra=extra)


# --- output parsing ----------------------------------------------------------


def _clean(text: str) -> str:
    return _ANSI.sub("", text or "")


def _to_number(value: str):
    """First whitespace-delimited token as an int, or None.

    A label with an empty value ("Pack Summary:") is normal in repomix's output,
    so this must never raise.
    """
    tokens = value.replace(",", "").split()
    if not tokens:
        return None
    try:
        return int(tokens[0])
    except ValueError:
        return None


def parse_summary(stdout: str, *, learned: dict[str, str] | None = None) -> dict:
    """Extract the Pack Summary block into stable JSON.

    Repomix prints a decorated human summary; agents need numbers. `learned`
    supplies extra label → field mappings discovered by `doctor --heal` when
    repomix renamed something (see core/knowledge.py); built-in labels always
    win, so a learned entry can never mask a label that still works.
    """
    fields = {**(learned or {}), **_SUMMARY_FIELDS}
    summary: dict = {}
    for line in _clean(stdout).splitlines():
        stripped = line.strip()
        if ":" not in stripped:
            continue
        label, _, value = stripped.partition(":")
        key = fields.get(label.strip())
        if not key:
            continue
        value = value.strip()
        summary[key] = _to_number(value) if key.startswith("total_") else value
    return summary


def _numeric_labels(stdout: str) -> dict[str, int]:
    """Every `Label: <number>` pair in the output, for label discovery."""
    found: dict[str, int] = {}
    for line in _clean(stdout).splitlines():
        stripped = line.strip()
        if ":" not in stripped:
            continue
        label, _, value = stripped.partition(":")
        number = _to_number(value.strip())
        if number is not None:
            found.setdefault(label.strip(), number)
    return found


def discover_summary_labels(stdout: str, truth: dict) -> dict[str, dict]:
    """Match repomix's current labels against counts we already know are true.

    `truth` comes from `run_file_inventory`, i.e. from repomix's JSON output —
    an independent source. A label is only accepted for `total_files` or
    `total_chars` when its number *equals* the known count, so a renamed label
    is verified rather than guessed.

    `total_tokens` has no independent ground truth (the count is repomix's own
    tokenizer), so it is matched by label wording alone and marked as such. A
    caller that needs certainty should treat HEURISTIC entries as unconfirmed.
    """
    from cli_it.repomix.core.knowledge import HEURISTIC, VERIFIED

    known = {name for name in _SUMMARY_FIELDS.values()}
    candidates = _numeric_labels(stdout)
    learned: dict[str, dict] = {}

    for field, expected in (
        ("total_files", truth.get("total_files")),
        ("total_chars", truth.get("total_chars")),
    ):
        if expected is None:
            continue
        hint = field.split("_")[1][:4]  # "file" / "char"
        matches = [label for label, number in candidates.items() if number == expected]
        if not matches:
            continue
        # Prefer a label that also *reads* like the field; fall back to a unique
        # numeric match. An ambiguous match with no wording hint is skipped
        # rather than guessed.
        worded = [label for label in matches if hint in label.lower()]
        chosen = worded[0] if worded else (matches[0] if len(matches) == 1 else None)
        if chosen is None or chosen in _SUMMARY_FIELDS:
            continue
        learned[chosen] = {
            "field": field,
            "provenance": VERIFIED,
            "evidence": f"label value {expected} equals the count from repomix's JSON output",
        }

    if "total_tokens" in known:
        for label in candidates:
            if label in _SUMMARY_FIELDS or label in learned:
                continue
            if "token" in label.lower():
                learned[label] = {
                    "field": "total_tokens",
                    "provenance": HEURISTIC,
                    "evidence": "label wording contains 'token'; no independent count exists to verify it",
                }
                break

    return learned


def parse_token_tree(stdout: str) -> list[dict]:
    """Parse the `--token-count-tree` block into {path_fragment, tokens} rows."""
    rows: list[dict] = []
    in_tree = False
    for line in _clean(stdout).splitlines():
        if "Token Count Tree" in line:
            in_tree = True
            continue
        if not in_tree:
            continue
        if not line.strip() or line.strip().startswith("─"):
            if rows:
                break
            continue
        match = re.search(r"([^\s│├└─]+/?)\s+\((\d[\d,]*) tokens\)", line)
        if not match:
            if rows:
                break
            continue
        depth = (len(line) - len(line.lstrip(" │├└─"))) // 4
        rows.append(
            {
                "name": match.group(1),
                "tokens": int(match.group(2).replace(",", "")),
                "depth": depth,
            }
        )
    return rows


def parse_security(stdout: str) -> dict:
    """Parse the Security Check block.

    Three outcomes, never two: `clean` requires repomix to have *said* the scan
    was clean, `findings` lists what it flagged, and `unknown` means the block
    could not be recognized at all. Defaulting an unrecognized block to clean
    would turn a formatting change in repomix into a silent "no secrets here",
    which is the one failure this command must never produce.
    """
    text = _clean(stdout)
    findings: list[str] = []
    saw_block = False
    in_block = False
    for line in text.splitlines():
        if "Security Check" in line:
            saw_block = True
            in_block = True
            continue
        if not in_block:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("─"):
            continue
        if stripped.startswith(("📊", "🎉", "💡", "🔢")):
            break
        if "No suspicious files detected" in stripped:
            return {"status": "clean", "clean": True, "suspicious_files": []}
        findings.append(stripped.lstrip("•-✖✔ ").strip())

    if findings:
        return {"status": "findings", "clean": False, "suspicious_files": findings}
    return {
        "status": "unknown",
        "clean": None,
        "suspicious_files": [],
        "detail": (
            "could not recognize repomix's security-check output"
            + ("" if saw_block else " (no Security Check block found)")
            + f" — this harness is tested against repomix {TESTED_VERSIONS}"
        ),
    }


# --- operations --------------------------------------------------------------


def run_pack(profile, *, cwd: Path | None = None, output: str | None = None,
             extra: list[str] | None = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Run a real pack and verify the artifact before reporting success."""
    target_output = output if output is not None else profile.output
    args = build_argv(profile, output=target_output, extra=extra)
    result = _run(args, cwd=cwd, timeout=timeout)
    stdout = _clean(result.stdout)
    stderr = _clean(result.stderr)

    if result.returncode != 0:
        detail = (stderr or stdout).strip()
        if profile.token_budget and "budget" in detail.lower():
            raise BackendError(
                f"token budget of {profile.token_budget} exceeded — {detail.splitlines()[-1]}"
            )
        raise BackendError(f"repomix failed (exit {result.returncode}): {detail[:600]}")

    base = Path(cwd) if cwd else Path.cwd()
    artifact = Path(target_output)
    if not artifact.is_absolute():
        artifact = base / artifact

    summary = parse_summary(stdout, learned=_learned_labels())
    security = parse_security(stdout)

    if not artifact.is_file() and not profile.split_output:
        raise BackendError(
            f"repomix reported success but {artifact} does not exist — "
            "check the output path in the profile"
        )
    if summary.get("total_files") is None:
        raise _drift_error("the pack summary", stdout)

    return {
        "output_path": str(artifact),
        "exists": artifact.is_file(),
        "bytes": artifact.stat().st_size if artifact.is_file() else None,
        "total_files": summary.get("total_files"),
        "total_tokens": summary.get("total_tokens"),
        "total_chars": summary.get("total_chars"),
        "security": security,
        "style": profile.style,
        "command": " ".join(require_bin() + args),
    }


def run_token_tree(profile, *, cwd: Path | None = None, threshold: int | None = None,
                   output: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Token-count tree for the profile's selection (writes to a scratch output)."""
    extra = ["--token-count-tree"] + ([str(threshold)] if threshold else [])
    args = build_argv(profile, output=output or profile.output, extra=extra)
    result = _run(args, cwd=cwd, timeout=timeout)
    stdout = _clean(result.stdout)
    if result.returncode != 0:
        raise BackendError(
            f"repomix failed (exit {result.returncode}): {(_clean(result.stderr) or stdout)[:600]}"
        )
    tree = parse_token_tree(stdout)
    summary = parse_summary(stdout, learned=_learned_labels())
    if not tree or summary.get("total_tokens") is None:
        raise _drift_error("the token-count tree", stdout)
    return {"tree": tree, "summary": summary}


def run_metrics(profile, *, cwd: Path | None = None, output: str | None = None,
                timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Metadata-only pack (`--no-files`): counts without shipping file contents."""
    args = build_argv(profile, output=output or profile.output, extra=["--no-files"])
    result = _run(args, cwd=cwd, timeout=timeout)
    stdout = _clean(result.stdout)
    if result.returncode != 0:
        raise BackendError(
            f"repomix failed (exit {result.returncode}): {(_clean(result.stderr) or stdout)[:600]}"
        )
    summary = parse_summary(stdout, learned=_learned_labels())
    if summary.get("total_files") is None:
        raise _drift_error("the pack summary", stdout)
    return {"summary": summary, "security": parse_security(stdout)}


def run_security_check(profile, *, cwd: Path | None = None, output: str | None = None,
                       timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Secretlint scan over the profile's selection, without writing contents."""
    if profile.options.get("no_security_check"):
        raise BackendError(
            "profile disables the security check "
            "(clear it with: option set no_security_check false)"
        )
    metrics = run_metrics(profile, cwd=cwd, output=output, timeout=timeout)
    security = metrics["security"]
    if security["status"] == "unknown":
        raise BackendError(
            f"{security['detail']}. Refusing to report a clean scan that was not "
            "actually confirmed — inspect the repository manually, or run "
            "`repomix` directly to see its security output."
        )
    return security


def generate_skill(directory: Path, *, name: str | None = None, skill_output: Path | None = None,
                   compress: bool = False, include: str | None = None, ignore: str | None = None,
                   timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Run repomix's own Claude Agent Skill generator (`--skill-generate`)."""
    args = [str(directory), "--skill-generate"]
    if name:
        args.append(name)
    if skill_output:
        args += ["--skill-output", str(skill_output)]
    if compress:
        args.append("--compress")
    if include:
        args += ["--include", include]
    if ignore:
        args += ["-i", ignore]
    args.append("-f")  # non-interactive: agents cannot answer overwrite prompts

    result = _run(args, timeout=timeout)
    stdout = _clean(result.stdout)
    if result.returncode != 0:
        raise BackendError(
            f"skill generation failed (exit {result.returncode}): "
            f"{(_clean(result.stderr) or stdout)[:600]}"
        )
    root = Path(skill_output) if skill_output else None
    files = sorted(str(p) for p in root.rglob("*") if p.is_file()) if root and root.exists() else []
    if root is not None and not files:
        raise BackendError(f"repomix reported success but no skill files exist under {root}")
    return {"skill_dir": str(root) if root else None, "files": files,
            "summary": parse_summary(stdout)}


def run_file_inventory(profile, *, cwd: Path | None = None,
                       timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Per-file inventory taken from repomix's **JSON output**, not its logging.

    `--style json --stdout` suppresses all decoration and emits
    `{fileSummary, directoryStructure, files: {path: content}}`. Everything here
    is derived from that structure, so unlike the summary/token/security
    parsers this command cannot be broken by a change to repomix's console
    formatting — only by a change to its documented JSON shape.
    """
    args = build_argv(profile, extra=["--stdout"])
    # repomix rejects `--stdout` alongside `-o`, so drop the output pair; and the
    # style must be json here regardless of what the profile asks for.
    output_flag = args.index("-o")
    del args[output_flag : output_flag + 2]
    args[args.index("--style") + 1] = "json"
    result = _run(args, cwd=cwd, timeout=timeout)
    if result.returncode != 0:
        raise BackendError(
            f"repomix failed (exit {result.returncode}): "
            f"{(_clean(result.stderr) or _clean(result.stdout))[:600]}"
        )
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise _drift_error("the JSON pack output", result.stdout)
    if not isinstance(payload, dict) or "files" not in payload:
        raise _drift_error("the JSON pack output (no 'files' key)", result.stdout)

    files = payload["files"]
    inventory = sorted(
        ({"path": path, "chars": len(content or "")} for path, content in files.items()),
        key=lambda row: row["chars"],
        reverse=True,
    )
    return {
        "files": inventory,
        "total_files": len(inventory),
        "total_chars": sum(row["chars"] for row in inventory),
        "directory_structure": payload.get("directoryStructure"),
        "source": "repomix --style json --stdout",
    }


def run_doctor(*, heal: bool = False, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Self-test every parser against a fixture whose true answer is known.

    A small tree is packed with the real repomix. `--style json --stdout` gives
    the true file and character counts; the console summary is then checked
    against them. When the summary no longer parses and `heal` is set, the new
    labels are learned from that comparison and persisted.

    The security check is diagnosed but **never healed**. Every other parser can
    be validated against an independent count; a secrets verdict cannot, so
    teaching the harness a new "clean" phrase would mean trusting a guess about
    whether a repository leaks credentials. It stays fail-closed by design.
    """
    import tempfile

    from cli_it.repomix.core.knowledge import record_labels
    from cli_it.repomix.core.profile import new_profile

    version = _installed_version()
    report: dict = {
        "version": version,
        "version_tested": version_is_tested(version),
        "tested_versions": TESTED_VERSIONS,
        "healed": False,
        "learned": {},
        "checks": {},
    }

    with tempfile.TemporaryDirectory(prefix="cli-it-repomix-doctor-") as workdir:
        root = Path(workdir)
        fixture = root / "fixture"
        (fixture / "src").mkdir(parents=True)
        (fixture / "src" / "one.txt").write_text("aaaa\n", encoding="utf-8")
        (fixture / "two.txt").write_text("bb\n", encoding="utf-8")

        profile = new_profile("doctor", [str(fixture)])
        profile.output = str(root / "out.xml")

        # Ground truth, straight from repomix's JSON — no scraping involved.
        try:
            truth = run_file_inventory(profile, timeout=timeout)
            report["checks"]["json_inventory"] = {
                "ok": True,
                "total_files": truth["total_files"],
                "total_chars": truth["total_chars"],
            }
        except BackendError as exc:
            report["checks"]["json_inventory"] = {"ok": False, "detail": str(exc)}
            report["verdict"] = "unhealthy"
            report["detail"] = (
                "repomix's JSON output could not be read, so nothing can be verified "
                "against it. This is the one failure the harness cannot work around."
            )
            return report

        result = _run(build_argv(profile), timeout=timeout)
        stdout = _clean(result.stdout)

        existing = _learned_labels()
        summary = parse_summary(stdout, learned=existing)
        summary_ok = summary.get("total_files") is not None
        report["checks"]["summary"] = {"ok": summary_ok, "parsed": summary}

        if not summary_ok and heal:
            discovered = discover_summary_labels(stdout, truth)
            if discovered and version:
                record_labels(version, discovered)
                report["learned"] = discovered
                report["healed"] = True
                summary = parse_summary(stdout, learned={
                    **existing, **{k: v["field"] for k, v in discovered.items()}
                })
                summary_ok = summary.get("total_files") is not None
                report["checks"]["summary"] = {
                    "ok": summary_ok,
                    "parsed": summary,
                    "after_healing": True,
                }

        tree = parse_token_tree(
            _clean(
                _run(build_argv(profile, extra=["--token-count-tree"]), timeout=timeout).stdout
            )
        )
        report["checks"]["token_tree"] = {"ok": bool(tree), "rows": len(tree)}

        security = parse_security(stdout)
        report["checks"]["security"] = {
            "ok": security["status"] != "unknown",
            "status": security["status"],
            "healable": False,
            "note": (
                "never healed automatically: a secrets verdict has no independent "
                "ground truth to check a learned format against, so the harness "
                "fails closed instead of guessing"
            ),
        }

    failed = [name for name, check in report["checks"].items() if not check["ok"]]
    report["verdict"] = "healthy" if not failed else "degraded"
    report["failing"] = failed
    return report


def export_config(profile, path: Path, *, overwrite: bool = False) -> dict:
    """Write a `repomix.config.json` equivalent to the profile.

    Repomix's own `--init` is a multi-step interactive wizard (@clack/prompts):
    with a non-TTY stdin it exits 0 having created nothing, so it cannot be
    driven by an agent. This writes the same file directly, in the schema from
    `src/config/configSchema.ts`, from state the harness already owns — it is
    config data, not engine work, and repomix reads it back verbatim.
    """
    from cli_it.repomix.core.profile import BOOL_OPTIONS

    if path.exists() and not overwrite:
        raise BackendError(f"refusing to overwrite existing config: {path} (pass --overwrite)")

    enabled = {key for key in BOOL_OPTIONS if profile.options.get(key)}
    config = {
        "$schema": "https://repomix.com/schemas/latest/schema.json",
        "output": {
            "filePath": profile.output,
            "style": profile.style,
            "parsableStyle": "parsable_style" in enabled,
            "compress": "compress" in enabled,
            "removeComments": "remove_comments" in enabled,
            "removeEmptyLines": "remove_empty_lines" in enabled,
            "showLineNumbers": "output_show_line_numbers" in enabled,
            "includeEmptyDirectories": "include_empty_directories" in enabled,
            "truncateBase64": "truncate_base64" in enabled,
            "git": {
                "includeDiffs": "include_diffs" in enabled,
                "includeLogs": "include_logs" in enabled,
                **(
                    {"includeLogsCount": profile.include_logs_count}
                    if profile.include_logs_count
                    else {}
                ),
            },
        },
        "include": list(profile.include),
        "ignore": {
            "useGitignore": "no_gitignore" not in enabled,
            "useDefaultPatterns": "no_default_patterns" not in enabled,
            "customPatterns": list(profile.ignore),
        },
        "security": {"enableSecurityCheck": "no_security_check" not in enabled},
        "tokenCount": {"encoding": profile.token_encoding},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return {"path": str(path), "written": True, "config": config}


def read_config(path: Path) -> dict:
    """Read a repomix.config.json.

    Repomix accepts JSONC — its own shipped config carries `//` comments — so
    strip line comments and trailing commas before parsing.
    """
    if not path.is_file():
        raise BackendError(f"no repomix config at {path} (create one with: config init)")
    raw = path.read_text(encoding="utf-8")
    stripped = re.sub(r"^\s*//.*$", "", raw, flags=re.MULTILINE)
    stripped = re.sub(r",(\s*[}\]])", r"\1", stripped)
    try:
        return json.loads(stripped)
    except ValueError as exc:
        raise BackendError(f"config at {path} is not valid JSON/JSONC: {exc}")
