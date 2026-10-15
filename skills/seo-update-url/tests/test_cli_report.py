import csv
import json
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from support import InventoryTest, ROOT


class CliReportTests(InventoryTest):
    def test_report_counts_languages_and_source_exclusivity_without_inventing_index_intent(self):
        report = self.module("report")
        store = self.module("store").Inventory(self.data / "inventory.sqlite", ["bingx.com"])
        self.addCleanup(store.close)
        a, b, c = "https://bingx.com/en/price/btc", "https://bingx.com/zh-tc/price/eth", "https://bingx.com/unclassified-route"
        store.record_source([{"url": a}, {"url": b}], source_id="A", kind="export", captured_at="2026-09-16")
        store.record_source([{"url": b}, {"url": c}, {"url": "https://bingx.com/sitemap.xml"}], source_id="B", kind="export", captured_at="2026-09-16")
        output = self.base / "report"
        report.write_report(store, output)
        summary = json.loads((output / "summary.json").read_text())
        self.assertEqual(summary["language_prefix_count"], 2)
        self.assertEqual(summary["technical_url_count"], 1)
        self.assertEqual(summary["unverified_page_url_count"], 3)
        self.assertIsNone(summary["expected_indexable_canonical_url_count"])
        self.assertIsNone(summary["confirmed_retired_url_count"])
        with (output / "source-coverage.csv").open(encoding="utf-8-sig") as f:
            sources = {r["source_id"]: r for r in csv.DictReader(f)}
        self.assertEqual(int(sources["A"]["exclusive_discovered_url_count"]), 1)
        self.assertEqual(int(sources["B"]["exclusive_discovered_url_count"]), 2)
        with (output / "languages.csv").open(encoding="utf-8-sig") as f:
            languages = {r["locale"]: int(r["page_url_count"]) for r in csv.DictReader(f)}
        self.assertEqual(languages, {"en": 1, "zh-tc": 1, "": 1})

    def test_reclassify_updates_existing_assets_without_resetting_history_or_http(self):
        import sqlite3
        self.import_file([{"url": "https://bingx.com/zh-tc/price/btc"}])
        with closing(sqlite3.connect(self.data / "inventory.sqlite")) as db, db:
            db.execute("UPDATE urls SET locale='',template='/zh-tc/price/btc',classified=0,last_status=404,last_checked='2026-09-16T01:00:00Z'")
            before = db.execute("SELECT first_seen,last_seen,last_status,last_checked FROM urls").fetchone()
            changes = db.execute("SELECT COUNT(*) FROM changes").fetchone()[0]
        result = self.cli("reclassify")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["updated"], 1)
        with closing(sqlite3.connect(self.data / "inventory.sqlite")) as db, db:
            self.assertEqual(db.execute("SELECT first_seen,last_seen,last_status,last_checked FROM urls").fetchone(), before)
            self.assertEqual(db.execute("SELECT locale,template,classified FROM urls").fetchone(), ("zh-tc", "/{locale}/price/{asset}", 1))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM changes").fetchone()[0], changes)
        second = self.cli("reclassify")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["updated"], 0)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.data = self.base / "data with spaces"
        self.profile = self.base / "profile.json"
        self.profile.write_text(json.dumps({"site":"bingx.com","business_profile":"bingx","allowed_hosts": ["bingx.com"], "seeds": ["https://bingx.com/en"], "sitemaps": []}))

    def cli(self, *args):
        script = ROOT / "scripts" / "update_url.py"
        self.assertTrue(script.is_file(), "尚未实现可调用的CLI")
        return subprocess.run([sys.executable, str(script), *map(str, args), "--data", str(self.data), "--profile", str(self.profile)],
                              capture_output=True, text=True, timeout=20)

    def import_file(self, rows):
        path = self.base / "urls.json"
        path.write_text(json.dumps(rows))
        return self.cli("import", "--file", path, "--source-id", "history", "--kind", "historical", "--captured-at", "2026-09-16T00:00:00Z")

    def test_cli_import_report_and_repeat_are_real_and_idempotent(self):
        rows = [{"url": "https://bingx.com/en/price/btc"}, {"url": "https://bingx.com/ja/price/eth"}]
        first = self.import_file(rows)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.import_file(rows)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(first.stdout)["run_id"], json.loads(second.stdout)["run_id"])
        output = self.base / "report"
        result = self.cli("report", "--output", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((output / "summary.json").read_text())
        self.assertEqual(summary["url_count"], 2)
        self.assertIsNone(summary["whole_site_total"])
        self.assertEqual(summary["http_checked_count"], 0)
        with (output / "inventory.csv").open(encoding="utf-8-sig") as f:
            inventory = list(csv.DictReader(f))
        self.assertEqual({r["url"] for r in inventory}, {"https://bingx.com/en/price/btc", "https://bingx.com/ja/price/eth"})
        self.assertEqual(inventory[0]["last_checked"], "")
        self.assertTrue((output / "report.md").stat().st_size > 100)

    def test_bad_source_shape_returns_error_without_success_claim(self):
        result = self.import_file({"error": "please log in"})
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('"accepted"', result.stdout)

    def test_import_does_not_allow_secret_or_foreign_urls_into_inventory(self):
        result = self.import_file([{"url": "https://bingx.com/en"}, {"url": "https://bingx.com/?token=secret456"}, {"url": "https://elsewhere.test/"}])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["rejected"], 2)
        output = self.base / "report"
        self.cli("report", "--output", output)
        text = "\n".join(p.read_text(encoding="utf-8-sig") for p in output.iterdir() if p.is_file())
        self.assertNotIn("secret456", text)

    def test_browser_export_discovers_client_links_without_claiming_http_verification(self):
        path = self.base / "dom.json"
        path.write_text(json.dumps({"page_url": "https://bingx.com/en", "captured_at": "2026-09-16T02:00:00Z",
             "links": ["/en/xpool/detail?currency=84"], "canonicals": ["https://bingx.com/en"],
             "alternates": [{"url": "/ja", "hreflang": "ja"}]}))
        result = self.cli("import-dom", "--file", path, "--source-id", "browser:home")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.base / "report"
        self.cli("report", "--output", output)
        data = json.loads((output / "snapshot.json").read_text())
        urls = {x["url"] for x in data["urls"]}
        self.assertIn("https://bingx.com/en/xpool/detail?currency=84", urls)
        self.assertIn("https://bingx.com/ja", urls)
        self.assertEqual(data["summary"]["http_checked_count"], 0)
        self.assertTrue(any(r["relation"] == "canonical" for r in data["relations"]))

    def test_cli_zero_budget_creates_resumable_run_without_network(self):
        result = self.cli("discover", "--max-requests", "0")
        self.assertEqual(result.returncode, 2, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["requests"], 0)
        self.assertGreater(value["queued"], 0)
        status = self.cli("status")
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(json.loads(status.stdout)["latest_run"]["id"], value["run_id"])

    def test_export_protects_spreadsheet_formula_cells(self):
        mod = self.module("report")
        storemod = self.module("store")
        store = storemod.Inventory(self.data / "inventory.sqlite", ["bingx.com"])
        self.addCleanup(store.close)
        store.record_source([{"url": "https://bingx.com/en"}], source_id="=1+1", kind="export", captured_at="2026-09-16T00:00:00Z")
        out = self.base / "report"
        mod.write_report(store, out)
        with (out / "sources.csv").open(encoding="utf-8-sig") as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row["id"], "'=1+1")

    def test_second_writer_is_refused_while_inventory_is_locked(self):
        import fcntl
        self.data.mkdir()
        with (self.data / ".inventory.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.import_file([{"url": "https://bingx.com/en"}])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("inventory_locked", result.stderr)

    def test_data_directory_profile_is_used_without_repeating_cli_flag(self):
        self.data.mkdir()
        (self.data / "profile.json").write_text(json.dumps({"site":"support.bingx.com","allowed_hosts": ["support.bingx.com"], "seeds": [], "sitemaps": []}))
        path = self.base / "source.json"
        path.write_text('["https://support.bingx.com/"]')
        result = subprocess.run([sys.executable, str(ROOT / "scripts/update_url.py"), "import", "--data", str(self.data),
            "--file", str(path), "--source-id", "explicit-profile", "--kind", "export", "--captured-at", "2026-09-16"], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["accepted"], 1)

    def test_non_boolean_proxy_option_is_not_treated_as_permission(self):
        self.profile.write_text(json.dumps({"site":"bingx.com","business_profile":"bingx","allowed_hosts": ["bingx.com"], "allow_system_dns_alias": "false"}))
        result = self.cli("status")
        self.assertNotEqual(result.returncode, 0)
