"""Cross-client comparisons, Bing advice vs blocking, deduplication and history regressions."""
import unittest,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:from bing_audit.audit import audit
except ImportError:audit=None
from bing_audit.contracts import api
from crawlability.ledger import record,history
AT='2026-09-17T03:00:00Z';SITE='https://bingx.com/';URL=SITE+'en/example'
def obs(id,kind,d,time='2026-09-17T02:00:00Z'):return {'id':id,'kind':kind,'site':SITE,'captured_at':time,'proof':{'sha256':'a'*64,'path':id+'.json'},'data':d}
def indexed(**kw):return obs('index','bing_ui',{'kind':'ui_report','report':'url_inspection','rows':[],'inspection':{'url':URL,'device':'UNKNOWN','mode':'index','indexed':False,'fetch_state':'FAILED','http_status':None,'last_crawled':None,**kw},'gaps':[]})
def public(**kw):return obs('http','live_http',{'kind':'live_http','url':URL,'final_url':URL,'device':'UNKNOWN','status':200,**kw})
def live_test(**kw):return obs('live','bing_ui',{'kind':'ui_report','report':'live_url','rows':[],'inspection':{'url':URL,'device':'UNKNOWN','mode':'live','indexed':None,'fetch_state':'FAILED','http_status':403,**kw},'gaps':[]})
def recommendation(rule='title_too_long',report='recommendations',**kw):return obs('advice','bing_ui',{'kind':'ui_report','report':report,'rows':[{'url':URL,'device':'UNKNOWN','reason_key':rule,'reason_label':'Title too long','quote':'Title too long','severity':'High'}],'inspection':None,'gaps':[],**kw})
def data(*observations):return {'site':SITE,'scope':[{'url':URL,'device':'UNKNOWN'}],'observations':list(observations),'gaps':[],'run_kind':'audit','manifest_sha256':'b'*64}
class Audit(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(audit,'Bing audit not implemented')
 def run_audit(self,*obs):return audit(data(*obs),at=AT)
 def test_generic_historical_failure_not_called_5xx(self):
  r=self.run_audit(indexed(),public());self.assertEqual(r['checks'][0]['comparison'],'historical_generic_failure_not_reproduced');self.assertNotIn('server_error',{f['rule'] for f in r['findings']});self.assertFalse(r['checks'][0]['bing_fixed'])
 def test_known_5xx_current_503_reproduced_http_only(self):
  r=self.run_audit(indexed(http_status=503),public(status=503));self.assertEqual(r['checks'][0]['comparison'],'failure_reproduced_at_http_layer');self.assertFalse(r['checks'][0]['bingbot_live_verified'])
 def test_historical_503_current200_not_fixed(self):self.assertEqual(self.run_audit(indexed(http_status=503),public())['checks'][0]['comparison'],'historical_error_not_reproduced')
 def test_bing_live403_public200_discrepancy_preserved(self):
  r=self.run_audit(indexed(),live_test(),public());c=r['checks'][0];self.assertEqual(c['comparison'],'engine_live_failure_public_http_success');self.assertEqual(c['engine_live_http_status'],403);self.assertFalse(c['bing_fixed'])
 def test_bing_and_public403_not_global_site_failure(self):self.assertEqual(self.run_audit(indexed(),live_test(),public(status=403))['checks'][0]['comparison'],'engine_and_public_access_limited')
 def test_public429_is_collection_limit(self):self.assertEqual(self.run_audit(indexed(),public(status=429))['checks'][0]['comparison'],'current_access_limited')
 def test_different_landing_not_passed(self):self.assertEqual(self.run_audit(indexed(),public(final_url=SITE+'ja/'))['checks'][0]['comparison'],'different_landing_unverified')
 def test_query_variant_not_joined(self):self.assertEqual(self.run_audit(indexed(),public(url=URL+'?pair=ETH'))['coverage']['paired_variants'],0)
 def test_device_mismatch_not_joined(self):self.assertEqual(self.run_audit(indexed(),public(device='MOBILE'))['coverage']['paired_variants'],0)
 def test_unknown_device_not_claimed_same_physical_device(self):self.assertEqual(self.run_audit(indexed(),public())['checks'][0]['client_comparability'],'unproven')
 def test_live_success_not_indexed_snapshot(self):
  r=self.run_audit(live_test(fetch_state='SUCCESS',http_status=200),public());self.assertEqual(r['coverage']['index_snapshots'],0);self.assertFalse(r['coverage']['declared_checks_complete'])
 def test_api_ispage_cannot_close_ui_not_indexed(self):
  a=obs('api','bing_api',api('GetUrlInfo',{'siteUrl':SITE,'url':URL},{'d':{'Url':URL,'IsPage':True,'HttpStatus':200}},captured_at=AT));r=self.run_audit(indexed(),a,public());self.assertFalse(r['checks'][0]['bing_fixed']);self.assertTrue(r['findings'])
 def test_ui_indexed_and_http200_not_whole_site_pass(self):
  r=self.run_audit(indexed(indexed=True,fetch_state='SUCCESS',http_status=200),public());self.assertEqual(r['findings'],[]);self.assertFalse(r['coverage']['full_site_proven'])
 def test_title_length_high_severity_is_advice_not_index_blocker(self):
  r=self.run_audit(recommendation());f=r['findings'][0];self.assertEqual(f['classification'],'platform_recommendation');self.assertFalse(f['index_blocking_proven']);self.assertFalse(f['underlying_defect_confirmed']);self.assertEqual(r['referrals'][0]['owner_skill'],'007')
 def test_indexnow_not_used_never_auto_submission_or_index_defect(self):
  r=self.run_audit(recommendation('indexnow_not_submitted'));self.assertEqual(r['findings'][0]['classification'],'platform_recommendation');self.assertFalse(r['findings'][0]['index_blocking_proven'])
 def test_submission_accepted_is_not_successful_index(self):
  r=self.run_audit(recommendation('submission_accepted',report='submission'),public());self.assertEqual(r['coverage']['index_snapshots'],0);self.assertEqual(r['findings'],[])
 def test_generic_unknown_recommendation_retained_for_review(self):
  r=self.run_audit(recommendation('future_rule'));self.assertEqual(len(r['findings']),1);self.assertEqual(r['findings'][0]['classification'],'requires_review')
 def test_old_scan_not_treated_as_new_crawl(self):
  r=self.run_audit(recommendation(report='site_scan',scan={'id':'February','completed_date':'2026-02-12'},gaps=['historical_site_scan_not_current_live_capture']),public());self.assertEqual(r['coverage']['index_snapshots'],0);self.assertTrue(r['gaps']);self.assertIn('historical_scan_observation',r['findings'][0]['observation_modes'])
 def test_same_url_rule_across_reports_one_issue(self):
  a=recommendation(report='site_scan');a['id']='scan';r=self.run_audit(a,recommendation());self.assertEqual(len(r['findings']),1);self.assertEqual(len(r['findings'][0]['evidence']),2);self.assertEqual(len(r['referrals']),1)
 def test_counts_never_summed_as_affected_pages(self):
  r=self.run_audit(recommendation(reported_total=48003,count_unit='occurrences'));self.assertIsNone(r['coverage']['affected_page_total']);self.assertFalse(r['coverage']['all_reported_urls_verified'])
 def test_stale_live_does_not_rescue_failure(self):
  p=public();p['captured_at']='2026-09-01T00:00:00Z';self.assertEqual(self.run_audit(indexed(),p)['coverage']['paired_variants'],0)
 def test_latest_conflicting_snapshots_not_arbitrary(self):
  a=indexed(indexed=True,fetch_state='SUCCESS');a['id']='second';r=self.run_audit(indexed(),a,public());self.assertEqual(r['checks'][0]['comparison'],'conflicting_index_snapshots')
 def test_future_observation_is_gap(self):
  p=public();p['captured_at']='2027-01-01T00:00:00Z';self.assertEqual(self.run_audit(indexed(),p)['coverage']['paired_variants'],0)
 def test_historical_api_crawl_flags_generate_precise_owner(self):
  d=api('GetCrawlIssues',{'siteUrl':SITE},{'d':[{'Url':URL,'HttpCode':0,'Issues':16}]},captured_at=AT);r=self.run_audit(obs('crawl','bing_api',d));self.assertEqual(r['findings'][0]['rule'],'robots_blocked');self.assertEqual(r['referrals'][0]['owner_skill'],'003')
 def test_same_evidence_replay_deduplicated_and_absence_not_close(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'state.db';r=self.run_audit(indexed(),public());record(p,r);record(p,r);h=history(p);self.assertTrue(h);self.assertTrue(all(x['sightings']==1 for x in h))
   r2=self.run_audit(indexed(indexed=True,fetch_state='SUCCESS',http_status=200),public());r2['at']='2026-09-18T03:00:00Z';record(p,r2);self.assertTrue(all(x['status']=='open' for x in history(p)))
 def test_controlled_fixture_ids_do_not_pollute_real_issue_ids(self):
  a=data(indexed());r=audit(a,at=AT);a['run_kind']='controlled_fixture';f=audit(a,at=AT);self.assertNotEqual(r['findings'][0]['issue_id'],f['findings'][0]['issue_id'])
if __name__=='__main__':unittest.main()
