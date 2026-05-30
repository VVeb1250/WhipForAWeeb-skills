# WhipForAWeeb Skills Pack

Three Claude Code skills packaged as a plugin.

## Included Skills

| Skill | What it does |
|-------|-------------|
| `graphify-link` | Links a project to a graphify knowledge graph. Manages `graphify-roots.json`, installs fast-path drivers (`graphify-build.py`, `graphify-update.py`), starts `graphify watch`. |
| `codegraph-link` | Wires a project to the CodeGraph MCP (`@colbymchenry/codegraph`). Writes/removes the managed role-split block in `CLAUDE.md`. |
| `mistake-learning` | Stop hook that reads CLV2 session observations, detects known mistake patterns, and increments `(xN)` counters in `~/.claude/rules/mistakes-index.md`. |

## Requirements

- Python 3 — `py` launcher (Windows) or `python3` (macOS/Linux)
- `graphify` CLI — `graphify-link` skill only
- `codegraph` CLI — `codegraph-link` skill only
- `~/.claude/rules/mistakes-index.md` — `mistake-learning` skill only

> PowerShell is **not** required. All hooks are pure Python.

## Installation

### Manual

Copy the skill directories you want into `~/.claude/skills/`:

```powershell
# Windows
Copy-Item -Recurse "plugins\skills\graphify-link"    "$env:USERPROFILE\.claude\skills\"
Copy-Item -Recurse "plugins\skills\codegraph-link"   "$env:USERPROFILE\.claude\skills\"
Copy-Item -Recurse "plugins\skills\mistake-learning" "$env:USERPROFILE\.claude\skills\"
```

```bash
# macOS / Linux
cp -r plugins/skills/graphify-link    ~/.claude/skills/
cp -r plugins/skills/codegraph-link   ~/.claude/skills/
cp -r plugins/skills/mistake-learning ~/.claude/skills/
```

### Registering hooks in `~/.claude/settings.json`

**mistake-learning Stop hook — Windows:**

```json
{
  "hooks": {
    "Stop": [
      {
        "command": "py \"%USERPROFILE%\\.claude\\skills\\mistake-learning\\hooks\\stop-hook.py\"",
        "description": "Increment mistake counters on session end"
      }
    ]
  }
}
```

**mistake-learning Stop hook — macOS / Linux:**

```json
{
  "hooks": {
    "Stop": [
      {
        "command": "python3 \"$HOME/.claude/skills/mistake-learning/hooks/stop-hook.py\"",
        "description": "Increment mistake counters on session end"
      }
    ]
  }
}
```

**graphify intercept hook — Windows:**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "graphify",
        "command": "py \"%USERPROFILE%\\.claude\\skills\\graphify-link\\hooks\\intercept-graphify-skill.py\"",
        "description": "Fast-path graphify driver"
      }
    ]
  }
}
```

**graphify intercept hook — macOS / Linux:**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "graphify",
        "command": "python3 \"$HOME/.claude/skills/graphify-link/hooks/intercept-graphify-skill.py\"",
        "description": "Fast-path graphify driver"
      }
    ]
  }
}
```

## Testing manually

**mistake-learning:**

```powershell
# Windows
py "$env:USERPROFILE\.claude\skills\mistake-learning\hooks\stop-hook.py"
```

```bash
# macOS / Linux
python3 ~/.claude/skills/mistake-learning/hooks/stop-hook.py
```

**graphify intercept:**

```powershell
# Windows
py "$env:USERPROFILE\.claude\skills\graphify-link\hooks\intercept-graphify-skill.py" "$env:USERPROFILE\.claude\skills\graphify-link"
```

```bash
# macOS / Linux
python3 ~/.claude/skills/graphify-link/hooks/intercept-graphify-skill.py ~/.claude/skills/graphify-link
```

## Notes

- `graphify-build.py` and `graphify-update.py` carry a `# graphify-driver-version: N` stamp at line 1. Keep it at line 1 — tooling uses it to decide when to upgrade project-local copies.
- `graphify-link` stores graph registry at `~/.claude/graphify-roots.json` and session marker at `~/.claude/graphify.marker`.
- `mistake-learning` derives the home directory from `USERPROFILE` (Windows) or `HOME` (Unix) — no hardcoded paths.
- `hooks/intercept-graphify-skill.ps1` is a thin shim for existing configs that point to the `.ps1`; new installs should use `intercept-graphify-skill.py` directly.

## License

Local packaging of internal skill files for personal use. Follow existing repository licensing for redistribution.
