"""Missing proof, wrong site/URL, unsafe input and stale scan must not turn into a clean audit."""
import unittest,tempfile,json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:from bing_audit.adapters import load_manifest
except ImportError:load_manifest=None
AT='2026-09-17T02:00:00Z';SITE='https://bingx.com/';URL=SITE+'en/price/example'
class Evidence(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(load_manifest,'Bing evidence adapter not implemented')
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.raw='bingx.com/\nhttps://bingx.com/en/price/example\nBing Index\nDiscovered but not crawled\nFailed\nHTTP 403\n16 Sept 2026\n48,003\n'
  self.doc={'kind':'bing_ui','site':SITE,'captured_at':'2026-09-17T01:00:00Z','report':'url_inspection','site_quote':'bingx.com/','reviewer':'test fixture reviewer','source':{'url':'https://www.bing.com/webmasters/urlinspection?siteUrl=https%3A%2F%2Fbingx.com%2F','path':'ui.txt'},'report_date':None,'filters':{},'count_unit':'not_applicable','rows':[],
  'inspection':{'url':URL,'url_quote':URL,'device':'UNKNOWN','fields':{'indexed':{'value':False,'quote':'Discovered but not crawled'},'fetch_state':{'value':'FAILED','quote':'Failed'}}}}
  self.scope=[{'url':URL,'device':'UNKNOWN'}]
 def load(self,mutate=None):
  raw=self.raw.encode();(self.root/'ui.txt').write_bytes(raw);self.doc['source']['sha256']=hashlib.sha256(raw).hexdigest()
  b=json.dumps(self.doc).encode();(self.root/'capture.json').write_bytes(b)
  m={'schema_version':1,'site':SITE,'scope':self.scope,'evidence':[{'id':'ui','kind':self.doc['kind'],'path':'capture.json','sha256':hashlib.sha256(b).hexdigest()}]}
  if mutate:mutate(m)
  (self.root/'manifest.json').write_text(json.dumps(m));return load_manifest(self.root/'manifest.json',at=AT)
 def test_real_ui_binding_keeps_generic_failure_without_fake_code(self):
  d=self.load();self.assertEqual(len(d['observations']),1);v=d['observations'][0]['data']['inspection'];self.assertEqual(v['fetch_state'],'FAILED');self.assertIsNone(v['http_status'])
 def test_changed_proof_hash_quarantined(self):self.assertEqual(self.load(lambda m:m['evidence'][0].update(sha256='0'*64))['observations'],[])
 def test_outer_path_escape_rejected(self):self.assertEqual(self.load(lambda m:m['evidence'][0].update(path='../capture.json'))['observations'],[])
 def test_raw_source_hash_mismatch_rejected(self):
  orig=self.load
  self.doc['source']['path']='missing.txt';self.assertEqual(orig()['observations'],[])
 def test_raw_symlink_escape_rejected(self):
  self.doc['source']['path']='outside.txt';(self.root/'outside.txt').symlink_to('/etc/hosts');self.assertEqual(self.load()['observations'],[])
 def test_duplicate_id_quarantines_all(self):
  d=self.load(lambda m:m['evidence'].append(dict(m['evidence'][0])));self.assertEqual(d['observations'],[]);self.assertEqual(len(d['gaps']),2)
 def test_duplicate_content_only_one(self):
  d=self.load(lambda m:m['evidence'].append({**m['evidence'][0],'id':'second'}));self.assertEqual(len(d['observations']),1);self.assertTrue(d['gaps'])
 def test_source_property_mismatch_rejected(self):
  self.doc['source']['url']='https://www.bing.com/webmasters/urlinspection?siteUrl=https%3A%2F%2Fother.test%2F';self.assertEqual(self.load()['observations'],[])
 def test_non_bing_backend_cannot_supply_platform_evidence(self):
  self.doc['source']['url']='https://bingx.com/webmasters?siteUrl=https://bingx.com/';self.assertEqual(self.load()['observations'],[])
 def test_deceptive_bing_backend_rejected(self):
  self.doc['source']['url']='https://www.bing.com.evil.test/webmasters?siteUrl=https://bingx.com/';self.assertEqual(self.load()['observations'],[])
 def test_missing_selected_site_binding_rejected(self):
  self.doc['site_quote']='other.test/';self.assertEqual(self.load()['observations'],[])
 def test_longer_url_cannot_bind_shorter_url(self):
  self.raw=self.raw.replace(URL,URL+'-wrong');self.assertEqual(self.load()['observations'],[])
 def test_query_variant_cannot_bind_original_url(self):
  self.raw=self.raw.replace(URL,URL+'?ref=elsewhere');self.assertEqual(self.load()['observations'],[])
 def test_unquoted_field_rejected(self):
  self.doc['inspection']['fields']['fetch_state']['quote']='Successful';self.assertEqual(self.load()['observations'],[])
 def test_live_url_indexed_field_is_rejected(self):
  self.doc['report']='live_url';self.assertEqual(self.load()['observations'],[])
 def test_live_url_can_report_http403_without_index_assertion(self):
  self.doc['report']='live_url';self.doc['inspection']['fields'].pop('indexed');self.doc['inspection']['fields']['http_status']={'value':403,'quote':'HTTP 403'};d=self.load();self.assertEqual(d['observations'][0]['data']['inspection']['http_status'],403);self.assertIsNone(d['observations'][0]['data']['inspection']['indexed'])
 def test_invented_http_code_not_in_quote_rejected(self):
  self.doc['inspection']['fields']['http_status']={'value':503,'quote':'HTTP 403'};self.assertEqual(self.load()['observations'],[])
 def test_unknown_fetch_enum_rejected(self):
  self.doc['inspection']['fields']['fetch_state']['value']='SERVER_ERROR';self.assertEqual(self.load()['observations'],[])
 def test_stale_capture_quarantined(self):
  self.doc['captured_at']='2026-09-01T00:00:00Z';self.assertEqual(self.load()['observations'],[])
 def test_future_capture_quarantined(self):
  self.doc['captured_at']='2026-09-18T00:00:00Z';self.assertEqual(self.load()['observations'],[])
 def test_ui_date_must_match_source_not_reviewer_guess(self):
  self.doc.update(report_date='2026-09-15',report_date_quote='16 Sept 2026',report_date_format='D MMM YYYY');self.assertEqual(self.load()['observations'],[])
 def test_ui_date_accepts_bing_english_format(self):
  self.doc.update(report_date='2026-09-16',report_date_quote='16 Sept 2026',report_date_format='D MMM YYYY');self.assertEqual(len(self.load()['observations']),1)
 def test_count_rounded_display_not_exact_integer(self):
  self.doc.update(reported_total=48000,total_quote='48k',count_unit='pages');self.raw+='48k';self.assertEqual(self.load()['observations'],[])
 def test_count_bound_to_raw_integer(self):
  self.doc.update(reported_total=48003,total_quote='48,003',count_unit='pages');self.assertEqual(self.load()['observations'][0]['data']['reported_total'],48003)
 def test_unknown_report_not_silently_aliased(self):
  self.doc['report']='gsc_indexing';self.assertEqual(self.load()['observations'],[])
 def test_report_cannot_turn_retrieved_date_into_scan_date(self):
  self.doc['report']='site_scan';self.doc.pop('inspection');self.doc['scan']={'id':'prior','completed_at':'2026-08-01T00:00:00Z','quote':'16 Sept 2026'};self.assertEqual(self.load()['observations'],[])
 def test_plaintext_credentials_not_ingested(self):
  self.doc['api_key']='sensitive-placeholder';d=self.load();self.assertEqual(d['observations'],[]);self.assertNotIn('sensitive-placeholder',str(d))
 def test_raw_api_url_with_key_rejected(self):
  self.doc['source']['url']+='&apikey=sensitive-placeholder';d=self.load();self.assertEqual(d['observations'],[]);self.assertNotIn('sensitive-placeholder',str(d))
 def test_raw_capture_credentials_rejected(self):
  self.raw+='\nAuthorization: Bearer sensitive-placeholder';d=self.load();self.assertEqual(d['observations'],[]);self.assertNotIn('sensitive-placeholder',str(d))
 def test_empty_scope_not_success(self):
  self.scope=[];d=self.load();self.assertEqual(d['scope'],[])

class ScanDate(unittest.TestCase):
 setUp=Evidence.setUp;load=Evidence.load
 def test_old_scan_date_does_not_gain_today_timestamp(self):
  self.doc['report']='site_scan';self.doc.pop('inspection');self.raw+='\n12 Feb 2026\n';self.doc['scan']={'id':'Monthly Feb','completed_date':'2026-02-12','quote':'12 Feb 2026','date_format':'D MMM YYYY'}
  d=self.load();self.assertEqual(len(d['observations']),1);v=d['observations'][0]['data'];self.assertIn('historical_site_scan_not_current_live_capture',v['gaps']);self.assertEqual(v['scan']['completed_date'],'2026-02-12');self.assertNotIn('completed_at',v['scan'])
 def test_scan_date_quote_must_match(self):
  self.doc['report']='site_scan';self.doc.pop('inspection');self.raw+='\n12 Feb 2026\n';self.doc['scan']={'id':'Monthly Feb','completed_date':'2026-09-16','quote':'12 Feb 2026','date_format':'D MMM YYYY'};self.assertEqual(self.load()['observations'],[])

if __name__=='__main__':unittest.main()
