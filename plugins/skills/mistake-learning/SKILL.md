---
name: mistake-learning
description: Track and record recurring mistake patterns and provide automation to increment mistake counters in rules/mistakes-index.md via Stop hook.
---

# mistake-learning

This packaged copy provides the Stop hook that increments `(xN)` counters in `rules/mistakes-index.md` when specific patterns are observed. The canonical source remains in `skills/mistake-learning/`, but this plugin includes a minimal `hooks/stop-hook.py` so the packaged plugin is self-contained.

Install behavior:
- `plugins/skills/mistake-learning/hooks/stop-hook.py` will be invoked by the plugin Stop hook.

Do not duplicate entries: the hook increments existing entries when patterns match.
