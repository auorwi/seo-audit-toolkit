"""CLI/history/report behavior, not snapshots of implementation code."""
import unittest,tempfile,json,hashlib,subprocess,sys,html
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:from bing_audit.report import write_report
except ImportError:write_report=None
from bing_audit.audit import audit
from test_audit import data,indexed,public,recommendation,AT,URL,SITE
CLI=Path(__file__).resolve().parents[1]/'scripts/audit_bing.py'
class Report(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(write_report,'Report implementation missing')
 def test_quote_and_mode_kept_in_human_report(self):
  r=audit(data(recommendation()),at=AT)
  with tempfile.TemporaryDirectory() as t:
   write_report(Path(t),r,[]);s=html.unescape((Path(t)/'report.md').read_text());self.assertIn('Title too long',s);self.assertIn('recommendation_observation',s)
 def test_unrelated_row_not_attributed_to_issue(self):
  a=recommendation();a['data']['rows'].append({'url':URL+'/other','reason_key':'valid','reason_label':'unrelated evidence','quote':'unrelated evidence'});r=audit(data(a),at=AT)
  with tempfile.TemporaryDirectory() as t:
   write_report(Path(t),r,[]);self.assertNotIn('unrelated evidence',(Path(t)/'report.md').read_text())
 def test_raw_html_escaped_in_markdown(self):
  a=recommendation();a['data']['rows'][0]['quote']='<script>alert(1)</script>';r=audit(data(a),at=AT)
  with tempfile.TemporaryDirectory() as t:
   write_report(Path(t),r,[]);self.assertNotIn('<script>',(Path(t)/'report.md').read_text())
 def test_empty_result_not_whole_site_health(self):
  r=audit(data(),at=AT)
  with tempfile.TemporaryDirectory() as t:
   write_report(Path(t),r,[]);out=json.loads((Path(t)/'report.json').read_text());self.assertFalse(out['coverage']['declared_checks_complete']);self.assertFalse(out['coverage']['full_site_proven'])
 def test_fixture_labeled_and_required_artifacts_exist(self):
  d=data();d['run_kind']='controlled_fixture';r=audit(d,at=AT)
  with tempfile.TemporaryDirectory() as t:
   write_report(Path(t),r,[]);self.assertIn('控制样例',(Path(t)/'report.md').read_text())
   for n in ['checks.json','findings.csv','issue-history.json','issue-history.csv','referrals.json']:self.assertTrue((Path(t)/n).is_file())
 def test_report_cannot_overwrite_evidence_directory(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'proof.txt';p.write_text('original')
   with self.assertRaises(ValueError):write_report(Path(t),audit(data(),at=AT),[])
   self.assertEqual(p.read_text(),'original')
class CLIBehavior(unittest.TestCase):
 def setUp(self):
  self.assertTrue(CLI.is_file(),'CLI not implemented');self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.manifest={'schema_version':1,'run_kind':'controlled_fixture','site':SITE,'scope':[{'url':URL,'device':'UNKNOWN'}],'evidence':[]}
 def run_cli(self,name='out'):
  p=self.root/'manifest.json';p.write_text(json.dumps(self.manifest));return subprocess.run([sys.executable,str(CLI),'--manifest',str(p),'--state',str(self.root/'state'),'--output',str(self.root/name),'--at',AT],capture_output=True,text=True)
 def test_missing_evidence_returns_partial_with_report(self):
  r=self.run_cli();self.assertEqual(r.returncode,2,r.stderr);self.assertTrue((self.root/'out/report.md').exists())
 def test_empty_declared_scope_not_zero_exit(self):
  self.manifest['scope']=[];self.assertEqual(self.run_cli().returncode,2)
 def test_invalid_site_fails_before_history_write(self):
  self.manifest['site']='https://evil.test/';r=self.run_cli();self.assertEqual(r.returncode,1);self.assertFalse((self.root/'state').exists())
 def test_existing_output_rejected_before_state_changes(self):
  (self.root/'out').mkdir();(self.root/'out/evidence.txt').write_text('proof');r=self.run_cli();self.assertEqual(r.returncode,1);self.assertFalse((self.root/'state').exists());self.assertEqual((self.root/'out/evidence.txt').read_text(),'proof')
 def test_same_run_outputs_identical_history(self):
  self.assertEqual(self.run_cli('first').returncode,2);self.assertEqual(self.run_cli('second').returncode,2)
  for f in ['report.json','issue-history.json']:self.assertEqual((self.root/'first'/f).read_bytes(),(self.root/'second'/f).read_bytes())

class CompleteScopedCLI(unittest.TestCase):
 def test_explicit_index_snapshot_and_http_complete_only_declared_scope(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);raw='bingx.com/\n'+URL+'\nIndexed successfully\nSuccessful\n';(root/'raw.txt').write_text(raw)
   source={'url':'https://www.bing.com/webmasters/urlinspection?siteUrl=https%3A%2F%2Fbingx.com%2F','path':'raw.txt','sha256':hashlib.sha256(raw.encode()).hexdigest()}
   ui={'kind':'bing_ui','site':SITE,'captured_at':'2026-09-17T02:00:00Z','report':'url_inspection','site_quote':'bingx.com/','reviewer':'controlled fixture','source':source,'report_date':None,'filters':{},'count_unit':'not_applicable','rows':[],'inspection':{'url':URL,'url_quote':URL,'device':'UNKNOWN','fields':{'indexed':{'value':True,'quote':'Indexed successfully'},'fetch_state':{'value':'SUCCESS','quote':'Successful'}}}}
   http={'kind':'live_http','site':SITE,'captured_at':'2026-09-17T02:00:00Z','url':URL,'final_url':URL,'device':'UNKNOWN','method':'GET','status':200,'source_description':'controlled fixture, not actual network'};refs=[]
   for i,d in enumerate([ui,http]):
    b=json.dumps(d).encode();p=root/(str(i)+'.json');p.write_bytes(b);refs.append({'id':str(i),'kind':d['kind'],'path':p.name,'sha256':hashlib.sha256(b).hexdigest()})
   m={'schema_version':1,'run_kind':'controlled_fixture','site':SITE,'scope':[{'url':URL,'device':'UNKNOWN'}],'evidence':refs};(root/'manifest.json').write_text(json.dumps(m))
   r=subprocess.run([sys.executable,str(CLI),'--manifest',str(root/'manifest.json'),'--state',str(root/'state'),'--output',str(root/'out'),'--at',AT],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr);v=json.loads((root/'out/report.json').read_text());self.assertTrue(v['coverage']['declared_checks_complete']);self.assertFalse(v['coverage']['full_site_proven']);self.assertFalse(v['checks'][0]['bing_fixed']);self.assertEqual(v['checks'][0]['client_comparability'],'unproven')

if __name__=='__main__':unittest.main()
