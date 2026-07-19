# DemoApp harness

Stateful CLI-It harness for DemoApp: JSON project files with locked sessions, undo/redo journaling, and rendering through the real external DemoApp engine process.

DemoApp is the *exemplar* harness of the CLI-It monorepo — its "engine" is a
deliberately trivial external Python renderer, so the harness demonstrates
every convention (backend boundary, PEP 420 namespace, ReplSkin REPL, dual
SKILL.md, preview bundles) without requiring Blender-sized software.

## Usage

```bash
cli-it-demoapp                                     # REPL
cli-it-demoapp project new -n demo -o /tmp/demo.json
cli-it-demoapp item add -p /tmp/demo.json -n hello -k note
cli-it-demoapp --json project info -p /tmp/demo.json
cli-it-demoapp session undo -p /tmp/demo.json
cli-it-demoapp export run -p /tmp/demo.json -o /tmp/demo.txt
cli-it-demoapp preview capture -p /tmp/demo.json
```

Agents: read `skills/SKILL.md` (or the repo-root copy at
`skills/cli-it-demoapp/SKILL.md`).
