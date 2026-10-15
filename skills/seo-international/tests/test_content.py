from support import InternationalTest,AT
from test_clusters import cap,E,F
def review(c,language='fr',**kw):return {'url':c['url'],'snapshot_id':c['snapshot_id'],'document_sha256':c['document_sha256'],'reviewed_at':AT,'source':'analyst actual main inspection','method':'human_review','confidence':'high','body_language':language,'quotes':['Bonjour le monde'],'entity_id':'bitcoin',**kw}
def french(**kw):return cap(F,visible_main='Bonjour le monde. Le prix du Bitcoin.',html_langs=['fr'],**kw)
class ContentTests(InternationalTest):
    def run_check(self,cs,rs,assets=None):return self.module('content').review_content(cs,rs,assets or [],at=AT)
    def rules(self,r):return [o['rule'] for o in r['observations']]
    def test_language_match_no_issue(self):
        c=french();self.assertEqual(self.run_check([c],[review(c)])['observations'],[])
    def test_html_body_mismatch(self):
        c=french();c['html_langs']=['en'];self.assertIn('html_body_language_mismatch',self.rules(self.run_check([c],[review(c)])))
    def test_schema_body_mismatch_candidate(self):
        c=french(schema_languages=[{'value':'en','path':'$.inLanguage'}]);self.assertIn('schema_body_language_review',self.rules(self.run_check([c],[review(c)])))
    def test_route_prefix_not_language_evidence(self):self.assertNotIn('route_body_language_mismatch',self.rules(self.run_check([french()],[])))
    def test_expected_route_map_body_mismatch(self):
        c=french();a=[{'url':F,'locale':'id','entity_id':'bitcoin'}];self.assertIn('route_body_language_mismatch',self.rules(self.run_check([c],[review(c)],a)))
    def test_bad_hash_not_used(self):
        c=french();r=review(c,document_sha256='b'*64);self.assertTrue(self.run_check([c],[r])['gaps']);self.assertEqual(self.run_check([c],[r])['body_reviews'],[])
    def test_quote_not_in_visible_main_rejected(self):
        c=french();self.assertEqual(self.run_check([c],[review(c,quotes=['invented text'])])['body_reviews'],[])
    def test_missing_visible_main_not_raw_html(self):
        c=cap(F);self.assertEqual(self.run_check([c],[review(c)])['body_reviews'],[])
    def test_low_confidence_not_confirmed(self):
        c=french();self.assertEqual(self.run_check([c],[review(c,confidence='low')])['body_reviews'],[])
    def test_unready_not_reviewed(self):
        c=french(readiness='unknown_timeout');self.assertEqual(self.run_check([c],[review(c)])['body_reviews'],[])
    def test_old_review_does_not_override_new(self):
        old=french(snapshot_id='old',captured_at='2026-09-17T02:00:00Z');new=french(snapshot_id='new');self.assertEqual(self.run_check([old,new],[review(old)])['body_reviews'],[])
    def test_cross_language_canonical_needs_both_bodies(self):
        c=french(canonicals=[{'target_url':E}]);r=self.run_check([c],[review(c)]);self.assertNotIn('translated_body_cross_language_canonical',self.rules(r));self.assertTrue(r['gaps'])
    def test_translated_body_cross_language_canonical(self):
        c=french(canonicals=[{'target_url':E}]);e=cap(E,visible_main='Hello world',html_langs=['en']);r=self.run_check([c,e],[review(c),review(e,'en',quotes=['Hello world'])]);self.assertIn('translated_body_cross_language_canonical',self.rules(r))
    def test_same_language_regional_canonical_not_failure(self):
        c=french(canonicals=[{'target_url':E}]);e=cap(E,visible_main='Bonjour le monde');self.assertNotIn('translated_body_cross_language_canonical',self.rules(self.run_check([c,e],[review(c),review(e)])))
    def test_different_canonical_entity(self):
        c=french(canonicals=[{'target_url':E}]);e=cap(E,visible_main='Bonjour le monde');self.assertIn('canonical_entity_review',self.rules(self.run_check([c,e],[review(c),review(e,entity_id='ethereum')])))
    def test_required_business_field_missing(self):
        c=french(visible_fields={'country':False});r=self.run_check([c],[review(c)],[{'url':F,'required_fields':['country']}]);self.assertIn('localized_required_field_missing',self.rules(r))
    def test_unknown_business_field_not_missing(self):
        c=french();r=self.run_check([c],[review(c)],[{'url':F,'required_fields':['country']}]);self.assertNotIn('localized_required_field_missing',self.rules(r));self.assertTrue(r['gaps'])
    def test_declared_region_does_not_prove_wrong_body(self):
        c=french();c['html_langs']=['fr-CA'];self.assertEqual(self.run_check([c],[review(c,'fr-FR')])['observations'],[])
    def test_review_does_not_bind_to_other_entry_canonical(self):
        direct=french(snapshot_id='direct');clicked=french(snapshot_id='clicked',entry_mode='switch',canonicals=[{'target_url':E}]);e=cap(E,visible_main='Hello world',html_langs=['en']);r=self.run_check([direct,clicked,e],[review(direct),review(e,'en',quotes=['Hello world'])]);self.assertNotIn('translated_body_cross_language_canonical',self.rules(r))
    def test_body_review_before_snapshot_is_invalid(self):
        c=french();self.assertEqual(self.run_check([c],[review(c,reviewed_at='2026-09-17T03:59:00Z')])['body_reviews'],[])
    def test_explicit_script_mismatch(self):
        c=french();c['html_langs']=['zh-Hans'];self.assertIn('html_body_script_mismatch',self.rules(self.run_check([c],[review(c,'zh-Hant')])) )
    def test_invalid_html_language_not_silently_passed(self):
        c=french();c['html_langs']=['xx'];self.assertIn('html_lang_code_review',self.rules(self.run_check([c],[review(c)])))
    def test_conflicting_peer_languages_require_review(self):
        c=french(canonicals=[{'target_url':E}]);en=cap(E,snapshot_id='en-direct',visible_main='Hello world');fr=cap(E,snapshot_id='en-switch',entry_mode='switch',visible_main='Bonjour le monde');r=self.run_check([c,en,fr],[review(c),review(fr),review(en,'en',quotes=['Hello world'])]);self.assertNotIn('translated_body_cross_language_canonical',self.rules(r));self.assertIn('body_review_variants_conflict',[g['reason'] for g in r['gaps']])
