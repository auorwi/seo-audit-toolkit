from support import LinkTest,AT
from test_graph import A,C,link,capture

def expectation(**kw):return {'source_url':A,'source_snapshot':A,'source_document_sha256':'a'*64,'locator':'a[0]','target_url':C,'expected_language':'fr','purpose':'content_navigation','source':'review of verified locale route map fixture','checked_at':'2026-09-17T02:30:00Z',**kw}
class LanguageTests(LinkTest):
    def check(self,cs=None,es=None):return self.module('language').review_language(cs or [capture(A,[link(C)]),capture(C,[],html_lang='en')],es if es is not None else [expectation()],at=AT)
    def test_explicit_expected_locale_and_actual_target_declaration_mismatch(self):
        r=self.check();self.assertEqual(r['observations'][0]['rule'],'target_declared_language_mismatch');self.assertEqual(r['observations'][0]['observed_language'],'en');self.assertEqual(r['observations'][0]['handoff_skill'],'010')
    def test_no_expectation_not_inferred_from_route(self):self.assertEqual(self.check(es=[])['observations'],[])
    def test_language_selector_intentionally_crosses_languages(self):self.assertEqual(self.check(es=[expectation(purpose='language_switch')])['observations'],[])
    def test_same_primary_language_region_not_misclassified(self):
        r=self.check(cs=[capture(A,[link(C)]),capture(C,[],html_lang='fr-CA')]);self.assertFalse(r['observations'])
    def test_mismatched_source_snapshot_or_link_not_used(self):
        for kw in [{'source_document_sha256':'c'*64},{'locator':'a[99]'},{'target_url':'https://bingx.com/wrong'}]:
            r=self.check(es=[expectation(**kw)]);self.assertFalse(r['observations']);self.assertTrue(r['gaps'])
    def test_missing_target_language_is_unknown_not_wrong(self):
        r=self.check(cs=[capture(A,[link(C)]),capture(C,[])]);self.assertFalse(r['observations']);self.assertTrue(r['gaps'])
    def test_latest_failed_target_does_not_use_older_language(self):
        cs=[capture(A,[link(C)]),capture(C,[],html_lang='en',snapshot_id='old'),capture(C,[],state='timeout',snapshot_id='new',captured_at='2026-09-17T02:20:00Z')]
        r=self.check(cs);self.assertFalse(r['observations']);self.assertTrue(r['gaps'])
    def test_stale_expectation_not_current_configuration_proof(self):
        r=self.check(es=[expectation(checked_at='2020-01-01T00:00:00Z')]);self.assertFalse(r['observations']);self.assertTrue(r['gaps'])
    def test_verified_redirect_uses_actual_final_document_language(self):
        dest='https://bingx.com/zh-tc/price/page/2';cs=[capture(A,[link(C)]),capture(dest,[],html_lang='zh-Hant')]
        r=self.module('language').review_language(cs,[expectation(expected_language='en')],at=AT,target_assessments=[{'requested_url':C,'final_url':dest,'kind':'redirected_link'}])
        self.assertEqual(r['observations'][0]['observed_language'],'zh-Hant');self.assertEqual(r['observations'][0]['target_url'],C);self.assertEqual(r['observations'][0]['final_url'],dest)
    def test_unverified_redirect_cannot_bind_unrelated_final_document(self):
        dest='https://bingx.com/zh-tc/price/page/2';cs=[capture(A,[link(C)]),capture(dest,[],html_lang='zh-Hant')]
        r=self.module('language').review_language(cs,[expectation(expected_language='en')],at=AT,target_assessments=[{'requested_url':C,'final_url':dest,'kind':'redirect_target_unverified'}]);self.assertFalse(r['observations']);self.assertTrue(r['gaps'])
    def test_source_binding_uses_latest_within_observed_entry_not_other_interaction_phase(self):
        cs=[capture(A,[link(C)]),capture(A,[link(C)],entry_mode='pagination',snapshot_id='clicked',captured_at='2026-09-17T02:20:00Z'),capture(C,[],html_lang='en')]
        r=self.check(cs);self.assertTrue(r['observations']);self.assertFalse(r['gaps'])
    def test_old_source_with_newer_same_entry_not_used(self):
        cs=[capture(A,[link(C)]),capture(A,[link(C)],snapshot_id='newer',captured_at='2026-09-17T02:20:00Z'),capture(C,[],html_lang='en')]
        r=self.check(cs);self.assertFalse(r['observations']);self.assertTrue(r['gaps'])
