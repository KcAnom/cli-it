# CLI-It Preview Protocol

Version identifiers: `preview-bundle/v1` and `preview-trajectory/v1`.

Previews let humans see what an agent did to a project **without opening the
GUI**. The contract has two strictly separated roles:

- **Producer** — a harness CLI. Renders with the *real application*
  (headless) and writes the artifacts described here. Helper:
  `cli-it-plugin/preview_bundle.py`.
- **Consumer** — `cli-it previews …` (`cli_it_hub/preview.py`). Reads and
  displays artifacts. It never invokes application renderers.

## Preview Bundle (`preview-bundle/v1`)

A bundle is a directory:

```text
<root>/<software>/<recipe>/
  manifest.json      # identity + protocol + fingerprint + status
  summary.json       # producer-reported results + artifact index
  artifacts/         # rendered files (images, text, json, video, …)
```

Default roots: user-global `~/.cli-it/previews/`, or project-local
`<project-dir>/.cli-it/previews/` when the producer is given a project path.

### manifest.json

```json
{
  "protocol": "preview-bundle/v1",
  "software": "demoapp",
  "recipe": "render",
  "inputs": {"project": "/abs/path/demo.json"},
  "fingerprint": "sha256:…",
  "created_at": "2026-07-19T12:00:00",
  "status": "preparing | complete",
  "finalized_at": "…",
  "artifact_count": 2
}
```

### summary.json

Producer-defined results plus a mandatory `artifacts` index
(`[{"path": "artifacts/render.txt", "bytes": 123}, …]`). All numbers in the
summary must come from the actual render output — honesty is part of the
protocol.

### Caching & fingerprints

`fingerprint` is `sha256:` over canonical JSON (sorted keys, compact
separators) of the render-relevant inputs. Identical fingerprint ⇒ producers
may skip re-rendering; consumers may treat bundles as immutable once
`status == "complete"`.

### Artifact roles

Conventional names, not enforced: `render.*` (primary output), `thumb.*`
(small preview), `diff.*` (comparisons), `log.*` (engine logs). Consumers list
whatever exists.

## Live Session (`preview-trajectory/v1`)

For long operations, a session directory:

```text
<dir>/
  session.json       # {"protocol": "preview-trajectory/v1", "software", "status": "running|stopped", …}
  trajectory.json    # append-only: {"protocol": …, "events": [{"seq", "ts", "type", "message", …}]}
```

Producers append one event per meaningful step; `seq` is monotonically
increasing. Consumers poll the files (`cli-it previews watch`, default 2 s)
and render the tail. Events may carry arbitrary extra keys; consumers
normalize unknown shapes.

## Producer CLI surface (per harness)

```text
<cli> preview recipes
<cli> preview capture <recipe> [args] [--json]   # prepare → render → finalize; prints bundle path
<cli> preview latest [<recipe>]
<cli> preview diff <bundle-a> <bundle-b>
<cli> preview live start|push|status|stop
```

## Consumer surface

```text
cli-it previews inspect <ref>          # bundle or session → structured JSON
cli-it previews html <ref> [-o file]   # standalone HTML page
cli-it previews watch <ref> [--poll n] # live session, auto-refresh
cli-it previews open <ref>             # serve + open in browser
```

A `<ref>` is a directory path, a `manifest.json`/`session.json` path, or
`<software>/<recipe>` resolved under `~/.cli-it/previews/`.

## Requirements & non-goals

- Producers must render **headlessly**; a preview capture must never pop a
  GUI window.
- Missing backend ⇒ `preview capture` fails with an install hint. No
  fabricated artifacts, ever.
- **Non-goals**: this is not remote screen sharing — no framebuffer
  streaming, no input injection, no live GUI mirroring. Bundles are files on
  disk; the consumer is a viewer, not a session broker.
