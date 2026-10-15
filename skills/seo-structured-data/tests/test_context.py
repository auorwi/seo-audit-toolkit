from support import StructuredTest,URL,AT
from test_rules import entity

def capture(**kw):return {'url':URL,'snapshot_id':'dom1','document_sha256':'a'*64,'captured_at':'2026-09-17T01:00:00Z','representation':'rendered_html','readiness':'ready','visible_text':'Bitcoin (BTC) Price $12.00 Download BingX App','entities':[entity('Offer',{'price':'$12.00','priceCurrency':'USD'},id=URL+'#offer')],**kw}
def context(**kw):return {'url':URL,'snapshot_id':'dom1','document_sha256':'a'*64,'checked_at':'2026-09-17T01:00:00Z','source':'Codex visible DOM review','profile':None,'checks':[],**kw}
def check(**kw):return {'entity_id':URL+'#offer','field':'price','schema_value':'$12.00','visible_quote':'$12.00','selector':'.price','status':'format_issue','reason':'Currency symbol mixed with numeric price','recommended_value':'12.00','update_rule':'Serialize actual numeric API value, not localized display text.','observed_at':'2026-09-17T01:00:00Z',**kw}
class ContextTests(StructuredTest):
    def run_review(self,c=None,ctx=None):return self.module('context').review_context(c or capture(),ctx or context(),at=AT)
    def test_profile_requires_actual_visible_evidence_and_binding(self):
        profile={'name':'google_software_app','applicable':True,'quote':'Download BingX App','reason':'Actual app download page'}
        r=self.run_review(ctx=context(profile=profile));self.assertEqual(r['profile'],'google_software_app');self.assertEqual(r['gaps'],[])
    def test_coin_page_not_forced_into_product_snippet_profile(self):
        r=self.run_review(ctx=context(profile={'name':'google_product_snippet','applicable':False,'quote':'Bitcoin (BTC) Price','reason':'Price information page; merchant applicability not established'}));self.assertIsNone(r['profile']);self.assertTrue(r['pending'])
    def test_bad_profile_quote_or_document_binding_rejected(self):
        for ctx in [context(document_sha256='b'*64),context(profile={'name':'google_product_snippet','applicable':True,'quote':'Buy a physical product','reason':'wrong'})]:
            r=self.run_review(ctx=ctx);self.assertIsNone(r['profile']);self.assertTrue(r['gaps'])
    def test_field_check_binds_current_schema_value_and_visible_quote(self):
        r=self.run_review(ctx=context(checks=[check()]));self.assertEqual(len(r['observations']),1);self.assertEqual(r['examples'][0]['recommended_value'],'12.00');self.assertTrue(r['examples'][0]['example_only'])
    def test_wrong_schema_value_quote_or_field_is_gap(self):
        for kw in [{'schema_value':'$99'},{'visible_quote':'$99'},{'field':'missing'},{'entity_id':'#wrong'}]:
            r=self.run_review(ctx=context(checks=[check(**kw)]));self.assertFalse(r['observations']);self.assertTrue(r['gaps'])
    def test_price_example_cannot_invent_zero_or_different_numeric_value(self):
        for value in ['0','13.00']:
            r=self.run_review(ctx=context(checks=[check(recommended_value=value)]));self.assertFalse(r['examples']);self.assertTrue(r['gaps'])
    def test_unready_source_or_old_capture_does_not_certify_visible_content(self):
        for kw in [{'readiness':'pending'},{'representation':'initial_html'},{'captured_at':'2020-01-01T00:00:00Z'}]:
            r=self.run_review(c=capture(**kw),ctx=context(checks=[check()]));self.assertFalse(r['examples']);self.assertTrue(r['gaps'])
    def test_current_field_mismatch_is_review_not_search_engine_verdict(self):
        r=self.run_review(ctx=context(checks=[check(status='mismatch',visible_quote='$12.00',recommended_value=None)]));self.assertEqual(r['observations'][0]['classification'],'visible_content_review')
    def test_missing_context_stays_pending_not_all_valid(self):
        r=self.module('context').review_context(capture(),None,at=AT);self.assertTrue(r['pending']);self.assertTrue(r['gaps'])
    def test_rating_examples_are_not_fabricated_from_missing_visible_values(self):
        c=capture(entities=[entity('AggregateRating',{'ratingValue':'bad'},id=URL+'#rating')])
        r=self.run_review(c,context(checks=[check(entity_id=URL+'#rating',field='ratingValue',schema_value='bad',visible_quote='Download BingX App',recommended_value='4.9')]))
        self.assertFalse(r['examples']);self.assertTrue(r['gaps'])
    def test_conflicting_same_path_in_other_script_does_not_break_precise_review_binding(self):
        a=entity('Offer',{'price':'$12.00'},id=URL+'#offer');a.update(script_index=0,path='$[0]')
        b=entity('Offer',{'price':'$99.00'},id=URL+'#offer');b.update(script_index=1,path='$[0]')
        r=self.run_review(capture(entities=[a,b]),context(checks=[check(script_index=0,entity_path='$[0]')]))
        self.assertEqual(len(r['observations']),1);self.assertEqual(r['examples'][0]['recommended_value'],'12.00')
        self.assertEqual(r['observations'][0].get('script_index'),0);self.assertEqual(r['observations'][0].get('entity_path'),'$[0]')
