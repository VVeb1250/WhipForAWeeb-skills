# Changelog

All notable changes to **WhipForAWeeb Skills Pack** are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [v0.5.0] — 2026-06-04

### Added — `codegraph-affected`

> Run only the tests impacted by a change, using CodeGraph's dependency graph instead of a full-suite run.

- Maps changed source files → impacted test files via `codegraph affected --stdin`, then runs only those tests.
- Health-gates on `codegraph status -j` (`initialized:true`); tells the user to run `/codegraph-link` first if no index.
- Picks the changed-file set from explicit args, `base=<ref>` diff, or uncommitted + staged + untracked.
- Hands off to existing runner skills (`/go-test`, `/flutter-test`, …); never silently falls back to the full suite.

### Changed — `codegraph-link` (CodeGraph 0.9.9 reconcile)

- Fixed stale MCP tool names in the managed `CLAUDE.md` block: dropped non-existent `codegraph_context` / `codegraph_trace`, added real `codegraph_search` / `codegraph_status`. Canonical 8-tool set now listed.
- **Index check** now gates on `codegraph status -j` health (`initialized`), not bare `.codegraph/codegraph.db` file presence.
- **MCP drift check**: compares the live `~/.claude.json` entry against `codegraph install --print-config claude` and flags stale config after a CLI upgrade.
- `init -i` → `init` (indexing runs by default as of 0.9.7+; `-i` deprecated). Install hint uses `-l global -y`.
- Added optional `CODEGRAPH_MCP_TOOLS` token-trim note and multi-agent install targets (`gemini`, `antigravity`, `kiro`, …).

> ⚠️ Already-linked projects keep stale tool names baked into their `CLAUDE.md` block — re-run `/codegraph-link` per project to refresh.

---

## [v0.4.0] — 2026-06-03

### Added — `skill-router`

> Local, no-AI skill suggester. Fires on every prompt. Costs ~0 tokens when nothing matches.

- `UserPromptSubmit` hook scores all installed skills/commands via **TF-IDF cosine** and injects top matches into Claude's context before the turn begins.
- Surfaces **dormant skills** the harness never lists (e.g. `~/.claude/skills/ecc/*`) by emitting a `Read <path>/SKILL.md` pointer instead of a slash command.
- **Silent below threshold** — no output, no tokens, no noise on unrelated prompts.
- Index (`count + Σmtime` signature) **auto-rebuilds** whenever skills are added, removed, or edited. No daemon, no cron.
- Tunable: `COSINE_MIN`, `REL_MIN`, `MAX_RESULTS` at top of script.
- Portable: cache stored next to script, paths derived from `~`, missing source dirs skipped silently. Any error → `exit 0`.
- `.skill-index.json` runtime cache added to `.gitignore`.

---

## [v0.3.0] — 2026-06-03

### Changed — `mistake-learning` overhaul

- **Self-contained install**: `stop-hook.py` reads transcript via `transcript_path` from stdin directly — no CLV2 dependency, no background daemon.
- `mistakes-sweep.py` bundled inside the skill (`hooks/`) and wired as a `SessionStart` hook. Flags over-budget index, stuck FIXED entries, missing date stamps, and aged LOW entries.
- `--fix-safe` flag: deterministic auto-move of FIXED entries from index → archive (append-first, then atomic rewrite; moves, never deletes).
- `--quiet` flag: silent when healthy — safe to wire as a warn-only hook.
- Seed files (`mistakes-index.md`, `mistakes-detail.md`, `mistakes-archive.md`) never overwrite existing records on install.
- Removed `slash_path` auto-detect pattern (matched legit git-bash `/` paths → false positives; see `[hook-false-positive]`).

### Added

- npm publish workflow (CI): triggers on `v*` tag push or manual dispatch, with npm provenance.
- `.npmignore` to exclude `__pycache__` from the npm tarball.
- `repository`, `homepage`, `bugs` fields in `package.json` (required for npm provenance).

---

## [v0.2.0] — 2026-06-03

### Added — `codegraph-link`

- Wires a project to the [CodeGraph MCP](https://github.com/colbymchenry/codegraph) (`@colbymchenry/codegraph`).
- Writes and removes a managed role-split block in `CLAUDE.md` (`codegraph` query → model read, `graphify` semantic context → graphify graph).
- Verifies CLI, index, MCP permissions, and auto-runs `codegraph index` when the index is missing.

### Improved — installer

- Interactive checkbox selector (`↑↓ Space a Enter q`) with prereq status per skill.
- Auto-checks prerequisites (Python, `graphify`, `codegraph`) and warns on missing deps.
- Prints ready-to-paste `settings.json` hook snippets for selected skills.

---

## [v0.1.3] — 2026-05-31

### Fixed

- Install script path handling on Windows (CRLF / path separator edge cases).

---

## [v0.1.1] — 2026-05-31 · Initial public release

### Added — `graphify-link`, `mistake-learning`

**`graphify-link`**
- Links any project to a [graphify](https://github.com/graphify-ai/graphify) knowledge graph.
- Manages `~/.claude/graphify-roots.json` registry and `~/.claude/graphify.marker` session flag.
- Installs project-local fast-path drivers (`graphify-build.py`, `graphify-update.py`) with a `# graphify-driver-version: N` stamp at line 1 for auto-upgrade detection.
- Starts `graphify watch` after linking.
- `PreToolUse` + `PostToolUse` hooks (`check-graphify.ps1`, `mark-graphify.ps1`) track file reads and flag incremental update opportunities.
- `.ps1` shim (`intercept-graphify-skill.ps1`) preserved for backward compat; new installs use `intercept-graphify-skill.py`.

**`mistake-learning`**
- Three-tier mistake storage: `mistakes-index.md` (hot, auto-loaded), `mistakes-detail.md` (on-demand), `mistakes-archive.md` (never auto-loaded).
- `Stop` hook auto-increments `(xN, date)` counters for syntactic patterns (`py-command`, `bash-wsl`, `ps-null-coalesce`). Semantic mistakes stay manual.
- Seeds `rules/mistakes-*.md` on install if absent.

---

[v0.4.0]: https://github.com/VVeb1250/WhipForAWeeb-skills/releases/tag/v0.4.0
[v0.3.0]: https://github.com/VVeb1250/WhipForAWeeb-skills/releases/tag/v0.3.0
[v0.2.0]: https://github.com/VVeb1250/WhipForAWeeb-skills/releases/tag/v0.2.0
[v0.1.3]: https://github.com/VVeb1250/WhipForAWeeb-skills/releases/tag/v0.1.3
[v0.1.1]: https://github.com/VVeb1250/WhipForAWeeb-skills/releases/tag/v0.1.1
