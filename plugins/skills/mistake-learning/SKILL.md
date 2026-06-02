---
name: mistake-learning
description: Track and record recurring mistake patterns and provide automation to increment mistake counters in rules/mistakes-index.md via Stop hook.
---

# mistake-learning

A self-maintaining record of recurring mistakes, split across three tiered files
plus two automation scripts. The Stop hook auto-increments counters for a few
**syntactic** patterns; everything else is recorded manually.

## Three-tier storage (`rules/`)

| File | Loaded? | Holds |
|------|---------|-------|
| `mistakes-index.md` | **auto every session** | hot path. One line per live mistake: `trigger → fix (xN, date)`. Budget **≤ 40 entries**. |
| `mistakes-detail.md` | on demand | full root-cause writeups. Index links via `[id] →detail`. LOW entries go straight here, never into index. |
| `mistakes-archive.md` | never | FIXED entries + LOW > 3 months + MED that stopped growing. History in case of recurrence. |

Entry format: `- [SEVERITY] [id] trigger → fix (xN, YYYY-MM-DD)` `[→detail]`
- `xN` = times seen; `date` = last seen.
- Severity: `HIGH` (frequent/costly), `MED` (sometimes), `LOW` (once → detail only).

## Two automation scripts

### Stop hook — `hooks/stop-hook.py`
Registered under Stop hooks in `~/.claude/settings.json`. At session end it reads
the transcript (`transcript_path` from stdin), scans `tool_use` calls, and bumps
`(xN, date)` for any matched pattern. Silent (exit 0) when nothing matches. Set
dedup → at most +1 per pattern per session. Never creates entries, only increments.

**Scope is SYNTACTIC only.** A pattern qualifies only if a single tool_use input
reliably identifies the mistake. Current `KNOWN_PATTERNS`:

| id | tool | matches |
|----|------|---------|
| `py-command` | Bash | `python`/`python3` invoked as a command |
| `bash-wsl` | PowerShell | `bash 'C:/...'` (WSL trap; git-bash full-path form excluded) |
| `ps-null-coalesce` | PowerShell | `??` operator |

**Semantic mistakes stay manual** — missing `await`, save-after-merge, "read graph
first", etc. depend on outcome/intent and cannot be matched from tool input. Do not
add loose substring patterns: they over-count. Anchor every regex to a command
boundary. (A prior `slash_path` rule matched legit git-bash `/` paths and inflated
`[path-backslash]` — see `[hook-false-positive]` in detail.)

### Health sweep — `hooks/mistakes-sweep.py` (bundled in this skill)
READ-ONLY report (always exit 0). Flags over-budget, FIXED stuck in index, LOW in
index, missing date stamps, aged entries. Operates on `~/.claude/rules/mistakes-*.md`
via `USERPROFILE`/`HOME` (no hardcoded path). Wire under SessionStart.
- `py hooks/mistakes-sweep.py` — print report
- `--quiet` — print only when unhealthy (safe to wire as SessionStart warn hook)
- `--fix-safe` — the ONE deterministic auto-move: relocate FIXED entries index → archive (append-archive-first, then atomic index rewrite; moves, never deletes)

## Manual workflow

1. New mistake not auto-detected → write the index line **immediately** (don't wait for the hook).
2. Root cause longer than one line → put it in `mistakes-detail.md`, leave `[id] →detail` in index.
3. Marked `FIXED` → moves to archive (run `--fix-safe` or move by hand).
4. Over budget → review old + low-`xN` entries, archive by hand (age alone never auto-archives — old ≠ stale).

Do not duplicate entries: the hook increments existing ones.
