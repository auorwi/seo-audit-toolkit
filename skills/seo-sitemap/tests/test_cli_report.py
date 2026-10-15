import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from support import AuditTest, ROOT, xml, AT

SITEMAP='https://bingx.com/sitemap.xml'
PAGE='https://bingx.com/en'

class CLITests(AuditTest):
    def test_invalid_page_shape_is_rejected_instead_of_silently_passing(self):
        for details in [{'noindex_observed':'false'},{'canonicals':'https://bingx.com/en'},{'robots_directives':{'robots':'noindex'}}]:
            with self.subTest(details=details):
                self.input['pages'][PAGE]['details']=details
                result=self.cli()
                self.assertEqual(result.returncode,1,result.stderr)

    def test_nonfinite_freshness_limit_is_rejected(self):
        for value in ['nan','inf','-1']:
            with self.subTest(value=value):
                self.assertEqual(self.cli('--max-age-hours',value).returncode,1)

    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.base=Path(temp.name); self.output=self.base/'report with spaces'; self.state=self.base/'state'
        self.file=self.base/'input.json'
        body=xml([PAGE]); evidence=self.base/'leaf.xml';evidence.write_bytes(body)
        page_body=b'<html><title>Not Found</title></html>'; pagefile=self.base/'page.html';pagefile.write_bytes(page_body)
        self.input={'documents':[{'url':SITEMAP,'checked_at':AT,'status':200,'evidence':{'path':str(evidence),'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}}],
            'pages':{PAGE:{'url':PAGE,'checked_at':AT,'status':404,'details':{},'evidence':{'path':str(pagefile),'sha256':hashlib.sha256(page_body).hexdigest(),'bytes':len(page_body)}}}}

    def cli(self,*args):
        script=ROOT/'scripts'/'audit_sitemap.py'
        self.assertTrue(script.is_file(),'尚未实现独立CLI')
        self.file.write_text(json.dumps(self.input))
        return subprocess.run([sys.executable,str(script),'--manifest',str(self.file),'--state',str(self.state),'--output',str(self.output),
            '--root',SITEMAP,'--at',AT,*args],capture_output=True,text=True,timeout=30)

    def test_cli_generates_action_lists_and_keeps_id_on_repeat(self):
        result=self.cli();self.assertEqual(result.returncode,0,result.stderr)
        first=json.loads((self.output/'report.json').read_text())
        self.assertIn('sitemap_http_missing',{r['rule'] for r in first['findings']})
        with (self.output/'remove.csv').open(encoding='utf-8-sig') as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(rows[0]['url'],PAGE)
        self.assertEqual(len(rows),1)
        self.assertEqual(first['coverage']['fresh_page_checks'],1)
        again=self.cli();self.assertEqual(again.returncode,0,again.stderr)
        second=json.loads((self.output/'report.json').read_text())
        self.assertTrue(second['ledger']['idempotent'])
        self.assertEqual(first['findings'][0]['id'],second['findings'][0]['id'])
        self.assertEqual(len(json.loads((self.output/'issue-history.json').read_text())),1)
        for category in ('add','remove','retarget','repair','confirm'):
            self.assertTrue((self.output/(category+'.csv')).is_file())

    def test_unchecked_page_is_partial_with_pending_list(self):
        self.input['pages']={}
        result=self.cli();self.assertEqual(result.returncode,2,result.stderr)
        report=json.loads((self.output/'report.json').read_text())
        self.assertEqual(report['coverage']['fresh_page_checks'],0)
        with (self.output/'pending.csv').open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
        self.assertIn(PAGE,{r['url'] for r in rows})
        self.assertIsNone(report['coverage']['expected_indexable_urls'])

    def test_invalid_expected_input_fails_without_creating_success_report(self):
        exp=self.base/'expected.json';exp.write_text('{"rows": []}')
        result=self.cli('--expected',str(exp))
        self.assertEqual(result.returncode,1)
        self.assertFalse((self.output/'report.json').exists())

    def test_modified_manifest_page_evidence_cannot_create_confirmed_site_error(self):
        (self.base/'page.html').write_text('changed')
        result=self.cli();self.assertEqual(result.returncode,2,result.stderr)
        report=json.loads((self.output/'report.json').read_text())
        self.assertNotIn('sitemap_http_missing',{r['rule'] for r in report['findings']})

    def test_locked_state_refuses_second_writer(self):
        import fcntl
        self.state.mkdir()
        with (self.state/'.sitemap.lock').open('w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            result=self.cli()
            self.assertEqual(result.returncode,1)
            self.assertIn('locked',result.stderr)

    def test_snapshot_csv_escapes_formula_cells(self):
        mod=self.module('report')
        text=mod.csv_text([{'url':'=HYPERLINK("bad")'}],['url'])
        row=next(csv.DictReader(text.lstrip('\ufeff').splitlines()))
        self.assertTrue(row['url'].startswith("'="))

    def test_manifest_normalizes_header_case_and_sanitizes_secrets(self):
        self.input['pages'][PAGE]['status']=200
        self.input['pages'][PAGE]['details']={'headers':{'X-Robots-Tag':'noindex','Set-Cookie':'account=private123'}}
        result=self.cli();self.assertEqual(result.returncode,0,result.stderr)
        report=(self.output/'report.json').read_text()
        self.assertNotIn('private123',report)
        self.assertIn('sitemap_noindex_conflict',report)
