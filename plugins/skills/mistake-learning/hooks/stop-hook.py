#!/usr/bin/env python3
"""
mistake-learning Stop hook
Reads Claude Code session transcript (transcript_path from stdin),
detects known mistake patterns in tool_use calls,
increments xN counter in mistakes-index.md.
"""
import json, os, re, sys
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", str(Path.home()))))
MISTAKES_FILE = HOME / ".claude" / "rules" / "mistakes-index.md"

# (id, tool_name, input_field, input_regex, entry_substring, severity)
KNOWN_PATTERNS = [
    ("python_cmd",  "Bash",        "command", r"(?<!\w)python3?\s",  "[py-command]",       "HIGH"),
    ("slash_path",  "Bash",        "command", r"['\"]\/[A-Za-z]",    "[path-backslash]",   "HIGH"),
    ("ps_null_coal","PowerShell",  "command", r"\?\?",               "[ps-null-coalesce]", "HIGH"),
]


def get_transcript_path():
    try:
        data = json.loads(sys.stdin.read())
        return data.get("transcript_path")
    except Exception:
        return None


def load_tool_calls(transcript_path):
    calls = []
    try:
        with open(transcript_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") != "assistant":
                        continue
                    content = entry.get("message", {}).get("content", [])
                    if not isinstance(content, list):
                        continue
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            calls.append({
                                "tool": block.get("name", ""),
                                "input": block.get("input", {}),
                            })
                except Exception:
                    pass
    except Exception:
        pass
    return calls


def detect_patterns(tool_calls):
    triggered = set()
    for call in tool_calls:
        tool = call.get("tool", "")
        inp = call.get("input", {})
        for pid, req_tool, field, pattern, _, _sev in KNOWN_PATTERNS:
            if tool != req_tool:
                continue
            value = inp.get(field, "") or ""
            if re.search(pattern, value):
                triggered.add(pid)
    return triggered


def increment_xn(content, match_substring):
    lines = content.splitlines(keepends=True)
    today = datetime.now().strftime("%Y-%m-%d")
    for i, line in enumerate(lines):
        if match_substring not in line:
            continue
        m = re.search(r"\(x(\d+),\s*[\d-]+\)", line)
        if m:
            n = int(m.group(1)) + 1
            lines[i] = line[: m.start()] + f"(x{n}, {today})" + line[m.end() :]
            return "".join(lines), True
        m = re.search(r"\(x(\d+)\)", line)
        if m:
            n = int(m.group(1)) + 1
            lines[i] = line[: m.start()] + f"(x{n}, {today})" + line[m.end() :]
            return "".join(lines), True
    return content, False


def main():
    transcript_path = get_transcript_path()
    if not transcript_path:
        sys.exit(0)

    tool_calls = load_tool_calls(transcript_path)
    if not tool_calls:
        sys.exit(0)

    triggered = detect_patterns(tool_calls)
    if not triggered:
        sys.exit(0)

    if not MISTAKES_FILE.exists():
        sys.exit(0)

    content = MISTAKES_FILE.read_text(encoding="utf-8")
    changed = False
    for pid, _tool, _field, _pat, match_sub, _sev in KNOWN_PATTERNS:
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
