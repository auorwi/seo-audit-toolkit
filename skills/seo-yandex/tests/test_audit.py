import sys,unittest,copy,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:from yandex_audit.audit import audit
except ImportError:audit=None
AT='2026-09-17T03:00:00Z';HOST='https:bingx.com:443';URL='https://bingx.com/en?a=1'
def row(**kwargs):return {'url':URL,'device':'DESKTOP','js':'DISABLED','searchable':False,'http_status':500,'reason':'HTTP_ERROR',**kwargs}
def ev(id,report,r,mode='engine_snapshot',at=AT):return {'id':id,'host_id':HOST,'captured_at':at,'kind':'yandex_ui','report':report,'mode':mode,'rows':[r],'source':{'path':id+'.txt','sha256':'a'*64},'gaps':[],'database_date':'2026-09-16'}
def data(*evs):return {'host_id':HOST,'run_kind':'controlled_fixture','scope':[{'url':URL,'device':'DESKTOP','js':'DISABLED'}],'evidence':list(evs),'gaps':[]}
def http(**kw):return ev('http','http',row(http_status=200,searchable=None,reason=None,final_url=URL,**kw),'ordinary_http')
class Audit(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(audit,'Yandex audit missing')
 def run_audit(self,*evs,inputs=None):return audit(inputs or data(*evs),at=AT)
 def check(self,*evs):return self.run_audit(*evs)['checks'][0]
 def test_historical_500_current_200_not_fixed(self):
  r=self.check(ev('db','database',row()),http());self.assertEqual(r['comparison'],'historical_http_failure_not_reproduced');self.assertFalse(r['engine_recovery_confirmed'])
 def test_live_200_not_index_snapshot(self):
  r=self.check(ev('live','page_check',row(searchable=True,http_status=200),'engine_live'),http());self.assertEqual(r['comparison'],'index_snapshot_unavailable');self.assertIsNone(r['searchable'])
 def test_js_modes_never_join(self):
  r=self.check(ev('db','database',row(js='ENABLED')),http());self.assertEqual(r['comparison'],'index_snapshot_unavailable')
 def test_device_modes_never_join(self):
  r=self.check(ev('db','database',row(device='MOBILE')),http());self.assertEqual(r['comparison'],'index_snapshot_unavailable')
 def test_query_variants_never_join(self):
  r=self.check(ev('db','database',row(url=URL+'&b=2')),http());self.assertEqual(r['comparison'],'index_snapshot_unavailable')
 def test_redirect_target_needs_review(self):
  h=http();h['rows'][0]['final_url']='https://bingx.com/en/';r=self.check(ev('db','database',row()),h);self.assertEqual(r['comparison'],'different_landing_unverified')
 def test_exact_error_reproduced(self):
  h=http();h['rows'][0]['http_status']=500;r=self.check(ev('db','database',row()),h);self.assertEqual(r['comparison'],'http_failure_reproduced')
 def test_engine_current_403_public_200(self):
  r=self.check(ev('db','database',row()),ev('live','page_check',row(http_status=403),'engine_live'),http());self.assertEqual(r['comparison'],'engine_live_failed_public_http_success')
 def test_engine_and_public_403(self):
  h=http();h['rows'][0]['http_status']=403;r=self.check(ev('db','database',row()),ev('live','page_check',row(http_status=403),'engine_live'),h);self.assertEqual(r['comparison'],'engine_and_public_access_limited')
 def test_indexed_with_recommendations(self):
  r=self.run_audit(ev('db','database',row(searchable=True,http_status=200,reason=None)),ev('diag','diagnostics',row(url=None,reason='NO_METRIKA_COUNTER',severity='RECOMMENDATION',state='PRESENT')),http());self.assertTrue(r['checks'][0]['searchable']);f=r['findings'][0];self.assertEqual(f['classification'],'platform_recommendation');self.assertFalse(f['confirmed_index_block'])
 def test_absent_diag_not_findings(self):
  r=self.run_audit(ev('diag','diagnostics',row(url=None,state='ABSENT',reason='DNS_ERROR')));self.assertEqual(r['findings'],[])
 def test_undefined_diag_is_gap(self):
  r=self.run_audit(ev('diag','diagnostics',row(url=None,state='UNDEFINED',reason='DNS_ERROR')));self.assertEqual(r['findings'],[]);self.assertTrue(r['gaps'])
 def test_low_quality_no_auto_delete_recommendation(self):
  f=self.run_audit(ev('db','database',row(reason='LOW_QUALITY',http_status=200)),http())['findings'][0];self.assertEqual(f['owner_skill'],'012');self.assertTrue(f['intent_review_required']);self.assertFalse(f['verified_site_defect'])
 def test_clean_params_routes_to_crawlability(self):
  f=self.run_audit(ev('db','database',row(reason='CLEAN_PARAMS')),http())['findings'][0];self.assertEqual(f['owner_skill'],'003');self.assertTrue(f['intent_review_required'])
 def test_duplicate_metadata_does_not_merge_different_groups(self):
  a=ev('a','duplicates',row(reason='DUPLICATE_TITLE',group_id='groupA'));b=ev('b','duplicates',row(reason='DUPLICATE_TITLE',group_id='groupB'));self.assertEqual(len(self.run_audit(a,b)['findings']),2)
 def test_same_issue_across_reports_one_id(self):
  a=ev('a','database',row(reason='NO_INDEX'));b=ev('b','excluded',row(reason='NO_INDEX'));r=self.run_audit(a,b);self.assertEqual(len(r['findings']),1);self.assertEqual(len(r['findings'][0]['evidence']),2)
 def test_sample_absence_does_not_close_issue(self):
  from crawlability.ledger import record,history
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.db';r=self.run_audit(ev('a','database',row()));record(p,r);record(p,self.run_audit(http()));self.assertEqual(history(p)[0]['status'],'open')
 def test_replay_idempotent(self):
  from crawlability.ledger import record,history
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.db';r=self.run_audit(ev('a','database',row()));record(p,r);record(p,r);self.assertEqual(history(p)[0]['sightings'],1)
 def test_latest_capture_selected(self):
  r=self.check(ev('old','database',row(),at='2026-09-17T02:00:00Z'),ev('new','database',row(searchable=True,http_status=200,reason=None)),http());self.assertTrue(r['searchable']);self.assertEqual(r['engine_evidence'],['new'])
 def test_same_time_conflict_not_choose_arbitrarily(self):
  r=self.check(ev('a','database',row()),ev('b','database',row(searchable=True)),http());self.assertEqual(r['comparison'],'conflicting_index_snapshots')
 def test_crawl_samples_no_search_status(self):
  r=self.check(ev('a','indexing/samples',row(http_status=200,searchable=None)),http());self.assertEqual(r['comparison'],'index_snapshot_unavailable')
 def test_live_capture_old_not_current(self):
  r=self.run_audit(ev('a','database',row(),at='2026-09-01T00:00:00Z'),http());self.assertEqual(r['coverage']['paired_variants'],0)
 def test_full_scope_pairs_not_all_site(self):
  r=self.run_audit(ev('db','database',row()),http());self.assertTrue(r['coverage']['declared_checks_complete']);self.assertFalse(r['coverage']['all_site_verified'])
 def test_unchecked_report_urls_counted(self):
  r=self.run_audit(ev('a','excluded',row(url=URL+'&other=1')));self.assertEqual(r['coverage']['unselected_observed_urls'],1)
 def test_missing_http_gap(self):self.assertEqual(self.check(ev('db','database',row()))['comparison'],'current_http_unavailable')
 def test_unknown_reason_needs_review(self):
  f=self.run_audit(ev('a','excluded',row(reason='NEW_REASON')))['findings'][0];self.assertEqual(f['classification'],'unmapped_platform_observation');self.assertEqual(f['owner_skill'],'016')
