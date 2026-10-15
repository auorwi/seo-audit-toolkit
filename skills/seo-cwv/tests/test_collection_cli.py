import tempfile,json,subprocess,sys
from pathlib import Path
from support import CWVTest,ROOT,URL
class CollectionTests(CWVTest):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def run_cli(self,urls=None,*extra):
        script=ROOT/'scripts/collect_lab.py';self.assertTrue(script.exists(),'尚未实现CWV采集CLI');p=self.root/'urls.json';p.write_text(json.dumps(urls if urls is not None else [URL]));return subprocess.run([sys.executable,str(script),'--urls-file',str(p),'--runtime','/runtime','--chrome','/Chrome','--output',str(self.root/'out'),'--lock',str(self.root/'perf.lock'),'--plan-only',*extra],capture_output=True,text=True,timeout=10)
    def test_plan_grid_both_devices_three_runs(self):
        r=self.run_cli();self.assertEqual(r.returncode,0,r.stderr);p=json.loads((self.root/'out/plan.json').read_text());self.assertEqual(len(p['cells']),2);self.assertEqual(sum(c['config']['ci']['collect']['numberOfRuns'] for c in p['cells']),6)
    def test_plan_only_no_measured_results(self):
        self.run_cli();m=json.loads((self.root/'out/manifest.json').read_text());self.assertEqual(m['lab_runs'],[]);self.assertEqual(len(m['expected_cells']),2)
    def test_duplicate_url_no_duplicate_jobs(self):
        self.run_cli([URL,URL]);self.assertEqual(len(json.loads((self.root/'out/plan.json').read_text())['cells']),2)
    def test_bad_target_rejected(self):self.assertEqual(self.run_cli(['https://evil.test']).returncode,1)
    def test_existing_output_protected(self):
        self.run_cli();p=self.root/'out/plan.json';old=p.read_bytes();self.assertEqual(self.run_cli().returncode,1);self.assertEqual(p.read_bytes(),old)
    def test_resume_scope_change_rejected(self):
        self.run_cli();self.assertEqual(self.run_cli(['https://bingx.com/en/'],'--resume').returncode,1)
    def test_resume_identical_plan_allowed(self):
        self.run_cli();self.assertEqual(self.run_cli(None,'--resume').returncode,0)
    def test_single_device_scope_explicit(self):
        self.run_cli(None,'--device','desktop');self.assertEqual(len(json.loads((self.root/'out/plan.json').read_text())['cells']),1)
