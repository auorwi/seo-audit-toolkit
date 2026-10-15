import unittest
import test_evidence as h
class Freshness(unittest.TestCase):
 setUp=h.Evidence.setUp
 load=h.Evidence.load
 def test_capture_today_does_not_refresh_old_page_test(self):
  self.env['test_date']={'value':'2026-09-16','quote':'September 16, 2026','format':'%B %d, %Y'};r=self.load();self.assertEqual(r['mode'],'historical_test');self.assertIn('historical_engine_test',r['gaps'])
 def test_no_test_date_is_not_current_engine_check(self):
  self.assertEqual(self.load()['mode'],'undated_test')
 def test_bound_test_today_can_be_live_but_time_precision_disclosed(self):
  self.env['captured_at']='2026-09-16T23:00:00Z';self.env['test_date']={'value':'2026-09-16','quote':'September 16, 2026','format':'%B %d, %Y'};r=self.load();self.assertEqual(r['mode'],'engine_live');self.assertEqual(r.get('test_time_precision'),'local_calendar_day_timezone_unavailable')
 def test_literal_title_cannot_be_rewritten_in_evidence(self):
  self.env['rows'][0]['fields']['title']=h.binding('Different title','LOW_QUALITY')
  with self.assertRaises(ValueError):self.load()
