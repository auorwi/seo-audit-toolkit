import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from support import LinkTest,ROOT,URL,AT
class CliTests(LinkTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);body=b'<main><a href="/broken">Missing</a><a href="/empty"></a></main>';(self.root/'page.html').write_bytes(body);sha=hashlib.sha256(body).hexdigest()
        self.data={'schema_version':1,'captures':[{'url':URL,'snapshot_id':'dom','document_sha256':sha,'captured_at':'2026-09-17T02:00:00Z','source':'controlled fixture','representation':'rendered_html','readiness':'ready','entry_mode':'direct','evidence':{'path':'page.html','bytes':len(body),'sha256':sha}}],'assets':[URL,'https://bingx.com/broken','https://bingx.com/empty'],'seeds':{'entry':[URL]}}
        self.manifest=self.root/'manifest.json';self.manifest.write_text(json.dumps(self.data))
    def run_cli(self,out='report',extra=None):
        script=ROOT/'scripts/audit_links.py';self.assertTrue(script.exists(),'尚未实现009审查CLI')
        return subprocess.run([sys.executable,str(script),'--manifest',str(self.manifest),'--state',str(self.root/'state'),'--output',str(self.root/out),'--at',AT]+(extra or []),text=True,capture_output=True)
    def test_report_graph_all_edges_paths_targets_and_history_written(self):
        r=self.run_cli();self.assertEqual(r.returncode,2,r.stderr)
        for name in ['report.md','report.json','edges.csv','nodes.csv','paths.csv','targets.json','pagination.json','findings.csv','orphan-candidates.csv','issue-history.json']:self.assertTrue((self.root/'report'/name).is_file(),name)
        data=json.loads((self.root/'report/report.json').read_text());self.assertFalse(data['coverage']['full_site']);self.assertEqual(len(data['graph']['edges']),2)
    def test_replay_does_not_duplicate_history(self):
        self.assertEqual(self.run_cli().returncode,2);self.assertEqual(self.run_cli('again').returncode,2);h=json.loads((self.root/'again/issue-history.json').read_text());self.assertTrue(h);self.assertTrue(all(x['sightings']==1 for x in h))
    def test_empty_assets_fail_before_writing_state(self):
        self.data['assets']=[];self.manifest.write_text(json.dumps(self.data));self.assertEqual(self.run_cli().returncode,1);self.assertFalse((self.root/'state').exists())
    def test_existing_report_preserved(self):
        self.run_cli();before=(self.root/'report/report.json').read_bytes();self.assertEqual(self.run_cli().returncode,1);self.assertEqual((self.root/'report/report.json').read_bytes(),before)
    def test_corrupt_body_reports_gap_not_zero_issue_all_pass(self):
        (self.root/'page.html').write_text('bad');self.assertEqual(self.run_cli().returncode,2);r=json.loads((self.root/'report/report.json').read_text());self.assertFalse(r['graph']['edges']);self.assertTrue(r['gaps'])
    def test_supplement_merges_sources_and_rejects_conflicting_seed_group(self):
        p=self.root/'more.json';p.write_text(json.dumps({'schema_version':1,'captures':[],'assets':[],'seeds':{'entry':['https://bingx.com/other']}}));self.assertEqual(self.run_cli(extra=['--supplement',str(p)]).returncode,1)
    def test_invalid_budget_rejected(self):self.assertEqual(self.run_cli(extra=['--max-age-hours','0']).returncode,1)
    def test_html_in_anchor_cannot_execute_in_markdown(self):
        self.run_cli();p=json.loads((self.root/'report/report.json').read_text());p['findings'][0]['recommendation']='<script>alert(1)</script>';self.module('report').write_report(self.root/'escaped',p,[]);self.assertNotIn('<script>',(self.root/'escaped/report.md').read_text())
