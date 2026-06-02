#!/usr/bin/env python3
"""
mistakes-sweep: READ-ONLY health report for rules/mistakes-index.md.

Reports budget usage, FIXED/LOW entries that should not be in the hot index,
and entry ages. MOVES NOTHING — human decides what to archive. Always exit 0
so it is safe to wire as a SessionStart warn hook.

Run: py rules/mistakes-sweep.py
"""
import os
import re
import sys
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", str(Path.home()))))
INDEX = HOME / ".claude" / "rules" / "mistakes-index.md"
ARCHIVE = HOME / ".claude" / "rules" / "mistakes-archive.md"

BUDGET_LINES = 40          # max entry lines before "over budget"
AGE_REVIEW_DAYS = 90       # informational: surface old entries when over budget

ENTRY_RE = re.compile(
    r"^- \[(?P<sev>HIGH|MED|LOW)\](?P<fixed>\[FIXED[^\]]*\])?\s*"
    r"\[(?P<id>[\w-]+)\].*?\(x(?P<n>\d+),\s*(?P<date>\d{4}-\d{2}-\d{2})\)"
)


def parse_entries(text):
    out = []
    for line in text.splitlines():
        m = ENTRY_RE.match(line.strip())
        if not m:
            # catch entries missing a date so they can be flagged
            loose = re.match(r"^- \[(HIGH|MED|LOW)\].*\[([\w-]+)\]", line.strip())
            if loose:
                out.append({"sev": loose.group(1), "id": loose.group(2),
                            "n": None, "date": None, "fixed": "FIXED" in line})
            continue
        out.append({
            "sev": m.group("sev"),
            "id": m.group("id"),
            "n": int(m.group("n")),
            "date": m.group("date"),
            "fixed": bool(m.group("fixed")),
        })
    return out


def fix_safe():
    """Deterministic auto-action: move FIXED-marked entries from index to archive.

    FIXED is the ONLY unambiguous, advisor-sanctioned auto-move (solved → not a
    live trap). Never touches non-FIXED entries. Moves, never deletes. Returns
    list of moved ids for visibility. No-op (returns []) when no FIXED present.
    """
    if not INDEX.exists() or not ARCHIVE.exists():
        return []
    idx_lines = INDEX.read_text(encoding="utf-8").splitlines(keepends=True)
    kept, moved_lines, moved_ids = [], [], []
    for line in idx_lines:
        s = line.strip()
        if s.startswith("- [") and "FIXED" in s:
            m = re.match(r"^- \[(?:HIGH|MED|LOW)\].*\[([\w-]+)\]", s)
            moved_ids.append(m.group(1) if m else "?")
            moved_lines.append(s)
        else:
            kept.append(line)

    if not moved_ids:
        return []

    # Archive first (append-only, low risk), then rewrite index atomically.
    # If interrupted between: entry is duplicated, never lost.
    today = datetime.now().strftime("%Y-%m-%d")
    block = f"\n## Auto-archived FIXED ({today})\n" + "\n".join(moved_lines) + "\n"
    with open(ARCHIVE, "a", encoding="utf-8") as f:
        f.write(block)

    tmp = INDEX.with_suffix(".md.tmp")
    tmp.write_text("".join(kept), encoding="utf-8")
    os.replace(tmp, INDEX)
    return moved_ids


def main():
    if not INDEX.exists():
        print(f"[mistakes-sweep] index not found: {INDEX}")
        sys.exit(0)

    moved = fix_safe() if "--fix-safe" in sys.argv else []

    entries = parse_entries(INDEX.read_text(encoding="utf-8"))
    today = datetime.now().date()
    total = len(entries)

    fixed_stuck = [e for e in entries if e["fixed"]]
    low_in_index = [e for e in entries if e["sev"] == "LOW"]
    no_date = [e for e in entries if e["date"] is None]

    aged = []
    for e in entries:
        if not e["date"]:
            continue
        try:
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        age = (today - d).days
        if age >= AGE_REVIEW_DAYS:
            aged.append((age, e))
    aged.sort(key=lambda t: t[0], reverse=True)  # sort by age only; dict is not orderable on ties

    over = total > BUDGET_LINES
    flag = over or fixed_stuck or low_in_index or no_date or moved

    # --quiet: print nothing when healthy (for SessionStart wiring, no per-session spam).
    # moved (an action happened) always counts as worth surfacing.
    if "--quiet" in sys.argv and not flag:
        sys.exit(0)

    lines = []
    head = "⚠️ " if flag else "✓ "
    lines.append(f"{head}mistakes-index: {total}/{BUDGET_LINES} entries"
                 + (" — OVER BUDGET" if over else ""))

    if moved:
        lines.append(f"  ✎ auto-archived FIXED → {', '.join(moved)} "
                     f"(moved to mistakes-archive.md)")

    if fixed_stuck:
        ids = ", ".join(e["id"] for e in fixed_stuck)
        lines.append(f"  • FIXED still in index → move to archive: {ids}")
    if low_in_index:
        ids = ", ".join(e["id"] for e in low_in_index)
        lines.append(f"  • LOW in index (belongs in detail): {ids}")
    if no_date:
        ids = ", ".join(e["id"] for e in no_date)
        lines.append(f"  • missing (xN, date) stamp: {ids}")

    # Age is informational only — shown to aid human review when over budget.
    # Old != stale; never auto-archive on age alone.
    if over and aged:
        oldest = ", ".join(f"{e['id']}({age}d)" for age, e in aged[:5])
        lines.append(f"  • over budget — oldest to consider: {oldest}")
    elif aged and not over:
        lines.append(f"  • {len(aged)} entr{'y' if len(aged)==1 else 'ies'} "
                     f"≥{AGE_REVIEW_DAYS}d old (fine to keep if still valid)")

    print("\n".join(lines))
    sys.exit(0)


if __name__ == "__main__":
    main()
