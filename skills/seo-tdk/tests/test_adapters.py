import hashlib,json,tempfile
from pathlib import Path
from support import TdkTest,URL
from test_context import context
class AdapterTests(TdkTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.html=b'<html><head><title>SOLV | BingX</title></head><body>SOLV Project Details</body></html>'
        self.proof=self.save('page.html',self.html)
        self.row={'url':URL,'snapshot_id':'dom1','document_sha256':self.proof['sha256'],'captured_at':'2026-09-17T00:00:00Z','source':'browser DOM','representation':'rendered_html','readiness':'ready','evidence':self.proof}
    def save(self,name,data):
        (self.root/name).write_bytes(data);return {'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    def load(self,rows=None,**kw):
        p=self.root/'manifest.json';p.write_text(json.dumps({'schema_version':1,'captures':rows if rows is not None else [self.row],**kw}))
        return self.module('adapters').load_manifest(p)
    def test_load_actual_html_no_inline_metadata_override(self):
        self.row['fields']={'titles':[{'value':'Fake'}]};r=self.load()
        self.assertEqual(r['captures'][0]['fields']['titles'][0]['value'],'SOLV | BingX')
    def test_body_hash_failure_is_gap_not_success(self):
        (self.root/'page.html').write_text('changed');r=self.load();self.assertEqual(r['captures'][0]['state'],'evidence_error');self.assertNotIn('fields',r['captures'][0]);self.assertTrue(r['gaps'])
    def test_document_binding_required(self):
        self.row['document_sha256']='b'*64;self.assertEqual(self.load()['captures'][0]['state'],'evidence_error')
    def test_missing_source_or_invalid_time_are_gaps(self):
        for key,value in [('source',''),('captured_at','bad')]:
            old=self.row[key];self.row[key]=value;self.assertTrue(self.load()['gaps']);self.row[key]=old
    def test_readiness_cannot_default_to_ready(self):
        del self.row['readiness'];self.assertEqual(self.load()['captures'][0]['state'],'evidence_error')
    def test_failed_capture_is_preserved_to_block_old_success(self):
        self.row['state']='timeout';self.row.pop('evidence');r=self.load();self.assertEqual(r['captures'][0]['state'],'timeout')
    def test_context_file_bound_to_actual_document(self):
        ctx=context(document_sha256=self.proof['sha256']);self.row['context_evidence']=self.save('context.json',json.dumps(ctx).encode())
        r=self.load();self.assertEqual(r['captures'][0]['context']['facts'][0]['value'],'SOLV')
    def test_external_fact_document_loaded_with_hash(self):
        ctx=context(document_sha256=self.proof['sha256']);f=ctx['facts'][0];f.update(origin='route_registry',document_evidence=self.save('route.txt',b'route SOLV'),quote='route SOLV')
        self.row['context_evidence']=self.save('ctx.json',json.dumps(ctx).encode());r=self.load();self.assertEqual(r['captures'][0]['context']['facts'][0]['document']['text'],'route SOLV')
    def test_inline_external_document_cannot_bypass_file_proof(self):
        ctx=context(document_sha256=self.proof['sha256']);ctx['facts'][0].update(origin='route_registry',document={'text':'fake','sha256':'a'*64})
        self.row['context_evidence']=self.save('ctx.json',json.dumps(ctx).encode());r=self.load();self.assertTrue(r['gaps']);self.assertFalse(r['captures'][0].get('context'))
    def test_bad_context_does_not_hide_valid_html(self):
        self.row['context_evidence']={'path':'missing','bytes':1,'sha256':'a'*64};r=self.load();self.assertEqual(len(r['captures']),1);self.assertTrue(r['gaps'])
    def test_manifest_version_or_wrong_shape_rejected(self):
        with self.assertRaises(ValueError):self.load(schema_version=99)
        with self.assertRaises(ValueError):self.load(rows='oops')
    def test_evidence_escape_rejected(self):
        self.row['evidence']={**self.proof,'path':'../page.html'};self.assertEqual(self.load()['captures'][0]['state'],'evidence_error')
    def test_corrupt_latest_attempt_preserved_so_old_success_cannot_hide_it(self):
        newer={**self.row,'snapshot_id':'new','captured_at':'2026-09-17T00:30:00Z','evidence':{**self.proof,'sha256':'b'*64}}
        r=self.load([self.row,newer]);self.assertEqual(len(r['captures']),2);self.assertEqual(r['captures'][1]['state'],'evidence_error')
