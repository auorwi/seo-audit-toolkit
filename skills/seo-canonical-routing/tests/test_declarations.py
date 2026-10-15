from support import RoutingTest

URL='https://bingx.com/en/launchpad/detail?currency=78'

class DeclarationTests(RoutingTest):
    def parse(self,html='',headers=None,url=URL):
        return self.module('declarations').parse(html,headers or [],url)

    def test_entity_query_and_path_case_not_removed(self):
        result=self.parse('<head><link rel="canonical" href="/en/launchpad/Detail?currency=78&amp;type=A"></head>')
        self.assertEqual(result['targets'],['https://bingx.com/en/launchpad/Detail?currency=78&type=A'])

    def test_relative_resolution_uses_first_head_base(self):
        result=self.parse('<head><base href="/en/"><base href="/fr/"><link rel="canonical" href="price/btc"></head>')
        self.assertEqual(result['targets'],['https://bingx.com/en/price/btc'])
        self.assertIn('multiple_base_elements',result['warnings'])

    def test_base_after_canonical_still_controls_document_resolution(self):
        result=self.parse('<head><link rel="canonical" href="btc"><base href="https://bingx.com/en/price/"></head>')
        self.assertEqual(result['targets'],['https://bingx.com/en/price/btc'])

    def test_body_canonical_is_evidence_but_not_effective_head_declaration(self):
        result=self.parse('<html><head></head><body><link rel="canonical" href="/en"></body></html>')
        self.assertEqual(result['targets'],[])
        self.assertIn('canonical_outside_head',result['warnings'])
        self.assertEqual(result['declarations'][0]['raw_target'],'/en')

    def test_comment_script_and_template_do_not_create_canonical(self):
        result=self.parse('<head><!-- <link rel=canonical href=/wrong> --><script>"<link rel=canonical href=/wrong>"</script><template><link rel=canonical href=/wrong></template></head>')
        self.assertEqual(result['targets'],[])

    def test_multiple_html_and_header_targets_report_conflict(self):
        result=self.parse('<head><link rel="canonical" href="/a"></head>',[('Link','<https://bingx.com/b>; rel="canonical"')])
        self.assertEqual(set(result['targets']),{'https://bingx.com/a','https://bingx.com/b'})
        self.assertTrue(result['conflict'])

    def test_identical_repeated_target_is_not_conflict(self):
        result=self.parse('<head><link rel="canonical" href="/a"><link rel="canonical" href="/a"></head>')
        self.assertFalse(result['conflict']);self.assertEqual(len(result['declarations']),2)
        self.assertIn('duplicate_canonical_declarations',result['warnings'])

    def test_http_link_comma_in_uri_and_quoted_param_preserved(self):
        result=self.parse(headers=[('Link','<https://bingx.com/a,b>; title="x,y"; rel="canonical", </other>; rel="alternate"')])
        self.assertEqual(result['targets'],['https://bingx.com/a,b'])

    def test_repeated_link_headers_and_multivalue_rel(self):
        result=self.parse(headers=[('LINK','</a>; rel="alternate canonical"'),('link','</b>; rel=canonical')])
        self.assertEqual(set(result['targets']),{'https://bingx.com/a','https://bingx.com/b'})

    def test_disqualifying_alternate_attributes_not_used_for_google_canonical(self):
        for attr in ['hreflang="fr"','lang="en"','media="print"','type="application/pdf"']:
            result=self.parse('<head><link rel="canonical" href="/a" '+attr+'></head>')
            self.assertEqual(result['targets'],[])
            self.assertIn('canonical_alternate_attributes',result['warnings'])

    def test_fragment_kept_in_evidence_but_http_target_has_no_fragment(self):
        result=self.parse('<head><link rel="canonical" href="/a#part"></head>')
        self.assertEqual(result['targets'],['https://bingx.com/a'])
        self.assertEqual(result['declarations'][0]['resolved_target'],'https://bingx.com/a#part')
        self.assertIn('canonical_fragment',result['warnings'])

    def test_empty_href_not_invented_as_self_canonical(self):
        result=self.parse('<head><link rel="canonical" href=""></head>')
        self.assertEqual(result['targets'],[]);self.assertIn('canonical_empty_target',result['warnings'])

    def test_unsafe_or_credential_target_not_accepted(self):
        for target in ['javascript:alert(1)','https://u:pass@bingx.com/a']:
            result=self.parse('<head><link rel="canonical" href="'+target+'"></head>')
            self.assertEqual(result['targets'],[]);self.assertIn('canonical_invalid_target',result['warnings'])

    def test_missing_canonical_does_not_invent_required_error(self):
        result=self.parse('<head><title>Home</title></head>')
        self.assertEqual(result['targets'],[]);self.assertFalse(result['conflict'])
        self.assertEqual(result['warnings'],[])

    def test_noncanonical_link_header_not_a_canonical(self):
        result=self.parse(headers={'Link':'</style.css>; rel=preload; as=style'})
        self.assertEqual(result['targets'],[])

    def test_meta_refresh_delay_and_target_observed_without_following(self):
        result=self.parse('<head><meta http-equiv="refresh" content="0; URL=/en/new"></head>')
        self.assertEqual(result['refreshes'][0]['target'],'https://bingx.com/en/new')
        self.assertEqual(result['refreshes'][0]['delay_seconds'],0)
        self.assertEqual(result['refreshes'][0]['signal'],'permanent_hint')
        self.assertEqual(result['targets'],[])

    def test_delayed_http_refresh_is_temporary_not_canonical_declaration(self):
        result=self.parse(headers={'Refresh':'5; url="/en/later"'})
        self.assertEqual(result['refreshes'][0]['signal'],'temporary_hint')
        self.assertEqual(result['refreshes'][0]['target'],'https://bingx.com/en/later')

    def test_invalid_refresh_retains_warning(self):
        result=self.parse('<head><meta http-equiv="refresh" content="later; url=/a"></head>')
        self.assertEqual(result['refreshes'],[])
        self.assertIn('refresh_unparsed',result['warnings'])

    def test_js_text_is_not_proof_of_executed_client_redirect(self):
        result=self.parse('<script>window.location="/en/login"</script>')
        self.assertEqual(result['refreshes'],[]);self.assertEqual(result['targets'],[])

    def test_relative_http_link_ignores_html_base(self):
        result=self.parse('<head><base href="https://blog.bingx.com/"></head>',headers={'Link':'</a>; rel=canonical'})
        self.assertEqual(result['targets'],['https://bingx.com/a'])

    def test_link_anchor_with_different_context_is_not_applied_to_current_page(self):
        result=self.parse(headers={'Link':'</a>; rel=canonical; anchor="https://bingx.com/other"'})
        self.assertEqual(result['targets'],[])
        self.assertIn('link_anchor_context_unverified',result['warnings'])
