<!-- codegraph-link:start -->
## CodeGraph + graphify (code intelligence)

This project has a CodeGraph index (`.codegraph/`) and a graphify graph (`graphify-out/`). Use them by strength - do not double-explore the same thing two ways.

**Code questions** (how does X work · what calls Y · impact of changing Z · find a symbol · trace a path): answer with CodeGraph MCP directly - `codegraph_context` to map an area, `codegraph_trace` for a call path, `codegraph_explore` / `codegraph_node` for source, `codegraph_callers` / `codegraph_callees` / `codegraph_impact` for flow. A handful of calls, usually **zero file reads**; treat returned source as authoritative (already read). The index auto-syncs on save; a warning banner names any file pending sync - Read that one directly.

**Do NOT delegate code exploration to an Explore sub-agent or a grep/Read loop when CodeGraph can answer it** - that re-derives what the index already built and costs more for the same result. For code-navigation on this project, this **overrides** the general "always use Explore / parallel agents" guidance. (Sub-agents are still right for non-code research, writing, and multi-file edits.)

**Architecture / orientation / where-is-what:** read the lean `graphify-out/GRAPH_DIGEST.md` (~300-600 tokens) first; full detail in `GRAPH_REPORT.md`. Reach for these instead of fanning out across the tree to rebuild a mental map.

**Docs · papers · images:** only graphify indexes these - CodeGraph is code-only. If doc content changed, the SessionStart hook offers `/graphify --update` to refresh the graph + digest.
<!-- codegraph-link:end -->
