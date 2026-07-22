from pathlib import Path

from setuptools import find_namespace_packages, setup

HERE = Path(__file__).resolve().parent

setup(
    name="cli-it-repomix",
    version="0.3.0",
    description="CLI-It agent harness for the repomix codebase packer",
    long_description=(HERE / "cli_it" / "repomix" / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/KcAnom/cli-it",
    license="Apache-2.0",
    python_requires=">=3.10",
    packages=find_namespace_packages(include=["cli_it.*"]),
    include_package_data=True,
    package_data={
        "cli_it.repomix": ["skills/SKILL.md", "tests/TEST.md", "README.md"],
    },
    install_requires=["click>=8.0"],
    extras_require={"repl": ["prompt_toolkit>=3.0"]},
    entry_points={
        "console_scripts": [
            "cli-it-repomix=cli_it.repomix.repomix_cli:cli",
        ]
    },
)
