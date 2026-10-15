import json,hashlib,tempfile
from pathlib import Path
from support import InternationalTest,AT
from test_clusters import F
class AdapterTests(InternationalTest):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def proof(self,name,body):
        raw=body.encode() if isinstance(body,str) else json.dumps(body).encode();(self.root/name).write_bytes(raw);return {'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    def capture(self):
        p=self.proof('page.html','<html lang="fr"><head><link rel="canonical" href="https://bingx.com/fr/a"></head><body><main>Bonjour</main></body></html>')
        return {'url':F,'snapshot_id':'dom1','captured_at':AT,'source':'actual browser','representation':'rendered_html','readiness':'ready','state':'completed','document_sha256':p['sha256'],'evidence':p}
    def load(self,**kw):
        p=self.root/'manifest.json';p.write_text(json.dumps({'schema_version':1,**kw}));return self.module('adapters').load_manifest(p)
    def test_parse_html_not_inline_claim(self):
        c=self.capture();c['html_langs']=['en'];self.assertEqual(self.load(captures=[c])['captures'][0]['html_langs'],['fr'])
    def test_proof_hash_corrupt_gap(self):
        c=self.capture();c['evidence']['sha256']='b'*64;r=self.load(captures=[c]);self.assertTrue(r['gaps']);self.assertEqual(r['captures'][0]['state'],'evidence_error')
    def test_inline_visible_main_ignored(self):
        c=self.capture();c['visible_main']='invented';self.assertNotIn('visible_main',self.load(captures=[c])['captures'][0])
    def test_bound_browser_visible_main(self):
        c=self.capture();b={k:c[k] for k in ['url','snapshot_id','captured_at','document_sha256']};b.update(source='actual DOM evaluate',visible_main='Bonjour',main_selector='main',visible_fields={'country':False});c['browser_evidence']=self.proof('browser.json',b);self.assertEqual(self.load(captures=[c])['captures'][0]['visible_main'],'Bonjour')
    def test_browser_wrong_document_not_used(self):
        c=self.capture();b={k:c[k] for k in ['url','snapshot_id','captured_at','document_sha256']};b.update(source='actual',visible_main='Bonjour',document_sha256='b'*64);c['browser_evidence']=self.proof('browser.json',b);self.assertNotIn('visible_main',self.load(captures=[c])['captures'][0])
    def test_path_escape_rejected(self):
        c=self.capture();c['evidence']['path']='../outside.html';self.assertTrue(self.load(captures=[c])['gaps'])
    def test_failed_attempt_kept(self):
        c=self.capture();c.update(state='failed',entry_mode='language_switch');r=self.load(captures=[c]);self.assertEqual(r['captures'][0]['entry_mode'],'language_switch');self.assertEqual(r['captures'][0]['state'],'failed')
    def test_invalid_version(self):
        p=self.root/'manifest.json';p.write_text('{"schema_version":99}')
        with self.assertRaises(ValueError):self.module('adapters').load_manifest(p)
    def test_http_actual_headers(self):
        h={'url':F,'checked_at':AT,'source':'actual GET','state':'completed','method':'GET','status':200,'headers':[['Link','<https://bingx.com/en/a>; rel=alternate; hreflang=en']]};p=self.proof('http.json',h);r=self.load(http_records=[{**h,'evidence':p,'evidence_kind':'actual_response_metadata'}]);self.assertEqual(r['captures'][0]['alternates'][0]['locale'],'en')
    def test_http_modified_status_not_used(self):
        h={'url':F,'checked_at':AT,'source':'actual GET','state':'completed','method':'GET','status':404,'headers':[]};p=self.proof('http.json',h);r=self.load(http_records=[{**h,'status':200,'evidence':p,'evidence_kind':'actual_response_metadata'}]);self.assertTrue(r['http_records'][0]['evidence_error'])
    def test_head_not_hreflang_response_evidence(self):
        h={'url':F,'checked_at':AT,'source':'actual HEAD','state':'completed','method':'HEAD','status':200,'headers':[['Link','<https://bingx.com/en/a>; rel=alternate; hreflang=en']]};p=self.proof('http.json',h);self.assertEqual(self.load(http_records=[{**h,'evidence':p,'evidence_kind':'actual_response_metadata'}])['captures'],[])
    def test_sitemap_actual_xml(self):
        p=self.proof('map.xml','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:x="http://www.w3.org/1999/xhtml"><url><loc>https://bingx.com/fr/a</loc><x:link rel="alternate" hreflang="fr" href="https://bingx.com/fr/a"/></url></urlset>');r=self.load(sitemaps=[{'evidence':p,'captured_at':AT,'source':'actual sitemap','url':'https://bingx.com/sitemap.xml'}]);self.assertEqual(r['captures'][0]['representation'],'sitemap')
    def test_review_proof_loaded(self):
        p=self.proof('reviews.json',[{'source':'review','snapshot_id':'x'}]);self.assertEqual(self.load(body_reviews=[p])['body_reviews'][0]['snapshot_id'],'x')
    def test_mapping_needs_provenance(self):
        p=self.proof('assets.json',[{'url':F,'entity_id':'bitcoin','locale':'fr','published':True}]);r=self.load(asset_mappings=[p]);self.assertEqual(r['assets'],[]);self.assertTrue(r['gaps'])
    def test_mapping_with_source_kept(self):
        p=self.proof('assets.json',[{'url':F,'entity_id':'bitcoin','locale':'fr','published':True,'source':'CMS export','mapped_at':AT}]);self.assertEqual(len(self.load(asset_mappings=[p])['assets']),1)
    def test_duplicate_snapshot_conflict_rejected(self):
        c=self.capture();d={**c,'url':'https://bingx.com/en/a'}
        with self.assertRaises(ValueError):self.load(captures=[c,d])
    def test_malformed_sitemap_retains_gap_not_crash(self):
        p=self.proof('broken.xml','<urlset><url>');r=self.load(sitemaps=[{'evidence':p,'captured_at':AT,'source':'actual','url':'https://bingx.com/sitemap.xml'}]);self.assertTrue(r['gaps'])
