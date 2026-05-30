---
name: graphify-link
description: Initialize or connect a project graphify knowledge graph. Use for first-time graph setup, adding a submodule to an existing graph, starting graphify watch, or unlinking a registered root. Not needed every session because reset-graphify.ps1 starts watch automatically when a registered graph exists.
---

# graphify-link

## Intent

Use this skill only when the user asks to link/init graphify, add coverage, start watch for an existing graph, or unlink/remove graphify.

- Unlink words: `unlink`, `ยกเลิก`, `cancel`, `remove`, `ลบ`, `ถอด`
- Add words: `add`, `เพิ่ม`, `append`, `include`, `ใส่`
- A bare path means "use this as the root" unless it follows an add word, then it means "add this submodule"

## Workflow

1. **Resolve intent and root**
   - Root defaults to cwd unless args provide a root path.
   - If unlink intent, remove the selected root from `~/.claude/graphify-roots.json`, stop graphify watch, delete `~/.claude/graphify.marker`, then report one line.
   - If `graphify.marker` already exists for this root, report that it is already linked and stop.

2. **Decide what work is needed**
   - If `**/graphify-out/GRAPH_REPORT.md` exists, prefer using the existing graph.
   - For add intent, run `/graphify` on the provided submodule path, then `graphify merge-graphs <root>/graphify-out/graph.json <path>/graphify-out/graph.json --out <root>/graphify-out/graph.json`, then `graphify cluster-only <root>`.
   - For re-init intent, ask which paths to extract; default to `.`.
   - For an existing graph with no add/re-init request, skip extraction and just start watch.
   - For no existing graph, ask once for confirmation and run `/graphify` on `.` unless the user provided specific paths.

3. **Register and install fast path**
   - Add root to `graphify-roots.json` if missing, using a case-insensitive duplicate check.
   - Copy `graphify-build.py` and `graphify-update.py` from this skill directory into the project root only when missing.
   - Do not overwrite project copies during initial link. Version upgrades are handled by `reset-graphify.ps1` using the `# graphify-driver-version: N` stamp, which must stay near the top of each driver.

4. **Start watch and finish**
   - Read the highest-level `GRAPH_REPORT.md` so the session has graph context.
   - Stop any existing graphify watch, then start `graphify watch <root>` in the background.
   - Write `~/.claude/graphify.marker` as:
     ```json
     {"root":"<root>","timestamp":"<ISO timestamp>"}
     ```
   - Confirm with one line: report loaded, root registered, watch started.

## Guardrails

- `/graphify` is the slow semantic extraction; `graphify watch` is the fast AST daemon.
- If extraction fails for one selected path, continue with the rest and summarize failures at the end.
- If merge fails, stop before clustering.
- If clustering fails after a successful merge, warn that `graph.json` was updated but clustering needs a retry.
- Runtime hook: point `settings.json` at `hooks/intercept-graphify-skill.py` (cross-platform, no PowerShell needed). The `.ps1` shim in the same directory still works for existing configs.
