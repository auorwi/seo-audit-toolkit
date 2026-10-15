import unittest,json,hashlib
import test_evidence as h
from recheck.audit import audit
class Regressions(unittest.TestCase):
 setUp=h.Evidence.setUp
 load=h.Evidence.load
 def test_same_timestamp_two_payloads_not_two_repetitions(self):
  c=self.plan['issues'][0]['cases'][0];c['repetitions']=2;x=h.snapshot(self.root,'another.json','2026-09-17T03:00:00Z',['EURCAD']);p=self.root/'another.json';v=json.loads(p.read_text());v['extra']='different unrelated value';x['source']=h.save(self.root,'another.json',v);c['after'].append(x);r=audit(self.load(),at=h.AT)['rechecks'][0];self.assertFalse(r['repair_verified']);self.assertEqual(r['status'],'partial_pass')
 def test_report_level_issue_not_closed_as_one_url(self):
  p=self.root/'source.json';v=json.loads(p.read_text());v['findings'][0]['url']=None;self.plan['issues'][0]['source_report']=h.save(self.root,'source.json',v);self.assertEqual(self.load()['issues'],[])

 def test_old_open_tab_cannot_prove_deployed_fix(self):
  c=self.plan['issues'][0]['cases'][0];v=json.loads((self.root/'after.json').read_text());v.pop('navigation_at');c['after'][0]['source']=h.save(self.root,'after.json',v);r=audit(self.load(),at=h.AT)['rechecks'][0];self.assertFalse(r['repair_verified']);self.assertEqual(r['status'],'inconclusive')
 def test_navigation_before_deployment_not_repair(self):
  c=self.plan['issues'][0]['cases'][0];v=json.loads((self.root/'after.json').read_text());v['navigation_at']='2026-09-17T01:00:00Z';c['after'][0]['source']=h.save(self.root,'after.json',v);r=audit(self.load(),at=h.AT)['rechecks'][0];self.assertFalse(r['repair_verified'])
