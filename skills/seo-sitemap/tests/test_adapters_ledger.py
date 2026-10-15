import hashlib
import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from support import AuditTest, xml, AT

ROOT='https://bingx.com/sitemap.xml'
PAGE='https://bingx.com/en'

class AdaptersLedgerTests(AuditTest):
    def test_ledger_normalizes_timezone_before_ordering_runs(self):
        store=self.module('ledger').Ledger(self.base/'issues.sqlite');self.addCleanup(store.close)
        newer=self.finding();newer['evidence']=[{'status':410}]
        store.record(self.result([newer],'2026-09-16T15:00:00+08:00'))
        store.record(self.result([self.finding()],'2026-09-16T10:00:00+08:00'))
        row=store.issues()[0]
        self.assertEqual(row['first_reported_at'],'2026-09-16T02:00:00Z')
        self.assertEqual(row['last_reported_at'],'2026-09-16T07:00:00Z')

    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name)

    def inventory(self):
        path=self.base/'inventory.sqlite'
        db=sqlite3.connect(path)
        db.executescript('''CREATE TABLE meta(key TEXT,value TEXT);INSERT INTO meta VALUES('schema_version','1');
        CREATE TABLE tasks(url TEXT,kind TEXT);
        CREATE TABLE fetches(id INTEGER PRIMARY KEY,run_id TEXT,url TEXT,status INTEGER,error TEXT,headers TEXT,evidence TEXT,checked_at TEXT);
        CREATE TABLE checks(id INTEGER PRIMARY KEY,url TEXT,run_id TEXT,checked_at TEXT,status INTEGER,details TEXT);''')
        body=xml([PAGE]); file=self.base/'body.xml'; file.write_bytes(body)
        evidence={'path':str(file),'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}
        db.execute('INSERT INTO tasks VALUES(?,?)',(ROOT,'sitemap'))
        db.execute('INSERT INTO fetches VALUES(1,?,?,?,?,?,?,?)',('run',ROOT,200,None,'{}',json.dumps(evidence),AT))
        db.commit(); db.close()
        return path,file

    def test_adapter_reads_sqlite_and_verified_evidence_without_writing(self):
        path,file=self.inventory(); before=path.read_bytes()
        data=self.module('adapters').from_inventory(path)
        self.assertEqual(data['documents'][0]['body'],file.read_bytes())
        self.assertEqual(data['documents'][0]['url'],ROOT)
        self.assertEqual(path.read_bytes(),before)

    def test_tampered_evidence_is_not_used_as_site_failure(self):
        path,file=self.inventory(); file.write_bytes(b'<html>fake</html>')
        data=self.module('adapters').from_inventory(path)
        self.assertEqual(data['documents'][0]['error'],'evidence_hash_mismatch')
        self.assertNotIn('body',data['documents'][0])

    def test_evidence_path_outside_inventory_directory_is_rejected(self):
        path,file=self.inventory()
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('UPDATE fetches SET evidence=?',(json.dumps({'path':'/etc/hosts','sha256':'irrelevant','bytes':0}),))
        data=self.module('adapters').from_inventory(path)
        self.assertEqual(data['documents'][0]['error'],'evidence_path_outside_inventory')

    def test_latest_failed_fetch_wins_over_last_success(self):
        path,file=self.inventory()
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('INSERT INTO fetches VALUES(2,?,?,?,?,?,?,?)',('run2',ROOT,None,'TimeoutError',None,None,'2026-09-16T11:00:00Z'))
        data=self.module('adapters').from_inventory(path)
        self.assertEqual(len(data['documents']),1)
        self.assertEqual(data['documents'][0]['error'],'TimeoutError')

    def test_unsupported_schema_is_rejected_before_read(self):
        path,file=self.inventory()
        with closing(sqlite3.connect(path)) as db, db: db.execute("UPDATE meta SET value='99'")
        mod=self.module('adapters')
        with self.assertRaisesRegex(ValueError,'schema'):mod.from_inventory(path)

    def test_bad_intent_types_and_conflicting_duplicate_rows_are_rejected(self):
        mod=self.module('adapters')
        for rows in [[{'url':PAGE,'should_index':'false'}],[{'url':PAGE,'published':True},{'url':PAGE,'published':False}]]:
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):mod.validate_expected({'source_id':'cms','kind':'cms','coverage':'complete','scope_roots':[ROOT],'captured_at':AT,'rows':rows})

    def test_expected_secret_url_rejected_without_value_in_error(self):
        mod=self.module('adapters')
        with self.assertRaises(ValueError) as raised:
            mod.validate_expected({'source_id':'cms','kind':'cms','coverage':'complete','scope_roots':[ROOT],'captured_at':AT,'rows':[{'url':'https://bingx.com/?token=secret123'}]})
        self.assertNotIn('secret123',str(raised.exception))

    def finding(self):
        return {'id':'issue1','rule':'sitemap_http_missing','url':PAGE,'category':'remove','certainty':'confirmed','observed_at':AT,'evidence':[{'status':404}]}

    def result(self,findings,at=AT):
        return {'schema_version':1,'skill':'002-sitemap','at':at,'findings':findings,'coverage':{'sitemap_set_read_complete':False}}

    def test_same_run_is_idempotent_and_same_issue_keeps_first_seen(self):
        store=self.module('ledger').Ledger(self.base/'issues.sqlite');self.addCleanup(store.close)
        first=store.record(self.result([self.finding()]))
        repeat=store.record(self.result([self.finding()]))
        self.assertEqual(first['run_id'],repeat['run_id'])
        self.assertTrue(repeat['idempotent'])
        store.record(self.result([self.finding()],'2026-09-23T10:00:00Z'))
        rows=store.issues()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['first_reported_at'],AT)
        self.assertEqual(rows[0]['last_reported_at'],'2026-09-23T10:00:00Z')
        self.assertEqual(rows[0]['observation_count'],2)

    def test_missing_from_new_run_never_closes_existing_issue(self):
        store=self.module('ledger').Ledger(self.base/'issues.sqlite');self.addCleanup(store.close)
        store.record(self.result([self.finding()]))
        store.record(self.result([],'2026-09-23T10:00:00Z'))
        self.assertEqual(store.issues()[0]['status'],'open')
        self.assertFalse(store.issues()[0]['seen_in_latest_run'])

    def test_older_run_does_not_replace_newer_problem_payload(self):
        store=self.module('ledger').Ledger(self.base/'issues.sqlite');self.addCleanup(store.close)
        newer=self.finding();newer['evidence']=[{'status':410}]
        store.record(self.result([newer],'2026-09-23T10:00:00Z'))
        store.record(self.result([self.finding()]))
        self.assertEqual(store.issues()[0]['finding']['evidence'],[{'status':410}])

    def test_malformed_run_is_atomic(self):
        store=self.module('ledger').Ledger(self.base/'issues.sqlite');self.addCleanup(store.close)
        with self.assertRaises(ValueError):store.record(self.result([self.finding(),{'url':PAGE}]))
        self.assertEqual(store.issues(),[])
