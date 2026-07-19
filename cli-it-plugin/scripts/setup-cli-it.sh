#!/usr/bin/env bash
# Dev setup for a CLI-It checkout: hub + demoapp harness + test deps.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-python3}"

if [ ! -d .venv ]; then
  echo "Creating virtualenv at .venv"
  "$PYTHON" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --quiet --upgrade pip
pip install --quiet -e ./cli-it-hub
pip install --quiet -e ./demoapp/agent-harness
pip install --quiet pytest

export CLI_HUB_NO_ANALYTICS=1
echo
echo "Setup complete. Smoke check:"
cli-it --version
cli-it-demoapp --help >/dev/null && echo "cli-it-demoapp OK"
echo
echo "Run tests with: pytest -q cli-it-hub/tests cli-it-plugin/tests demoapp/agent-harness"
