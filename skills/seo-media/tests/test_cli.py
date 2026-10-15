import json,tempfile,subprocess,sys,hashlib
from pathlib import Path
from support import MediaTest,ROOT
AT='2026-09-16T23:00:00Z'
class CliTests(MediaTest):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def audit(self,manifest):
        self.assertTrue((ROOT/'scripts/audit_media.py').is_file(),'media CLI missing');p=self.root/'manifest.json';p.write_text(json.dumps(manifest))
        return subprocess.run([sys.executable,str(ROOT/'scripts/audit_media.py'),'--manifest',str(p),'--state',str(self.root/'state'),'--output',str(self.root/'out'),'--at',AT],capture_output=True,text=True)
    def test_empty_capture_produces_partial_report_not_pass(self):
        r=self.audit({'schema_version':1,'scope':[{'url':'https://bingx.com/en/','devices':['desktop']}],'captures':[]});self.assertEqual(r.returncode,2,r.stderr);report=json.loads((self.root/'out/report.json').read_text());self.assertFalse(report['coverage']['declared_checks_complete']);self.assertTrue((self.root/'out/report.md').exists())
    def test_bad_scope_cli_returns_error(self):self.assertEqual(self.audit({'schema_version':1,'scope':[]}).returncode,1)
    def test_existing_report_not_overwritten(self):
        (self.root/'out').mkdir();(self.root/'out/keep').write_text('original');r=self.audit({'schema_version':1,'scope':[]});self.assertEqual(r.returncode,1);self.assertEqual((self.root/'out/keep').read_text(),'original')
    def collect(self,args):
        self.assertTrue((ROOT/'scripts/collect_page.mjs').is_file(),'media browser CLI missing');return subprocess.run(['node',str(ROOT/'scripts/collect_page.mjs'),*args],capture_output=True,text=True,timeout=15)
    def test_collector_rejects_other_site_before_browser_launch(self):
        r=self.collect(['--url','https://example.com']);self.assertEqual(r.returncode,1);self.assertIn('unsupported_target',r.stderr)
    def test_collector_rejects_credentials_in_url(self):self.assertIn('unsupported_target',self.collect(['--url','https://user:password@bingx.com/en/']).stderr)
    def test_collector_requires_device(self):self.assertIn('device_required',self.collect(['--url','https://bingx.com/en/']).stderr)
    def test_collector_requires_config_signals(self):
        p=self.root/'config.json';p.write_text('{}');r=self.collect(['--url','https://bingx.com/en/','--device','mobile','--config',str(p)]);self.assertIn('template_signals_required',r.stderr)
    def test_collector_refuses_invalid_capture_limit(self):
        p=self.root/'config.json';p.write_text(json.dumps({'mainSelector':'main','identitySelector':'h1','expectedIdentity':'x','placeholderSelector':'.loading','errorSelector':'.error','maxImages':-2}));r=self.collect(['--url','https://bingx.com/en/','--device','mobile','--config',str(p)]);self.assertIn('invalid_maxImages',r.stderr)
