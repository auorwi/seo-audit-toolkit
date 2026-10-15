import json,pathlib,subprocess,sys,unittest
import test_core as c
SCRIPT=pathlib.Path(__file__).resolve().parents[1]/'scripts/report_seo.py'
class CliTests(unittest.TestCase):
 setUp=c.CoreTests.setUp;source=c.CoreTests.source;load=c.CoreTests.load
 def runcli(self,*args):
  self.assertTrue(SCRIPT.is_file(),'CLI missing')
  return subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],text=True,capture_output=True)
 def test_aggregate_real_process(self):
  self.source();self.load();x=self.runcli('build','--manifest',self.root/'manifest.json','--state',self.root/'state','--output',self.root/'out');self.assertEqual(x.returncode,0,x.stderr);self.assertEqual(json.loads((self.root/'out/report.json').read_text())['issues'][0]['issue_id'],'same')
 def test_bad_input_nonzero(self):
  x=self.runcli('build','--manifest',self.root/'missing','--state',self.root/'state','--output',self.root/'out');self.assertEqual(x.returncode,1)
 def test_publish_not_automatic(self):
  self.source();self.load();x=self.runcli('build','--manifest',self.root/'manifest.json','--state',self.root/'state','--output',self.root/'out');self.assertEqual(x.returncode,0);self.assertFalse((self.root/'state/publication-state.json').exists())
 def test_help(self):self.assertEqual(self.runcli('--help').returncode,0)
