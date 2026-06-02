<!-- codegraph-link:start -->
## CodeGraph (code intelligence)

This project has a CodeGraph index (`.codegraph/`). Use it for code navigation instead of a grep/Read/Explore loop.

**Code questions** (how does X work · what calls Y · impact of changing Z · find a symbol · trace a path): answer with CodeGraph MCP directly - `codegraph_context` to map an area, `codegraph_trace` for a call path, `codegraph_explore` / `codegraph_node` for source, `codegraph_callers` / `codegraph_callees` / `codegraph_impact` for flow. A handful of calls, usually **zero file reads**; treat returned source as authoritative (already read). The index auto-syncs on save; a warning banner names any file pending sync - Read that one directly.

**Do NOT delegate code exploration to an Explore sub-agent or a grep/Read loop when CodeGraph can answer it** - that re-derives what the index already built and costs more for the same result. For code-navigation on this project, this **overrides** the general "always use Explore / parallel agents" guidance. (Sub-agents are still right for non-code research, writing, and multi-file edits.)

**Architecture / orientation & docs / papers / images:** CodeGraph is code-only and there's no graphify graph here. Build orientation from CodeGraph itself (`codegraph_files`, then `codegraph_context` on entry points) plus direct reads for docs. Run `/graphify` then re-run `/codegraph-link` to upgrade this block to the graphify-aware split (architecture digest + multimodal doc coverage).
<!-- codegraph-link:end -->
