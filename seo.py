#!/usr/bin/env python3
"""SEO Audit Toolkit: site setup, bounded HTTP checks, and specialist dispatch."""
import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'skills/seo-crawlability/scripts'))
from crawlability.site import get_profile, require_url, _allowed, _host
from toolkit.runtime import doctor, setup, default_runtime

ENTRIES = {
    'update-url': 'update_url.py', 'sitemap': 'audit_sitemap.py', 'crawlability': 'audit_crawlability.py',
    'canonical-routing': 'audit_canonical.py', 'rendering': 'audit_rendering.py', 'semantics': 'audit_semantics.py',
    'tdk': 'audit_tdk.py', 'structured-data': 'audit_structured.py', 'internal-links': 'audit_links.py',
    'international': 'audit_international.py', 'cwv': 'audit_cwv.py', 'content-integrity': 'audit_content.py',
    'media': 'audit_media.py', 'gsc': 'audit_gsc.py', 'bing': 'audit_bing.py', 'yandex': 'audit_yandex.py',
    'recheck': 'recheck_issues.py', 'report': 'report_seo.py'}


def data_home():
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'seo-audit-toolkit/data'


def initialize(site, data_dir, brand='', hosts=None):
    parsed = urlsplit(site)
    if not parsed.netloc.isascii():raise ValueError('Unicode hostnames are not supported; use explicit ASCII punycode A-labels')
    host = _host(parsed.hostname or '')
    hosts = [_host(value) for value in (hosts or [])]
    profile = {'site': host, 'allowed_hosts': list(dict.fromkeys([host] + (hosts or []))),
               'seeds': [site], 'sitemaps': [parsed.scheme + '://' + parsed.netloc + '/sitemap.xml'],
               'brand': brand, 'business_profile': 'generic',
               'excluded_path_patterns': ['(?i)/(?:login|logout|sign-in|sign-out|register|account|checkout|cart|api)(?:/|$)'],
               'query_variants_per_path': 2}
    if not _allowed(site, profile) or parsed.query or parsed.fragment:
        raise ValueError('Use a public HTTP(S) site URL without credentials, query or fragment')
    slug = re.sub(r'[^a-zA-Z0-9._-]', '-', host)
    directory = Path(data_dir).expanduser().resolve() / slug
    path = directory / 'profile.json'
    directory.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('x', encoding='utf-8') as out:
            json.dump(profile, out, ensure_ascii=False, indent=2)
            out.write('\n')
    except FileExistsError:
        raise ValueError(f'Profile already exists: {path}. Reuse it with --profile, or edit it to change this site configuration.') from None
    os.environ['SEO_SITE_PROFILE'] = str(path)
    try:
        get_profile()
    except ValueError:
        path.unlink()
        raise
    return {'profile': str(path), 'site_data': str(directory), 'site': host,
            'next': 'Run doctor, then audit --profile with this file. Edit allowed_hosts only for intended hosts.'}


