import tempfile,sys,json,importlib.util
from pathlib import Path
from unittest.mock import patch
from support import CWVTest,ROOT,URL

class PreflightTests(CWVTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        spec=importlib.util.spec_from_file_location('cwv_collect_for_test',ROOT/'scripts/collect_lab.py');self.cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.cli)
        for name,version in [('@lhci/cli','0.15.1'),('lighthouse','12.6.1')]:
            p=self.root/'runtime/node_modules'/name/'package.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'version':version}))
        (self.root/'urls.json').write_text(json.dumps([URL]));(self.root/'Chrome').touch()
    def args(self,*more):return ['collect_lab.py','--urls-file',str(self.root/'urls.json'),'--runtime',str(self.root/'runtime'),'--chrome',str(self.root/'Chrome'),'--output',str(self.root/'out'),'--lock',str(self.root/'lock'),*more]
    def test_busy_host_preserves_full_plan_without_launch(self):
        self.assertTrue(hasattr(self.cli,'preflight'),'尚未实现采集前环境门禁')
        quality=self.module('environment').assess_load((300,200,100),(300,200,100),10)
        with patch.object(sys,'argv',self.args()),patch.object(self.cli,'preflight',return_value=quality),patch.object(self.cli,'run_lhci_cell') as launch:
            self.assertEqual(self.cli.main(),2);launch.assert_not_called()
        m=json.loads((self.root/'out/manifest.json').read_text());self.assertEqual(len(m['expected_cells']),2);self.assertEqual(m['lab_runs'],[]);self.assertEqual(len(m['collection_events']),1)
        loaded=self.module('adapters').load_manifest(self.root/'out/manifest.json');self.assertIn('collection_paused_high_host_load',[g['reason'] for g in loaded['gaps']])
    def test_unknown_host_not_automatically_accepted(self):
        self.assertTrue(hasattr(self.cli,'preflight'),'尚未实现采集前环境门禁')
        quality=self.module('environment').assess_load(None,None,None)
        with patch.object(sys,'argv',self.args()),patch.object(self.cli,'preflight',return_value=quality),patch.object(self.cli,'run_lhci_cell') as launch:
            self.assertEqual(self.cli.main(),2);launch.assert_not_called()
    def test_plan_only_has_no_measurement_preflight(self):
        self.assertTrue(hasattr(self.cli,'preflight'),'尚未实现采集前环境门禁')
        with patch.object(sys,'argv',self.args('--plan-only')),patch.object(self.cli,'preflight') as check:self.assertEqual(self.cli.main(),0);check.assert_not_called()
