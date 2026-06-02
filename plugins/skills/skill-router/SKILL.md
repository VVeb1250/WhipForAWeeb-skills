---
name: skill-router
description: Local, no-AI skill suggester. A UserPromptSubmit hook scores every installed skill/command against your prompt (TF-IDF cosine) and injects only high-confidence matches, so the model picks the right skill without you remembering names. Surfaces dormant skills that the harness does not list.
---

# skill-router

A **UserPromptSubmit hook** that auto-suggests the most relevant skills for each
prompt. Pure local Python — no AI call, no network, no extra tokens unless a skill
is a strong match.

## Why

A large skill library has two problems:

1. You can't remember which skill fits which task → skills go unused.
2. Skills installed under nested dirs (e.g. `~/.claude/skills/ecc/*`) are **not
   surfaced** in the harness skill list at all → invisible capability.

skill-router fixes both by indexing every skill source and injecting the top
matches into context — but only when confident, so unrelated prompts cost ~0
tokens.

## How it works

On every prompt the hook:

1. **Loads/rebuilds an index** of all skills (cached as `.skill-index.json` next
   to the script). Rebuild is automatic: the cache signature is
   `(file count, Σ mtime)` of all sources, so any add / remove / edit triggers a
   lazy rebuild on the next prompt. No daemon.
2. **Scores** each skill by TF-IDF cosine similarity of the prompt against
   `name×3 + description`.
3. **Injects** the top matches via `additionalContext`, but only those with
   `cosine ≥ COSINE_MIN` and within `REL_MIN` of the top score (max `MAX_RESULTS`).
   Below threshold → silent (no output, no tokens).

Skills that the harness lists as invokable are emitted as `/name`; dormant skills
(e.g. `skills/ecc/*`) are emitted as `Read <path>/SKILL.md` so they can still be
applied.

### Indexed sources

| Glob | Tier | Emitted as |
|------|------|-----------|
| `~/.claude/commands/*.md` | `cmd` | `/name` |
| `~/.claude/skills/ecc/*/SKILL.md` | `ecc` | `Read <path>` (dormant) |
| `~/.claude/skills/*/SKILL.md` | `skill` | `/name` |
| `~/.agents/skills/*/SKILL.md` | `agent` | `/name` |

Missing source dirs are skipped silently, so the hook is safe on any setup.

## Tuning

Constants at the top of `hooks/skill-router.py`:

| Const | Default | Effect |
|-------|---------|--------|
| `COSINE_MIN` | `0.16` | Confidence floor. Raise → fewer, surer suggestions. |
| `REL_MIN` | `0.5` | Keep results within this fraction of the top score. |
| `MAX_RESULTS` | `3` | Max skills suggested per prompt. |
| `MIN_PROMPT_LEN` | `8` | Skip very short prompts. |

## Install

Copy `hooks/skill-router.py` to `~/.claude/skills/skill-router/hooks/`, then wire
the hook in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "shell": "powershell",
            "command": "py \"%USERPROFILE%\\.claude\\skills\\skill-router\\hooks\\skill-router.py\""
          }
        ]
      }
    ]
  }
}
```

On macOS/Linux use `python3` and the path
`"$HOME/.claude/skills/skill-router/hooks/skill-router.py"` (drop the `shell` key).

## Safety

Any error → `exit 0` with no output. The hook never blocks or alters your prompt;
worst case it simply suggests nothing.