def activate_profile(path):
    path = Path(path).expanduser().resolve()
    os.environ['SEO_SITE_PROFILE'] = str(path)
    return path, get_profile()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    native = []
    if '--' in argv:
        separator = argv.index('--')
        native, argv = argv[separator + 1:], argv[:separator]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', action='version', version=(ROOT / 'VERSION').read_text().strip())
    commands = p.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init', help='Create a separate target-site profile; never overwrites an existing one')
    init.add_argument('--site', required=True)
    init.add_argument('--data-dir', type=Path, default=data_home())
    init.add_argument('--brand', default='')
    init.add_argument('--allow-host', action='append', default=[])
    check = commands.add_parser('doctor', help='Report installed capabilities; accounts are optional')
    check.add_argument('--runtime-dir', type=Path, default=default_runtime())
    check.add_argument('--probe-browser', action='store_true', help='Actually launch isolated browser and render a local HTML document')
    check.add_argument('--browser', type=Path)
    bootstrap = commands.add_parser('setup', help='Install selected optional dependencies, without accounts')
    bootstrap.add_argument('--extras', nargs='+', required=True, choices=['browser', 'cwv', 'structured'])
    bootstrap.add_argument('--runtime-dir', type=Path, default=default_runtime())
    bootstrap.add_argument('--system-browser', type=Path, help='Use this browser instead of downloading managed Chromium')
    quick = commands.add_parser('audit', help='Bounded initial-HTML checks; not all specialist audits')
    quick.add_argument('--profile', type=Path, required=True)
    quick.add_argument('--url', action='append', help='Override seed URLs within the configured scope')
    quick.add_argument('--output', type=Path)
    quick.add_argument('--max-pages', type=int, default=10)
    quick.add_argument('--max-requests', type=int, default=40)
    quick.add_argument('--delay', type=float, default=1)
    quick.add_argument('--timeout', type=float, default=20)
    quick.add_argument('--no-follow-links', action='store_true')
    runner = commands.add_parser('run', help='Run a specialist; put native arguments after --')
    runner.add_argument('module', choices=sorted(ENTRIES))
    runner.add_argument('--profile', type=Path, required=True)
    runner.add_argument('--script', help='Optional packaged script filename (for collection or alternate commands)')
    capture = commands.add_parser('capture', help='Collect browser evidence for a specialist with collect_page.mjs')
    capture.add_argument('module', choices=['tdk', 'semantics', 'structured-data', 'internal-links', 'international', 'media', 'content-integrity'])
    capture.add_argument('--profile', type=Path, required=True)
    capture.add_argument('--url', required=True)
    capture.add_argument('--output', type=Path, required=True)
    capture.add_argument('--runtime-dir', type=Path, default=default_runtime())
    capture.add_argument('--browser', type=Path)
    capture.add_argument('--config', type=Path)
    tests = commands.add_parser('test', help='Run offline toolkit and specialist regression tests')
    tests.add_argument('--log-dir', type=Path)
    args = p.parse_args(argv)
    try:
        if native and args.command not in {'run', 'capture'}:
            raise ValueError('Arguments after -- are only accepted by run/capture')
        if args.command == 'init':
            result = initialize(args.site, args.data_dir, args.brand, args.allow_host)
        elif args.command == 'doctor':
            result = doctor(args.runtime_dir, probe=args.probe_browser, browser=args.browser)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result['base_ready'] and (not args.probe_browser or result['browser'].get('probe_passed')) else 2
        elif args.command == 'setup':
            result = setup(args.extras, args.runtime_dir, args.system_browser)
        elif args.command == 'audit':
            path, profile = activate_profile(args.profile)
            if args.url:
                profile = dict(profile, seeds=[require_url(u) for u in args.url])
            if profile.get('test_only_allow_loopback'):
                raise ValueError('The live HTTP audit does not support fixture/private targets')
            output = args.output or path.parent / 'reports' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
            from toolkit.quick_audit import audit
            report = audit(profile, output, max_pages=args.max_pages, max_requests=args.max_requests,
                           delay=args.delay, timeout=args.timeout, follow_links=not args.no_follow_links)
            from toolkit.history import record
            record(path.parent / 'history.sqlite', report, output)
            result = {'status': report['status'], 'site': profile['site'], 'pages': len(report['pages']),
                      'findings': len(report['findings']), 'coverage': report['coverage'], 'output': str(Path(output).resolve())}
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2 if report['status'] == 'partial' else 0
        elif args.command == 'run':
            activate_profile(args.profile)
            script = args.script or ENTRIES[args.module]
            if not re.fullmatch(r'[a-zA-Z0-9_]+\.(?:py|mjs|cjs)', script):
                raise ValueError('Invalid packaged script name')
            path = ROOT / 'skills' / ('seo-' + args.module) / 'scripts' / script
            if not path.is_file():
                raise ValueError('Script is not included in this module')
            executable = sys.executable if path.suffix == '.py' else 'node'
            return subprocess.run([executable, str(path), *native], check=False).returncode
        elif args.command == 'capture':
            activate_profile(args.profile)
            require_url(args.url)
            capabilities = doctor(args.runtime_dir, browser=args.browser)
            if not capabilities['browser']['ready']:
                raise ValueError('Browser dependencies unavailable; run setup --extras browser and doctor --probe-browser')
            script = ROOT / 'skills' / ('seo-' + args.module) / 'scripts/collect_page.mjs'
            command = ['node', str(script), '--url', args.url, '--runtime', str(args.runtime_dir.resolve() / 'browser'),
                       '--browser-executable', capabilities['browser']['executable'], '--output', str(args.output)]
            if args.config:
                command += ['--config', str(args.config)]
            return subprocess.run(command + native, check=False).returncode
        else:
            from toolkit.testing import run_tests
            return run_tests(args.log_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
