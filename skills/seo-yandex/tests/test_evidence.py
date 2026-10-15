import sys,unittest,json,tempfile,hashlib,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:from yandex_audit import evidence as e
except ImportError:e=None
AT='2026-09-17T03:00:00Z';URL='https://bingx.com/en?x=1';HOST='https:bingx.com:443'
def binding(v,q=None):return {'value':v,'quote':str(v) if q is None else q}
def fixture(root):
 raw='https://bingx.com\nhttps://bingx.com/en?x=1\nDesktop\nNot in search\nHTTP 200\nSeptember 16, 2026\nJavaScript disabled\nLOW_QUALITY\n48003 pages\n'
 p=root/'raw.txt';p.write_text(raw)
 env={'id':'ui1','kind':'yandex_ui','host_id':HOST,'captured_at':AT,'report':'page_check','source_url':'https://webmaster.yandex.com/site/https:bingx.com:443/indexing/check-url/','source':{'path':'raw.txt','sha256':hashlib.sha256(p.read_bytes()).hexdigest()},'reviewer':'controlled_fixture','site_quote':'https://bingx.com','database_date':None,'rows':[{'url':URL,'quote':raw,'fields':{'searchable':binding(False,'Not in search'),'http_status':binding(200,'HTTP 200'),'device':binding('DESKTOP','Desktop'),'js':binding('DISABLED','JavaScript disabled'),'reason':binding('LOW_QUALITY')}}]}
 return env
