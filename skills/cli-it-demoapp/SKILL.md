---
name: cli-it-demoapp
description: Stateful CLI-It harness for DemoApp: JSON project files with locked sessions, undo/redo journaling, and rendering through the real external DemoApp engine process.
version: 0.1.0
license: Apache-2.0
---

# Demoapp — agent harness CLI

`cli-it-demoapp` is a CLI-It harness: a stateful command-line interface that
drives the real Demoapp software. Running it with no subcommand
starts an interactive REPL; every command also works non-interactively.

## Installation

```bash
pip install -e /Users/kcdacre8tor/.claude/plugins/marketplaces/cli-it/demoapp/agent-harness
cli-it-demoapp --help
```

## Command groups

| Group | Command | Description |
|-------|---------|-------------|
| `project` | `new` | Create a new project file. |
| `project` | `open` | Validate a project and ensure its session exists. |
| `project` | `info` | Show project details. |
| `project` | `save` | Re-save a project canonically (validates + normalizes formatting). |
| `item` | `add` | Add an item to the project (auto-saves, journaled). |
| `item` | `list` | List project items. |
| `item` | `remove` | Remove an item by id (auto-saves, journaled). |
| `session` | `status` | Show undo/redo depths and session file location. |
| `session` | `undo` | Undo the most recent journaled mutation. |
| `session` | `redo` | Redo the most recently undone mutation. |
| `export` | `run` | Render the project to a file via the external engine process. |
| `root` | `backend` | Probe the DemoApp engine backend. |
| `preview` | `recipes` | List available preview recipes. |
| `preview` | `capture` | Render the project into a preview bundle and print its path. |
| `preview` | `latest` | Print the newest bundle path for a recipe. |

## Examples

**Show all commands**

```bash
cli-it-demoapp --help
```

**Create a new project file.**

```bash
cli-it-demoapp project new
```

**Add an item to the project (auto-saves, journaled).**

```bash
cli-it-demoapp item add
```

**Show undo/redo depths and session file location.**

```bash
cli-it-demoapp session status
```

**Render the project to a file via the external engine process.**

```bash
cli-it-demoapp export run
```

**Probe the DemoApp engine backend.**

```bash
cli-it-demoapp backend
```

**List available preview recipes.**

```bash
cli-it-demoapp preview recipes
```

**Machine-readable output**

```bash
cli-it-demoapp --json <group> <command>
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
