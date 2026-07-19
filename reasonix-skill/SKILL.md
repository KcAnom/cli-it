---
name: cli-it
description: Build agent-native CLI harnesses for real software with the CLI-It 7-phase methodology.
---

# CLI-It for Reasonix

Same contract as every CLI-It adapter — this file is intentionally thin:

- **Methodology**: read and follow `cli-it-plugin/HARNESS.md` from
  https://github.com/elev8tion/cli-it (clone if absent). Phases 0–7, in
  order, no skipping the analysis or TEST.md-before-tests steps.
- **Input**: local path or GitHub URL only.
- **Workflow commands**: `cli-it-plugin/commands/{cli-it,refine,test,validate,list}.md`
  define the build / refine / test / validate / inventory flows.
- **Ecosystem**: `pip install cli-it-hub` gives `cli-it` for
  list/search/install, `can` intent lookup, matrices (`preflight` exit 3 =
  gaps), and `previews` viewing.
