import json,subprocess,tempfile
from pathlib import Path
from support import StructuredTest,ROOT,URL
class CollectionCliTests(StructuredTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.config=self.root/'config.json'
        self.config.write_text(json.dumps({'mainSelector':'main','identitySelector':'h1','expectedIdentity':'BTC','placeholderSelector':'.loading','errorSelector':'.error'}))
    def run_cli(self,extra=None):
        script=ROOT/'scripts/collect_page.mjs';self.assertTrue(script.exists(),'尚未实现008浏览器CLI')
        return subprocess.run(['node',str(script),'--url',URL,'--config',str(self.config),'--runtime',str(self.root/'missing'),'--browser-executable','missing','--output',str(self.root/'out')]+(extra or []),capture_output=True,text=True)
    def test_external_target_rejected(self):self.assertIn('unsupported_target',self.run_cli(['--url','https://example.com/']).stderr)
    def test_signals_required(self):
        self.config.write_text('{}');self.assertIn('template_signals_required',self.run_cli().stderr)
    def test_budget_positive(self):
        c=json.loads(self.config.read_text());c['timeoutMs']=0;self.config.write_text(json.dumps(c));self.assertIn('invalid_capture_budget',self.run_cli().stderr)
    def test_existing_output_not_modified(self):
        (self.root/'out').mkdir();(self.root/'out/keep').write_text('keep');self.assertIn('output_directory_not_empty',self.run_cli().stderr);self.assertEqual((self.root/'out/keep').read_text(),'keep')
    def test_internal_navigation_requires_origin_and_observed_link_selector(self):
        self.assertIn('entry_contract_required',self.run_cli(['--entry-origin','https://bingx.com/en/price']).stderr)
    def test_external_entry_origin_rejected(self):
        self.assertIn('unsupported_entry_origin',self.run_cli(['--entry-origin','https://example.com/','--entry-link','a']).stderr)
    def test_unavailable_runtime_never_writes_successful_manifest(self):
        r=self.run_cli();self.assertEqual(r.returncode,1);self.assertFalse((self.root/'out/manifest.json').exists())
    def test_content_checks_require_selector_and_nonempty_predicate(self):
        for checks in ['bad',[{}],[{'selector':'#reward'}],[{'selector':'#reward','forbiddenText':''}]]:
            c=json.loads(self.config.read_text());c['contentChecks']=checks;self.config.write_text(json.dumps(c))
            self.assertIn('invalid_content_checks',self.run_cli().stderr)
