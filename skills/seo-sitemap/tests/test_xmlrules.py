import gzip
from support import AuditTest, xml, NS

class XMLTests(AuditTest):
    def test_empty_sitemap_is_visible_without_being_mistaken_for_parse_failure(self):
        data=self.parse(xml([]))
        self.assertIn('sitemap_empty',self.codes(data))
        self.assertTrue(data['parsed_complete'])

    def test_empty_lastmod_is_not_same_as_omitted_lastmod(self):
        data=self.parse(f'<urlset xmlns="{NS}"><url><loc>https://bingx.com/en</loc><lastmod/></url></urlset>'.encode())
        self.assertIn('lastmod_invalid',self.codes(data))

    def test_overlong_url_and_malformed_percent_escape_are_invalid(self):
        for url in ['https://bingx.com/'+('a'*2048),'https://bingx.com/a%ZZ']:
            with self.subTest(url=url[:40]):
                self.assertIn('sitemap_loc_invalid',self.codes(self.parse(xml([url]))))

    def test_valid_leaf_preserves_business_parameters_and_old_lastmod(self):
        data = self.parse(f'<urlset xmlns="{NS}"><url><loc>https://bingx.com/en/xpool/detail?currency=84&amp;type=1</loc><lastmod>2015-01-01</lastmod></url></urlset>'.encode())
        self.assertEqual(data["kind"], "urlset")
        self.assertEqual(data["entries"][0]["url"], "https://bingx.com/en/xpool/detail?currency=84&type=1")
        self.assertEqual(data["findings"], [])
        self.assertTrue(data["parsed_complete"])

    def test_index_is_not_a_page_url_collection(self):
        data = self.parse(xml(["https://bingx.com/en/sitemap-main.xml"], "sitemapindex"))
        self.assertEqual(data["kind"], "index")
        self.assertEqual(len(data["entries"]), 1)

    def test_html_submission_is_not_an_empty_valid_sitemap(self):
        data = self.parse(b'<!doctype html><html><title>Login</title></html>')
        self.assertIn("sitemap_not_xml", self.codes(data))
        self.assertFalse(data["parsed_complete"])

    def test_malformed_xml_cannot_establish_completeness(self):
        data = self.parse(b'<urlset>')
        self.assertIn("sitemap_xml_invalid", self.codes(data))
        self.assertFalse(data["parsed_complete"])

    def test_non_utf8_is_reported_and_entities_are_not_expanded(self):
        data = self.parse(('<?xml version="1.0" encoding="UTF-16"?>'+xml([]).decode()).encode('utf-16'))
        self.assertIn("sitemap_encoding", self.codes(data))
        unsafe = b'<!DOCTYPE urlset [<!ENTITY xx "unsafe">]><urlset><url><loc>&xx;</loc></url></urlset>'
        self.assertIn("sitemap_doctype", self.codes(self.parse(unsafe)))

    def test_wrong_namespace_and_wrong_child_are_explicit(self):
        data = self.parse(b'<urlset xmlns="https://wrong.test"><sitemap><loc>https://bingx.com/en</loc></sitemap></urlset>')
        self.assertIn("sitemap_namespace", self.codes(data))
        self.assertIn("sitemap_structure", self.codes(data))
        self.assertFalse(data["parsed_complete"])

    def test_relative_missing_and_duplicate_loc_are_not_silently_used(self):
        data = self.parse(f'<urlset xmlns="{NS}"><url><loc>/en</loc></url><url/><url><loc>https://bingx.com/a</loc><loc>https://bingx.com/b</loc></url></urlset>'.encode())
        self.assertIn("sitemap_loc_invalid", self.codes(data))
        self.assertIn("sitemap_loc_count", self.codes(data))
        self.assertEqual(data["entries"], [])

    def test_duplicate_urls_retained_as_evidence(self):
        data = self.parse(xml(["https://bingx.com/en", "https://bingx.com/en"]))
        self.assertIn("sitemap_duplicate_entry", self.codes(data))
        self.assertEqual(len(data["entries"]), 2)

    def test_url_count_50000_allowed_50001_reported(self):
        self.assertNotIn("sitemap_entry_limit", self.codes(self.parse(xml([f'https://bingx.com/a/{i}' for i in range(50000)]))))
        self.assertIn("sitemap_entry_limit", self.codes(self.parse(xml([f'https://bingx.com/a/{i}' for i in range(50001)]))))

    def test_gzip_limit_uses_uncompressed_bytes(self):
        data = self.parse(gzip.compress(xml(["https://bingx.com/"+"a"*1000])), max_bytes=500)
        self.assertIn("sitemap_size_limit", self.codes(data))
        self.assertFalse(data["parsed_complete"])
        self.assertNotIn('sitemap_gzip_invalid',self.codes(self.parse(gzip.compress(xml([])))))

    def test_lastmod_invalid_or_future_but_missing_optional_fields_ok(self):
        for value, rule in [("2026-13-01", "lastmod_invalid"), ("2027-01-01", "lastmod_future"), ("2026-09-16T22:00:00", "lastmod_invalid")]:
            with self.subTest(value=value):
                body = f'<urlset xmlns="{NS}"><url><loc>https://bingx.com/en</loc><lastmod>{value}</lastmod></url></urlset>'.encode()
                self.assertIn(rule, self.codes(self.parse(body)))
        self.assertEqual(self.parse(xml(["https://bingx.com/en"]))["findings"], [])

    def test_extensions_do_not_count_image_urls_as_page_entries(self):
        body=f'<urlset xmlns="{NS}" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"><url><loc>https://bingx.com/en</loc><image:image><image:loc>https://cdn.test/a.jpg</image:loc></image:image></url></urlset>'.encode()
        self.assertEqual(len(self.parse(body)["entries"]), 1)

    def test_priority_and_changefreq_are_not_google_defects(self):
        body=f'<urlset xmlns="{NS}"><url><loc>https://bingx.com/en</loc><priority>0.5</priority><changefreq>monthly</changefreq></url></urlset>'.encode()
        self.assertEqual(self.parse(body)["findings"], [])

    def test_fragment_and_secret_urls_are_visible_without_leaking_secret(self):
        data=self.parse(xml(["https://bingx.com/a#section", "https://bingx.com/?token=secret123"]))
        self.assertIn("sitemap_fragment", self.codes(data))
        self.assertIn("sitemap_sensitive_url", self.codes(data))
        self.assertNotIn("secret123", str(data))
