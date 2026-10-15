from support import InternationalTest
U='https://bingx.com/fr/price/bitcoin'
class ExtractTests(InternationalTest):
    def html(self,s):return self.module('extract').extract_html(s,U)
    def test_head_hreflang(self):
        r=self.html('<html lang="fr"><head><link rel="alternate" hreflang="en" href="https://bingx.com/en/a"></head>');self.assertEqual(r['alternates'][0]['target_url'],'https://bingx.com/en/a');self.assertTrue(r['alternates'][0]['eligible'])
    def test_relative_hreflang_resolved_but_ineligible(self):
        r=self.html('<head><link rel="alternate" hreflang="en" href="/en/a"></head>')['alternates'][0];self.assertEqual(r['target_url'],'https://bingx.com/en/a');self.assertIn('not_absolute',r['problems'])
    def test_scheme_relative_ineligible(self):self.assertFalse(self.html('<head><link rel="alternate" hreflang="en" href="//bingx.com/en/a"></head>')['alternates'][0]['eligible'])
    def test_body_declaration_preserved_but_invalid(self):self.assertIn('outside_head',self.html('<body><link rel="alternate" hreflang="en" href="https://bingx.com/en/a">')['alternates'][0]['problems'])
    def test_media_not_hreflang_equivalent(self):self.assertIn('media_attribute',self.html('<head><link rel="alternate" media="screen" hreflang="en" href="https://bingx.com/en/a">')['alternates'][0]['problems'])
    def test_template_ignored(self):self.assertEqual(self.html('<head><template><link rel="alternate" hreflang="fr" href="https://bingx.com/fr/a"></template>')['alternates'],[])
    def test_anchor_language_not_declaration(self):self.assertEqual(self.html('<a hreflang="fr" href="https://bingx.com/fr/a">fr</a>')['alternates'],[])
    def test_jsonld_nested_languages(self):self.assertEqual(self.html('<script type="application/ld+json">{"@graph":[{"inLanguage":"fr"},{"inLanguage":["en","fr"]}]}</script>')['schema_languages'][1]['path'],'$[script=0].@graph[1].inLanguage[0]')
    def test_broken_json_gap(self):self.assertEqual(len(self.html('<script type="application/ld+json">{bad</script>')['gaps']),1)
    def test_canonical_base(self):self.assertEqual(self.html('<head><base href="https://bingx.com/en/"><link rel="canonical" href="a?x=1"></head>')['canonicals'][0]['target_url'],'https://bingx.com/en/a?x=1')
    def test_duplicate_attribute_gap(self):self.assertTrue(self.html('<html lang="fr" lang="en">')['gaps'])
    def test_fragment_kept_as_problem(self):self.assertIn('fragment',self.html('<head><link rel="alternate" hreflang="fr" href="https://bingx.com/fr/a#top"></head>')['alternates'][0]['problems'])
    def test_external_hreflang_permitted(self):self.assertTrue(self.html('<head><link rel="alternate" hreflang="fr" href="https://example.fr/a"></head>')['alternates'][0]['eligible'])
    def test_http_quoted_comma(self):
        r=self.module('extract').extract_headers([['Link','<https://bingx.com/fr/a>; rel="alternate"; hreflang="fr"; title="A, B", <https://bingx.com/en/a>; rel="alternate"; hreflang="en"']],U);self.assertEqual(len(r['alternates']),2)
    def test_http_repeated_headers(self):
        r=self.module('extract').extract_headers([['link','<https://bingx.com/fr/a>; rel=alternate; hreflang=fr'],['LINK','<https://bingx.com/en/a>; rel=canonical']],U);self.assertEqual(len(r['alternates']),1);self.assertEqual(len(r['canonicals']),1)
    def test_http_anchor_context_not_assumed(self):
        r=self.module('extract').extract_headers([['Link','<https://bingx.com/fr/a>; rel=alternate; hreflang=fr; anchor="/other"']],U);self.assertFalse(r['alternates'][0]['eligible'])
    def test_sitemap_namespace(self):
        xml='<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml"><url><loc>https://bingx.com/en/a</loc><xhtml:link rel="alternate" hreflang="fr" href="https://bingx.com/fr/a"/></url></urlset>';r=self.module('extract').extract_sitemap(xml);self.assertEqual(r['alternates'][0]['source_url'],'https://bingx.com/en/a')
    def test_sitemap_wrong_namespace_not_used(self):
        xml='<urlset><url><loc>https://bingx.com/en/a</loc><link rel="alternate" hreflang="fr" href="https://bingx.com/fr/a"/></url></urlset>';r=self.module('extract').extract_sitemap(xml);self.assertEqual(r['alternates'],[]);self.assertTrue(r['gaps'])
    def test_sitemap_entity_rejected(self):
        with self.assertRaises(ValueError):self.module('extract').extract_sitemap('<!DOCTYPE x [<!ENTITY test "abc">]><urlset/>')
    def test_invalid_target_preserved(self):self.assertFalse(self.html('<head><link rel="alternate" hreflang="fr" href="javascript:alert(1)"></head>')['alternates'][0]['eligible'])
    def test_malformed_bracket_url_preserved(self):self.assertFalse(self.html('<head><link rel="alternate" hreflang="fr" href="https://[broken"></head>')['alternates'][0]['eligible'])
