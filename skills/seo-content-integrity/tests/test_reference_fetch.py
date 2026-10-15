import io,json,tempfile
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError,URLError
from support import IntegrityTest

class ReferenceFetchTests(IntegrityTest):
    def test_invalid_symbol_before_network(self):
        mod=self.module('reference_fetch')
        with self.assertRaises(ValueError):mod.fetch('BTC/USDT')
    def test_http_429_keeps_raw_response(self):
        mod=self.module('reference_fetch');e=HTTPError('https://open-api.bingx.com',429,'quota',{},io.BytesIO(b'{"code":429}'))
        with patch.object(mod,'urlopen',side_effect=e):r=mod.fetch('BTC-USDT')
        self.assertEqual(r['status'],429);self.assertEqual(r['body'],'{"code":429}');self.assertEqual(r['method'],'GET')
    def test_network_error_not_business_state(self):
        mod=self.module('reference_fetch')
        with patch.object(mod,'urlopen',side_effect=URLError('unavailable')):r=mod.fetch('BTC-USDT')
        self.assertIsNone(r['status']);self.assertIn('unavailable',r['error'])
    def test_no_account_or_order_endpoint(self):
        mod=self.module('reference_fetch')
        with patch.object(mod,'urlopen',side_effect=URLError('offline')) as op:mod.fetch('BTC-USDT')
        request=op.call_args.args[0];self.assertIn('/openApi/spot/v1/common/symbols?',request.full_url);self.assertEqual(request.get_method(),'GET');self.assertIsNone(request.data);self.assertNotIn('X-bx-apikey',request.headers)
