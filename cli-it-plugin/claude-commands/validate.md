---
description: Validate a harness against the HARNESS.md checklist
---

# /cli-it:validate — conformance check

## Asset root

Read `${CLAUDE_PLUGIN_ROOT}/HARNESS.md`, then execute
`${CLAUDE_PLUGIN_ROOT}/commands/validate.md`. Read every
`cli-it-plugin/<file>` reference in either document as
`${CLAUDE_PLUGIN_ROOT}/<file>` — in particular, the `utils/repl_skin.py`
identity check compares against `${CLAUDE_PLUGIN_ROOT}/repl_skin.py`.

The canonical-skill and registry checks apply only when a real
`CLI_IT_REPO_ROOT` checkout is present. Without one, mark those items **n/a**
with that reason rather than failing them.

## Guardrails

Perform no file reads, installs, or checks until the candidate's path contract
passes: exact `agent-harness` basename, parent and child resolved separately,
child equal to `resolved(TARGET_PROJECT)/agent-harness`, and no `cli_it/`,
package, or output path escaping the harness. Do not repair an invalid path.

Print the full pass/fail checklist with evidence — file paths and real command
output, not assertions. Report each failure with the specific fix needed, then
offer to apply them.
