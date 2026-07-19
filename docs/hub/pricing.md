---
layout: default
title: Pricing
---

# Pricing

**CLI-It is free.** The hub (`cli-it-hub`), the methodology plugin, all
in-repo harnesses, the registries, and the matrix skill packs are open-source
software under the Apache-2.0 license. There are no paid tiers, seats, or
usage limits.

Costs that can still apply come from *third parties* a matrix provider might
use — e.g. `image.generate` via an image API needs your own API key, and
`audio.tts` via a hosted voice service bills on that provider's plan.
Preflight output (`cli-it matrix preflight <name>`) labels such providers
with `cost_tier: paid`; offline/free alternatives are listed whenever they
exist.

Self-hosting the hub site is a static file deploy (GitHub Pages or any web
server) — see the repository's `deploy-pages.yml` workflow.
