import tempfile,subprocess,json,sys
from pathlib import Path
from support import IntegrityTest,ROOT
from test_adapters import ManifestFixture
from test_comparison import AT

class CLITests(IntegrityTest):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name);self.f=ManifestFixture(self.base)
    def run_cli(self,extra=None):
        script=ROOT/'scripts/audit_content.py';self.assertTrue(script.exists(),'012 audit CLI missing')
        return subprocess.run([sys.executable,str(script),'--manifest',str(self.f.write()),'--state',str(self.base/'state'),'--output',str(self.base/'out'),'--at',AT]+(extra or []),capture_output=True,text=True)
    def test_success_writes_all_artifacts(self):
        r=self.run_cli();self.assertEqual(r.returncode,0,r.stderr)
        for name in ['report.md','report.json','findings.csv','checks.json','issue-history.json','issue-history.csv']:self.assertTrue((self.base/'out'/name).is_file())
    def test_partial_exit_two(self):self.f.check['citations']=[];self.assertEqual(self.run_cli().returncode,2)
    def test_invalid_version_exit_one(self):self.f.manifest['schema_version']=9;self.assertEqual(self.run_cli().returncode,1)
    def test_existing_output_not_overwritten(self):
        (self.base/'out').mkdir();(self.base/'out/keep').write_text('safe');r=self.run_cli();self.assertEqual(r.returncode,1);self.assertEqual((self.base/'out/keep').read_text(),'safe');self.assertFalse((self.base/'state').exists())
    def test_report_does_not_claim_global_health(self):
        self.run_cli();body=(self.base/'out/report.md').read_text();self.assertIn('不证明全站',body);self.assertIn('首次',body)
    def test_no_network_replay(self):
        r=self.run_cli();self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['findings'],1)

class CollectionCLITests(IntegrityTest):
    def invoke(self,args):
        script=ROOT/'scripts/collect_page.mjs';self.assertTrue(script.exists(),'012 collection CLI missing')
        return subprocess.run(['node',str(script)]+args,capture_output=True,text=True,timeout=15)
    def test_rejects_non_bingx_before_browser(self):
        r=self.invoke(['--url','https://example.com']);self.assertNotEqual(r.returncode,0);self.assertIn('unsupported_target',r.stderr)
    def test_rejects_credentials(self):self.assertIn('unsupported_target',self.invoke(['--url','https://user:pw@bingx.com/en']).stderr)
    def test_rejects_http(self):self.assertIn('unsupported_target',self.invoke(['--url','http://bingx.com/en']).stderr)
    def test_requires_observed_template_signals(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'config.json';p.write_text('{}');r=self.invoke(['--url','https://bingx.com/en/price/bitcoin','--config',str(p)]);self.assertIn('template_signals_required',r.stderr)
    def test_no_unknown_trade_option(self):self.assertNotEqual(self.invoke(['--trade','true']).returncode,0)
