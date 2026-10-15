import unittest,tempfile,json,sys,subprocess,copy
from pathlib import Path
import test_evidence as h
from recheck.audit import audit
try:from recheck.delivery import record,history,write_report
except ImportError:record=history=write_report=None
class Delivery(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(record,'Recheck delivery missing');self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);self.plan=h.fixture(self.root)
 load=h.Evidence.load
 def result(self):return audit(self.load(),at=h.AT)
 def test_same_run_no_duplicate_sighting(self):
  r=self.result();p=self.root/'x.db';record(p,r);record(p,r);self.assertEqual(history(p)[0]['sightings'],1)
 def test_recurrence_same_original_issue(self):
  r=self.result();p=self.root/'x.db';record(p,r);r['at']='2026-09-17T05:00:00Z';r['rechecks'][0]['status']='failed';r['rechecks'][0]['repair_verified']=False;record(p,r);hist=history(p);self.assertEqual(len(hist),1);self.assertEqual(hist[0]['issue_id'],h.ID);self.assertEqual(hist[0]['status'],'failed');self.assertEqual(hist[0]['sightings'],2)
 def test_out_of_order_replay_does_not_override_latest(self):
  r=self.result();old=copy.deepcopy(r);r['at']='2026-09-17T05:00:00Z';r['rechecks'][0]['status']='failed';p=self.root/'x.db';record(p,r);record(p,old);self.assertEqual(history(p)[0]['status'],'failed')
 def test_absent_issue_not_closed(self):
  r=self.result();p=self.root/'x.db';record(p,r);r['rechecks']=[];r['at']='2026-09-17T05:00:00Z';record(p,r);self.assertEqual(len(history(p)),1)
 def test_fixture_uses_separate_state_namespace(self):
  r=self.result();p=self.root/'x.db';record(p,r);r['run_kind']='audit';record(p,r);self.assertEqual(len(history(p)),2)
 def test_overwrite_rejected(self):
  p=self.root/'out';write_report(p,self.result(),[])
  with self.assertRaises(ValueError):write_report(p,self.result(),[])
 def test_readable_report_keeps_original_id(self):
  p=self.root/'out';write_report(p,self.result(),[]);text=(p/'report.md').read_text();self.assertIn(h.ID,text);self.assertIn('控制样例',text)
 def test_json_contains_before_after_evidence(self):
  p=self.root/'out';write_report(p,self.result(),[]);r=json.loads((p/'report.json').read_text());self.assertEqual(r['rechecks'][0]['cases'][0]['baseline']['result']['observed'],['BTCUSDT']);self.assertEqual(r['rechecks'][0]['cases'][0]['attempts'][0]['observed'],['EURCAD'])
 def cli(self):
  p=self.root/'plan.json';p.write_text(json.dumps(self.plan));return subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/recheck_issues.py'),'--plan',str(p),'--state',str(self.root/'state'),'--output',str(self.root/'out'),'--at',h.AT],capture_output=True,text=True)
 def test_cli_complete_returns_zero(self):
  r=self.cli();self.assertEqual(r.returncode,0,r.stderr)
 def test_cli_missing_after_partial(self):
  self.plan['issues'][0]['cases'][0]['after']=[];r=self.cli();self.assertEqual(r.returncode,2,r.stderr);self.assertTrue((self.root/'out/report.json').exists())
 def test_cli_bad_plan_no_report(self):
  self.plan={};r=self.cli();self.assertEqual(r.returncode,1,r.stderr);self.assertFalse((self.root/'out').exists())
 def test_failed_check_is_completed_audit_not_runtime_failure(self):
  self.plan['issues'][0]['cases'][0]['after']=[h.snapshot(self.root,'failure.json','2026-09-17T03:00:00Z',['BTCUSDT'])];r=self.cli();self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads((self.root/'out/report.json').read_text())['rechecks'][0]['status'],'failed')
