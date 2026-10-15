import json,tempfile,subprocess
from pathlib import Path
from support import InternationalTest,ROOT
class CollectionCLITests(InternationalTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.cfg={'mainSelector':'main','identitySelector':'h1','expectedIdentity':'Bitcoin','placeholderSelector':'.loading','errorSelector':'.error'}
    def run_cli(self,*extra,url='https://bingx.com/en/price/bitcoin'):
        script=ROOT/'scripts/collect_page.mjs';self.assertTrue(script.exists(),'尚未实现010采集CLI');p=self.root/'config.json';p.write_text(json.dumps(self.cfg));return subprocess.run(['node',str(script),'--url',url,'--config',str(p),'--output',str(self.root/'out'),*extra],capture_output=True,text=True,timeout=10)
    def test_external_host_refused(self):self.assertIn('unsupported_target',self.run_cli(url='https://bingx.com.evil.test/a').stderr)
    def test_credentials_refused(self):self.assertIn('unsupported_target',self.run_cli(url='https://me:password@bingx.com/a').stderr)
    def test_http_refused(self):self.assertIn('unsupported_target',self.run_cli(url='http://bingx.com/a').stderr)
    def test_missing_identity_signals(self):
        del self.cfg['expectedIdentity'];self.assertIn('template_signals_required',self.run_cli().stderr)
    def test_bad_budget_refused(self):
        self.cfg['timeoutMs']=-1;self.assertIn('invalid_capture_budget',self.run_cli().stderr)
    def test_switch_missing_config_refused(self):self.assertIn('switch_options_required',self.run_cli('--switch-selector','#fr').stderr)
