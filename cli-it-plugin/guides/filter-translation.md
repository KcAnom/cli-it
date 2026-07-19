# Filter translation

For media software (image editors, NLEs, DAWs) the hard part is translating a
human/agent intent ("warmer", "blur the background", "duck the music") into
the app's native filter primitives.

## Approach

1. **Enumerate native filters first** (Phase 1): dump the app's filter/effect
   registry with parameter names, types, and ranges into `<SOFTWARE>.md`.
2. **Expose primitives verbatim**: `filter add <name> --param k=v` maps 1:1 to
   the native filter; no invented names.
3. **Add intent aliases sparingly**: a curated table in the harness mapping
   common intents to native filter + parameter presets, documented in
   SKILL.md so agents know both layers.
4. **Ranges and units**: validate parameters against the native ranges and say
   what the unit is in `--help` (dB, px, 0–1) — agents guess wrong otherwise.
5. **Round-trip**: `filter list -p <project>` must show applied filters with
   their resolved native parameters so an agent can verify its edit.

Keep the translation table in one module so refining coverage
(`/cli-it:refine filters`) is a data change, not a refactor.
