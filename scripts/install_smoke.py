#!/usr/bin/env python3
"""Install a relocated source ZIP into disposable directories, then unregister it."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import install


def call(*args):
    result = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result


with tempfile.TemporaryDirectory(prefix='seo release smoke ') as name:
    base = Path(name)
    archive = base / 'source.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        for path in install.source_files(ROOT):
            z.write(path, 'source/' + str(path.relative_to(ROOT)))
    with zipfile.ZipFile(archive) as z:
        z.extractall(base / 'extracted')
    source = base / 'extracted/source'
    target, skills = base / 'managed', base / 'codex/.agents/skills'
    call(source / 'install.py', '--target', target, '--skills-dir', skills)
    shutil.rmtree(source)
    cli = target / 'current/seo.py'
    doctor = json.loads(call(cli, 'doctor', '--runtime-dir', base / 'no-extras').stdout)
    assert doctor['base_ready'] and not doctor['browser']['ready']
    initialized = json.loads(call(cli, 'init', '--site', 'https://example.org/', '--data-dir', base / 'sites').stdout)
    call(cli, 'run', 'tdk', '--profile', initialized['profile'], '--', '--help')
    # Exercise the installed report pipeline with deterministic, injected HTTP evidence.
    # Real public networking is verified separately by public_smoke.py.
    report_path = base / 'sites/example.org/reports/controlled-smoke'
    call('-c', '''
import json, os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
os.environ['SEO_SITE_PROFILE'] = sys.argv[2]
import seo
from crawlability.site import get_profile
from toolkit.quick_audit import audit
profile = get_profile()
profile['sitemaps'] = []
def fetch(url):
    if url.endswith('/robots.txt'):
        return {'url': url, 'status': 404, 'headers': {}, 'body': b''}
    return {'url': url, 'status': 200, 'headers': {'content-type': 'text/html'},
            'body': b'<title>Installed toolkit fixture</title><h1>Example</h1>'}
report = audit(profile, Path(sys.argv[3]), fetch=fetch, max_pages=1)
assert len(report['pages']) == 1
assert report['site'] == 'example.org'
assert 'missing_description' in {item['rule'] for item in report['findings']}
assert report['coverage']['browser_rendering'] is False
''', cli.resolve().parent, initialized['profile'], report_path)
    assert (report_path / 'report.md').is_file()
    assert (report_path / 'issues.csv').is_file()
    assert len(list(skills.glob('seo-*'))) == 20
    call(target / 'current/install.py', '--target', target, '--skills-dir', skills, '--uninstall')
    assert not list(skills.glob('seo-*'))
    assert Path(initialized['profile']).is_file()
    assert (report_path / 'report.json').is_file()
print(json.dumps({'relocated_zip_install': 'passed', 'skills': 20,
                  'installed_controlled_report': 'passed', 'uninstall_preserves_data': True}))
