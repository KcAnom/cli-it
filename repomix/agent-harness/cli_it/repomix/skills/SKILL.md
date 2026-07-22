---
name: cli-it-repomix
description: Agent-native, stateful CLI harness for the real [repomix](https://repomix.com)
version: 0.1.0
license: Apache-2.0
---

# Repomix — agent harness CLI

`cli-it-repomix` is a CLI-It harness: a stateful command-line interface that
drives the real Repomix software. Running it with no subcommand
starts an interactive REPL; every command also works non-interactively.

## Installation

```bash
pip install -e /Users/kcdacre8tor/.claude/plugins/marketplaces/cli-it/repomix/agent-harness
cli-it-repomix --help
```

## Command groups

| Group | Command | Description |
|-------|---------|-------------|
| `root` | `backend` | Probe the real repomix installation. |
| `profile` | `new` | Create a new pack profile with repomix defaults. |
| `profile` | `info` | Show profile details. |
| `profile` | `save` | Re-save a profile canonically (validates + normalizes formatting). |
| `target` | `show` | Show the current pack target. |
| `target` | `set` | Point the profile at directories or a remote repo (undoable). |
| `filter` | `list` | List include and ignore patterns. |
| `filter` | `add` | Add a glob PATTERN to the include or ignore list (undoable). |
| `filter` | `remove` | Remove a glob PATTERN from the include or ignore list (undoable). |
| `option` | `list` | List every settable option with its current value. |
| `option` | `set` | Set option KEY to VALUE (undoable). |
| `pack` | `argv` | Print the exact repomix command this profile would run. |
| `pack` | `run` | Pack the target with the real repomix (verifies the artifact exists). |
| `analyze` | `tokens` | Token-count tree for the profile's file selection. |
| `analyze` | `metrics` | File/token/char counts via a metadata-only pack (`--no-files`). |
| `security` | `check` | Scan for credentials and secrets; exit non-zero when any are found. |
| `skill` | `generate` | Run `repomix --skill-generate` and verify the skill files exist. |
| `config` | `export` | Write a repomix.config.json equivalent to the profile. |
| `config` | `show` | Print a repomix config (JSONC comments tolerated). |
| `session` | `status` | Show journal depth and the session file path. |
| `session` | `undo` | Undo the most recent profile mutation. |
| `session` | `redo` | Redo the most recently undone mutation. |
| `preview` | `recipes` | List available preview recipes. |
| `preview` | `capture` | Write the last real pack result into a preview bundle. |
| `preview` | `latest` | Print the newest bundle path for a recipe. |

## Examples

**Show all commands**

```bash
cli-it-repomix --help
```

**Probe the real repomix installation.**

```bash
cli-it-repomix backend
```

**Create a new pack profile with repomix defaults.**

```bash
cli-it-repomix profile new
```

**Show the current pack target.**

```bash
cli-it-repomix target show
```

**List include and ignore patterns.**

```bash
cli-it-repomix filter list
```

**List every settable option with its current value.**

```bash
cli-it-repomix option list
```

**Print the exact repomix command this profile would run.**

```bash
cli-it-repomix pack argv
```

**Token-count tree for the profile's file selection.**

```bash
cli-it-repomix analyze tokens
```

**Scan for credentials and secrets; exit non-zero when any are found.**

```bash
cli-it-repomix security check
```

**Run `repomix --skill-generate` and verify the skill files exist.**

```bash
cli-it-repomix skill generate
```

**Write a repomix.config.json equivalent to the profile.**

```bash
cli-it-repomix config export
```

**Show journal depth and the session file path.**

```bash
cli-it-repomix session status
```

**List available preview recipes.**

```bash
cli-it-repomix preview recipes
```

**Machine-readable output**

```bash
cli-it-repomix --json <group> <command>
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
