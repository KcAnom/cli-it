---
name: cli-it-matrix-knowledge-research
description: Capability matrix for research workflows — search the web, fetch documents, structure findings.
version: 0.1.0
---

# Knowledge & Research matrix

```bash
cli-it matrix preflight knowledge-research --json
```

## Capabilities

- `web.search` — use the host agent's built-in web-search tooling
  (`agent-native`/`web-search` provider; no install).
- `doc.fetch` — fetch and convert pages/PDFs to text (`curl` or Python
  `requests`).

## Workflow

1. **Search** broadly with several query formulations; collect candidate
   sources with URLs.
2. **Fetch** each source (`doc.fetch`); keep the raw copy next to your notes
   so claims stay citable.
3. **Verify** load-bearing claims against at least two independent sources.
4. **Structure** findings with explicit citations; separate facts from
   inference.

<!-- MATRIX_SKILL_PATHS:START -->
(rendered locally by `cli-it matrix skill knowledge-research`)
<!-- MATRIX_SKILL_PATHS:END -->
