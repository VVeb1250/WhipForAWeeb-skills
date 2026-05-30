#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');
const readline = require('readline');
const { spawnSync } = require('child_process');

const isWin = process.platform === 'win32';
const py = isWin ? 'py' : 'python3';
const sep = isWin ? '\\' : '/';
const home = os.homedir();
const dest = path.join(home, '.claude', 'skills');
const src = path.join(__dirname, '..', 'plugins', 'skills');

const E = ''; // ESC for ANSI codes
const clrLine = `${E}[2K`;
const reset   = `${E}[0m`;
const bold    = `${E}[1m`;
const dim     = `${E}[2m`;
const cyan    = `${E}[36m`;
const green   = `${E}[32m`;
const red     = `${E}[31m`;
const yellow  = `${E}[33m`;

function has(cmd) {
  return spawnSync(cmd, ['--version'], { stdio: 'ignore' }).status === 0;
}

function skillPath(...parts) {
  return [home, '.claude', 'skills', ...parts].join(sep);
}

const SKILLS = [
  {
    id: 'graphify-link',
    desc: 'Knowledge graph for your codebase',
    prereqs: [
      { label: `Python (${py})`, ok: () => has(py) },
      { label: `graphify CLI  (pip install graphify)`, ok: () => has('graphify') },
    ],
    hook: () => ({
      event: 'PreToolUse',
      entry: {
        matcher: 'graphify',
        command: `${py} "${skillPath('graphify-link', 'hooks', 'intercept-graphify-skill.py')}"`,
        description: 'Fast-path graphify driver'
      }
    })
  },
  {
    id: 'codegraph-link',
    desc: 'CodeGraph MCP integration (CLAUDE.md role-split)',
    prereqs: [
      { label: 'codegraph CLI  (npm i -g @colbymchenry/codegraph)', ok: () => has('codegraph') },
    ],
    hook: null
  },
  {
    id: 'mistake-learning',
    desc: 'Auto-increment mistake counters on session end',
    prereqs: [
      { label: `Python (${py})`, ok: () => has(py) },
    ],
    hook: () => ({
      event: 'Stop',
      entry: {
        command: `${py} "${skillPath('mistake-learning', 'hooks', 'stop-hook.py')}"`,
        description: 'Increment mistake counters on session end'
      }
    })
  }
];

function checkSkill(skill) {
  return skill.prereqs.map(p => ({ ...p, passed: p.ok() }));
}

function copyDir(from, to) {
  fs.mkdirSync(to, { recursive: true });
  for (const entry of fs.readdirSync(from, { withFileTypes: true })) {
    const s = path.join(from, entry.name);
    const d = path.join(to, entry.name);
    entry.isDirectory() ? copyDir(s, d) : fs.copyFileSync(s, d);
  }
}

function installSkill(skill) {
  const from = path.join(src, skill.id);
  const to = path.join(dest, skill.id);
  copyDir(from, to);
  console.log(`  ${green}✓${reset} installed: ${skill.id}`);
}

function printHooks(installed) {
  const stopHooks = installed.filter(s => s.hook && s.hook().event === 'Stop').map(s => s.hook().entry);
  const preHooks  = installed.filter(s => s.hook && s.hook().event === 'PreToolUse').map(s => s.hook().entry);
  if (!stopHooks.length && !preHooks.length) return;
  const hooks = {};
  if (stopHooks.length) hooks.Stop       = stopHooks;
  if (preHooks.length)  hooks.PreToolUse = preHooks;
  console.log('\nAdd to ~/.claude/settings.json:\n');
  console.log(JSON.stringify({ hooks }, null, 2));
}

// ── Interactive checkbox selector ──────────────────────────────────────────

const HEADER_LINES    = 4; // blank + guide + blank + column header
const LINES_PER_SKILL = 3; // name/toggle, prereqs, blank spacer

