from support import CrawlTest

class RobotsTests(CrawlTest):
    def test_specific_agent_group_does_not_merge_global_disallow(self):
        result=self.rules('User-agent: *\nDisallow: /\nUser-agent: Googlebot\nAllow: /en')
        self.assertTrue(result['allowed'])
        self.assertEqual(result['selected_agents'],['googlebot'])

    def test_same_specific_groups_are_combined(self):
        text='User-agent: Googlebot\nDisallow: /a\nUser-agent: Bingbot\nDisallow: /\nUser-agent: GOOGLEBOT\nDisallow: /b'
        self.assertFalse(self.rules(text,'https://bingx.com/a')['allowed'])
        self.assertFalse(self.rules(text,'https://bingx.com/b')['allowed'])
        self.assertTrue(self.rules(text,'https://bingx.com/c')['allowed'])

    def test_yandexbot_prefers_exact_then_yandex_then_global(self):
        text='User-agent: *\nDisallow: /\nUser-agent: Yandex\nDisallow: /a\nUser-agent: YandexBot\nDisallow: /b'
        self.assertTrue(self.rules(text,'https://bingx.com/a',agent='YandexBot')['allowed'])
        self.assertFalse(self.rules(text,'https://bingx.com/b',agent='YandexBot')['allowed'])
        self.assertFalse(self.rules('User-agent: Yandex\nDisallow: /a','https://bingx.com/a',agent='YandexBot')['allowed'])

    def test_longest_path_and_allow_tie(self):
        text='User-agent: *\nDisallow: /\nDisallow: /en\nAllow: /en/public\nDisallow: /en/public'
        self.assertTrue(self.rules(text,'https://bingx.com/en/public')['allowed'])
        self.assertFalse(self.rules(text,'https://bingx.com/en/private')['allowed'])

    def test_official_wildcard_precedence_examples(self):
        self.assertFalse(self.rules('User-agent: *\nAllow: /page\nDisallow: /*.htm','https://bingx.com/page.htm')['allowed'])
        self.assertTrue(self.rules('User-agent: *\nAllow: /page\nDisallow: /*.ph','https://bingx.com/page.php5')['allowed'])

    def test_query_and_end_anchor_are_considered_without_fragment(self):
        text='User-agent: *\nDisallow: /*?currency=84$'
        self.assertFalse(self.rules(text,'https://bingx.com/en/xpool/detail?currency=84#section')['allowed'])
        self.assertTrue(self.rules(text,'https://bingx.com/en/xpool/detail?currency=840')['allowed'])

    def test_path_is_case_sensitive_but_field_and_agent_are_not(self):
        text='uSeR-AgEnT: gOoGlEbOt\nDISALLOW: /CopyTrading'
        self.assertFalse(self.rules(text,'https://bingx.com/CopyTrading')['allowed'])
        self.assertTrue(self.rules(text,'https://bingx.com/copytrading')['allowed'])

    def test_utf8_and_percent_encoded_paths_match(self):
        text='User-agent: *\nDisallow: /ツ'
        self.assertFalse(self.rules(text,'https://bingx.com/%E3%83%84')['allowed'])
        self.assertFalse(self.rules('User-agent: *\nDisallow: /%E3%83%84','https://bingx.com/ツ')['allowed'])

    def test_unreserved_encoding_is_decoded_but_reserved_slash_is_not(self):
        text='User-agent: *\nDisallow: /foo/bar'
        self.assertFalse(self.rules(text,'https://bingx.com/foo/%62ar')['allowed'])
        self.assertTrue(self.rules(text,'https://bingx.com/foo%2Fbar')['allowed'])

    def test_encoded_wildcard_and_dollar_are_literals(self):
        text='User-agent: *\nDisallow: /file%2A\nDisallow: /money%24'
        self.assertFalse(self.rules(text,'https://bingx.com/file*')['allowed'])
        self.assertFalse(self.rules(text,'https://bingx.com/money$')['allowed'])
        self.assertTrue(self.rules(text,'https://bingx.com/file123')['allowed'])

    def test_empty_rules_and_rules_before_any_agent_are_ignored(self):
        self.assertTrue(self.rules('Disallow: /\nUser-agent: *\nDisallow: \nAllow: ')['allowed'])

    def test_bom_comments_and_cr_lines_keep_evidence_line_numbers(self):
        result=self.rules('\ufeff# intro\rUser-agent: *\rDisallow: /en # comment')
        self.assertFalse(result['allowed'])
        self.assertEqual(result['matched_rules'][0]['line'],3)

    def test_main_origin_rules_do_not_apply_to_subdomain_scheme_or_port(self):
        for url in ['https://blog.bingx.com/en','http://bingx.com/en','https://bingx.com:444/en']:
            with self.subTest(url=url):
                result=self.rules('User-agent: *\nDisallow: /',url)
                self.assertIsNone(result['allowed'])
                self.assertEqual(result['reason'],'robots_origin_mismatch')

    def test_default_port_is_equivalent_but_subdirectory_robots_not_authoritative(self):
        self.assertFalse(self.rules('User-agent: *\nDisallow: /','https://bingx.com:443/en')['allowed'])
        result=self.rules('User-agent: *\nDisallow: /',robots_url='https://bingx.com/en/robots.txt')
        self.assertIsNone(result['allowed'])

    def test_google_html_response_keeps_valid_lines_and_marks_technical_problem(self):
        result=self.rules('<!doctype html>\nUser-agent: *\nDisallow: /en\n</html>')
        self.assertFalse(result['allowed'])
        self.assertIn('robots_html_response',result['warnings'])

    def test_google_ignores_rules_after_500_kib_and_reports_truncation(self):
        body=b'User-agent: *\n'+b'#'+b'a'*(512000-len(b'User-agent: *\n')-2)+b'\nDisallow: /en\n'
        result=self.rules(body)
        self.assertTrue(result['allowed'])
        self.assertIn('robots_size_truncated',result['warnings'])

    def test_noindex_in_robots_is_not_a_valid_indexing_directive(self):
        result=self.rules('User-agent: *\nNoindex: /en')
        self.assertTrue(result['allowed'])
        self.assertIn('robots_noindex_unsupported',result['warnings'])

    def test_sitemap_between_agents_does_not_split_a_google_group(self):
        text='User-agent: googlebot\nSitemap: https://bingx.com/sitemap.xml\nUser-agent: bingbot\nDisallow: /en'
        self.assertFalse(self.rules(text)['allowed'])
