import json,subprocess,tempfile,unittest
from pathlib import Path
from support import ROOT,URL

class CollectionCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.config=self.root/'config.json';self.config.write_text(json.dumps({'mainSelector':'main','identitySelector':'h1','expectedIdentity':'Prices','placeholderSelector':'.loading','errorSelector':'.error'}))

    def run_cli(self,extra=None,url=URL):
        script=ROOT/'scripts/collect_page.mjs';self.assertTrue(script.is_file(),'尚未实现独立浏览器采集命令')
        return subprocess.run(['node',str(script),'--url',url,'--config',str(self.config),'--runtime',str(self.root/'missing-runtime'),'--browser-executable',str(self.root/'missing-browser'),'--output',str(self.root/'report')]+(extra or []),capture_output=True,text=True)

    def test_cli_excludes_non_bingx_and_non_https_targets_before_browser(self):
        for url in ['https://example.com','http://bingx.com','https://user:password@bingx.com']:
            run=self.run_cli(url=url);self.assertEqual(run.returncode,1)
            self.assertEqual(json.loads(run.stderr)['reason'],'unsupported_target')
            self.assertFalse((self.root/'report').exists())

    def test_missing_template_signals_rejected(self):
        self.config.write_text('{}');run=self.run_cli()
        self.assertEqual(run.returncode,1);self.assertEqual(json.loads(run.stderr)['reason'],'template_signals_required')
        self.assertFalse((self.root/'report').exists())

    def test_invalid_budget_rejected(self):
        data=json.loads(self.config.read_text());data['timeoutMs']=-1;self.config.write_text(json.dumps(data))
        run=self.run_cli();self.assertEqual(run.returncode,1);self.assertEqual(json.loads(run.stderr)['reason'],'invalid_capture_budget')

    def test_existing_evidence_directory_not_overwritten(self):
        (self.root/'report').mkdir();(self.root/'report/keep').write_text('prior')
        run=self.run_cli();self.assertEqual(run.returncode,1);self.assertEqual(json.loads(run.stderr)['reason'],'output_directory_not_empty')
        self.assertEqual((self.root/'report/keep').read_text(),'prior')

    def test_missing_runtime_is_not_empty_success(self):
        run=self.run_cli();self.assertEqual(run.returncode,1)
        self.assertFalse((self.root/'report').exists())

    def test_collection_refuses_url_not_in_announced_plan_before_browser(self):
        scope=self.root/'scope.json';scope.write_text(json.dumps({'schema_version':1,'count':1,'targets':[{'url':'https://bingx.com/en/learn'}]}))
        run=self.run_cli(['--scope',str(scope)])
        self.assertEqual(run.returncode,1)
        self.assertEqual(json.loads(run.stderr)['reason'],'url_not_in_scope')
        self.assertFalse((self.root/'report').exists())

if __name__=='__main__':unittest.main()
