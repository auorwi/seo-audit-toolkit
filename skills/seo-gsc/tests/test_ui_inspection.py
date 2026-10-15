"""Browser UI must remain a usable first-class collector without an OAuth token."""
import unittest,sys,json,hashlib,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gsc_audit.adapters import load_manifest
from gsc_audit.audit import audit
AT='2026-09-17T00:00:00Z'
class UIInspection(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
        raw='sc-domain:bingx.com\nhttps://bingx.com/en\nURL is not on Google\nServer error (5xx)\nGooglebot smartphone\nSep 1, 2026, 12:00:00 AM UTC\n'
        b=raw.encode();(self.root/'ui.txt').write_bytes(b)
        self.doc={'kind':'gsc_ui','property':'sc-domain:bingx.com','captured_at':'2026-09-16T23:00:00Z','report':'url_inspection','report_date':None,'filters':{},'count_unit':'not_applicable','property_quote':'sc-domain:bingx.com','reviewer':'Codex','source':{'path':'ui.txt','sha256':hashlib.sha256(b).hexdigest(),'url':'https://search.google.com/search-console/inspect?resource_id=sc-domain%3Abingx.com'},'rows':[],
        'inspection':{'url':'https://bingx.com/en','url_quote':'https://bingx.com/en','fields':{'verdict':{'value':'FAIL','quote':'URL is not on Google'},'pageFetchState':{'value':'SERVER_ERROR','quote':'Server error (5xx)'},'crawledAs':{'value':'MOBILE','quote':'Googlebot smartphone'},'lastCrawlTime':{'value':'2026-09-01T00:00:00Z','quote':'Sep 1, 2026, 12:00:00 AM UTC'}}}}
    def load(self):
        b=json.dumps(self.doc).encode();(self.root/'capture.json').write_bytes(b)
        m={'schema_version':1,'property':'sc-domain:bingx.com','scope':[{'url':'https://bingx.com/en','device':'MOBILE'}],'evidence':[{'id':'ui','kind':'gsc_ui','path':'capture.json','sha256':hashlib.sha256(b).hexdigest()}]}
        (self.root/'manifest.json').write_text(json.dumps(m));return load_manifest(self.root/'manifest.json',at=AT)
    def test_quoted_ui_inspection_matches_declared_url(self):
        x=self.load();self.assertEqual(len(x['observations']),1);r=audit(x,at=AT);self.assertEqual(r['coverage']['declared_urls_inspected'],1);self.assertEqual(r['checks'][0]['comparison'],'live_url_not_checked');self.assertEqual(len(r['findings']),1)
    def test_fabricated_inspection_field_quote_rejected(self):
        self.doc['inspection']['fields']['pageFetchState']['quote']='Page fetch successful';self.assertEqual(self.load()['observations'],[])
    def test_missing_inspection_url_quote_rejected(self):
        self.doc['inspection']['url']='https://bingx.com/en/notthere';self.assertEqual(self.load()['observations'],[])
    def test_live_test_cannot_supply_indexed_snapshot(self):
        self.doc['report']='live_test';self.assertEqual(self.load()['observations'],[])
    def test_live_only_field_not_silently_treated_as_indexed(self):
        self.doc['inspection']['fields']['isIndexed']={'value':True,'quote':'URL is not on Google'};self.assertEqual(self.load()['observations'],[])
    def test_ui_lastcrawl_after_capture_rejected(self):
        self.doc['inspection']['fields']['lastCrawlTime']['value']='2026-09-18T00:00:00Z';self.assertEqual(self.load()['observations'],[])
if __name__=='__main__':unittest.main()
