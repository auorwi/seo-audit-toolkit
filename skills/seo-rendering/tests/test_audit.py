import json
from support import RenderingTest
from test_readiness import snapshot,URL

AT='2026-09-17T00:01:00Z'
FIELDS=['title','titles','descriptions','canonical','h1','main_text','identity','schema','links','placeholder_count','page_errors']
def sample(id='a',at='2026-09-17T00:00:01Z',**kw):
    values={'requested_url':URL,'titles':['Solv Protocol'],'descriptions':['Project'],'schema':[],'links':[],
        'visible_items':['BTC'] if id=='a' else ['ETH'],'page_indicator':'2116' if id=='a' else '2117',
        'coverage':{key:'complete' for key in FIELDS},**kw}
    return snapshot(id,at,**values)
def initial(**kw):
    return sample('initial','2026-09-17T00:00:00Z',stage='initial',**kw)

class RenderAuditTests(RenderingTest):
    def test_independent_http_is_not_proof_of_same_navigation_rendering(self):
        result=self.audit([initial(baseline_relation='independent_http'),sample(),sample('b','2026-09-17T00:00:03Z')])
        self.assertIn('initial_navigation_context_gap',self.codes(result))
        self.assertEqual(result['rows'][0].get('baseline_relation'),'independent_http')

    def test_entry_paths_compare_stable_metadata_for_same_url(self):
        samples=[initial(),sample(),sample('b','2026-09-17T00:00:03Z'),
            sample('i1','2026-09-17T00:00:10Z',entry_mode='internal',navigation_id='n2',title='Generic'),
            sample('i2','2026-09-17T00:00:12Z',entry_mode='internal',navigation_id='n2',title='Generic')]
        result=self.audit(samples,targets=[{'url':URL,'expected_entry_modes':['direct','internal']}])
        self.assertIn('entry_path_content_mismatch',self.codes(result))
        finding=next(f for f in result['findings'] if f['rule']=='entry_path_content_mismatch')
        self.assertIn('title',finding['evidence'][0]['differences'])

    def test_entry_paths_do_not_compare_unstable_or_different_environment(self):
        for extra in [[],[sample('i2','2026-09-17T00:00:12Z',entry_mode='internal',navigation_id='n2',title='Generic',environment={'device':'mobile'})]]:
            samples=[initial(),sample(),sample('b','2026-09-17T00:00:03Z'),
                sample('i1','2026-09-17T00:00:10Z',entry_mode='internal',navigation_id='n2',title='Generic',environment={'device':'mobile'}),*extra]
            result=self.audit(samples,targets=[{'url':URL,'expected_entry_modes':['direct','internal']}])
            self.assertNotIn('entry_path_content_mismatch',self.codes(result))

    def transition(self,kind='back',**kw):
        return {'id':'go','url':URL,'kind':kind,'before_id':'a','after_id':'c','source':'browser',
            'checked_at':AT,'evidence':{'path':'event.json'},'expected_url':URL,'expected_identity':'SOLV',**kw}

    def transition_samples(self,**kw):
        return [initial(),sample(),sample('b','2026-09-17T00:00:03Z',stage='interaction',phase_id='after',**kw),
            sample('c','2026-09-17T00:00:05Z',stage='interaction',phase_id='after',**kw)]

    def test_back_returning_old_entity_is_observed_mismatch(self):
        result=self.audit(self.transition_samples(identity='BTC'),interactions=[self.transition()])
        self.assertIn('interaction_identity_mismatch',self.codes(result))

    def test_internal_link_checks_expected_destination(self):
        result=self.audit(self.transition_samples(url='https://bingx.com/en/other'),interactions=[self.transition('open_internal_link')])
        self.assertIn('interaction_destination_mismatch',self.codes(result))

    def test_back_without_expected_target_cannot_claim_success(self):
        event=self.transition();del event['expected_url'];del event['expected_identity']
        result=self.audit(self.transition_samples(),interactions=[event])
        self.assertIn('interaction_expectation_gap',self.codes(result))

    def test_one_post_click_snapshot_is_not_stable_completion(self):
        result=self.audit([initial(),sample(),sample('c','2026-09-17T00:00:05Z',stage='interaction',phase_id='after')],interactions=[self.transition()])
        self.assertIn('interaction_readiness_gap',self.codes(result))

    def test_public_transition_checks_context_and_chronology(self):
        for override in [{'environment':{'device':'other'}},{'captured_at':'2026-09-16T23:59:50Z'}]:
            samples=self.transition_samples();samples[-1].update(override)
            result=self.audit(samples,interactions=[self.transition()])
            self.assertIn('interaction_evidence_gap',self.codes(result))

    def test_filter_requires_captured_items_matching_event(self):
        result=self.audit(self.transition_samples(),interactions=[self.transition('filter',before_items=['BTC'],after_items=['FAKE'])])
        self.assertIn('interaction_evidence_gap',self.codes(result))

    def test_filter_records_observed_change_and_metadata_difference(self):
        samples=self.transition_samples(title='Filtered',canonical=['https://bingx.com/en/filtered'])
        result=self.audit(samples,interactions=[self.transition('filter',before_items=['BTC'],after_items=['ETH'])])
        event=result['interactions'][0]
        self.assertEqual(event.get('verification'),'observed_stable_transition')
        self.assertEqual(event['comparison']['title'],{'before':'Solv Protocol','after':'Filtered'})
        self.assertEqual(event['comparison']['canonical']['after'],['https://bingx.com/en/filtered'])

    def test_filter_no_data_change_is_unknown_not_verified(self):
        samples=self.transition_samples(visible_items=['BTC'])
        result=self.audit(samples,interactions=[self.transition('filter',before_items=['BTC'],after_items=['BTC'])])
        self.assertIn('interaction_effect_not_observed',self.codes(result))

    def test_back_with_matching_destination_and_stable_entity_is_verified(self):
        result=self.audit(self.transition_samples(),interactions=[self.transition()])
        self.assertEqual(result['interactions'][0].get('verification'),'observed_stable_transition')

    def test_pagination_cannot_borrow_another_pages_snapshots(self):
        other='https://bingx.com/en/price/bitcoin'
        samples=[initial(),sample(requested_url=other),sample('b','2026-09-17T00:00:03Z',requested_url=other)]
        event={'id':'next','url':URL,'kind':'paginate','before_id':'a','after_id':'b','source':'browser','checked_at':AT,'evidence':{'path':'event.json'},'before_page':'2116','after_page':'2117','before_items':['BTC'],'after_items':['ETH']}
        result=self.audit(samples,interactions=[event])
        self.assertIn('interaction_evidence_gap',self.codes(result))
        self.assertNotIn('pagination_url_unchanged_candidate',self.codes(result))

    def test_reversed_interaction_timestamps_do_not_prove_transition(self):
        event={'id':'next','url':URL,'kind':'paginate','before_id':'b','after_id':'a','source':'browser','checked_at':AT,'evidence':{'path':'event.json'},'before_page':'2117','after_page':'2116','before_items':['ETH'],'after_items':['BTC']}
        result=self.audit(interactions=[event])
        self.assertIn('interaction_evidence_gap',self.codes(result))
        self.assertNotIn('pagination_url_unchanged_candidate',self.codes(result))

    def test_interaction_claim_cannot_contradict_captured_items(self):
        event={'id':'next','url':URL,'kind':'paginate','before_id':'a','after_id':'b','source':'browser','checked_at':AT,'evidence':{'path':'event.json'},'before_page':'2116','after_page':'2117','before_items':['BTC'],'after_items':['MADE-UP']}
        result=self.audit(interactions=[event])
        self.assertIn('interaction_evidence_gap',self.codes(result))
        self.assertNotIn('pagination_url_unchanged_candidate',self.codes(result))

    def audit(self,samples=None,targets=None,**kw):
        return self.module('audit').audit(samples if samples is not None else [initial(),sample(),sample('b','2026-09-17T00:00:03Z')],
            targets or [{'url':URL,'expected_entry_modes':['direct'],'readiness':{'required_identity':'SOLV'}}],at=AT,**kw)
    def codes(self,result):return {f['rule'] for f in result['findings']}

    def test_initial_empty_h1_filled_by_dom_is_completion_not_failure(self):
        result=self.audit([initial(h1=['']),sample(),sample('b','2026-09-17T00:00:03Z')])
        self.assertIn('h1_populated',{c['change'] for c in result['changes']})
        self.assertNotIn('heading_disappeared',self.codes(result))
        self.assertEqual(result['rows'][0]['readiness']['state'],'ready')

    def test_title_and_canonical_changes_preserve_both_values(self):
        dom=[sample(title='Different',canonical=['https://bingx.com/en']),sample('b','2026-09-17T00:00:03Z',title='Different',canonical=['https://bingx.com/en'])]
        result=self.audit([initial(),*dom])
        self.assertIn('canonical_changed_after_render',self.codes(result))
        change=next(c for c in result['changes'] if c['field']=='title')
        self.assertEqual(change['before'],'Solv Protocol');self.assertEqual(change['after'],'Different')

    def test_missing_capture_not_treated_as_disappeared_h1(self):
        coverage={key:'complete' for key in FIELDS};coverage['h1']='unknown'
        result=self.audit([initial(),sample(h1=None,coverage=coverage),sample('b','2026-09-17T00:00:03Z',h1=None,coverage=coverage)])
        self.assertNotIn('heading_disappeared',self.codes(result))
        self.assertIn('comparison_coverage_gap',self.codes(result))

    def test_heading_disappears_only_after_ready_dom(self):
        result=self.audit([initial(),sample(h1=[]),sample('b','2026-09-17T00:00:03Z',h1=[])])
        self.assertIn('heading_disappeared',self.codes(result))

    def test_unstable_pending_dom_not_called_permanent_heading_loss(self):
        result=self.audit([initial(),sample(h1=[])])
        self.assertNotIn('heading_disappeared',self.codes(result))
        self.assertIn('render_readiness_gap',self.codes(result))

    def test_duplicate_title_injection_reported_without_single_h1_rule(self):
        dom=[sample(titles=['Solv Protocol','Old']),sample('b','2026-09-17T00:00:03Z',titles=['Solv Protocol','Old'])]
        result=self.audit([initial(),*dom])
        self.assertIn('metadata_nodes_increased',self.codes(result))

    def test_repeated_identical_schema_growth_is_candidate_not_same_id_error(self):
        block={'parsed':{'@id':'#x','name':'One'},'error':None}
        result=self.audit([initial(schema=[block]),sample(schema=[block,block]),sample('b','2026-09-17T00:00:03Z',schema=[block,block])])
        self.assertIn('repeated_schema_block_after_render',self.codes(result))
        other={'parsed':{'@id':'#x','name':'Additional'},'error':None}
        result=self.audit([initial(schema=[block]),sample(schema=[block,other]),sample('b','2026-09-17T00:00:03Z',schema=[block,other])])
        self.assertNotIn('repeated_schema_block_after_render',self.codes(result))

    def test_initial_links_filled_by_dom_are_recorded_as_discovery_difference(self):
        links=[{'href':'https://bingx.com/en/new','text':'New'}]
        result=self.audit([initial(),sample(links=links),sample('b','2026-09-17T00:00:03Z',links=links)])
        self.assertTrue(any(c['field']=='links' and c['after']==links for c in result['changes']))

    def test_partial_main_text_not_claimed_as_exact_content_loss(self):
        cover={key:'complete' for key in FIELDS};cover['main_text']='partial'
        result=self.audit([initial(main_text='Long text',coverage=cover),sample(),sample('b','2026-09-17T00:00:03Z')])
        self.assertIn('comparison_coverage_gap',self.codes(result))
        self.assertNotIn('main_content_disappeared',self.codes(result))

    def test_stale_browser_capture_does_not_certify_current_ready(self):
        result=self.audit([initial(),sample(at='2025-01-01T00:00:00Z')])
        self.assertNotEqual(result['rows'][0]['readiness']['state'],'ready')
        self.assertIn('rendered_evidence_gap',self.codes(result))

    def test_three_entry_modes_are_reported_separately(self):
        result=self.audit(targets=[{'url':URL,'expected_entry_modes':['direct','internal','back']}])
        self.assertEqual(result['coverage']['missing_entry_modes'],[{'url':URL,'modes':['internal','back']}])
        self.assertFalse(result['coverage']['all_requested_paths_observed'])

    def test_wrong_entity_console_error_and_ui_error_are_distinct(self):
        result=self.audit([initial(),sample(identity='BTC'),sample('b','2026-09-17T00:00:31Z',identity='BTC')])
        self.assertIn('render_readiness_gap',self.codes(result))
        result=self.audit([initial(),sample(page_errors=['Load failed'])])
        self.assertIn('visible_page_error',self.codes(result))

    def test_same_url_pagination_change_is_candidate_without_policy(self):
        interaction={'id':'next','url':URL,'kind':'paginate','before_id':'a','after_id':'b','source':'browser','checked_at':AT,'evidence':{'path':'event.json'},'before_page':'2116','after_page':'2117','before_items':['BTC'],'after_items':['ETH']}
        result=self.audit(interactions=[interaction])
        self.assertIn('pagination_url_unchanged_candidate',self.codes(result))
        self.assertNotIn('pagination_route_policy_conflict',self.codes(result))

    def test_same_url_pagination_change_with_explicit_shareable_policy_is_conflict(self):
        interaction={'id':'next','url':URL,'kind':'paginate','before_id':'a','after_id':'b','source':'browser','checked_at':AT,'evidence':{'path':'event.json'},'before_page':'2116','after_page':'2117','before_items':['BTC'],'after_items':['ETH']}
        targets=[{'url':URL,'expected_entry_modes':['direct'],'policy_source':'public listing route contract','policy_at':AT,'pagination_requires_url_change':True}]
        result=self.audit(targets=targets,interactions=[interaction])
        self.assertIn('pagination_route_policy_conflict',self.codes(result))

    def test_pagination_click_without_observed_after_data_is_not_verified_transition(self):
        event={'id':'next','url':URL,'kind':'paginate','before_id':'a','after_id':'missing','source':'browser','checked_at':AT,'evidence':{'path':'event.json'}}
        result=self.audit(interactions=[event])
        self.assertIn('interaction_evidence_gap',self.codes(result))
        self.assertNotIn('pagination_url_unchanged_candidate',self.codes(result))

    def test_forbidden_action_in_input_is_not_executed_or_counted_as_audit(self):
        result=self.audit(interactions=[{'id':'trade','url':URL,'kind':'place_order','before_id':'a','after_id':'b'}])
        self.assertIn('unsupported_interaction',self.codes(result))

    def test_initial_only_does_not_count_as_browser_audit(self):
        result=self.audit([initial()])
        self.assertIn('rendered_evidence_gap',self.codes(result))

    def test_report_serializable_and_issue_ids_stable_across_runs(self):
        samples=[initial(),sample(h1=[]),sample('b','2026-09-17T00:00:03Z',h1=[])]
        first=self.audit(samples);second=self.audit(samples)
        json.dumps(first)
        self.assertEqual({f['issue_id'] for f in first['findings']},{f['issue_id'] for f in second['findings']})
