from support import RenderingTest, AT

URL='https://bingx.com/en/launchpad/detail?currency=78'
def snapshot(id='a',at='2026-09-17T00:00:01Z',**kw):
    return {'id':id,'url':URL,'navigation_id':'navigation-1','entry_mode':'direct','captured_at':at,
        'source':'actual-browser','stage':'dom','title':'Solv Protocol','canonical':[URL],
        'h1':['Solv Protocol'],'identity':'SOLV','main_text':'SOLV project information',
        'placeholder_count':0,'page_errors':[],'console_errors':[],'document_ready_state':'complete',
        'network_idle':False,**kw}

class ReadinessTests(RenderingTest):
    def test_different_device_contexts_do_not_form_one_stable_window(self):
        result=self.ready([snapshot(environment={'device':'desktop'}),snapshot('b','2026-09-17T00:00:03Z',environment={'device':'mobile'})])
        self.assertEqual(result['state'],'pending')

    def test_stable_title_does_not_count_prior_placeholder_as_loaded_sample(self):
        result=self.ready([snapshot(placeholder_count=1),snapshot('b','2026-09-17T00:00:03Z')])
        self.assertEqual(result['state'],'pending')
        self.assertEqual(result['samples_used'],['b'])

    def test_stable_identity_does_not_count_prior_empty_main_as_ready(self):
        result=self.ready([snapshot(main_text=''),snapshot('b','2026-09-17T00:00:03Z')])
        self.assertEqual(result['state'],'pending')

    def ready(self,samples=None,**policy):
        return self.module('readiness').evaluate(samples if samples is not None else [snapshot(),snapshot('b','2026-09-17T00:00:03Z')],
            {'required_identity':'SOLV','max_wait_ms':30000,'min_stable_samples':2,'stable_window_ms':1000,**policy},started_at=AT)

    def test_stable_entity_is_ready_while_network_remains_active(self):
        result=self.ready()
        self.assertEqual(result['state'],'ready');self.assertEqual(result['snapshot_id'],'b')

    def test_network_idle_with_empty_main_is_not_ready(self):
        samples=[snapshot(network_idle=True,main_text=''),snapshot('b','2026-09-17T00:00:03Z',network_idle=True,main_text='')]
        result=self.ready(samples)
        self.assertEqual(result['state'],'pending');self.assertIn('main_content_missing',result['unmet'])

    def test_placeholder_must_disappear(self):
        result=self.ready([snapshot(placeholder_count=2),snapshot('b','2026-09-17T00:00:03Z',placeholder_count=2)])
        self.assertEqual(result['state'],'pending');self.assertIn('placeholders_present',result['unmet'])

    def test_latest_loaded_state_needs_stability_not_one_observation(self):
        result=self.ready([snapshot(identity=None,placeholder_count=1),snapshot('b','2026-09-17T00:00:03Z')])
        self.assertEqual(result['state'],'pending');self.assertIn('stable_samples_missing',result['unmet'])

    def test_identity_mismatch_is_not_ready_even_if_title_looks_correct(self):
        result=self.ready([snapshot(identity='BTC'),snapshot('b','2026-09-17T00:00:03Z',identity='BTC')])
        self.assertEqual(result['state'],'pending');self.assertIn('expected_identity_not_observed',result['unmet'])

    def test_dynamic_price_changes_do_not_prevent_identity_stability(self):
        result=self.ready([snapshot(main_text='SOLV price 0.02',price='0.02'),snapshot('b','2026-09-17T00:00:03Z',main_text='SOLV price 0.03',price='0.03')])
        self.assertEqual(result['state'],'ready')

    def test_canonical_change_resets_stability_window(self):
        result=self.ready([snapshot(canonical=['https://bingx.com/en']),snapshot('b','2026-09-17T00:00:03Z')])
        self.assertEqual(result['state'],'pending')

    def test_dom_ready_state_alone_not_sufficient(self):
        result=self.ready([snapshot(document_ready_state='complete')])
        self.assertEqual(result['state'],'pending')

    def test_timeout_is_unknown_with_reasons_not_website_broken(self):
        result=self.ready([snapshot(at='2026-09-17T00:00:31Z',identity=None,main_text='')])
        self.assertEqual(result['state'],'unknown_timeout')
        self.assertIn('expected_identity_not_observed',result['unmet'])

    def test_observed_page_error_distinct_from_console_warning(self):
        result=self.ready([snapshot(page_errors=['Load failed, please try again'])])
        self.assertEqual(result['state'],'page_error')
        result=self.ready([snapshot(console_errors=['Hydration mismatch']),snapshot('b','2026-09-17T00:00:03Z',console_errors=['Hydration mismatch'])])
        self.assertEqual(result['state'],'ready')

    def test_samples_from_different_navigation_are_not_combined(self):
        result=self.ready([snapshot(),snapshot('b','2026-09-17T00:00:03Z',navigation_id='navigation-2')])
        self.assertEqual(result['state'],'pending');self.assertIn('stable_samples_missing',result['unmet'])

    def test_different_entry_paths_are_not_combined(self):
        result=self.ready([snapshot(),snapshot('b','2026-09-17T00:00:03Z',entry_mode='internal')])
        self.assertEqual(result['state'],'pending')

    def test_snapshots_must_be_distinct_and_separated_in_time(self):
        self.assertEqual(self.ready([snapshot(),snapshot()])['state'],'pending')
        self.assertEqual(self.ready([snapshot(),snapshot('b','2026-09-17T00:00:01.001Z')])['state'],'pending')

    def test_missing_placeholder_count_is_unknown_not_zero(self):
        result=self.ready([snapshot(placeholder_count=None),snapshot('b','2026-09-17T00:00:03Z',placeholder_count=None)])
        self.assertEqual(result['state'],'pending');self.assertIn('placeholder_state_unknown',result['unmet'])

    def test_initial_http_html_is_not_browser_ready_evidence(self):
        result=self.ready([snapshot(stage='initial'),snapshot('b','2026-09-17T00:00:03Z',stage='initial')])
        self.assertEqual(result['state'],'pending');self.assertIn('browser_dom_not_observed',result['unmet'])

    def test_empty_samples_return_pending_without_fake_snapshot(self):
        result=self.ready([])
        self.assertEqual(result['state'],'pending');self.assertIsNone(result['snapshot_id'])

    def test_invalid_limits_and_unknown_stable_fields_are_rejected(self):
        for policy in [{'max_wait_ms':0},{'min_stable_samples':0},{'stable_window_ms':-1},{'stable_fields':['secretState']}]:
            with self.subTest(policy=policy),self.assertRaises(ValueError):self.ready(**policy)

    def test_timestamp_before_start_is_invalid_evidence(self):
        result=self.ready([snapshot(at='2026-09-16T23:59:59Z')])
        self.assertEqual(result['state'],'invalid_evidence')
