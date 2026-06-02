---
name: mistake-learning
description: Track and record recurring mistake patterns and provide automation to increment mistake counters in rules/mistakes-index.md via Stop hook.
---

# mistake-learning

Stop hook that increments `(xN)` counters in `rules/mistakes-index.md` when known mistake patterns appear in a session's tool_use calls.

Reads the session transcript directly from `transcript_path` (provided via stdin by Claude Code at session end) — no CLV2/ecc-homunculus dependency.

Install behavior:
- `hooks/stop-hook.py` registered under Stop hooks in `~/.claude/settings.json`
- Runs automatically at session end; silent (exit 0) when no patterns match

Do not duplicate entries: the hook increments existing entries when patterns match.
