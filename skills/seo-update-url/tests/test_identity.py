from support import InventoryTest


class IdentityTests(InventoryTest):
    def test_real_bingx_sitemap_locale_prefixes_are_classified(self):
        mod = self.module("identity")
        for locale in ["en", "zh-tc", "vi", "ru", "ja", "es", "id", "pt", "th", "ar", "fr", "uk"]:
            with self.subTest(locale=locale):
                value = mod.classify("https://bingx.com/" + locale + "/price/bitcoin")
                self.assertEqual(value["locale"], locale)
                self.assertEqual(value["template"], "/{locale}/price/{asset}")
                self.assertTrue(value["classified"])

    def test_normalizes_only_transport_identity(self):
        n = self.module("identity").normalize_url
        self.assertEqual(n("HTTPS://BINGX.COM:443/en/Price/BTC?currency=84#intro"),
                         "https://bingx.com/en/Price/BTC?currency=84")

    def test_business_parameters_remain_different_assets(self):
        n = self.module("identity").normalize_url
        values = ["https://bingx.com/en/xpool/detail?currency=84",
                  "https://bingx.com/en/xpool/detail?currency=78",
                  "https://bingx.com/en/xpool/detail"]
        self.assertEqual([n(v) for v in values], values)
        self.assertEqual(len({n(v) for v in values}), 3)

    def test_query_order_repetitions_and_tracking_are_not_silently_removed(self):
        n = self.module("identity").normalize_url
        url = "https://bingx.com/en/CopyTrading?type=spot&x=1&x=2&utm_source=test"
        self.assertEqual(n(url), url)

    def test_case_slash_and_encoded_separators_are_not_merged(self):
        n = self.module("identity").normalize_url
        values = ["https://bingx.com/en/leaderBoard", "https://bingx.com/en/leaderboard",
                  "https://bingx.com/en/leaderboard/", "https://bingx.com/en/a%2Fb"]
        self.assertEqual(len({n(v) for v in values}), 4)

    def test_hash_routes_are_distinct_from_document_anchors(self):
        n = self.module("identity").normalize_url
        self.assertEqual(n("https://bingx.com/#/market"), "https://bingx.com/#/market")
        self.assertEqual(n("https://bingx.com/#!/price/BTC"), "https://bingx.com/#!/price/BTC")
        self.assertEqual(n("https://bingx.com/en#faq"), "https://bingx.com/en")

    def test_relative_url_resolution(self):
        n = self.module("identity").normalize_url
        self.assertEqual(n("../price/btc", "https://bingx.com/en/market/"),
                         "https://bingx.com/en/price/btc")

    def test_rejects_non_http_credentials_invalid_ports_and_control_characters(self):
        n = self.module("identity").normalize_url
        for url in ["javascript:alert(1)", "mailto:a@b.com", "file:///tmp/x",
                    "https://user:pass@bingx.com/", "https://bingx.com:99999/",
                    "https://bingx.com/a\nb", "https://bingx.com/a b", "https://bingx.com\\@evil.com/"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                n(url)

    def test_exact_host_allowlist_does_not_include_deceptive_or_unapproved_hosts(self):
        scope = self.module("identity").in_scope
        self.assertTrue(scope("https://bingx.com/en", ["bingx.com"]))
        for url in ["https://bingx.com.evil.test/", "https://evilbingx.com/",
                    "https://account.bingx.com/", "https://bingx.com:8443/"]:
            self.assertFalse(scope(url, ["bingx.com"]), url)

    def test_sensitive_query_values_are_rejected_and_redacted(self):
        mod = self.module("identity")
        url = "https://bingx.com/en?access_token=secret123&currency=84"
        self.assertFalse(mod.in_scope(url, ["bingx.com"]))
        self.assertNotIn("secret123", mod.redact_url(url))
        self.assertIn("currency=84", mod.redact_url(url))

    def test_classifies_locale_template_and_entity_without_inventing_instances(self):
        c = self.module("identity").classify
        got = c("https://bingx.com/ja/how-to-buy/melon-2/brazil")
        self.assertEqual(got["locale"], "ja")
        self.assertEqual(got["template"], "/{locale}/how-to-buy/{asset}/{country}")
        self.assertEqual(got["entities"], {"asset": "melon-2", "country": "brazil"})

    def test_pagination_not_classified_as_asset_slug(self):
        c = self.module("identity").classify
        self.assertEqual(c("https://bingx.com/en/price/page/2116")["template"],
                         "/{locale}/price/page/{page}")
        self.assertEqual(c("https://bingx.com/en/price/bitcoin")["entities"], {"asset": "bitcoin"})

    def test_unknown_route_keeps_literal_and_flags_unclassified(self):
        got = self.module("identity").classify("https://bingx.com/en/new-service/custom-42")
        self.assertEqual(got["template"], "/{locale}/new-service/custom-42")
        self.assertFalse(got["classified"])

    def test_business_parameter_is_part_of_route_family(self):
        got = self.module("identity").classify("https://bingx.com/en/xpool/detail?currency=84")
        self.assertEqual(got["template"], "/{locale}/xpool/detail?currency={currency}")
        self.assertEqual(got["entities"], {"currency": "84"})
