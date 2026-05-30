#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const os = require('os');

const dest = path.join(os.homedir(), '.claude', 'skills');
const src = path.join(__dirname, '..', 'plugins', 'skills');
const skills = ['graphify-link', 'codegraph-link', 'mistake-learning'];

fs.mkdirSync(dest, { recursive: true });

for (const skill of skills) {
  copyDir(path.join(src, skill), path.join(dest, skill));
  console.log(`  installed: ${skill}`);
}

const isWin = process.platform === 'win32';
const skillsDir = isWin
  ? '%USERPROFILE%\\.claude\\skills'
  : '$HOME/.claude/skills';
const sep = isWin ? '\\\\' : '/';
const py = isWin ? 'py' : 'python3';

console.log('\nInstalled to ~/.claude/skills/');
console.log('\nAdd these hooks to ~/.claude/settings.json:\n');
console.log(JSON.stringify({
  hooks: {
    Stop: [{
      command: `${py} "${skillsDir}${sep}mistake-learning${sep}hooks${sep}stop-hook.py"`,
      description: 'Increment mistake counters on session end'
    }],
    PreToolUse: [{
      matcher: 'graphify',
      command: `${py} "${skillsDir}${sep}graphify-link${sep}hooks${sep}intercept-graphify-skill.py"`,
      description: 'Fast-path graphify driver'
    }]
  }
}, null, 2));

function copyDir(from, to) {
  fs.mkdirSync(to, { recursive: true });
  for (const entry of fs.readdirSync(from, { withFileTypes: true })) {
    const s = path.join(from, entry.name);
    const d = path.join(to, entry.name);
    entry.isDirectory() ? copyDir(s, d) : fs.copyFileSync(s, d);
  }
}
