import tempfile,subprocess,sys,json,os
from pathlib import Path
from support import CWVTest,ROOT,URL
class FieldCLITests(CWVTest):
    def run_cli(self,tmp,*extra):
        s=ROOT/'scripts/collect_field.py';self.assertTrue(s.exists(),'尚未实现字段数据CLI');env=dict(os.environ);env.pop('CWV_TEST_ABSENT_KEY',None);return subprocess.run([sys.executable,str(s),'--source','crux_api','--url',URL,'--device','mobile','--output',str(Path(tmp)/'out'),'--key-env','CWV_TEST_ABSENT_KEY',*extra],capture_output=True,text=True,env=env,timeout=10)
    def test_no_key_preserves_auth_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.run_cli(tmp);self.assertEqual(r.returncode,2,r.stderr);m=json.loads((Path(tmp)/'out/manifest.json').read_text());self.assertEqual(m['field_records'],[])
    def test_no_output_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:self.run_cli(tmp);self.assertEqual(self.run_cli(tmp).returncode,1)
    def test_bad_site_refused_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:self.assertEqual(self.run_cli(tmp,'--url','https://evil.test').returncode,1)
