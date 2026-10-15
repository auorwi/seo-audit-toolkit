import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from support import ROOT,URL,AT

class NuCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.html=self.root/'input.html';self.html.write_text('<!doctype html><html lang="en"><title>Fixture</title><main><h1>Prices</h1></main></html>')
        self.fake=self.root/'fixture-nu';self.fake.write_text('#!'+sys.executable+'\nimport sys,json\nprint("fixture-nu" if "--version" in sys.argv else json.dumps({"messages":[]}))\n');self.fake.chmod(0o755)

    def run_cli(self,extra=None):
        script=ROOT/'scripts/check_html.py';self.assertTrue(script.is_file(),'尚未实现独立Nu命令')
        return subprocess.run([sys.executable,str(script),'--nu-executable',str(self.fake),'--html',str(self.html),'--url',URL,'--source','controlled test fixture','--captured-at','2026-09-17T00:00:00Z','--at',AT,'--output',str(self.root/'out')]+(extra or []),capture_output=True,text=True)

    def test_nu_cli_manifest_keeps_source_capture_time_separate(self):
        run=self.run_cli();self.assertEqual(run.returncode,0,run.stderr)
        from semantics_audit.adapters import load_manifest
        result=load_manifest(self.root/'out/manifest.json')
        self.assertEqual(result['gaps'],[])
        self.assertEqual(result['captures'][0]['captured_at'],'2026-09-17T00:00:00Z')
        self.assertEqual(result['tool_reports'][0]['checked_at'],AT)

    def test_invalid_source_time_rejected_before_writes(self):
        run=self.run_cli(['--captured-at','unknown']);self.assertEqual(run.returncode,1)
        self.assertFalse((self.root/'out').exists())

    def test_stale_source_is_not_redated_to_checker_run(self):
        run=self.run_cli(['--captured-at','2020-01-01T00:00:00Z']);self.assertEqual(run.returncode,0,run.stderr)
        manifest=json.loads((self.root/'out/manifest.json').read_text())
        self.assertEqual(manifest['captures'][0]['captured_at'],'2020-01-01T00:00:00Z')

    def test_missing_executable_produces_evidence_gap_capture(self):
        run=self.run_cli(['--nu-executable',str(self.root/'missing')]);self.assertEqual(run.returncode,2,run.stderr)
        capture=json.loads((self.root/'out/nu.capture.json').read_text())
        self.assertEqual(capture['state'],'unavailable')
