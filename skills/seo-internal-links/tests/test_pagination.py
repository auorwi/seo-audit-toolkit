import copy
from support import LinkTest,AT
from test_graph import link
URL='https://bingx.com/en/price'
def page(id='before',url=URL,items=None,**kw):return {'url':url,'snapshot_id':id,'document_sha256':('a' if id=='before' else 'b')*64,'captured_at':'2026-09-17T02:00:00Z' if id=='before' else '2026-09-17T02:02:00Z','readiness':'ready','source':'actual controlled browser fixture','item_keys':items if items is not None else ['BTC','ETH'],'links':[],**kw}
def action(**kw):return {'source':'actual browser click fixture','before_snapshot':'before','after_snapshot':'after','before_document_sha256':'a'*64,'after_document_sha256':'b'*64,'clicked_at':'2026-09-17T02:01:00Z','selector':'button.next','control':{'tag':'button','text':'Next','disabled':False,'href':None},**kw}
class PaginationTests(LinkTest):
    def review(self,b=None,a=None,d=None,act=None):return self.module('pagination').review_pagination(b or page(),a or page('after',items=['SOL','XRP']),act or action(),direct=d,at=AT)
    def rules(self,r):return {x['rule'] for x in r['observations']}
    def test_changed_items_same_url_reported_without_claiming_all_items_unindexable(self):
        r=self.review();self.assertIn('pagination_same_document_address',self.rules(r));self.assertFalse(r['all_items_unindexable_proven'])
    def test_hash_only_change_is_same_document_address(self):
        r=self.review(a=page('after',url=URL+'#page2',items=['SOL']));self.assertIn('pagination_same_document_address',self.rules(r))
    def test_query_url_and_real_anchor_allow_discovery_observation(self):
        b=page(links=[link(URL+'?page=2')]);a=page('after',url=URL+'?page=2',items=['SOL']);d=page('direct',url=URL+'?page=2',items=['SOL'])
        r=self.review(b,a,d);self.assertNotIn('pagination_href_not_observed',self.rules(r));self.assertEqual(r['direct_result'],'same_items_observed')
    def test_clickable_button_without_discoverable_href_remains_review(self):
        r=self.review(a=page('after',url=URL+'?page=2',items=['SOL']));self.assertIn('pagination_href_not_observed',self.rules(r))
    def test_button_with_other_real_page_link_not_false_missing_href(self):
        b=page(links=[link(URL+'?page=2',locator='a.page2')]);r=self.review(b,a=page('after',url=URL+'?page=2',items=['SOL']));self.assertNotIn('pagination_href_not_observed',self.rules(r))
    def test_noscript_link_alone_not_regular_rendered_discovery_proof(self):
        b=page(links=[link(URL+'?page=2',conditional_noscript=True)]);r=self.review(b,a=page('after',url=URL+'?page=2',items=['SOL']));self.assertIn('pagination_href_not_observed',self.rules(r))
    def test_direct_route_returns_wrong_items_is_separate_observation(self):
        r=self.review(a=page('after',url=URL+'?page=2',items=['SOL']),d=page('direct',url=URL+'?page=2',items=['BTC']));self.assertEqual(r['direct_result'],'different_items_observed');self.assertIn('pagination_direct_content_difference',self.rules(r))
    def test_direct_missing_unready_or_wrong_url_not_pass(self):
        for d in [None,page('direct',readiness='unknown_timeout'),page('direct',url='https://bingx.com/en/download')]:
            r=self.review(d=d);self.assertEqual(r['direct_result'],'unverified');self.assertTrue(r['gaps'])
    def test_stale_or_unready_or_missing_identity_snapshots_not_compared(self):
        for kw in [{'captured_at':'2020-01-01T00:00:00Z'},{'readiness':'pending'},{'item_keys':[]}]:
            r=self.review(b=page(**kw));self.assertFalse(r['observations']);self.assertTrue(r['gaps'])
    def test_action_document_binding_required(self):
        r=self.review(act=action(before_document_sha256='c'*64));self.assertFalse(r['observations']);self.assertTrue(r['gaps'])
    def test_action_time_outside_capture_sequence_not_valid_transition(self):
        r=self.review(act=action(clicked_at='2026-09-17T02:03:00Z'));self.assertFalse(r['observations']);self.assertTrue(r['gaps'])
    def test_unchanged_items_are_unknown_transition_not_proof_of_success(self):
        r=self.review(a=page('after'));self.assertEqual(r['transition'],'items_unchanged');self.assertNotIn('pagination_same_document_address',self.rules(r))
    def test_disabled_last_page_control_not_pagination_failure(self):
        r=self.review(act=action(control={'tag':'button','text':'Next','disabled':True,'href':None}));self.assertEqual(r['transition'],'disabled_control');self.assertFalse(r['observations'])
    def test_input_objects_not_mutated(self):
        b=page();before=copy.deepcopy(b);self.review(b=b);self.assertEqual(b,before)
    def test_actual_pagination_href_not_lost_when_client_url_fails_to_update(self):
        dest='https://bingx.com/price/page/2';b=page(links=[link(dest)]);a=page('after',items=['SOL']);d=page('direct',url=dest,items=['SOL'])
        act=action(control={'tag':'a','href':'/price/page/2','text':'2','disabled':False})
        r=self.review(b,a,d,act);self.assertNotIn('pagination_href_not_observed',self.rules(r));self.assertEqual(r.get('declared_target_url'),dest);self.assertEqual(r['direct_result'],'same_items_observed')
    def test_direct_redirect_can_compare_items_if_requested_url_is_bound(self):
        dest=URL+'?page=2';b=page(links=[link(dest)]);a=page('after',url=dest,items=['SOL']);d=page('direct',url=URL+'/page/2',items=['SOL'],requested_url=dest)
        r=self.review(b,a,d);self.assertEqual(r['direct_result'],'same_items_observed')
