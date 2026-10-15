import tempfile
from pathlib import Path
from support import InventoryTest


class StoreTests(InventoryTest):
    def make_store(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        s = self.module("store").Inventory(Path(tmp.name) / "inventory.sqlite", ["bingx.com"])
        self.addCleanup(s.close)
        return s

    def ingest(self, s, urls, source="sitemap", date="2026-09-16T00:00:00Z", coverage="sample"):
        return s.record_source([{"url": u} for u in urls], source_id=source, kind="export",
                               captured_at=date, coverage=coverage)

    def test_distinct_business_urls_persist_and_canonical_does_not_merge_them(self):
        s = self.make_store()
        self.ingest(s, ["https://bingx.com/en/detail?currency=84", "https://bingx.com/en/detail?currency=78"])
        s.record_check("https://bingx.com/en/detail?currency=84", "check-1", 200,
                       details={"canonicals": ["https://bingx.com/en/detail"]})
        self.assertEqual(s.summary()["url_count"], 2)
        self.assertEqual(s.get_url("https://bingx.com/en/detail?currency=84")["last_status"], 200)

    def test_duplicate_source_import_is_idempotent(self):
        s = self.make_store()
        a = self.ingest(s, ["https://bingx.com/en"])
        b = self.ingest(s, ["https://bingx.com/en"])
        self.assertEqual(a["run_id"], b["run_id"])
        self.assertEqual(s.summary()["url_count"], 1)
        self.assertEqual(s.summary()["source_snapshot_count"], 1)

    def test_multiple_sources_share_url_but_keep_provenance(self):
        s = self.make_store()
        self.ingest(s, ["https://bingx.com/en"], source="gsc")
        self.ingest(s, ["https://bingx.com/en"], source="nav")
        row = s.get_url("https://bingx.com/en")
        self.assertEqual(set(row["sources"]), {"gsc", "nav"})
        self.assertEqual(s.summary()["url_count"], 1)

    def test_import_does_not_claim_current_http_or_index_status(self):
        s = self.make_store()
        self.ingest(s, ["https://bingx.com/en"], date="2026-01-01T00:00:00Z")
        row = s.get_url("https://bingx.com/en")
        self.assertIsNone(row["last_status"])
        self.assertIsNone(row["last_checked"])
        self.assertEqual(row["first_seen"], "2026-01-01T00:00:00Z")
        self.assertEqual(row["index_intent"], "unknown")

    def test_full_source_absence_is_candidate_not_deleted_url(self):
        s = self.make_store()
        self.ingest(s, ["https://bingx.com/en", "https://bingx.com/ja"], coverage="complete")
        result = self.ingest(s, ["https://bingx.com/en"], date="2026-09-23T00:00:00Z", coverage="complete")
        self.assertEqual(s.summary()["url_count"], 2)
        self.assertEqual(s.get_url("https://bingx.com/ja")["source_memberships"][0]["state"], "missing_candidate")
        self.assertIn("missing_from_source", {x["change"] for x in s.changes(result["run_id"])})

    def test_sample_absence_never_marks_missing(self):
        s = self.make_store()
        self.ingest(s, ["https://bingx.com/en", "https://bingx.com/ja"], coverage="complete")
        self.ingest(s, ["https://bingx.com/en"], date="2026-09-23T00:00:00Z", coverage="sample")
        self.assertEqual(s.get_url("https://bingx.com/ja")["source_memberships"][0]["state"], "observed")

    def test_older_complete_import_cannot_override_newer_source_membership(self):
        s = self.make_store()
        self.ingest(s, ["https://bingx.com/en", "https://bingx.com/ja"], date="2026-09-23T00:00:00Z", coverage="complete")
        self.ingest(s, ["https://bingx.com/en"], date="2026-09-16T00:00:00Z", coverage="complete")
        self.assertEqual(s.get_url("https://bingx.com/ja")["source_memberships"][0]["state"], "observed")
        self.assertEqual(s.get_url("https://bingx.com/en")["last_seen"], "2026-09-23T00:00:00Z")

    def test_returning_url_keeps_first_seen_and_records_reappearance(self):
        s = self.make_store()
        self.ingest(s, ["https://bingx.com/ja"], coverage="complete")
        self.ingest(s, [], date="2026-09-23T00:00:00Z", coverage="complete")
        result = self.ingest(s, ["https://bingx.com/ja"], date="2026-09-30T00:00:00Z", coverage="complete")
        self.assertEqual(s.get_url("https://bingx.com/ja")["first_seen"], "2026-09-16T00:00:00Z")
        self.assertIn("reappeared_in_source", {x["change"] for x in s.changes(result["run_id"])})

    def test_rejected_rows_are_visible_and_cannot_clear_full_source(self):
        s = self.make_store()
        self.ingest(s, ["https://bingx.com/en"], coverage="complete")
        r = self.ingest(s, ["javascript:bad", "https://evil.test/", "https://bingx.com/?token=hidden-secret"],
                        date="2026-09-23T00:00:00Z", coverage="complete")
        self.assertEqual(r["rejected"], 3)
        self.assertEqual(s.get_url("https://bingx.com/en")["source_memberships"][0]["state"], "observed")
        self.assertNotIn("hidden-secret", str(s.exclusions()))

    def test_route_counts_are_templates_not_instance_counts(self):
        s = self.make_store()
        self.ingest(s, ["https://bingx.com/en/price/btc", "https://bingx.com/ja/price/eth", "https://bingx.com/en/about"])
        self.assertEqual(s.summary()["url_count"], 3)
        self.assertEqual(s.summary()["route_family_count"], 2)
        self.assertIsNone(s.summary()["whole_site_total"])

    def test_database_reopen_retains_inventory(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cls = self.module("store").Inventory
        p = Path(tmp.name) / "i.sqlite"
        s = cls(p, ["bingx.com"])
        self.ingest(s, ["https://bingx.com/en"])
        s.close()
        s = cls(p, ["bingx.com"])
        self.addCleanup(s.close)
        self.assertEqual(s.summary()["url_count"], 1)

    def test_invalid_timestamp_leaves_database_unchanged(self):
        s = self.make_store()
        with self.assertRaises(ValueError):
            self.ingest(s, ["https://bingx.com/en"], date="yesterday")
        self.assertEqual(s.summary()["url_count"], 0)

    def test_same_url_new_response_generates_status_change_without_new_asset(self):
        s = self.make_store()
        self.ingest(s, ["https://bingx.com/en"])
        s.record_check("https://bingx.com/en", "run-1", 200, checked_at="2026-09-16T00:00:00Z")
        s.record_check("https://bingx.com/en", "run-2", 404, checked_at="2026-09-23T00:00:00Z")
        self.assertEqual(s.summary()["url_count"], 1)
        self.assertEqual(s.get_url("https://bingx.com/en")["last_status"], 404)
        self.assertIn("http_status_changed", {x["change"] for x in s.changes("run-2")})

    def test_date_only_historical_source_does_not_invent_capture_time(self):
        s = self.make_store()
        self.ingest(s, ["https://bingx.com/en"], date="2026-09-16")
        self.assertEqual(s.get_url("https://bingx.com/en")["first_seen"], "2026-09-16")

    def test_older_newly_imported_url_is_not_present_in_newer_complete_snapshot(self):
        s = self.make_store()
        self.ingest(s, ["https://bingx.com/en"], date="2026-09-23T00:00:00Z", coverage="complete")
        self.ingest(s, ["https://bingx.com/ja"], date="2026-09-16T00:00:00Z", coverage="complete")
        self.assertEqual(s.get_url("https://bingx.com/ja")["source_memberships"][0]["state"], "missing_candidate")
