# graphify-driver-version: 3
"""
graphify-build.py — full-pipeline graph build driver (fast-path).

Consolidates Steps 4-9 of the upstream graphify skill into a single Python
session: build graph, cluster, analyze, render report, write HTML, save
manifest/cost. Skips the inter-step process spawns and repeated networkx
imports (saves ~5-10s on Windows per full build).

Usage:
  python graphify-build.py [path] [--phase=auto|prepare|finalize] [--obsidian]

Phases:
  auto       Decide between prepare and finalize based on disk state (default).
  prepare    Run detect + AST + cache check + merge any subagent chunks. If
             everything is code-only or doc-cache-hit, continue straight to
             finalize. Otherwise emit `.uncached.txt` and exit 2 (caller
             should dispatch semantic subagents, then re-run).
  finalize   Assume `.graphify_extract.json` exists. Build graph + cluster +
             analyze + report + HTML + obsidian (if --obsidian) + save.

Exit codes:
  0  Done. All outputs written.
  1  Fatal error (corpus too large / missing deps / extraction failed /
     graphify package API mismatch).
  2  Uncached non-code files present; semantic subagents required.
     `.uncached.txt` written with one path per line.

Labels:
  After finalize runs without explicit labels, default community labels are
  written. Callers may overwrite `graphify-out/.graphify_labels.json` with
  human-readable labels and re-run finalize cheaply.
"""
from __future__ import annotations

import json
import os
import sys
import glob
from datetime import datetime, timezone
from pathlib import Path

CODE_EXTS = {
    ".py", ".ts", ".js", ".go", ".rs", ".java", ".cpp", ".c", ".rb", ".swift",
    ".kt", ".cs", ".scala", ".php", ".cc", ".cxx", ".hpp", ".h", ".kts",
    ".lua", ".toc",
}


def _resolve_input(root: Path, value: str | Path) -> Path:
    """Resolve detector/cache paths against root when graphify returns relatives."""
    path = Path(value)
    return path if path.is_absolute() else root / path


def _load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[graphify-build] ignoring malformed {path.name}: {exc}",
              file=sys.stderr)
        return fallback


# --- EC-6: wrap graphify imports with version-mismatch fallback ------------
def _safe_import(spec: str):
    """Return imported attribute or None on ImportError/AttributeError."""
    try:
        module_path, _, attr = spec.partition(":")
        mod = __import__(module_path, fromlist=[attr] if attr else [])
        return getattr(mod, attr) if attr else mod
    except (ImportError, AttributeError) as exc:
        print(
            f"[graphify-build] graphify API mismatch on '{spec}': {exc}. "
            f"Upgrade may have changed the package; falling back to upstream "
            f"skill (rerun via Skill tool will work).",
            file=sys.stderr,
        )
        return None


def parse_args(argv: list[str]) -> tuple[Path, str, bool]:
    root = Path(".")
    phase = "auto"
    obsidian = False
    for arg in argv[1:]:
        if arg.startswith("--phase="):
            phase = arg.split("=", 1)[1]
        elif arg == "--obsidian":
            obsidian = True
        elif not arg.startswith("--"):
            root = Path(arg)
    return root.resolve(), phase, obsidian


# --- EC-3: merge subagent chunks into cache before checking ----------------
def _merge_chunks(out: Path) -> tuple[int, int, int]:
    """Read any .graphify_chunk_*.json, save to semantic cache, return totals."""
    save_cache = _safe_import("graphify.cache:save_semantic_cache")
    if save_cache is None:
        return 0, 0, 0

    chunk_files = sorted(glob.glob(str(out / ".graphify_chunk_*.json")))
    if not chunk_files:
        return 0, 0, 0

    all_nodes: list[dict] = []
    all_edges: list[dict] = []
    all_hyperedges: list[dict] = []
    for cf in chunk_files:
        try:
            d = json.loads(Path(cf).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[graphify-build] skipping malformed chunk {cf}: {exc}",
                  file=sys.stderr)
            continue
        all_nodes.extend(d.get("nodes", []))
        all_edges.extend(d.get("edges", []))
        all_hyperedges.extend(d.get("hyperedges", []))

    if all_nodes or all_edges:
        try:
            save_cache(all_nodes, all_edges, all_hyperedges)
        except Exception as exc:
            print(f"[graphify-build] save_semantic_cache failed: {exc}",
                  file=sys.stderr)
            return 0, 0, 0
        print(f"Chunk merge: {len(chunk_files)} chunk(s) → cache "
              f"({len(all_nodes)} nodes, {len(all_edges)} edges)")
    return len(all_nodes), len(all_edges), len(all_hyperedges)


def _cleanup_chunks(out: Path) -> None:
    """EC-5: remove session-specific chunk files after successful finalize."""
    for cf in glob.glob(str(out / ".graphify_chunk_*.json")):
        try:
            Path(cf).unlink()
        except OSError:
            pass


