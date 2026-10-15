import unittest,copy
import test_evidence as h
try:from recheck.audit import audit
except ImportError:audit=None
class Audit(unittest.TestCase):
 setUp=h.Evidence.setUp
 load=h.Evidence.load
 def result(self):
  self.assertIsNotNone(audit,'Recheck status evaluator missing');return audit(self.load(),at=h.AT)
 def issue(self):return self.result()['rechecks'][0]
 def test_pass_after_deployment_verifies_declared_url(self):
  r=self.issue();self.assertEqual(r['status'],'passed');self.assertTrue(r['repair_verified']);self.assertEqual(r['issue_id'],h.ID)
 def test_no_deployment_cannot_claim_repair(self):
  self.plan['issues'][0]['deployment']=None;r=self.issue();self.assertEqual(r['status'],'inconclusive');self.assertFalse(r['repair_verified']);self.assertEqual(r['cases'][0]['current_status'],'passed')
 def test_unchanged_failure_is_failed_without_deployment(self):
  c=self.plan['issues'][0]['cases'][0];c['after']=[h.snapshot(self.root,'fail.json','2026-09-17T03:00:00Z',['BTCUSDT'])];self.plan['issues'][0]['deployment']=None;r=self.issue();self.assertEqual(r['status'],'failed');self.assertFalse(r['repair_verified'])
 def test_passed_single_sample_not_whole_template(self):
  self.plan['issues'][0]['scope_type']='template';r=self.issue();self.assertEqual(r['status'],'partial_pass');self.assertFalse(r['repair_verified'])
 def test_missing_after_inconclusive(self):
  self.plan['issues'][0]['cases'][0]['after']=[];self.assertEqual(self.issue()['status'],'inconclusive')
 def test_two_repetitions_only_one_capture_partial(self):
  self.plan['issues'][0]['cases'][0]['repetitions']=2;self.assertEqual(self.issue()['status'],'partial_pass')
 def test_two_distinct_passes(self):
  c=self.plan['issues'][0]['cases'][0];c['repetitions']=2;c['after'].append(h.snapshot(self.root,'second.json','2026-09-17T03:30:00Z',['EURCAD']));self.assertTrue(self.issue()['repair_verified'])
 def test_intermittent_failure_not_pass(self):
  c=self.plan['issues'][0]['cases'][0];c['after'].append(h.snapshot(self.root,'failed.json','2026-09-17T03:30:00Z',['BTCUSDT']));self.assertEqual(self.issue()['status'],'failed')
 def test_same_time_conflicting_capture_inconclusive(self):
  c=self.plan['issues'][0]['cases'][0];c['after'].append(h.snapshot(self.root,'conflict.json','2026-09-17T03:00:00Z',['BTCUSDT']));self.assertEqual(self.issue()['status'],'inconclusive')
 def test_after_before_deployment_not_pass(self):
  c=self.plan['issues'][0]['cases'][0];c['after']=[h.snapshot(self.root,'old.json','2026-09-17T01:00:00Z',['EURCAD'])];self.assertEqual(self.issue()['status'],'inconclusive')
 def test_original_capture_reused_not_new_check(self):
  c=self.plan['issues'][0]['cases'][0];c['after']=[c['baseline']];self.assertFalse(self.issue()['repair_verified'])
 def test_current_pass_without_reproduced_baseline_inconclusive(self):
  c=self.plan['issues'][0]['cases'][0];c['predicate']={'field':'title','op':'nonempty'};self.assertEqual(self.issue()['status'],'inconclusive')
 def test_missing_control_prevents_full_pass(self):
  c=copy.deepcopy(self.plan['issues'][0]['cases'][0]);c.update(id='mobile',role='control',baseline=None,after=[]);self.plan['issues'][0]['cases'].append(c);self.assertEqual(self.issue()['status'],'partial_pass')
 def test_template_unknown_explicit_gap(self):
  self.plan['issues'][0]['scope_type']='unknown';r=self.issue();self.assertEqual(r['status'],'partial_pass');self.assertIn('original_scope_not_fully_verified',r['gaps'])
 def test_unknown_environment_not_closable(self):
  r=self.load();c=r['issues'][0]['cases'][0];c['device']='UNKNOWN';self.assertIsNotNone(audit);o=audit(r,at=h.AT);self.assertFalse(o['rechecks'][0]['repair_verified'])
 def test_engine_not_inferred_from_public_pass(self):
  r=self.issue();self.assertFalse(r['engine_recovery_confirmed']);self.assertEqual(r['engine_state'],'requires_platform_recheck')
 def test_failed_capture_evidence_kept(self):
  c=self.plan['issues'][0]['cases'][0];c['after']=[h.snapshot(self.root,'fail.json','2026-09-17T03:00:00Z',['BTCUSDT'])];r=self.issue()['cases'][0];self.assertEqual(r['attempts'][0]['observed'],['BTCUSDT']);self.assertIn('sha256',r['attempts'][0]['source'])
 def test_no_source_report_means_no_fake_issue_update(self):
  self.plan['issues'][0]['source_report']['sha256']='0'*64;r=self.result();self.assertEqual(r['rechecks'],[]);self.assertFalse(r['coverage']['complete'])
 def test_source_state_never_modified(self):
  old=(self.root/'source.json').read_bytes();self.result();self.assertEqual((self.root/'source.json').read_bytes(),old)
 def test_control_failure_overrides_symptom_pass(self):
  c=copy.deepcopy(self.plan['issues'][0]['cases'][0]);c.update(id='control',role='control',baseline=None,predicate={'field':'title','op':'equals','expected':'Other'});self.plan['issues'][0]['cases'].append(c);self.assertEqual(self.issue()['status'],'failed')
