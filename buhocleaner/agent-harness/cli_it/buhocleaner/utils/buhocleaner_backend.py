"""The BuhoCleaner backend boundary.

This is the ONLY module that touches the real BuhoCleaner installation.
BuhoCleaner ships no CLI, no AppleScript dictionary, and no URL scheme; its
destructive engine is a code-sign-gated privileged XPC helper that third-party
code must not (and cannot) drive. The real surface this module wraps:

  - launch/activate via `open -b com.drbuho.BuhoCleaner` (optionally handing
    an .app bundle to Buho's uninstaller Service),
  - graceful quit via Apple Events (may prompt for Automation permission),
  - the live `com.drbuho.BuhoCleaner` defaults domain (scan-category toggles),
  - Sparkle appcast update check,
  - privileged-helper / menu-agent presence probes.

The harness itself never deletes files — cleaning is always confirmed by the
human inside the real app.
"""

from __future__ import annotations

import json
import plistlib
import re
import subprocess
from pathlib import Path

BUNDLE_ID = "com.drbuho.BuhoCleaner"
APP_PATH = Path("/Applications/BuhoCleaner.app")
HELPER_PATH = Path(
    "/Library/PrivilegedHelperTools/com.drbuho.BuhoCleaner.PrivilegedHelperTool"
)
MENU_AGENT = APP_PATH / "Contents/Library/LoginItems/BuhoCleanerMenu.app"
INSTALL_HINT = "Install BuhoCleaner from https://www.drbuho.com/buhocleaner"

# Defaults keys the harness may write (Flash Clean category checkboxes).
# Everything else in the domain is read-only from the harness's viewpoint.
WRITABLE_TOGGLE_KEYS = {
    "userCacheFilesSelected",
    "systemCacheFilesSelected",
    "systemLogFilesSelected",
    "trashCanSelected",
    "screenshotFilesSelected",
    "unusedDMGFilesSelected",
    "mailDownloadsFilesSelected",
    "browserCacheSelected",
    "purgeableSpaceSelected",
}


class BackendError(RuntimeError):
    pass


def _run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise BackendError(f"required macOS tool missing: {cmd[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise BackendError(f"timed out running: {' '.join(cmd)}") from exc


def app_path() -> Path:
    return APP_PATH


def backend_available() -> bool:
    return (APP_PATH / "Contents/Info.plist").is_file()


def require_backend() -> None:
    if not backend_available():
        raise BackendError(f"BuhoCleaner.app not found at {APP_PATH}. {INSTALL_HINT}")


def app_version() -> dict:
    require_backend()
    with open(APP_PATH / "Contents/Info.plist", "rb") as fh:
        info = plistlib.load(fh)
    return {
        "version": info.get("CFBundleShortVersionString", "?"),
        "build": info.get("CFBundleVersion", "?"),
        "feed_url": info.get("SUFeedURL"),
    }


def is_running() -> bool:
    return _run(["pgrep", "-x", "BuhoCleaner"]).returncode == 0


def launch(open_paths: list[str | Path] | None = None) -> None:
    """Launch/activate BuhoCleaner, optionally handing it file arguments."""
    require_backend()
    cmd = ["open", "-b", BUNDLE_ID]
    for path in open_paths or []:
        cmd.append(str(path))
    result = _run(cmd)
    if result.returncode != 0:
        raise BackendError(f"open failed: {result.stderr.strip()}")


def open_uninstaller(target_app: str | Path) -> None:
    """Hand an .app bundle to BuhoCleaner's uninstaller Service."""
    target = Path(target_app)
    if not (target.suffix == ".app" and target.is_dir()):
        raise BackendError(f"not an application bundle: {target}")
    launch([target])


def quit_app() -> bool:
    """Ask BuhoCleaner to quit via Apple Events (may prompt for Automation)."""
    if not is_running():
        return False
    result = _run(["osascript", "-e", f'quit app id "{BUNDLE_ID}"'])
    if result.returncode != 0:
        raise BackendError(f"quit failed: {result.stderr.strip()}")
    return True


# --- defaults domain ---------------------------------------------------------


def read_prefs() -> dict:
    """Read the live com.drbuho.BuhoCleaner defaults domain as a dict."""
    require_backend()
    result = _run(["defaults", "export", BUNDLE_ID, "-"])
    if result.returncode != 0:
        raise BackendError(
            f"defaults export failed: {result.stderr.strip() or 'domain missing'}"
        )
    doc = plistlib.loads(result.stdout.encode("utf-8"))
    return {key: (value if isinstance(value, (str, int, float, bool)) else repr(value))
            for key, value in sorted(doc.items())}


def read_pref(key: str):
    """Read one key; returns None when absent."""
    require_backend()
    result = _run(["defaults", "read", BUNDLE_ID, key])
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def write_pref(key: str, value, value_type: str = "bool") -> None:
    """Write one whitelisted key into the app's defaults domain."""
    require_backend()
    if key not in WRITABLE_TOGGLE_KEYS:
        raise BackendError(
            f"refusing to write non-whitelisted key {key!r} "
            f"(writable: {', '.join(sorted(WRITABLE_TOGGLE_KEYS))})"
        )
    flags = {"bool": "-bool", "int": "-int", "string": "-string"}
    if value_type not in flags:
        raise BackendError(f"unsupported type {value_type!r} (bool|int|string)")
    result = _run(["defaults", "write", BUNDLE_ID, key, flags[value_type], str(value)])
    if result.returncode != 0:
        raise BackendError(f"defaults write failed: {result.stderr.strip()}")


# --- update check ------------------------------------------------------------


def update_check(timeout: int = 15) -> dict:
    """Fetch the Sparkle appcast and compare against the installed version."""
    info = app_version()
    feed = info.get("feed_url")
    if not feed:
        raise BackendError("no SUFeedURL in Info.plist")
    result = _run(["curl", "-fsSL", "--max-time", str(timeout), feed], timeout=timeout + 5)
    if result.returncode != 0:
        raise BackendError(f"appcast fetch failed: {result.stderr.strip() or feed}")
    versions = re.findall(r'sparkle:shortVersionString="([^"]+)"', result.stdout)
    latest = versions[0] if versions else None
    return {
        "installed": info["version"],
        "latest": latest,
        "up_to_date": (latest == info["version"]) if latest else None,
        "feed_url": feed,
    }


# --- probe -------------------------------------------------------------------


def probe() -> dict:
    """Structured backend health info for `--json` consumers."""
    available = backend_available()
    info: dict = {
        "available": available,
        "app_path": str(APP_PATH),
        "bundle_id": BUNDLE_ID,
    }
    if available:
        info.update(app_version())
        info["running"] = is_running()
        info["helper_installed"] = HELPER_PATH.exists()
        info["menu_agent"] = MENU_AGENT.exists()
    else:
        info["install_hint"] = INSTALL_HINT
    return info


if __name__ == "__main__":
    print(json.dumps(probe(), indent=2))
