from support import TdkTest,AT
from test_context import capture,context,fact

def review(**kw):
    return {'snapshot_id':'dom1','document_sha256':'a'*64,'checked_at':'2026-09-17T00:00:00Z','source':'Codex review of saved evidence','topic':'search_intent','status':'needs_change',
        'quotes':[{'field':'body_text','text':'SOLV Project Details'}],'fact_ids':['page'],'reason':'Identify the actual project explicitly.',
        'proposed':{'title':'SOLV Project Details | BingX','description':'Explore SOLV project details.'},'language':'en','update_rule':'Update entity from verified project record; no availability claims.',**kw}
class ReviewTests(TdkTest):
    def assess(self,rows=None,blocked=False):
        ctx=context(reviews=rows if rows is not None else [review()]);v=self.module('context').validate_context(capture(),ctx,at=AT)
        return self.module('reviews').review_drafts(capture(),v,rewrite_blocked=blocked,at=AT)
    def test_valid_draft_keeps_facts_and_is_not_auto_publish(self):
        r=self.assess();self.assertEqual(len(r['drafts']),1);self.assertEqual(r['drafts'][0]['status'],'draft_requires_editorial_review');self.assertEqual(r['drafts'][0]['fact_ids'],['page'])
    def test_wrong_snapshot_hash_old_time_quote_rejected(self):
        for kw in [{'snapshot_id':'old'},{'document_sha256':'b'*64},{'checked_at':'2020-01-01T00:00:00Z'},{'quotes':[{'field':'body_text','text':'ETH'}]}]:
            r=self.assess([review(**kw)]);self.assertFalse(r['drafts']);self.assertTrue(r['gaps'])
    def test_missing_fact_reference_or_source_rejected(self):
        for kw in [{'fact_ids':['not-observed']},{'fact_ids':[]},{'source':''}]:self.assertFalse(self.assess([review(**kw)])['drafts'])
    def test_route_mismatch_blocks_rewrite(self):
        r=self.assess(blocked=True);self.assertFalse(r['drafts']);self.assertTrue(r['withheld'])
    def test_proposed_guaranteed_returns_are_withheld(self):
        r=self.assess([review(proposed={'title':'SOLV guaranteed profit | BingX'})]);self.assertFalse(r['drafts']);self.assertTrue(r['withheld'])
    def test_trading_proposal_without_catalog_confirmation_withheld(self):
        r=self.assess([review(proposed={'title':'Trade SOLV now | BingX'})]);self.assertFalse(r['drafts'])
    def test_proposed_entity_cannot_silently_change(self):
        r=self.assess([review(proposed={'title':'ETH Project | BingX'})]);self.assertFalse(r['drafts'])
    def test_wrong_language_and_missing_update_rule_do_not_pass(self):
        for kw in [{'language':'ja'},{'update_rule':''}]:self.assertFalse(self.assess([review(**kw)])['drafts'])
    def test_unknown_review_remains_pending(self):
        r=self.assess([review(status='unknown')]);self.assertFalse(r['drafts']);self.assertTrue(r['pending'])
    def test_review_does_not_clear_unreviewed_topics(self):
        r=self.assess();self.assertIn('language_and_wording',r['pending'])
    def test_unmatched_listed_catalog_cannot_authorize_trade_draft(self):
        from test_context import external_fact
        status=external_fact('status','listing_status','listed','product_catalog',text='ETH spot listed')
        status['subject']={'entity':'ETH','product':'spot','market_scope':'unknown'}
        ctx=context(facts=[fact(),status],reviews=[review(proposed={'title':'Trade SOLV now | BingX'})])
        v=self.module('context').validate_context(capture(),ctx,at=AT)
        r=self.module('reviews').review_drafts(capture(),v,rewrite_blocked=False,at=AT)
        self.assertFalse(r['drafts'])
