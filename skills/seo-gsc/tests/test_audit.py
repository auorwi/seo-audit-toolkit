"""Catch false repair/index claims, inaccurate URL/device joins and lost history."""
import unittest,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:from gsc_audit.audit import audit
except ImportError:audit=None
from gsc_audit.contracts import inspection
from crawlability.ledger import record,history
AT='2026-09-17T00:00:00Z';URL='https://bingx.com/en';PROP='sc-domain:bingx.com'
def api(url=URL,**idx):
    return {'id':'gsc1','kind':'inspection_api','property':PROP,'captured_at':'2026-09-16T23:00:00Z','proof':{'sha256':'a'*64},'data':inspection({'siteUrl':PROP,'inspectionUrl':url},{'inspectionResult':{'indexStatusResult':{'verdict':'FAIL','pageFetchState':'SERVER_ERROR','crawledAs':'MOBILE','lastCrawlTime':'2026-09-01T00:00:00Z',**idx}}})}
def live(url=URL,**kw):
    return {'id':'http1','kind':'live_http','property':PROP,'captured_at':'2026-09-16T23:30:00Z','proof':{'sha256':'b'*64},'data':{'kind':'live_http','url':url,'final_url':url,'device':'MOBILE','status':200,**kw}}
def data(*obs):return {'property':PROP,'scope':[{'url':URL,'device':'MOBILE'}],'observations':list(obs),'gaps':[],'manifest_sha256':'c'*64}
def ui(report='page_indexing',rows=None,**kw):
    return {'id':'ui1','kind':'gsc_ui','property':PROP,'captured_at':'2026-09-16T23:00:00Z','proof':{'sha256':'d'*64},'data':{'kind':'ui_report','report':report,'report_date':'2026-09-04','filters':{},'count_unit':'pages','reported_total':44682,'observed_url_examples':1,'examples_exhaustive':False,'rows':rows if rows is not None else [{'url':URL,'device':'UNKNOWN','reason_key':'server_error','reason_label':'Server error (5xx)','quote':'Server error (5xx)'}],**kw}}
