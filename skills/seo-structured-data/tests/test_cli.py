import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from support import StructuredTest,ROOT,URL,AT
class CliTests(StructuredTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        body=b'<html><head><script type="application/ld+json">{"@context":"https://schema.org","@type":"Offer","price":"$12.00"}</script></head><body>BTC</body></html>'
        (self.root/'page.html').write_bytes(body);digest=hashlib.sha256(body).hexdigest()
        self.manifest=self.root/'manifest.json';self.manifest.write_text(json.dumps({'schema_version':1,'captures':[{'url':URL,'snapshot_id':'dom1','document_sha256':digest,'captured_at':'2026-09-17T01:00:00Z','source':'controlled fixture','representation':'rendered_html','readiness':'ready','entry_mode':'direct','evidence':{'path':'page.html','bytes':len(body),'sha256':digest}}]}))
    def run_cli(self,out='report',extra=None,scope=True):
        script=ROOT/'scripts/audit_structured.py';self.assertTrue(script.exists(),'尚未实现008审查CLI')
        cmd=[sys.executable,str(script),'--manifest',str(self.manifest),'--state',str(self.root/'state'),'--output',str(self.root/out),'--at',AT]
        if scope:cmd+=['--url',URL]
        return subprocess.run(cmd+(extra or []),capture_output=True,text=True)
    def test_outputs_four_layers_graph_and_history_with_gaps(self):
        r=self.run_cli();self.assertEqual(r.returncode,2,r.stderr)
        for name in ['report.md','report.json','coverage.csv','findings.csv','entities.json','graph-edges.csv','examples.json','engine-evidence.json','issue-history.json']:
            self.assertTrue((self.root/'report'/name).is_file())
        result=json.loads((self.root/'report/report.json').read_text());self.assertEqual(result['rows'][0]['layers']['actual_display'],'unverified')
    def test_replay_idempotent(self):
        self.assertEqual(self.run_cli().returncode,2);self.assertEqual(self.run_cli(out='again').returncode,2)
        history=json.loads((self.root/'again/issue-history.json').read_text());self.assertTrue(history);self.assertTrue(all(x['sightings']==1 for x in history))
    def test_no_scope_no_false_pass(self):
        self.assertEqual(self.run_cli(scope=False).returncode,1);self.assertFalse((self.root/'state').exists())
    def test_existing_output_preserved(self):
        self.run_cli();before=(self.root/'report/report.json').read_bytes();self.assertEqual(self.run_cli().returncode,1);self.assertEqual((self.root/'report/report.json').read_bytes(),before)
    def test_invalid_freshness_rejected(self):self.assertEqual(self.run_cli(extra=['--max-age-hours','0']).returncode,1)
    def test_bad_body_evidence_gaps_not_empty_success(self):
        (self.root/'page.html').write_text('bad');self.assertEqual(self.run_cli().returncode,2)
        r=json.loads((self.root/'report/report.json').read_text());self.assertEqual(r['coverage']['ready_documents'],0);self.assertTrue(r['input_gaps'])
    def test_report_escapes_page_content(self):
        report=self.module('report');from test_audit import capture
        c=capture();c['jsonld']['entities'][0]['data']['price']='<script>alert(1)</script>'
        r=self.module('audit').audit([c],[URL],at=AT);report.write_report(self.root/'escaped',r,[])
        self.assertNotIn('<script>',(self.root/'escaped/report.md').read_text())
