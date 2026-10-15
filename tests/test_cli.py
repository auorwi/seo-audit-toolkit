import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def cli(self, *args):
        self.assertTrue((ROOT / 'seo.py').exists(), 'CLI entrypoint missing')
        return subprocess.run([sys.executable, str(ROOT / 'seo.py'), *map(str, args)],
                              capture_output=True, text=True, timeout=30)

    def test_init_profile_and_second_site_isolation(self):
        with tempfile.TemporaryDirectory(prefix='seo cli ') as d:
            r = self.cli('init', '--site', 'https://example.org/', '--data-dir', d)
            self.assertEqual(r.returncode, 0, r.stderr)
            p = Path(json.loads(r.stdout)['profile'])
            first = json.loads(p.read_text())
            self.assertEqual(first['site'], 'example.org')
            self.assertEqual(first['business_profile'], 'generic')
            self.assertEqual(first['allowed_hosts'], ['example.org'])
            r2 = self.cli('init', '--site', 'https://example.com/', '--data-dir', d)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertNotEqual(p.parent, Path(json.loads(r2.stdout)['profile']).parent)
            repeat = self.cli('init', '--site', 'https://example.org/', '--data-dir', d)
            self.assertNotEqual(repeat.returncode, 0)
            self.assertIn(str(p), repeat.stderr)
            self.assertIn('reuse', repeat.stderr.lower())
            self.assertIn('edit', repeat.stderr.lower())
            self.assertEqual(json.loads(p.read_text()), first)

    def test_init_rejects_secret_private_and_non_http(self):
        with tempfile.TemporaryDirectory() as d:
            for u in ['file:///tmp/page.html', 'http://127.0.0.1/', 'https://example.org/?token=x', 'https://me:secret@example.org/']:
                with self.subTest(url=u):
                    self.assertNotEqual(self.cli('init', '--site', u, '--data-dir', d).returncode, 0)

    def test_init_requires_explicit_ascii_punycode_hosts(self):
        with tempfile.TemporaryDirectory() as d:
            for host in ['faß.de','bücher.de','K.com','a\u200cb.de']:
                with self.subTest(host=host):
                    result=self.cli('init','--site','https://'+host+'/','--data-dir',d)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn('punycode',result.stderr)
            extra=self.cli('init','--site','https://example.com/','--allow-host','faß.de','--data-dir',d)
            self.assertNotEqual(extra.returncode,0);self.assertIn('punycode',extra.stderr)
            self.assertEqual(list(Path(d).glob('*/profile.json')),[])
            result=self.cli('init','--site','https://xn--fa-hia.de/','--data-dir',d)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['site'],'xn--fa-hia.de')

    def test_doctor_base_does_not_require_optional_accounts(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.cli('doctor', '--runtime-dir', d)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertTrue(data['base_ready'])
            self.assertFalse(data['browser']['ready'])
            self.assertIn('optional', data['webmaster_platforms'])

    def test_specialist_dispatch_explicit_profile_and_native_help(self):
        r = self.cli('run', 'tdk', '--profile', ROOT / 'profiles/example.json', '--', '--help')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('--manifest', r.stdout)
        self.assertNotEqual(self.cli('run', '../other', '--profile', ROOT / 'profiles/example.json').returncode, 0)

    def test_missing_profile_fails_before_network(self):
        r = self.cli('audit', '--profile', '/does-not-exist', '--output', '/does-not-exist/report')
        self.assertNotEqual(r.returncode, 0)


if __name__ == '__main__':
    unittest.main()
