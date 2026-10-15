import unittest,copy
import test_evidence as h
from recheck.audit import audit
class EngineUpdates(unittest.TestCase):
 setUp=h.Evidence.setUp
 load=h.Evidence.load
 def attach(self,**kw):
  d={'skill_id':'016','at':'2026-09-17T03:30:00Z','findings':[],'checks':[{'url':h.URL,'device':'DESKTOP','js':'DISABLED','searchable':True,'engine_evidence':['database-1']}]};d.update(kw);self.plan['issues'][0]['engine_reports']=[{'platform':'yandex','source':h.save(self.root,'engine.json',d)}]
 def result(self):return audit(self.load(),at=h.AT)['rechecks'][0]
 def test_yandex_snapshot_independent_from_local_fix(self):
  self.attach();r=self.result();self.assertEqual(len(r.get('engine_observations',[])),1);self.assertFalse(r['engine_recovery_confirmed'])
 def test_indexed_true_not_clear_metadata_issue(self):
  self.attach();r=self.result();self.assertEqual(r.get('engine_observations',[{}])[0].get('status'),'snapshot_available_clearance_unverified')
 def test_same_issue_platform_evidence_still_reported(self):
  self.attach(findings=[{'issue_id':h.ID,'evidence':[{'mode':'engine_snapshot'}]}]);r=self.result();self.assertEqual(r.get('engine_observations',[{}])[0].get('status'),'issue_still_reported')
 def test_public_dom_finding_not_engine_reported(self):
  self.attach(findings=[{'issue_id':h.ID,'evidence':[{'mode':'public_dom'}]}]);r=self.result();self.assertEqual(r.get('engine_observations',[{}])[0].get('status'),'snapshot_available_clearance_unverified')
 def test_wrong_url_not_platform_verified(self):
  self.attach(checks=[{'url':h.URL+'?x=1','searchable':True}]);r=self.result();self.assertEqual(r.get('engine_observations',[{}])[0].get('status'),'exact_url_not_checked')
 def test_stale_report_not_fresh(self):
  self.attach(at='2026-09-01T00:00:00Z');r=self.load();self.assertTrue(r['gaps'])
 def test_wrong_engine_adapter_rejected(self):
  self.attach(skill_id='015');r=self.load();self.assertTrue(r['gaps'])
 def test_manual_content_review_with_platform_capture_not_native_alarm(self):
  self.attach(findings=[{'issue_id':h.ID,'classification':'reviewed_public_observation','evidence':[{'mode':'public_dom'},{'mode':'engine_live'}]}]);r=self.result();self.assertEqual(r['engine_observations'][0]['status'],'snapshot_available_clearance_unverified')
