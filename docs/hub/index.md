---
layout: default
title: CLI-It Hub
---

# CLI-It Hub

**Make real software agent-native.** CLI-It wraps GUI/desktop/SaaS software in
stateful, discoverable CLI harnesses that AI coding agents drive directly —
while the real application keeps doing the rendering and exporting.

## Install the hub

```bash
pip install cli-it-hub
cli-it list
cli-it install demoapp
```

## Registries (the hub API)

The hub is registry-driven — these JSON files are the entire API surface:

- [`registry.json`](registry.json) — CLI-It harness CLIs
- [`public_registry.json`](public_registry.json) — public agent-friendly CLIs
- [`matrix_registry.json`](matrix_registry.json) — capability matrices
- [`registry-dates.json`](registry-dates.json) — last-update metadata
- [`openapi.json`](openapi.json) — OpenAPI 3.1 description of these endpoints

Matrix skill packs are published under [`matrix/<name>/SKILL.md`](matrix/).

## For agents

Read [`llms.txt`](llms.txt) (short) or [`llms-full.txt`](llms-full.txt)
(complete command reference). Capability lookup:

```bash
cli-it can "convert image" --json
cli-it matrix preflight image-design --json   # exit 3 = gaps
```

## Build your own harness

Install the plugin from the
[CLI-It repository](https://github.com/elev8tion/cli-it) and run
`/cli-it <path-or-url>` in your agent. The 7-phase methodology lives in
[`cli-it-plugin/HARNESS.md`](https://github.com/elev8tion/cli-it/blob/main/cli-it-plugin/HARNESS.md).

## Pricing

See [pricing](pricing.md) — CLI-It is free, open-source software
(Apache-2.0).