function renderMenu(skills, checks, selected, cursor, firstRender) {
  const total = HEADER_LINES + skills.length * LINES_PER_SKILL;

  if (!firstRender) process.stdout.write(`${E}[${total}A`);

  // Header
  process.stdout.write(`${clrLine}\n`);
  process.stdout.write(
    `${clrLine}  Controls: ${bold}↑↓${reset} move  ${bold}Space${reset} toggle  ` +
    `${bold}a${reset} toggle all  ${bold}Enter${reset} confirm  ${bold}q${reset} cancel\n`
  );
  process.stdout.write(`${clrLine}\n`);
  process.stdout.write(`${clrLine}  ${dim}  skill                       description${reset}\n`);

  skills.forEach((skill, i) => {
    const isCursor = i === cursor;
    const arrow    = isCursor ? `${cyan}›${reset}` : ' ';
    const box      = selected[i] ? `${green}[x]${reset}` : '[ ]';
    const nameCol  = skill.id.padEnd(26);
    const prereqStr = checks[i]
      .map(c => (c.passed ? `${green}✓${reset}` : `${red}✗${reset}`) + ' ' + c.label)
      .join('   ');
    const missing = checks[i].filter(c => !c.passed);
    const warn    = missing.length
      ? `${yellow}  ⚠ need: ${missing.map(c => c.label.split('(')[0].trim()).join(', ')}${reset}`
      : '';

    process.stdout.write(`${clrLine}  ${arrow} ${box} ${nameCol}${skill.desc}\n`);
    process.stdout.write(`${clrLine}       ${dim}${prereqStr}${reset}${warn}\n`);
    process.stdout.write(`${clrLine}\n`);
  });
}

async function selectSkillsInteractive(skills) {
  const checks   = skills.map(checkSkill);
  // Default: check skills where all prereqs pass
  const selected = skills.map((_, i) => checks[i].every(c => c.passed));
  let cursor = 0;

  return new Promise(resolve => {
    readline.emitKeypressEvents(process.stdin);
    process.stdin.setRawMode(true);

    renderMenu(skills, checks, selected, cursor, true);

    function cleanup() {
      process.stdin.removeListener('keypress', onKey);
      process.stdin.setRawMode(false);
    }

    function onKey(_str, key) {
      if (!key) return;
      if (key.ctrl && key.name === 'c') { cleanup(); process.exit(0); }

      if      (key.name === 'up'   || key.name === 'k') cursor = (cursor - 1 + skills.length) % skills.length;
      else if (key.name === 'down' || key.name === 'j') cursor = (cursor + 1) % skills.length;
      else if (key.name === 'space') selected[cursor] = !selected[cursor];
      else if (key.name === 'a') {
        const any = selected.some(Boolean);
        for (let i = 0; i < selected.length; i++) selected[i] = !any;
      } else if (key.name === 'return') {
        cleanup();
        process.stdout.write('\n');
        resolve(skills.filter((_, i) => selected[i]));
        return;
      } else if (key.name === 'escape' || key.name === 'q') {
        cleanup();
        process.stdout.write('\n');
        resolve(null);
        return;
      }

      renderMenu(skills, checks, selected, cursor, false);
    }

    process.stdin.on('keypress', onKey);
  });
}

// ── Main ───────────────────────────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);
  let selected;

  if (args.length) {
    selected = args.includes('all')
      ? SKILLS
      : SKILLS.filter(s => args.includes(s.id));
    if (!selected.length) {
      console.error(`Unknown skill(s): ${args.join(', ')}`);
      console.error(`Available: ${SKILLS.map(s => s.id).join(', ')}, all`);
      process.exit(1);
    }
  } else if (process.stdin.isTTY) {
    const result = await selectSkillsInteractive(SKILLS);
    if (result === null)  { console.log('Cancelled.'); return; }
    if (!result.length)   { console.log('Nothing selected.'); return; }
    selected = result;
  } else {
    selected = SKILLS;
    console.log('Non-interactive: installing all skills.');
  }

  fs.mkdirSync(dest, { recursive: true });
  console.log();
  selected.forEach(installSkill);
  printHooks(selected);
}

main().catch(err => { console.error(err.message); process.exit(1); });
