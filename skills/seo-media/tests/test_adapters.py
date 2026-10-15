import json,hashlib,tempfile
from pathlib import Path
from support import MediaTest
AT='2026-09-16T23:00:00Z';URL='https://bingx.com/en/'
class AdapterTests(MediaTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.shot=self.save('shot.png',b'\x89PNG\r\n\x1a\nfixture')
        self.capture={'snapshot_id':'a','url':URL,'requested_url':URL,'device':'desktop','captured_at':AT,'readiness':'ready','html':'<main>Bitcoin diagram</main>',
          'entity':'Bitcoin','visible_main':'Bitcoin diagram','source':'actual browser','screenshot':self.shot,'responses':[],
          'media':[{'slot':'img#hero','tag':'img','captured_at':AT,'current_src':'https://bingx.com/a.png'}]}
        self.capture['document_sha256']=hashlib.sha256(self.capture['html'].encode()).hexdigest()
        self.review={'snapshot_id':'a','reviewer':'test reviewer','method':'screenshot and visible context review','reviewed_at':AT,'screenshot_sha256':self.shot['sha256'],
          'items':[{'slot':'img#hero','purpose':'informative','citation':{'field':'visible_main','quote':'Bitcoin diagram'},'notes':'Diagram communicates asset information.'}]}
    def save(self,name,data):
        if not isinstance(data,bytes):data=(json.dumps(data)+'\n').encode()
        (self.root/name).write_bytes(data);return {'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    def write(self,reviews=True):
        proof=self.save('capture.json',self.capture);self.review.setdefault('capture_sha256',proof['sha256'])
        self.manifest={'schema_version':1,'scope':[{'url':URL,'devices':['desktop']}],'captures':[proof],'reviews':[self.save('review.json',self.review)] if reviews else []}
        return self.manifest
    def load(self,manifest=None):
        self.save('manifest.json',manifest or self.write());return self.module('adapters').load_manifest(self.root/'manifest.json',at=AT)
    def test_bound_capture_and_named_review_accepted(self):
        r=self.load();self.assertEqual(len(r['captures']),1);self.assertEqual(r['reviews']['a']['img#hero']['purpose'],'informative')
    def test_capture_modified_bytes_not_accepted(self):
        m=self.write();(self.root/'capture.json').write_text('{}');r=self.load(m);self.assertEqual(r['captures'],[]);self.assertIn('evidence_integrity_mismatch',str(r['gaps']))
    def test_changed_html_invalid_even_file_hash_updated(self):
        self.capture['html']='changed';self.assertEqual(self.load()['captures'],[])
    def test_review_binds_entire_capture_not_only_html(self):
        self.review['capture_sha256']='0'*64;r=self.load();self.assertNotIn('a',r['reviews'])
    def test_review_wrong_screenshot_rejected(self):self.review['screenshot_sha256']='0'*64;self.assertEqual(self.load()['reviews'],{})
    def test_missing_reviewer_rejected(self):del self.review['reviewer'];self.assertEqual(self.load()['reviews'],{})
    def test_missing_method_rejected(self):del self.review['method'];self.assertEqual(self.load()['reviews'],{})
    def test_future_review_rejected(self):self.review['reviewed_at']='2026-09-17T00:00:00Z';self.assertEqual(self.load()['reviews'],{})
    def test_review_before_capture_rejected(self):self.review['reviewed_at']='2026-09-16T22:00:00Z';self.assertEqual(self.load()['reviews'],{})
    def test_nonexistent_slot_rejected(self):self.review['items'][0]['slot']='img#invented';self.assertEqual(self.load()['reviews'],{})
    def test_invented_quote_rejected(self):self.review['items'][0]['citation']['quote']='not in evidence';self.assertEqual(self.load()['reviews'],{})
    def test_empty_quote_rejected(self):self.review['items'][0]['citation']['quote']='';self.assertEqual(self.load()['reviews'],{})
    def test_unbound_observation_time_rejected(self):self.capture['media'][0]['captured_at']='2026-09-16T22:00:00Z';self.assertEqual(self.load()['captures'],[])
    def test_duplicate_slot_rejected(self):self.capture['media'].append(dict(self.capture['media'][0]));self.assertEqual(self.load()['captures'],[])
    def test_unknown_device_rejected(self):
        m=self.write();m['scope'][0]['devices']=['desktopish'];
        with self.assertRaises(ValueError):self.load(m)
    def test_missing_scope_rejected(self):
        m=self.write();m['scope']=[]
        with self.assertRaises(ValueError):self.load(m)
    def test_capture_without_review_still_available(self):r=self.load(self.write(False));self.assertEqual(len(r['captures']),1);self.assertEqual(r['reviews'],{})
    def test_source_file_outside_root_rejected(self):
        m=self.write();m['captures'][0]['path']='../outside.json';self.assertEqual(self.load(m)['captures'],[])
    def test_missing_screenshot_does_not_erase_machine_capture(self):
        self.capture.pop('screenshot');r=self.load();self.assertEqual(len(r['captures']),1);self.assertEqual(r['reviews'],{})
    def test_tampered_screenshot_rejects_purpose_review(self):
        m=self.write();(self.root/'shot.png').write_bytes(b'changed');r=self.load(m);self.assertEqual(r['reviews'],{})
    def test_duplicate_snapshot_id_poisoned_not_last_wins(self):
        m=self.write();m['captures'].append(dict(m['captures'][0]));self.assertEqual(self.load(m)['captures'],[])
    def test_invalid_purpose_review_rejected(self):self.review['items'][0]['purpose']='possibly fine';self.assertEqual(self.load()['reviews'],{})
    def test_conflicting_review_for_slot_not_last_wins(self):
        m=self.write();other=dict(self.review);other['items']=[{**self.review['items'][0],'purpose':'decorative'}];m['reviews'].append(self.save('other.json',other));self.assertEqual(self.load(m)['reviews'],{})
    def test_declared_html_extracted_without_claiming_selected_srcset(self):
        self.capture['html']='<img src="/a.png" srcset="/b.png 2x">';self.capture['document_sha256']=hashlib.sha256(self.capture['html'].encode()).hexdigest();r=self.load();self.assertEqual(len(r['captures'][0]['declarations']['resource_refs']),2)
    def test_nested_capture_screenshot_is_relative_to_capture_file(self):
        m=self.write();(self.root/'nested').mkdir();(self.root/'capture.json').rename(self.root/'nested/capture.json');(self.root/'shot.png').rename(self.root/'nested/shot.png');m['captures'][0]['path']='nested/capture.json';self.assertIn('a',self.load(m)['reviews'])
    def test_wrong_purpose_for_image_not_accepted(self):self.review['items'][0]['purpose']='watch_video';self.assertEqual(self.load()['reviews'],{})
    def test_decode_future_timestamp_rejected(self):
        self.capture['media'][0]['decode']={'result':'fulfilled','current_src':'https://bingx.com/a.png','source_after_probe':'https://bingx.com/a.png','completed_at':'2026-09-17T00:00:00Z'};self.assertEqual(self.load()['captures'],[])
    def test_decode_changed_resource_not_accepted(self):
        self.capture['media'][0]['decode']={'result':'fulfilled','current_src':'https://bingx.com/a.png','source_after_probe':'https://bingx.com/b.png','completed_at':AT};self.assertEqual(self.load()['captures'],[])
