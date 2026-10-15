"""Controlled examples must not look like live audits or pollute production issue IDs."""
import unittest,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gsc_audit.audit import audit
from gsc_audit.report import write_report
from test_audit import data,api,live,AT
import test_evidence as helpers
class Provenance(unittest.TestCase):
    def test_controlled_run_is_explicit_in_machine_and_human_report(self):
        x=data(api(),live());x['run_kind']='controlled_fixture';r=audit(x,at=AT);self.assertEqual(r.get('run_kind'),'controlled_fixture')
        with tempfile.TemporaryDirectory() as t:
            write_report(Path(t),r,[]);self.assertIn('控制样例',(Path(t)/'report.md').read_text())
    def test_fixture_issue_id_cannot_collide_with_real_audit(self):
        x=data(api(),live());normal=audit(x,at=AT);x['run_kind']='controlled_fixture';fake=audit(x,at=AT);self.assertNotEqual(normal['findings'][0]['issue_id'],fake['findings'][0]['issue_id'])
    def test_historical_run_preserves_issue_identity(self):
        x=data(api(),live());normal=audit(x,at=AT);x['run_kind']='historical_replay';r=audit(x,at=AT);self.assertEqual(normal['findings'][0]['issue_id'],r['findings'][0]['issue_id'])
class InputProvenance(unittest.TestCase):
    setUp=helpers.Evidence.setUp;load=helpers.Evidence.load
    def test_kind_preserved(self):
        self.manifest['run_kind']='controlled_fixture';self.assertEqual(self.load().get('run_kind'),'controlled_fixture')
    def test_invalid_run_kind_rejected(self):
        self.manifest['run_kind']='fake-live'
        with self.assertRaises(ValueError):self.load()
if __name__=='__main__':unittest.main()
