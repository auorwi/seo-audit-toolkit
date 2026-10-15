import json
import subprocess
import sys
import tempfile
from pathlib import Path
from support import RoutingTest, ROOT, AT
import test_adapters
from test_audit import A,B,response

class RoutingCliTests(RoutingTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
        self.evidence=lambda name,body:test_adapters.RoutingAdapterTests.evidence(self,name,body)
        records=[response(target=B),response(url=B,target=B),response(url='https://bingx.com/robots.txt',body=b'User-agent: *\nAllow: /',headers=[('content-type','text/plain')])]
        self.data={'schema_version':1,'records':[test_adapters.RoutingAdapterTests.stored(self,r,str(i)+'.body') for i,r in enumerate(records)]}
        self.manifest=self.base/'manifest.json';self.manifest.write_text(json.dumps(self.data))
        self.urls=self.base/'urls.json';self.urls.write_text(json.dumps([A]))

    def run_cli(self,extra=None,output='report',scope=True):
        script=ROOT/'scripts/audit_canonical.py';self.assertTrue(script.is_file(),'尚未实现004 CLI')
        cmd=[sys.executable,str(script),'--manifest',str(self.manifest),'--state',str(self.base/'state'),'--output',str(self.base/output),'--at',AT]
        if scope:cmd+=['--urls',str(self.urls)]
        return subprocess.run(cmd+(extra or []),capture_output=True,text=True)

    def test_end_to_end_outputs_graph_parameter_diff_and_history(self):
        run=self.run_cli();self.assertEqual(run.returncode,0,run.stderr)
        r=json.loads((self.base/'report/report.json').read_text())
        self.assertEqual(len(r['rows']),1);self.assertEqual(r['rows'][0]['url'],A)
        self.assertTrue((self.base/'report/relations.csv').is_file())
        self.assertTrue((self.base/'report/parameter-changes.csv').is_file())
        self.assertTrue((self.base/'report/report.md').is_file())
        self.assertTrue((self.base/'state/issues.sqlite').is_file())

    def test_missing_target_produces_pending_list_and_partial_exit(self):
        self.data['records']=self.data['records'][:1];self.manifest.write_text(json.dumps(self.data))
        run=self.run_cli();self.assertEqual(run.returncode,2,run.stderr)
        pending=(self.base/'report/pending-targets.csv').read_text()
        self.assertIn(B,pending)

    def test_no_scope_rejected_before_writes(self):
        run=self.run_cli(scope=False);self.assertEqual(run.returncode,1,run.stderr)
        self.assertFalse((self.base/'state').exists())

    def test_identical_rerun_preserves_single_sighting(self):
        self.assertEqual(self.run_cli().returncode,0)
        self.assertEqual(self.run_cli(output='again').returncode,0)
        history=json.loads((self.base/'again/issue-history.json').read_text())
        self.assertTrue(history);self.assertTrue(all(i['sightings']==1 for i in history))

    def test_existing_report_not_overwritten(self):
        self.assertEqual(self.run_cli().returncode,0)
        before=(self.base/'report/report.json').read_bytes()
        self.assertEqual(self.run_cli().returncode,1)
        self.assertEqual((self.base/'report/report.json').read_bytes(),before)

    def test_supplement_actual_rendered_conflict_is_reported(self):
        dom=test_adapters.RoutingAdapterTests.stored(self,response(target=A,mode='rendered'),'dom.body')
        supplement=self.base/'browser.json';supplement.write_text(json.dumps({'schema_version':1,'records':[],'rendered':[dom]}))
        run=self.run_cli(['--supplement',str(supplement)]);self.assertEqual(run.returncode,0,run.stderr)
        result=json.loads((self.base/'report/report.json').read_text())
        self.assertIn('raw_rendered_canonical_conflict',{f['rule'] for f in result['findings']})

    def test_report_does_not_include_raw_html_or_interpret_csv_formulas(self):
        report=self.module('report')
        result={'at':AT,'scope':[A],'coverage':{'requested_urls':1,'full_site':False},'rows':[],'relations':[],'findings':[{'issue_id':'routing-x','url':A,'rule':'=malicious','classification':'review_needed','recommendation':'<script>bad</script>','evidence':[]}],'input_gaps':[]}
        report.write_report(self.base/'manual',result,[])
        self.assertIn("'=malicious",(self.base/'manual/findings.csv').read_text())
        self.assertNotIn('<script>bad</script>',(self.base/'manual/report.md').read_text())

    def test_tampered_evidence_returns_partial_not_validated_canonical(self):
        (self.base/'0.body').write_bytes(b'changed')
        run=self.run_cli();self.assertEqual(run.returncode,2,run.stderr)
        result=json.loads((self.base/'report/report.json').read_text())
        self.assertIsNone(result['rows'][0]['raw']);self.assertTrue(result['input_gaps'])
