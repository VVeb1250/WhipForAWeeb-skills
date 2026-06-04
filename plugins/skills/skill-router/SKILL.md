---
name: skill-router
description: Local, no-AI skill suggester. A UserPromptSubmit hook scores every installed skill/command against your prompt (hybrid: TF-IDF cosine + an optional curated intent-phrase boost, conflict pruning and prerequisite fan-out via skill-graph.json) and injects only high-confidence matches, so the model picks the right skill without you remembering names. Multilingual via an optional semantic tier (any language → English skills). Surfaces dormant skills that the harness does not list.
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

### Tier-2: multilingual semantic fallback

TF-IDF is **lexical** — it only matches when prompt and skill docs share the same
words, so a non-English prompt against an English corpus scores ~0. Tier-2 fixes
this:

- Tier-1 (TF-IDF, instant) runs first on every prompt.
- **Only** if tier-1 returns nothing **and** the prompt contains non-ASCII
  letters (Thai, CJK, Cyrillic, …), tier-2 (`embed.py`) loads a multilingual
  MiniLM model (ONNX) and matches by sentence-embedding cosine in a shared
  cross-lingual space. A prompt in any language then matches the English skills.

Plain-English prompts never load the model, so the common path stays free. When
tier-2 fires it costs ~1–1.5 s (model + tokenizer load + one embed; the 303 corpus
vectors are embedded once and cached in `.skill-vecs.npz`, keyed by index sig).
The header reads `local, semantic` instead of `local, cosine≥…` so you can tell
which tier answered.

Tier-2 is **optional**. If `onnxruntime` / `tokenizers` / the model files are
absent, `embed.py` raises and the hook falls back to silence — exactly as before.
Enable it once with `setup_embeddings.ps1` (installs deps, downloads the ~113 MB
quantized model + tokenizer into `hooks/models/`).

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

Tier-2 constants (top of `hooks/embed.py`):

| Const | Default | Effect |
|-------|---------|--------|
| `SEM_MIN` | `0.30` | Semantic-cosine floor (MiniLM scale, not TF-IDF). |
| `REL_MIN` | `0.85` | Keep semantic results within this fraction of the top. |
| `MAX_TOKENS` | `128` | Truncate prompt/doc length before embedding. |

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

Copy `embed.py` and `setup_embeddings.ps1` alongside `skill-router.py`. The model
files and vector cache must live in the **same directory as the running script**
(`embed.py` resolves `models/` and `.skill-*` relative to its own location), so
deploy all code to one dir and run setup there.

To enable the multilingual tier:

```powershell
# from the hooks dir that the settings.json command points at
powershell -File setup_embeddings.ps1
```

This installs `onnxruntime` + `tokenizers` and downloads the model into
`models/`. Skip it to keep the router English-only (lexical tier still works).

## Safety

Any error → `exit 0` with no output. The hook never blocks or alters your prompt;
worst case it simply suggests nothing.
