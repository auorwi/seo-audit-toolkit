import json
import hashlib
import inspect
from support import RoutingTest, AT

A='https://bingx.com/en/launchpad/detail?currency=78'
B='https://bingx.com/en/launchpad/detail'

def response(url=A,target=None,**kw):
    html='<html><head>'+('<link rel="canonical" href="'+target+'">' if target else '')+'</head><body><h1>Project 78</h1></body></html>'
    return {'url':url,'status':200,'checked_at':AT,'headers':[('content-type','text/html')],'body':html.encode(),
        'captured_header_names':['link','refresh','content-type','x-robots-tag'],**kw}

def policy(**kw):
    return {'url':A,'policy_source':'approved route contract','policy_at':AT,**kw}

def fact(url=A,**kw):
    return {'url':url,'checked_at':AT,'source':'browser-main-content','evidence':{'path':'actual-dom.html','sha256':'documented'},**kw}

class RoutingAuditTests(RoutingTest):
    def test_public_route_http_redirect_to_login_is_also_flagged(self):
        login='https://bingx.com/en/accounts/login'
        records=[response(status=302,headers=[('location',login)]),response(url=login,target=login)]
        result=self.audit(records,targets=[policy(expected_role='public')])
        self.assertIn('public_route_to_restricted_candidate',self.codes(result))
        self.assertTrue(any(r['relation']=='http_redirect' for r in result['relations']))

    def test_observed_favorites_content_without_url_change_is_reviewable(self):
        result=self.audit(targets=[policy(expected_role='public')],facts=[fact(role='favorites',quote='Favorites',selector='main')])
        self.assertIn('public_route_role_mismatch',self.codes(result))

    def test_rendered_only_target_status_is_checked(self):
        result=self.audit([response(target=A),response(url=B,status=404)],rendered=[response(target=B,mode='rendered')])
        self.assertIn('canonical_target_http_error',self.codes(result))
        self.assertIn(B,{c['url'] for c in result['rows'][0]['target_checks']})

    def test_language_conflict_prevents_target_recommendation(self):
        records=[response(target=B),response(url=B,target=B)]
        eq=self.assessment(records);records.append(self.public_robots())
        result=self.audit(records,targets=[policy(preferred_canonical=B)],equivalences=[eq],facts=[fact(A,language='fr'),fact(B,language='en')])
        self.assertIsNone(result['rows'][0]['suggested_target'])

    def test_equivalence_status_keeps_multiple_targets_separate(self):
        C='https://bingx.com/en/third'
        records=[response(target=B,headers=[('content-type','text/html'),('link','<'+C+'>; rel=canonical')]),response(url=B),response(url=C)]
        first=self.assessment(records[:2],'different')
        second=self.assessment([records[0],records[2]],'equivalent');second['target_url']=C
        result=self.audit(records,equivalences=[first,second])
        self.assertEqual(result['rows'][0]['content_equivalence'],'multiple_target_assessments')
        self.assertIsNone(result['rows'][0]['suggested_target'])

    def assessment(self,records,result='equivalent'):
        for record in records:
            record['evidence']={'path':'evidence.body','sha256':hashlib.sha256(record['body']).hexdigest(),'bytes':len(record['body'])}
        return {'source_url':A,'target_url':B,'result':result,'source':'content reviewer','checked_at':AT,
            'evidence':{'path':'comparison.json'},'source_sha256':records[0]['evidence']['sha256'],'target_sha256':records[1]['evidence']['sha256']}

    def public_robots(self):
        return response(url='https://bingx.com/robots.txt',body=b'User-agent: *\nAllow: /',headers=[('content-type','text/plain')])

    def test_old_capture_cannot_claim_http_canonical_absence(self):
        result=self.audit([response(target=A,captured_header_names=None)])
        self.assertIn('canonical_header_evidence_gap',self.codes(result))

    def test_current_equivalence_assessment_can_support_explicit_policy_target(self):
        records=[response(target=B),response(url=B,target=B)]
        eq=self.assessment(records);records.append(self.public_robots())
        result=self.audit(records,targets=[policy(preferred_canonical=B)],equivalences=[eq])
        row=result['rows'][0]
        self.assertEqual(row['content_equivalence'],'equivalent_by_assessment')
        self.assertEqual(row['suggested_target'],B)

    def test_equivalence_is_not_reused_after_source_or_target_body_changes(self):
        records=[response(target=B),response(url=B,target=B)]
        eq=self.assessment(records);records[1]['evidence']['sha256']='new-version'
        result=self.audit(records,targets=[policy(preferred_canonical=B)],equivalences=[eq])
        self.assertEqual(result['rows'][0]['content_equivalence'],'unknown')
        self.assertIsNone(result['rows'][0]['suggested_target'])

    def test_non_equivalent_content_is_not_recommended_as_canonical(self):
        records=[response(target=B),response(url=B,target=B)]
        eq=self.assessment(records,'different');records.append(self.public_robots())
        result=self.audit(records,targets=[policy(preferred_canonical=B)],equivalences=[eq])
        self.assertIn('canonical_content_not_equivalent',self.codes(result))
        self.assertIsNone(result['rows'][0]['suggested_target'])

    def test_target_noindex_prevents_recommendation_even_if_content_equivalent(self):
        records=[response(target=B),response(url=B,target=B,headers=[('content-type','text/html'),('x-robots-tag','noindex')])]
        eq=self.assessment(records);records.append(self.public_robots())
        result=self.audit(records,targets=[policy(preferred_canonical=B)],equivalences=[eq])
        self.assertIsNone(result['rows'][0]['suggested_target'])

    def test_meta_refresh_disagrees_with_canonical_without_claiming_executed_redirect(self):
        body=b'<head><link rel="canonical" href="https://bingx.com/en"><meta http-equiv="refresh" content="0;url=/en/login"></head>'
        result=self.audit([response(body=body)])
        self.assertIn('refresh_canonical_difference',self.codes(result))
        self.assertFalse(any(r['relation']=='client_navigation' for r in result['relations']))

    def test_graph_walk_limit_is_an_explicit_gap(self):
        urls=['https://bingx.com/en/page/'+str(i) for i in range(33)]
        records=[response(url=u,target=urls[i+1]) for i,u in enumerate(urls[:-1])]+[response(url=urls[-1],target=urls[-1])]
        result=self.audit(records,targets=[{'url':urls[0]}])
        self.assertIn('canonical_graph_limit',self.codes(result))

    def audit(self,records=None,targets=None,**kw):
        audit=self.module('audit').audit
        if 'equivalences' in kw:self.assertIn('equivalences',inspect.signature(audit).parameters,'尚未实现内容等价性输入')
        return audit(records or [response(target=A)],targets or [{'url':A}],at=AT,**kw)
    def codes(self,r):return {f['rule'] for f in r['findings']}

    def test_self_canonical_not_cycle_and_not_proof_engine_selected_it(self):
        result=self.audit()
        self.assertNotIn('canonical_cycle',self.codes(result))
        self.assertEqual(result['rows'][0]['engine_selected_canonical'],'unknown')

    def test_no_canonical_not_automatically_configuration_error(self):
        result=self.audit([response()])
        self.assertNotIn('missing_canonical',self.codes(result))

    def test_currency_removal_requires_policy_before_confirmed_parameter_issue(self):
        records=[response(target=B),response(url=B,target=B)]
        result=self.audit(records)
        self.assertIn('query_change_needs_equivalence',self.codes(result))
        self.assertNotIn('entity_parameter_changed',self.codes(result))
        confirmed=self.audit(records,targets=[policy(entity_parameters=['currency'])])
        self.assertIn('entity_parameter_changed',self.codes(confirmed))
        self.assertEqual(confirmed['rows'][0]['url'],A)

    def test_tracking_parameter_removal_uses_policy_and_still_needs_equivalence(self):
        source='https://bingx.com/en?utm_source=x';target='https://bingx.com/en'
        result=self.audit([response(url=source,target=target),response(url=target,target=target)],targets=[policy(url=source,tracking_parameters=['utm_source'])])
        self.assertNotIn('entity_parameter_changed',self.codes(result))
        self.assertEqual(result['rows'][0]['parameter_changes'][0]['category'],'tracking_by_policy')
        self.assertEqual(result['rows'][0]['content_equivalence'],'unknown')

    def test_parameter_value_change_and_repeated_values_preserved(self):
        target=B+'?currency=84&currency=85'
        result=self.audit([response(target=target),response(url=target)],targets=[policy(entity_parameters=['currency'])])
        change=result['rows'][0]['parameter_changes'][0]
        self.assertEqual(change['source_values'],['78']);self.assertEqual(change['target_values'],['84','85'])

    def test_stale_policy_does_not_confirm_entity_parameter_bug(self):
        result=self.audit([response(target=B),response(url=B)],targets=[policy(entity_parameters=['currency'],policy_at='2025-01-01T00:00:00Z')])
        self.assertNotIn('entity_parameter_changed',self.codes(result))

    def test_canonical_target_404_is_observed_without_suggesting_unverified_alternative(self):
        result=self.audit([response(target=B),response(url=B,status=404)])
        self.assertIn('canonical_target_http_error',self.codes(result))
        self.assertIsNone(result['rows'][0]['suggested_target'])

    def test_latest_target_failure_not_replaced_with_old_200(self):
        result=self.audit([response(target=B),response(url=B,checked_at='2026-09-16T15:00:00Z'),response(url=B,status=None,error='TimeoutError')])
        self.assertIn('canonical_target_evidence_gap',self.codes(result))
        self.assertNotIn('canonical_target_http_error',self.codes(result))

    def test_target_noindex_is_separate_from_target_200(self):
        record=response(url=B,body=b'<head><meta name="robots" content="noindex"></head>')
        result=self.audit([response(target=B),record])
        self.assertIn('canonical_target_noindex',self.codes(result))

    def test_canonical_loop_is_explicit_graph_cycle(self):
        result=self.audit([response(target=B),response(url=B,target=A)])
        self.assertIn('canonical_cycle',self.codes(result))
        self.assertEqual(result['rows'][0]['canonical_path'],[A,B,A])

    def test_canonical_chain_has_original_and_every_observed_target(self):
        C='https://bingx.com/en/final'
        result=self.audit([response(target=B),response(url=B,target=C),response(url=C,target=C)])
        self.assertIn('canonical_chain',self.codes(result))
        self.assertEqual(result['rows'][0]['canonical_path'],[A,B,C])

    def test_html_header_conflict_retains_both_relations(self):
        result=self.audit([response(target=A,headers=[('content-type','text/html'),('link','<'+B+'>; rel="canonical"')])])
        self.assertIn('canonical_conflict',self.codes(result))
        self.assertEqual({e['target'] for e in result['relations'] if e['relation']=='canonical'},{A,B})

    def test_rendered_change_is_not_merged_with_raw_declaration(self):
        result=self.audit([response(target=A),response(url=B)],rendered=[response(target=B,mode='rendered')])
        self.assertIn('raw_rendered_canonical_conflict',self.codes(result))
        row=result['rows'][0];self.assertEqual(row['raw']['targets'],[A]);self.assertEqual(row['rendered']['targets'],[B])

    def test_stale_rendered_snapshot_not_current_conflict(self):
        result=self.audit(rendered=[response(target=B,mode='rendered',checked_at='2025-01-01T00:00:00Z')])
        self.assertNotIn('raw_rendered_canonical_conflict',self.codes(result))

    def test_cross_locale_path_is_candidate_not_proven_content_language(self):
        fr='https://bingx.com/fr/learn/topic';en='https://bingx.com/en/learn/topic'
        result=self.audit([response(url=fr,target=en),response(url=en,target=en)],targets=[{'url':fr}])
        self.assertIn('cross_locale_canonical_candidate',self.codes(result))
        self.assertNotIn('content_language_mismatch',self.codes(result))

    def test_evidenced_language_difference_is_distinguished_from_route_guess(self):
        fr='https://bingx.com/fr/learn/topic';en='https://bingx.com/en/learn/topic'
        result=self.audit([response(url=fr,target=en),response(url=en)],targets=[{'url':fr}],facts=[fact(fr,language='fr'),fact(en,language='en')])
        self.assertIn('content_language_mismatch',self.codes(result))
        item=next(f for f in result['findings'] if f['rule']=='content_language_mismatch')
        self.assertEqual(item['classification'],'evidence_backed_review')

    def test_expected_gold_route_and_observed_btc_is_content_mismatch_not_title_fix(self):
        gold='https://bingx.com/en/trade/GOLDUSD'
        result=self.audit([response(url=gold,target=gold)],targets=[policy(url=gold,expected_entity='GOLDUSD')],facts=[fact(gold,entity='BTC',quote='BTC',selector='main h1')])
        self.assertIn('route_entity_mismatch',self.codes(result))
        self.assertIsNone(result['rows'][0]['suggested_target'])

    def test_unproven_or_stale_fact_cannot_confirm_entity_mismatch(self):
        for f in [{'url':A,'entity':'BTC'},fact(entity='BTC',checked_at='2025-01-01T00:00:00Z')]:
            result=self.audit(targets=[policy(expected_entity='GOLDUSD')],facts=[f])
            self.assertNotIn('route_entity_mismatch',self.codes(result))

    def test_actual_client_navigation_to_login_is_retained_separately(self):
        nav={'from_url':A,'to_url':'https://bingx.com/en/login','entry_mode':'direct','checked_at':AT,'source':'browser','evidence':{'path':'nav.json'}}
        result=self.audit(targets=[policy(expected_role='public')],navigation=[nav])
        self.assertIn('public_route_to_restricted_candidate',self.codes(result))
        self.assertTrue(any(e['relation']=='client_navigation' for e in result['relations']))

    def test_js_source_code_is_not_observed_navigation(self):
        result=self.audit([response(body=b'<head></head><script>location="/en/login"</script>')])
        self.assertFalse(any(e['relation']=='client_navigation' for e in result['relations']))

    def test_engine_canonical_snapshot_keeps_source_and_timestamp(self):
        obs={'url':A,'canonical':B,'engine':'google','kind':'index_snapshot','checked_at':AT,'source':'gsc','evidence':{'path':'export.json'}}
        result=self.audit(engine_observations=[obs])
        self.assertEqual(result['rows'][0]['engine_observations'][0]['canonical'],B)
        self.assertEqual(result['rows'][0]['engine_selected_canonical'],'unknown')
        self.assertIn('declared_engine_canonical_difference',self.codes(result))

    def test_export_json_keeps_distinct_urls_and_no_bytes(self):
        result=self.audit([response(target=B),response(url=B)],targets=[{'url':A},{'url':B}])
        json.dumps(result);self.assertEqual(len(result['rows']),2)
        self.assertEqual({r['url'] for r in result['rows']},{A,B})
