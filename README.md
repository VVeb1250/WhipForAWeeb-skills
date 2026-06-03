# WhipForAWeeb Skills Pack

Five Claude Code skills packaged as a plugin.

## Included Skills

| Skill | What it does |
|-------|-------------|
| `graphify-link` | Links a project to a graphify knowledge graph. Manages `graphify-roots.json`, installs fast-path drivers (`graphify-build.py`, `graphify-update.py`), starts `graphify watch`. |
| `codegraph-link` | Wires a project to the CodeGraph MCP (`@colbymchenry/codegraph`). Writes/removes the managed role-split block in `CLAUDE.md`. |
| `codegraph-affected` | Runs only the tests impacted by a change. Maps changed source files → impacted test files via `codegraph affected`, then runs just those (hands off to existing runner skills). Requires a CodeGraph index. |
| `mistake-learning` | Stop hook that reads the session transcript directly (no CLV2 dependency), detects known syntactic mistake patterns, and increments `(xN)` counters in `~/.claude/rules/mistakes-index.md`. Bundles a `mistakes-sweep.py` health/auto-archive script and seeds the `rules/mistakes-*.md` files on install. |
| `skill-router` | UserPromptSubmit hook that scores every installed skill/command against your prompt (local TF-IDF cosine, no AI) and injects only high-confidence matches, so the model picks the right skill without you naming it. Surfaces dormant nested skills (e.g. `skills/ecc/*`) the harness does not list. Silent below threshold → ~0 tokens on unrelated prompts. Index auto-rebuilds when skills are added/removed/edited. |

## Requirements

- Python 3 — `py` launcher (Windows) or `python3` (macOS/Linux)
- `graphify` CLI — `graphify-link` skill only
- `codegraph` CLI — `codegraph-link` skill only
- `~/.claude/rules/mistakes-*.md` — `mistake-learning` skill auto-seeds these on install if missing (existing files are never overwritten)

> PowerShell is **not** required. All hooks are pure Python.

## Installation

### Claude Code plugin marketplace (`/plugin`)

Installs **skills *and* hooks** natively — no copy step, no manual `settings.json` edit.

```
/plugin marketplace add VVeb1250/WhipForAWeeb-skills
/plugin install whipforaweeb-skills@whipforaweeb-skills
```

The five skills auto-discover, and the `skill-router` (UserPromptSubmit),
`mistake-learning` (Stop + SessionStart), and `graphify` (PreToolUse) hooks
register automatically.

> **Requires `node` on `PATH`.** The hooks are Python, but the `py` (Windows)
> vs `python3` (macOS/Linux) launcher cannot be expressed in a single plugin
> hook command — so every hook is routed through `plugins/hooks/run.js`, a tiny
> Node launcher that picks the right interpreter at runtime. Node ships with
> Claude Code, so this is normally already satisfied.
>
> Prefer the npm installer if you want hooks written into your own
> `~/.claude/settings.json` (it prints OS-correct `py`/`python3` snippets) rather
> than scoped to the plugin.

### npx (no install needed)

```bash
npx whipforaweeb-skills
```

### npm global

```bash
npm install -g whipforaweeb-skills
whipforaweeb-skills
```

### Script (from cloned repo)

```bash
# macOS / Linux
git clone https://github.com/VVeb1250/WhipForAWeeb-skills.git
cd WhipForAWeeb-skills
bash install.sh
```

```powershell
# Windows
git clone https://github.com/VVeb1250/WhipForAWeeb-skills.git
cd WhipForAWeeb-skills
pwsh install.ps1
```

### Manual

Copy the skill directories you want into `~/.claude/skills/`:

```powershell
# Windows
Copy-Item -Recurse "plugins\skills\graphify-link"      "$env:USERPROFILE\.claude\skills\"
Copy-Item -Recurse "plugins\skills\codegraph-link"     "$env:USERPROFILE\.claude\skills\"
Copy-Item -Recurse "plugins\skills\codegraph-affected" "$env:USERPROFILE\.claude\skills\"
Copy-Item -Recurse "plugins\skills\mistake-learning"   "$env:USERPROFILE\.claude\skills\"
Copy-Item -Recurse "plugins\skills\skill-router"       "$env:USERPROFILE\.claude\skills\"
```

