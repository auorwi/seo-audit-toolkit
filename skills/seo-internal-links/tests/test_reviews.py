from support import LinkTest,URL,AT
from test_graph import A,B,C,D,link,capture
class ReviewTests(LinkTest):
    def review(self,cs,targets=None,**kw):
        g=self.module('graph').build_graph(cs,[A,B,C,D],{'home':[A]},at=AT)
        return self.module('reviews').review_links(cs,g,targets or {'targets':[]},at=AT,**kw)
    def test_one_broken_target_collects_every_observed_source_and_position(self):
        cs=[capture(A,[link(C),link(C,locator='a[1]')]),capture(B,[link(C)])]
        r=self.review(cs,{'targets':[{'requested_url':C,'kind':'broken_http_target','status':404,'chain':[]}]});f=next(x for x in r['findings'] if x['rule']=='broken_http_target')
        self.assertEqual(f['url'],C);self.assertEqual(f['source_urls'],[A,B]);self.assertEqual(len(f['link_occurrences']),3)
    def test_target_findings_stable_when_sources_or_count_change(self):
        target={'targets':[{'requested_url':C,'kind':'broken_http_target','status':404,'chain':[]}]}
        a=self.review([capture(A,[link(C)])],target);b=self.review([capture(A,[link(C)]),capture(B,[link(C)])],target)
        self.assertEqual(next(x['issue_id'] for x in a['findings'] if x['rule']=='broken_http_target'),next(x['issue_id'] for x in b['findings'] if x['rule']=='broken_http_target'))
    def test_redirect_suggestion_requires_equivalence_not_blind_final_url(self):
        r=self.review([capture(A,[link(C)])],{'targets':[{'requested_url':C,'final_url':D,'kind':'redirected_link','chain':[]}]});f=next(x for x in r['findings'] if x['rule']=='redirected_link');self.assertTrue(f['target_equivalence_required'])
    def test_unfetched_target_not_emitted_as_broken(self):
        r=self.review([capture(A,[link(C)])],{'targets':[{'requested_url':C,'kind':'not_observed'}]});self.assertFalse(any(x['rule']=='broken_http_target' for x in r['findings']))
    def test_empty_anchor_is_candidate_and_aria_hint_kept(self):
        c=capture(A,[link(C,seo_text_candidate='',aria_label='Logo')]);r=self.review([c]);f=next(x for x in r['findings'] if x['rule']=='empty_anchor_text_candidate');self.assertEqual(f['classification'],'review');self.assertFalse(f['accessible_name_failure_proven'])
    def test_image_alt_text_prevents_false_empty_anchor_candidate(self):
        r=self.review([capture(A,[link(C,seo_text_candidate='Bitcoin guide')])]);self.assertFalse(any(x['rule']=='empty_anchor_text_candidate' for x in r['findings']))
    def test_nohref_anchor_is_review_but_mailto_and_regular_button_not_errors(self):
        links=[link(None,href=None,kind='missing_href',http_link=False),link(None,href='mailto:help@bingx.com',kind='non_http_href',http_link=False,locator='a[1]')]
        r=self.review([capture(A,links)]);self.assertEqual(len([x for x in r['findings'] if x['rule']=='anchor_http_destination_missing']),1)
    def test_language_switch_not_guessed_wrong_from_path(self):
        r=self.review([capture(A,[link('https://bingx.com/fr/',hreflang='fr')])]);self.assertFalse(any('language' in x['rule'] for x in r['findings']))
    def test_internal_nofollow_is_hint_not_discovery_block(self):
        r=self.review([capture(A,[link(C,rel=['nofollow'])])]);f=next(x for x in r['findings'] if x['rule']=='internal_nofollow_review');self.assertFalse(f['discovery_block_proven'])
    def test_old_failed_capture_links_not_reviewed_as_current(self):
        c=capture(A,[link(C,seo_text_candidate='')],snapshot_id='old');bad=capture(A,[],snapshot_id='bad',state='timeout',captured_at='2026-09-17T02:30:00Z')
        r=self.review([c,bad]);self.assertFalse(any(x['rule']=='empty_anchor_text_candidate' for x in r['findings']))
    def test_inventory_orphans_remain_separate_candidates_not_confirmed_failures(self):
        r=self.review([capture(A,[link(B)])]);self.assertIn(D,r['orphan_candidates']);self.assertFalse(any(x['rule']=='confirmed_orphan' for x in r['findings']))
    def test_parameter_growth_hint_has_examples_and_no_infinite_claim(self):
        links=[link(B+'?sort='+x) for x in ['a','b','c']];r=self.review([capture(A,links)],parameter_variant_hint=3)
        f=next(x for x in r['findings'] if x['rule']=='parameter_growth_review');self.assertEqual(f['variant_count'],3);self.assertFalse(f['infinite_trap_proven']);self.assertEqual(len(f['examples']),3)
    def test_declared_pagination_parameter_not_flagged_as_trap(self):
        links=[link(B+'?page='+str(x)) for x in range(1,5)];r=self.review([capture(A,links)],parameter_variant_hint=3,expected_parameters=['page'])
        self.assertFalse(any(x['rule']=='parameter_growth_review' for x in r['findings']))
    def test_empty_href_remains_destination_review_even_if_resolved_to_self(self):
        r=self.review([capture(A,[link(A,href='',kind='empty_href',same_document=True)])]);self.assertTrue(any(x['rule']=='anchor_http_destination_missing' for x in r['findings']))
