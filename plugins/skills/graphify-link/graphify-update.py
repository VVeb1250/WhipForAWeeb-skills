# graphify-driver-version: 2
"""
Incremental graphify update driver used by reset-graphify.ps1.

Behavior:
 - Scans repo root for changed files since last snapshot (or uses provided list).
 - Runs semantic extraction only for changed files (calls graphify.extract.extract_files).
 - Merges semantic results into the project's semantic cache and appends to graph.json.
 - Writes a short summary to stdout and exits 0.

Exit codes: 0 success, 1 fatal error, 2 no-op (nothing changed).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from datetime import datetime


def main(argv: list[str]):
    root = Path(argv[1]) if len(argv) > 1 else Path('.')
    out = root / 'graphify-out'
    if not out.exists():
        print('No graphify-out found; run full build first.', file=sys.stderr)
        return 1

    changed = []
    if len(argv) > 2:
        changed = argv[2:]
    else:
        # naive: check git status or mtime tree (keeps this driver dependency-free)
        changed = []

    if not changed:
        print('No changed files provided; nothing to do.')
        return 2

    extract = None
    try:
        from graphify.extract import extract_files
        extract = extract_files
    except Exception as exc:
        print(f'graphify.extract not available: {exc}', file=sys.stderr)
        return 1

    # Run extraction
    try:
        nodes, edges, hyperedges = extract(changed)
    except Exception as exc:
        print(f'Extraction failed: {exc}', file=sys.stderr)
        return 1

    # Merge into cache
    try:
        from graphify.cache import save_semantic_cache
        save_semantic_cache(nodes, edges, hyperedges)
    except Exception as exc:
        print(f'Failed to save semantic cache: {exc}', file=sys.stderr)
        return 1

    # Append chunk file for safe merge by full builder
    chunk_path = out / f'.graphify_chunk_{int(datetime.now().timestamp())}.json'
    chunk_path.write_text(json.dumps({
        'nodes': nodes,
        'edges': edges,
        'hyperedges': hyperedges
    }, ensure_ascii=False), encoding='utf-8')

    print(f'Wrote incremental chunk: {chunk_path.name} (nodes={len(nodes)})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