```bash
# macOS / Linux
cp -r plugins/skills/graphify-link    ~/.claude/skills/
cp -r plugins/skills/codegraph-link   ~/.claude/skills/
cp -r plugins/skills/codegraph-affected ~/.claude/skills/
cp -r plugins/skills/mistake-learning ~/.claude/skills/
cp -r plugins/skills/skill-router     ~/.claude/skills/
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

**mistake-learning sweep (health + auto-archive) — SessionStart, Windows:**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "command": "py \"%USERPROFILE%\\.claude\\skills\\mistake-learning\\hooks\\mistakes-sweep.py\" --fix-safe --quiet; exit 0",
        "description": "Budget check + auto-archive FIXED entries"
      }
    ]
  }
}
```

**mistake-learning sweep — SessionStart, macOS / Linux:**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "command": "python3 \"$HOME/.claude/skills/mistake-learning/hooks/mistakes-sweep.py\" --fix-safe --quiet; exit 0",
        "description": "Budget check + auto-archive FIXED entries"
      }
    ]
  }
}
```

> **Make Claude log mistakes proactively.** The Stop hook only auto-counts the 3
> syntactic patterns. For Claude to record *new* mistakes, add this line to your
> `~/.claude/CLAUDE.md` so the trigger is always in context:
>
> ```
> ## Mistakes
> `rules/mistakes-index.md` auto-loaded. New mistake → write entry immediately. [HIGH] pattern → warn first.
> ```

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

**skill-router UserPromptSubmit hook — Windows:**

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "command": "py \"%USERPROFILE%\\.claude\\skills\\skill-router\\hooks\\skill-router.py\"",
        "description": "Suggest high-confidence skill matches for the prompt"
      }
    ]
  }
}
```

**skill-router UserPromptSubmit hook — macOS / Linux:**

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "command": "python3 \"$HOME/.claude/skills/skill-router/hooks/skill-router.py\"",
        "description": "Suggest high-confidence skill matches for the prompt"
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

**mistake-learning sweep (health report):**

```powershell
# Windows
py "$env:USERPROFILE\.claude\skills\mistake-learning\hooks\mistakes-sweep.py"
```

```bash
# macOS / Linux
python3 ~/.claude/skills/mistake-learning/hooks/mistakes-sweep.py
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

**skill-router** (pipe a fake prompt; prints injected context or nothing):

```powershell
# Windows
'{"prompt":"review my uncommitted changes for bugs"}' | py "$env:USERPROFILE\.claude\skills\skill-router\hooks\skill-router.py"
```

```bash
# macOS / Linux
echo '{"prompt":"review my uncommitted changes for bugs"}' | python3 ~/.claude/skills/skill-router/hooks/skill-router.py
```

## Notes

- `graphify-build.py` and `graphify-update.py` carry a `# graphify-driver-version: N` stamp at line 1. Keep it at line 1 — tooling uses it to decide when to upgrade project-local copies.
- `graphify-link` stores graph registry at `~/.claude/graphify-roots.json` and session marker at `~/.claude/graphify.marker`.
- `mistake-learning` derives the home directory from `USERPROFILE` (Windows) or `HOME` (Unix) — no hardcoded paths.
- `skill-router` writes its index cache (`.skill-index.json`) next to the script and derives all source paths from `~` — no hardcoded paths. The cache is generated at runtime and is git-ignored. Missing source dirs (e.g. `~/.agents/skills`) are skipped silently.
- `hooks/intercept-graphify-skill.ps1` is a thin shim for existing configs that point to the `.ps1`; new installs should use `intercept-graphify-skill.py` directly.

## License

Local packaging of internal skill files for personal use. Follow existing repository licensing for redistribution.
