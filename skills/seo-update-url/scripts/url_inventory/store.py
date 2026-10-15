"""Transactional, source-aware inventory. Absence is never deletion."""

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .identity import classify, in_scope, normalize_url, redact_url


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def timestamp(value):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as e:
        raise ValueError("captured_at_requires_ISO8601_with_timezone") from e
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value  # Preserve day precision of historical evidence.
    if dt.tzinfo is None:
        raise ValueError("captured_at_requires_timezone")
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Inventory:
    def __init__(self, path, allowed_hosts):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.allowed_hosts = allowed_hosts
        self.db = sqlite3.connect(self.path, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,kind TEXT,started_at TEXT,finished_at TEXT,status TEXT,settings TEXT);
        CREATE TABLE IF NOT EXISTS urls(
          url TEXT PRIMARY KEY,first_seen TEXT,last_seen TEXT,host TEXT,locale TEXT,
          template TEXT,entities TEXT,classified INTEGER,kind TEXT,index_intent TEXT DEFAULT 'unknown',
          last_status INTEGER,last_checked TEXT,last_details TEXT);
        CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,kind TEXT,locator TEXT,last_captured_at TEXT);
        CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY,source_id TEXT,run_id TEXT,captured_at TEXT,
          coverage TEXT,accepted INTEGER,rejected INTEGER,ingested_at TEXT);
        CREATE TABLE IF NOT EXISTS source_urls(source_id TEXT,url TEXT,first_seen TEXT,last_seen TEXT,state TEXT,
          PRIMARY KEY(source_id,url));
        CREATE TABLE IF NOT EXISTS appearances(snapshot_id TEXT,url TEXT,raw_url TEXT,metadata TEXT,
          PRIMARY KEY(snapshot_id,url,raw_url));
        CREATE TABLE IF NOT EXISTS exclusions(id INTEGER PRIMARY KEY,run_id TEXT,source_id TEXT,url TEXT,reason TEXT);
        CREATE TABLE IF NOT EXISTS changes(id INTEGER PRIMARY KEY,run_id TEXT,url TEXT,source_id TEXT,change TEXT,
          before_value TEXT,after_value TEXT,changed_at TEXT);
        CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY,url TEXT,run_id TEXT,checked_at TEXT,
          status INTEGER,details TEXT);
        CREATE TABLE IF NOT EXISTS relations(run_id TEXT,source_url TEXT,target_url TEXT,relation TEXT,
          UNIQUE(run_id,source_url,target_url,relation));
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,run_id TEXT,url TEXT,kind TEXT,depth INTEGER,
          parent TEXT,status TEXT DEFAULT 'queued',reason TEXT,UNIQUE(run_id,url,kind));
        CREATE TABLE IF NOT EXISTS fetches(id INTEGER PRIMARY KEY,run_id TEXT,url TEXT,status INTEGER,
          error TEXT,headers TEXT,evidence TEXT,checked_at TEXT);
        CREATE TABLE IF NOT EXISTS robots(run_id TEXT,origin TEXT,status TEXT,body TEXT,PRIMARY KEY(run_id,origin));
        CREATE INDEX IF NOT EXISTS source_urls_by_url ON source_urls(url);
        CREATE INDEX IF NOT EXISTS tasks_by_run_status ON tasks(run_id,status,kind);
        CREATE INDEX IF NOT EXISTS fetches_by_run ON fetches(run_id);
        """)
        existing = self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if existing and existing[0] != "1":
            self.close()
            raise ValueError("unsupported_database_version")
        self.db.execute("INSERT OR IGNORE INTO meta VALUES('schema_version','1')")
        if 'headers_all' not in {row[1] for row in self.db.execute('PRAGMA table_info(fetches)')}:
            self.db.execute('ALTER TABLE fetches ADD COLUMN headers_all TEXT')
        if 'captured_header_names' not in {row[1] for row in self.db.execute('PRAGMA table_info(fetches)')}:
            self.db.execute('ALTER TABLE fetches ADD COLUMN captured_header_names TEXT')
        self.db.commit()

    def close(self):
        self.db.close()

    def begin_run(self, kind, settings=None, run_id=None):
        run_id = run_id or kind + "-" + uuid.uuid4().hex[:16]
        self.db.execute("INSERT OR IGNORE INTO runs VALUES(?,?,?,?,?,?)",
                        (run_id, kind, now(), None, "running", packed(settings or {})))
        self.db.commit()
        return run_id

    def finish_run(self, run_id, status):
        self.db.execute("UPDATE runs SET status=?,finished_at=? WHERE id=?", (status, now(), run_id))
        self.db.commit()

    def _change(self, run_id, url, source_id, change, before=None, after=None, at=None):
        self.db.execute("INSERT INTO changes(run_id,url,source_id,change,before_value,after_value,changed_at) VALUES(?,?,?,?,?,?,?)",
                        (run_id, url, source_id, change, before, after, at or now()))

    def record_source(self, records, *, source_id, kind, captured_at, coverage="sample", locator="", run_id=None):
        captured_at = timestamp(captured_at)
        if coverage not in {"sample", "complete", "unknown"} or not source_id.strip():
            raise ValueError("invalid_source_metadata")
        if kind not in {"historical", "gsc", "bing", "yandex", "cms", "routes", "logs", "export", "sitemap", "html", "browser", "seed", "redirect"}:
            raise ValueError("invalid_source_kind")
        valid, invalid = [], []
        for row in records:
            raw = row.get("url") if isinstance(row, dict) else None
            try:
                url = normalize_url(raw)
                if not in_scope(url, self.allowed_hosts):
                    raise ValueError("outside_scope_or_sensitive_url")
                valid.append((url, raw, {k: row[k] for k in ("id", "page_type", "family", "group", "lastmod", "source_ids", "coverage_note", "route_family") if k in row}))
            except ValueError as e:
                invalid.append((redact_url(raw), str(e)))
        digest_input = [source_id, kind, captured_at, coverage, locator, valid, invalid]
        digest = hashlib.sha256(packed(digest_input).encode()).hexdigest()
        existing = self.db.execute("SELECT * FROM snapshots WHERE id=?", (digest,)).fetchone()
        if existing:
            return {"run_id": existing["run_id"], "accepted": existing["accepted"], "rejected": existing["rejected"], "idempotent": True}
        own_run = run_id is None
        run_id = run_id or "import-" + digest[:20]
        effective_coverage = "sample" if invalid else coverage
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO runs VALUES(?,?,?,?,?,?)", (run_id, "import", now(), None, "running", "{}"))
            previous = self.db.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
            newest = not previous or captured_at >= previous["last_captured_at"]
            self.db.execute("INSERT OR IGNORE INTO sources VALUES(?,?,?,?)", (source_id, kind, redact_url(locator) if locator.startswith("http") else locator, captured_at))
            if newest:
                self.db.execute("UPDATE sources SET kind=?,locator=?,last_captured_at=? WHERE id=?", (kind, redact_url(locator) if locator.startswith("http") else locator, captured_at, source_id))
            self.db.execute("INSERT INTO snapshots VALUES(?,?,?,?,?,?,?,?)",
                            (digest, source_id, run_id, captured_at, effective_coverage, len(valid), len(invalid), now()))
            present = {u for u, _, _ in valid}
            for url, raw, metadata in valid:
                old = self.db.execute("SELECT * FROM urls WHERE url=?", (url,)).fetchone()
                if not old:
                    c = classify(url)
                    self.db.execute("INSERT INTO urls(url,first_seen,last_seen,host,locale,template,entities,classified,kind) VALUES(?,?,?,?,?,?,?,?,?)",
                                    (url, captured_at, captured_at, c["host"], c["locale"], c["template"], packed(c["entities"]), c["classified"], c["kind"]))
                    self._change(run_id, url, source_id, "new_url", after=url, at=captured_at)
                else:
                    self.db.execute("UPDATE urls SET first_seen=MIN(first_seen,?),last_seen=MAX(last_seen,?) WHERE url=?", (captured_at, captured_at, url))
                membership = self.db.execute("SELECT * FROM source_urls WHERE source_id=? AND url=?", (source_id, url)).fetchone()
                if not membership:
                    later_complete = (not newest and self.db.execute("SELECT 1 FROM snapshots WHERE source_id=? AND coverage='complete' AND captured_at>? LIMIT 1", (source_id, captured_at)).fetchone())
                    state = "missing_candidate" if later_complete else "observed"
                    self.db.execute("INSERT INTO source_urls VALUES(?,?,?,?,?)", (source_id, url, captured_at, captured_at, state))
                else:
                    if newest and membership["state"] == "missing_candidate":
                        self._change(run_id, url, source_id, "reappeared_in_source", "missing_candidate", "observed", captured_at)
                    self.db.execute("UPDATE source_urls SET first_seen=MIN(first_seen,?),last_seen=MAX(last_seen,?),state=? WHERE source_id=? AND url=?",
                                    (captured_at, captured_at, "observed" if newest else membership["state"], source_id, url))
                self.db.execute("INSERT OR IGNORE INTO appearances VALUES(?,?,?,?)", (digest, url, raw, packed(metadata)))
            if newest and effective_coverage == "complete":
                for row in self.db.execute("SELECT * FROM source_urls WHERE source_id=? AND state='observed'", (source_id,)).fetchall():
                    if row["url"] not in present:
                        self.db.execute("UPDATE source_urls SET state='missing_candidate' WHERE source_id=? AND url=?", (source_id, row["url"]))
                        self._change(run_id, row["url"], source_id, "missing_from_source", "observed", "missing_candidate", captured_at)
            self.db.executemany("INSERT INTO exclusions(run_id,source_id,url,reason) VALUES(?,?,?,?)", [(run_id, source_id, u, reason) for u, reason in invalid])
            if own_run:
                self.db.execute("UPDATE runs SET status=?,finished_at=? WHERE id=?", ("partial" if invalid else "completed", now(), run_id))
        return {"run_id": run_id, "accepted": len(valid), "rejected": len(invalid), "idempotent": False}

    def record_check(self, url, run_id, status, checked_at=None, details=None):
        url = normalize_url(url)
        at = timestamp(checked_at or now())
        if not self.db.execute("SELECT 1 FROM urls WHERE url=?", (url,)).fetchone():
            raise ValueError("url_must_be_discovered_before_check")
        details = details or {}
        with self.db:
            old = self.db.execute("SELECT * FROM urls WHERE url=?", (url,)).fetchone()
            self.db.execute("INSERT INTO checks(url,run_id,checked_at,status,details) VALUES(?,?,?,?,?)", (url, run_id, at, status, packed(details)))
            if not old["last_checked"] or at >= old["last_checked"]:
                if old["last_status"] is not None and old["last_status"] != status:
                    self._change(run_id, url, "http", "http_status_changed", str(old["last_status"]), str(status), at)
                self.db.execute("UPDATE urls SET last_status=?,last_checked=?,last_details=? WHERE url=?", (status, at, packed(details), url))

    def add_relation(self, run_id, source, target, relation):
        if not in_scope(source, self.allowed_hosts) or not in_scope(target, self.allowed_hosts):
            return
        self.db.execute("INSERT OR IGNORE INTO relations VALUES(?,?,?,?)", (run_id, normalize_url(source), normalize_url(target), relation))
        self.db.commit()

    def get_url(self, url):
        row = self.db.execute("SELECT * FROM urls WHERE url=?", (normalize_url(url),)).fetchone()
        if not row:
            return None
        value = dict(row)
        value["entities"] = json.loads(value["entities"])
        value["last_details"] = json.loads(value["last_details"]) if value["last_details"] else None
        value["source_memberships"] = [dict(r) for r in self.db.execute("SELECT * FROM source_urls WHERE url=? ORDER BY source_id", (row["url"],))]
        value["sources"] = [r["source_id"] for r in value["source_memberships"]]
        return value

    def changes(self, run_id=None):
        if run_id:
            return [dict(r) for r in self.db.execute("SELECT * FROM changes WHERE run_id=? ORDER BY id", (run_id,))]
        return [dict(r) for r in self.db.execute("SELECT * FROM changes ORDER BY id")]

    def reclassify(self):
        """Refresh derived route fields without changing observed evidence."""
        fields = ("host", "locale", "template", "entities", "classified", "kind")
        scanned, updated = 0, 0
        with self.db:
            for row in self.db.execute("SELECT * FROM urls").fetchall():
                scanned += 1
                value = classify(row["url"])
                value["entities"] = packed(value["entities"])
                if any(row[key] != value[key] for key in fields):
                    self.db.execute("UPDATE urls SET host=?,locale=?,template=?,entities=?,classified=?,kind=? WHERE url=?",
                                    (*[value[key] for key in fields], row["url"]))
                    updated += 1
        return {"scanned": scanned, "updated": updated, "scope": "derived_classification_only"}

    def exclusions(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM exclusions ORDER BY id")]

    def summary(self):
        count = lambda sql: self.db.execute(sql).fetchone()[0]
        return {"url_count": count("SELECT COUNT(*) FROM urls"),
                "page_url_count": count("SELECT COUNT(*) FROM urls WHERE kind='page'"),
                "technical_url_count": count("SELECT COUNT(*) FROM urls WHERE kind='technical'"),
                "language_prefix_count": count("SELECT COUNT(DISTINCT locale) FROM urls WHERE kind='page' AND locale!=''"),
                "classified_route_family_count": count("SELECT COUNT(*) FROM (SELECT DISTINCT host,template FROM urls WHERE kind='page' AND classified=1)"),
                "unverified_page_url_count": count("SELECT COUNT(*) FROM urls WHERE kind='page' AND last_checked IS NULL"),
                "expected_indexable_canonical_url_count": None,
                "confirmed_retired_url_count": None,
                "route_family_count": count("SELECT COUNT(*) FROM (SELECT DISTINCT host,template FROM urls WHERE kind='page')"),
                "unclassified_url_count": count("SELECT COUNT(*) FROM urls WHERE classified=0 AND kind='page'"),
                "source_snapshot_count": count("SELECT COUNT(*) FROM snapshots"),
                "http_checked_count": count("SELECT COUNT(*) FROM urls WHERE last_checked IS NOT NULL"),
                "http_200_count": count("SELECT COUNT(*) FROM urls WHERE last_status=200"),
                "source_count": count("SELECT COUNT(*) FROM sources"),
                "whole_site_total": None, "coverage_claim": "discovered_inventory_only",
                "generated_at": now()}