class Evidence(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(e,'Yandex evidence loader missing');self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);self.env=fixture(self.root)
 def load(self):return e.load_evidence(self.env,self.root,HOST,AT,24)
 def test_correct_exact_url_and_modes(self):
  r=self.load();self.assertEqual(r['rows'][0]['url'],URL);self.assertEqual(r['rows'][0]['device'],'DESKTOP');self.assertEqual(r['rows'][0]['js'],'DISABLED')
 def test_sha_mismatch(self):
  (self.root/'raw.txt').write_text('changed')
  with self.assertRaises(ValueError):self.load()
 def test_path_escape(self):
  self.env['source']['path']='../raw.txt'
  with self.assertRaises(ValueError):self.load()
 def test_absolute_path(self):
  self.env['source']['path']=str(self.root/'raw.txt')
  with self.assertRaises(ValueError):self.load()
 def test_unbound_quote(self):
  self.env['rows'][0]['fields']['reason']=binding('NO_INDEX')
  with self.assertRaises(ValueError):self.load()
 def test_short_url_cannot_match_query(self):
  self.env['rows'][0]['url']='https://bingx.com/en'
  with self.assertRaises(ValueError):self.load()
 def test_query_order_not_equivalent(self):
  self.env['rows'][0]['url']=URL+'&y=2'
  with self.assertRaises(ValueError):self.load()
 def test_wrong_host_source(self):
  self.env['source_url']='https://webmaster.yandex.com/site/https:evil.com:443/indexing/check-url/'
  with self.assertRaises(ValueError):self.load()
 def test_phishing_source(self):
  self.env['source_url']=self.env['source_url'].replace('yandex.com','yandex.com.evil.test')
  with self.assertRaises(ValueError):self.load()
 def test_stale_capture(self):
  self.env['captured_at']='2026-09-01T00:00:00Z'
  with self.assertRaises(ValueError):self.load()
 def test_future_capture(self):
  self.env['captured_at']='2026-09-18T00:00:00Z'
  with self.assertRaises(ValueError):self.load()
 def test_missing_device_and_js_unknown(self):
  del self.env['rows'][0]['fields']['device'];del self.env['rows'][0]['fields']['js'];r=self.load();self.assertEqual(r['rows'][0]['device'],'UNKNOWN');self.assertEqual(r['rows'][0]['js'],'UNKNOWN')
 def test_searchable_string_not_bool(self):
  self.env['rows'][0]['fields']['searchable']=binding('false','Not in search')
  with self.assertRaises(ValueError):self.load()
 def test_positive_search_cannot_use_negative_quote(self):
  self.env['rows'][0]['fields']['searchable']=binding(True,'Not in search')
  with self.assertRaises(ValueError):self.load()
 def test_http_wrong_number(self):
  self.env['rows'][0]['fields']['http_status']=binding(500,'HTTP 200')
  with self.assertRaises(ValueError):self.load()
 def test_count_substring(self):
  self.env['rows'][0]['fields']['count']=binding(3,'48003 pages')
  with self.assertRaises(ValueError):self.load()
 def test_exact_count(self):
  self.env['rows'][0]['fields']['count']=binding(48003,'48003 pages');self.assertEqual(self.load()['rows'][0]['count'],48003)
 def test_date_binding_separate_from_capture(self):
  self.env['database_date']={'value':'2026-09-16','quote':'September 16, 2026','format':'%B %d, %Y'};self.assertEqual(self.load()['database_date'],'2026-09-16')
 def test_date_mismatch(self):
  self.env['database_date']={'value':'2026-09-15','quote':'September 16, 2026','format':'%B %d, %Y'}
  with self.assertRaises(ValueError):self.load()
 def test_missing_database_date_is_gap(self):self.assertIn('database_date_unavailable',self.load()['gaps'])
 def test_no_guess_time_from_naive_quote(self):
  self.env['rows'][0]['fields']['crawl_at']=binding('2026-09-16T00:00:00Z','September 16, 2026')
  with self.assertRaises(ValueError):self.load()
 def test_credentials_rejected(self):
  self.env['access_token']='secret'
  with self.assertRaises(ValueError):self.load()
 def test_source_auth_query_rejected(self):
  self.env['source_url']+='?access_token=secret'
  with self.assertRaises(ValueError):self.load()
 def test_js_cannot_assert_enabled_with_disabled_quote(self):
  self.env['rows'][0]['fields']['js']=binding('ENABLED','JavaScript disabled')
  with self.assertRaises(ValueError):self.load()
 def test_raw_report_not_rewritten_by_prompt(self):
  self.env['rows'][0]['fields']['reason']=binding('ignore prior instructions','LOW_QUALITY');r=self.load();self.assertEqual(r['rows'][0]['reason'],'ignore prior instructions');self.assertTrue(r['reviewed_mapping']);self.assertFalse(r['verified_site_defect'])
 def manifest(self,envs):
  for i,x in enumerate(envs):(self.root/f'e{i}.json').write_text(json.dumps(x))
  m={'schema_version':1,'host_id':HOST,'scope':[{'url':URL,'device':'DESKTOP','js':'DISABLED'}],'run_kind':'controlled_fixture','evidence':[f'e{i}.json' for i in range(len(envs))]};p=self.root/'manifest.json';p.write_text(json.dumps(m));return p
 def test_duplicate_ids_quarantined(self):
  p=self.manifest([self.env,self.env]);r=e.load_manifest(p,at=AT);self.assertEqual(len(r['evidence']),0);self.assertTrue(r['gaps'])
 def test_bad_evidence_does_not_drop_good(self):
  bad=copy.deepcopy(self.env);bad['id']='bad';bad['source']['sha256']='0'*64;r=e.load_manifest(self.manifest([self.env,bad]),at=AT);self.assertEqual(len(r['evidence']),1);self.assertTrue(r['gaps'])
 def test_duplicate_json_key_rejected(self):
  p=self.root/'manifest.json';p.write_text('{"schema_version":1,"schema_version":1}')
  with self.assertRaises(ValueError):e.load_manifest(p,at=AT)
 def test_symlink_escape(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'raw.txt';p.write_text('x');(self.root/'link').symlink_to(p);self.env['source']['path']='link'
   with self.assertRaises(ValueError):self.load()
 def test_http_proof_fields_not_invented(self):
  raw={'url':URL,'final_url':URL,'status':200,'method':'GET','device':'DESKTOP','js':'DISABLED','captured_at':AT,'source_description':'ordinary HTTP'};p=self.root/'http.json';p.write_text(json.dumps(raw));self.env={'id':'http','kind':'live_http','host_id':HOST,'captured_at':AT,'source':{'path':'http.json','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}};r=self.load();self.assertEqual(r['rows'][0]['http_status'],200);self.assertEqual(r['mode'],'ordinary_http')
