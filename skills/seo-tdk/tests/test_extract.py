from support import TdkTest,URL
class ExtractTests(TdkTest):
    def parse(self,html,**kw):return self.module('extract').extract(html,URL,**kw)
    def test_title_and_description_keep_original_and_source_location(self):
        r=self.parse('<html><head>\n<title> BTC &amp; Price </title><meta NAME="Description" content="BTC &amp; USDT"></head><body><h1>BTC <span>Price</span></h1></body></html>')
        self.assertEqual(r['titles'][0]['value'],' BTC & Price ')
        self.assertEqual(r['descriptions'][0]['value'],'BTC & USDT')
        self.assertEqual(r['titles'][0]['line'],2)
        self.assertEqual(r['h1'],['BTC Price'])
    def test_duplicates_are_preserved_even_identical(self):
        r=self.parse('<head><title>A</title><title>A</title><meta name="description" content="D"><meta name="description" content="D"></head>')
        self.assertEqual(len(r['titles']),2);self.assertEqual(len(r['descriptions']),2)
    def test_empty_missing_content_and_missing_tag_are_distinct(self):
        r=self.parse('<head><title> </title><meta name="description"></head>')
        self.assertEqual(r['titles'][0]['value'],' ');self.assertIsNone(r['descriptions'][0]['value']);self.assertEqual(r['keywords'],[])
    def test_template_svg_and_body_title_not_head_title(self):
        r=self.parse('<head><template><title>Template</title></template><title>Real</title></head><body><svg><title>Icon</title></svg><title>Body</title></body>')
        self.assertEqual([x['value'] for x in r['titles']],['Real'])
    def test_script_style_and_template_text_excluded_from_content(self):
        r=self.parse('<head><title>A</title><style>secret</style></head><body><main>BTC<script>fake ETH</script><template>fake SOL</template> price</main></body>')
        self.assertEqual(r['body_text'],'BTC price')
    def test_language_and_existing_keywords_are_inventory_only(self):
        r=self.parse('<html lang="zh-Hant"><head><meta name="KEYWORDS" content="Bitcoin,BTC"></head></html>')
        self.assertEqual(r['html_lang'],'zh-Hant');self.assertEqual(r['keywords'][0]['value'],'Bitcoin,BTC')
    def test_og_description_is_not_meta_description(self):
        r=self.parse('<head><meta property="og:description" content="OG"></head>')
        self.assertEqual(r['descriptions'],[])
    def test_unicode_and_inline_heading_spacing(self):
        r=self.parse('<head><title>比特币价格</title></head><body><h1>比特币<span>价格</span></h1></body>')
        self.assertEqual(r['titles'][0]['value'],'比特币价格');self.assertEqual(r['h1'],['比特币价格'])
    def test_truncated_content_records_incomplete(self):
        r=self.parse('<body>'+'a'*100+'</body>',max_text_chars=20)
        self.assertEqual(len(r['body_text']),20);self.assertFalse(r['coverage']['body_complete'])
    def test_unclosed_title_not_silently_missing(self):
        r=self.parse('<head><title>BTC')
        self.assertEqual(r['titles'][0]['value'],'BTC');self.assertFalse(r['coverage']['closed_head'])
