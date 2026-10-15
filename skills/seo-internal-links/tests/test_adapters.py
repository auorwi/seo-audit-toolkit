import hashlib,json,tempfile
from pathlib import Path
from support import LinkTest,URL
class AdapterTests(LinkTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.proof=self.save('page.html',b'<html lang="en"><main><a href="/en/price">Price</a></main></html>')
        self.row={'url':URL,'snapshot_id':'dom','document_sha256':self.proof['sha256'],'source':'actual fixture browser','captured_at':'2026-09-17T02:00:00Z','representation':'rendered_html','readiness':'ready','entry_mode':'direct','evidence':self.proof}
    def save(self,name,data):
        body=data if isinstance(data,bytes) else json.dumps(data).encode();(self.root/name).write_bytes(body);return {'path':name,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
    def load(self,**kw):
        p=self.root/'manifest.json';p.write_text(json.dumps({'schema_version':1,'captures':[self.row],'assets':[URL],'seeds':{'home':['https://bingx.com/en/']},**kw}));return self.module('adapters').load_manifest(p)
    def test_actual_html_parsed_inline_link_claims_ignored(self):
        self.row['links']=[{'target':'https://evil.example'}];r=self.load();self.assertEqual(r['captures'][0]['links'][0]['target'],'https://bingx.com/en/price');self.assertEqual(r['captures'][0]['html_lang'],'en')
    def test_bad_html_hash_preserves_failed_internal_attempt(self):
        self.row['entry_mode']='internal';(self.root/'page.html').write_text('bad');c=self.load()['captures'][0];self.assertEqual(c['state'],'evidence_error');self.assertEqual(c['entry_mode'],'internal')
    def test_document_sha_must_match_real_evidence(self):
        self.row['document_sha256']='b'*64;self.assertEqual(self.load()['captures'][0]['state'],'evidence_error')
    def test_initial_html_has_no_assumed_rendered_readiness(self):
        self.row['representation']='initial_html';del self.row['readiness'];self.assertIsNone(self.load()['captures'][0]['readiness'])
    def test_missing_rendered_readiness_not_auto_ready(self):
        del self.row['readiness'];self.assertEqual(self.load()['captures'][0]['state'],'evidence_error')
    def browser(self,**kw):return {**{k:self.row[k] for k in ['url','snapshot_id','document_sha256','captured_at']},'source':'same browser evaluate fixture','links':[{'locator':'a[observed-index=0]','href':'/en/price','visible':True,'inner_text':'Price'}],'item_keys':['BTC','ETH'],**kw}
    def test_actual_browser_visibility_only_if_matching_snapshot_href_and_locator(self):
        self.row['browser_evidence']=self.save('browser.json',self.browser());c=self.load()['captures'][0];self.assertEqual(c['links'][0]['visibility'],'visible');self.assertEqual(c['item_keys'],['BTC','ETH'])
    def test_wrong_browser_binding_is_gap_not_false_visibility(self):
        self.row['browser_evidence']=self.save('browser.json',self.browser(document_sha256='b'*64));r=self.load();self.assertEqual(r['captures'][0]['links'][0]['visibility'],'not_observed');self.assertTrue(r['gaps'])
    def test_wrong_href_does_not_attach_visibility_to_other_link(self):
        self.row['browser_evidence']=self.save('browser.json',self.browser(links=[{'locator':'a[observed-index=0]','href':'/wrong','visible':True}]))
        r=self.load();self.assertEqual(r['captures'][0]['links'][0]['visibility'],'not_observed');self.assertTrue(r['gaps'])
    def test_target_http_actual_body_hash_required(self):
        row={'url':URL,'checked_at':'2026-09-17T02:00:00Z','source':'actual GET fixture','method':'GET','status':404,'evidence':self.proof,'headers':[]}
        r=self.load(http_records=[row]);self.assertNotIn('evidence_error',r['http_records'][0]);(self.root/'page.html').write_text('changed');self.assertTrue(self.load(http_records=[row])['http_records'][0]['evidence_error'])
    def test_failed_http_attempt_retained_without_body(self):
        r=self.load(http_records=[{'url':URL,'checked_at':'2026-09-17T02:30:00Z','source':'actual failed request','method':'GET','status':None,'error':'timeout'}]);self.assertEqual(r['http_records'][0]['error'],'timeout')
    def test_pagination_actions_require_real_file_proof_not_inline(self):
        r=self.load(pagination=[{'before':'dom','after':'dom2','action_evidence':self.save('action.json',{'before_snapshot':'dom','after_snapshot':'dom2','source':'actual fixture'})}]);self.assertEqual(r['pagination'][0]['action']['before_snapshot'],'dom')
    def test_missing_optional_evidence_is_gap_preserving_actual_links(self):
        self.row['browser_evidence']={'path':'missing','bytes':1,'sha256':'a'*64};r=self.load();self.assertTrue(r['captures'][0]['links']);self.assertTrue(r['gaps'])
    def test_language_expectations_read_from_proof_bound_file(self):
        r=self.load(language_expectations=[self.save('language.json',{'source_url':URL,'expected_language':'fr'})]);self.assertEqual(r['language_expectations'][0]['expected_language'],'fr')
    def test_invalid_top_level_shapes_rejected(self):
        for kwargs in [{'schema_version':2},{'captures':'bad'},{'http_records':'bad'},{'assets':'bad'},{'seeds':[]}]:
            with self.assertRaises(ValueError):self.load(**kwargs)
    def test_evidence_path_escape_rejected(self):
        self.row['evidence']={**self.proof,'path':'../page.html'};self.assertEqual(self.load()['captures'][0]['state'],'evidence_error')
    def test_interaction_discovery_scope_survives_adapter(self):
        self.row['discovery_mode']='interaction_only';self.assertEqual(self.load()['captures'][0].get('discovery_mode'),'interaction_only')
    def test_http_metadata_manifest_cannot_change_saved_response_status(self):
        original={'url':URL,'checked_at':'2026-09-17T02:00:00Z','source':'actual response chain fixture','method':'GET','status':200,'headers':[],'state':'completed'}
        proof=self.save('http.json',original);r=self.load(http_records=[{**original,'status':404,'evidence':proof,'evidence_kind':'actual_response_metadata'}])
        self.assertEqual(r['http_records'][0].get('evidence_error'),'http_metadata_binding')
    def test_matching_http_metadata_is_usable_evidence(self):
        original={'url':URL,'checked_at':'2026-09-17T02:00:00Z','source':'actual response chain fixture','method':'GET','status':302,'headers':[['location','/en/price']],'state':'completed'}
        r=self.load(http_records=[{**original,'evidence':self.save('http.json',original),'evidence_kind':'actual_response_metadata'}]);self.assertNotIn('evidence_error',r['http_records'][0])
