"""Actual loopback API transport tests; kept separate from pure unit tests."""
from support import CWVTest
from test_field_fetch import Handler
import json,threading
from http.server import ThreadingHTTPServer
from urllib.request import Request
class FieldHTTPTests(CWVTest):
    def test_response_success_actual_bytes(self):
        m=self.module('field_fetch');server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:r=m.fetch_response(Request(f'http://127.0.0.1:{server.server_port}/'),timeout=3);self.assertEqual(r['status'],200);self.assertEqual(json.loads(r['body']),{'record':{'metrics':{}}})
        finally:server.shutdown();server.server_close()
    def test_429_body_preserved_no_retry(self):
        m=self.module('field_fetch');server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:r=m.fetch_response(Request(f'http://127.0.0.1:{server.server_port}/quota'),timeout=3);self.assertEqual(r['status'],429);self.assertEqual(json.loads(r['body'])['error']['code'],429)
        finally:server.shutdown();server.server_close()
