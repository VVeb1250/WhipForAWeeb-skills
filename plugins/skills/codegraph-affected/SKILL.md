---
name: codegraph-affected
description: Run only the tests impacted by your changes, using CodeGraph's dependency graph (`codegraph affected`) to map changed source files to the test files that exercise them. Use when the user wants to test a diff/branch fast, run "affected tests only", or avoid a full-suite run after edits. Requires a CodeGraph index (`.codegraph/`).
---

# codegraph-affected

Map changed source files → impacted test files via the CodeGraph dependency graph, then run **only** those tests. Avoids full-suite runs on small diffs.

Root = cwd unless a path-like arg overrides it. Requires a CodeGraph index — if absent, tell user to run `/codegraph-link` first and **stop**.

## Steps

1. **Gate** — `codegraph status -j $root`. `initialized:true` → continue. Else → stop: "no CodeGraph index; run `/codegraph-link` first".

2. **Changed files** — pick the source list in this order:
   - Explicit file args → use them.
   - `base=<ref>` arg (e.g. `base=main`) → `git diff --name-only <base>...HEAD`.
   - Default → uncommitted + staged: `git diff --name-only HEAD` plus untracked (`git ls-files --others --exclude-standard`).
   - No git / no changes → stop, say so.

3. **Affected tests** — feed the file list on stdin (one per line):
   ```
   <files> | codegraph affected --stdin -q
   ```
   Flags: `-q` paths-only, `-j` JSON if you need to parse, `-f "<glob>"` to scope test files (e.g. `-f "**/*.spec.ts"`), `-d <n>` traversal depth (default 5). On PowerShell, join the paths with newlines before piping:
   ```powershell
   $files -join [Environment]::NewLine | codegraph affected --stdin -q
   ```
   Empty result → report "no tests affected by these changes" and stop (do **not** fall back to full suite unless user asks).

4. **Run** — run the project's test runner against **only** the returned files. Detect runner from the project (e.g. `vitest run <files>`, `jest <files>`, `pytest <files>`, `go test <pkgs>`, `cargo test`). If a runner skill exists (`/go-test`, `/flutter-test`, …) hand the file list to it. Do not invent a runner — if unclear, ask which command runs a single test file.

5. **Report** — `codegraph-affected: <N> changed files → <M> affected tests → <pass/fail summary>`. On failure show the runner output.

## Guardrails

- CodeGraph index must be fresh. The `serve` watcher auto-syncs on save; if the index is stale (watcher off / `--no-watch`), run `codegraph sync -q` before step 3.
- `affected` is a **filter**, not a coverage guarantee — for release gates run the full suite. Use this for the inner edit→test loop.
- Read-only on the graph; only writes are the test run's own artifacts.
