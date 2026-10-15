"""Catch tampered, stale, invented, cross-property and duplicate evidence."""
import unittest,sys,json,hashlib,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:from gsc_audit.adapters import load_manifest
except ImportError:load_manifest=None
AT='2026-09-17T00:00:00Z'
class Evidence(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(load_manifest,'Evidence adapter missing');self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.manifest={'schema_version':1,'property':'sc-domain:bingx.com','scope':[{'url':'https://bingx.com/en','device':'MOBILE'}],'evidence':[]}
    def add(self,obj,kind=None,id='e1'):
        b=json.dumps(obj).encode();p=self.root/(id+'.json');p.write_bytes(b)
        self.manifest['evidence'].append({'id':id,'kind':kind or obj['kind'],'path':p.name,'sha256':hashlib.sha256(b).hexdigest()});return p
    def load(self):
        p=self.root/'manifest.json';p.write_text(json.dumps(self.manifest));return load_manifest(p,at=AT,max_age_hours=24)
    def api(self):return {'kind':'inspection_api','property':'sc-domain:bingx.com','captured_at':'2026-09-16T23:00:00Z','http_status':200,'request':{'siteUrl':'sc-domain:bingx.com','inspectionUrl':'https://bingx.com/en'},'response':{'inspectionResult':{'indexStatusResult':{'verdict':'FAIL','pageFetchState':'SERVER_ERROR','crawledAs':'MOBILE','lastCrawlTime':'2026-09-01T00:00:00Z'}}}}
    def ui(self):
        raw='Property sc-domain:bingx.com\nServer error (5xx) 44,682\nhttps://bingx.com/en\nReport date 2026-09-04'
        b=raw.encode();(self.root/'raw.txt').write_bytes(b)
        return {'kind':'gsc_ui','property':'sc-domain:bingx.com','captured_at':'2026-09-16T23:00:00Z','report':'page_indexing','report_date':'2026-09-04','filters':{'scope':'all known pages'},'count_unit':'pages','reported_total':44682,'total_quote':'44,682','report_date_quote':'2026-09-04','property_quote':'sc-domain:bingx.com','reviewer':'Codex','source':{'url':'https://search.google.com/search-console/index?resource_id=sc-domain%3Abingx.com','path':'raw.txt','sha256':hashlib.sha256(b).hexdigest()},'rows':[{'url':'https://bingx.com/en','reason_key':'server_error','reason_label':'Server error (5xx)','quote':'Server error (5xx) 44,682','url_quote':'https://bingx.com/en'}]}
    def test_valid_api_hash_retains_old_lastcrawl(self):
        self.add(self.api());r=self.load();self.assertEqual(len(r['observations']),1);self.assertEqual(r['observations'][0]['data']['index']['lastCrawlTime'],'2026-09-01T00:00:00Z');self.assertEqual(r['gaps'],[])
    def test_changed_bytes_quarantined(self):
        p=self.add(self.api());p.write_text('{}');r=self.load();self.assertEqual(r['observations'],[]);self.assertIn('sha256_mismatch',str(r['gaps']))
    def test_stale_acquisition_not_current(self):
        a=self.api();a['captured_at']='2026-09-01T00:00:00Z';self.add(a);r=self.load();self.assertEqual(r['observations'],[]);self.assertIn('stale_or_future_capture',str(r['gaps']))
    def test_future_capture_quarantined(self):
        a=self.api();a['captured_at']='2026-09-18T00:00:00Z';self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_foreign_property_quarantined(self):
        a=self.api();a['property']='sc-domain:uat.bingx.com';self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_request_property_disagreement_quarantined(self):
        a=self.api();a['request']['siteUrl']='https://bingx.com/';self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_error_status_not_success(self):
        a=self.api();a['http_status']=403;self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_api_missing_status_not_assumed_200(self):
        a=self.api();del a['http_status'];self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_lastcrawl_after_capture_quarantined(self):
        a=self.api();a['response']['inspectionResult']['indexStatusResult']['lastCrawlTime']='2026-09-17T01:00:00Z';self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_duplicate_id_poisoned_not_last_wins(self):
        self.add(self.api());self.manifest['evidence'].append(dict(self.manifest['evidence'][0]));r=self.load();self.assertEqual(r['observations'],[]);self.assertIn('duplicate_evidence_id',str(r['gaps']))
    def test_duplicate_content_not_two_observations(self):
        self.add(self.api());self.add(self.api(),id='e2');r=self.load();self.assertEqual(len(r['observations']),1);self.assertIn('duplicate_evidence_content',str(r['gaps']))
    def test_path_traversal_not_read(self):
        self.add(self.api());self.manifest['evidence'][0]['path']='../outside.json';r=self.load();self.assertEqual(r['observations'],[]);self.assertIn('proof_outside_root',str(r['gaps']))
    def test_symlink_escape_not_read(self):
        outside=Path(self.tmp.name).parent/'gsc-adapter-outside-test.json';outside.write_text('{}');self.addCleanup(lambda:outside.unlink(missing_ok=True));(self.root/'sym.json').symlink_to(outside)
        self.manifest['evidence']=[{'id':'e1','kind':'inspection_api','path':'sym.json','sha256':hashlib.sha256(b'{}').hexdigest()}];r=self.load();self.assertIn('proof_outside_root',str(r['gaps']))
    def test_kind_disagreement_quarantined(self):
        self.add(self.api(),kind='gsc_ui');self.assertEqual(self.load()['observations'],[])
    def test_api_outside_declared_scope_retained_but_not_paired(self):
        a=self.api();a['request']['inspectionUrl']='https://bingx.com/en/other';self.add(a);r=self.load();self.assertEqual(len(r['observations']),1);self.assertEqual(r['scope'][0]['url'],'https://bingx.com/en')
    def test_valid_ui_keeps_units_filters_and_count_not_url_count(self):
        self.add(self.ui());r=self.load();d=r['observations'][0]['data'];self.assertEqual(d['reported_total'],44682);self.assertEqual(d['observed_url_examples'],1);self.assertEqual(d['count_unit'],'pages');self.assertFalse(d['examples_exhaustive']);self.assertEqual(d['report_date'],'2026-09-04')
    def test_unsubstantiated_ui_quote_rejected(self):
        a=self.ui();a['rows'][0]['quote']='Everything is fixed';self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_unsubstantiated_ui_url_rejected(self):
        a=self.ui();a['rows'][0]['url']='https://bingx.com/en/phantom';self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_invented_total_rejected(self):
        a=self.ui();a['reported_total']=50000;self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_invented_report_date_rejected(self):
        a=self.ui();a['report_date']='2026-09-05';self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_source_property_query_mismatch_rejected(self):
        a=self.ui();a['source']['url']='https://search.google.com/search-console/index?resource_id=sc-domain%3Auat.bingx.com';self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_missing_reviewer_rejected(self):
        a=self.ui();del a['reviewer'];self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_ui_report_date_in_future_rejected(self):
        a=self.ui();a['report_date']='2027-01-01';self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_ui_unit_must_be_explicit(self):
        a=self.ui();a['count_unit']='unknown';self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_ui_source_must_be_search_console(self):
        a=self.ui();a['source']['url']='https://search.google.com.evil.org/';self.add(a);self.assertEqual(self.load()['observations'],[])
    def test_invalid_live_get_head_and_final_url(self):
        base={'kind':'live_http','property':'sc-domain:bingx.com','captured_at':'2026-09-16T23:00:00Z','url':'https://bingx.com/en','final_url':'https://bingx.com/en','device':'MOBILE','method':'GET','status':200,'source_description':'actual read-only HTTP capture'}
        for i,patch in enumerate([{'method':'HEAD'},{'status':True},{'device':'TABLET'},{'final_url':'https://example.com/'}]):
            self.manifest['evidence']=[];self.add({**base,**patch},id='live'+str(i));self.assertEqual(self.load()['observations'],[])
    def test_invalid_scope_fails_manifest(self):
        self.manifest['scope']=[{'url':'https://example.com','device':'MOBILE'}]
        with self.assertRaises(ValueError):self.load()
    def test_empty_evidence_not_empty_scope_pass(self):
        r=self.load();self.assertEqual(r['observations'],[]);self.assertEqual(len(r['scope']),1)
    def test_unknown_kind_quarantined(self):
        self.add({'kind':'fake','property':'sc-domain:bingx.com','captured_at':'2026-09-16T23:00:00Z'});self.assertEqual(self.load()['observations'],[])
if __name__=='__main__':unittest.main()
