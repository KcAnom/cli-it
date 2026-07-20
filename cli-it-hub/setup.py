"""Packaging for cli-it-hub (console command: cli-it).

At build time the sibling ``../cli-it-matrix`` skill packs are vendored into
``cli_it_hub/_matrix_data/`` so published wheels can render matrix skills
without a repo checkout. Editable installs may skip vendoring — at runtime the
lookup order tries the repo checkout first (see cli_it_hub/matrix_skill.py).
"""

import re
import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

HERE = Path(__file__).resolve().parent
MATRIX_SOURCE = HERE.parent / "cli-it-matrix"
MATRIX_TARGET = HERE / "cli_it_hub" / "_matrix_data"


def read_version() -> str:
    text = (HERE / "cli_it_hub" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__ = "([^"]+)"', text).group(1)


def vendor_matrix_data() -> None:
    if not MATRIX_SOURCE.is_dir():
        return  # building outside the monorepo (e.g. from an sdist) — data already in place
    if MATRIX_TARGET.exists():
        shutil.rmtree(MATRIX_TARGET)
    shutil.copytree(
        MATRIX_SOURCE,
        MATRIX_TARGET,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


class BuildPyWithMatrixData(build_py):
    def run(self):
        vendor_matrix_data()
        super().run()


class SdistWithMatrixData(sdist):
    def run(self):
        vendor_matrix_data()
        super().run()


setup(
    name="cli-it-hub",
    version=read_version(),
    description=(
        "CLI-It Hub — package manager for agent-native stateful CLI harnesses"
    ),
    long_description=(HERE / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/KcAnom/cli-it",
    license="Apache-2.0",
    python_requires=">=3.10",
    packages=["cli_it_hub"],
    include_package_data=True,
    package_data={
        "cli_it_hub": [
            "_matrix_data/*/SKILL.md",
            "_matrix_data/*/references/*",
            "_matrix_data/*/scripts/*",
        ]
    },
    install_requires=[
        "click>=8.0",
        "requests>=2.28",
    ],
    entry_points={
        "console_scripts": [
            "cli-it=cli_it_hub.cli:main",
        ]
    },
    cmdclass={
        "build_py": BuildPyWithMatrixData,
        "sdist": SdistWithMatrixData,
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Build Tools",
    ],
)
