import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from support import SemanticsTest,ROOT,URL,AT
from test_rules import dom,node
from test_tool_reports import report,axe_rule

class SemanticCliTests(SemanticsTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        body=b'<!doctype html><html><main><h1>Prices</h1></main></html>'
        digest=hashlib.sha256(body).hexdigest();document=self.save('dom.html',body)
        capture=dom([node('m','main'),node('h','h1','Prices')],document_sha256=digest)
        row={k:capture[k] for k in ['url','snapshot_id','captured_at','source']}
        row.update({'kind':'rendered_elements','evidence':self.save('elements.json',json.dumps(capture).encode()),'document_evidence':document})
        native=report(document_sha256=digest,input_sha256=digest);native['payload']['violations']=[axe_rule()]
        checker={k:native[k] for k in ['tool','url','capture_id','checked_at']}
        checker.update({'evidence':self.save('axe.json',json.dumps(native).encode()),'document_evidence':document})
        self.manifest=self.root/'manifest.json';self.manifest.write_text(json.dumps({'schema_version':1,'captures':[row],'tool_reports':[checker]}))
        self.urls=self.root/'urls.json';self.urls.write_text(json.dumps([{'url':URL,'required_tools':['axe']}]))

    def save(self,name,body):
        (self.root/name).write_bytes(body)
        return {'path':name,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}

    def run_cli(self,extra=None,out='report',scope=True):
        script=ROOT/'scripts/audit_semantics.py';self.assertTrue(script.is_file(),'尚未实现006 CLI')
        cmd=[sys.executable,str(script),'--manifest',str(self.manifest),'--state',str(self.root/'state'),'--output',str(self.root/out),'--at',AT]
        if scope:cmd+=['--urls',str(self.urls)]
        return subprocess.run(cmd+(extra or []),capture_output=True,text=True)

    def test_cli_outputs_evidence_and_pending_manual_review(self):
        run=self.run_cli();self.assertEqual(run.returncode,2,run.stderr)
        result=json.loads((self.root/'report/report.json').read_text())
        self.assertTrue(any(f['rule']=='button-name' for f in result['findings']))
        self.assertTrue(result['pending_reviews'])
        for name in ['report.md','coverage.csv','findings.csv','handoffs.csv','pending-reviews.json','issue-history.json']:
            self.assertTrue((self.root/'report'/name).exists())

    def test_same_run_updates_history_once(self):
        self.assertEqual(self.run_cli().returncode,2)
        self.assertEqual(self.run_cli(out='again').returncode,2)
        history=json.loads((self.root/'again/issue-history.json').read_text())
        self.assertTrue(history);self.assertTrue(all(row['sightings']==1 for row in history))

    def test_missing_scope_rejected_before_state(self):
        run=self.run_cli(scope=False);self.assertEqual(run.returncode,1);self.assertFalse((self.root/'state').exists())

    def test_prior_report_is_not_overwritten(self):
        self.assertEqual(self.run_cli().returncode,2)
        before=(self.root/'report/report.json').read_bytes()
        self.assertEqual(self.run_cli().returncode,1)
        self.assertEqual((self.root/'report/report.json').read_bytes(),before)

    def test_invalid_evidence_produces_gap_not_empty_pass(self):
        (self.root/'elements.json').write_text('{}')
        run=self.run_cli();self.assertEqual(run.returncode,2,run.stderr)
        result=json.loads((self.root/'report/report.json').read_text())
        self.assertTrue(result['input_gaps']);self.assertEqual(result['coverage']['ready_documents'],0)

    def test_bad_freshness_fails_before_state(self):
        self.assertEqual(self.run_cli(['--max-age-hours','0']).returncode,1)
        self.assertFalse((self.root/'state').exists())

    def test_invalid_checker_selection_not_accepted(self):
        self.urls.write_text(json.dumps([{'url':URL,'required_tools':['invented']}]))
        self.assertEqual(self.run_cli().returncode,1)

    def test_scope_plan_retains_unvisited_pages_in_report(self):
        plan=self.module('scope').build_plan([URL,'https://bingx.com/en/learn'],mode='all',source='test list',at=AT)
        scope=self.root/'scope.json';scope.write_text(json.dumps(plan))
        run=self.run_cli(['--scope',str(scope)],scope=False)
        self.assertEqual(run.returncode,2,run.stderr)
        self.assertTrue((self.root/'report/report.json').exists(),run.stderr)
        result=json.loads((self.root/'report/report.json').read_text())
        self.assertEqual(result['scope'],[URL,'https://bingx.com/en/learn'])
        self.assertEqual(result['scope_plan']['scope_id'],plan['scope_id'])
        checklist=json.loads((self.root/'report/page-checklist.json').read_text())
        self.assertEqual(len(checklist['pages']),2)
        self.assertEqual(checklist['pages'][1]['browser_state'],'not_checked')

    def test_scope_plan_cannot_be_silently_narrowed_with_urls(self):
        plan=self.module('scope').build_plan([URL,'https://bingx.com/en/learn'],mode='all',source='test list',at=AT)
        scope=self.root/'scope.json';scope.write_text(json.dumps(plan))
        run=self.run_cli(['--scope',str(scope)])
        self.assertEqual(run.returncode,1)
        self.assertFalse((self.root/'state').exists())

    def test_human_report_escapes_page_markup(self):
        report_module=self.module('report')
        result={'at':AT,'scope':[URL],'coverage':{'requested_urls':1,'ready_documents':0,'usable_tool_runs':0,'full_accessibility_certification':False},'rows':[],'handoffs':[],'pending_reviews':[],'gaps':[],'input_gaps':[],
            'findings':[{'issue_id':'one','url':URL,'rule':'=formula','classification':'manual_review','recommendation':'<script>alert(1)</script>','retest':'Check','evidence':[]}]}
        report_module.write_report(self.root/'manual',result,[])
        self.assertNotIn('<script>',(self.root/'manual/report.md').read_text())
        self.assertIn("'=formula",(self.root/'manual/findings.csv').read_text())

    def test_human_report_groups_repeated_rule_and_retains_full_json(self):
        self.run_cli()
        result=json.loads((self.root/'report/report.json').read_text())
        first=result['findings'][0]
        result['findings']=[{**first,'issue_id':str(i),'evidence':[{'html':'x'*10000,'target':['#n'+str(i)]}]} for i in range(40)]
        self.module('report').write_report(self.root/'compact',result,[])
        text=(self.root/'compact/report.md').read_text()
        self.assertLess(len(text),20000)
        self.assertNotIn('40 条记录',text)
        self.assertNotIn('x'*100,text)
        stored=json.loads((self.root/'compact/report.json').read_text())
        self.assertEqual(len(stored['findings']),40)
        self.assertEqual(len(stored['findings'][39]['evidence'][0]['html']),10000)

    def test_human_report_keeps_checker_message_and_location(self):
        self.run_cli()
        result=json.loads((self.root/'report/report.json').read_text())
        result['findings'][0]['evidence']=[{'message':'Attribute hid is invalid','location':{'firstLine':5},'html':'<style hid="x">'}]
        self.module('report').write_report(self.root/'message',result,[])
        text=(self.root/'message/report-details.md').read_text()
        self.assertIn('Attribute hid is invalid',text)
        self.assertIn('firstLine',text)
