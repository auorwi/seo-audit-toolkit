import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class QuickAuditTests(unittest.TestCase):
    def setUp(self):
        self.profile_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.profile_dir.cleanup)
        path = Path(self.profile_dir.name) / 'profile.json'
        path.write_text(json.dumps(self.profile()))
        self.environment = patch.dict(os.environ, {'SEO_SITE_PROFILE': str(path)})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def load(self):
        self.assertTrue((ROOT / 'toolkit' / 'quick_audit.py').is_file(), 'Unified audit is missing')
        from toolkit.quick_audit import audit
        return audit

    def profile(self):
        return {'site': 'example.org', 'allowed_hosts': ['example.org'],
                'seeds': ['https://example.org/'], 'sitemaps': ['https://example.org/sitemap.xml'],
                'excluded_path_patterns': ['/account'], 'query_variants_per_path': 2}

    def fetcher(self, mapping, calls):
        def fetch(url):
            calls.append(url)
            status, headers, body = mapping.get(url, (404, {}, b''))
            return {'url': url, 'status': status, 'headers': headers, 'body': body}
        return fetch

    def test_budget_and_raw_evidence_and_non_bingx_report(self):
        run = self.load()
        calls = []
        mapping = {
            'https://example.org/robots.txt': (200, {}, b'User-agent: *\nDisallow: /private'),
            'https://example.org/sitemap.xml': (200, {}, b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.org/about</loc></url></urlset>'),
            'https://example.org/': (200, {'content-type': 'text/html'}, b'<title>Hello</title><h1>Example</h1><a href="/private">Private</a><a href="/about">About</a><a href="https://outside.test/">External</a>'),
            'https://example.org/about': (200, {'content-type': 'text/html'}, b'<title>About</title><h1>About</h1>')}
        with tempfile.TemporaryDirectory() as d:
            r = run(self.profile(), Path(d) / 'report', max_pages=1, max_requests=5,
                    fetch=self.fetcher(mapping, calls))
            self.assertEqual(r['site'], 'example.org')
            self.assertEqual(len(r['pages']), 1)
            self.assertIn('missing_description', {f['rule'] for f in r['findings']})
            self.assertTrue((Path(d) / 'report' / 'report.md').is_file())
            self.assertTrue((Path(d) / 'report' / 'issues.csv').is_file())
            self.assertTrue((Path(d) / 'report' / r['pages'][0]['evidence']['path']).is_file())
            self.assertFalse(any('outside.test' in x or '/private' in x for x in calls))
            self.assertFalse(r['coverage']['browser_rendering'])
            self.assertTrue(r['coverage']['limits_reached'])

    def test_unknown_robots_blocks_pages_and_missing_is_not_passed(self):
        run = self.load()
        calls = []
        with tempfile.TemporaryDirectory() as d:
            result = run(self.profile(), Path(d) / 'r', fetch=self.fetcher({
                'https://example.org/robots.txt': (503, {}, b'unavailable')}, calls))
            self.assertEqual(len(result['pages']), 0)
            self.assertEqual(calls, ['https://example.org/robots.txt'])
            self.assertEqual(result['status'], 'partial')
            self.assertTrue(result['gaps'])

    def test_redirect_outside_scope_not_followed(self):
        run = self.load()
        calls = []
        with tempfile.TemporaryDirectory() as d:
            result = run(self.profile(), Path(d) / 'r', fetch=self.fetcher({
                'https://example.org/robots.txt': (404, {}, b''),
                'https://example.org/': (302, {'location': 'https://outside.test/'}, b'')}, calls))
            self.assertNotIn('https://outside.test/', calls)
            self.assertTrue(any(g['reason'] == 'redirect_outside_scope' for g in result['gaps']))

    def test_noindex_is_observation_not_unconditional_error(self):
        run = self.load()
        with tempfile.TemporaryDirectory() as d:
            r = run(self.profile(), Path(d) / 'r', fetch=self.fetcher({
                'https://example.org/robots.txt': (404, {}, b''),
                'https://example.org/': (200, {'content-type': 'text/html'}, b'<title>Private</title><meta name="robots" content="noindex"><h1>Private</h1>')}, []))
            f = next(f for f in r['findings'] if f['rule'] == 'noindex_declared')
            self.assertEqual(f['classification'], 'review')

    def test_secret_urls_and_non_page_actions_not_requested(self):
        run = self.load()
        calls = []
        with tempfile.TemporaryDirectory() as d:
            run(self.profile(), Path(d) / 'r', fetch=self.fetcher({
                'https://example.org/robots.txt': (404, {}, b''),
                'https://example.org/': (200, {'content-type': 'text/html'}, b'<title>Home</title><a href="/?token=private">Secret</a><a href="/account">Account</a><a href="/file.pdf">Download</a>')}, calls))
            self.assertFalse(any('token=' in x or '/account' in x or '.pdf' in x for x in calls))

    def test_nonempty_report_directory_not_overwritten(self):
        run = self.load()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'existing'; p.mkdir(); (p / 'report.md').write_text('keep')
            with self.assertRaises(ValueError):
                run(self.profile(), p, fetch=lambda _: None)
            self.assertEqual((p / 'report.md').read_text(), 'keep')

    def test_explicit_profile_works_without_or_with_unrelated_ambient_profile(self):
        for ambient in (None, str(ROOT / 'profiles/bingx.json')):
            with self.subTest(ambient=ambient), tempfile.TemporaryDirectory() as d:
                if ambient is None:
                    os.environ.pop('SEO_SITE_PROFILE', None)
                else:
                    os.environ['SEO_SITE_PROFILE'] = ambient
                result = self.load()(dict(self.profile(), sitemaps=[]), Path(d), fetch=self.fetcher({
                    'https://example.org/robots.txt': (404, {}, b''),
                    'https://example.org/': (200, {'content-type': 'text/html'}, b'<title>Home</title>')}, []))
                self.assertEqual(len(result['pages']), 1)

    def test_live_fetch_requires_matching_activated_profile_before_requests(self):
        for ambient in (None, str(ROOT / 'profiles/bingx.json')):
            with self.subTest(ambient=ambient), tempfile.TemporaryDirectory() as d:
                if ambient is None:
                    os.environ.pop('SEO_SITE_PROFILE', None)
                else:
                    os.environ['SEO_SITE_PROFILE'] = ambient
                with self.assertRaisesRegex(ValueError, 'matching activated SEO_SITE_PROFILE'):
                    self.load()(self.profile(), Path(d))
                self.assertFalse((Path(d) / 'evidence').exists())

    def test_encoded_robots_and_excluded_paths_are_not_fetched(self):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            self.load()(dict(self.profile(), sitemaps=[]), Path(d), fetch=self.fetcher({
                'https://example.org/robots.txt': (200, {}, b'User-agent: *\nDisallow: /private'),
                'https://example.org/': (200, {'content-type': 'text/html'},
                    b'<a href="/private">P</a><a href="/%70rivate">P</a><a href="/account">A</a><a href="/%61ccount">A</a>')}, calls))
        self.assertEqual(calls, ['https://example.org/robots.txt', 'https://example.org/'])

    def test_malformed_html_urls_are_localized_and_reports_saved(self):
        cases = [('anchor', b'<a href="http://[">Broken</a>', 'invalid_link'),
                 ('base', b'<base href="http://[">', 'invalid_base'),
                 ('canonical', b'<link rel="canonical" href="http://[">', 'invalid_canonical')]
        for label, markup, reason in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as d:
                result = self.load()(dict(self.profile(), sitemaps=[]), Path(d), fetch=self.fetcher({
                    'https://example.org/robots.txt': (404, {}, b''),
                    'https://example.org/': (200, {'content-type': 'text/html'}, markup + b'<a href="/valid">Valid</a>'),
                    'https://example.org/valid': (200, {'content-type': 'text/html'}, b'<title>Valid</title>')}, []))
                self.assertEqual(len(result['pages']), 2)
                self.assertTrue((Path(d) / 'report.json').is_file())
                self.assertTrue((Path(d) / 'report.md').is_file())
                if label == 'canonical':
                    self.assertIn(reason, {f['rule'] for f in result['findings']})
                else:
                    self.assertIn(reason, {g['reason'] for g in result['gaps']})

    def test_malformed_redirect_url_does_not_abort_other_seed(self):
        for technical in (False, True):
            with self.subTest(technical=technical), tempfile.TemporaryDirectory() as d:
                source = 'https://example.org/sitemap.xml' if technical else 'https://example.org/'
                mapping = {'https://example.org/robots.txt': (404, {}, b''),
                           source: (302, {'location': 'http://['}, b''),
                           'https://example.org/valid': (200, {'content-type': 'text/html'}, b'<title>Valid</title>')}
                profile = dict(self.profile(), seeds=['https://example.org/valid'] if technical else ['https://example.org/', 'https://example.org/valid'],
                               sitemaps=[source] if technical else [])
                result = self.load()(profile, Path(d), fetch=self.fetcher(mapping, []))
                self.assertEqual(len(result['pages']), 1)
                self.assertIn('invalid_redirect', {g['reason'] for g in result['gaps']})
                self.assertTrue((Path(d) / 'report.json').is_file())

    def test_malformed_robots_redirect_saves_partial_report(self):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            result = self.load()(dict(self.profile(), sitemaps=[]), Path(d), fetch=self.fetcher({
                'https://example.org/robots.txt': (302, {'location': 'http://['}, b'')}, calls))
            self.assertEqual(calls, ['https://example.org/robots.txt'])
            self.assertEqual(result['status'], 'partial')
            self.assertIn('invalid_redirect', {g['reason'] for g in result['gaps']})
            self.assertTrue((Path(d) / 'report.json').is_file())

    def test_redirect_cycles_are_gaps(self):
        for target in ('/', '/next'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as d:
                result = self.load()(dict(self.profile(), sitemaps=[]), Path(d), fetch=self.fetcher({
                    'https://example.org/robots.txt': (404, {}, b''),
                    'https://example.org/': (302, {'location': target}, b''),
                    'https://example.org/next': (302, {'location': '/'}, b'')}, []))
                self.assertEqual(result['status'], 'partial')
                self.assertIn('redirect_loop', {g['reason'] for g in result['gaps']})

    def test_convergent_redirects_to_successful_page_are_not_loops(self):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            result = self.load()(dict(self.profile(), seeds=['https://example.org/', 'https://example.org/other'], sitemaps=[]),
                Path(d), max_pages=3, fetch=self.fetcher({
                    'https://example.org/robots.txt': (404, {}, b''),
                    'https://example.org/': (302, {'location': '/valid'}, b''),
                    'https://example.org/other': (302, {'location': '/valid'}, b''),
                    'https://example.org/valid': (200, {'content-type': 'text/html'}, b'<title>Valid</title>')}, calls))
            self.assertEqual(result['status'], 'completed_scoped_http_audit')
            self.assertFalse(result['gaps'])
            self.assertEqual(calls.count('https://example.org/valid'), 1)

    def test_page_budget_still_allows_technical_sitemap_requests(self):
        for budget in (2, 3):
            with self.subTest(budget=budget), tempfile.TemporaryDirectory() as d:
                calls = []
                result = self.load()(self.profile(), Path(d), max_pages=1, max_requests=budget, fetch=self.fetcher({
                    'https://example.org/robots.txt': (404, {}, b''),
                    'https://example.org/': (200, {'content-type': 'text/html'}, b'<a href="/more">More</a>'),
                    'https://example.org/sitemap.xml': (200, {}, b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>')}, calls))
                self.assertLessEqual(len(calls), budget)
                self.assertEqual(result['coverage']['http_requests'], len(calls))
                self.assertEqual(len(result['sitemaps']), 1 if budget == 3 else 0)
                self.assertTrue(result['coverage']['limits_reached'])
                self.assertGreater(result['coverage']['queued'], 0)

    def test_last_request_slot_used_by_robots_is_not_counted_as_a_page(self):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            result = self.load()(dict(self.profile(), sitemaps=[]), Path(d), max_requests=1,
                                fetch=self.fetcher({'https://example.org/robots.txt': (404, {}, b'')}, calls))
            self.assertEqual(result['coverage']['page_requests'], 0)
            self.assertEqual(result['coverage']['http_requests'], 1)
            self.assertEqual(result['coverage']['queued'], 1)


if __name__ == '__main__':
    unittest.main()
