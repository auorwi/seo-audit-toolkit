import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path
from support import RoutingTest, AT
from test_audit import A,B,response

class RoutingAdapterTests(RoutingTest):
    def test_nonobject_saved_navigation_is_rejected_as_evidence_gap(self):
        proof=self.evidence('navigation.json',b'[]')
        nav={'from_url':A,'to_url':B,'entry_mode':'direct','source':'browser','checked_at':AT,'evidence':proof}
        try:result=self.module('adapters').load_manifest(self.manifest(navigation=[nav]))
        except AttributeError:self.fail('Nonobject saved navigation crashed instead of producing an evidence gap')
        self.assertEqual(result['navigation'],[]);self.assertTrue(result['gaps'])

    def test_navigation_claim_must_match_saved_structured_event(self):
        actual={'from_url':A,'to_url':B,'entry_mode':'direct','source':'browser','checked_at':AT}
        proof=self.evidence('event.json',json.dumps(actual).encode())
        claim={**actual,'to_url':'https://bingx.com/en/login','evidence':proof}
        result=self.module('adapters').load_manifest(self.manifest(navigation=[claim]))
        self.assertEqual(result['navigation'],[]);self.assertTrue(result['gaps'])

    def test_equivalence_claim_must_match_saved_comparison(self):
        actual={'source_url':A,'target_url':B,'result':'different','source_sha256':'a','target_sha256':'b','source':'reviewer','checked_at':AT}
        proof=self.evidence('comparison.json',json.dumps(actual).encode())
        claim={**actual,'result':'equivalent','evidence':proof}
        result=self.module('adapters').load_manifest(self.manifest(equivalences=[claim]))
        self.assertEqual(result['equivalences'],[]);self.assertTrue(result['gaps'])

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)

    def evidence(self,name,body):
        path=self.base/name;path.write_bytes(body)
        return {'path':name,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}

    def manifest(self,**kw):
        data={'schema_version':1,'records':[],**kw};path=self.base/'manifest.json'
        path.write_text(json.dumps(data));return path

    def stored(self,row,name):
        row=dict(row);row['evidence']=self.evidence(name,row.pop('body'));return row

    def test_actual_hash_and_quote_required_for_semantic_fact(self):
        evidence=self.evidence('dom.html',b'<main><h1>BTC</h1></main>')
        fact={'url':A,'entity':'BTC','quote':'BTC','selector':'main h1','source':'browser','checked_at':AT,'evidence':evidence}
        result=self.module('adapters').load_manifest(self.manifest(facts=[fact]))
        self.assertEqual(result['facts'][0]['entity'],'BTC')
        self.assertEqual(result['facts'][0]['evidence_verification'],'hash_and_quote')

    def test_unmatched_quote_is_gap_not_entity_proof(self):
        evidence=self.evidence('dom.html',b'<main><h1>ETH</h1></main>')
        fact={'url':A,'entity':'BTC','quote':'BTC','selector':'main h1','source':'browser','checked_at':AT,'evidence':evidence}
        result=self.module('adapters').load_manifest(self.manifest(facts=[fact]))
        self.assertEqual(result['facts'],[]);self.assertTrue(result['gaps'])

    def test_tampered_semantic_evidence_does_not_enter_audit(self):
        evidence=self.evidence('dom.html',b'<h1>BTC</h1>');(self.base/'dom.html').write_bytes(b'changed')
        result=self.module('adapters').load_manifest(self.manifest(facts=[{'url':A,'entity':'BTC','quote':'BTC','selector':'h1','source':'browser','checked_at':AT,'evidence':evidence}]))
        self.assertEqual(result['facts'],[])
        self.assertEqual(result['gaps'][0]['reason'],'evidence_integrity_mismatch')

    def test_navigation_keeps_proof_and_entry_path_separate_from_http(self):
        nav={'from_url':A,'to_url':'https://bingx.com/en/login','entry_mode':'direct','source':'browser','checked_at':AT}
        nav['evidence']=self.evidence('navigation.json',json.dumps(nav).encode())
        result=self.module('adapters').load_manifest(self.manifest(navigation=[nav]))
        self.assertEqual(result['records'],[]);self.assertEqual(result['navigation'][0]['entry_mode'],'direct')

    def test_navigation_missing_proof_not_treated_as_executed(self):
        nav={'from_url':A,'to_url':'https://bingx.com/en/login','source':'browser','checked_at':AT}
        result=self.module('adapters').load_manifest(self.manifest(navigation=[nav]))
        self.assertEqual(result['navigation'],[]);self.assertTrue(result['gaps'])

    def test_equivalence_assessment_has_verified_local_report_but_separate_page_hashes(self):
        row={'source_url':A,'target_url':B,'result':'equivalent','source':'reviewer','checked_at':AT,'source_sha256':'sourcehash','target_sha256':'targethash'}
        row['evidence']=self.evidence('comparison.json',json.dumps(row).encode())
        result=self.module('adapters').load_manifest(self.manifest(equivalences=[row]))
        self.assertEqual(result['equivalences'][0]['source_sha256'],'sourcehash')
        self.assertEqual(result['equivalences'][0]['result'],'equivalent')

    def test_unknown_equivalence_result_rejected(self):
        row={'source_url':A,'target_url':B,'result':'maybe','source':'reviewer','checked_at':AT}
        row['evidence']=self.evidence('comparison.json',json.dumps(row).encode())
        result=self.module('adapters').load_manifest(self.manifest(equivalences=[row]))
        self.assertEqual(result['equivalences'],[]);self.assertTrue(result['gaps'])

    def test_inventory_reads_canonical_targets_beyond_http_redirects(self):
        rows=[self.stored(response(target=B),'a.body'),self.stored(response(url=B,target=B),'b.body')]
        path=self.base/'inventory.sqlite';db=sqlite3.connect(path)
        db.executescript("CREATE TABLE meta(key TEXT,value TEXT); INSERT INTO meta VALUES('schema_version','1'); CREATE TABLE fetches(id INTEGER PRIMARY KEY,run_id TEXT,url TEXT,status INTEGER,error TEXT,headers TEXT,evidence TEXT,checked_at TEXT,headers_all TEXT,captured_header_names TEXT);")
        for i,row in enumerate(rows):
            db.execute('INSERT INTO fetches VALUES(?,?,?,?,?,?,?,?,?,?)',(i+1,'run',row['url'],200,None,'{}',json.dumps(row['evidence']),AT,json.dumps(row['headers']),json.dumps(row['captured_header_names'])))
        db.commit();db.close();before=path.read_bytes()
        result=self.module('adapters').load_inventory(path,[A])
        self.assertEqual({r['url'] for r in result['records']},{A,B})
        self.assertEqual(path.read_bytes(),before)

    def test_link_headers_survive_supplement_import(self):
        row=self.stored(response(headers=[('content-type','text/html'),('link','<'+B+'>; rel=canonical')]),'a.body')
        result=self.module('adapters').load_manifest(self.manifest(records=[row]))
        self.assertIn(('link','<'+B+'>; rel=canonical'),result['records'][0]['headers'])

    def test_platform_canonical_keeps_independent_evidence(self):
        row={'url':A,'canonical':B,'engine':'google','kind':'index_snapshot','source':'gsc','checked_at':AT}
        row['evidence']=self.evidence('inspection.json',json.dumps(row).encode())
        result=self.module('adapters').load_manifest(self.manifest(engine_observations=[row]))
        self.assertEqual(result['engine_observations'][0]['canonical'],B)
