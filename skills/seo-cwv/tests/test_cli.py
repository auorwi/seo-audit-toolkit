import json,subprocess,sys,tempfile,hashlib
from pathlib import Path
from support import CWVTest,ROOT,AT,URL
from test_field import crux
class CLITests(CWVTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        def proof(name,data):
            b=json.dumps(data).encode();(self.root/name).write_bytes(b);return {'path':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
        d=crux();d['record']['metrics']['largest_contentful_paint']['percentiles']['p75']=4500
        ep=proof('field.json',d);qp=proof('query.json',{'source':'crux_api','request':{'url':URL,'formFactor':'PHONE'},'observed_at':AT,'status':200})
        self.manifest={'schema_version':1,'field_records':[{'source':'crux_api','evidence':ep,'query_evidence':qp}],'expected_cells':[{'url':URL,'device':'mobile'}]};(self.root/'m.json').write_text(json.dumps(self.manifest))
    def run_cli(self,*extra,out='out'):
        s=ROOT/'scripts/audit_cwv.py';self.assertTrue(s.exists(),'尚未实现CWV报告CLI');return subprocess.run([sys.executable,str(s),'--manifest',str(self.root/'m.json'),'--state',str(self.root/'state'),'--output',str(self.root/out),'--at',AT,*extra],capture_output=True,text=True,timeout=10)
    def test_field_findings_and_partial_scope(self):
        r=self.run_cli();self.assertEqual(r.returncode,2,r.stderr);d=json.loads((self.root/'out/report.json').read_text());self.assertEqual(d['findings'][0]['rule'],'field_p75_not_good');self.assertFalse(d['coverage']['laboratory_scope_complete'])
    def test_same_run_history_idempotent(self):
        self.run_cli();self.run_cli(out='out2');self.assertEqual(json.loads((self.root/'out2/issue-history.json').read_text())[0]['sightings'],1)
    def test_absent_data_not_fix(self):
        self.run_cli();(self.root/'m.json').write_text('{"schema_version":1}');self.run_cli(out='out2');self.assertEqual(json.loads((self.root/'out2/issue-history.json').read_text())[0]['status'],'open')
    def test_existing_report_not_overwritten(self):
        self.run_cli();old=(self.root/'out/report.json').read_bytes();self.assertEqual(self.run_cli().returncode,1);self.assertEqual((self.root/'out/report.json').read_bytes(),old)
    def test_machine_readable_matrices(self):
        self.run_cli();self.assertTrue((self.root/'out/lab-matrix.csv').exists());self.assertTrue((self.root/'out/field-matrix.csv').exists());self.assertTrue((self.root/'out/coverage.csv').exists())
    def test_bad_timestamp_error(self):self.assertEqual(self.run_cli('--at','bad').returncode,1)
    def test_empty_manifest_no_healthy_claim(self):
        (self.root/'m.json').write_text('{"schema_version":1}');self.assertEqual(self.run_cli().returncode,2)
    def test_baseline_input_provenance_saved(self):
        self.run_cli();r=self.run_cli('--baseline',str(self.root/'out/report.json'),out='out2');self.assertEqual(r.returncode,2,r.stderr);self.assertEqual(len(json.loads((self.root/'out2/report.json').read_text())['baseline_evidence']['sha256']),64)
    def test_report_discloses_business_validation_separately(self):
        self.run_cli();text=(self.root/'out/report.md').read_text();self.assertIn('业务页面复核',text);self.assertTrue((self.root/'out/page-reviews.csv').exists())
    def test_report_separates_reliable_baseline_from_raw_observations(self):
        self.run_cli();text=(self.root/'out/report.md').read_text();self.assertIn('环境检查',text);self.assertIn('可靠回归基线',text)
