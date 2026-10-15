import unittest,sys,tempfile,json,hashlib,subprocess
from pathlib import Path
import test_evidence as helper
import test_audit as a
try:from yandex_audit.report import write_report
except ImportError:write_report=None
class Delivery(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(write_report,'Yandex report missing');self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
 def result(self):return a.audit(a.data(a.ev('db','database',a.row()),a.http()),at=a.AT)
 def test_json_keeps_modes_and_proof(self):
  write_report(self.root/'out',self.result(),[]);r=json.loads((self.root/'out/report.json').read_text());self.assertEqual(r['findings'][0]['evidence'][0]['source']['sha256'],'a'*64)
 def test_output_overwrite_rejected(self):
  p=self.root/'out';write_report(p,self.result(),[])
  with self.assertRaises(ValueError):write_report(p,self.result(),[])
 def test_html_and_table_escape(self):
  r=self.result();r['findings'][0]['recommendation']='<script>alert(1)</script>|x';write_report(self.root/'out',r,[]);s=(self.root/'out/report.md').read_text();self.assertNotIn('<script>',s);self.assertIn('&lt;script&gt;',s)
 def test_csv_formula_escape(self):
  r=self.result();r['findings'][0]['recommendation']='=HYPERLINK("evil")';write_report(self.root/'out',r,[]);self.assertIn("'=HYPERLINK",(self.root/'out/findings.csv').read_text())
 def test_fixture_not_claimed_actual_audit(self):
  write_report(self.root/'out',self.result(),[]);self.assertIn('控制样例',(self.root/'out/report.md').read_text())
 def test_historical_replay_label(self):
  r=self.result();r['run_kind']='historical_replay';write_report(self.root/'out',r,[]);self.assertIn('历史证据重放',(self.root/'out/report.md').read_text())
 def manifest(self,complete=False):
  env=helper.fixture(self.root);env['report']='database';env['database_date']={'value':'2026-09-16','quote':'September 16, 2026','format':'%B %d, %Y'};(self.root/'ui.json').write_text(json.dumps(env));files=['ui.json']
  if complete:
   h={'url':helper.URL,'final_url':helper.URL,'status':200,'method':'GET','device':'DESKTOP','js':'DISABLED','captured_at':helper.AT,'source_description':'controlled'};p=self.root/'http.json';p.write_text(json.dumps(h));x={'id':'http','kind':'live_http','host_id':helper.HOST,'captured_at':helper.AT,'source':{'path':'http.json','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}};(self.root/'env-http.json').write_text(json.dumps(x));files.append('env-http.json')
  m={'schema_version':1,'host_id':helper.HOST,'scope':[{'url':helper.URL,'device':'DESKTOP','js':'DISABLED'}],'run_kind':'controlled_fixture','evidence':files};p=self.root/'manifest.json';p.write_text(json.dumps(m));return p
 def cli(self,manifest):
  return subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/audit_yandex.py'),'--manifest',str(manifest),'--state',str(self.root/'state'),'--output',str(self.root/'out'),'--at',helper.AT],capture_output=True,text=True)
 def test_cli_partial_writes_report(self):
  r=self.cli(self.manifest());self.assertEqual(r.returncode,2,r.stderr);self.assertTrue((self.root/'out/report.md').exists())
 def test_cli_completed_scoped_comparison(self):
  r=self.cli(self.manifest(True));self.assertEqual(r.returncode,0,r.stderr);self.assertFalse(json.loads((self.root/'out/report.json').read_text())['coverage']['all_site_verified'])
 def test_cli_invalid_input_no_report(self):
  p=self.root/'bad.json';p.write_text('{}');r=self.cli(p);self.assertEqual(r.returncode,1);self.assertFalse((self.root/'out').exists())
 def test_replayed_seven_artifacts_identical(self):
  from crawlability.ledger import record,history
  r=self.result();db=self.root/'x.db';record(db,r);write_report(self.root/'a',r,history(db));record(db,r);write_report(self.root/'b',r,history(db));names=['report.json','report.md','checks.json','findings.csv','issue-history.json','issue-history.csv','referrals.json'];self.assertEqual(len(list((self.root/'a').iterdir())),7)
  for name in names:self.assertEqual((self.root/'a'/name).read_bytes(),(self.root/'b'/name).read_bytes())
