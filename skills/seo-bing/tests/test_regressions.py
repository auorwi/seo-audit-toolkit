"""Review regressions: incomplete UI fields and conflicting live modes stay visible."""
import unittest
from test_audit import indexed,public,live_test,data,AT,recommendation
from bing_audit.audit import audit
import test_evidence as evidence_helper
class Review(unittest.TestCase):
 def test_live_generic_failure_is_not_discarded_when_historical_index_passed(self):
  r=audit(data(indexed(indexed=True,fetch_state='SUCCESS',http_status=200),live_test(http_status=None),public()),at=AT)
  self.assertEqual(r['checks'][0]['comparison'],'engine_live_failure_public_http_success')
 def test_same_index_and_live_rule_merges_modes_independent_of_order(self):
  for values in [(indexed(http_status=403),live_test()),(live_test(),indexed(http_status=403))]:
   r=audit(data(*values),at=AT);self.assertEqual(len(r['findings']),1);self.assertEqual(r['findings'][0]['classification'],'mixed_platform_observation')
 def test_noindex_is_intent_review_not_automatic_defect(self):
  r=audit(data(recommendation('noindex',report='url_inspection')),at=AT);self.assertEqual(r['findings'][0]['classification'],'requires_intent_review')
class MissingStatus(unittest.TestCase):
 setUp=evidence_helper.Evidence.setUp;load=evidence_helper.Evidence.load
 def test_empty_index_fields_yield_gap_not_clean_snapshot(self):
  self.doc['inspection']['fields']={};d=self.load();self.assertEqual(len(d['observations']),1);self.assertIn('explicit_index_status_unavailable',d['observations'][0]['data']['gaps'])

class ActualUIRules(unittest.TestCase):
 def test_redirect_stub_http301_routes_to_routing_not_generic_success(self):
  r=audit(data(indexed(indexed=True,fetch_state='SUCCESS',http_status=301)),at=AT)
  self.assertEqual(len(r['findings']),1);self.assertEqual(r['findings'][0]['rule'],'redirect_301');self.assertEqual(r['findings'][0]['classification'],'requires_intent_review');self.assertEqual(r['referrals'][0]['owner_skill'],'004')
 def test_meta_description_length_advice_not_index_blocker(self):
  r=audit(data(recommendation('description_length_review')),at=AT)
  self.assertEqual(r['findings'][0]['classification'],'platform_recommendation');self.assertEqual(r['referrals'][0]['owner_skill'],'007');self.assertFalse(r['findings'][0]['index_blocking_proven'])
 def test_missing_meta_language_requires_real_html_lang_review(self):
  r=audit(data(recommendation('meta_language_missing')),at=AT)
  self.assertEqual(r['findings'][0]['classification'],'platform_recommendation');self.assertEqual(r['referrals'][0]['owner_skill'],'010')

if __name__=='__main__':unittest.main()
