# Skill generation

`SKILL.md` is how agents discover a harness without reading its source. Never
hand-write it — generate it so it stays in sync with the CLI.

## Paths and validation

Define these paths separately:

- `TARGET_PROJECT`: the acquired local source or clone root.
- `HARNESS_PATH = TARGET_PROJECT / "agent-harness"`.
- `CLI_IT_REPO_ROOT`: the optional CLI-It checkout that owns canonical skills.

Before running the generator, verify that `HARNESS_PATH` has the lexical
basename `agent-harness` and that resolving the parent and child separately
produces `resolved(TARGET_PROJECT) / "agent-harness"`. Do not pass a project or
repository root and do not silently append `agent-harness`. Absolute paths,
cwd-relative paths, `..` normalization, and symlinked project ancestors are
valid. A top-level harness symlink or nested `cli_it`, package, or output
symlink that escapes its intended root is rejected.

```bash
python cli-it-plugin/skill_generator.py "$HARNESS_PATH"
# optional explicit canonical-output root:
python cli-it-plugin/skill_generator.py "$HARNESS_PATH" \
  --repo-root "$CLI_IT_REPO_ROOT"
```

Both output destinations are boundary-checked before either is written:

1. `$CLI_IT_REPO_ROOT/skills/cli-it-<software>/SKILL.md` — canonical;
   consumed by `npx skills add …` and by the ReplSkin banner in a checkout.
2. `$HARNESS_PATH/cli_it/<software>/skills/SKILL.md` — packaged copy shipped
   in wheels so installed harnesses stay self-describing.

An explicit repository root must already exist and contain both the
`registry.json` file and `skills/` directory markers; invalid roots are
rejected before either output is written. When no repository root is supplied,
the generator searches ancestors for those markers; otherwise it writes only
the packaged copy.

## How it extracts metadata

- Finds `cli_it/<software>/` and parses `<software>_cli.py` Click decorators
  (regex-based; the harness is not imported).
- Version from `setup.py`, description from the first prose line of the
  harness README.
- Renders `templates/SKILL.md.template` (`{{ var }}` substitution; the
  command-group table and examples are pre-rendered blocks).

## When to regenerate

Any time commands, groups, help text, or the version change — and always
during Phase 6.5. `/cli-it:validate` flags root/package skill drift.
