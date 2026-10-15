import copy
from support import LinkTest,URL,AT
A='https://bingx.com/en/';B='https://bingx.com/en/price';C=URL;D='https://bingx.com/en/price/ethereum'
def link(target,**kw):return {'target':target,'href':target,'http_link':True,'internal':True,'same_document':False,'conditional_noscript':False,'locator':'a[0]','rel':[],'component':'main','anchor_text':'Details',**kw}
def capture(url,links,**kw):return {'url':url,'snapshot_id':url,'document_sha256':'a'*64,'captured_at':'2026-09-17T02:00:00Z','source':'controlled HTML fixture','representation':'rendered_html','readiness':'ready','entry_mode':'direct','state':'completed','links':links,**kw}
class GraphTests(LinkTest):
    def graph(self,captures,assets=None,seeds=None,**kw):return self.module('graph').build_graph(captures,assets or [A,B,C,D],seeds or {'home':[A],'category':[B]},at=AT,**kw)
    def test_observed_shortest_path_by_distinct_entry_groups(self):
        r=self.graph([capture(A,[link(B)]),capture(B,[link(C)])]);self.assertEqual(r['paths']['home'][C]['depth'],2);self.assertEqual(r['paths']['home'][C]['path'],[A,B,C]);self.assertEqual(r['paths']['category'][C]['depth'],1)
    def test_repeated_navigation_deduplicates_graph_but_preserves_all_sources(self):
        r=self.graph([capture(A,[link(C,component='header'),link(C,component='footer',locator='a[1]')]),capture(B,[link(C)])]);self.assertEqual(len(r['edges']),2);self.assertEqual(r['nodes'][C]['observed_inbound_sources'],[A,B]);self.assertEqual(len(next(x for x in r['edges'] if x['source']==A)['occurrences']),2)
    def test_source_and_rendered_observations_do_not_double_inbound_count(self):
        r=self.graph([capture(A,[link(C)],snapshot_id='source',representation='initial_html',readiness=None),capture(A,[link(C)],snapshot_id='dom')]);self.assertEqual(r['nodes'][C]['inbound_source_count'],1);self.assertEqual(len(r['edges'][0]['occurrences']),2)
    def test_no_inbound_is_observed_candidate_never_absolute_orphan(self):
        r=self.graph([capture(A,[link(B)])]);self.assertEqual(r['nodes'][D]['status'],'no_observed_inbound_candidate');self.assertFalse(r['coverage']['full_site']);self.assertIsNone(r['paths']['home'][D]['depth'])
    def test_self_link_does_not_clear_orphan_candidate(self):
        r=self.graph([capture(D,[link(D,same_document=True)])]);self.assertEqual(r['nodes'][D]['inbound_source_count'],0);self.assertEqual(r['nodes'][D]['status'],'no_observed_inbound_candidate')
    def test_cycle_with_inbound_but_no_seed_path_is_unreachable_not_orphan(self):
        r=self.graph([capture(C,[link(D)]),capture(D,[link(C)])]);self.assertEqual(r['nodes'][C]['status'],'observed_inbound');self.assertIsNone(r['paths']['home'][C]['depth'])
    def test_nofollow_path_preserved_as_observation_not_guaranteed_followed(self):
        r=self.graph([capture(A,[link(C,rel=['nofollow'])])]);self.assertEqual(r['paths']['home'][C]['depth'],1);self.assertTrue(r['edges'][0]['all_observed_links_nofollow']);self.assertFalse(r['coverage']['engine_discovery_proven'])
    def test_external_and_conditional_noscript_links_excluded_with_counts(self):
        r=self.graph([capture(A,[link(C,conditional_noscript=True),link('https://example.com/',internal=False)])]);self.assertFalse(r['edges']);self.assertEqual(r['coverage']['excluded_conditional_links'],1)
    def test_query_variants_not_collapsed_into_one_page(self):
        r=self.graph([capture(A,[link(B+'?page=1'),link(B+'?page=2')])],assets=[A,B+'?page=1',B+'?page=2']);self.assertEqual(len(r['edges']),2)
    def test_failed_latest_attempt_never_falls_back_to_previous_link_graph(self):
        r=self.graph([capture(A,[link(C)],snapshot_id='old'),capture(A,[],snapshot_id='new',captured_at='2026-09-17T02:30:00Z',state='timeout')]);self.assertFalse(r['edges']);self.assertTrue(r['gaps'])
    def test_unready_and_stale_and_future_captures_do_not_supply_edges(self):
        for kw in [{'readiness':'unknown_timeout'},{'captured_at':'2020-01-01T00:00:00Z'},{'captured_at':'2027-01-01T00:00:00Z'}]:self.assertFalse(self.graph([capture(A,[link(C)],**kw)])['edges'])
    def test_unobserved_target_is_still_leaf_and_outgoing_coverage_unknown(self):
        r=self.graph([capture(A,[link(C)])]);self.assertEqual(r['paths']['home'][C]['depth'],1);self.assertFalse(r['nodes'][C]['outgoing_observed'])
    def test_deep_path_is_threshold_hint_not_ranking_error(self):
        r=self.graph([capture(A,[link(B)]),capture(B,[link(C)]),capture(C,[link(D)])],depth_hint=2);hint=next(x for x in r['depth_hints'] if x['url']==D and x['seed_group']=='home');self.assertEqual(hint['depth'],3);self.assertEqual(hint['classification'],'review_hint')
    def test_shortcut_reduces_depth_and_duplicate_order_does_not_change_paths(self):
        cs=[capture(A,[link(B),link(C)]),capture(B,[link(C)])];a=self.graph(cs);b=self.graph(list(reversed(cs)));self.assertEqual(a['paths'],b['paths']);self.assertEqual(a['paths']['home'][C]['depth'],1)
    def test_missing_seed_is_reported_not_fake_zero_coverage_success(self):
        r=self.graph([capture(B,[link(C)])]);self.assertTrue(any(g.get('reason')=='seed_source_not_observed' and g.get('url')==A for g in r['gaps']))
    def test_conflicting_identity_invalid_seed_and_invalid_threshold_rejected(self):
        a=capture(A,[]);b={**a,'links':[link(B)]}
        with self.assertRaises(ValueError):self.graph([a,b])
        with self.assertRaises(ValueError):self.module('graph').build_graph([],[],{},at=AT)
        with self.assertRaises(ValueError):self.graph([],depth_hint=-1)
    def test_source_inputs_not_mutated(self):
        cs=[capture(A,[link(C)])];before=copy.deepcopy(cs);self.graph(cs);self.assertEqual(cs,before)
    def test_click_only_link_state_not_counted_as_initial_discovery_path(self):
        r=self.graph([capture(A,[link(C)],entry_mode='pagination',discovery_mode='interaction_only')]);self.assertFalse(r['edges']);self.assertEqual(r['coverage'].get('excluded_interaction_captures'),1)
