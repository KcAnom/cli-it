#!/usr/bin/env bash
# Install the CLI-It skill for Codex-style agents that read ~/.codex/skills.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${CODEX_SKILLS_DIR:-$HOME/.codex/skills}/cli-it"
mkdir -p "$DEST"
cp "$SRC/SKILL.md" "$DEST/"
echo "Installed CLI-It skill → $DEST"
