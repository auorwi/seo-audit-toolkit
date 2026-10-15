"""Exercise delivered entry point, persistent SQLite, and readable output."""
import unittest,tempfile,json,subprocess,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CLI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.man={'schema_version':1,'property':'sc-domain:bingx.com','scope':[{'url':'https://bingx.com/en','device':'MOBILE'}],'evidence':[]}
    def run_cli(self,out='report',extra=None):
        p=self.root/'manifest.json';p.write_text(json.dumps(self.man));return subprocess.run([sys.executable,str(ROOT/'scripts/audit_gsc.py'),'--manifest',str(p),'--state',str(self.root/'state'),'--output',str(self.root/out),'--at','2026-09-17T00:00:00Z',*(extra or [])],text=True,capture_output=True)
    def test_empty_evidence_is_partial_and_outputs_gaps(self):
        r=self.run_cli();self.assertEqual(r.returncode,2,r.stderr);self.assertTrue((self.root/'report/report.json').is_file(),r.stderr);data=json.loads((self.root/'report/report.json').read_text());self.assertFalse(data['coverage']['declared_checks_complete']);self.assertGreater(len(data['gaps']),0)
    def test_report_has_machine_data_and_human_artifact(self):
        r=self.run_cli();self.assertEqual(r.returncode,2,r.stderr)
        for f in ['report.md','report.json','checks.json','findings.csv','issue-history.csv','issue-history.json','referrals.json']:self.assertTrue((self.root/'report'/f).is_file(),f)
    def test_existing_output_not_overwritten(self):
        p=self.root/'report';p.mkdir();(p/'report.md').write_text('keep me');r=self.run_cli();self.assertEqual(r.returncode,1,r.stderr);self.assertEqual((p/'report.md').read_text(),'keep me');self.assertFalse((self.root/'state/issues.sqlite').exists())
    def test_wrong_property_no_state(self):
        self.man['property']='sc-domain:evil.org';r=self.run_cli();self.assertEqual(r.returncode,1,r.stderr);self.assertFalse((self.root/'state/issues.sqlite').exists())
    def test_invalid_age_no_state(self):
        r=self.run_cli(extra=['--max-age-hours','nan']);self.assertEqual(r.returncode,1,r.stderr);self.assertFalse((self.root/'state/issues.sqlite').exists())
    def test_persistent_replay_has_one_sighting(self):
        raw={'kind':'inspection_api','property':'sc-domain:bingx.com','captured_at':'2026-09-16T23:00:00Z','http_status':200,'request':{'siteUrl':'sc-domain:bingx.com','inspectionUrl':'https://bingx.com/en'},'response':{'inspectionResult':{'indexStatusResult':{'verdict':'FAIL','pageFetchState':'SERVER_ERROR','crawledAs':'MOBILE'}}}}
        b=json.dumps(raw).encode();(self.root/'api.json').write_bytes(b);self.man['evidence']=[{'id':'e1','kind':'inspection_api','path':'api.json','sha256':hashlib.sha256(b).hexdigest()}]
        self.assertEqual(self.run_cli('one').returncode,2);self.assertEqual(self.run_cli('two').returncode,2);self.assertTrue((self.root/'two/issue-history.json').is_file());h=json.loads((self.root/'two/issue-history.json').read_text());self.assertEqual(len(h),1);self.assertEqual(h[0]['sightings'],1)
if __name__=='__main__':unittest.main()
