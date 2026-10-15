import gzip
import json
from support import InventoryTest


class ExtractTests(InventoryTest):
    def test_robots_wildcard_specificity_matches_published_path_examples(self):
        mod = self.module("extract")
        policy = mod.RobotsPolicy('User-agent: *\nAllow: /page\nDisallow: /*.htm\n')
        self.assertFalse(policy.allowed('https://bingx.com/page.htm'))
        policy = mod.RobotsPolicy('User-agent: *\nAllow: /page\nDisallow: /*.ph\n')
        self.assertTrue(policy.allowed('https://bingx.com/page.php5'))

    def test_sitemap_index_returns_child_files_not_page_urls(self):
        p = self.module("extract").parse_sitemap
        r = p(b'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://bingx.com/en.xml</loc></sitemap></sitemapindex>')
        self.assertEqual(r["kind"], "index")
        self.assertEqual(r["children"], ["https://bingx.com/en.xml"])
        self.assertEqual(r["pages"], [])

    def test_urlset_preserves_business_query_and_language_alternates(self):
        body = b'''<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"><url><loc>https://bingx.com/en/detail?currency=84&amp;x=2</loc><lastmod>2020-01-01</lastmod><xhtml:link rel="alternate" hreflang="ja" href="https://bingx.com/ja/detail?currency=84"/><image:image><image:loc>https://cdn.test/a.png</image:loc></image:image></url></urlset>'''
        r = self.module("extract").parse_sitemap(body)
        self.assertEqual(r["pages"], [{"url": "https://bingx.com/en/detail?currency=84&x=2", "lastmod": "2020-01-01"}])
        self.assertEqual(r["alternates"][0]["url"], "https://bingx.com/ja/detail?currency=84")

    def test_gzip_sitemap(self):
        r = self.module("extract").parse_sitemap(gzip.compress(b'<urlset><url><loc>https://bingx.com/en</loc></url></urlset>'))
        self.assertEqual(r["pages"][0]["url"], "https://bingx.com/en")

    def test_rejects_html_malformed_xml_and_relative_sitemap_locations(self):
        p = self.module("extract").parse_sitemap
        for body in [b"<html>Access denied</html>", b"<urlset>", b"<urlset><url><loc>/en</loc></url></urlset>"]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                p(body)

    def test_rejects_doctype_even_in_utf16(self):
        p = self.module("extract").parse_sitemap
        text = '<!DOCTYPE urlset [<!ENTITY a "https://bingx.com/en">]><urlset><url><loc>&a;</loc></url></urlset>'
        for encoding in ["utf-8", "utf-16"]:
            with self.subTest(encoding=encoding), self.assertRaises(ValueError):
                p(text.encode(encoding))

    def test_limits_decompressed_sitemap_size(self):
        p = self.module("extract").parse_sitemap
        with self.assertRaises(ValueError):
            p(gzip.compress(b"<urlset>" + b" " * 1000 + b"</urlset>"), max_bytes=100)

    def test_html_extracts_links_canonical_alternate_and_resolves_first_base(self):
        body = '<base href="/en/"><base href="https://evil.test/"><a href="price/btc#faq">BTC</a><a href="javascript:void(0)">x</a><link rel="canonical" href="price/btc"><link rel="alternate" hreflang="ja" href="/ja/price/btc"><meta name="robots" content="noindex,follow"><title>BTC &amp; More</title>'
        r = self.module("extract").parse_html(body, "https://bingx.com/old/")
        self.assertEqual(r["links"], ["https://bingx.com/en/price/btc"])
        self.assertEqual(r["canonicals"], ["https://bingx.com/en/price/btc"])
        self.assertEqual(r["alternates"][0]["url"], "https://bingx.com/ja/price/btc")
        self.assertTrue(r["noindex"])
        self.assertEqual(r["title"], "BTC & More")

    def test_base_after_anchor_still_applies_to_document(self):
        r = self.module("extract").parse_html('<a href="btc">x</a><base href="/en/price/">', "https://bingx.com/")
        self.assertEqual(r["links"], ["https://bingx.com/en/price/btc"])

    def test_csv_bom_chinese_header_and_blank_rows(self):
        p = self.module("extract").parse_import
        r = p('\ufeff网页,点击次数\nhttps://bingx.com/en,12\n,0\n'.encode(), "csv")
        self.assertEqual(r, [{"url": "https://bingx.com/en"}])

    def test_json_historical_and_envelope_imports(self):
        p = self.module("extract").parse_import
        for value in [[{"url": "https://bingx.com/en", "id": "P001"}],
                      {"records": ["https://bingx.com/en"]}]:
            r = p(json.dumps(value).encode(), "json")
            self.assertEqual(r[0]["url"], "https://bingx.com/en")

    def test_ambiguous_columns_and_invalid_json_shape_fail_instead_of_empty_success(self):
        p = self.module("extract").parse_import
        for data, fmt in [(b"x,y\na,b\n", "csv"), (b'{"error":"login required"}', "json")]:
            with self.subTest(fmt=fmt), self.assertRaises(ValueError):
                p(data, fmt)

    def test_robots_prefers_specific_group_and_longest_allow(self):
        cls = self.module("extract").RobotsPolicy
        body = 'User-agent: *\nDisallow: /\nUser-agent: SeoAuditToolkit\nDisallow: /private\nAllow: /private/public\nSitemap: https://bingx.com/sitemap.xml\n'
        r = cls(body)
        self.assertTrue(r.allowed("https://bingx.com/en"))
        self.assertFalse(r.allowed("https://bingx.com/private/a"))
        self.assertTrue(r.allowed("https://bingx.com/private/public/a"))
        self.assertEqual(r.sitemaps, ["https://bingx.com/sitemap.xml"])

    def test_robots_wildcard_query_and_end_anchor(self):
        r = self.module("extract").RobotsPolicy('User-agent: *\nDisallow: /*?sort=\nDisallow: /gone$\nAllow: /gone/new\n')
        self.assertFalse(r.allowed("https://bingx.com/en?sort=up"))
        self.assertFalse(r.allowed("https://bingx.com/gone"))
        self.assertTrue(r.allowed("https://bingx.com/gone/new"))
        self.assertTrue(r.allowed("https://bingx.com/gone/"))

    def test_robots_percent_encoded_unreserved_cannot_bypass_disallow(self):
        cls=self.module('extract').RobotsPolicy
        rules=cls('User-agent: *\nDisallow: /private\nDisallow: /%61dmin$\nDisallow: /docs/*?sort=\n')
        for path in ['/private','/%70rivate','/pr%69vate/account','/%61dmin','/admin','/docs/a?%73ort=up']:
            with self.subTest(path=path):self.assertFalse(rules.allowed('https://example.com'+path))
        self.assertTrue(rules.allowed('https://example.com/admin/new'))
        self.assertTrue(rules.allowed('https://example.com/Private'))

    def test_robots_reserved_slash_is_distinct_and_hex_case_is_normalized(self):
        cls=self.module('extract').RobotsPolicy
        plain=cls('User-agent: *\nDisallow: /private/account$\n')
        self.assertFalse(plain.allowed('https://example.com/private/account'))
        self.assertTrue(plain.allowed('https://example.com/private%2Faccount'))
        encoded=cls('User-agent: *\nDisallow: /private%2faccount$\n')
        self.assertFalse(encoded.allowed('https://example.com/private%2Faccount'))
        self.assertTrue(encoded.allowed('https://example.com/private/account'))

    def test_robots_equivalent_rule_specificity_uses_normalized_octets(self):
        rules=self.module('extract').RobotsPolicy('User-agent: *\nDisallow: /%61b\nAllow: /ab\n')
        self.assertTrue(rules.allowed('https://example.com/ab'))

    def test_robots_encoded_literal_metacharacters_match_uri_literals(self):
        cls=self.module('extract').RobotsPolicy
        rules=cls('User-agent: *\nDisallow: /file%2A.html\nDisallow: /foo%24\nDisallow: /inner$amount\n')
        for path in ['/file*.html','/file%2a.html','/foo$','/foo%24','/inner$amount']:
            with self.subTest(path=path):self.assertFalse(rules.allowed('https://example.com'+path))
        for path in ['/fileX.html','/file%252A.html','/foo','/innerXamount']:
            with self.subTest(path=path):self.assertTrue(rules.allowed('https://example.com'+path))
        wildcard=cls('User-agent: *\nDisallow: /file*.html$\nDisallow: /exact$\n')
        self.assertFalse(wildcard.allowed('https://example.com/file-any.html'))
        self.assertFalse(wildcard.allowed('https://example.com/exact'))
        self.assertTrue(wildcard.allowed('https://example.com/file-any.html/next'))
        self.assertTrue(wildcard.allowed('https://example.com/exact$'))

    def test_wrong_child_structure_is_not_a_complete_empty_sitemap(self):
        p = self.module("extract").parse_sitemap
        for body in [b'<urlset><sitemap><loc>https://bingx.com/en</loc></sitemap></urlset>',
                     b'<sitemapindex><url><loc>https://bingx.com/en</loc></url></sitemapindex>']:
            with self.subTest(body=body), self.assertRaises(ValueError):
                p(body)

    def test_only_generic_robots_noindex_is_reported_as_generic_noindex(self):
        result = self.module("extract").parse_html('<meta name="googlebot" content="noindex">', 'https://bingx.com/en')
        self.assertFalse(result["noindex"])
        self.assertEqual(result["robots_directives"], {"googlebot": ["noindex"]})

    def test_import_preserves_legacy_source_ids_without_account_fields(self):
        p = self.module("extract").parse_import
        r = p(b'url,source_ids,coverage_note,email\nhttps://bingx.com/en,S001|S062,history,private@example.com\n', 'csv')
        self.assertEqual(r[0].get("source_ids"), "S001|S062")
        self.assertEqual(r[0]["coverage_note"], "history")
        self.assertNotIn("email", r[0])