class Audit(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(audit,'Audit implementation missing')
    def run_audit(self,*obs):return audit(data(*obs),at=AT)
    def test_historical_5xx_current200_not_declared_fixed(self):
        r=self.run_audit(api(),live());self.assertEqual(r['checks'][0]['comparison'],'historical_error_not_reproduced');self.assertFalse(r['checks'][0]['google_fixed']);self.assertEqual(len(r['findings']),1);self.assertEqual(r['findings'][0]['classification'],'engine_observation')
    def test_historical_5xx_current503_reproduced_only_http(self):
        r=self.run_audit(api(),live(status=503));self.assertEqual(r['checks'][0]['comparison'],'failure_reproduced_at_http_layer');self.assertFalse(r['checks'][0]['googlebot_live_verified'])
    def test_403_not_assumed_site_broken(self):
        r=self.run_audit(api(),live(status=403));self.assertEqual(r['checks'][0]['comparison'],'current_access_limited')
    def test_429_not_assumed_site_broken(self):
        self.assertEqual(self.run_audit(api(),live(status=429))['checks'][0]['comparison'],'current_access_limited')
    def test_redirected200_not_matched_page_verified(self):
        r=self.run_audit(api(),live(final_url='https://bingx.com/ja/'));self.assertEqual(r['checks'][0]['comparison'],'different_landing_unverified')
    def test_different_url_query_not_joined(self):
        r=self.run_audit(api(),live(URL+'?pair=ETH'));self.assertEqual(r['checks'][0]['comparison'],'live_url_not_checked');self.assertEqual(r['coverage']['paired_variants'],0)
    def test_different_device_not_joined(self):
        r=self.run_audit(api(),live(device='DESKTOP'));self.assertEqual(r['checks'][0]['comparison'],'live_url_not_checked')
    def test_engine_wrong_device_kept_as_gap(self):
        r=self.run_audit(api(crawledAs='DESKTOP'),live());self.assertEqual(r['checks'][0]['comparison'],'engine_device_unmatched');self.assertEqual(r['coverage']['paired_variants'],0)
    def test_unknown_index_result_not_success(self):
        a=api();a['data']=inspection({'siteUrl':PROP,'inspectionUrl':URL},{'inspectionResult':{}});r=self.run_audit(a,live());self.assertEqual(r['checks'][0]['comparison'],'engine_device_unmatched');self.assertIn('index_status_unavailable',str(r['gaps']))
    def test_stale_live_does_not_count(self):
        l=live();l['captured_at']='2026-09-01T23:00:00Z';r=self.run_audit(api(),l);self.assertEqual(r['checks'][0]['comparison'],'live_url_not_checked')
    def test_neutral_exclusion_needs_intent_not_defect(self):
        r=self.run_audit(api(verdict='NEUTRAL',pageFetchState='SUCCESSFUL',indexingState='BLOCKED_BY_META_TAG'),live());self.assertEqual(r['findings'][0]['classification'],'requires_intent_review');self.assertEqual(r['referrals'][0]['owner_skill'],'003')
    def test_google_selected_canonical_is_not_declared_canonical(self):
        r=self.run_audit(api(verdict='NEUTRAL',pageFetchState='SUCCESSFUL',googleCanonical='https://bingx.com/en/other',userCanonical=URL),live());self.assertTrue(any(f['rule']=='google_canonical_disagreement' for f in r['findings']));self.assertTrue(any(f['owner_skill']=='004' for f in r['referrals']))
    def test_missing_googlecanonical_not_assumed_equal(self):
        r=self.run_audit(api(verdict='PASS',pageFetchState='SUCCESSFUL'),live());self.assertFalse(any(f['rule']=='google_canonical_disagreement' for f in r['findings']))
    def test_pass_does_not_prove_whole_site(self):
        r=self.run_audit(api(verdict='PASS',pageFetchState='SUCCESSFUL'),live());self.assertEqual(r['findings'],[]);self.assertFalse(r['coverage']['full_site_proven']);self.assertFalse(r['checks'][0]['google_fixed'])
    def test_ui_samples_not_expanded_into_fake_urls(self):
        r=self.run_audit(ui());self.assertEqual(len(r['findings']),1);self.assertEqual(len(r['checks']),1);self.assertEqual(r['coverage']['declared_variants'],1);self.assertFalse(r['coverage']['all_reported_urls_verified'])
    def test_item_counts_never_sum_to_pages(self):
        r=self.run_audit(ui(report='rich_results',count_unit='items',reported_total=512));self.assertIsNone(r['coverage']['affected_page_total']);self.assertEqual(r['platform_reports'][0]['count_unit'],'items')
    def test_cwv_group_report_routes011_not_lighthouse_pass(self):
        r=self.run_audit(ui(report='cwv',count_unit='groups',rows=[{'url':URL,'device':'MOBILE','reason_key':'poor_lcp','reason_label':'Poor LCP','quote':'Poor LCP'}]));self.assertEqual(r['referrals'][0]['owner_skill'],'011');self.assertFalse(r['coverage']['cwv_live_verified'])
    def test_live_test_never_becomes_index_snapshot(self):
        r=self.run_audit(ui(report='live_test',kind='live_test',rows=[{'url':URL,'device':'MOBILE','reason_key':'available','reason_label':'URL available','quote':'URL available'}]),live());self.assertEqual(r['coverage']['indexed_url_observations'],0);self.assertEqual(r['checks'][0]['comparison'],'platform_url_not_inspected')
    def test_validation_pass_does_not_close(self):
        r=self.run_audit(ui(rows=[{'url':URL,'device':'UNKNOWN','reason_key':'validation_passed','reason_label':'Passed','quote':'Passed'}]));self.assertFalse(r['checks'][0]['google_fixed']);self.assertTrue(all(f['classification']!='resolved' for f in r['findings']))
    def test_api_and_ui_same_url_reason_deduplicated(self):
        r=self.run_audit(api(),ui(),live());self.assertEqual(len(r['findings']),1);self.assertEqual(len(r['findings'][0]['evidence']),2)
    def test_different_lastcrawl_same_issueid(self):
        a=self.run_audit(api());b=self.run_audit(api(lastCrawlTime='2026-09-05T00:00:00Z'));self.assertEqual(a['findings'][0]['issue_id'],b['findings'][0]['issue_id'])
    def test_conflicting_same_time_inspections_not_arbitrarily_selected(self):
        b=api(verdict='PASS',pageFetchState='SUCCESSFUL');b['id']='gsc2';b['proof']['sha256']='e'*64;r=self.run_audit(api(),b,live());self.assertEqual(r['checks'][0]['comparison'],'conflicting_engine_snapshots')
    def test_latest_live_selected_not_list_order(self):
        old=live(status=503);old['id']='old';old['captured_at']='2026-09-16T22:00:00Z';r=self.run_audit(api(),live(),old);self.assertEqual(r['checks'][0]['comparison'],'historical_error_not_reproduced')
    def test_no_data_reports_missing_not_pass(self):
        r=self.run_audit();self.assertEqual(r['checks'][0]['comparison'],'platform_url_not_inspected');self.assertFalse(r['coverage']['declared_checks_complete'])
    def test_ledger_replay_and_absence_keeps_open(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'issues.db';r=self.run_audit(api(),live());record(p,r);record(p,r);h=history(p);self.assertEqual(len(h),1);self.assertEqual(h[0]['sightings'],1)
            absent=self.run_audit(api(verdict='PASS',pageFetchState='SUCCESSFUL'));absent['at']='2026-09-18T00:00:00Z';record(p,absent);self.assertEqual(history(p)[0]['status'],'open')
if __name__=='__main__':unittest.main()
