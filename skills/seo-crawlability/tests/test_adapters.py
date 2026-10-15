import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path
from support import CrawlTest, AT
from test_responses import ROOT, PAGE

class AdapterTests(CrawlTest):
    def test_link_refresh_headers_and_capture_policy_survive_shared_adapter(self):
        row=self.record(headers=[['Link','</a>; rel=canonical'],['Refresh','0;url=/b']],captured_header_names=['link','refresh'])
        record=self.module('adapters').load_manifest(self.manifest([row]))['records'][0]
        self.assertEqual(record['headers'],[('link','</a>; rel=canonical'),('refresh','0;url=/b')])
        self.assertEqual(record['captured_header_names'],['link','refresh'])

    def test_inventory_retains_server_request_id_and_local_capture_id(self):
        row=self.record(headers_all=[['cf-ray','edge-request-42']])
        path=self.database([row],modern=True)
        record=self.module('adapters').load_inventory(path,[PAGE])['records'][0]
        self.assertEqual(record['request_id'],'edge-request-42')
        self.assertEqual(record['capture_id'],'test:1')

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)

    def evidence(self,name='page',body=b'<meta name="robots" content="noindex">'):
        path=self.base/(name+'.body');path.write_bytes(body)
        return {'path':str(path),'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}

    def record(self,**kw):
        return {'url':PAGE,'status':200,'checked_at':AT,'headers':[['content-type','text/html']], 'evidence':self.evidence(),**kw}

    def manifest(self,records,**kw):
        path=self.base/'manifest.json'
        path.write_text(json.dumps({'schema_version':1,'records':records,**kw}))
        return path

    def database(self,rows,modern=False):
        path=self.base/'inventory.sqlite';db=sqlite3.connect(path)
        db.executescript("CREATE TABLE meta(key TEXT,value TEXT); INSERT INTO meta VALUES('schema_version','1'); CREATE TABLE fetches(id INTEGER PRIMARY KEY,run_id TEXT,url TEXT,status INTEGER,error TEXT,headers TEXT,evidence TEXT,checked_at TEXT);")
        if modern:db.execute('ALTER TABLE fetches ADD COLUMN headers_all TEXT')
        for idx,row in enumerate(rows):
            data={'id':idx+1,'run_id':'test','url':row['url'],'status':row.get('status'),'error':row.get('error'),
                  'headers':json.dumps(row.get('headers',{})),'evidence':json.dumps(row.get('evidence')),'checked_at':row['checked_at']}
            if modern:data['headers_all']=json.dumps(row['headers_all']) if 'headers_all' in row else None
            db.execute('INSERT INTO fetches('+','.join(data)+') VALUES('+','.join('?' for _ in data)+')',list(data.values()))
        db.commit();db.close();return path

    def test_valid_manifest_loads_verified_body_and_preserves_duplicates(self):
        row=self.record(headers=[['X-Robots-Tag','noindex'],['X-Robots-Tag','nofollow']])
        result=self.module('adapters').load_manifest(self.manifest([row]))
        self.assertEqual(result['records'][0]['body'],b'<meta name="robots" content="noindex">')
        self.assertEqual(result['records'][0]['headers'],[('x-robots-tag','noindex'),('x-robots-tag','nofollow')])
        self.assertTrue(result['records'][0]['header_capture_complete'])

    def test_dictionary_headers_cannot_prove_duplicate_capture(self):
        data=self.module('adapters').load_manifest(self.manifest([self.record(headers={})]))
        self.assertFalse(data['records'][0]['header_capture_complete'])

    def test_tampered_body_is_not_parsed_as_verified_content(self):
        row=self.record();Path(row['evidence']['path']).write_bytes(b'changed')
        result=self.module('adapters').load_manifest(self.manifest([row]))
        self.assertNotIn('body',result['records'][0]);self.assertEqual(result['records'][0]['status'],200)
        self.assertEqual(result['gaps'][0]['reason'],'evidence_integrity_mismatch')

    def test_wrong_size_is_rejected_even_with_matching_hash(self):
        row=self.record();row['evidence']['bytes']=1
        result=self.module('adapters').load_manifest(self.manifest([row]))
        self.assertNotIn('body',result['records'][0]);self.assertTrue(result['gaps'])

    def test_outside_root_and_symlink_body_are_not_read(self):
        with tempfile.TemporaryDirectory() as external:
            secret=Path(external)/'secret';secret.write_bytes(b'secret')
            link=self.base/'link';link.symlink_to(secret)
            for path in [secret,link]:
                row=self.record();row['evidence']['path']=str(path)
                result=self.module('adapters').load_manifest(self.manifest([row]))
                self.assertNotIn('body',result['records'][0])
                self.assertEqual(result['gaps'][0]['reason'],'evidence_outside_root')

    def test_cookie_and_authorization_headers_are_not_propagated(self):
        row=self.record(headers=[['Set-Cookie','SECRET'],['Authorization','SECRET'],['CF-Ray','trace']])
        result=self.module('adapters').load_manifest(self.manifest([row]))
        self.assertNotIn('SECRET',str(result));self.assertEqual(result['records'][0]['request_id'],'trace')

    def test_malformed_timestamps_and_status_fail_input_validation(self):
        mod=self.module('adapters')
        for override in [{'checked_at':'2026-09-16'},{'status':'200'},{'status':True},{'status':999}]:
            with self.subTest(override=override),self.assertRaises(ValueError):
                mod.load_manifest(self.manifest([self.record(**override)]))

    def test_missing_body_and_request_error_do_not_disappear(self):
        row=self.record(status=None,error='TimeoutError');row.pop('evidence')
        result=self.module('adapters').load_manifest(self.manifest([row]))
        self.assertEqual(len(result['records']),1);self.assertEqual(result['records'][0]['error'],'TimeoutError')

    def test_inventory_is_read_only_and_selects_scope_plus_robot_redirects(self):
        records=[self.record(),self.record(url=ROOT,status=301,headers={'location':'/rules.txt'}),
            self.record(url='https://bingx.com/rules.txt',evidence=self.evidence('robots',b'User-agent: *\nAllow: /')),
            self.record(url='https://bingx.com/unselected')]
        path=self.database(records);before=path.read_bytes()
        result=self.module('adapters').load_inventory(path,[PAGE])
        self.assertEqual({r['url'] for r in result['records']},{PAGE,ROOT,'https://bingx.com/rules.txt'})
        self.assertEqual(path.read_bytes(),before)
        self.assertFalse(result['records'][0]['header_capture_complete'])

    def test_inventory_uses_new_header_pairs_over_legacy_lossy_dictionary(self):
        path=self.database([self.record(headers={'x-robots-tag':'nofollow'},headers_all=[['x-robots-tag','noindex'],['x-robots-tag','nofollow']])],modern=True)
        record=self.module('adapters').load_inventory(path,[PAGE])['records'][0]
        self.assertEqual(record['headers'],[('x-robots-tag','noindex'),('x-robots-tag','nofollow')])
        self.assertTrue(record['header_capture_complete'])

    def test_inventory_keeps_old_failures_and_latest_error(self):
        path=self.database([self.record(status=503,checked_at='2026-09-16T10:00:00Z'),self.record(checked_at='2026-09-16T11:00:00Z'),self.record(status=None,error='TimeoutError')])
        result=self.module('adapters').load_inventory(path,[PAGE])
        self.assertEqual([r['status'] for r in result['records']],[503,200,None])

    def test_missing_inventory_does_not_create_database(self):
        path=self.base/'missing.sqlite'
        with self.assertRaises((ValueError,FileNotFoundError,sqlite3.OperationalError)):
            self.module('adapters').load_inventory(path,[PAGE])
        self.assertFalse(path.exists())

    def test_manifest_inline_body_cannot_bypass_evidence_verification(self):
        row=self.record(body='made-up');row.pop('evidence')
        result=self.module('adapters').load_manifest(self.manifest([row]))
        self.assertNotIn('body',result['records'][0]);self.assertTrue(result['gaps'])

    def test_rendered_and_platform_records_are_separate(self):
        row=self.record(mode='rendered')
        obs={'url':PAGE,'engine':'google','kind':'index_snapshot','checked_at':AT,'source':'gsc-export','indexed':True}
        result=self.module('adapters').load_manifest(self.manifest([],rendered=[row],observations=[obs]))
        self.assertEqual(result['records'],[]);self.assertEqual(result['rendered'][0]['mode'],'rendered')
        self.assertEqual(result['observations'][0]['source'],'gsc-export')

    def test_manifest_version_and_observation_provenance_required(self):
        mod=self.module('adapters')
        with self.assertRaises(ValueError):mod.load_manifest(self.manifest([],schema_version=99))
        with self.assertRaises(ValueError):mod.load_manifest(self.manifest([],observations=[{'url':PAGE}]))
