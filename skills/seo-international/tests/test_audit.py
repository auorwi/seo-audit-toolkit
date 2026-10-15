from support import InternationalTest,AT
from test_clusters import cap,alt,E,F
def inputs(**kw):return {'captures':[],'assets':[],'http_records':[],'body_reviews':[],'switches':[],'gaps':[],**kw}
def http(url,status,**kw):return {'url':url,'status':status,'method':'GET','checked_at':AT,'source':'fixture actual GET','state':'completed','headers':[],'evidence':{'sha256':'f'*64},**kw}
class AuditTests(InternationalTest):
    def run_check(self,i):return self.module('audit').audit(i,at=AT)
    def rules(self,r):return [f['rule'] for f in r['findings']]
    def test_hreflang_target_404(self):
        r=self.run_check(inputs(captures=[cap(E,[alt(E,F,'fr')])],http_records=[http(F,404)]));self.assertIn('hreflang_target_http_problem',self.rules(r))
    def test_403_not_permanent_broken(self):
        r=self.run_check(inputs(captures=[cap(E,[alt(E,F,'fr')])],http_records=[http(F,403)]));self.assertFalse(r['targets'][0]['permanent_broken_proven'])
    def test_target_redirect_keeps_chain(self):
        r=self.run_check(inputs(captures=[cap(E,[alt(E,F,'fr')])],http_records=[http(F,302,headers=[['location',E]]),http(E,200)]));self.assertIn('hreflang_target_redirect',self.rules(r));self.assertEqual(r['targets'][0]['final_url'],E)
    def test_200_not_body_verified(self):
        r=self.run_check(inputs(captures=[cap(E,[alt(E,F,'fr')])],http_records=[http(F,200)]));self.assertEqual(r['targets'][0]['content_validity'],'unverified')
    def test_stable_issue_id_different_snapshot(self):
        a=inputs(captures=[cap(E,[alt(E,F,'fr')])]);b=inputs(captures=[cap(E,[alt(E,F,'fr')],snapshot_id='new')]);self.assertEqual([f['issue_id'] for f in self.run_check(a)['findings']],[f['issue_id'] for f in self.run_check(b)['findings']])
    def test_repeated_source_dedup_findings(self):
        c=cap(E,[alt(E,F,'fr')]);r=self.run_check(inputs(captures=[c,c]));self.assertEqual(len({f['issue_id'] for f in r['findings']}),len(r['findings']))
    def test_full_site_never_claimed(self):self.assertFalse(self.run_check(inputs())['coverage']['full_site_proven'])
    def test_invalid_freshness_rejected(self):
        with self.assertRaises(ValueError):self.module('audit').audit(inputs(),at=AT,max_age_hours=0)
    def test_mapping_conflict_rejected(self):
        with self.assertRaises(ValueError):self.run_check(inputs(assets=[{'url':E,'entity_id':'a'},{'url':E,'entity_id':'b'}]))
    def test_snapshot_collision_rejected(self):
        with self.assertRaises(ValueError):self.run_check(inputs(captures=[cap(E,snapshot_id='one'),cap(F,snapshot_id='one')]))
    def test_hreflang_target_actual_body_mismatch(self):
        from test_content import review
        f=cap(F,visible_main='Bonjour le monde');r=self.run_check(inputs(captures=[cap(E,[alt(E,F,'en')]),f],body_reviews=[review(f,'fr')]));self.assertIn('hreflang_body_language_mismatch',self.rules(r))
    def test_redirect_final_body_checked_under_original_declaration(self):
        from test_content import review
        j='https://bingx.com/ja/a';jcap=cap(j,visible_main='Bonjour le monde');r=self.run_check(inputs(captures=[cap(E,[alt(E,F,'fr')]),jcap],body_reviews=[review(jcap,'ja')],http_records=[http(F,302,headers=[['location',j]]),http(j,200)]));self.assertIn('hreflang_body_language_mismatch',self.rules(r))
    def test_stale_mapping_not_used_to_invent_missing_variant(self):
        assets=[{'url':E,'entity_id':'a','published':True,'mapped_at':'2020-01-01T00:00:00Z'},{'url':F,'entity_id':'a','published':True,'mapped_at':'2020-01-01T00:00:00Z'}];r=self.run_check(inputs(captures=[cap(E)],assets=assets));self.assertNotIn('published_variant_not_declared',self.rules(r))
