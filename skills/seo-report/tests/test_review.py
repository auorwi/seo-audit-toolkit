import copy, pathlib, sys, unittest
import test_core as c
import test_delivery as d
import test_publish as p
class ReviewTests(unittest.TestCase):
 def setUp(self):c.CoreTests.setUp(self)
 source=c.CoreTests.source;load=c.CoreTests.load;build=c.CoreTests.build
 def test_transaction_rolls_back_late_conflict(self):
  self.source();self.build();before=(self.root/'state/ledger.sqlite').read_bytes();self.report['findings'][0]['rule']='collision';self.man['sources']=[];self.source()
  with self.assertRaises(ValueError):self.build()
  self.assertEqual(before,(self.root/'state/ledger.sqlite').read_bytes())
 def test_017_same_time_conflict(self):
  self.source();c.CoreTests.add_recheck(self);r={'skill_id':'017','at':'2026-09-17T03:45:00Z','rechecks':[{'issue_id':'same','rule':'entity','original_url':'https://bingx.com/en/x?a=1','status':'passed','repair_verified':True}]};self.source(r,'recheck2.json','017')
  with self.assertRaises(ValueError):self.build()
 def test_raw_credentials_in_url_userinfo(self):
  self.report['findings'][0]['url']='https://user:secret@bingx.com/en';self.source()
  with self.assertRaises(ValueError):self.load()
class RenderReviewTests(unittest.TestCase):
 setUp=d.DeliveryTests.setUp
 def test_large_gap_list_is_bounded_but_count_visible(self):
  self.report['sources'][0]['gaps']=[{'reason':'x'*500}]*1000
  doc=d.delivery.documents(self.report)['report'];self.assertLess(len(str(doc)),15000);self.assertIn('1000',str(doc));self.assertIn('截断',str(doc))
 def test_problem_evidence_has_observed_quote(self):
  doc=d.delivery.documents(self.report)['ledger'];self.assertIn('actual',str(doc))
class PublishReviewTests(unittest.TestCase):
 setUp=p.PublishTests.setUp;runpub=p.PublishTests.runpub
 def test_link_target_is_part_of_readback(self):
  self.doc['sections'][0]['xml']='<p><a href="https://bingx.com/en">link</a></p>';url=self.runpub();self.remote.docs[url]=self.remote.docs[url].replace('https://bingx.com/en','https://bingx.com/ru')
  with self.assertRaises(ValueError):self.runpub()
 def test_link_entry_keeps_previous_run(self):
  self.runpub();self.doc['sections']=[{'key':'group-b','xml':'<p>second</p>'}];url=self.runpub();self.assertIn('original',self.remote.docs[url]);self.assertIn('second',self.remote.docs[url])
class ReportFocusTests(unittest.TestCase):
 setUp=d.DeliveryTests.setUp
 def test_failed_rechecks_have_fix_direction_in_summary(self):
  doc=d.delivery.documents(self.report)['report'];self.assertIn('&lt;check&gt;',str(doc));self.assertIn('重点复查',str(doc))
class MutationGapTests(unittest.TestCase):
 setUp=c.CoreTests.setUp;source=c.CoreTests.source;load=c.CoreTests.load;build=c.CoreTests.build
 def test_hash_tamper_otherwise_valid_report(self):
  self.source();r=copy.deepcopy(self.report);r['findings'][0]['evidence'][0]['quote']='different';(self.root/'a.json').write_text(c.json.dumps(r))
  with self.assertRaises(ValueError):self.load()
 def test_unknown_class_stays_review(self):
  self.source();self.assertEqual(self.build()['issues'][0]['category'],'review')
 def test_cross_date_url_collision(self):
  self.source();self.build();self.man['sources']=[];r=copy.deepcopy(self.report);r['at']='2026-09-17T03:30:00Z';r['findings'][0]['url']='https://bingx.com/en/y';self.source(r,'later.json')
  with self.assertRaises(ValueError):self.build()
class XmlRoundtripTests(unittest.TestCase):
 setUp=d.DeliveryTests.setUp
 def test_newlines_are_explicit_breaks(self):
  doc=d.delivery.documents(self.report)['ledger'];self.assertIn('<br',str(doc))
class PendingTests(unittest.TestCase):
 setUp=p.PublishTests.setUp;runpub=p.PublishTests.runpub
 def test_pending_replace_with_old_body_not_retried(self):
  url=self.runpub();original=self.remote.docs[url];self.doc['sections'][0]['xml']='<p>new</p>';self.remote.fail='replace'
  with self.assertRaises(TimeoutError):self.runpub()
  self.remote.docs[url]=original;n=self.remote.writes
  with self.assertRaises(ValueError):self.runpub()
  self.assertEqual(n,self.remote.writes)
class EvidenceAdapterTests(unittest.TestCase):
 setUp=d.DeliveryTests.setUp
 def test_link_occurrences_are_evidence(self):
  self.issue['finding']['evidence']=[];self.issue['finding']['link_occurrences']=[{'locator':'a[index=7]','snapshot_id':'real-dom'}]
  self.assertIn('real-dom',str(d.delivery.documents(self.report)['ledger']))
class MissingProofTests(unittest.TestCase):
 setUp=c.CoreTests.setUp;source=c.CoreTests.source;load=c.CoreTests.load;build=c.CoreTests.build
 def test_confirmation_without_any_evidence_is_gap(self):
  f=self.report['findings'][0];f['classification']='confirmed';f['evidence']=[];self.source();self.assertEqual(self.build()['issues'][0]['category'],'evidence_gap')
class PartialScopeTests(unittest.TestCase):
 setUp=c.CoreTests.setUp;source=c.CoreTests.source;load=c.CoreTests.load;build=c.CoreTests.build
 def test_single_skill_requested_does_not_mark_others_missing(self):
  self.source();self.man['requested_skills']=['016'];self.assertEqual(self.build()['missing_skills'],[])
 def test_requested_missing_platform_is_visible(self):
  self.source();self.man['requested_skills']=['015','016'];self.assertEqual(self.build()['missing_skills'],['015'])
 def test_unknown_requested_skill_rejected(self):
  self.source();self.man['requested_skills']=['999']
  with self.assertRaises(ValueError):self.load()
 def test_empty_requested_scope_rejected(self):
  self.source();self.man['requested_skills']=[]
  with self.assertRaises(ValueError):self.load()
