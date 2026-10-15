#!/usr/bin/env python3
"""Read one public example.org page through the real HTTP audit; retain all outcomes."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
args = p.parse_args()
root = args.output.resolve()
root.mkdir(parents=True)
profile = root / 'profile.json'
profile.write_text(json.dumps({'site': 'example.org', 'allowed_hosts': ['example.org'],
                              'seeds': ['https://example.org/'], 'sitemaps': [], 'business_profile': 'generic'}))
r = subprocess.run([sys.executable, str(ROOT / 'seo.py'), 'audit', '--profile', str(profile),
                    '--output', str(root / 'report'), '--max-pages', '1', '--max-requests', '5', '--no-follow-links'],
                   capture_output=True, text=True, timeout=90)
print(r.stdout)
print(r.stderr, file=sys.stderr)
report = json.loads((root / 'report/report.json').read_text())
assert len(report['pages']) == 1, 'Public network smoke did not acquire the example page'
assert report['pages'][0]['fields']['title'], 'Example page lacked parsed title'
assert report['site'] == 'example.org'
assert report['coverage']['browser_rendering'] is False
assert r.returncode in (0, 2)
