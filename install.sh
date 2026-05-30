#!/usr/bin/env bash
set -e
DEST="${HOME}/.claude/skills"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$DEST"
for skill in graphify-link codegraph-link mistake-learning; do
  src="$SCRIPT_DIR/plugins/skills/$skill"
  if [ -d "$src" ]; then
    cp -r "$src" "$DEST/"
    echo "  installed: $skill"
  fi
done
echo "Done. Add hooks to ~/.claude/settings.json — see README."
