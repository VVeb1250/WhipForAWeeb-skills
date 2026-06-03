#!/usr/bin/env node
'use strict';
// Cross-platform hook launcher for the /plugin install path.
//
// A plugin hook command is a single fixed string, but the Python launcher
// differs per OS (`py` on Windows, `python3` elsewhere). Node is guaranteed
// available wherever this plugin runs, so we route every hook through here and
// pick the right interpreter at runtime.
//
// Usage:  node run.js [--soft] <script-rel-to-plugin-root> [args...]
//   --soft  always exit 0 (use for non-critical hooks like SessionStart so a
//           failing script never blocks the session)
//
// stdin/stdout/stderr are inherited so the hook payload (transcript path, etc.)
// flows to the child and its output flows back to Claude Code unchanged.

const { spawnSync } = require('child_process');
const path = require('path');

let args = process.argv.slice(2);
let soft = false;
if (args[0] === '--soft') {
  soft = true;
  args = args.slice(1);
}

const rel = args[0];
const extra = args.slice(1);
if (!rel) process.exit(0); // nothing to run — never block

const py = process.platform === 'win32' ? 'py' : 'python3';
const script = path.join(__dirname, '..', rel);

const r = spawnSync(py, [script, ...extra], { stdio: 'inherit' });

// Propagate the child's exit code, but never crash the hook on a spawn failure
// (e.g. interpreter missing) — exit 0 so Claude Code is never blocked.
process.exit(soft ? 0 : (r.status == null ? 0 : r.status));
