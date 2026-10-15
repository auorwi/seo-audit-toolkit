"""Run each legacy unittest suite in isolation to avoid same-name test collisions."""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_tests(log_dir=None):
    directory = Path(log_dir or tempfile.mkdtemp(prefix='seo-test-logs-')).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    suites = [ROOT / 'tests'] + sorted(p for p in (ROOT / 'skills').glob('*/tests') if p.is_dir())
    results = []
    for suite in suites:
        name = 'toolkit' if suite == ROOT / 'tests' else suite.parent.name
        env = {**os.environ, 'SEO_SITE_PROFILE': str(ROOT / 'profiles/bingx.json'), 'PYTHONDONTWRITEBYTECODE': '1'}
        try:
            check = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(suite), '-p', 'test_*.py'],
                                   env=env, cwd=ROOT, capture_output=True, text=True, timeout=240)
            text = check.stdout + check.stderr
            count = re.search(r'Ran (\d+) tests?', text)
            skipped = re.search(r'skipped=(\d+)', text)
            row = {'suite': name, 'returncode': check.returncode, 'tests': int(count.group(1)) if count else 0,
                   'skipped': int(skipped.group(1)) if skipped else 0}
        except subprocess.TimeoutExpired as error:
            text = 'Suite timed out after 240 seconds\n'
            row = {'suite': name, 'returncode': 1, 'tests': 0, 'skipped': 0, 'timeout': True}
        (directory / (name + '.log')).write_text(text, encoding='utf-8')
        results.append(row)
        print(json.dumps(row), flush=True)
    summary = {'suites': len(results), 'tests': sum(x['tests'] for x in results),
               'skipped': sum(x['skipped'] for x in results),
               'failed_suites': [x['suite'] for x in results if x['returncode']], 'logs': str(directory)}
    (directory / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return int(bool(summary['failed_suites']))
