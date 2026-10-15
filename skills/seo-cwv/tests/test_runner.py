import tempfile,json
from pathlib import Path
from support import CWVTest,URL
class RunnerTests(CWVTest):
    def config(self,**kw):return self.module('runner').build_collect_config(kw.pop('url',URL),kw.pop('device','mobile'),'/Chrome',**kw)
    def test_three_runs_default(self):self.assertEqual(self.config()['ci']['collect']['numberOfRuns'],3)
    def test_no_upload_configuration(self):self.assertNotIn('upload',self.config()['ci'])
    def test_mobile_cpu_profile(self):self.assertEqual(self.config()['ci']['collect']['settings']['throttling']['cpuSlowdownMultiplier'],4)
    def test_desktop_distinct_screen(self):self.assertFalse(self.config(device='desktop')['ci']['collect']['settings']['screenEmulation']['mobile'])
    def test_fewer_than_three_live_runs_rejected(self):
        with self.assertRaises(ValueError):self.config(runs=1)
    def test_non_bingx_live_url_rejected(self):
        with self.assertRaises(ValueError):self.config(url='https://bingx.com.evil.test/a')
    def test_credentials_rejected(self):
        with self.assertRaises(ValueError):self.config(url='https://user:secret@bingx.com/en')
    def test_fixture_local_explicit(self):self.assertEqual(self.config(url='http://127.0.0.1:12345/',runs=1,allow_local_fixture=True)['ci']['collect']['numberOfRuns'],1)
    def test_local_without_fixture_flag_rejected(self):
        with self.assertRaises(ValueError):self.config(url='http://127.0.0.1:12345/')
    def test_invalid_device_rejected(self):
        with self.assertRaises(ValueError):self.config(device='phone')
    def test_lock_excludes_concurrent_collector(self):
        m=self.module('runner')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'performance.lock'
            with m.PerformanceLock(p):
                with self.assertRaises(RuntimeError):
                    with m.PerformanceLock(p):pass
            with m.PerformanceLock(p):self.assertTrue(p.exists())
    def test_command_only_collect(self):
        m=self.module('runner');cmd=m.invocation(Path('/runtime'),Path('/config.json'),Path('/hook.cjs'));self.assertEqual(cmd[-2:],['collect','--config=/config.json']);self.assertIn('--require',cmd)
