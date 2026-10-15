from support import LinkTest,URL
class ExtractTests(LinkTest):
    def extract(self,html,**kw):return self.module('extract').extract_links(html,URL,**kw)
    def test_resolves_relative_href_and_preserves_query(self):
        r=self.extract('<main><a href="../ethereum?currency=78&amp;page=2"> Ether <b>details</b> </a></main>')['links'][0]
        self.assertEqual(r['target'],'https://bingx.com/en/ethereum?currency=78&page=2');self.assertEqual(r['anchor_text'],'Ether details');self.assertEqual(r['component'],'main')
    def test_first_base_applies_to_all_links_even_before_base_tag(self):
        r=self.extract('<a href="btc">BTC</a><base href="/en/academy/"><base href="/wrong/">')
        self.assertEqual(r['links'][0]['target'],'https://bingx.com/en/academy/btc');self.assertEqual(r['base_url'],'https://bingx.com/en/academy/')
    def test_external_base_not_silently_resolved_to_internal(self):
        r=self.extract('<base href="https://elsewhere.example/"><a href="btc">BTC</a>')['links'][0];self.assertEqual(r['target'],'https://elsewhere.example/btc');self.assertFalse(r['internal'])
    def test_invalid_base_is_gap_and_cannot_create_assumed_edges(self):
        r=self.extract('<base href="javascript:bad"><a href="btc">BTC</a>');self.assertTrue(r['gaps']);self.assertIsNone(r['links'][0]['target'])
    def test_fragment_has_page_target_but_is_not_a_new_document_edge(self):
        r=self.extract('<a href="#faq">FAQ</a>')['links'][0];self.assertEqual(r['target'],URL);self.assertTrue(r['same_document']);self.assertEqual(r['fragment'],'faq')
    def test_query_only_pagination_is_distinct_address(self):
        r=self.extract('<a href="?page=2">Next</a>')['links'][0];self.assertEqual(r['target'],URL+'?page=2');self.assertFalse(r['same_document'])
    def test_empty_href_and_missing_href_are_preserved_not_useful_new_edges(self):
        links=self.extract('<a href="">Empty</a><a routerLink="/en/price">Router</a>')['links'];self.assertEqual(links[0]['kind'],'empty_href');self.assertEqual(links[1]['kind'],'missing_href');self.assertIsNone(links[1]['target'])
    def test_javascript_mailto_data_are_not_fetchable_web_targets(self):
        for href in ['javascript:go(1)','mailto:help@bingx.com','data:text/html,x','tel:123']:
            r=self.extract(f'<a href="{href}">x</a>')['links'][0];self.assertIsNone(r['target']);self.assertEqual(r['kind'],'non_http_href')
    def test_userinfo_and_malformed_port_not_fetched(self):
        for href in ['https://user:pass@bingx.com/en','https://bingx.com:bad/en']:
            r=self.extract(f'<a href="{href}">x</a>');self.assertIsNone(r['links'][0]['target']);self.assertTrue(r['gaps'])
    def test_nofollow_rel_tokens_preserved_not_claimed_unfetchable(self):
        r=self.extract('<a href="/en/price" rel="NOFOLLOW ugc noopener">Price</a>')['links'][0]
        self.assertIn('nofollow',r['rel']);self.assertTrue(r['http_link']);self.assertTrue(r['internal'])
    def test_subdomain_scope_is_explicit_and_suffix_attack_excluded(self):
        r=self.extract('<a href="https://blog.bingx.com/a">Blog</a><a href="https://bingx.com.evil.test/a">Other</a>',internal_hosts=['bingx.com','blog.bingx.com'])['links'];self.assertTrue(r[0]['internal']);self.assertFalse(r[1]['internal'])
    def test_image_alt_and_title_separated_from_aria_accessible_name(self):
        r=self.extract('<a href="/a"><img alt="Bitcoin guide"></a><a href="/b" title="Price" aria-label="Open"></a>')['links']
        self.assertEqual(r[0]['seo_text_candidate'],'Bitcoin guide');self.assertEqual(r[1]['seo_text_candidate'],'Price');self.assertEqual(r[1]['aria_label'],'Open');self.assertTrue(r[1]['accessible_name_unverified'])
    def test_aria_only_link_not_falsely_reported_as_confirmed_empty_name(self):
        r=self.extract('<a href="/a" aria-label="Logo"><svg></svg></a>')['links'][0];self.assertEqual(r['seo_text_candidate'],'');self.assertEqual(r['aria_label'],'Logo');self.assertTrue(r['accessible_name_unverified'])
    def test_template_and_script_embedded_markup_not_real_links(self):
        r=self.extract('<template><a href="/inert">Inert</a></template><script>let s="<a href=\'/fake\'>x</a>";</script><a href="/real">Real</a>');self.assertEqual([x['target'] for x in r['links']],['https://bingx.com/real'])
    def test_noscript_link_preserved_as_conditional(self):
        r=self.extract('<noscript><a href="/fallback">Fallback</a></noscript>')['links'][0];self.assertTrue(r['conditional_noscript'])
    def test_controls_not_misrepresented_as_anchor_edges(self):
        r=self.extract('<button data-page="2">Next</button><span role="link" onclick="go()">More</span>');self.assertEqual(r['links'],[]);self.assertEqual(len(r['controls']),2);self.assertTrue(all(x['target'] is None for x in r['controls']))
    def test_duplicates_keep_each_location_and_component(self):
        r=self.extract('<nav><a href="/a">A</a></nav>\n<footer><a href="/a">A</a></footer>')['links'];self.assertEqual(len(r),2);self.assertNotEqual(r[0]['locator'],r[1]['locator']);self.assertEqual([x['component'] for x in r],['nav','footer'])
    def test_duplicate_href_attributes_flag_ambiguity_keep_browser_first_value(self):
        r=self.extract('<a href="/first" href="/last">X</a>');self.assertEqual(r['links'][0]['target'],'https://bingx.com/first');self.assertTrue(r['gaps'])
    def test_script_and_style_text_not_anchor_text(self):
        r=self.extract('<a href="/a">Good<script>secret</script><style>.x{}</style><span> Link</span></a>')['links'][0];self.assertEqual(r['anchor_text'],'Good Link')
    def test_html_lang_and_hreflang_preserved_without_auto_wrong_language(self):
        r=self.extract('<html lang="fr"><a href="/en/a" hreflang="en">English</a></html>');self.assertEqual(r['html_lang'],'fr');self.assertEqual(r['links'][0]['hreflang'],'en');self.assertFalse(r['findings'])
