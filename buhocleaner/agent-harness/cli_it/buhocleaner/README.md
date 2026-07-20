# cli-it-buhocleaner

Agent-native, stateful CLI harness for the real BuhoCleaner macOS app: read-only cleanup scans, undoable cleanup plans, live preference control, and safe hand-off to the app for actual cleaning.

BuhoCleaner ships no CLI, no AppleScript, and no URL scheme — its deletion
engine is a code-sign-gated privileged XPC helper. This harness therefore:

- **probes** (never deletes): per-category size scans of caches, logs, trash,
  screenshots, DMG installers, mail downloads, and large files;
- **plans**: a JSON cleanup-plan project with journaled, undoable mutations;
- **controls** the real app: launch/quit, Flash Clean category toggles via its
  `defaults` domain, Sparkle update check, uninstaller hand-off;
- **defers** all destruction to the real BuhoCleaner GUI, where a human
  confirms.

## Quick start

```bash
cli-it-buhocleaner backend                       # is the app installed?
cli-it-buhocleaner plan new -n weekly -o /tmp/weekly.json
cli-it-buhocleaner scan run -p /tmp/weekly.json  # read-only size probe
cli-it-buhocleaner clean open -p /tmp/weekly.json  # sync toggles, open app
cli-it-buhocleaner --json scan report -p /tmp/weekly.json
```

Run with no subcommand for the REPL. Root `--json` gives stable
machine-readable output on every command.
