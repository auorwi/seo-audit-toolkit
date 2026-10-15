#!/usr/bin/env python3
"""Run real isolated Chromium and extruct checks against controlled pages only."""
import argparse
import ast
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from toolkit.runtime import browser_executable

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--runtime-dir', type=Path, required=True)
args = p.parse_args()
runtime = args.runtime_dir.resolve()
chrome = browser_executable(runtime)
if not chrome:
    raise SystemExit('Missing browser: setup browser extras first')
env = {**os.environ, 'SEO_SITE_PROFILE': str(ROOT / 'profiles/bingx.json'),
       'SEO_BROWSER_RUNTIME': str(runtime / 'browser'), 'SEO_BROWSER_EXECUTABLE': chrome,
       'SEMANTICS_RUNTIME': str(runtime / 'browser'), 'SEMANTICS_CHROME': chrome,
       'EXTRUCT_PYTHON': str(runtime / 'structured/bin/python')}
commands = [[sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT / 'tests'), '-p', 'test_generic_specialists.py']]
for module in ['tdk', 'semantics', 'structured-data', 'international', 'internal-links']:
    path = ROOT / 'skills' / ('seo-' + module) / 'tests/browser_integration.py'
    command = [sys.executable, str(path)]
    if module == 'semantics':
        # The inherited public BingX acceptance case is not part of a controlled smoke.
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.ClassDef):
                command += [node.name + '.' + item.name for item in node.body
                            if isinstance(item, ast.FunctionDef) and item.name.startswith('test_')
                            and item.name != 'test_public_cli_emits_verifiable_manifest']
    commands.append(command)
commands.append([sys.executable, str(ROOT / 'skills/seo-structured-data/tests/extruct_integration.py')])
for command in commands:
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=240)
    output = result.stdout + result.stderr
    print(output, flush=True)
    if result.returncode or 'skipped=' in output:
        raise SystemExit(result.returncode or 1)
