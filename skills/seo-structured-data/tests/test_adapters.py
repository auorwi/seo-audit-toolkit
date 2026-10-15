import hashlib,json,tempfile
from pathlib import Path
from support import StructuredTest,URL
from test_vocabulary import vocabulary
class AdapterTests(StructuredTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.html=b'<html><head><script type="application/ld+json">{"@context":"https://schema.org","@type":"Offer","price":"$1"}</script></head><body>BTC $1</body></html>'
        self.proof=self.save('page.html',self.html)
        self.row={'url':URL,'snapshot_id':'dom1','document_sha256':self.proof['sha256'],'captured_at':'2026-09-17T01:00:00Z','source':'actual browser fixture','representation':'rendered_html','readiness':'ready','entry_mode':'direct','evidence':self.proof}
    def save(self,name,data):
        data=data if isinstance(data,bytes) else json.dumps(data).encode();(self.root/name).write_bytes(data);return {'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    def load(self,**kw):
        p=self.root/'manifest.json';p.write_text(json.dumps({'schema_version':1,'captures':[self.row],**kw}));return self.module('adapters').load_manifest(p)
    def test_parses_actual_html_and_ignores_inline_fake_entities(self):
        self.row['entities']=[{'types':['Fake']}];r=self.load();self.assertEqual(r['captures'][0]['jsonld']['entities'][0]['types'],['Offer'])
    def test_bad_body_hash_becomes_preserved_failed_attempt(self):
        (self.root/'page.html').write_text('bad');r=self.load();self.assertEqual(r['captures'][0]['state'],'evidence_error');self.assertTrue(r['gaps'])
    def test_missing_readiness_does_not_default_to_ready(self):
        del self.row['readiness'];self.assertEqual(self.load()['captures'][0]['state'],'evidence_error')
    def test_visible_text_must_match_capture_identity_and_document(self):
        v={k:self.row[k] for k in ['url','snapshot_id','document_sha256','captured_at','source']};v['visible_text']='BTC $1';self.row['visible_evidence']=self.save('visible.json',v)
        r=self.load();self.assertEqual(r['captures'][0]['visible_text'],'BTC $1')
        v['document_sha256']='a'*64;self.row['visible_evidence']=self.save('bad-visible.json',v);r=self.load();self.assertNotIn('visible_text',r['captures'][0]);self.assertTrue(r['gaps'])
    def test_external_result_bound_to_real_html_not_only_record_claim(self):
        from test_embedded import record
        e=record(document_sha256=self.proof['sha256'],input_sha256=self.proof['sha256']);self.row['extraction_evidence']=self.save('extruct.json',e)
        r=self.load();self.assertEqual(r['captures'][0]['extruct']['document_sha256'],self.proof['sha256'])
    def test_optional_missing_extraction_file_does_not_hide_jsonld(self):
        self.row['extraction_evidence']={'path':'missing','sha256':'a'*64,'bytes':1};r=self.load();self.assertTrue(r['gaps']);self.assertEqual(len(r['captures'][0]['jsonld']['entities']),1)
    def test_vocabulary_snapshot_has_file_proof_and_source(self):
        r=self.load(vocabulary={'evidence':self.save('vocab.json',vocabulary()),'source':'https://schema.org/version/latest/schemaorg-current-https.jsonld','retrieved_at':'2026-09-17T01:00:00Z'})
        self.assertIn('Product',r['vocabulary']['terms']['classes']);self.assertTrue(r['vocabulary']['evidence']['sha256'])
    def test_bad_vocabulary_is_gap_not_empty_valid_dictionary(self):
        r=self.load(vocabulary={'evidence':self.save('vocab.json',{}),'source':'https://schema.org/','retrieved_at':'2026-09-17T01:00:00Z'});self.assertIsNone(r['vocabulary']);self.assertTrue(r['gaps'])
    def test_engine_mapping_requires_original_export_proof(self):
        mapping={'url':URL,'engine':'Google','tool':'Search Console','kind':'historical_issue','checked_at':'2026-09-01T00:00:00Z','source':'platform fixture','rule':'rating_number_review','result':'error'}
        row={'evidence':self.save('mapping.json',mapping),'original_evidence':self.save('original.txt',b'Original engine diagnostic fixture')};r=self.load(engine_reports=[row]);self.assertEqual(r['engine_reports'][0]['artifact_sha256'],row['original_evidence']['sha256'])
    def test_missing_original_export_rejects_mapped_engine_record(self):
        r=self.load(engine_reports=[{'evidence':self.save('mapping.json',{'url':URL})}]);self.assertEqual(r['engine_reports'],[]);self.assertTrue(r['gaps'])
    def test_manifest_wrong_shape_rejected(self):
        with self.assertRaises(ValueError):self.load(captures='bad')
        with self.assertRaises(ValueError):self.load(schema_version=99)
    def test_outside_root_evidence_rejected(self):
        self.row['evidence']={**self.proof,'path':'../page.html'};r=self.load();self.assertEqual(r['captures'][0]['state'],'evidence_error')
    def test_failed_internal_attempt_preserves_entry_for_current_selection(self):
        self.row.update(entry_mode='internal',state='http_error')
        self.assertEqual(self.load()['captures'][0].get('entry_mode'),'internal')
    def test_corrupted_internal_attempt_preserves_entry_for_current_selection(self):
        self.row['entry_mode']='internal';(self.root/'page.html').write_text('corrupt')
        self.assertEqual(self.load()['captures'][0].get('entry_mode'),'internal')
    def test_nonobject_engine_row_is_explicit_gap_not_uncaught_crash(self):
        r=self.load(engine_reports=['bad']);self.assertEqual(r['engine_reports'],[]);self.assertTrue(r['gaps'])
