import json
from support import IntegrityTest
from test_comparison import AT

def response(**kw):
    return {'url':'https://open-api.bingx.com/openApi/spot/v1/common/symbols?symbol=BTC-USDT','method':'GET','status':200,'captured_at':AT,'source':'actual public HTTP response','body':json.dumps({'code':0,'data':{'symbols':[{'symbol':'BTC-USDT','status':1}]}}),**kw}

class MarketReferenceTests(IntegrityTest):
    def check(self,row=None,symbol='BTC-USDT'):return self.module('market_reference').review_response(row or response(),symbol=symbol,at=AT)
    def test_active_symbol(self):self.assertEqual(self.check()['state'],'active')
    def test_explicit_inactive(self):self.assertEqual(self.check(response(body=json.dumps({'code':0,'data':{'symbols':[{'symbol':'BTC-USDT','status':0}]}})))['state'],'inactive')
    def test_absence_not_unlisted(self):self.assertEqual(self.check(symbol='XRP-USDT')['state'],'unknown')
    def test_api_error_not_unlisted(self):self.assertEqual(self.check(response(body='{"code":100204,"msg":"missing data"}'))['state'],'unknown')
    def test_http_429_not_site_status(self):self.assertEqual(self.check(response(status=429))['state'],'unknown')
    def test_not_futures(self):self.assertEqual(self.check(response(url='https://open-api.bingx.com/openApi/swap/v2/quote/contracts'))['state'],'unknown')
    def test_wrong_host(self):self.assertEqual(self.check(response(url='https://fake.example/openApi/spot/v1/common/symbols'))['state'],'unknown')
    def test_requires_readonly_get(self):self.assertEqual(self.check(response(method='POST'))['state'],'unknown')
    def test_old_reference_not_current(self):self.assertEqual(self.check(response(captured_at='2025-01-01T00:00:00Z'))['state'],'unknown')
    def test_malformed_response(self):self.assertEqual(self.check(response(body='<html>error</html>'))['state'],'unknown')
    def test_conflicting_rows_not_choose_one(self):self.assertEqual(self.check(response(body=json.dumps({'code':0,'data':{'symbols':[{'symbol':'BTC-USDT','status':0},{'symbol':'BTC-USDT','status':1}]}})))['state'],'unknown')
    def test_unknown_status_not_coerced(self):self.assertEqual(self.check(response(body=json.dumps({'code':0,'data':{'symbols':[{'symbol':'BTC-USDT','status':'active'}]}})))['state'],'unknown')
    def test_reference_limited_to_spot(self):self.assertEqual(self.check()['market'],'spot');self.assertFalse(self.check()['all_products_verified'])
    def test_actual_null_symbols_not_delisting(self):
        r=self.check(response(body='{"code":0,"data":{"symbols":null}}'));self.assertEqual(r['state'],'unknown');self.assertEqual(r['reason'],'symbol_absent_not_proof_of_delisting')
