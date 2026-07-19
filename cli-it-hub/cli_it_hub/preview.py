"""Generic preview *consumer* for CLI-It preview bundles and live sessions.

Harness CLIs are the producers (see cli-it-plugin/preview_bundle.py and
docs/PREVIEW_PROTOCOL.md). This module only reads the artifacts a producer
wrote — it never invokes application renderers.

A bundle ref may be:
  * a path to a bundle directory (contains manifest.json + summary.json)
  * a path to a manifest.json inside a bundle
  * "<software>/<recipe>" resolved under ~/.cli-it/previews/

A live session ref is a directory (or session.json path) containing
session.json and, optionally, an append-only trajectory.json.
"""

from __future__ import annotations

import functools
import html
import json
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PREVIEWS_ROOT = Path.home() / ".cli-it" / "previews"


class PreviewError(RuntimeError):
    pass


def resolve_bundle(ref: str) -> Path:
    path = Path(ref).expanduser()
    if path.name == "manifest.json" and path.is_file():
        path = path.parent
    if not path.is_dir() and "/" in ref and not ref.startswith((".", "/", "~")):
        path = PREVIEWS_ROOT / ref
    if not (path / "manifest.json").is_file():
        raise PreviewError(f"'{ref}' is not a preview bundle (no manifest.json)")
    return path.resolve()


def resolve_session(ref: str) -> Path:
    path = Path(ref).expanduser()
    if path.name == "session.json" and path.is_file():
        path = path.parent
    if not path.is_dir() and "/" in ref and not ref.startswith((".", "/", "~")):
        path = PREVIEWS_ROOT / ref
    if not (path / "session.json").is_file():
        raise PreviewError(f"'{ref}' is not a live preview session (no session.json)")
    return path.resolve()


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PreviewError(f"cannot read {path}: {exc}") from exc


def normalize_trajectory_events(raw_events: list) -> list[dict]:
    """Coerce heterogeneous producer events into display-ready dicts."""
    events = []
    for i, event in enumerate(raw_events):
        if not isinstance(event, dict):
            event = {"message": str(event)}
        events.append(
            {
                "seq": event.get("seq", i),
                "ts": event.get("ts"),
                "type": event.get("type", "event"),
                "message": event.get("message", ""),
                "data": {
                    k: v
                    for k, v in event.items()
                    if k not in ("seq", "ts", "type", "message")
                },
            }
        )
    return events


def inspect_bundle(ref: str) -> dict:
    bundle = resolve_bundle(ref)
    manifest = _read_json(bundle / "manifest.json")
    summary_path = bundle / "summary.json"
    summary = _read_json(summary_path) if summary_path.is_file() else {}
    artifacts_dir = bundle / "artifacts"
    artifacts = []
    if artifacts_dir.is_dir():
        for artifact in sorted(artifacts_dir.rglob("*")):
            if artifact.is_file():
                artifacts.append(
                    {
                        "path": str(artifact.relative_to(bundle)),
                        "bytes": artifact.stat().st_size,
                    }
                )
    return {
        "bundle": str(bundle),
        "protocol": manifest.get("protocol"),
        "software": manifest.get("software"),
        "recipe": manifest.get("recipe"),
        "fingerprint": manifest.get("fingerprint"),
        "created_at": manifest.get("created_at"),
        "manifest": manifest,
        "summary": summary,
        "artifacts": artifacts,
    }


def inspect_session(ref: str) -> dict:
    session_dir = resolve_session(ref)
    session = _read_json(session_dir / "session.json")
    trajectory_path = session_dir / "trajectory.json"
    events: list[dict] = []
    if trajectory_path.is_file():
        raw = _read_json(trajectory_path)
        events = normalize_trajectory_events(
            raw.get("events", []) if isinstance(raw, dict) else raw
        )
    return {
        "session_dir": str(session_dir),
        "protocol": session.get("protocol"),
        "software": session.get("software"),
        "status": session.get("status"),
        "session": session,
        "events": events,
        "event_count": len(events),
    }


