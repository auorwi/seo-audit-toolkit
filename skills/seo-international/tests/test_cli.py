import json,hashlib,subprocess,sys,tempfile
from pathlib import Path
from support import InternationalTest,ROOT,AT
class CLITests(InternationalTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        html='<html lang="en"><head><link rel="alternate" hreflang="fr" href="/fr/a"></head></html>';raw=html.encode();(self.root/'page.html').write_bytes(raw);sha=hashlib.sha256(raw).hexdigest()
        m={'schema_version':1,'captures':[{'url':'https://bingx.com/en/a','snapshot_id':'s1','captured_at':AT,'source':'fixture','representation':'initial_html','state':'completed','document_sha256':sha,'evidence':{'path':'page.html','bytes':len(raw),'sha256':sha}}]};(self.root/'m.json').write_text(json.dumps(m))
    def run_cli(self,*args,out='out'):
        script=ROOT/'scripts/audit_international.py';self.assertTrue(script.is_file(),'尚未实现010 CLI')
        return subprocess.run([sys.executable,str(script),'--manifest',str(self.root/'m.json'),'--state',str(self.root/'state'),'--output',str(self.root/out),'--at',AT,*args],text=True,capture_output=True)
    def test_partial_exit_and_evidence(self):
        r=self.run_cli();self.assertEqual(r.returncode,2,r.stderr);report=json.loads((self.root/'out/report.json').read_text());self.assertEqual(report['findings'][0]['rule'],'hreflang_declaration_ineligible')
    def test_rerun_idempotent_history(self):
        self.run_cli();self.run_cli(out='out2');history=json.loads((self.root/'out2/issue-history.json').read_text());self.assertEqual(history[0]['sightings'],1)
    def test_absent_issue_not_closed(self):
        self.run_cli();(self.root/'m.json').write_text('{"schema_version":1}');self.run_cli(out='out2');self.assertEqual(json.loads((self.root/'out2/issue-history.json').read_text())[0]['status'],'open')
    def test_output_no_overwrite(self):
        self.run_cli();before=(self.root/'out/report.json').read_bytes();r=self.run_cli();self.assertEqual(r.returncode,1);self.assertEqual((self.root/'out/report.json').read_bytes(),before)
    def test_bad_at_input_error(self):self.assertEqual(self.run_cli('--at','invalid').returncode,1)
    def test_empty_evidence_not_full_success(self):
        (self.root/'m.json').write_text('{"schema_version":1}');self.assertEqual(self.run_cli().returncode,2)
    def test_detail_exports_written(self):
        self.run_cli();self.assertTrue((self.root/'out/language-matrix.csv').is_file());self.assertTrue((self.root/'out/findings.csv').is_file());self.assertTrue((self.root/'out/report.md').is_file())
    def test_supplement_can_add_new_capture(self):
        (self.root/'extra.json').write_text('{"schema_version":1}');self.assertEqual(self.run_cli('--supplement',str(self.root/'extra.json')).returncode,2)
