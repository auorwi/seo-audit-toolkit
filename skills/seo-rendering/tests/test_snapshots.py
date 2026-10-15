from support import RenderingTest

URL='https://bingx.com/en/price/bitcoin'

class SnapshotTests(RenderingTest):
    def test_dom_pagination_fields_preserve_observed_items_and_page(self):
        try:result=self.module('snapshots').normalize_dom({'url':URL,'visible_items':['BTC','ETH'],'page_indicator':'2117','coverage':{'visible_items':'complete','page_indicator':'complete'}})
        except ValueError:self.fail('Pagination capture fields are not supported yet')
        self.assertEqual(result['visible_items'],['BTC','ETH']);self.assertEqual(result['page_indicator'],'2117')

    def html(self,text,**kw):
        return self.module('snapshots').extract_html(text,URL,**kw)

    def test_initial_html_preserves_empty_h1_without_calling_it_rendered_failure(self):
        result=self.html('<html><head><title>Bitcoin</title></head><body><main><h1></h1></main></body></html>')
        self.assertEqual(result['h1'],['']);self.assertEqual(result['title'],'Bitcoin')
        self.assertEqual(result['representation'],'initial_html')
        self.assertIsNone(result['identity']);self.assertIsNone(result['placeholder_count'])

    def test_title_description_and_canonical_duplicates_are_preserved(self):
        result=self.html('<head><title>A</title><title>B</title><meta name="description" content="One"><meta name="description" content="Two"><link rel="canonical" href="/en"><link rel="canonical" href="/en"></head>')
        self.assertEqual(result['titles'],['A','B']);self.assertEqual(result['descriptions'],['One','Two'])
        self.assertEqual(result['canonical'],['https://bingx.com/en','https://bingx.com/en'])

    def test_main_text_excludes_script_style_comment_and_inert_template(self):
        result=self.html('<main><h1>Bitcoin <span>BTC</span></h1><script>SECRET</script><style>.x{content:"NO"}</style><!--ignore--><template>HIDDEN</template><p>Price information</p></main>')
        self.assertEqual(result['h1'],['Bitcoin BTC'])
        self.assertEqual(result['main_text'],'Bitcoin BTC Price information')
        self.assertNotIn('SECRET',result['main_text'])

    def test_navigation_text_is_not_invented_as_main_content(self):
        result=self.html('<nav>BTC ETH</nav><div>Other</div>')
        self.assertIsNone(result['main_text'])
        self.assertEqual(result['coverage']['main_text'],'unknown')

    def test_role_main_supported_with_nested_text(self):
        result=self.html('<div role="main"><h1>Solv</h1><p>Project <strong>details</strong></p></div>')
        self.assertEqual(result['main_text'],'Solv Project details')

    def test_relative_links_resolve_but_action_urls_are_not_crawl_targets(self):
        result=self.html('<main><a href="/en/price/ethereum">ETH</a><a href="javascript:trade()">Trade</a><button>Next</button></main>')
        self.assertEqual(result['links'][0]['href'],'https://bingx.com/en/price/ethereum')
        self.assertEqual(result['links'][0]['text'],'ETH')
        self.assertIsNone(result['links'][1]['href'])
        self.assertEqual(result['links'][1]['raw_href'],'javascript:trade()')

    def test_json_ld_preserves_multiple_blocks_and_parse_failures(self):
        result=self.html('<script type="application/ld+json">{"@type":"Product","name":"BTC"}</script><script type="application/ld+json">{bad}</script>')
        self.assertEqual(len(result['schema']),2)
        self.assertEqual(result['schema'][0]['parsed']['name'],'BTC')
        self.assertEqual(result['schema'][1]['error'],'invalid_json')

    def test_schema_same_id_is_not_automatically_duplicate_error(self):
        result=self.html('<script type="application/ld+json">{"@id":"#org"}</script><script type="application/ld+json">{"@id":"#org","name":"BingX"}</script>')
        self.assertEqual(len(result['schema']),2)
        self.assertEqual(result['schema'][1]['parsed']['name'],'BingX')

    def test_main_and_links_truncation_is_explicit_partial_coverage(self):
        result=self.html('<main>abcdefghijklmnop<a href="/a">a</a><a href="/b">b</a></main>',max_text_chars=5,max_links=1)
        self.assertEqual(result['main_text'],'abcde')
        self.assertEqual(result['coverage']['main_text'],'partial')
        self.assertEqual(result['coverage']['links'],'partial')
        self.assertEqual(len(result['links']),1)

    def test_incomplete_dom_fields_remain_unknown_not_empty(self):
        mod=self.module('snapshots')
        result=mod.normalize_dom({'url':URL,'title':'Bitcoin','coverage':{'title':'complete'}})
        self.assertIsNone(result['h1']);self.assertIsNone(result['canonical'])
        self.assertEqual(result['coverage']['h1'],'unknown')

    def test_complete_empty_dom_heading_is_distinct_from_uncaptured_heading(self):
        result=self.module('snapshots').normalize_dom({'url':URL,'h1':[],'coverage':{'h1':'complete'}})
        self.assertEqual(result['h1'],[]);self.assertEqual(result['coverage']['h1'],'complete')

    def test_dom_fields_do_not_pretend_to_be_complete_html(self):
        result=self.module('snapshots').normalize_dom({'url':URL,'title':'A','coverage':{'title':'complete'}})
        self.assertEqual(result['representation'],'dom_fields')
        self.assertFalse(result['full_dom'])

    def test_capture_claim_without_value_is_rejected(self):
        with self.assertRaises(ValueError):self.module('snapshots').normalize_dom({'url':URL,'coverage':{'h1':'complete'}})

    def test_bad_dom_types_or_coverage_are_rejected(self):
        for data in [{'url':URL,'h1':'Heading','coverage':{'h1':'complete'}}, {'url':URL,'h1':[],'coverage':{'h1':'all'}}]:
            with self.subTest(data=data),self.assertRaises(ValueError):self.module('snapshots').normalize_dom(data)

    def test_source_urls_preserve_entity_query_and_case(self):
        result=self.module('snapshots').normalize_dom({'url':'https://bingx.com/en/Detail?currency=78','coverage':{}})
        self.assertEqual(result['url'],'https://bingx.com/en/Detail?currency=78')

    def test_title_entities_and_whitespace_match_visible_text(self):
        result=self.html('<head><title>BTC &amp; ETH\n Prices</title></head>')
        self.assertEqual(result['title'],'BTC & ETH Prices')
