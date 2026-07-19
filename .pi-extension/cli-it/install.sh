#!/usr/bin/env bash
# Install the CLI-It Pi extension: copy the extension and the plugin assets it
# reads at runtime into the Pi extensions directory.
set -euo pipefail

EXT_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$EXT_SRC/../.." && pwd)"
PLUGIN_DIR="$REPO_ROOT/cli-it-plugin"
DEST="${PI_EXTENSIONS_DIR:-$HOME/.pi/agent/extensions}/cli-it"

if [ ! -f "$PLUGIN_DIR/HARNESS.md" ]; then
  echo "error: cli-it-plugin/HARNESS.md not found — run from a CLI-It checkout" >&2
  exit 1
fi

echo "Installing CLI-It Pi extension → $DEST"
mkdir -p "$DEST/scripts"

# Extension code
cp "$EXT_SRC/index.ts" "$DEST/"
cp "$EXT_SRC/README.md" "$DEST/"

# Plugin assets the extension reads at runtime
cp "$PLUGIN_DIR/HARNESS.md" "$DEST/"
cp -R "$PLUGIN_DIR/commands" "$DEST/"
cp -R "$PLUGIN_DIR/guides" "$DEST/"
cp -R "$PLUGIN_DIR/templates" "$DEST/"
cp "$PLUGIN_DIR/skill_generator.py" "$DEST/"
cp "$PLUGIN_DIR/preview_bundle.py" "$DEST/"
cp "$PLUGIN_DIR/repl_skin.py" "$DEST/scripts/repl_skin.py"

echo "Done. Restart Pi to pick up the cli-it commands:"
echo "  /cli-it <path-or-url> · /cli-it:refine · /cli-it:test · /cli-it:validate · /cli-it:list"
