"""Real LHCI, real Chrome, real loopback HTTP. No performance fixture is a live BingX claim."""
import os,json,threading,tempfile,unittest,sys
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from support import CWVTest,ROOT
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status=404 if self.path.startswith('/missing') else 200
        body=b'<!doctype html><html lang="en"><head><title>Controlled CWV fixture</title><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><main><h1>Controlled page</h1><p>Actual loopback HTML for measurement validation.</p></main></body></html>'
        self.send_response(status);self.send_header('content-type','text/html');self.send_header('content-length',str(len(body)));self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass
class RuntimeTests(CWVTest):
    def collect(self,path):
        m=self.module('runner');self.assertTrue(hasattr(m,'run_lhci_cell'),'尚未实现LHCI实际采集与失败留存');self.assertTrue((ROOT/'scripts/record_lhci.cjs').exists(),'尚未实现真实LHCI每次尝试取证')
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                url=f'http://127.0.0.1:{server.server_address[1]}{path}';cfg=m.build_collect_config(url,'desktop',os.environ['CWV_CHROME'],runs=1,allow_local_fixture=True)
                result=m.run_lhci_cell(Path(tmp)/'cell',cfg,Path(os.environ['CWV_RUNTIME']),ROOT/'scripts/record_lhci.cjs',{'runner':'lhci','host_id':'controlled-test','network_location':'loopback','entry_mode':'direct','login':'unauthenticated'},timeout_seconds=150)
                evidence=[]
                for a in result['attempts']:
                    row={**a}
                    if a.get('lhr_evidence'):row['lhr']=json.loads((Path(tmp)/'cell'/a['lhr_evidence']['path']).read_text())
                    evidence.append(row)
                result['loaded_attempts']=evidence;return result
        finally:server.shutdown();server.server_close();thread.join()
    def test_real_lhr_saved_and_parseable(self):
        r=self.collect('/');self.assertEqual(r['exit_code'],0,r.get('stderr'));self.assertEqual(len(r['attempts']),1);a=r['loaded_attempts'][0];self.assertEqual(a['state'],'completed');self.assertTrue(a['lhr']['lighthouseVersion']);parsed=self.module('lab').parse_lhr(a['lhr'],r['context']);self.assertTrue(parsed['valid_measurement']);self.assertIsNone(parsed['metrics']['INP'])
    def test_actual_http_error_retries_not_lost(self):
        r=self.collect('/missing');self.assertNotEqual(r['exit_code'],0);self.assertEqual(len(r['attempts']),3);self.assertTrue(all(a['state']=='failed' for a in r['attempts']));self.assertTrue(all(a.get('error') for a in r['attempts']))
if __name__=='__main__':unittest.main()
