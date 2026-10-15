import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from support import SemanticsTest,URL,AT

class NuRunnerTests(SemanticsTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
        self.html=self.base/'sample ; not-a-command.html';self.html.write_text('<!doctype html><html lang="en"><title>Example</title><main><h1>Hello</h1></main></html>')
        self.fake=self.base/'fixture_nu.py'
        self.write_fake("print(json.dumps({'messages':[]}))")

    def write_fake(self,body):
        self.fake.write_text('import sys,json,time\nif "--version" in sys.argv:\n print("fixture-nu-1")\n raise SystemExit(0)\n'+body+'\n')

    def run_nu(self,**kw):
        return self.module('nu_runner').run_nu([sys.executable,str(self.fake)],self.html,URL,self.base/'report',at=AT,**kw)

    def test_success_binds_copied_input_and_actual_checker_output(self):
        result=self.run_nu();self.assertEqual(result['state'],'completed');self.assertEqual(result['checker_version'],'fixture-nu-1')
        expected=hashlib.sha256(self.html.read_bytes()).hexdigest()
        self.assertEqual(result['document_sha256'],expected);self.assertEqual(result['input_sha256'],expected)
        self.assertEqual((self.base/'report/input.html').read_bytes(),self.html.read_bytes())
        saved=json.loads((self.base/'report/nu.capture.json').read_text());self.assertEqual(saved['payload'],{'messages':[]})
        self.assertEqual(self.module('tool_reports').normalize_tool_report(result,at=AT)['status'],'usable')

    def test_document_errors_exit_one_are_completed_checker_not_system_failure(self):
        self.write_fake("print(json.dumps({'messages':[{'type':'error','message':'Missing title'}]}));raise SystemExit(1)")
        result=self.run_nu();self.assertEqual(result['state'],'completed')
        parsed=self.module('tool_reports').normalize_tool_report(result,at=AT)
        self.assertEqual(parsed['observations'][0]['category'],'html_conformance_error')

    def test_input_is_passed_as_one_argv_argument_not_shell_code(self):
        self.write_fake("assert sys.argv[-1].endswith('/input.html');assert '--stdout' in sys.argv;assert sys.argv[sys.argv.index('--format')+1]=='json';print(json.dumps({'messages':[]}))")
        self.assertEqual(self.run_nu()['state'],'completed')

    def test_timeout_does_not_produce_empty_success(self):
        self.write_fake('time.sleep(2)')
        result=self.run_nu(timeout=0.05);self.assertEqual(result['state'],'timeout')
        self.assertEqual(self.module('tool_reports').normalize_tool_report(result,at=AT)['status'],'evidence_gap')

    def test_invalid_json_is_failed_checker(self):
        self.write_fake('print("not-json")')
        result=self.run_nu();self.assertEqual(result['state'],'failed');self.assertTrue(result['error'])

    def test_missing_executable_returns_unavailable_with_evidence(self):
        result=self.module('nu_runner').run_nu([str(self.base/'missing')],self.html,URL,self.base/'report',at=AT)
        self.assertEqual(result['state'],'unavailable');self.assertTrue((self.base/'report/nu.capture.json').exists())

    def test_process_exit_two_cannot_look_like_completed_check(self):
        self.write_fake("print(json.dumps({'messages':[]}));raise SystemExit(2)")
        self.assertEqual(self.run_nu()['state'],'failed')

    def test_existing_report_not_overwritten(self):
        self.run_nu();before=(self.base/'report/nu.capture.json').read_bytes()
        with self.assertRaises(ValueError):self.run_nu()
        self.assertEqual((self.base/'report/nu.capture.json').read_bytes(),before)

    def test_nonpositive_timeout_rejected(self):
        with self.assertRaises(ValueError):self.run_nu(timeout=0)
        self.assertFalse((self.base/'report').exists())

    def test_input_size_limit_before_external_checker(self):
        self.html.write_bytes(b'x'*8_000_001)
        with self.assertRaises(ValueError):self.run_nu()
        self.assertFalse((self.base/'report').exists())
