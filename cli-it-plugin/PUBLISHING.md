# Publishing a harness

## 1. Package layout sanity

- `setup.py` uses `find_namespace_packages(include=["cli_it.*"])`.
- **No** `cli_it/__init__.py` anywhere (PEP 420 — a stray init breaks every
  other installed harness).
- `package_data` includes `skills/SKILL.md` and `tests/TEST.md`.
- Entry point named `cli-it-<software>`.

## 2. Local verification

```bash
pip install -e <software>/agent-harness
cli-it-<software> --help
python -m cli_it.<software> --help
pytest -q <software>/agent-harness
```

## 3. Build and upload

```bash
cd <software>/agent-harness
python -m pip install build twine
python -m build
python -m twine upload dist/*
```

For in-repo harnesses you can skip PyPI: the registry `install_cmd` may point
at the monorepo subdirectory:

```text
pip install "git+https://github.com/elev8tion/cli-it.git#subdirectory=<software>/agent-harness"
```

## 4. Registry entry

Add the entry to `registry.json` (all fields in the CONTRIBUTING.md table are
required) and run `python .github/scripts/validate_root_skills.py`.

## 5. Hub publish (maintainers)

`cli-it-hub` itself publishes via `.github/workflows/publish-cli-it.yml`
using PyPI trusted publishing — bump `cli_it_hub/__init__.py.__version__`,
merge to main, and the workflow builds/publishes if the version is new.
