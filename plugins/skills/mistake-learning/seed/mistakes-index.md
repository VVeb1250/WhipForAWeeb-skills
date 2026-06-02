# Mistakes Index

> Auto-loaded every session. Format: `- [SEV] [id] trigger → fix (xN, date)` [→detail].
> SEV: HIGH=frequent/costly, MED=sometimes, LOW→detail only. Maintenance rules (tier/budget≤40/sweep/FIXED→archive) → mistake-learning SKILL.md.

---

## CODING

(none yet)

---

## COMMANDS / SHELL

> These three are auto-incremented by the Stop hook (see SKILL.md). Edit/remove if not relevant to your OS.

- [HIGH] [py-command] `python`/`python3` not found (Windows) → use `py` (x1, 2026-01-01)
- [HIGH] [ps-null-coalesce] `??` in PowerShell → parse error (PS 5.1) → use `if/else` (x1, 2026-01-01)
- [HIGH] [bash-wsl] PowerShell calls `bash 'C:/...'` → WSL treats as Linux path → exit 127 → use git-bash full path (x1, 2026-01-01)

---

## WORKFLOW

(none yet)

---
Detail → mistakes-detail.md | Archive → mistakes-archive.md | Sweep → mistake-learning/hooks/mistakes-sweep.py
_Last updated: 2026-01-01_
