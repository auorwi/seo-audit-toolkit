import json,hashlib,tempfile
from pathlib import Path
from support import CWVTest,AT,URL
from test_lab import lhr,CTX
from test_field import crux
class AdapterTests(CWVTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def proof(self,name,value):
        raw=(json.dumps(value)+'\n').encode();(self.root/name).write_bytes(raw);return {'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    def lab(self):
        p=self.proof('lhr.json',lhr());meta={'run_id':'r1','url':URL,'state':'completed','started_at':AT,'finished_at':AT,'source':'actual pinned LHCI node runner invocation'};mp=self.proof('attempt.json',meta);cp=self.proof('cell.json',{'context':CTX,'attempts':[{**meta,'lhr_evidence':p}]});return {**meta,'lhr_evidence':p,'attempt_evidence':mp,'context_evidence':cp}
    def field(self):
        p=self.proof('crux.json',crux());q=self.proof('query.json',{'source':'crux_api','request':{'url':URL,'formFactor':'PHONE'},'observed_at':AT,'status':200});return {'source':'crux_api','evidence':p,'query_evidence':q}
    def load(self,**kw):
        p=self.root/'manifest.json';p.write_text(json.dumps({'schema_version':1,**kw}));return self.module('adapters').load_manifest(p)
    def test_lhr_parsed_actual_bytes(self):
        row=self.lab();row['metrics']={'LCP':1};self.assertEqual(self.load(lab_runs=[row])['lab_runs'][0]['metrics']['LCP'],3200)
    def test_corrupt_lhr_preserves_failure(self):
        row=self.lab();row['lhr_evidence']['sha256']='a'*64;r=self.load(lab_runs=[row]);self.assertFalse(r['lab_runs'][0]['valid_measurement']);self.assertTrue(r['gaps'])
    def test_context_sha_binding(self):
        row=self.lab();c=json.loads((self.root/'cell.json').read_text());c['attempts'][0]['lhr_evidence']['sha256']='b'*64;row['context_evidence']=self.proof('cell.json',c);self.assertFalse(self.load(lab_runs=[row])['lab_runs'][0]['valid_measurement'])
    def test_attempt_metadata_binding(self):
        row=self.lab();row['url']='https://bingx.com/en/';self.assertFalse(self.load(lab_runs=[row])['lab_runs'][0]['valid_measurement'])
    def test_failed_attempt_without_lhr_kept(self):
        row=self.lab();meta=json.loads((self.root/'attempt.json').read_text());meta['state']='failed';row.update(state='failed',attempt_evidence=self.proof('attempt.json',meta));del row['lhr_evidence'];r=self.load(lab_runs=[row]);self.assertFalse(r['lab_runs'][0]['valid_measurement'])
    def test_crux_actual_field_units(self):self.assertEqual(self.load(field_records=[self.field()])['field_records'][0]['metrics']['CLS'],0.08)
    def test_field_wrong_source_binding(self):
        row=self.field();row['source']='psi_api';self.assertTrue(self.load(field_records=[row])['gaps'])
    def test_query_metadata_not_inline(self):
        row=self.field();row['request']={'url':'https://bingx.com/en/','formFactor':'DESKTOP'};self.assertEqual(self.load(field_records=[row])['field_records'][0]['device'],'PHONE')
    def test_path_escape_gap(self):
        row=self.field();row['evidence']['path']='../outside.json';self.assertTrue(self.load(field_records=[row])['gaps'])
    def test_api_error_preserved(self):
        row=self.field();row['evidence']=self.proof('crux.json',{'error':{'code':429}});self.assertEqual(self.load(field_records=[row])['field_records'][0]['status'],'api_error')
    def test_unsupported_manifest_version(self):
        p=self.root/'manifest.json';p.write_text('{"schema_version":2}')
        with self.assertRaises(ValueError):self.module('adapters').load_manifest(p)
    def test_scope_expectations_kept(self):self.assertEqual(self.load(expected_cells=[{'url':URL,'device':'mobile','minimum_valid_runs':3}])['expected_cells'][0]['url'],URL)
    def test_malformed_record_not_crash(self):self.assertTrue(self.load(field_records=[{'source':'crux_api'}])['gaps'])
    def test_actual_document_diagnostics_loaded(self):self.assertIn('diagnostics',self.load(lab_runs=[self.lab()])['lab_runs'][0])
    def test_http_error_cannot_promote_body_metrics(self):
        row=self.field();q=json.loads((self.root/'query.json').read_text());q['status']=500;row['query_evidence']=self.proof('query.json',q);self.assertEqual(self.load(field_records=[row])['field_records'][0]['status'],'unverified')
    def test_lhr_outside_attempt_time_not_valid(self):
        row=self.lab();raw=lhr();raw['fetchTime']='2020-01-01T00:00:00Z';row['lhr_evidence']=self.proof('lhr.json',raw);c=json.loads((self.root/'cell.json').read_text());c['attempts'][0]['lhr_evidence']=row['lhr_evidence'];row['context_evidence']=self.proof('cell.json',c);self.assertFalse(self.load(lab_runs=[row])['lab_runs'][0]['valid_measurement'])
    def test_missing_authorization_attempt_is_explicit_gap(self):
        p=self.proof('attempt-field.json',{'source':'crux_api','request':{'url':URL,'formFactor':'PHONE'},'observed_at':AT,'state':'authorization_missing','status':None});r=self.load(field_attempts=[p]);self.assertIn('field_authorization_missing',[g['reason'] for g in r['gaps']]);self.assertEqual(r['field_records'],[])
    def test_success_transport_not_fake_missing_auth(self):
        p=self.proof('attempt-field.json',{'source':'psi_api','request':{'url':URL,'strategy':'mobile'},'observed_at':AT,'state':'response_received','status':200});r=self.load(field_attempts=[p]);self.assertNotIn('field_authorization_missing',[g['reason'] for g in r['gaps']])
    def reviewed(self,**kw):
        from test_page_reviews import raw,review
        row=self.lab();data=lhr();data.update(raw());row['lhr_evidence']=self.proof('lhr.json',data)
        cell=json.loads((self.root/'cell.json').read_text());cell['attempts'][0]['lhr_evidence']=row['lhr_evidence'];row['context_evidence']=self.proof('cell.json',cell)
        proof=self.proof('review.json',review(lhr_sha256=row['lhr_evidence']['sha256'],**kw));return row,proof
    def test_bound_review_loaded_from_actual_bytes(self):
        row,proof=self.reviewed();r=self.load(lab_runs=[row],page_reviews=[proof]);self.assertEqual(r['lab_runs'][0]['page_content_validity'],'reviewed_valid');self.assertEqual(r['lab_runs'][0]['page_review_evidence'],proof)
    def test_invalid_business_review_excludes_run(self):
        row,proof=self.reviewed(status='invalid');self.assertFalse(self.load(lab_runs=[row],page_reviews=[proof])['lab_runs'][0]['valid_measurement'])
    def test_tampered_review_not_promoted(self):
        row,proof=self.reviewed();proof['sha256']='f'*64;r=self.load(lab_runs=[row],page_reviews=[proof]);self.assertTrue(r['gaps']);self.assertNotEqual(r['lab_runs'][0]['page_content_validity'],'reviewed_valid')
    def test_conflicting_reviews_not_order_dependent(self):
        row,proof=self.reviewed();review=json.loads((self.root/'review.json').read_text());review['status']='invalid';second=self.proof('conflict.json',review);r=self.load(lab_runs=[row],page_reviews=[proof,second]);self.assertIn('page_review_conflict',[g['reason'] for g in r['gaps']])
    def test_orphan_review_keeps_gap(self):
        row,proof=self.reviewed();r=self.load(page_reviews=[proof]);self.assertIn('page_review_measurement_missing',[g['reason'] for g in r['gaps']])
