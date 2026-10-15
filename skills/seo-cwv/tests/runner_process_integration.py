"""Real process-group cleanup; no browser or external website is contacted."""
import tempfile,json,sys,os,signal,time,threading,unittest
from pathlib import Path
from unittest.mock import patch
from support import CWVTest

class ProcessTests(CWVTest):
    def exercise(self,interrupt):
        m=self.module('runner')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);child=root/'child.py';grand=root/'grand.py'
            grand.write_text("import signal,time,pathlib,sys\nmarker=pathlib.Path(sys.argv[1])\ndef stop(*args):\n marker.write_text('SIGTERM observed in grandchild')\n raise SystemExit(0)\nsignal.signal(signal.SIGTERM,stop)\npathlib.Path(sys.argv[2]).write_text('ready')\nwhile True:time.sleep(0.05)\n")
            child.write_text("import subprocess,sys,os,pathlib,time,json\np=subprocess.Popen([sys.executable,sys.argv[1],sys.argv[2],sys.argv[3]],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)\npathlib.Path(sys.argv[4]).write_text(json.dumps({'parent':os.getpid(),'grandchild':p.pid}))\nprint('measurement process started',flush=True)\nwhile True:time.sleep(0.05)\n")
            ready=root/'ready';marker=root/'terminated';pids=root/'pids.json';timer=None
            def deliver():
                deadline=time.monotonic()+5
                while not ready.exists() and time.monotonic()<deadline:time.sleep(.02)
                if ready.exists():os.kill(os.getpid(),signal.SIGINT)
            try:
                with patch.object(m,'invocation',return_value=[sys.executable,str(child),str(grand),str(marker),str(ready),str(pids)]):
                    if interrupt:
                        timer=threading.Timer(.1,deliver);timer.start()
                        with self.assertRaises(KeyboardInterrupt):m.run_lhci_cell(root/'cell',{},'/runtime','/hook',{},timeout_seconds=8)
                    else:m.run_lhci_cell(root/'cell',{},'/runtime','/hook',{},timeout_seconds=.7)
                deadline=time.monotonic()+2
                while not marker.exists() and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(marker.exists(),'Grandchild must receive termination, not just its launcher')
                result=json.loads((root/'cell/cell.json').read_text());self.assertEqual(result['interrupted'],interrupt);self.assertEqual(result['timed_out'],not interrupt);self.assertIn('measurement process started',(root/'cell/collect.stdout.txt').read_text())
            finally:
                if timer:timer.cancel();timer.join(timeout=6)
                if pids.exists():
                    for pid in json.loads(pids.read_text()).values():
                        try:os.kill(pid,signal.SIGKILL)
                        except ProcessLookupError:pass
    def test_actual_timeout_stops_descendant(self):self.exercise(False)
    def test_actual_interrupt_stops_descendant_and_saves_logs(self):self.exercise(True)
if __name__=='__main__':unittest.main()
