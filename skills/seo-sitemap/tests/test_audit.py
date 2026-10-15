from support import AuditTest, xml, AT, NS

ROOT='https://bingx.com/sitemap.xml'
LEAF='https://bingx.com/en/sitemap-main.xml'
PAGE='https://bingx.com/en/price/bitcoin'

def doc(url, body, status=200, at=AT, **kw):
    return {'url':url,'body':body,'status':status,'checked_at':at,**kw}

def page(status=200, at=AT, **kw):
    return {'url':PAGE,'status':status,'checked_at':at,'details':kw}

def expected(rows, **kw):
    return {'source_id':'cms-release','kind':'cms','coverage':'complete','captured_at':AT,'scope_roots':[ROOT],'rows':rows,**kw}

class AuditRulesTests(AuditTest):
    def test_day_precision_lastmod_does_not_claim_same_day_change_is_missing(self):
        body=f'<urlset xmlns="{NS}"><url><loc>{PAGE}</loc><lastmod>2026-09-16</lastmod></url></urlset>'.encode()
        result=self.audit([doc(ROOT,body)],expected=expected([{'url':PAGE,'modified_at':'2026-09-16T08:00:00Z','modification_kind':'significant'}]))
        self.assertNotIn('lastmod_behind_known_change',self.codes(result))

    def test_even_clean_file_keeps_timestamp_and_evidence_reference(self):
        proof={'path':'/evidence/body.xml','sha256':'known-test-hash','bytes':50}
        result=self.audit([doc(ROOT,xml([PAGE]),evidence=proof)])
        self.assertEqual(result['files'][0].get('checked_at'),AT)
        self.assertEqual(result['files'][0].get('evidence'),proof)

    def test_index_child_above_parent_directory_needs_scope_review(self):
        parent='https://bingx.com/public/index.xml'
        result=self.module('audit').audit([doc(parent,xml([ROOT],'sitemapindex')),doc(ROOT,xml([]))],{},[parent],AT)
        self.assertIn('sitemap_index_path_scope',self.codes(result))

    def test_missing_expectation_with_untranslated_canonical_is_intent_unknown(self):
        result=self.audit(expected=expected([{'url':'https://bingx.com/fr/price/bitcoin','published':True,'should_index':True,'canonical_url':PAGE}]))
        self.assertNotIn('sitemap_expected_missing',self.codes(result))

    def test_page_evidence_failure_reason_is_exported_not_just_pending_url(self):
        source=page(200);source['error']='evidence_hash_mismatch'
        result=self.audit(pages={PAGE:source})
        f=next((f for f in result['findings'] if f['rule']=='page_evidence_unverified'),None)
        self.assertIsNotNone(f)
        self.assertIn('evidence_hash_mismatch',str(f['evidence']))

    def test_future_business_change_is_not_used_to_flag_current_lastmod(self):
        body=f'<urlset xmlns="{NS}"><url><loc>{PAGE}</loc><lastmod>2026-09-15</lastmod></url></urlset>'.encode()
        result=self.audit([doc(ROOT,body)],expected=expected([{'url':PAGE,'modified_at':'2027-01-01','modification_kind':'significant'}]))
        self.assertNotIn('lastmod_behind_known_change',self.codes(result))
        self.assertIn('expected_modified_in_future',self.codes(result))

    def test_omission_scope_must_match_independent_expected_scope(self):
        exp=expected([{'url':PAGE,'published':True,'should_index':True,'canonical_url':PAGE}],scope_roots=['https://bingx.com/another.xml'])
        result=self.audit([doc(ROOT,xml([]))],expected=exp)
        f=next(f for f in result['findings'] if f['rule']=='sitemap_expected_missing')
        self.assertEqual(f['certainty'],'candidate')
        self.assertIsNone(result['coverage']['expected_indexable_urls'])

    def test_unreachable_acquired_file_does_not_hide_root_omission(self):
        exp=expected([{'url':PAGE,'published':True,'should_index':True,'canonical_url':PAGE}])
        result=self.audit([doc(ROOT,xml([])),doc(LEAF,xml([PAGE]))],expected=exp)
        self.assertIn('sitemap_expected_missing',self.codes(result))
        self.assertEqual(result['coverage']['expected_present_urls'],0)

    def test_invalid_page_canonical_is_reported_without_aborting_other_rules(self):
        try:
            result=self.audit(pages={PAGE:page(200,canonicals=['javascript:bad'])})
        except ValueError as error:
            self.fail('单个 canonical 不应中断整批检查：'+str(error))
        self.assertIn('sitemap_canonical_invalid',self.codes(result))

    def audit(self, docs=None, pages=None, **kw):
        return self.module('audit').audit(docs or [doc(ROOT,xml([PAGE]))], pages or {}, [ROOT], AT, **kw)

    def test_nested_index_and_cycle_have_separate_findings(self):
        result=self.audit([doc(ROOT,xml([LEAF],'sitemapindex')),doc(LEAF,xml([ROOT],'sitemapindex'))])
        self.assertIn('sitemap_nested_index',self.codes(result))
        self.assertIn('sitemap_cycle',self.codes(result))
        self.assertEqual(result['coverage']['listed_page_urls'],0)

    def test_unread_child_prevents_claim_of_complete_sitemap_set(self):
        result=self.audit([doc(ROOT,xml([LEAF],'sitemapindex'))])
        self.assertFalse(result['coverage']['sitemap_set_read_complete'])
        self.assertEqual(result['coverage']['unread_sitemaps'],[LEAF])

    def test_latest_failed_attempt_does_not_fall_back_to_old_success(self):
        result=self.audit([doc(ROOT,xml([PAGE]),at='2026-09-16T08:00:00Z'),doc(ROOT,b'',status=None,error='TimeoutError')])
        self.assertEqual(result['coverage']['listed_page_urls'],0)
        self.assertIn('sitemap_fetch_unverified',self.codes(result))

    def test_current_404_listed_page_is_evidenced_but_not_called_retired(self):
        result=self.audit(pages={PAGE:page(404)})
        finding=next(f for f in result['findings'] if f['rule']=='sitemap_http_missing')
        self.assertEqual(finding['certainty'],'confirmed')
        self.assertEqual(finding['category'],'remove')
        self.assertIn('退役',finding['recommendation'])
        self.assertEqual(result['coverage']['fresh_page_checks'],1)

    def test_old_404_is_not_a_current_removal_finding(self):
        result=self.audit(pages={PAGE:page(404,at='2025-01-01T00:00:00Z')})
        self.assertNotIn('sitemap_http_missing',self.codes(result))
        self.assertEqual(result['coverage']['unverified_page_urls'],[PAGE])

    def test_redirect_requires_target_verification_and_preserves_original(self):
        result=self.audit(pages={PAGE:page(301,headers={'location':'/en/price/btc'})})
        f=next(f for f in result['findings'] if f['rule']=='sitemap_redirect')
        self.assertEqual(f['category'],'retarget')
        self.assertEqual(f['certainty'],'candidate')
        self.assertEqual(f['url'],PAGE)
        self.assertIn('https://bingx.com/en/price/btc',str(f['evidence']))

    def test_5xx_403_and_429_are_confirm_checks_not_remove_lists(self):
        for status in (500,503,403,429):
            with self.subTest(status=status):
                result=self.audit(pages={PAGE:page(status)})
                self.assertTrue(result['findings'])
                self.assertTrue(all(f['category']=='confirm' for f in result['findings']))

    def test_generic_noindex_and_bot_specific_directives_keep_scope(self):
        result=self.audit(pages={PAGE:page(200,noindex_observed=True)})
        self.assertIn('sitemap_noindex_conflict',self.codes(result))
        result=self.audit(pages={PAGE:page(200,robots_directives={'bingbot':['noindex']})})
        f=next(f for f in result['findings'] if f['rule']=='sitemap_noindex_conflict')
        self.assertEqual(f['engine'],'bingbot')

    def test_canonical_to_different_language_is_not_automatically_recommended_target(self):
        result=self.audit(pages={PAGE:page(200,canonicals=['https://bingx.com/fr/price/bitcoin'])})
        f=next(f for f in result['findings'] if f['rule']=='sitemap_canonical_conflict')
        self.assertEqual(f['certainty'],'candidate')
        self.assertEqual(f['category'],'confirm')

    def test_independent_complete_expectations_and_read_set_find_real_omission(self):
        missing='https://bingx.com/ja/price/bitcoin'
        exp=expected([{'url':PAGE,'published':True,'should_index':True,'canonical_url':PAGE}, {'url':missing,'published':True,'should_index':True,'canonical_url':missing}])
        result=self.audit(expected=exp)
        f=next(f for f in result['findings'] if f['rule']=='sitemap_expected_missing')
        self.assertEqual(f['url'],missing)
        self.assertEqual(f['category'],'add')
        self.assertEqual(f['certainty'],'confirmed')
        self.assertEqual(result['coverage']['expected_indexable_urls'],2)
        self.assertEqual(result['coverage']['expected_present_urls'],1)

    def test_same_sitemap_source_cannot_prove_completeness(self):
        result=self.audit(expected=expected([{'url':PAGE,'published':True,'should_index':True,'canonical_url':PAGE}],kind='sitemap'))
        self.assertIsNone(result['coverage']['expected_indexable_urls'])
        self.assertIn('expected_source_not_independent',self.codes(result))

    def test_missing_in_partial_set_is_only_candidate(self):
        exp=expected([{'url':PAGE,'published':True,'should_index':True,'canonical_url':PAGE}])
        result=self.audit([doc(ROOT,xml([LEAF],'sitemapindex'))],expected=exp)
        f=next(f for f in result['findings'] if f['rule']=='sitemap_expected_missing')
        self.assertEqual(f['certainty'],'candidate')
        self.assertEqual(f['category'],'confirm')

    def test_unknown_intent_is_not_counted_as_should_be_indexed(self):
        result=self.audit(expected=expected([{'url':PAGE}]))
        self.assertEqual(result['coverage']['expected_indexable_urls'],0)
        self.assertIn('expected_intent_unknown',self.codes(result))

    def test_business_retirement_is_distinct_from_old_lastmod(self):
        result=self.audit(expected=expected([{'url':PAGE,'retired':True}]))
        self.assertIn('sitemap_retired_entry',self.codes(result))
        body=f'<urlset xmlns="{NS}"><url><loc>{PAGE}</loc><lastmod>2001-01-01</lastmod></url></urlset>'.encode()
        self.assertNotIn('sitemap_retired_entry',self.codes(self.audit([doc(ROOT,body)])))

    def test_lastmod_checked_against_known_significant_change(self):
        body=f'<urlset xmlns="{NS}"><url><loc>{PAGE}</loc><lastmod>2026-01-01</lastmod></url></urlset>'.encode()
        result=self.audit([doc(ROOT,body)],expected=expected([{'url':PAGE,'modified_at':'2026-09-15','modification_kind':'significant'}]))
        self.assertIn('lastmod_behind_known_change',self.codes(result))
        result=self.audit([doc(ROOT,body)],expected=expected([{'url':PAGE,'modified_at':'2026-09-15','modification_kind':'copyright'}]))
        self.assertNotIn('lastmod_behind_known_change',self.codes(result))

    def test_cross_site_submission_configuration_prevents_false_domain_error(self):
        other='https://blog.bingx.com/a'
        result=self.audit([doc(ROOT,xml([other]))])
        self.assertIn('sitemap_cross_site_unverified',self.codes(result))
        result=self.audit([doc(ROOT,xml([other]))],cross_site_hosts=['blog.bingx.com'])
        self.assertNotIn('sitemap_cross_site_unverified',self.codes(result))

    def test_empty_roots_cannot_produce_vacuous_complete_claim(self):
        result=self.module('audit').audit([],{},[],AT)
        self.assertFalse(result['coverage']['sitemap_set_read_complete'])
        self.assertIn('sitemap_roots_unknown',self.codes(result))

    def test_two_files_same_broken_url_produce_one_issue_with_both_sources(self):
        other='https://bingx.com/second.xml'
        result=self.audit([doc(ROOT,xml([LEAF,other],'sitemapindex')),doc(LEAF,xml([PAGE])),doc(other,xml([PAGE]))],pages={PAGE:page(404)})
        findings=[f for f in result['findings'] if f['rule']=='sitemap_http_missing']
        self.assertEqual(len(findings),1)
        self.assertEqual(set(findings[0]['sitemaps']),{LEAF,other})

    def test_bot_header_noindex_is_not_promoted_to_all_engines(self):
        result=self.audit(pages={PAGE:page(200,headers={'x-robots-tag':'googlebot: noindex, nofollow'})})
        f=next(f for f in result['findings'] if f['rule']=='sitemap_noindex_conflict')
        self.assertEqual(f['engine'],'googlebot')

    def test_observed_error_content_requires_explicit_reviewer_evidence(self):
        result=self.audit(pages={PAGE:page(200,content_verdict={'state':'error_content','evidence':'Rendered H1: Page not found','reviewed_at':AT})})
        self.assertIn('sitemap_error_content',self.codes(result))
        result=self.audit(pages={PAGE:page(200,title='404 coin price forecast')})
        self.assertNotIn('sitemap_error_content',self.codes(result))
