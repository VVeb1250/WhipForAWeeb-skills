---
name: codegraph-link
description: Wire a project to use CodeGraph MCP (@colbymchenry/codegraph) alongside graphify. Verifies CLI/index/MCP/permissions, writes or removes the managed CLAUDE.md role-split block, and leaves CodeGraph installation/indexing to codegraph itself. Handles unlink when args contain unlink/ยกเลิก/cancel/remove/ลบ/ถอด.
---

# codegraph-link

Coordination glue between **CodeGraph** (real-time code intelligence) and **graphify-link** (architecture/docs graph). This skill does not install CodeGraph, edit `.claude.json`, or build the index; it only verifies those pieces and writes the project guidance block.

## Intent

- Link/update: default intent, using cwd as root unless args provide a path.
- Unlink: args include `unlink`, `ยกเลิก`, `cancel`, `remove`, `ลบ`, or `ถอด`.

## Workflow

1. **Resolve root and intent**
   - Root defaults to cwd; a path-like arg overrides it.

2. **Unlink branch (early exit)** — only when intent is unlink:
   - Strip the managed block (markers inclusive) from `$root\CLAUDE.md`. If `CLAUDE.md` or the block is absent, say "nothing to unlink" and stop.
   - Do not remove `.codegraph/`, MCP config, or `mcp__codegraph__*` permissions; tell the user to use `codegraph uninstall` / `codegraph uninit` for those.
   - Confirm with one line: `codegraph-link: role-split removed from <root>\CLAUDE.md; codegraph MCP/index left intact (use codegraph uninstall to remove those).` Then **stop** — do not run the steps below.

3. **Verify prerequisites**
   - `where.exe codegraph` must find the CLI. If missing, stop and tell the user to install CodeGraph, then run `codegraph init -i`.
   - `$root\.codegraph\codegraph.db` must exist. If missing, stop and tell the user to run `codegraph init -i` or `codegraph index`.
   - Check for a `codegraph` MCP entry in `~/.claude.json`; if missing, report it and suggest `codegraph install --target=claude`. Do not hand-edit `.claude.json`.
   - Check `~/.claude/settings.json` for `mcp__codegraph__*` allow entries; report missing entries only.

4. **Choose and write the role split**
   - If `$root\graphify-out\graph.json` exists, write **Block A**.
   - Otherwise write **Block B** and tell the user they can rerun `/codegraph-link` after `/graphify` to upgrade.
   - Insert or replace idempotently in `$root\CLAUDE.md` using the managed markers. Create `CLAUDE.md` if missing. Write UTF-8 without BOM.
   - Idempotent replace: match `(?s)<!-- codegraph-link:start -->.*?<!-- codegraph-link:end -->`; if it matches, replace, else append. Use a literal replacement so `$` and regex metachars in the block survive.

5. **Confirm**
   - One line: `codegraph-link: <full split | code-only> block written to <root>\CLAUDE.md; index OK, graphify <present/absent>, MCP <present/missing>, auto-allow <present/missing>.`

## Managed Blocks

**Block A - graphify present**

```markdown
<!-- codegraph-link:start -->
## CodeGraph + graphify (code intelligence)

This project has a CodeGraph index (`.codegraph/`) and a graphify graph (`graphify-out/`). Use them by strength - do not double-explore the same thing two ways.

**Code questions** (how does X work · what calls Y · impact of changing Z · find a symbol · trace a path): answer with CodeGraph MCP directly - `codegraph_context` to map an area, `codegraph_trace` for a call path, `codegraph_explore` / `codegraph_node` for source, `codegraph_callers` / `codegraph_callees` / `codegraph_impact` for flow. A handful of calls, usually **zero file reads**; treat returned source as authoritative (already read). The index auto-syncs on save; a warning banner names any file pending sync - Read that one directly.

**Do NOT delegate code exploration to an Explore sub-agent or a grep/Read loop when CodeGraph can answer it** - that re-derives what the index already built and costs more for the same result. For code-navigation on this project, this **overrides** the general "always use Explore / parallel agents" guidance. (Sub-agents are still right for non-code research, writing, and multi-file edits.)

**Architecture / orientation / where-is-what:** read the lean `graphify-out/GRAPH_DIGEST.md` (~300-600 tokens) first; full detail in `GRAPH_REPORT.md`. Reach for these instead of fanning out across the tree to rebuild a mental map.

**Docs · papers · images:** only graphify indexes these - CodeGraph is code-only. If doc content changed, the SessionStart hook offers `/graphify --update` to refresh the graph + digest.
<!-- codegraph-link:end -->
```

**Block B - code-only**

```markdown
<!-- codegraph-link:start -->
## CodeGraph (code intelligence)

This project has a CodeGraph index (`.codegraph/`). Use it for code navigation instead of a grep/Read/Explore loop.

**Code questions** (how does X work · what calls Y · impact of changing Z · find a symbol · trace a path): answer with CodeGraph MCP directly - `codegraph_context` to map an area, `codegraph_trace` for a call path, `codegraph_explore` / `codegraph_node` for source, `codegraph_callers` / `codegraph_callees` / `codegraph_impact` for flow. A handful of calls, usually **zero file reads**; treat returned source as authoritative (already read). The index auto-syncs on save; a warning banner names any file pending sync - Read that one directly.

**Do NOT delegate code exploration to an Explore sub-agent or a grep/Read loop when CodeGraph can answer it** - that re-derives what the index already built and costs more for the same result. For code-navigation on this project, this **overrides** the general "always use Explore / parallel agents" guidance. (Sub-agents are still right for non-code research, writing, and multi-file edits.)

**Architecture / orientation & docs / papers / images:** CodeGraph is code-only and there's no graphify graph here. Build orientation from CodeGraph itself (`codegraph_files`, then `codegraph_context` on entry points) plus direct reads for docs. Run `/graphify` then re-run `/codegraph-link` to upgrade this block to the graphify-aware split (architecture digest + multimodal doc coverage).
<!-- codegraph-link:end -->
```

## Guardrails

- CodeGraph owns code navigation; graphify owns coarse architecture and docs/images/papers.
- This skill is hookless; CodeGraph uses its own watcher via `codegraph serve --mcp`.
- The managed block intentionally overrides broad Explore/parallel-agent guidance for code navigation.
- Works on any project with a `.codegraph/` index; not ROP-specific.