def write_digest(out, G, communities, labels, gods, *, max_hubs: int = 25, max_gods: int = 10) -> None:
    """Write a lean orientation map (GRAPH_DIGEST.md): just the community map
    and load-bearing nodes. codegraph (MCP) owns code detail / navigation, so
    the digest stays a cheap "where is what" pointer (~300-600 tokens) rather
    than the full GRAPH_REPORT.md. Soft-gate hint steers agents here first."""
    sized = sorted(
        ((cid, len(nodes)) for cid, nodes in communities.items() if len(nodes) >= 3),
        key=lambda kv: kv[1], reverse=True,
    )[:max_hubs]
    lines = [
        "# GRAPH_DIGEST",
        f"{G.number_of_nodes()} nodes · {G.number_of_edges()} edges · {len(communities)} communities",
        "",
        "## Map (largest communities)",
    ]
    lines += [f"- {labels.get(cid, f'Community {cid}')} ({size})" for cid, size in sized]
    lines += ["", "## Load-bearing (god nodes)"]
    lines += [f"- {g.get('label', g.get('id', '?'))} ({g.get('degree', '?')})" for g in gods[:max_gods]]
    has_cg = (out.parent / ".codegraph" / "codegraph.db").exists()
    lines += ["", "## How to use"]
    if has_cg:
        lines += [
            "- Code find / trace / callers / impact → codegraph MCP (`codegraph_context`, `codegraph_trace`, …)",
            "- Docs & full detail → graphify-out/GRAPH_REPORT.md",
        ]
    else:
        lines += [
            "- Code / docs / orientation → this graph: graphify-out/GRAPH_REPORT.md + the BFS/DFS query tools (god nodes & communities above are the entry points)",
        ]
    (out / "GRAPH_DIGEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare(root: Path) -> int:
    """Detect files, run AST, merge chunks, check cache. Emit extract or stop."""
    detect = _safe_import("graphify.detect:detect")
    collect_files = _safe_import("graphify.extract:collect_files")
    extract = _safe_import("graphify.extract:extract")
    check_cache = _safe_import("graphify.cache:check_semantic_cache")
    if None in (detect, collect_files, extract, check_cache):
        return 1

    out = root / "graphify-out"
    out.mkdir(parents=True, exist_ok=True)

    det = detect(root)
    if det["total_files"] == 0:
        print(f"No supported files found in {root}.", file=sys.stderr)
        return 1
    if det["total_words"] > 2_000_000 or det["total_files"] > 200:
        print(
            f"WARN: large corpus ({det['total_files']} files, "
            f"{det['total_words']:,} words). Consider scoping to a subfolder.",
            file=sys.stderr,
        )

    (out / ".graphify_detect.json").write_text(
        json.dumps(det, ensure_ascii=False), encoding="utf-8"
    )
    video_count = len(det['files'].get('video', []))
    print(
        f"Detect: {det['total_files']} files, {det['total_words']:,} words "
        f"(code: {len(det['files'].get('code', []))}, "
        f"document: {len(det['files'].get('document', []))}, "
        f"paper: {len(det['files'].get('paper', []))}, "
        f"image: {len(det['files'].get('image', []))}, "
        f"video: {video_count})"
    )

    # Video files require Whisper transcription (Step 2.5 in upstream skill).
    # Fast-path driver does not call Whisper; fall through cleanly.
    if video_count > 0:
        print(
            f"\nSTOP: {video_count} video/audio file(s) require Whisper "
            f"transcription — upstream skill will handle Step 2.5.",
            file=sys.stderr,
        )
        return 2

    # EC-3: merge any subagent chunks that arrived between runs
    _merge_chunks(out)

    # AST on code files
    code_files: list[Path] = []
    for f in det["files"].get("code", []):
        p = _resolve_input(root, f)
        code_files.extend(collect_files(p) if p.is_dir() else [p])
    code_files = [p for p in code_files if p.suffix.lower() in CODE_EXTS]

    if code_files:
        ast = extract(code_files)
        print(f"AST: {len(ast['nodes'])} nodes, {len(ast['edges'])} edges "
              f"from {len(code_files)} code files")
    else:
        ast = {"nodes": [], "edges": [], "input_tokens": 0, "output_tokens": 0}

    # Cache check for non-code files
    non_code = [
        str(_resolve_input(root, f))
        for f in (det["files"].get("document", [])
                  + det["files"].get("paper", [])
                  + det["files"].get("image", []))
    ]
    if non_code:
        cached_nodes, cached_edges, cached_hyperedges, uncached = check_cache(non_code)
        print(f"Semantic cache: {len(non_code) - len(uncached)}/{len(non_code)} hits")
    else:
        cached_nodes, cached_edges, cached_hyperedges, uncached = [], [], [], []

    # Merge AST + cached semantic into extract.json
    seen = {n["id"] for n in ast["nodes"]}
    merged_nodes = list(ast["nodes"])
    for n in cached_nodes:
        if n["id"] not in seen:
            merged_nodes.append(n)
            seen.add(n["id"]) 

    extract_doc = {
        "nodes": merged_nodes,
        "edges": ast["edges"] + cached_edges,
        "hyperedges": cached_hyperedges,
        "input_tokens": ast.get("input_tokens", 0),
        "output_tokens": ast.get("output_tokens", 0),
    }
    (out / ".graphify_extract.json").write_text(
        json.dumps(extract_doc, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Extract: {len(merged_nodes)} nodes, {len(extract_doc['edges'])} edges")

    if uncached:
        (out / ".uncached.txt").write_text(
            "\n".join(uncached), encoding="utf-8"
        )
        print(
            f"\nSTOP: {len(uncached)} uncached non-code file(s) need semantic "
            f"extraction. Wrote graphify-out/.uncached.txt. Dispatch subagents "
            f"and re-run."
        )
        return 2

    return 0


def finalize(root: Path, *, obsidian: bool) -> int:
    """Build + cluster + report + HTML + save. Single networkx import."""
    build_from_json = _safe_import("graphify.build:build_from_json")
    cluster_fn = _safe_import("graphify.cluster:cluster")
    score_all = _safe_import("graphify.cluster:score_all")
    god_nodes = _safe_import("graphify.analyze:god_nodes")
    surprising = _safe_import("graphify.analyze:surprising_connections")
    suggest_questions = _safe_import("graphify.analyze:suggest_questions")
    generate = _safe_import("graphify.report:generate")
    to_json = _safe_import("graphify.export:to_json")
    to_html = _safe_import("graphify.export:to_html")
    save_manifest = _safe_import("graphify.detect:save_manifest")
    if None in (build_from_json, cluster_fn, score_all, god_nodes, surprising,
                suggest_questions, generate, to_json, to_html, save_manifest):
        return 1

    out = root / "graphify-out"
    extract_path = out / ".graphify_extract.json"
    detect_path = out / ".graphify_detect.json"
    if not extract_path.exists() or not detect_path.exists():
        print(
            "Missing .graphify_extract.json or .graphify_detect.json — "
            "run with --phase=prepare first.",
            file=sys.stderr,
        )
        return 1

    extraction = json.loads(extract_path.read_text(encoding="utf-8"))
    detection = json.loads(detect_path.read_text(encoding="utf-8"))

    G = build_from_json(extraction)
    if G.number_of_nodes() == 0:
        print("ERROR: Graph is empty — extraction produced no nodes.", file=sys.stderr)
        return 1

    communities = cluster_fn(G)
    cohesion = score_all(G, communities)
    gods = god_nodes(G)
    surprises = surprising(G, communities)

    # Reuse user-curated labels if present
    labels_path = out / ".graphify_labels.json"
    if labels_path.exists():
        labels_raw = _load_json(labels_path, {})
        labels = {int(k): v for k, v in labels_raw.items()}
        for cid in communities:
            labels.setdefault(cid, f"Community {cid}")
    else:
        labels = {cid: f"Community {cid}" for cid in communities}
        labels_path.write_text(
            json.dumps({str(k): v for k, v in labels.items()}, ensure_ascii=False),
            encoding="utf-8",
        )

    questions = suggest_questions(G, communities, labels)
    tokens = {
        "input": extraction.get("input_tokens", 0),
        "output": extraction.get("output_tokens", 0),
    }

    report = generate(
        G, communities, cohesion, labels, gods, surprises,
        detection, tokens, str(root),
        suggested_questions=questions,
    )
    (out / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
    try:
        write_digest(out, G, communities, labels, gods)
    except Exception as exc:
        print(f"[graphify-build] digest skipped: {exc}", file=sys.stderr)

    # EC-4: to_json may refuse to shrink the graph. Try once; on refusal,
    # accept the existing graph.json as authoritative (a prior, more complete
    # run is preserved).
    graph_out_path = str(out / "graph.json")
    try:
        to_json(G, communities, graph_out_path)
    except Exception as exc:
        # If graphify's to_json raises on shrink-refusal we let the existing
        # graph.json stand; print a clear message so the user sees why.
        print(
            f"[graphify-build] graph.json not overwritten: {exc}. "
            f"This usually means the existing graph has more nodes (probably "
            f"from a previous run with subagents). The new graph is in memory "
            f"but not persisted; rerun via Skill tool if you want subagents.",
            file=sys.stderr,
        )

    analysis = {
        "communities": {str(k): v for k, v in communities.items()},
        "cohesion": {str(k): v for k, v in cohesion.items()},
        "gods": gods,
        "surprises": surprises,
        "questions": questions,
    }
    (out / ".graphify_analysis.json").write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if G.number_of_nodes() > 5000:
        print(f"Graph has {G.number_of_nodes()} nodes — skipping HTML viz.")
    else:
        to_html(G, communities, str(out / "graph.html"),
                community_labels=labels or None)
        print("graph.html written")

    if obsidian:
        to_obsidian = _safe_import("graphify.export:to_obsidian")
        to_canvas = _safe_import("graphify.export:to_canvas")
        if to_obsidian and to_canvas:
            obs_dir = str(out / "obsidian")
            n_notes = to_obsidian(G, communities, obs_dir,
                                  community_labels=labels or None, cohesion=cohesion)
            to_canvas(G, communities, f"{obs_dir}/graph.canvas",
                      community_labels=labels or None)
            print(f"Obsidian vault: {n_notes} notes in {obs_dir}/")