# --- HTML rendering ----------------------------------------------------------

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
{refresh}
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; margin: 2rem auto; max-width: 60rem; padding: 0 1rem; color: #1d2939; }}
  h1 {{ font-size: 1.4rem; }} code {{ background: #f2f4f7; padding: .1em .3em; border-radius: 4px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ text-align: left; border-bottom: 1px solid #e4e7ec; padding: .4rem .6rem; font-size: .9rem; }}
  .meta {{ color: #667085; font-size: .85rem; }}
  pre {{ background: #f9fafb; border: 1px solid #e4e7ec; border-radius: 6px; padding: 1rem; overflow-x: auto; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="meta">{subtitle}</p>
{body}
</body>
</html>
"""


def _table(rows: list[tuple[str, str]]) -> str:
    body = "".join(
        f"<tr><th>{html.escape(k)}</th><td>{html.escape(str(v))}</td></tr>"
        for k, v in rows
    )
    return f"<table>{body}</table>"


def render_html(ref: str) -> str:
    info = inspect_bundle(ref)
    artifact_rows = "".join(
        f"<tr><td><code>{html.escape(a['path'])}</code></td>"
        f"<td>{a['bytes']} bytes</td></tr>"
        for a in info["artifacts"]
    ) or "<tr><td colspan=2 class=meta>no artifacts</td></tr>"
    body = _table(
        [
            ("Protocol", info.get("protocol") or "?"),
            ("Software", info.get("software") or "?"),
            ("Recipe", info.get("recipe") or "?"),
            ("Fingerprint", info.get("fingerprint") or "?"),
            ("Created", info.get("created_at") or "?"),
        ]
    )
    body += f"<h2>Artifacts</h2><table><tr><th>Path</th><th>Size</th></tr>{artifact_rows}</table>"
    body += (
        "<h2>Summary</h2><pre>"
        + html.escape(json.dumps(info["summary"], indent=2))
        + "</pre>"
    )
    return _PAGE.format(
        refresh="",
        title=f"Preview — {info.get('software') or 'bundle'} / {info.get('recipe') or ''}",
        subtitle=f"bundle at <code>{html.escape(info['bundle'])}</code>",
        body=body,
    )


def render_live_html(ref: str, poll_seconds: int = 2) -> str:
    info = inspect_session(ref)
    event_rows = "".join(
        f"<tr><td>{e['seq']}</td><td>{html.escape(str(e['ts'] or ''))}</td>"
        f"<td><code>{html.escape(e['type'])}</code></td>"
        f"<td>{html.escape(e['message'])}</td></tr>"
        for e in info["events"][-200:]
    ) or "<tr><td colspan=4 class=meta>no events yet</td></tr>"
    body = _table(
        [
            ("Protocol", info.get("protocol") or "?"),
            ("Software", info.get("software") or "?"),
            ("Status", info.get("status") or "?"),
            ("Events", info["event_count"]),
        ]
    )
    body += (
        "<h2>Trajectory</h2><table><tr><th>#</th><th>Time</th><th>Type</th>"
        f"<th>Message</th></tr>{event_rows}</table>"
    )
    refresh = f'<meta http-equiv="refresh" content="{poll_seconds}">'
    return _PAGE.format(
        refresh=refresh,
        title=f"Live preview — {info.get('software') or 'session'}",
        subtitle=(
            f"session at <code>{html.escape(info['session_dir'])}</code> "
            f"(auto-refreshes every {poll_seconds}s)"
        ),
        body=body,
    )


# --- serving -----------------------------------------------------------------


def start_static_server(
    directory: str | Path, host: str = "127.0.0.1", port: int = 0
) -> tuple[ThreadingHTTPServer, str]:
    """Serve a directory in a background thread; returns (server, url)."""
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://{host}:{server.server_address[1]}/"
    return server, url


def open_in_browser(url: str) -> bool:
    try:
        return webbrowser.open(url)
    except Exception:
        return False
