import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from support import CrawlTest, AT, ROOT

class CliReportTests(CrawlTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        records=[]
        for name,url,body,ctype in [('robots','https://bingx.com/robots.txt',b'User-agent: *\nAllow: /','text/plain'),('page','https://bingx.com/en',b'<meta name="robots" content="noindex">','text/html')]:
            path=self.base/(name+'.body');path.write_bytes(body)
            records.append({'url':url,'status':200,'checked_at':AT,'headers':[['content-type',ctype]],
                'evidence':{'path':path.name,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}})
        self.data={'schema_version':1,'records':records}
        self.manifest=self.base/'manifest.json';self.manifest.write_text(json.dumps(self.data))
        self.targets=self.base/'urls.json';self.targets.write_text(json.dumps([{'url':'https://bingx.com/en','index_intent':'indexable','intent_source':'route owner','intent_at':AT}]))

    def run_cli(self,extra=None,scope=True,output='report'):
        script=ROOT/'scripts/audit_crawlability.py'
        self.assertTrue(script.is_file(),'尚未实现：003独立CLI')
        cmd=[sys.executable,str(script),'--manifest',str(self.manifest),'--state',str(self.base/'state'),'--output',str(self.base/output),'--at',AT]
        if scope:cmd+=['--urls',str(self.targets)]
        return subprocess.run(cmd+(extra or []),capture_output=True,text=True)

    def test_end_to_end_writes_evidence_report_and_three_engine_rows(self):
        run=self.run_cli();self.assertEqual(run.returncode,0,run.stderr)
        result=json.loads((self.base/'report/report.json').read_text())
        self.assertEqual(len(result['rows']),3)
        self.assertEqual(len([f for f in result['findings'] if f['rule']=='unexpected_noindex']),3)
        self.assertTrue((self.base/'report/report.md').is_file())
        self.assertTrue((self.base/'report/rows.csv').is_file())
        self.assertTrue((self.base/'report/request-history.csv').is_file())
        self.assertTrue((self.base/'state/issues.sqlite').is_file())
        self.assertFalse(result['coverage']['full_site'])

    def test_single_engine_scope_is_supported(self):
        run=self.run_cli(['--agent','Bingbot']);self.assertEqual(run.returncode,0,run.stderr)
        result=json.loads((self.base/'report/report.json').read_text())
        self.assertEqual(len(result['rows']),1);self.assertEqual(result['rows'][0]['agent'],'Bingbot')

    def test_missing_robot_evidence_returns_partial_report_not_success(self):
        self.data['records']=self.data['records'][1:];self.manifest.write_text(json.dumps(self.data))
        run=self.run_cli();self.assertEqual(run.returncode,2,run.stderr)
        result=json.loads((self.base/'report/report.json').read_text())
        self.assertTrue(any(f['rule']=='robots_evidence_gap' for f in result['findings']))

    def test_empty_scope_fails_before_creating_state_or_output(self):
        run=self.run_cli(scope=False)
        self.assertNotEqual(run.returncode,0)
        self.assertFalse((self.base/'state').exists());self.assertFalse((self.base/'report').exists())

    def test_tampered_evidence_produces_gap_not_current_noindex(self):
        (self.base/'page.body').write_bytes(b'changed')
        run=self.run_cli();self.assertEqual(run.returncode,2,run.stderr)
        result=json.loads((self.base/'report/report.json').read_text())
        self.assertTrue(result['input_gaps'])
        self.assertFalse(any(f['rule']=='unexpected_noindex' for f in result['findings']))

    def test_rerun_other_output_does_not_duplicate_historical_issues(self):
        self.assertEqual(self.run_cli().returncode,0)
        self.assertEqual(self.run_cli(output='again').returncode,0)
        data=json.loads((self.base/'again/issue-history.json').read_text())
        self.assertEqual(len(data),3);self.assertTrue(all(i['sightings']==1 for i in data))

    def test_invalid_freshness_and_engine_fail_before_writes(self):
        for args in [['--max-age-hours','nan'],['--agent','AdsBot-Google']]:
            run=self.run_cli(args);self.assertEqual(run.returncode,1,run.stderr)
        self.assertFalse((self.base/'state').exists())

    def test_existing_report_is_not_silently_overwritten(self):
        self.assertEqual(self.run_cli().returncode,0)
        first=(self.base/'report/report.json').read_bytes()
        run=self.run_cli();self.assertEqual(run.returncode,1)
        self.assertEqual((self.base/'report/report.json').read_bytes(),first)

    def test_csv_formula_payload_is_literal_and_markdown_html_is_escaped(self):
        report=self.module('report')
        rows=[{'issue_id':'x','rule':'=HYPERLINK("evil")','url':'https://bingx.com/','agent':'Googlebot','classification':'review_needed','recommendation':'<img src=x>','evidence':{}}]
        result={'at':AT,'scope':['https://bingx.com/'],'coverage':{'requested_urls':1,'engine_rows':0,'full_site':False,'rendered_rows_observed':0},'rows':[],'findings':rows,'input_gaps':[]}
        report.write_report(self.base/'standalone',result,[])
        self.assertIn("'=HYPERLINK",(self.base/'standalone/findings.csv').read_text())
        self.assertNotIn('<img src=x>',(self.base/'standalone/report.md').read_text())
