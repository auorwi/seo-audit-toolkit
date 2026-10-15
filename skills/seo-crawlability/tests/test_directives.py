from support import CrawlTest, AT

class DirectiveTests(CrawlTest):
    def test_google_expiration_not_assumed_supported_by_other_engines(self):
        for agent in ['Bingbot','YandexBot']:
            data=self.parse(headers={'X-Robots-Tag':'unavailable_after: 2020-01-01'},agent=agent)
            self.assertIsNone(data['expired'])
            self.assertIn('engine_expiration_behavior_unverified',data['warnings'])

    def test_body_meta_behavior_is_not_copied_from_google_to_other_engines(self):
        for agent in ['Bingbot','YandexBot']:
            data=self.parse('<body><meta name="robots" content="noindex"></body>',agent=agent)
            self.assertFalse(data['noindex'])
            self.assertIn('body_meta_behavior_unverified',data['warnings'])

    def parse(self,html='',headers=None,agent='Googlebot'):
        return self.module('directives').parse_directives(html,headers or [],agent,AT)

    def test_generic_and_specific_negative_rules_combine(self):
        data=self.parse('<meta name="robots" content="nofollow"><meta name="GoogleBot" content="noindex">')
        self.assertTrue(data['noindex']);self.assertTrue(data['nofollow'])
        self.assertEqual(data['index_status'],'unknown')

    def test_specific_positive_rule_does_not_override_generic_noindex(self):
        data=self.parse('<meta name="robots" content="noindex"><meta name="googlebot" content="index">')
        self.assertTrue(data['noindex']);self.assertTrue(data['index_conflict'])

    def test_other_engine_meta_is_not_applied_to_google(self):
        text='<meta name="bingbot" content="noindex">'
        self.assertFalse(self.parse(text)['noindex'])
        self.assertTrue(self.parse(text,agent='Bingbot')['noindex'])

    def test_yandex_generic_token_applies_to_yandexbot_only(self):
        html='<meta name="yandex" content="noindex">'
        self.assertTrue(self.parse(html,agent='YandexBot')['noindex'])
        self.assertFalse(self.parse(html)['noindex'])

    def test_none_expands_but_nosnippet_and_nofollow_do_not_mean_noindex(self):
        data=self.parse('<meta name="robots" content="none">')
        self.assertTrue(data['noindex']);self.assertTrue(data['nofollow'])
        data=self.parse('<meta name="robots" content="nosnippet, nofollow">')
        self.assertFalse(data['noindex']);self.assertTrue(data['nofollow'])

    def test_repeated_headers_preserve_every_value_and_reset_scope(self):
        data=self.parse(headers=[('X-Robots-Tag','bingbot: noindex'),('X-Robots-Tag','nofollow'),('x-robots-tag','googlebot: noindex')])
        self.assertTrue(data['noindex']);self.assertTrue(data['nofollow'])
        self.assertEqual(len([s for s in data['sources'] if s['kind']=='header']),3)

    def test_header_scope_continues_within_value_but_not_next_header(self):
        headers=[('X-Robots-Tag','bingbot: noindex, nofollow'),('X-Robots-Tag','index')]
        data=self.parse(headers=headers)
        self.assertFalse(data['noindex']);self.assertFalse(data['nofollow'])

    def test_header_and_html_conflict_is_reported_with_both_sources(self):
        data=self.parse('<meta name="robots" content="index">',[('X-Robots-Tag','noindex')])
        self.assertTrue(data['noindex']);self.assertTrue(data['index_conflict'])
        self.assertEqual({s['kind'] for s in data['sources']},{'meta','header'})

    def test_rfc_date_with_comma_not_split_into_bogus_directives(self):
        data=self.parse(headers=[('X-Robots-Tag','unavailable_after: Tue, 15 Sep 2026 10:00:00 GMT')])
        self.assertTrue(data['expired'])
        self.assertFalse(data['noindex'])
        self.assertEqual(data['expiration_values'],['Tue, 15 Sep 2026 10:00:00 GMT'])

    def test_future_or_invalid_expiration_is_not_expired(self):
        self.assertFalse(self.parse(headers={'X-Robots-Tag':'unavailable_after: 2027-01-01'})['expired'])
        data=self.parse(headers={'X-Robots-Tag':'unavailable_after: someday'})
        self.assertIsNone(data['expired'])
        self.assertIn('unavailable_after_unparsed',data['warnings'])

    def test_indexifembedded_does_not_cancel_standalone_noindex(self):
        data=self.parse('<meta name="robots" content="noindex,indexifembedded">')
        self.assertTrue(data['noindex']);self.assertTrue(data['embedded_exception'])

    def test_google_respects_body_meta_but_script_comment_template_are_inert(self):
        self.assertTrue(self.parse('<body><meta name="robots" content="noindex"></body>')['noindex'])
        html='<!-- <meta name="robots" content="noindex"> --><script>"<meta name=robots content=noindex>"</script><template><meta name="robots" content="noindex"></template>'
        self.assertFalse(self.parse(html)['noindex'])

    def test_first_duplicate_html_attribute_matches_browser_behavior(self):
        data=self.parse('<meta name="bingbot" name="robots" content="noindex">')
        self.assertFalse(data['noindex'])

    def test_case_space_tokens_and_line_evidence(self):
        data=self.parse('<head>\n<META NAME="ROBOTS" CONTENT="NOINDEX NOFOLLOW"></head>')
        self.assertTrue(data['noindex']);self.assertTrue(data['nofollow'])
        self.assertEqual(data['sources'][0]['line'],2)

    def test_no_instructions_is_not_positive_index_confirmation(self):
        data=self.parse('<h1>Bitcoin</h1>')
        self.assertFalse(data['noindex']);self.assertEqual(data['index_status'],'unknown')
