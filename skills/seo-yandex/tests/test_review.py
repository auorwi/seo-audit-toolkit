import unittest,json,hashlib,copy
import test_evidence as helper
import test_audit as a
from yandex_audit import evidence as e
class Review(unittest.TestCase):
 setUp=helper.Evidence.setUp
 def dom(self):
  raw={'url':helper.URL,'title':'BTC USDT','h1':['BTCUSDT'],'body_excerpt':'BTCUSDT trade','canonical':helper.URL,'captured_at':helper.AT,'device':'DESKTOP','js':'ENABLED'};p=self.root/'dom.json';p.write_text(json.dumps(raw));self.env={'id':'dom','kind':'public_dom','host_id':helper.HOST,'captured_at':helper.AT,'source':{'path':'dom.json','sha256':hashlib.sha256(p.read_bytes()).hexdigest()},'reviewer':'controlled','reviews':[{'reason':'ROUTE_ENTITY_MISMATCH','field':'h1','quote':'BTCUSDT'}]};return self.env
 def load(self):
  return helper.Evidence.load(self)
 def supported(self):
  try:return self.load()
  except ValueError as ex:self.fail('public DOM support missing: '+str(ex))
 def test_dom_not_yandex_snapshot(self):
  self.dom();r=self.supported();self.assertEqual(r['mode'],'public_dom');self.assertIsNone(r['rows'][0]['searchable']);self.assertEqual(r['rows'][0]['reason'],'ROUTE_ENTITY_MISMATCH')
 def test_dom_review_quote_bound_to_specific_field(self):
  self.dom();self.env['reviews'][0]['field']='title'
  with self.assertRaises(ValueError):self.load()
 def test_dom_url_identity_from_proof(self):
  self.dom();r=self.supported();self.assertEqual(r['rows'][0]['url'],helper.URL)
 def test_dom_review_unknown_rule_not_accepted(self):
  self.dom();self.env['reviews'][0]['reason']='DELETE_WEBSITE'
  with self.assertRaises(ValueError):self.load()
 def test_dom_empty_title_can_be_observed_without_nonempty_quote(self):
  self.dom();v=json.loads((self.root/'dom.json').read_text());v['title']='';p=self.root/'dom.json';p.write_text(json.dumps(v));self.env['source']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();self.env['reviews']=[{'reason':'EMPTY_METADATA','field':'title','quote':''}];self.assertEqual(self.supported()['rows'][0]['reason'],'EMPTY_METADATA')
 def test_empty_quote_cannot_prove_nonempty_field(self):
  self.dom();self.env['reviews']=[{'reason':'EMPTY_METADATA','field':'title','quote':''}]
  with self.assertRaises(ValueError):self.load()
 def test_body_200_error_page_is_candidate_no_engine_classification(self):
  r=a.ev('dom','dom',a.row(js='ENABLED',reason='ERROR_PAGE_CONTENT',searchable=None),'public_dom');f=a.audit(a.data(r),at=a.AT)['findings'][0];self.assertEqual(f['classification'],'reviewed_public_observation');self.assertFalse(f['verified_site_defect']);self.assertEqual(f['owner_skill'],'004')
 def test_dom_joins_as_supplement_not_same_js_claim(self):
  r=a.ev('dom','dom',a.row(js='ENABLED',reason='ROUTE_ENTITY_MISMATCH',searchable=None),'public_dom');o=a.audit(a.data(a.ev('db','database',a.row()),a.http(),r),at=a.AT);self.assertEqual(o['checks'][0].get('public_dom_evidence'),['dom']);self.assertEqual(o['checks'][0]['js'],'DISABLED')
 def test_api_proof_requires_host_endpoint_request(self):
  p=self.root/'api.json';p.write_text('{"problems":{}}');self.env={'id':'api','kind':'yandex_api','host_id':helper.HOST,'captured_at':helper.AT,'endpoint':'diagnostics','source':{'path':'api.json','sha256':hashlib.sha256(p.read_bytes()).hexdigest()},'request_url':'https://api.webmaster.yandex.net/v4/user/123/hosts/https:other.com:443/diagnostics'}
  with self.assertRaises(ValueError):self.load()
 def test_api_verified_request_passes(self):
  p=self.root/'api.json';p.write_text('{"problems":{}}');self.env={'id':'api','kind':'yandex_api','host_id':helper.HOST,'captured_at':helper.AT,'endpoint':'diagnostics','source':{'path':'api.json','sha256':hashlib.sha256(p.read_bytes()).hexdigest()},'request_url':'https://api.webmaster.yandex.net/v4/user/123/hosts/https:bingx.com:443/diagnostics'};self.assertEqual(self.load()['rows'],[])
