"""Fire-and-forget, privacy-respecting usage telemetry.

Disabled whenever ``CLI_HUB_NO_ANALYTICS`` is set to 1/true/yes, when no
project token is configured (the in-repo default is an empty placeholder), or
when the network is unavailable — in every case events silently no-op.

Providers: PostHog (default) or Umami. Override via environment:
  CLI_HUB_ANALYTICS_PROVIDER      posthog | umami
  CLI_HUB_ANALYTICS_DISTINCT_ID   stable anonymous id override
  CLI_HUB_POSTHOG_API_HOST        PostHog ingestion host
  CLI_HUB_POSTHOG_PROJECT_TOKEN   PostHog public project token
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path

import requests

from . import __version__

# Placeholders only — never commit production tokens. Deployments set the
# CLI_HUB_POSTHOG_* environment variables instead.
DEFAULT_POSTHOG_HOST = "https://us.i.posthog.com"
DEFAULT_POSTHOG_TOKEN = ""  # empty ⇒ analytics no-op unless overridden
DEFAULT_UMAMI_HOST = ""
DEFAULT_UMAMI_WEBSITE_ID = ""

_ID_FILE = Path.home() / ".cli-it-hub" / "analytics_id"

_AGENT_ENV_HINTS = (
    "CLAUDECODE",
    "CLAUDE_CODE",
    "CURSOR_TRACE_ID",
    "CODEX_SANDBOX",
    "PI_AGENT",
    "OPENCODE",
)


def analytics_disabled() -> bool:
    return os.environ.get("CLI_HUB_NO_ANALYTICS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _provider() -> str:
    return os.environ.get("CLI_HUB_ANALYTICS_PROVIDER", "posthog").strip().lower()


def _distinct_id() -> str:
    override = os.environ.get("CLI_HUB_ANALYTICS_DISTINCT_ID")
    if override:
        return override
    try:
        if _ID_FILE.is_file():
            return _ID_FILE.read_text(encoding="utf-8").strip()
        new_id = str(uuid.uuid4())
        _ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        _ID_FILE.write_text(new_id, encoding="utf-8")
        return new_id
    except OSError:
        return "anonymous"


def detect_agent_context() -> str | None:
    """Best-effort guess at which coding agent (if any) is driving the CLI."""
    for hint in _AGENT_ENV_HINTS:
        if os.environ.get(hint):
            return hint.lower()
    try:  # parent process name, best effort
        import psutil  # type: ignore  # optional; absent in default installs

        parent = psutil.Process(os.getppid()).name().lower()
        for token in ("claude", "cursor", "codex", "pi", "node"):
            if token in parent:
                return parent
    except Exception:
        pass
    return None


def _post(url: str, payload: dict) -> None:
    try:
        requests.post(url, json=payload, timeout=3)
    except Exception:
        pass  # telemetry must never break the CLI


def capture(event: str, properties: dict | None = None) -> None:
    """Queue a telemetry event in a daemon thread; no-op when disabled."""
    if analytics_disabled():
        return
    props = dict(properties or {})
    props.setdefault("cli_it_hub_version", __version__)
    agent = detect_agent_context()
    if agent:
        props.setdefault("agent_context", agent)

    provider = _provider()
    if provider == "umami":
        host = os.environ.get("CLI_HUB_UMAMI_HOST", DEFAULT_UMAMI_HOST)
        website = os.environ.get("CLI_HUB_UMAMI_WEBSITE_ID", DEFAULT_UMAMI_WEBSITE_ID)
        if not host or not website:
            return
        url = f"{host.rstrip('/')}/api/send"
        payload = {
            "type": "event",
            "payload": {
                "website": website,
                "name": event,
                "data": props,
                "url": "/cli",
            },
        }
    else:
        host = os.environ.get("CLI_HUB_POSTHOG_API_HOST", DEFAULT_POSTHOG_HOST)
        token = os.environ.get("CLI_HUB_POSTHOG_PROJECT_TOKEN", DEFAULT_POSTHOG_TOKEN)
        if not token:
            return
        url = f"{host.rstrip('/')}/capture/"
        payload = {
            "api_key": token,
            "event": event,
            "distinct_id": _distinct_id(),
            "properties": props,
        }

    threading.Thread(target=_post, args=(url, payload), daemon=True).start()


# Convenience wrappers used across the hub -----------------------------------


def track_visit() -> None:
    capture("visit")


def track_install(name: str, ok: bool) -> None:
    capture("install", {"cli": name, "ok": ok})


def track_uninstall(name: str) -> None:
    capture("uninstall", {"cli": name})


def track_launch(name: str) -> None:
    capture("launch", {"cli": name})


def track_matrix(action: str, matrix: str, ok: bool | None = None) -> None:
    props: dict = {"matrix": matrix}
    if ok is not None:
        props["ok"] = ok
    capture(f"matrix_{action}", props)
