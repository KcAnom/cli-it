# Preview methodology (producer side)

Previews let a human watch what an agent is doing to a project without opening
the real GUI. The contract is split:

- **Producers** — harness CLIs. They render with the *real software* and write
  bundles/sessions using `cli-it-plugin/preview_bundle.py`.
- **Consumer** — `cli-it previews …`. It only reads artifacts. Never make the
  hub call an app renderer.

Full protocol: `docs/PREVIEW_PROTOCOL.md`.

## Producer CLI surface

Add a `preview` command group to the harness:

```text
<cli> preview recipes                  # list available preview recipes
<cli> preview capture <recipe> [...]   # render → finalize a bundle, print path
<cli> preview latest [<recipe>]        # print newest bundle path
<cli> preview diff <a> <b>             # compare two bundles' summaries
<cli> preview live start|push|status|stop
```

`capture` flow: `prepare_bundle()` → invoke the real software **headlessly**
to render artifacts into `artifacts/` → `finalize_bundle(summary)` → print the
bundle path (JSON with `--json`).

## Honesty rules

- A bundle must reflect what the software would actually produce — same
  renderer, same settings. No mock thumbnails, no hand-drawn approximations.
- If the backend is missing, `preview capture` must **fail** with an install
  hint, not fabricate artifacts.
- `summary.json` numbers (frame counts, durations, object counts) come from
  the render output, never from the request.
- Fingerprints are content-derived (`preview_bundle.fingerprint`) so repeated
  captures of identical state dedupe honestly.

## Live sessions

For long operations, `preview live start` creates `session.json` +
`trajectory.json`; push an event (`append_live_trajectory`) after each
meaningful step. Events are append-only; `cli-it previews watch` polls and
renders them.
