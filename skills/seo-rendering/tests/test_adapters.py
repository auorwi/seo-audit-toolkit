import hashlib
import json
import tempfile
from pathlib import Path
from support import RenderingTest,AT
from test_readiness import URL

class RenderAdapterTests(RenderingTest):
    def test_preparation_gaps_remain_in_loaded_manifest(self):
        result=self.module('adapters').load_manifest(self.manifest(gaps=[{'url':URL,'reason':'initial_http_not_current'}]))
        self.assertEqual(result['gaps'],[{'url':URL,'reason':'initial_http_not_current'}])

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)

    def evidence(self,name,body):
        p=self.base/name;p.write_bytes(body)
        return {'path':name,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}

    def metadata(self,**kw):
        return {'id':'s1','url':URL,'requested_url':URL,'kind':'dom_fields','stage':'dom','entry_mode':'direct',
            'navigation_id':'nav1','source':'actual browser','captured_at':AT,**kw}

    def dom(self,**kw):
        data={**self.metadata(),'title':'Solv Protocol','h1':['Solv'],'coverage':{'title':'complete','h1':'complete'},**kw}
        return data

    def manifest(self,snapshots=None,**kw):
        p=self.base/'manifest.json';p.write_text(json.dumps({'schema_version':1,'snapshots':snapshots or [],**kw}));return p

    def test_verified_dom_fields_import_keeps_unknown_http_and_partial_coverage(self):
        evidence=self.evidence('dom.json',json.dumps(self.dom()).encode())
        result=self.module('adapters').load_manifest(self.manifest([{**self.metadata(),'evidence':evidence}]))
        row=result['snapshots'][0]
        self.assertEqual(row['title'],'Solv Protocol');self.assertIsNone(row['main_text'])
        self.assertIsNone(row.get('http_status'));self.assertFalse(row['full_dom'])

    def test_initial_html_import_is_marked_initial(self):
        evidence=self.evidence('initial.html',b'<head><title>Initial</title></head><main><h1></h1></main>')
        record={**self.metadata(kind='initial_html',stage='initial'),'evidence':evidence,'http_status':200}
        result=self.module('adapters').load_manifest(self.manifest([record]))
        self.assertEqual(result['snapshots'][0]['representation'],'initial_html')
        self.assertEqual(result['snapshots'][0]['h1'],[''])

    def test_raw_html_cannot_be_relabeled_browser_execution(self):
        evidence=self.evidence('initial.html',b'<main>Text</main>')
        result=self.module('adapters').load_manifest(self.manifest([{**self.metadata(kind='initial_html',stage='dom'),'evidence':evidence}]))
        self.assertEqual(result['snapshots'],[]);self.assertTrue(result['gaps'])

    def test_tampered_file_is_gap_without_using_inline_snapshot_values(self):
        evidence=self.evidence('dom.json',json.dumps(self.dom()).encode());(self.base/'dom.json').write_bytes(b'changed')
        row={**self.metadata(),'title':'injected','evidence':evidence}
        result=self.module('adapters').load_manifest(self.manifest([row]))
        self.assertEqual(result['snapshots'],[])
        self.assertEqual(result['gaps'][0]['reason'],'evidence_integrity_mismatch')

    def test_dom_capture_id_url_and_time_cannot_be_changed_in_manifest(self):
        evidence=self.evidence('dom.json',json.dumps(self.dom()).encode())
        for override in [{'id':'forged'},{'url':'https://bingx.com/en/other'},{'captured_at':'2026-09-18T00:00:00Z'}]:
            result=self.module('adapters').load_manifest(self.manifest([{**self.metadata(),'evidence':evidence,**override}]))
            self.assertEqual(result['snapshots'],[]);self.assertTrue(result['gaps'])

    def test_external_evidence_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            external=Path(tmp)/'private';external.write_bytes(b'private')
            evidence={'path':str(external),'bytes':7,'sha256':hashlib.sha256(b'private').hexdigest()}
            result=self.module('adapters').load_manifest(self.manifest([{**self.metadata(),'evidence':evidence}]))
            self.assertEqual(result['snapshots'],[]);self.assertEqual(result['gaps'][0]['reason'],'evidence_outside_root')

    def test_dom_context_cannot_be_reassigned_or_omitted_in_manifest(self):
        context={'environment':{'device':'desktop'},'phase_id':'loaded','navigation_started_at':'2026-09-16T23:59:58Z','http_status':None}
        proof=self.evidence('dom.json',json.dumps(self.dom(**context)).encode())
        for changed in [{'environment':{'device':'mobile'}},{'phase_id':'other'},{'navigation_started_at':AT},{'http_status':200}]:
            row={**self.metadata(),**context,**changed,'evidence':proof}
            result=self.module('adapters').load_manifest(self.manifest([row]))
            self.assertEqual(result['snapshots'],[])
            self.assertTrue(result['gaps'])
        result=self.module('adapters').load_manifest(self.manifest([{**self.metadata(),'evidence':proof}]))
        self.assertEqual(result['snapshots'],[])

    def test_rendered_html_does_not_invent_runtime_identity_or_placeholder_state(self):
        proof=self.evidence('dom.html',b'<main><h1>SOLV</h1></main>')
        row={**self.metadata(kind='rendered_html'),'evidence':proof}
        result=self.module('adapters').load_manifest(self.manifest([row]))
        snapshot=result['snapshots'][0]
        self.assertEqual(snapshot['representation'],'rendered_html');self.assertTrue(snapshot['full_dom'])
        self.assertIsNone(snapshot['identity']);self.assertIsNone(snapshot['placeholder_count'])

    def test_interaction_must_match_its_saved_event(self):
        event={'id':'e1','url':URL,'kind':'paginate','before_id':'s1','after_id':'s2','source':'browser','checked_at':AT,'before_page':'1','after_page':'2','before_items':['A'],'after_items':['B']}
        proof=self.evidence('event.json',json.dumps(event).encode())
        result=self.module('adapters').load_manifest(self.manifest(interactions=[{**event,'evidence':proof}]))
        self.assertEqual(result['interactions'][0]['after_items'],['B'])
        result=self.module('adapters').load_manifest(self.manifest(interactions=[{**event,'after_items':['FAKE'],'evidence':proof}]))
        self.assertEqual(result['interactions'],[]);self.assertTrue(result['gaps'])

    def test_invalid_manifest_version_fails_without_output_mutations(self):
        with self.assertRaises(ValueError):self.module('adapters').load_manifest(self.manifest(schema_version=99))

    def test_invalid_capture_time_is_gap_not_command_crash(self):
        proof=self.evidence('dom.json',json.dumps(self.dom(captured_at='no-time')).encode())
        result=self.module('adapters').load_manifest(self.manifest([{**self.metadata(captured_at='no-time'),'evidence':proof}]))
        self.assertEqual(result['snapshots'],[]);self.assertTrue(result['gaps'])
