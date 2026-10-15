import tempfile,json,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.request import Request
from support import CWVTest,URL
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status=429 if self.path=='/quota' else 200;body=b'{"error":{"code":429}}' if status==429 else b'{"record":{"metrics":{}}}';self.send_response(status);self.send_header('content-type','application/json');self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass
class FetchTests(CWVTest):
    def test_crux_origin_query(self):
        r=self.module('field_fetch').query_for('crux_api',URL,'mobile','origin');self.assertEqual(r,{'origin':'https://bingx.com','formFactor':'PHONE'})
    def test_crux_url_query_preserves_parameters(self):self.assertEqual(self.module('field_fetch').query_for('crux_api',URL+'?a=1','desktop','url')['url'],URL+'?a=1')
    def test_psi_device_query(self):self.assertEqual(self.module('field_fetch').query_for('psi_api',URL,'mobile','url')['strategy'],'mobile')
    def test_external_target_refused(self):
        with self.assertRaises(ValueError):self.module('field_fetch').query_for('psi_api','https://evil.test','mobile','url')
    def test_missing_key_records_no_request(self):
        m=self.module('field_fetch')
        with tempfile.TemporaryDirectory() as tmp:
            r=m.collect_field('crux_api',URL,'mobile','url',Path(tmp)/'out',key=None);self.assertEqual(r['state'],'authorization_missing');saved=json.loads((Path(tmp)/'out/manifest.json').read_text());self.assertEqual(saved['field_records'],[]);self.assertEqual(len(saved['field_attempts']),1)
    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):self.module('field_fetch').query_for('invented',URL,'mobile','url')
