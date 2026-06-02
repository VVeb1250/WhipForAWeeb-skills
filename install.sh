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

# mistake-learning needs rules/mistakes-*.md to exist. Seed them ONLY if absent —
# never overwrite an existing record.
RULES="${HOME}/.claude/rules"
SEED="$SCRIPT_DIR/plugins/skills/mistake-learning/seed"
if [ -d "$SEED" ]; then
  mkdir -p "$RULES"
  for f in mistakes-index.md mistakes-detail.md mistakes-archive.md; do
    if [ ! -f "$RULES/$f" ]; then
      cp "$SEED/$f" "$RULES/$f"
      echo "  seeded: rules/$f"
    fi
  done
fi
echo "Done. Add hooks to ~/.claude/settings.json — see README."
