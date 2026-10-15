import tempfile,json,subprocess,signal
from pathlib import Path
from unittest.mock import Mock,patch
from support import CWVTest

class LifecycleTests(CWVTest):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def invoke(self,m):
        # Native process discovery is covered separately and by real detached-child tests.
        with patch.object(m,'owned_process_groups',return_value=([43210],[],[]),create=True),patch.object(m,'live_groups',return_value=set(),create=True):
            return m.run_lhci_cell(self.root/'cell',{'ci':{'collect':{}}},'/runtime','/hook',{},timeout_seconds=1)
    def test_detached_owned_group_selected_unrelated_group_excluded(self):
        m=self.module('runner');self.assertTrue(hasattr(m,'owned_process_groups'))
        rows='PID PPID PGID\n100 1 100\n101 100 100\n102 101 102\n103 102 102\n999 1 999\n'
        with patch.object(m.subprocess,'check_output',return_value=rows):groups,pids,warnings=m.owned_process_groups(100)
        self.assertEqual(set(groups),{100,102});self.assertEqual(pids,[]);self.assertEqual(warnings,[])
    def test_shared_external_group_not_killed_as_group(self):
        m=self.module('runner');self.assertTrue(hasattr(m,'owned_process_groups'))
        rows='PID PPID PGID\n100 1 100\n102 100 77\n77 1 77\n'
        with patch.object(m.subprocess,'check_output',return_value=rows):groups,pids,warnings=m.owned_process_groups(100)
        self.assertNotIn(77,groups);self.assertEqual(pids,[102])
    def test_interrupt_stops_child_and_preserves_logs_then_reraises(self):
        m=self.module('runner');p=Mock(pid=43210,returncode=-15);p.communicate.side_effect=[KeyboardInterrupt(),('partial output','stopped')]
        with patch.object(m.subprocess,'Popen',return_value=p),patch.object(m.os,'killpg') as kill:
            with self.assertRaises(KeyboardInterrupt):self.invoke(m)
        self.assertTrue(kill.called,'Interrupt must terminate the measured process group before releasing the lock');self.assertEqual(kill.call_args_list[0].args,(43210,signal.SIGTERM));self.assertTrue((self.root/'cell/cell.json').exists());self.assertTrue(json.loads((self.root/'cell/cell.json').read_text())['interrupted']);self.assertEqual((self.root/'cell/collect.stdout.txt').read_text(),'partial output')
    def test_timeout_process_exit_race_keeps_evidence(self):
        m=self.module('runner');p=Mock(pid=43210,returncode=0);p.communicate.side_effect=[subprocess.TimeoutExpired('lhci',1),('finished','')]
        with patch.object(m.subprocess,'Popen',return_value=p),patch.object(m.os,'killpg',side_effect=ProcessLookupError):
            r=self.invoke(m)
        self.assertTrue(r['timed_out']);self.assertEqual((self.root/'cell/collect.stdout.txt').read_text(),'finished')
    def test_timeout_escalates_after_grace(self):
        m=self.module('runner');p=Mock(pid=43210,returncode=-9);p.communicate.side_effect=[subprocess.TimeoutExpired('lhci',1),subprocess.TimeoutExpired('lhci',10),('partial','killed')]
        with patch.object(m.subprocess,'Popen',return_value=p),patch.object(m.os,'killpg') as kill:r=self.invoke(m)
        self.assertEqual([c.args[1] for c in kill.call_args_list],[signal.SIGTERM,signal.SIGKILL]);self.assertTrue(r['timed_out'])
