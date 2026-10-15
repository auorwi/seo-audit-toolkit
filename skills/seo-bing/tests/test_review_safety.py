"""Final boundary review: credential URLs, partial timestamps and conflicting device observations."""
import unittest,json,hashlib
import test_evidence as h
from test_audit import data,indexed,public,live_test,AT
from bing_audit.audit import audit
class BindingReview(unittest.TestCase):
 setUp=h.Evidence.setUp;load=h.Evidence.load
 def test_source_url_userinfo_rejected(self):
  self.doc['source']['url']=self.doc['source']['url'].replace('https://www.','https://user:pass@www.');self.assertEqual(self.load()['observations'],[])
 def test_false_http_status_cannot_arrive_from_head(self):
  self.doc={'kind':'live_http','site':h.SITE,'captured_at':'2026-09-17T01:00:00Z','url':h.URL,'final_url':h.URL,'device':'UNKNOWN','status':200,'method':'HEAD','source_description':'controlled fixture','source':{'path':'ui.txt'}};self.assertEqual(self.load()['observations'],[])
 def test_site_scan_two_conflicting_completion_times_rejected(self):
  self.doc['report']='site_scan';self.doc.pop('inspection');self.raw+='\n2026-09-16\n';self.doc['scan']={'id':'x','completed_date':'2026-09-16','completed_at':'2026-02-01T00:00:00Z','quote':'2026-09-16'};self.assertEqual(self.load()['observations'],[])
class ObservationReview(unittest.TestCase):
 def test_live_reports_other_url_do_not_influence_this_check(self):
  b=live_test();b['data']['inspection']['url']+='?x=1';r=audit(data(indexed(),public(),b),at=AT);self.assertEqual(r['checks'][0]['comparison'],'historical_generic_failure_not_reproduced');self.assertEqual(r['checks'][0]['engine_live_evidence'],[])
 def test_conflicting_live_reports_block_silent_choice(self):
  b=live_test(fetch_state='SUCCESS',http_status=200);b['id']='another';r=audit(data(indexed(),public(),live_test(),b),at=AT);self.assertEqual(r['checks'][0]['comparison'],'conflicting_engine_live_observations')

class NumberBinding(unittest.TestCase):
 setUp=h.Evidence.setUp;load=h.Evidence.load
 def test_count_quote_cannot_be_substring_of_another_number(self):
  self.doc.update(reported_total=3,total_quote='3',count_unit='pages');self.assertEqual(self.load()['observations'],[])

if __name__=='__main__':unittest.main()
