from support import LinkTest,AT
from test_graph import A,B,C,D,link,capture
from test_targets import response
class AuditTests(LinkTest):
    def audit(self,**kw):
        inputs={'captures':[capture(A,[link(C)])],'http_records':[response(C,404)],'assets':[A,B,C,D],'seeds':{'home':[A]},'pagination':[],'language_expectations':[],'gaps':[],**kw}
        return self.module('audit').audit(inputs,at=AT)
    def test_graph_target_join_preserves_source_for_repair(self):
        r=self.audit();f=next(x for x in r['findings'] if x['rule']=='broken_http_target');self.assertEqual(f['source_urls'],[A]);self.assertEqual(r['graph']['paths']['home'][C]['depth'],1)
    def test_asset_without_links_kept_as_candidate_and_unobserved_target(self):
        r=self.audit();self.assertIn(D,r['orphan_candidates']);self.assertFalse(r['coverage']['full_site']);self.assertTrue(r['gaps'])
    def test_pagination_interaction_items_not_counted_as_initial_discovery(self):
        from test_pagination import page,action
        b=page();a=page('after',items=['SOL']);b.update(representation='rendered_html',links=[],entry_mode='direct');a.update(representation='rendered_html',links=[link(C)],entry_mode='pagination',discovery_mode='interaction_only')
        r=self.audit(captures=[b,a],assets=[b['url'],C],seeds={'category':[b['url']]},pagination=[{'before':'before','after':'after','action':action()}]);self.assertFalse(r['graph']['edges']);self.assertTrue(r['pagination'][0]['observations'])
    def test_missing_pagination_snapshot_explicit_gap(self):
        r=self.audit(pagination=[{'before':'missing','after':'missing','action':{}}]);self.assertTrue(any(g['reason']=='pagination_snapshot_missing' for g in r['gaps']))
    def test_wrong_language_expectation_handoff_preserved(self):
        from test_language import expectation
        r=self.audit(captures=[capture(A,[link(C)]),capture(C,[],html_lang='en')],language_expectations=[expectation()]);self.assertTrue(any(x['rule']=='target_declared_language_mismatch' for x in r['findings']))
    def test_conflicting_asset_metadata_not_silently_overwritten(self):
        with self.assertRaises(ValueError):self.audit(assets=[{'url':A,'locale':'en'},{'url':A,'locale':'fr'}])
    def test_input_gaps_preserved_even_when_some_graph_edges_valid(self):
        r=self.audit(gaps=[{'reason':'damaged_capture','url':B}]);self.assertTrue(any(g['reason']=='damaged_capture' for g in r['gaps']));self.assertTrue(r['graph']['edges'])
    def test_fixed_timestamp_replay_produces_stable_issue_ids(self):
        self.assertEqual([f['issue_id'] for f in self.audit()['findings']],[f['issue_id'] for f in self.audit()['findings']])
