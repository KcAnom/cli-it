---
name: cli-it-buhocleaner
description: Agent-native, stateful CLI harness for the real BuhoCleaner macOS app: read-only cleanup scans, undoable cleanup plans, live preference control, and safe hand-off to the app for actual cleaning.
version: 0.2.0
license: Apache-2.0
---

# Buhocleaner — agent harness CLI

`cli-it-buhocleaner` is a CLI-It harness: a stateful command-line interface that
drives the real Buhocleaner software. Running it with no subcommand
starts an interactive REPL; every command also works non-interactively.

## Installation

```bash
pip install -e /Users/kcdacre8tor/.claude/plugins/marketplaces/cli-it/buhocleaner/agent-harness
cli-it-buhocleaner --help
```

## Command groups

| Group | Command | Description |
|-------|---------|-------------|
| `root` | `backend` | Probe the BuhoCleaner installation. |
| `app` | `info` | Show bundle version, helper, and running state. |
| `app` | `launch` | Launch (or activate) BuhoCleaner. |
| `app` | `quit` | Ask BuhoCleaner to quit (may prompt for Automation permission). |
| `app` | `update-check` | Compare the installed version against the Sparkle appcast. |
| `plan` | `new` | Create a new cleanup plan with all categories enabled. |
| `plan` | `info` | Show plan details. |
| `plan` | `save` | Re-save a plan canonically (validates + normalizes formatting). |
| `category` | `list` | List categories with enabled state and scan roots. |
| `category` | `enable` | Enable a category (journaled). |
| `category` | `disable` | Disable a category (journaled). |
| `category` | `threshold` | Set the large-files scan threshold in MB (journaled). |
| `category` | `root` | Override a category's scan root (journaled). |
| `scan` | `run` | Probe enabled categories and snapshot sizes into the plan (journaled). |
| `scan` | `report` | Show the plan's last scan snapshot. |
| `prefs` | `show` | Dump the com.drbuho.BuhoCleaner defaults domain. |
| `prefs` | `set` | Write one whitelisted toggle key (journaled; undo restores it). |
| `prefs` | `sync` | Push the plan's category toggles into the app's defaults (journaled). |
| `clean` | `open` | Optionally sync prefs from the plan, then launch BuhoCleaner. |
| `clean` | `status` | Read the live BuhoCleaner window (buttons, found-junk summary). |
| `clean` | `scan` | Drive a Flash Clean scan in the real app and report found junk. |
| `clean` | `run` | Run Flash Clean in the real app via GUI automation. |
| `uninstall` | `open` | Open APP_PATH in BuhoCleaner's uninstaller (human confirms there). |
| `session` | `status` | Show undo/redo depths and session file location. |
| `session` | `undo` | Undo the most recent journaled mutation. |
| `session` | `redo` | Redo the most recently undone mutation. |
| `preview` | `recipes` | List available preview recipes. |
| `preview` | `capture` | Write the last scan snapshot into a preview bundle and print its path. |
| `preview` | `latest` | Print the newest bundle path for a recipe. |

## Examples

**Show all commands**

```bash
cli-it-buhocleaner --help
```

**Probe the BuhoCleaner installation.**

```bash
cli-it-buhocleaner backend
```

**Show bundle version, helper, and running state.**

```bash
cli-it-buhocleaner app info
```

**Create a new cleanup plan with all categories enabled.**

```bash
cli-it-buhocleaner plan new
```

**List categories with enabled state and scan roots.**

```bash
cli-it-buhocleaner category list
```

**Probe enabled categories and snapshot sizes into the plan (journaled).**

```bash
cli-it-buhocleaner scan run
```

**Dump the com.drbuho.BuhoCleaner defaults domain.**

```bash
cli-it-buhocleaner prefs show
```

**Optionally sync prefs from the plan, then launch BuhoCleaner.**

```bash
cli-it-buhocleaner clean open
```

**Open APP_PATH in BuhoCleaner's uninstaller (human confirms there).**

```bash
cli-it-buhocleaner uninstall open
```

**Show undo/redo depths and session file location.**

```bash
cli-it-buhocleaner session status
```

**List available preview recipes.**

```bash
cli-it-buhocleaner preview recipes
```

**Machine-readable output**

```bash
cli-it-buhocleaner --json <group> <command>
```

## Agent guidance

- Pass `--json` on the root command for machine-readable output, then parse
  stdout as JSON.
- Always use **absolute paths** for project and output files.
- Check the process return code after every invocation; non-zero means the
  command failed and stderr explains why.
- Verify that expected output files exist after mutating or exporting.
- The REPL is for humans; agents should prefer one-shot subcommands.
- Session state is protected by an exclusive file lock — run one mutating
  command at a time per project.
