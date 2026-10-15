import json,subprocess,tempfile
from pathlib import Path
from support import TdkTest,ROOT,URL
class CollectionCliTests(TdkTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.config=self.root/'config.json';self.config.write_text(json.dumps({'mainSelector':'main','identitySelector':'#entity','expectedIdentity':'SOLV','placeholderSelector':'.loading','errorSelector':'.error'}))
    def run_cli(self,extra=None):
        script=ROOT/'scripts/collect_page.mjs';self.assertTrue(script.is_file(),'尚未实现007采集CLI')
        return subprocess.run(['node',str(script),'--url',URL,'--config',str(self.config),'--runtime',str(self.root/'missing'),'--browser-executable','missing','--output',str(self.root/'out')]+(extra or []),capture_output=True,text=True)
    def test_external_url_rejected_before_runtime(self):
        r=self.run_cli(['--url','https://example.com/']);self.assertEqual(r.returncode,1);self.assertIn('unsupported_target',r.stderr)
    def test_template_signals_mandatory(self):
        self.config.write_text('{}');r=self.run_cli();self.assertIn('template_signals_required',r.stderr)
    def test_invalid_budget_rejected(self):
        c=json.loads(self.config.read_text());c['timeoutMs']=-1;self.config.write_text(json.dumps(c));self.assertIn('invalid_capture_budget',self.run_cli().stderr)
    def test_existing_output_not_overwritten(self):
        (self.root/'out').mkdir();(self.root/'out/keep').write_text('keep');r=self.run_cli();self.assertIn('output_directory_not_empty',r.stderr);self.assertEqual((self.root/'out/keep').read_text(),'keep')
    def test_missing_runtime_does_not_create_capture(self):
        r=self.run_cli();self.assertEqual(r.returncode,1);self.assertFalse((self.root/'out/manifest.json').exists())
