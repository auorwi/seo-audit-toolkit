import hashlib
import json
import sqlite3
import tempfile
import subprocess
import sys
from pathlib import Path
from support import RenderingTest,ROOT
from test_readiness import URL

AT='2026-09-17T00:01:00Z'
class InventoryBaselineTests(RenderingTest):
    def test_prepare_cli_creates_importable_manifest(self):
        script=ROOT/'scripts/prepare_baseline.py';self.assertTrue(script.is_file(),'尚未实现baseline CLI')
        bindings=self.base/'bindings.json';bindings.write_text(json.dumps([self.binding]))
        run=subprocess.run([sys.executable,str(script),'--inventory',str(self.db),'--bindings',str(bindings),'--output',str(self.base/'cli'),'--at',AT],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertTrue((self.base/'cli/manifest.json').is_file())

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
        self.db=self.base/'inventory.sqlite'
        with sqlite3.connect(self.db) as db:
            db.executescript("CREATE TABLE meta(key TEXT,value TEXT);INSERT INTO meta VALUES('schema_version','1');CREATE TABLE fetches(id INTEGER,run_id TEXT,url TEXT,status INTEGER,error TEXT,headers TEXT,evidence TEXT,checked_at TEXT);")
        self.body=b'<head><title>Initial</title></head><main>Content</main>'
        (self.base/'body.html').write_bytes(self.body)
        self.proof={'path':'body.html','bytes':len(self.body),'sha256':hashlib.sha256(self.body).hexdigest()}
        self.binding={'url':URL,'navigation_id':'nav1','entry_mode':'direct'}
        self.insert()

    def insert(self,id=1,status=200,error=None,time='2026-09-17T00:00:00Z',headers=None):
        with sqlite3.connect(self.db) as db:
            db.execute('INSERT INTO fetches VALUES(?,?,?,?,?,?,?,?)',(id,'run1',URL,status,error,json.dumps(headers or {'content-type':'text/html'}),json.dumps(self.proof),time))

    def prepare(self,**kw):
        return self.module('baseline').prepare_inventory(self.db,[self.binding],self.base/'out',at=AT,**kw)

    def test_import_copies_verified_bytes_and_labels_independent_http(self):
        result=self.prepare();self.assertEqual(result['gaps'],[])
        parsed=self.module('adapters').load_manifest(self.base/'out/manifest.json')
        self.assertEqual(parsed['snapshots'][0]['title'],'Initial')
        self.assertEqual(parsed['snapshots'][0].get('baseline_relation'),'independent_http')
        self.assertEqual((self.base/'out'/result['snapshots'][0]['evidence']['path']).read_bytes(),self.body)

    def test_latest_failure_is_not_hidden_by_old_success(self):
        self.insert(2,None,'timeout','2026-09-17T00:00:30Z')
        result=self.prepare();self.assertEqual(result['snapshots'],[]);self.assertTrue(result['gaps'])

    def test_non_html_response_is_not_initial_document(self):
        self.insert(2,200,None,'2026-09-17T00:00:30Z',{'content-type':'application/json'})
        result=self.prepare();self.assertEqual(result['snapshots'],[]);self.assertTrue(result['gaps'])

    def test_redirect_response_is_not_final_html(self):
        self.insert(2,302,None,'2026-09-17T00:00:30Z')
        self.assertEqual(self.prepare()['snapshots'],[])

    def test_tampered_body_is_gap(self):
        (self.base/'body.html').write_bytes(b'changed')
        result=self.prepare();self.assertEqual(result['snapshots'],[]);self.assertTrue(result['gaps'])

    def test_stale_or_future_capture_cannot_be_current_baseline(self):
        result=self.prepare(max_age_hours=0.001);self.assertEqual(result['snapshots'],[])
        with tempfile.TemporaryDirectory() as other:
            self.insert(2,200,None,'2026-09-18T00:00:00Z')
            result=self.module('baseline').prepare_inventory(self.db,[self.binding],Path(other)/'out',at=AT)
            self.assertEqual(result['snapshots'],[])

    def test_existing_output_not_overwritten(self):
        self.prepare();before=(self.base/'out/manifest.json').read_bytes()
        with self.assertRaises(ValueError):self.prepare()
        self.assertEqual((self.base/'out/manifest.json').read_bytes(),before)

    def test_empty_bindings_rejected_before_writing(self):
        with self.assertRaises(ValueError):self.module('baseline').prepare_inventory(self.db,[],self.base/'out',at=AT)
        self.assertFalse((self.base/'out').exists())
