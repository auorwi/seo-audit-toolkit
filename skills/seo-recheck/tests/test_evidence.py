import sys,unittest,tempfile,json,hashlib,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:from recheck.evidence import load_plan
except ImportError:load_plan=None
AT='2026-09-17T04:00:00Z';URL='https://bingx.com/en/futures/forex/EURCAD';ID='yandex-actual-issue-id'
def save(root,name,obj):
 p=root/name;p.write_text(json.dumps(obj,ensure_ascii=False));return {'path':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def snapshot(root,name,at,h1):
 return {'kind':'dom','entry':'direct','source':save(root,name,{'url':URL,'captured_at':at,'navigation_at':at,'device':'DESKTOP','js':'ENABLED','h1':h1,'title':'EURCAD','body_excerpt':'excerpt'})}
def fixture(root):
 before=snapshot(root,'before.json','2026-09-16T01:00:00Z',['BTCUSDT']);after=snapshot(root,'after.json','2026-09-17T03:00:00Z',['EURCAD']);source=save(root,'source.json',{'skill_id':'016','at':'2026-09-16T02:00:00Z','findings':[{'issue_id':ID,'url':URL,'rule':'ROUTE_ENTITY_MISMATCH','owner_skill':'004','evidence':[{'source':before['source']}]}]});deployment=save(root,'deployment.txt.json',{'record':'Deployed 2026-09-17T02:00:00Z'});case={'id':'symptom','role':'symptom','url':URL,'device':'DESKTOP','js':'ENABLED','entry':'direct','predicate':{'field':'h1','op':'equals','expected':['EURCAD']},'baseline':before,'after':[after],'repetitions':1};issue={'issue_id':ID,'source_report':source,'scope_type':'url','deployment':{'at':'2026-09-17T02:00:00Z','source':deployment,'quote':'Deployed 2026-09-17T02:00:00Z'},'cases':[case]};return {'schema_version':1,'run_kind':'controlled_fixture','issues':[issue]}
class Evidence(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(load_plan,'Recheck evidence loader missing');self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);self.plan=fixture(self.root)
 def load(self):
  p=self.root/'plan.json';p.write_text(json.dumps(self.plan));return load_plan(p,at=AT,max_age_hours=24)
 def test_original_issue_id_retained(self):self.assertEqual(self.load()['issues'][0]['issue_id'],ID)
 def test_source_report_must_have_id(self):
  self.plan['issues'][0]['issue_id']='unknown';r=self.load();self.assertEqual(r['issues'],[]);self.assertTrue(r['gaps'])
 def test_tampered_report_quarantined(self):
  (self.root/'source.json').write_text('{}');self.assertEqual(self.load()['issues'],[])
 def test_unbound_baseline_rejected(self):
  self.plan['issues'][0]['cases'][0]['baseline']=snapshot(self.root,'invented.json','2026-09-16T01:00:00Z',['wrong']);r=self.load();self.assertTrue(r['gaps']);self.assertFalse(r['issues'][0]['cases'][0]['baseline'])
 def test_sha_wrong_after_preserved_as_gap(self):
  (self.root/'after.json').write_text('{}');r=self.load();self.assertEqual(r['issues'][0]['cases'][0]['after'],[]);self.assertTrue(r['gaps'])
 def test_stale_after_rejected(self):
  c=self.plan['issues'][0]['cases'][0];c['after']=[snapshot(self.root,'old.json','2026-09-01T00:00:00Z',['EURCAD'])];self.assertEqual(self.load()['issues'][0]['cases'][0]['after'],[])
 def test_future_after_rejected(self):
  c=self.plan['issues'][0]['cases'][0];c['after']=[snapshot(self.root,'future.json','2026-10-01T00:00:00Z',['EURCAD'])];self.assertEqual(self.load()['issues'][0]['cases'][0]['after'],[])
 def test_after_device_mismatch_rejected(self):
  self.plan['issues'][0]['cases'][0]['device']='MOBILE';r=self.load();self.assertEqual(r['issues'][0]['cases'][0]['after'],[])
 def test_entry_mismatch_rejected(self):
  self.plan['issues'][0]['cases'][0]['after'][0]['entry']='internal';self.assertEqual(self.load()['issues'][0]['cases'][0]['after'],[])
 def test_query_not_dropped(self):
  self.plan['issues'][0]['cases'][0]['url']=URL+'?currency=CAD';r=self.load();self.assertTrue(r['gaps'])
 def test_no_deployment_allowed_but_unknown(self):
  self.plan['issues'][0]['deployment']=None;self.assertIsNone(self.load()['issues'][0]['deployment_at'])
 def test_deployment_time_bound(self):
  self.plan['issues'][0]['deployment']['at']='2026-09-17T01:00:00Z';self.assertEqual(self.load()['issues'],[])
 def test_report_date_not_new_baseline_date(self):
  r=self.load();self.assertEqual(r['issues'][0]['cases'][0]['baseline']['captured_at'],'2026-09-16T01:00:00Z')
 def test_duplicate_capture_not_two_repetitions(self):
  c=self.plan['issues'][0]['cases'][0];c['after']*=2;c['repetitions']=2;r=self.load();self.assertEqual(len(r['issues'][0]['cases'][0]['after']),1)
 def test_control_does_not_require_failure_baseline(self):
  c=copy.deepcopy(self.plan['issues'][0]['cases'][0]);c.update(id='control',role='control',baseline=None);self.plan['issues'][0]['cases'].append(c);self.assertIsNone(self.load()['issues'][0]['cases'][1]['baseline'])
 def test_zero_repeat_rejected(self):
  self.plan['issues'][0]['cases'][0]['repetitions']=0;self.assertEqual(self.load()['issues'],[])
 def test_repeated_case_id_rejected(self):
  self.plan['issues'][0]['cases']*=2;self.assertEqual(self.load()['issues'],[])
 def test_duplicate_issue_ids_all_quarantined(self):
  self.plan['issues']*=2;self.assertEqual(self.load()['issues'],[])
 def test_scope_url_not_silent_template(self):
  self.plan['issues'][0]['scope_type']='global';self.assertEqual(self.load()['issues'],[])
 def test_path_escape(self):
  self.plan['issues'][0]['source_report']['path']='../outside.json';self.assertEqual(self.load()['issues'],[])
 def test_credentials_rejected(self):
  self.plan['access_token']='secret'
  with self.assertRaises(ValueError):self.load()
 def test_only_after_source_cannot_prove_original_baseline(self):
  self.plan['issues'][0]['cases'][0]['baseline']=self.plan['issues'][0]['cases'][0]['after'][0];self.assertIsNone(self.load()['issues'][0]['cases'][0]['baseline'])
 def test_case_no_symptom_rejected(self):
  self.plan['issues'][0]['cases'][0]['role']='control';self.assertEqual(self.load()['issues'],[])

 def test_valid_json_tamper_still_rejected_by_hash(self):
  p=self.root/'after.json';v=json.loads(p.read_text());v['h1']=['BTCUSDT'];p.write_text(json.dumps(v));r=self.load();self.assertEqual(r['issues'][0]['cases'][0]['after'],[]);self.assertTrue(any(g['reason']=='sha256_mismatch' for g in r['gaps']))
