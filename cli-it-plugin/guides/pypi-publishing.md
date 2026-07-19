# PyPI publishing for harnesses

## Namespace packaging is the whole trick

All harnesses share the `cli_it` namespace (PEP 420). That only works if **no
distribution ever ships `cli_it/__init__.py`** — one stray init file shadows
every other installed harness.

```python
from setuptools import find_namespace_packages, setup

setup(
    name="cli-it-<software>",
    version="0.1.0",
    packages=find_namespace_packages(include=["cli_it.*"]),
    include_package_data=True,
    package_data={"cli_it.<software>": ["skills/SKILL.md", "tests/TEST.md"]},
    python_requires=">=3.10",
    install_requires=["click>=8.0"],
    entry_points={
        "console_scripts": [
            "cli-it-<software>=cli_it.<software>.<software>_cli:cli",
        ]
    },
)
```

## Checklist before upload

- `python -m build` produces a wheel; `unzip -l dist/*.whl` shows
  `cli_it/<software>/…` and **no** top-level `cli_it/__init__.py`.
- Fresh-venv smoke: `pip install dist/*.whl && cli-it-<software> --help`.
- SKILL.md packaged copy present in the wheel.
- Version bumped everywhere it appears (setup.py is the source of truth).

## Upload

`python -m twine upload dist/*`, or skip PyPI entirely and register with a
git-subdirectory `install_cmd` (see PUBLISHING.md).
