import tempfile
from pathlib import Path
from support import InventoryTest


class DiscoveryTests(InventoryTest):
    def setup_runner(self, pages, seeds=None, sitemap=None):
        mod = self.module("discover")
        storemod = self.module("store")
        net = self.module("network")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = storemod.Inventory(Path(tmp.name) / "i.sqlite", ["bingx.com"])
        self.addCleanup(store.close)
        calls = []

        def fetch(url):
            calls.append(url)
            value = pages.get(url, (404, {}, b""))
            if isinstance(value, BaseException):
                raise value
            return net.Response(url, value[0], value[1], value[2])

        profile = {"allowed_hosts": ["bingx.com"], "seeds": seeds or ["https://bingx.com/en"],
                   "sitemaps": sitemap or [], "excluded_path_patterns": [r"^/(?:en/)?(?:login|search)(?:/|$)"],
                   "query_variants_per_path": 2}
        runner = mod.Discovery(store, fetch, profile, Path(tmp.name) / "evidence")
        return runner, store, calls

    def test_recursive_sitemap_cycle_discovers_all_known_leaves_once(self):
        pages = {
            "https://bingx.com/robots.txt": (200, {}, b"User-agent: *\nSitemap: https://bingx.com/sitemap.xml"),
            "https://bingx.com/sitemap.xml": (200, {}, b'<sitemapindex><sitemap><loc>https://bingx.com/leaf.xml</loc></sitemap><sitemap><loc>https://bingx.com/sitemap.xml</loc></sitemap></sitemapindex>'),
            "https://bingx.com/leaf.xml": (200, {}, b'<urlset><url><loc>https://bingx.com/en/price/btc</loc></url></urlset>'),
            "https://bingx.com/en": (200, {"content-type": "text/html"}, b'<a href="/en/price/eth">ETH</a>'),
            "https://bingx.com/en/price/btc": (200, {"content-type": "text/html"}, b'<title>BTC</title>'),
            "https://bingx.com/en/price/eth": (200, {"content-type": "text/html"}, b'<title>ETH</title>')}
        runner, store, calls = self.setup_runner(pages)
        result = runner.run(max_requests=20, max_depth=1, max_sitemaps=10)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(calls.count("https://bingx.com/sitemap.xml"), 1)
        self.assertIsNotNone(store.get_url("https://bingx.com/en/price/btc"))
        self.assertIsNotNone(store.get_url("https://bingx.com/en/price/eth"))

    def test_budget_includes_robots_and_resume_uses_same_run(self):
        pages = {"https://bingx.com/robots.txt": (404, {}, b""),
                 "https://bingx.com/en": (200, {"content-type": "text/html"}, b'<a href="/en/about">A</a>'),
                 "https://bingx.com/en/about": (200, {"content-type": "text/html"}, b"ok")}
        runner, store, calls = self.setup_runner(pages)
        first = runner.run(max_requests=1)
        self.assertEqual(first["status"], "partial")
        self.assertEqual(len(calls), 1)
        second = runner.run(max_requests=10, resume=first["run_id"])
        self.assertEqual(second["run_id"], first["run_id"])
        self.assertEqual(second["status"], "completed")
        self.assertEqual(calls.count("https://bingx.com/robots.txt"), 1)

    def test_robots_disallow_prevents_page_request_but_keeps_asset(self):
        runner, store, calls = self.setup_runner({"https://bingx.com/robots.txt": (200, {}, b"User-agent: *\nDisallow: /en")})
        result = runner.run(max_requests=10)
        self.assertNotIn("https://bingx.com/en", calls)
        self.assertIsNotNone(store.get_url("https://bingx.com/en"))
        self.assertGreater(result["blocked"], 0)

    def test_robots_503_is_unknown_not_allow_all(self):
        runner, _, calls = self.setup_runner({"https://bingx.com/robots.txt": (503, {}, b"unavailable")})
        result = runner.run(max_requests=10)
        self.assertNotIn("https://bingx.com/en", calls)
        self.assertEqual(result["status"], "partial")

    def test_external_redirect_target_not_requested_or_added_as_site_asset(self):
        runner, store, calls = self.setup_runner({"https://bingx.com/robots.txt": (404, {}, b""),
            "https://bingx.com/en": (302, {"location": "https://evil.test/a"}, b"")})
        runner.run(max_requests=10)
        self.assertNotIn("https://evil.test/a", calls)
        self.assertIsNone(store.get_url("https://evil.test/a"))
        self.assertTrue(store.exclusions())

    def test_internal_redirect_target_becomes_separate_asset_and_edge(self):
        runner, store, calls = self.setup_runner({"https://bingx.com/robots.txt": (404, {}, b""),
            "https://bingx.com/en": (301, {"location": "/en/new"}, b""),
            "https://bingx.com/en/new": (200, {"content-type": "text/html"}, b"ok")})
        runner.run(max_requests=10)
        self.assertEqual(store.get_url("https://bingx.com/en")["last_status"], 301)
        self.assertEqual(store.get_url("https://bingx.com/en/new")["last_status"], 200)
        self.assertEqual(store.db.execute("SELECT relation FROM relations WHERE source_url='https://bingx.com/en'").fetchone()[0], "redirect")

    def test_canonical_is_a_relation_not_replacement_of_original_url(self):
        runner, store, _ = self.setup_runner({"https://bingx.com/robots.txt": (404, {}, b""),
            "https://bingx.com/en": (200, {"content-type": "text/html"}, b'<link rel="canonical" href="/en/detail?currency=84">')})
        runner.run(max_requests=10)
        self.assertIsNotNone(store.get_url("https://bingx.com/en"))
        self.assertIsNotNone(store.get_url("https://bingx.com/en/detail?currency=84"))

    def test_depth_limits_fetching_not_discovery(self):
        runner, store, calls = self.setup_runner({"https://bingx.com/robots.txt": (404, {}, b""),
            "https://bingx.com/en": (200, {"content-type": "text/html"}, b'<a href="/en/deep">D</a>')})
        result = runner.run(max_requests=10, max_depth=0)
        self.assertIsNotNone(store.get_url("https://bingx.com/en/deep"))
        self.assertNotIn("https://bingx.com/en/deep", calls)
        self.assertGreater(result["deferred"], 0)

    def test_parameter_explosion_keeps_inventory_but_bounds_requests(self):
        links = b''.join(f'<a href="/en/list?sort={i}">s</a>'.encode() for i in range(7))
        runner, store, calls = self.setup_runner({"https://bingx.com/robots.txt": (404, {}, b""),
            "https://bingx.com/en": (200, {"content-type": "text/html"}, links)})
        runner.run(max_requests=30)
        self.assertEqual(len([u for u in calls if "sort=" in u]), 2)
        self.assertEqual(store.db.execute("SELECT COUNT(*) FROM urls WHERE url LIKE '%sort=%'").fetchone()[0], 7)

    def test_private_routes_are_inventoried_without_fetching(self):
        runner, store, calls = self.setup_runner({"https://bingx.com/robots.txt": (404, {}, b""),
            "https://bingx.com/en": (200, {"content-type": "text/html"}, b'<a href="/en/login">Login</a>')})
        runner.run(max_requests=10)
        self.assertIsNotNone(store.get_url("https://bingx.com/en/login"))
        self.assertNotIn("https://bingx.com/en/login", calls)

    def test_http_failure_retains_evidence_and_does_not_abort_other_seeds(self):
        runner, store, calls = self.setup_runner({"https://bingx.com/robots.txt": (404, {}, b""),
            "https://bingx.com/en": OSError("connection reset"),
            "https://bingx.com/ja": (200, {"content-type": "text/html"}, b"ok")},
            seeds=["https://bingx.com/en", "https://bingx.com/ja"])
        result = runner.run(max_requests=10)
        self.assertIn("https://bingx.com/ja", calls)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(store.get_url("https://bingx.com/ja")["last_status"], 200)

    def test_invalid_sitemap_is_reported_not_silent_empty_success(self):
        runner, _, _ = self.setup_runner({"https://bingx.com/robots.txt": (404, {}, b""),
            "https://bingx.com/sitemap.xml": (200, {"content-type": "text/html"}, b"<html>blocked</html>")},
            sitemap=["https://bingx.com/sitemap.xml"])
        result = runner.run(max_requests=10)
        self.assertGreater(result["failed"], 0)

    def test_zero_budget_makes_no_requests_and_preserves_queue(self):
        runner, _, calls = self.setup_runner({})
        result = runner.run(max_requests=0)
        self.assertEqual(calls, [])
        self.assertGreater(result["queued"], 0)

    def test_resume_rejects_changed_scope(self):
        runner, _, _ = self.setup_runner({})
        first = runner.run(max_requests=0, max_depth=1)
        with self.assertRaises(ValueError):
            runner.run(max_requests=10, max_depth=3, resume=first["run_id"])

    def test_rate_limit_stops_remaining_requests_to_same_origin(self):
        runner, _, calls = self.setup_runner({"https://bingx.com/robots.txt": (404, {}, b""),
            "https://bingx.com/en": (429, {"retry-after": "3600"}, b"slow down"),
            "https://bingx.com/ja": (200, {"content-type": "text/html"}, b"ok")},
            seeds=["https://bingx.com/en", "https://bingx.com/ja"])
        result = runner.run(max_requests=10)
        self.assertNotIn("https://bingx.com/ja", calls)
        self.assertGreater(result["blocked"], 0)

    def test_inventory_capacity_rejects_new_urls_without_scheduling_them(self):
        runner, store, calls = self.setup_runner({"https://bingx.com/robots.txt": (404, {}, b""),
            "https://bingx.com/en": (200, {"content-type": "text/html"}, b'<a href="/en/a">a</a><a href="/en/b">b</a>')})
        result = runner.run(max_requests=20, max_urls=3)
        self.assertEqual(store.summary()["url_count"], 3)
        self.assertNotIn("https://bingx.com/en/b", calls)
        self.assertEqual(result["status"], "partial")

    def test_safe_robots_redirect_is_followed_within_budget(self):
        runner, _, calls = self.setup_runner({"https://bingx.com/robots.txt": (301, {"location": "/robots-v2.txt"}, b""),
            "https://bingx.com/robots-v2.txt": (200, {"content-type": "text/plain"}, b"User-agent: *\nAllow: /"),
            "https://bingx.com/en": (200, {"content-type": "text/html"}, b"ok")})
        result = runner.run(max_requests=10)
        self.assertIn("https://bingx.com/en", calls)
        self.assertEqual(result["requests"], 3)

    def test_cross_scope_redirect_is_marked_as_unverified_target(self):
        runner, _, _ = self.setup_runner({"https://bingx.com/robots.txt": (404, {}, b""),
            "https://bingx.com/en": (302, {"location": "https://evil.test/a"}, b"")})
        result = runner.run(max_requests=10)
        self.assertEqual(result["status"], "partial")

    def test_malformed_http_response_does_not_abort_other_seeds(self):
        from http.client import BadStatusLine
        runner, store, calls = self.setup_runner({"https://bingx.com/robots.txt": (404, {}, b""),
            "https://bingx.com/en": BadStatusLine("bad server response"),
            "https://bingx.com/ja": (200, {"content-type": "text/html"}, b"ok")},
            seeds=["https://bingx.com/en", "https://bingx.com/ja"])
        result = runner.run(max_requests=10)
        self.assertIn("https://bingx.com/ja", calls)
        self.assertEqual(result["status"], "partial")

    def test_keyboard_interrupt_resumes_running_task_and_counts_attempt(self):
        pages = {"https://bingx.com/robots.txt": KeyboardInterrupt(),
                 "https://bingx.com/en": (200, {"content-type": "text/html"}, b"ok")}
        runner, store, calls = self.setup_runner(pages)
        with self.assertRaises(KeyboardInterrupt):
            runner.run(max_requests=10)
        run_id = store.db.execute("SELECT id FROM runs WHERE kind='discover'").fetchone()[0]
        pages["https://bingx.com/robots.txt"] = (404, {}, b"")
        result = runner.run(max_requests=10, resume=run_id)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["requests"], 3)
        self.assertEqual(calls.count("https://bingx.com/robots.txt"), 2)
