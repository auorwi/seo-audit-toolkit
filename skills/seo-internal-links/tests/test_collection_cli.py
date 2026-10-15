import json,subprocess,tempfile
from pathlib import Path
from support import LinkTest,ROOT,URL
class CollectionTests(LinkTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.config=self.root/'config.json';self.config.write_text(json.dumps({'mainSelector':'main','identitySelector':'h1','expectedIdentity':'BTC','placeholderSelector':'.loading','errorSelector':'.error'}))
    def run_cli(self,extra=None):
        script=ROOT/'scripts/collect_page.mjs';self.assertTrue(script.exists(),'尚未实现009采集CLI')
        return subprocess.run(['node',str(script),'--url',URL,'--config',str(self.config),'--runtime',str(self.root/'missing'),'--browser-executable','missing','--output',str(self.root/'out')]+(extra or []),capture_output=True,text=True)
    def test_external_url_rejected(self):self.assertIn('unsupported_target',self.run_cli(['--url','https://example.com/']).stderr)
    def test_signals_required(self):
        self.config.write_text('{}');self.assertIn('template_signals_required',self.run_cli().stderr)
    def test_positive_budgets_required(self):
        d=json.loads(self.config.read_text());d['timeoutMs']=0;self.config.write_text(json.dumps(d));self.assertIn('invalid_capture_budget',self.run_cli().stderr)
    def test_pagination_needs_item_identity_selector(self):self.assertIn('pagination_items_required',self.run_cli(['--pagination-selector','button.next']).stderr)
    def test_pagination_needs_expected_control_text(self):
        d=json.loads(self.config.read_text());d['itemSelector']='.items a';self.config.write_text(json.dumps(d));self.assertIn('pagination_control_text_required',self.run_cli(['--pagination-selector','button.next']).stderr)
    def test_existing_output_not_overwritten(self):
        (self.root/'out').mkdir();(self.root/'out/keep').write_text('keep');self.assertIn('output_directory_not_empty',self.run_cli().stderr);self.assertEqual((self.root/'out/keep').read_text(),'keep')
    def test_missing_runtime_never_writes_success_manifest(self):
        r=self.run_cli();self.assertEqual(r.returncode,1);self.assertFalse((self.root/'out/manifest.json').exists())
