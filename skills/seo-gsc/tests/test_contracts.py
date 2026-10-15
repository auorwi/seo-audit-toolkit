"""Breaks caught: cross-property mixing, false current/indexed claims, invalid metrics."""
import unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try: from gsc_audit import contracts as c
except ImportError: c=None

class Contracts(unittest.TestCase):
    def setUp(self): self.assertIsNotNone(c,'GSC contract implementation missing')
    def test_domain_property_includes_subdomains_and_protocols(self):
        for u in ['https://bingx.com/en','http://uat.bingx.com/x','https://a.b.bingx.com/x']:
            with self.subTest(u=u): self.assertTrue(c.belongs('sc-domain:bingx.com',u))
    def test_domain_boundary_rejects_other_hosts(self):
        for u in ['https://bingx.com.evil.org/x','https://notbingx.com/x','https://other.com/?bingx.com']:
            with self.subTest(u=u): self.assertFalse(c.belongs('sc-domain:bingx.com',u))
    def test_prefix_keeps_protocol_port_and_path_case(self):
        for u,want in [('https://bingx.com/en/x',True),('https://bingx.com/english/x',False),('http://bingx.com/en/x',False),('https://bingx.com/EN/x',False),('https://bingx.com:444/en/x',False)]:
            with self.subTest(u=u): self.assertEqual(c.belongs('https://bingx.com/en/',u),want)
    def test_non_bingx_properties_rejected(self):
        for p in ['sc-domain:example.com','sc-domain:bingx.com/path','https://example.com/','https://user@bingx.com/','https://bingx.com/#x','https://bingx.com/?x=1','https://bingx.com/en']:
            with self.subTest(p=p),self.assertRaises(ValueError): c.property_id(p)
    def test_url_identity_keeps_query_and_case(self):
        self.assertEqual(c.url_id('https://BINGX.com:443/en/Trade?a=1&b=2#x'),'https://bingx.com/en/Trade?a=1&b=2')
    def test_inspection_success_is_index_snapshot_not_live(self):
        r=c.inspection({'siteUrl':'sc-domain:bingx.com','inspectionUrl':'https://bingx.com/en'}, {'inspectionResult':{'indexStatusResult':{'verdict':'PASS','pageFetchState':'SUCCESSFUL','lastCrawlTime':'2026-09-01T00:00:00Z','googleCanonical':'https://bingx.com/en'}}})
        self.assertEqual(r['index']['verdict'],'PASS');self.assertEqual(r['kind'],'indexed_snapshot');self.assertFalse(r['live_test']);self.assertEqual(r['index']['lastCrawlTime'],'2026-09-01T00:00:00Z')
    def test_absent_index_fields_are_unknown_not_success(self):
        r=c.inspection({'siteUrl':'sc-domain:bingx.com','inspectionUrl':'https://bingx.com/en'}, {'inspectionResult':{}})
        self.assertIsNone(r['index']['googleCanonical']);self.assertIsNone(r['index']['verdict']);self.assertIn('index_status_unavailable',r['gaps'])
    def test_absent_sitemap_is_not_proof_url_excluded(self):
        r=c.inspection({'siteUrl':'sc-domain:bingx.com','inspectionUrl':'https://bingx.com/en'}, {'inspectionResult':{'indexStatusResult':{'verdict':'PASS'}}})
        self.assertIsNone(r['index']['sitemap']);self.assertFalse(r['sitemap_list_exhaustive'])
    def test_unknown_enum_preserved_and_flagged(self):
        r=c.inspection({'siteUrl':'sc-domain:bingx.com','inspectionUrl':'https://bingx.com/en'}, {'inspectionResult':{'indexStatusResult':{'pageFetchState':'NEW_FUTURE_VALUE','coverageState':'被抓取了但还没有索引'}}})
        self.assertEqual(r['index']['pageFetchState'],'NEW_FUTURE_VALUE');self.assertEqual(r['index']['coverageState'],'被抓取了但还没有索引');self.assertIn('unknown_enum:pageFetchState',r['gaps'])
    def test_wrong_property_inspection_rejected(self):
        with self.assertRaises(ValueError):c.inspection({'siteUrl':'https://bingx.com/en/','inspectionUrl':'https://bingx.com/ja/'},{'inspectionResult':{}})
    def test_api_error_never_becomes_empty_pass(self):
        with self.assertRaises(ValueError): c.inspection({'siteUrl':'sc-domain:bingx.com','inspectionUrl':'https://bingx.com/en'},{'error':{'code':403}})
    def test_invalid_lastcrawl_rejected(self):
        with self.assertRaises(ValueError):c.inspection({'siteUrl':'sc-domain:bingx.com','inspectionUrl':'https://bingx.com/en'},{'inspectionResult':{'indexStatusResult':{'lastCrawlTime':'2026-09-01'}}})
    def test_rich_error_not_entire_page_index_failure(self):
        r=c.inspection({'siteUrl':'sc-domain:bingx.com','inspectionUrl':'https://bingx.com/en'}, {'inspectionResult':{'indexStatusResult':{'verdict':'PASS'},'richResultsResult':{'verdict':'FAIL','detectedItems':[{'richResultType':'Product','items':[{'name':'x','issues':[{'issueMessage':'price invalid','severity':'ERROR'}]}]}]}}})
        self.assertEqual(r['index']['verdict'],'PASS');self.assertEqual(r['rich_results']['verdict'],'FAIL')
    def test_mobile_usability_not_cwv(self):
        r=c.inspection({'siteUrl':'sc-domain:bingx.com','inspectionUrl':'https://bingx.com/en'}, {'inspectionResult':{'mobileUsabilityResult':{'verdict':'PASS'}}})
        self.assertIsNone(r['cwv']);self.assertTrue(r['deprecated_mobile_usability_present'])
    def test_invalid_index_types_rejected(self):
        for data in [{'sitemap':'https://bingx.com/sitemap.xml'},{'verdict':True},{'googleCanonical':12},{'referringUrls':[42]}]:
            with self.subTest(data=data),self.assertRaises(ValueError):c.inspection({'siteUrl':'sc-domain:bingx.com','inspectionUrl':'https://bingx.com/en'},{'inspectionResult':{'indexStatusResult':data}})
    def test_analytics_preserves_dimension_order_and_pt(self):
        r=c.analytics({'startDate':'2026-09-01','endDate':'2026-09-07','dimensions':['query','page']},{'rows':[{'keys':['btc','https://bingx.com/en'],'clicks':2,'impressions':20,'ctr':.1,'position':3}], 'responseAggregationType':'byPage'})
        self.assertEqual(r['rows'][0]['dimensions'],{'query':'btc','page':'https://bingx.com/en'});self.assertEqual(r['timezone'],'America/Los_Angeles');self.assertFalse(r['exhaustive']);self.assertFalse(r['indexing_evidence'])
    def test_zero_rows_do_not_mean_unindexed(self):
        r=c.analytics({'startDate':'2026-09-01','endDate':'2026-09-07'}, {})
        self.assertEqual(r['rows'],[]);self.assertFalse(r['indexing_evidence']);self.assertFalse(r['exhaustive'])
    def test_partial_dates_kept(self):
        r=c.analytics({'startDate':'2026-09-01','endDate':'2026-09-07','dataState':'all'}, {'metadata':{'first_incomplete_date':'2026-09-06'}})
        self.assertEqual(r['metadata']['first_incomplete_date'],'2026-09-06');self.assertTrue(r['may_include_incomplete_data'])
    def test_invalid_analytics_windows_and_paging_rejected(self):
        base={'startDate':'2026-09-01','endDate':'2026-09-07'}
        for patch in [{'endDate':'2026-08-01'},{'rowLimit':25001},{'rowLimit':True},{'startRow':-1},{'startDate':'2026-02-30'},{'dimensions':['page','page']},{'dimensions':['madeup']},{'dataState':'fake'},{'type':'fake'}]:
            with self.subTest(patch=patch),self.assertRaises(ValueError): c.analytics({**base,**patch},{})
    def test_page_property_aggregation_rejected(self):
        with self.assertRaises(ValueError):c.analytics({'startDate':'2026-09-01','endDate':'2026-09-07','dimensions':['page'],'aggregationType':'byProperty'}, {})
    def test_bad_metrics_and_key_count_rejected(self):
        req={'startDate':'2026-09-01','endDate':'2026-09-07','dimensions':['page']}
        row={'keys':['https://bingx.com/en'],'clicks':1,'impressions':10,'ctr':.1,'position':2}
        for patch in [{'keys':[]},{'clicks':-1},{'clicks':True},{'impressions':float('nan')},{'ctr':1.1},{'position':-1},{'keys':[4]}]:
            with self.subTest(patch=patch),self.assertRaises(ValueError):c.analytics(req,{'rows':[{**row,**patch}]})
    def test_sitemap_deprecated_indexed_not_coverage(self):
        r=c.sitemaps({'sitemap':[{'path':'https://bingx.com/en/sitemap.xml','errors':'2','warnings':'1','isPending':False,'contents':[{'type':'web','submitted':'100','indexed':'100'}]}]})
        self.assertEqual(r['entries'][0]['errors'],2);self.assertEqual(r['entries'][0]['contents'][0]['submitted'],100);self.assertNotIn('indexed',r['entries'][0]['contents'][0]);self.assertIn('deprecated_indexed_ignored',r['gaps']);self.assertFalse(r['full_site_inventory'])
    def test_sitemap_invalid_counts_rejected(self):
        for n in [True,-1,'2.5','-2']:
            with self.subTest(n=n),self.assertRaises(ValueError):c.sitemaps({'sitemap':[{'path':'https://bingx.com/s.xml','errors':n}]})
    def test_sitemap_empty_is_not_full_site_clean(self):
        r=c.sitemaps({});self.assertEqual(r['entries'],[]);self.assertFalse(r['full_site_inventory'])

if __name__=='__main__':unittest.main()
