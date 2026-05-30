#!/usr/bin/env python3
"""
mistake-learning Stop hook
Reads CLV2 observations for this session, detects known mistake patterns,
increments xN counter in mistakes-index.md.
"""
import json, os, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", str(Path.home()))))
MISTAKES_FILE = HOME / ".claude" / "rules" / "mistakes-index.md"
HOMUNCULUS_BASE = HOME / ".local" / "share" / "ecc-homunculus"
SESSION_WINDOW_HOURS = 4

# Known patterns: (id, tool, input_regex, entry_substring_to_match, severity)
# entry_substring_to_match = unique substring in existing mistakes-index entry
KNOWN_PATTERNS = [
    (
        "python_cmd",
        "Bash",
        r"(?<!\w)(python3?)\s",
        "python` หรือ `python3`",
        "HIGH",
    ),
    (
        "slash_path",
        "Bash",
        r"['\"]\/[A-Za-z]",
        "ใช้ `/` ใน path",
        "HIGH",
    ),
    (
        "ps_null_coal",
        "PowerShell",
        r"\?\?",
        "null-coalescing operator",
        "HIGH",
    ),
]


def load_recent_observations():
    if not HOMUNCULUS_BASE.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=SESSION_WINDOW_HOURS)
    obs = []
    for obs_file in HOMUNCULUS_BASE.rglob("observations.jsonl"):
        try:
            with open(obs_file, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        ts_str = entry.get("timestamp", "")
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if ts > cutoff:
                            obs.append(entry)
                    except Exception:
                        pass
        except Exception:
            pass
    return obs


def detect_patterns(observations):
    triggered = set()
    for entry in observations:
        if entry.get("event") != "tool_start":
            continue
        tool = entry.get("tool", "")
        inp = entry.get("input", "") or ""
        for pid, req_tool, pattern, _, severity in KNOWN_PATTERNS:
            if req_tool and tool != req_tool:
                continue
            if re.search(pattern, inp):
                triggered.add(pid)
    return triggered


def increment_xn(content, match_substring):
    """Find line containing match_substring and increment its (xN) counter."""
    lines = content.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if match_substring in line:
            m = re.search(r"\(x(\d+)\)", line)
            if m:
                n = int(m.group(1)) + 1
                lines[i] = line[: m.start()] + f"(x{n})" + line[m.end() :]
                return "".join(lines), True
    return content, False


def main():
    observations = load_recent_observations()
    if not observations:
        sys.exit(0)

    triggered = detect_patterns(observations)
    if not triggered:
        sys.exit(0)

    if not MISTAKES_FILE.exists():
        sys.exit(0)

    content = MISTAKES_FILE.read_text(encoding="utf-8")
    changed = False

    for pid, _tool, _pattern, match_sub, _sev in KNOWN_PATTERNS:
        if pid in triggered:
            content, did_change = increment_xn(content, match_sub)
            if did_change:
                changed = True

    if changed:
        today = datetime.now().strftime("%Y-%m-%d")
        content = re.sub(
            r"_Last updated:.*_",
            f"_Last updated: {today} (auto-updated by mistake-learning)_",
            content,
        )
        MISTAKES_FILE.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
