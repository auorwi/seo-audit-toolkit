import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from support import RenderingTest,ROOT
from test_readiness import URL
from test_audit import sample

AT='2026-09-17T00:01:00Z'
class RenderCliTests(RenderingTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
        raw=b'<head><title>Solv Protocol</title><meta name="description" content="Project"><link rel="canonical" href="https://bingx.com/en/launchpad/detail?currency=78"></head><main><h1></h1>Project</main>'
        metadata={'id':'initial','url':URL,'requested_url':URL,'stage':'initial','kind':'initial_html','entry_mode':'direct','navigation_id':'navigation-1','source':'HTTP collector','captured_at':'2026-09-17T00:00:00Z'}
        self.records=[{**metadata,'evidence':self.save('initial.html',raw)}]
        for id,time in [('a','2026-09-17T00:00:01Z'),('b','2026-09-17T00:00:03Z')]:
            capture=sample(id,time,kind='dom_fields')
            evidence=self.save(id+'.json',json.dumps(capture).encode())
            self.records.append({k:v for k,v in capture.items() if k in {'id','url','requested_url','stage','kind','entry_mode','navigation_id','source','captured_at'}}|{'evidence':evidence})
        self.manifest=self.base/'manifest.json';self.manifest.write_text(json.dumps({'schema_version':1,'snapshots':self.records}))
        self.urls=self.base/'urls.json';self.urls.write_text(json.dumps([{'url':URL,'expected_entry_modes':['direct'],'readiness':{'required_identity':'SOLV'}}]))

    def save(self,name,body):
        p=self.base/name;p.write_bytes(body)
        return {'path':name,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}

    def run_cli(self,extra=None,output='report',scope=True):
        script=ROOT/'scripts/audit_rendering.py';self.assertTrue(script.is_file(),'尚未实现005 CLI')
        cmd=[sys.executable,str(script),'--manifest',str(self.manifest),'--state',str(self.base/'state'),'--output',str(self.base/output),'--at',AT]
        if scope:cmd+=['--urls',str(self.urls)]
        return subprocess.run(cmd+(extra or []),capture_output=True,text=True)

    def test_pipeline_outputs_completion_and_explicit_unknown_initial_identity(self):
        run=self.run_cli();self.assertEqual(run.returncode,2,run.stderr)
        result=json.loads((self.base/'report/report.json').read_text())
        self.assertEqual(result['rows'][0]['readiness']['state'],'ready')
        self.assertTrue(any(c['change']=='h1_populated' for c in result['changes']))
        self.assertIn('identity',result['rows'][0]['unchecked_fields'])
        for name in ['report.md','changes.csv','coverage.csv','findings.csv','issue-history.json']:
            self.assertTrue((self.base/'report'/name).exists())

    def test_idempotent_rerun_does_not_duplicate_same_issue(self):
        self.assertEqual(self.run_cli().returncode,2)
        self.assertEqual(self.run_cli(output='again').returncode,2)
        history=json.loads((self.base/'again/issue-history.json').read_text())
        self.assertTrue(history);self.assertTrue(all(x['sightings']==1 for x in history))

    def test_bad_scope_fails_before_state_writes(self):
        run=self.run_cli(scope=False);self.assertEqual(run.returncode,1,run.stderr)
        self.assertFalse((self.base/'state').exists())

    def test_old_report_not_overwritten(self):
        self.assertEqual(self.run_cli().returncode,2)
        before=(self.base/'report/report.json').read_bytes()
        self.assertEqual(self.run_cli().returncode,1)
        self.assertEqual((self.base/'report/report.json').read_bytes(),before)

    def test_input_hash_failure_stays_visible_in_report(self):
        (self.base/'b.json').write_text('{}')
        run=self.run_cli();self.assertEqual(run.returncode,2,run.stderr)
        result=json.loads((self.base/'report/report.json').read_text())
        self.assertTrue(result['input_gaps'])
        self.assertNotEqual(result['rows'][0]['readiness']['state'],'ready')

    def test_negative_freshness_is_rejected(self):
        run=self.run_cli(['--max-age-hours','-1']);self.assertEqual(run.returncode,1,run.stderr)

    def test_missing_dependency_report_not_empty_success(self):
        run=self.run_cli(['--manifest',str(self.base/'missing.json')])
        self.assertEqual(run.returncode,1);self.assertFalse((self.base/'report').exists())

    def test_report_escapes_markup_and_csv_formula_cells(self):
        report=self.module('report')
        result={'at':AT,'coverage':{'requested_urls':1,'ready_paths':0,'missing_entry_modes':[],'all_requested_paths_observed':False},'rows':[],'changes':[],'interactions':[],'input_gaps':[],
            'findings':[{'issue_id':'r1','url':URL,'rule':'=formula','classification':'review','recommendation':'<img src=x>','evidence':[]}]}
        report.write_report(self.base/'manual',result,[])
        self.assertIn("'=formula",(self.base/'manual/findings.csv').read_text())
        self.assertNotIn('<img src=x>',(self.base/'manual/report.md').read_text())

    def test_human_report_exposes_interaction_verification(self):
        report=self.module('report')
        result={'at':AT,'coverage':{'requested_urls':1,'ready_paths':0,'missing_entry_modes':[]},'rows':[],'changes':[],'findings':[],
            'interactions':[{'id':'event-1','url':URL,'kind':'back','verification':'observed_stable_transition','comparison':{'title':{'before':'Old','after':'New'}},'readiness':{'state':'ready'}}]}
        report.write_report(self.base/'interaction-report',result,[])
        self.assertIn('observed_stable_transition',(self.base/'interaction-report/report.md').read_text())
        self.assertIn('Old',(self.base/'interaction-report/interactions.csv').read_text())
