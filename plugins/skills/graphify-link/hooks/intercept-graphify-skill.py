#!/usr/bin/env python3
"""
intercept-graphify-skill — cross-platform launcher for graphify-build.py.
No PowerShell required. Works on Windows (py), macOS, and Linux (python3).

Usage: python intercept-graphify-skill.py [plugin_root]
  plugin_root  path to the plugin root (default: auto-detected from script location)
"""
import os
import subprocess
import sys
from pathlib import Path


def find_driver(plugin_root: Path) -> Path | None:
    local = plugin_root / 'plugins' / 'skills' / 'graphify-link' / 'graphify-build.py'
    if local.exists():
        return local
    home = Path(os.environ.get('USERPROFILE', os.environ.get('HOME', str(Path.home()))))
    canonical = home / '.claude' / 'skills' / 'graphify-link' / 'graphify-build.py'
    if canonical.exists():
        return canonical
    return None


def main() -> int:
    # script lives at <plugin_root>/plugins/skills/graphify-link/hooks/
    plugin_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parents[4]
    print(f'[intercept-graphify-skill] plugin root: {plugin_root}')

    driver = find_driver(plugin_root)
    if driver is None:
        print('No graphify driver available', file=sys.stderr)
        return 1

    print(f'[intercept-graphify-skill] driver: {driver}')
    py_cmd = 'py' if os.name == 'nt' else 'python3'
    result = subprocess.run([py_cmd, str(driver), '--phase=auto'])
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
