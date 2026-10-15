import tempfile,json
from support import IntegrityTest
from test_adapters import ManifestFixture
from test_comparison import AT
from test_market_reference import response

class ReferenceBindingTests(IntegrityTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.f=ManifestFixture(self.tmp.name)
        self.ref={'reference_id':'r1',**response(body=json.dumps({'code':0,'data':{'symbols':[{'symbol':'BTC-USDT','status':0}]}}))}
        self.f.check.update(kind='claim',payload={'kind':'lifecycle','observed_at':AT,'reviewed':True,'asset_id':'bitcoin','market':'spot','page_state':'active','reference_scope':'official_api','reference_id':'r1','reference_symbol':'BTC-USDT','reference_state':'inactive','reference_status':'ok','reference_asset_id':'bitcoin','reference_market':'spot','reference_at':AT})
    def load(self):
        self.f.manifest['references']=[self.f.save('reference.json',self.ref)];return self.module('adapters').load_manifest(self.f.write(),at=AT)
    def test_raw_response_binds_explicit_inactive_state(self):self.assertEqual(len(self.load()['checks']),1)
    def test_no_reference_id(self):self.f.check['payload'].pop('reference_id');self.assertEqual(self.load()['checks'],[])
    def test_unknown_reference(self):self.f.check['payload']['reference_id']='missing';self.assertEqual(self.load()['checks'],[])
    def test_asserted_state_disagrees_with_response(self):self.f.check['payload']['reference_state']='active';self.assertEqual(self.load()['checks'],[])
    def test_different_symbol_not_inactive(self):self.f.check['payload']['reference_symbol']='XRP-USDT';self.assertEqual(self.load()['checks'],[])
    def test_http_error_not_business_state(self):self.ref['status']=429;self.assertEqual(self.load()['checks'],[])
