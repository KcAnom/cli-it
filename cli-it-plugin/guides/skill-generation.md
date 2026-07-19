# Skill generation

`SKILL.md` is how agents discover a harness without reading its source. Never
hand-write it — generate it so it stays in sync with the CLI.

## Run

```bash
python cli-it-plugin/skill_generator.py <software>/agent-harness
# optional explicit root:
python cli-it-plugin/skill_generator.py <software>/agent-harness --repo-root /path/to/cli-it
```

Two files are written (dual-write convention):

1. `<repo>/skills/cli-it-<software>/SKILL.md` — canonical; consumed by
   `npx skills add …` and by the ReplSkin banner in a checkout.
2. `<harness>/cli_it/<software>/skills/SKILL.md` — packaged copy shipped in
   wheels so installed harnesses stay self-describing.

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
