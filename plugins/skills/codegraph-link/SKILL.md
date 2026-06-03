---
name: codegraph-link
description: Wire a project to use CodeGraph MCP (@colbymchenry/codegraph) alongside graphify. Verifies CLI/index/MCP/permissions, auto-runs `codegraph index` if index is missing, writes or removes the managed CLAUDE.md role-split block. Handles unlink when args contain unlink/ยกเลิก/cancel/remove/ลบ/ถอด.
---

# codegraph-link

Verifies CodeGraph prerequisites, auto-builds the index if missing, and writes a guidance block to the project's `CLAUDE.md` so the agent prefers CodeGraph MCP over grep/Explore for code navigation. Does not install CodeGraph or edit `.claude.json`.

Root = cwd unless a path-like arg overrides it.

## Unlink (args contain unlink/ยกเลิก/cancel/remove/ลบ/ถอด)

Strip the managed block (markers inclusive, regex `(?s)<!-- codegraph-link:start -->.*?<!-- codegraph-link:end -->`) from `$root\CLAUDE.md`. If the file or block is absent, say "nothing to unlink". Leave `.codegraph/`, MCP config, and permissions intact (point user to `codegraph uninstall`). Confirm in one line, then **stop**.

## Link (default)

1. **CLI** — `where.exe codegraph`. Missing → stop, tell user to install CodeGraph (`npm i -g @colbymchenry/codegraph`) then `codegraph init`.
2. **Index** — gate on real health, not file presence: `codegraph status -j $root` → parse JSON. `initialized:true` → OK. `initialized:false` (or non-zero exit, or no `.codegraph\`) → run `codegraph init` in `$root` (init + initial index runs by default as of 0.9.7+; the old `-i` flag is deprecated but still accepted); show output; non-zero exit → stop, report error. If `.codegraph\` exists but `status` reports not-initialized/empty (corrupt or interrupted index), run `codegraph index` to rebuild.
3. **MCP** — `codegraph` entry in `~/.claude.json`.
   - Missing → suggest `codegraph install --target=claude -l global -y` (non-interactive; also writes the auto-allow list). Do not hand-edit `.claude.json`.
   - Present → **drift check**: run `codegraph install --print-config claude` and compare its `command`/`args` to the live entry. Differ (stale config after a CLI upgrade) → report the drift and suggest re-running the install line above to refresh.
   - Optional token trim: add `"env": { "CODEGRAPH_MCP_TOOLS": "explore,search,node,callers,callees,impact,files,status" }` to the entry to expose only the tools you use (comma short-names; drop ones you never call to shrink the per-session tool schema).
   - Multi-agent: 0.9.9 also targets `cursor, codex, opencode, hermes, gemini, antigravity, kiro` — one index, many agents via `codegraph install -t <ids> -y`.
4. **Permissions** — report any missing `mcp__codegraph__*` allow entries in `~/.claude/settings.json`. Canonical set (8 tools): `codegraph_explore`, `codegraph_search`, `codegraph_callers`, `codegraph_callees`, `codegraph_impact`, `codegraph_node`, `codegraph_files`, `codegraph_status`.
5. **Write block** — pick by `$root\graphify-out\graph.json`: exists → `blocks/graphify.md`, else → `blocks/code-only.md` (and note user can rerun after `/graphify` to upgrade). Read that block file (it already contains the markers) and write it verbatim into `$root\CLAUDE.md` (UTF-8 no BOM, create if missing). Idempotent: if the marker regex above matches, replace that span; else append. Use a literal replacement so `$`/regex metachars survive.
6. **Confirm** — one line: `codegraph-link: <full split | code-only> block written to <root>\CLAUDE.md; index OK, graphify <present/absent>, MCP <present/missing/drift>, auto-allow <present/missing>.`

## Guardrails

- CodeGraph owns code navigation; graphify owns coarse architecture and docs/images/papers.
- Hookless skill; CodeGraph runs its own watcher via `codegraph serve --mcp`.
- The block intentionally overrides broad Explore/parallel-agent guidance for code navigation.
- Works on any project with a `.codegraph/` index.
