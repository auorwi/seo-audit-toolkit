"""Additional review-discovered failure cases, written before their fixes."""
import unittest,sys,tempfile,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gsc_audit.contracts import analytics,inspection
from gsc_audit.audit import audit
from test_audit import api,live,data,ui,AT,URL
import test_evidence as evidence_tests
class Regression(unittest.TestCase):
    def test_date_dimension_windows_not_compared_by_literal_dates(self):
        from gsc_audit.performance import compare
        q={'dimensions':['date'],'startDate':'2026-09-01','endDate':'2026-09-07'};a=analytics(q,{});b=analytics({**q,'startDate':'2026-09-08','endDate':'2026-09-14'}, {})
        with self.assertRaises(ValueError):compare(a,b)
    def test_analytics_clicks_cannot_exceed_impressions(self):
        with self.assertRaises(ValueError):analytics({'startDate':'2026-09-01','endDate':'2026-09-07'},{'rows':[{'keys':[],'clicks':11,'impressions':10,'ctr':1,'position':2}]})
    def test_analytics_rows_more_than_requested_rejected(self):
        row={'keys':[],'clicks':0,'impressions':1,'ctr':0,'position':1}
        with self.assertRaises(ValueError):analytics({'startDate':'2026-09-01','endDate':'2026-09-07','rowLimit':1},{'rows':[row,row]})
    def test_datastate_case_insensitive_per_official_contract(self):
        r=analytics({'startDate':'2026-09-01','endDate':'2026-09-07','dataState':'FINAL'},{})
        self.assertFalse(r['may_include_incomplete_data'])
    def test_bad_index_url_backslash_rejected(self):
        from gsc_audit.contracts import belongs
        with self.assertRaises(ValueError):belongs('sc-domain:bingx.com','https://bingx.com\\@evil.org/')
    def test_ui_device_unknown_never_counts_as_inspection(self):
        r=audit(data(ui(),live()),at=AT);self.assertEqual(r['coverage']['declared_urls_inspected'],0)
    def test_googlecanonical_without_usercanonical_routes_review(self):
        r=audit(data(api(verdict='NEUTRAL',pageFetchState='SUCCESSFUL',googleCanonical='https://bingx.com/en/other'),live()),at=AT)
        self.assertTrue(any(f['rule']=='google_selected_other_url' for f in r['findings']));self.assertTrue(any(x['owner_skill']=='004' for x in r['referrals']))
    def test_api_captured_url_hash_fragment_preserved_only_for_proof_not_match(self):
        r=audit(data(api(URL+'#section'),live()),at=AT);self.assertEqual(r['coverage']['paired_variants'],1)
    def test_unknown_verdict_is_incomplete_comparison(self):
        r=audit(data(api(verdict='VERDICT_UNSPECIFIED',pageFetchState='SUCCESSFUL'),live()),at=AT);self.assertFalse(r['coverage']['declared_checks_complete']);self.assertIn('index_verdict_unavailable',str(r['gaps']))
    def test_finite_huge_search_metric_not_report_infinity(self):
        with self.assertRaises(ValueError):analytics({'startDate':'2026-09-01','endDate':'2026-09-07'},{'rows':[{'keys':[],'clicks':1e308,'impressions':1e308,'ctr':1,'position':1e308}]})
    def test_comparison_declared_but_missing_evidence_is_gap(self):
        x=data(api(),live());x['comparisons']=[{'before':'missing','after':'missing2'}];r=audit(x,at=AT);self.assertIn('performance_comparison_missing_evidence',str(r['gaps']));self.assertEqual(r['performance_comparisons'],[])
    def test_duplicate_browser_same_moment_different_status_is_conflict(self):
        a=live(status=404);a['id']='other';r=audit(data(api(),live(),a),at=AT);self.assertEqual(r['checks'][0]['comparison'],'conflicting_live_observations');self.assertEqual(r['coverage']['paired_variants'],0)

# Reuse a setup utility rather than inheriting all already-run tests.
class AdapterRegressions(unittest.TestCase):
    setUp=evidence_tests.Evidence.setUp;add=evidence_tests.Evidence.add;load=evidence_tests.Evidence.load;api=evidence_tests.Evidence.api;ui=evidence_tests.Evidence.ui
    def test_invalid_api_body_key_is_gap(self):
        a=self.api();a['response']={};self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_filter_context_cannot_be_omitted(self):
        a=self.ui();del a['filters'];self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_ui_total_cannot_be_smaller_than_distinct_examples(self):
        a=self.ui();a['reported_total']=0;a['total_quote']='0';self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_ui_source_declared_property_must_match_exact_token(self):
        a=self.ui();a['property_quote']='Property sc-domain:bingx.com';a['property']='sc-domain:uat.bingx.com';self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_duplicate_json_key_quarantined(self):
        self.add(self.api());p=self.root/'e1.json';p.write_bytes(b'{"kind":"inspection_api","kind":"fake"}');self.manifest['evidence'][0]['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();r=self.load();self.assertEqual(r['observations'],[]);self.assertIn('duplicate_json_key',str(r['gaps']))
    def test_comparison_ids_preserved(self):
        self.manifest['comparisons']=[{'before':'prior','after':'current'}];self.assertEqual(self.load().get('comparisons'),[{'before':'prior','after':'current'}])
if __name__=='__main__':unittest.main()
