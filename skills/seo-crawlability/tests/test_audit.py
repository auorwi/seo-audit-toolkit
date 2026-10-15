import json
from support import CrawlTest, AT
from test_responses import response, ROOT, PAGE

def page(body=b'<title>Home</title>', **kw):
    return response(url=PAGE, body=body, headers=[('content-type','text/html')], **kw)

def intent(value='indexable'):
    return {'url':PAGE, 'index_intent':value, 'intent_source':'approved-route-policy', 'intent_at':AT}

class AuditTests(CrawlTest):
    def test_fragment_is_not_a_separate_http_resource(self):
        row=self.audit(targets=[{'url':PAGE+'#content'}])['rows'][0]
        self.assertEqual(row['url'],PAGE)
        self.assertEqual(row['page']['reason'],'complete')

    def test_missing_content_type_does_not_certify_meta_absence(self):
        record=page(b'<meta name="robots" content="noindex">');record['headers']=[]
        result=self.audit([response(),record])
        self.assertEqual(result['rows'][0]['directive_status'],'incomplete_evidence')
        self.assertIn('content_type_evidence_gap',self.codes(result))

    def test_blocked_intermediate_redirect_prevents_noindex_readability(self):
        middle='https://bingx.com/blocked';end='https://bingx.com/final'
        records=[response(body=b'User-agent: *\nDisallow: /blocked'),
            response(url=PAGE,status=301,headers={'location':middle}),
            response(url=middle,status=301,headers={'location':end}),
            response(url=end,body=b'<meta name="robots" content="noindex">',headers={'content-type':'text/html'})]
        result=self.audit(records)
        self.assertFalse(result['rows'][0]['noindex_readable_under_rules'])
        self.assertIn('robots_blocks_noindex',self.codes(result))

    def test_network_failure_rendered_snapshot_not_trusted(self):
        result=self.audit(rendered=[page(b'<meta name="robots" content="noindex">',mode='rendered',status=503)])
        self.assertIsNone(result['rows'][0]['rendered_directives'])

    def audit(self, records=None, targets=None, **kw):
        return self.module('audit').audit(records if records is not None else [response(body=b'User-agent: *\nAllow: /'),page()], targets or [intent()], at=AT, agents=['Googlebot'], **kw)

    def codes(self,result): return {row['rule'] for row in result['findings']}

    def test_allow_and_200_do_not_prove_indexing(self):
        result=self.audit();row=result['rows'][0]
        self.assertTrue(row['robots']['allowed'])
        self.assertEqual(row['index_status'],'unknown')
        self.assertEqual(row['actual_bot_access'],'unknown')
        self.assertEqual(row['directive_status'],'no_restriction_observed')

    def test_noindex_on_expected_public_page_is_actionable_with_evidence(self):
        result=self.audit([response(body=b'User-agent: *\nAllow: /'),page(b'<meta name="robots" content="noindex">')])
        issue=next(f for f in result['findings'] if f['rule']=='unexpected_noindex')
        self.assertEqual(issue['classification'],'confirmed_configuration')
        self.assertEqual(issue['url'],PAGE)
        self.assertTrue(issue['evidence']); self.assertTrue(issue['recommendation'])

    def test_unknown_intent_does_not_label_noindex_misconfiguration(self):
        result=self.audit([response(),page(b'<meta name="robots" content="noindex">')], targets=[{'url':PAGE}])
        self.assertNotIn('unexpected_noindex',self.codes(result))
        self.assertIn('intent_confirmation_needed',self.codes(result))

    def test_expected_exclusion_does_not_recommend_removing_noindex(self):
        result=self.audit([response(),page(b'<meta name="robots" content="noindex">')],targets=[intent('excluded')])
        self.assertNotIn('unexpected_noindex',self.codes(result))
        self.assertNotIn('unexpected_robots_block',self.codes(result))

    def test_intent_without_source_or_stale_policy_is_unknown(self):
        for target in [{'url':PAGE,'index_intent':'indexable'}, {**intent(),'intent_at':'2025-01-01T00:00:00Z'}]:
            result=self.audit([response(),page()],targets=[target])
            self.assertEqual(result['rows'][0]['index_intent'],'unknown')
            self.assertNotIn('unexpected_robots_block',self.codes(result))

    def test_disallowed_noindex_is_observed_but_crawler_cannot_read_it(self):
        result=self.audit([response(),page(b'<meta name="robots" content="noindex">')])
        row=result['rows'][0]
        self.assertTrue(row['raw_directives']['noindex'])
        self.assertFalse(row['noindex_readable_under_rules'])
        self.assertIn('robots_blocks_noindex',self.codes(result))

    def test_stale_page_is_not_current_noindex(self):
        result=self.audit([response(),page(b'<meta name="robots" content="noindex">',at='2025-01-01T00:00:00Z')])
        self.assertIsNone(result['rows'][0]['raw_directives'])
        self.assertIn('page_evidence_gap',self.codes(result))
        self.assertNotIn('unexpected_noindex',self.codes(result))

    def test_latest_network_failure_overrides_old_ok_without_site_error_claim(self):
        result=self.audit([response(),page(at='2026-09-16T11:00:00Z'),page(status=None,error='TimeoutError')])
        self.assertIn('page_evidence_gap',self.codes(result))
        self.assertNotIn('http_access_failure',self.codes(result))
        self.assertEqual(result['rows'][0]['page']['reason'],'request_unverified')

    def test_error_page_meta_does_not_become_content_noindex(self):
        result=self.audit([response(),page(b'<meta name="robots" content="noindex">',status=503)])
        self.assertIn('http_access_failure',self.codes(result))
        self.assertNotIn('unexpected_noindex',self.codes(result))
        self.assertIsNone(result['rows'][0]['raw_directives'])

    def test_single_5xx_is_single_observation_not_persistent_failure(self):
        result=self.audit([response(),page(status=503,request_id='ray-123',environment='local-sg')])
        row=result['rows'][0]
        self.assertEqual(row['http_pattern'],'single_observation')
        self.assertEqual(row['request_history'][0]['request_id'],'ray-123')

    def test_recovered_http_request_keeps_prior_5xx_event(self):
        result=self.audit([response(),page(status=503,at='2026-09-16T11:00:00Z',environment='local'),page(environment='local')])
        row=result['rows'][0]
        self.assertEqual(row['http_pattern'],'mixed_observations')
        self.assertEqual([r['status'] for r in row['request_history']],[503,200])
        self.assertNotIn('http_access_failure',self.codes(result))

    def test_different_environments_not_called_intermittent_same_client(self):
        row=self.audit([response(),page(status=403,at='2026-09-16T11:00:00Z',environment='eu'),page(environment='sg')])['rows'][0]
        self.assertEqual(row['http_pattern'],'noncomparable_observations')

    def test_rendered_index_cannot_override_initial_noindex(self):
        rendered=[page(b'<meta name="robots" content="index">',mode='rendered')]
        result=self.audit([response(),page(b'<meta name="robots" content="noindex">')],rendered=rendered)
        row=result['rows'][0]
        self.assertTrue(row['raw_directives']['noindex']);self.assertFalse(row['rendered_directives']['noindex'])
        self.assertIn('raw_rendered_directive_difference',self.codes(result))
        self.assertIn('unexpected_noindex',self.codes(result))

    def test_stale_rendered_snapshot_is_gap_not_current_difference(self):
        result=self.audit(rendered=[page(b'<meta name="robots" content="noindex">',at='2025-01-01T00:00:00Z',mode='rendered')])
        self.assertIsNone(result['rows'][0]['rendered_directives'])
        self.assertNotIn('raw_rendered_directive_difference',self.codes(result))

    def test_headers_on_nonhtml_are_respected_without_parsing_pdf_as_html(self):
        record=response(url=PAGE,body=b'<meta name="robots" content="noindex">',headers=[('content-type','application/pdf')])
        result=self.audit([response(),record]);self.assertFalse(result['rows'][0]['raw_directives']['noindex'])
        record['headers'].append(('x-robots-tag','noindex'))
        self.assertTrue(self.audit([response(),record])['rows'][0]['raw_directives']['noindex'])

    def test_legacy_header_capture_marks_unknown_absence(self):
        result=self.audit([response(),page(header_capture_complete=False)])
        self.assertEqual(result['rows'][0]['directive_status'],'incomplete_evidence')
        self.assertIn('header_capture_gap',self.codes(result))

    def test_redirect_chain_terminal_noindex_identifies_both_urls(self):
        end='https://bingx.com/en/new'
        result=self.audit([response(),response(url=PAGE,status=301,headers={'location':end}),response(url=end,body=b'<meta name="robots" content="noindex">',headers={'content-type':'text/html'})])
        row=result['rows'][0]
        self.assertEqual(row['page']['final_url'],end)
        self.assertEqual(row['url'],PAGE)
        self.assertEqual(len(row['page']['chain']),2)

    def test_cross_origin_redirect_uses_terminal_origin_robots(self):
        end='https://blog.bingx.com/en'
        result=self.audit([response(body=b'User-agent: *\nAllow: /'),response(url=PAGE,status=301,headers={'location':end}),response(url=end,body=b'ok')])
        self.assertIsNone(result['rows'][0]['terminal_robots']['allowed'])
        self.assertIn('terminal_robots_evidence_gap',self.codes(result))

    def test_platform_observations_do_not_turn_synthetic_user_agent_into_verified_bot(self):
        observations=[{'url':PAGE,'engine':'google','kind':'user_agent_probe','checked_at':AT,'source':'probe','status':200}]
        row=self.audit(observations=observations)['rows'][0]
        self.assertEqual(row['actual_bot_access'],'unknown')
        self.assertEqual(row['platform_observations'][0]['kind'],'user_agent_probe')

    def test_no_bytes_in_export_and_stable_identity_across_evidence_updates(self):
        first=self.audit([response(),page(b'<meta name="robots" content="noindex">')])
        second=self.audit([response(),page(b'<meta name="robots" content="noindex"><p>changed</p>')])
        json.dumps(first)
        a=next(f for f in first['findings'] if f['rule']=='unexpected_noindex')
        b=next(f for f in second['findings'] if f['rule']=='unexpected_noindex')
        self.assertEqual(a['issue_id'],b['issue_id'])

    def test_explicit_scope_deduplicates_and_empty_scope_rejected(self):
        mod=self.module('audit')
        self.assertEqual(len(self.audit(targets=[intent(),intent()])['rows']),1)
        with self.assertRaises(ValueError):mod.audit([],[],at=AT)

    def test_missing_rendered_evidence_is_reported_as_unchecked(self):
        self.assertEqual(self.audit()['rows'][0]['rendered_status'],'not_checked')
