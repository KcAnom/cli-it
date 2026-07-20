# skills/ — canonical agent skills

This directory is the canonical, `npx skills`-compatible home for every
CLI-It skill:

- `cli-it-meta-skill/` — ecosystem catalog skill (mirrors
  `/cli-it-meta-skill/SKILL.md` at the repo root; CI regenerates it from
  `registry.json`).
- `cli-it-<software>/` — one skill per in-repo harness, **generated** by
  `cli-it-plugin/skill_generator.py` (never hand-edited). Each harness also
  packages a copy at `cli_it/<software>/skills/SKILL.md`; the two must match
  (`python .github/scripts/validate_root_skills.py`).

Install into an agent:

```bash
npx skills add KcAnom/cli-it --skill cli-it-meta-skill -g -y
npx skills add KcAnom/cli-it --skill cli-it-demoapp -g -y
```
