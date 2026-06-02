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

1. **CLI** — `where.exe codegraph`. Missing → stop, tell user to install CodeGraph then `codegraph init -i`.
2. **Index** — `$root\.codegraph\codegraph.db` must exist. Missing → run `codegraph init -i` in `$root` (`-i` = init + index, NOT interactive); show output. Non-zero exit → stop, report error.
3. **MCP** — `codegraph` entry in `~/.claude.json`. Missing → report, suggest `codegraph install --target=claude`. Do not hand-edit `.claude.json`.
4. **Permissions** — report any missing `mcp__codegraph__*` allow entries in `~/.claude/settings.json`.
5. **Write block** — pick by `$root\graphify-out\graph.json`: exists → `blocks/graphify.md`, else → `blocks/code-only.md` (and note user can rerun after `/graphify` to upgrade). Read that block file (it already contains the markers) and write it verbatim into `$root\CLAUDE.md` (UTF-8 no BOM, create if missing). Idempotent: if the marker regex above matches, replace that span; else append. Use a literal replacement so `$`/regex metachars survive.
6. **Confirm** — one line: `codegraph-link: <full split | code-only> block written to <root>\CLAUDE.md; index OK, graphify <present/absent>, MCP <present/missing>, auto-allow <present/missing>.`

## Guardrails

- CodeGraph owns code navigation; graphify owns coarse architecture and docs/images/papers.
- Hookless skill; CodeGraph runs its own watcher via `codegraph serve --mcp`.
- The block intentionally overrides broad Explore/parallel-agent guidance for code navigation.
- Works on any project with a `.codegraph/` index.
