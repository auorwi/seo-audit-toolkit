import tempfile,json,hashlib
from pathlib import Path
from support import IntegrityTest
from test_comparison import observation,AT

class ManifestFixture:
    def __init__(self,path):
        self.path=Path(path);html='<main><h1>Bitcoin</h1><b>100.00</b><b>110.00</b></main>'
        self.capture={'snapshot_id':'s1','url':'https://bingx.com/en/price/bitcoin','captured_at':AT,'source':'controlled fixture','readiness':'ready','html':html,'document_sha256':hashlib.sha256(html.encode()).hexdigest(),'visible_main':'Bitcoin 100.00 110.00', 'fields':{'card':{'present':True,'visible':True,'count':1,'text':'100.00','value':None},'body':{'present':True,'visible':True,'count':1,'text':'110.00','value':None}}}
        self.check={'check_id':'price-card-body','kind':'pair','url':self.capture['url'],'payload':{'left':observation('100.00'),'right':observation('110.00')},'citations':[{'snapshot_id':'s1','field':'card','quote':'100.00'},{'snapshot_id':'s1','field':'body','quote':'110.00'}]}
        self.review={'reviewer':'test reviewer','method':'semantic_review_of_bound_evidence','reviewed_at':AT,'snapshot_bindings':{'s1':self.capture['document_sha256']},'checks':[self.check]}
        self.manifest={'schema_version':1,'scope':[{'url':self.capture['url'],'kinds':['pair']}],'captures':[],'reviews':[],'actions':[]}
    def save(self,name,obj):
        raw=(json.dumps(obj,ensure_ascii=False)+'\n').encode();(self.path/name).write_bytes(raw);return {'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    def write(self):
        self.manifest['captures']=[self.save('capture.json',self.capture)];self.manifest['reviews']=[self.save('review.json',self.review)]
        (self.path/'manifest.json').write_text(json.dumps(self.manifest));return self.path/'manifest.json'

class AdapterTests(IntegrityTest):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.f=ManifestFixture(self.tmp.name)
    def load(self):return self.module('adapters').load_manifest(self.f.write(),at=AT)
    def test_valid_bound_review(self):self.assertEqual(len(self.load()['checks']),1)
    def test_html_hash_mismatch(self):self.f.capture['html']+='tamper';r=self.load();self.assertEqual(r['checks'],[]);self.assertTrue(r['gaps'])
    def test_wrong_review_hash(self):self.f.review['snapshot_bindings']['s1']='bad';self.assertEqual(self.load()['checks'],[])
    def test_review_before_capture(self):self.f.review['reviewed_at']='2026-09-17T04:59:59Z';self.assertEqual(self.load()['checks'],[])
    def test_future_review(self):self.f.review['reviewed_at']='2027-01-01T00:00:00Z';self.assertEqual(self.load()['checks'],[])
    def test_unknown_snapshot(self):self.f.check['citations'][0]['snapshot_id']='absent';self.assertEqual(self.load()['checks'],[])
    def test_missing_citations(self):self.f.check['citations']=[];self.assertEqual(self.load()['checks'],[])
    def test_quote_not_in_actual_field(self):self.f.check['citations'][0]['quote']='999';self.assertEqual(self.load()['checks'],[])
    def test_unquoted_number_not_accepted(self):self.f.check['payload']['left']=observation('120.00');self.assertEqual(self.load()['checks'],[])
    def test_hidden_field_not_visible_evidence(self):self.f.capture['fields']['card']['visible']=False;self.assertEqual(self.load()['checks'],[])
    def test_unready_page_not_normal_evidence(self):self.f.capture['readiness']='loading';self.assertEqual(self.load()['checks'],[])
    def test_missing_review_identity(self):self.f.review['reviewer']='';self.assertEqual(self.load()['checks'],[])
    def test_review_for_wrong_url(self):self.f.check['url']='https://bingx.com/en/price/ripple';self.assertEqual(self.load()['checks'],[])
    def test_stale_capture_not_current(self):self.f.capture['captured_at']='2025-01-01T00:00:00Z';self.assertEqual(self.load()['checks'],[])
    def test_raw_value_reparsed_not_trust_supplied_decimal(self):self.f.check['payload']['left']['number']['value']='999';self.assertEqual(self.load()['checks'],[])
    def test_capture_proof_tamper(self):
        path=self.f.write();(self.f.path/'capture.json').write_text('{}');r=self.module('adapters').load_manifest(path,at=AT);self.assertTrue(r['gaps']);self.assertEqual(r['checks'],[])
    def test_path_escape(self):
        path=self.f.write();d=json.loads(path.read_text());d['captures'][0]['path']='../secret';path.write_text(json.dumps(d));self.assertTrue(self.module('adapters').load_manifest(path,at=AT)['gaps'])
    def test_unknown_check_type(self):self.f.check['kind']='trade';self.assertEqual(self.load()['checks'],[])
    def test_duplicate_check_not_double_report(self):self.f.review['checks'].append(self.f.check);self.assertEqual(len(self.load()['checks']),1)
    def test_duplicate_field_selector_not_unique(self):self.f.capture['fields']['card']['count']=2;self.assertEqual(self.load()['checks'],[])
