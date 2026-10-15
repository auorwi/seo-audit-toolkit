import hashlib
import json
import tempfile
from pathlib import Path
from support import SemanticsTest,URL,AT
from test_rules import dom,node
from test_tool_reports import report

class EvidenceAdapterTests(SemanticsTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.html=b'<!doctype html><html><body><main><h1>Prices</h1></main></body></html>'
        self.digest=hashlib.sha256(self.html).hexdigest();self.document=self.save('dom.html',self.html)

    def save(self,name,body):
        (self.root/name).write_bytes(body)
        return {'path':name,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}

    def manifest(self,**kw):
        p=self.root/'manifest.json';p.write_text(json.dumps({'schema_version':1,'captures':[],'tool_reports':[],**kw}));return p

    def entry(self,**kw):
        capture=dom([node('main','main'),node('h','h1','Prices')],document_sha256=self.digest)
        proof=self.save('elements.json',json.dumps(capture).encode())
        return {'kind':'rendered_elements','url':URL,'snapshot_id':'dom1','captured_at':capture['captured_at'],'source':capture['source'],'evidence':proof,'document_evidence':self.document,**kw}

    def load(self,**kw):return self.module('adapters').load_manifest(self.manifest(**kw))

    def test_actual_elements_bound_to_verified_dom_file(self):
        result=self.load(captures=[self.entry()])
        self.assertEqual(result['gaps'],[]);self.assertEqual(result['captures'][0]['nodes'][1]['text'],'Prices')
        self.assertEqual(result['captures'][0]['document_sha256'],self.digest)

    def test_reassigned_url_or_capture_identity_rejected(self):
        for kw in [{'url':'https://bingx.com/en/other'},{'snapshot_id':'wrong'},{'captured_at':AT}]:
            result=self.load(captures=[self.entry(**kw)])
            self.assertEqual(result['captures'],[]);self.assertTrue(result['gaps'])

    def test_inline_readiness_cannot_override_saved_pending_or_ready(self):
        result=self.load(captures=[self.entry(readiness='pending')])
        self.assertEqual(result['captures'],[]);self.assertTrue(result['gaps'])

    def test_dom_hash_mismatch_is_not_current_element_evidence(self):
        wrong=self.save('other.html',b'<html>other</html>')
        result=self.load(captures=[self.entry(document_evidence=wrong)])
        self.assertEqual(result['captures'],[]);self.assertTrue(result['gaps'])

    def test_tampered_json_not_used(self):
        entry=self.entry();(self.root/'elements.json').write_text('{}')
        result=self.load(captures=[entry]);self.assertEqual(result['captures'],[])
        self.assertEqual(result['gaps'][0]['reason'],'evidence_integrity_mismatch')

    def test_source_html_stays_source_representation(self):
        entry={'kind':'initial_html','url':URL,'snapshot_id':'source1','captured_at':AT,'source':'HTTP collector','evidence':self.document}
        result=self.load(captures=[entry]);capture=result['captures'][0]
        self.assertEqual(capture['representation'],'source_elements');self.assertIsNone(capture['readiness'])
        self.assertEqual(capture['document_sha256'],self.digest)

    def test_external_checker_record_bound_to_same_document(self):
        record=report(document_sha256=self.digest,input_sha256=self.digest)
        proof=self.save('axe.json',json.dumps(record).encode())
        entry={'tool':'axe','url':URL,'capture_id':record['capture_id'],'checked_at':record['checked_at'],'evidence':proof,'document_evidence':self.document}
        result=self.load(tool_reports=[entry]);self.assertEqual(result['tool_reports'][0]['checker_version'],'4.10.3')
        self.assertEqual(result['gaps'],[])

    def test_checker_metadata_or_document_rebinding_is_gap(self):
        record=report(document_sha256=self.digest,input_sha256=self.digest)
        proof=self.save('axe.json',json.dumps(record).encode())
        entry={'tool':'axe','url':URL,'capture_id':'wrong','checked_at':record['checked_at'],'evidence':proof,'document_evidence':self.document}
        result=self.load(tool_reports=[entry]);self.assertEqual(result['tool_reports'],[]);self.assertTrue(result['gaps'])

    def test_evidence_path_outside_manifest_root_rejected(self):
        with tempfile.TemporaryDirectory() as other:
            path=Path(other)/'outside.json';path.write_bytes(b'{}')
            entry=self.entry(evidence={'path':str(path),'bytes':2,'sha256':hashlib.sha256(b'{}').hexdigest()})
            result=self.load(captures=[entry]);self.assertEqual(result['captures'],[])
            self.assertEqual(result['gaps'][0]['reason'],'evidence_outside_root')

    def test_invalid_manifest_schema_fails(self):
        with self.assertRaises(ValueError):self.load(schema_version=4)
