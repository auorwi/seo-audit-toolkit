import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from support import TdkTest,ROOT,URL,AT
class CliTests(TdkTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        body=b'<html lang="en"><head><title> </title><meta name="description" content="=unsafe"></head><body><h1>SOLV</h1></body></html>'
        (self.root/'page.html').write_bytes(body);digest=hashlib.sha256(body).hexdigest()
        self.manifest=self.root/'manifest.json';self.manifest.write_text(json.dumps({'schema_version':1,'captures':[{'url':URL,'snapshot_id':'dom1','document_sha256':digest,'captured_at':'2026-09-17T00:00:00Z','source':'controlled fixture','representation':'rendered_html','readiness':'ready','evidence':{'path':'page.html','bytes':len(body),'sha256':digest}}]}))
    def run_cli(self,*,out='report',extra=None,scope=True):
        script=ROOT/'scripts/audit_tdk.py';self.assertTrue(script.is_file(),'尚未实现007 CLI')
        cmd=[sys.executable,str(script),'--manifest',str(self.manifest),'--state',str(self.root/'state'),'--output',str(self.root/out),'--at',AT]
        if scope:cmd+=['--url',URL]
        return subprocess.run(cmd+(extra or []),capture_output=True,text=True)
    def test_scoped_report_has_history_original_values_and_pending(self):
        r=self.run_cli();self.assertEqual(r.returncode,2,r.stderr)
        for name in ['report.md','report.json','findings.csv','coverage.csv','duplicate-clusters.csv','drafts.json','handoffs.csv','issue-history.json']:
            self.assertTrue((self.root/'report'/name).is_file())
        data=json.loads((self.root/'report/report.json').read_text());self.assertTrue(data['pending_reviews']);self.assertTrue(any(f['rule']=='empty_title' for f in data['findings']))
    def test_identical_replay_is_idempotent(self):
        self.assertEqual(self.run_cli().returncode,2);self.assertEqual(self.run_cli(out='second').returncode,2)
        h=json.loads((self.root/'second/issue-history.json').read_text());self.assertTrue(h);self.assertTrue(all(x['sightings']==1 for x in h))
    def test_empty_scope_cannot_create_success(self):
        self.assertEqual(self.run_cli(scope=False).returncode,1);self.assertFalse((self.root/'state').exists())
    def test_existing_output_not_overwritten(self):
        self.run_cli();b=(self.root/'report/report.json').read_bytes();self.assertEqual(self.run_cli().returncode,1);self.assertEqual((self.root/'report/report.json').read_bytes(),b)
    def test_invalid_freshness_rejected(self):
        self.assertEqual(self.run_cli(extra=['--max-age-hours','nan']).returncode,1);self.assertFalse((self.root/'state').exists())
    def test_corrupt_evidence_creates_partial_report(self):
        (self.root/'page.html').write_text('bad');self.assertEqual(self.run_cli().returncode,2)
        r=json.loads((self.root/'report/report.json').read_text());self.assertEqual(r['coverage']['ready_pages'],0);self.assertTrue(r['input_gaps'])
    def test_invalid_urls_json_shape_rejected(self):
        (self.root/'urls.json').write_text('{}');self.assertEqual(self.run_cli(extra=['--urls',str(self.root/'urls.json')]).returncode,1)
    def test_report_escapes_markup_and_limits_display_evidence(self):
        report=self.module('report');audit=self.module('audit');from test_context import capture
        c=capture();c['fields']['titles']=[{'value':'<script>'+('x'*10000)}];r=audit.audit([c],[URL],at=AT)
        report.write_report(self.root/'escaped',r,[])
        text=(self.root/'escaped/report.md').read_text();self.assertNotIn('<script>',text);self.assertLess(len(text),15000)
