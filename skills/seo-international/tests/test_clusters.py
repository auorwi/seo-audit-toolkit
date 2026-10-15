from support import InternationalTest,AT
E='https://bingx.com/en/a';F='https://bingx.com/fr/a';J='https://bingx.com/ja/a'
def alt(source,target,lang,channel='html'):
    return {'source_url':source,'target_url':target,'href':target,'locale':lang,'eligible':True,'problems':[],'channel':channel,'locator':'link1'}
def cap(url,alts=None,**kw):
    return {'url':url,'snapshot_id':url,'captured_at':AT,'source':'fixture','representation':'rendered_html','entry_mode':'direct','readiness':'ready','state':'completed','document_sha256':'a'*64,'alternates':alts or [],'canonicals':[],'html_langs':[],'schema_languages':[],**kw}
class ClusterTests(InternationalTest):
    def run_check(self,cs,assets=None):return self.module('clusters').review_clusters(cs,assets or [],at=AT)
    def rules(self,r):return [f['rule'] for f in r['observations']]
    def pair(self):return [cap(E,[alt(E,E,'en'),alt(E,F,'fr')]),cap(F,[alt(F,F,'fr'),alt(F,E,'en')])]
    def test_reciprocal_complete(self):self.assertEqual(self.run_check(self.pair())['observations'],[])
    def test_no_xdefault_not_error(self):self.assertEqual(self.run_check(self.pair())['observations'],[])
    def test_missing_self(self):self.assertIn('hreflang_self_not_observed',self.rules(self.run_check([cap(E,[alt(E,F,'fr')])])))
    def test_missing_return_observed_candidate(self):self.assertIn('hreflang_return_not_observed',self.rules(self.run_check([cap(E,[alt(E,E,'en'),alt(E,F,'fr')]),cap(F)])))
    def test_unobserved_target_not_missing_return(self):
        r=self.run_check([cap(E,[alt(E,E,'en'),alt(E,F,'fr')])]);self.assertNotIn('hreflang_return_not_observed',self.rules(r));self.assertIn('target_declarations_unobserved',[g['reason'] for g in r['gaps']])
    def test_locale_conflict(self):self.assertIn('hreflang_locale_conflict',self.rules(self.run_check([cap(E,[alt(E,F,'fr'),alt(E,J,'fr')])])))
    def test_same_target_duplicate_channels_allowed(self):
        cs=self.pair();cs[0]['alternates'].append(alt(E,F,'fr','http'));self.assertEqual(self.run_check(cs)['observations'],[])
    def test_crosschannel_conflict(self):self.assertIn('hreflang_locale_conflict',self.rules(self.run_check([cap(E,[alt(E,F,'fr'),alt(E,J,'fr','sitemap')])])))
    def test_invalid_locale_not_edge(self):
        r=self.run_check([cap(E,[alt(E,F,'fr-UK')])]);self.assertIn('hreflang_code_unsupported',self.rules(r));self.assertEqual(r['edges'],[])
    def test_relative_not_edge(self):
        a=alt(E,F,'fr');a.update(eligible=False,problems=['not_absolute']);r=self.run_check([cap(E,[a])]);self.assertEqual(r['edges'],[]);self.assertIn('hreflang_declaration_ineligible',self.rules(r))
    def test_stale_capture_not_current(self):self.assertEqual(self.run_check([cap(E,[alt(E,F,'fr')],captured_at='2020-01-01T00:00:00Z')])['edges'],[])
    def test_failed_latest_does_not_resurrect_old(self):
        a=cap(E,[alt(E,F,'fr')],captured_at='2026-09-17T03:00:00Z');b=cap(E,state='failed');self.assertEqual(self.run_check([a,b])['edges'],[])
    def test_entity_mismatch_requires_explicit_map(self):
        assets=[{'url':E,'entity_id':'bitcoin','locale':'en','published':True},{'url':F,'entity_id':'ethereum','locale':'fr','published':True}];self.assertIn('hreflang_entity_mapping_mismatch',self.rules(self.run_check(self.pair(),assets)))
    def test_unpublished_translation_not_missing(self):
        a=[{'url':F,'entity_id':'a','locale':'fr','published':False}];self.assertNotIn('published_variant_not_declared',self.rules(self.run_check([cap(E)],a)))
    def test_published_same_entity_missing(self):
        a=[{'url':E,'entity_id':'a','locale':'en','published':True},{'url':F,'entity_id':'a','locale':'fr','published':True}];self.assertIn('published_variant_not_declared',self.rules(self.run_check([cap(E)],a)))
    def test_parameter_identity_preserved(self):
        r=self.run_check([cap(E,[alt(E,F+'?coin=2','fr')])]);self.assertEqual(r['edges'][0]['target_url'],F+'?coin=2')
    def test_initial_rendered_conflict_preserved(self):
        cs=[cap(E,[alt(E,F,'fr')],representation='initial_html'),cap(E,[alt(E,J,'fr')])];self.assertIn('hreflang_locale_conflict',self.rules(self.run_check(cs)))
    def test_no_alternates_no_invented_requirement(self):self.assertEqual(self.run_check([cap(E)])['observations'],[])
