"""Persistent, budgeted URL discovery. A finished crawl is not full-site proof."""

import hashlib
import http.client
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from .extract import RobotsPolicy, parse_html, parse_sitemap
from .identity import in_scope, normalize_url, redact_url
from .network import safe_headers, safe_header_pairs
from .store import now, packed


def origin(url):
    p = urlsplit(url)
    return p.scheme + "://" + p.netloc


class Discovery:
    def __init__(self, inventory, fetch, profile, evidence_dir):
        self.store = inventory
        self.db = inventory.db
        self.fetch = fetch
        self.profile = profile
        self.evidence_dir = Path(evidence_dir)

    def _status(self, task, status, reason=""):
        self.db.execute("UPDATE tasks SET status=?,reason=? WHERE id=?", (status, reason, task["id"]))
        self.db.commit()

    def _exclude(self, url, source, reason):
        self.db.execute("INSERT INTO exclusions(run_id,source_id,url,reason) VALUES(?,?,?,?)", (self.run_id, source, redact_url(url), reason))
        self.db.commit()

    def _observe(self, urls, source, kind, locator="", coverage="sample"):
        rows = []
        for item in urls:
            row = {"url": item} if isinstance(item, str) else item
            try:
                url = normalize_url(row["url"])
            except ValueError:
                self._exclude(row.get("url"), source, "invalid_url")
                continue
            if self.db.execute("SELECT COUNT(*) FROM urls").fetchone()[0] + len(rows) >= self.limits["max_urls"] and not self.store.get_url(url):
                self._exclude(url, source, "inventory_limit")
                continue
            rows.append(row)
        self.store.record_source(rows, source_id=source, kind=kind, captured_at=self.captured_at,
                                 locator=locator, coverage=coverage if len(rows) == len(urls) else "sample", run_id=self.run_id)

    def _enqueue(self, url, kind, depth=0, parent=""):
        try:
            url = normalize_url(url)
        except ValueError:
            self._exclude(url, parent, "invalid_url")
            return
        if not in_scope(url, self.profile["allowed_hosts"]):
            self._exclude(url, parent, "outside_scope_or_sensitive_url")
            return
        if self.db.execute("SELECT 1 FROM tasks WHERE run_id=? AND url=? AND kind=?", (self.run_id, url, kind)).fetchone():
            return
        state, reason = "queued", ""
        p = urlsplit(url)
        if kind == "page":
            if depth > self.limits["max_depth"]:
                state, reason = "deferred", "depth_limit"
            elif p.fragment:
                state, reason = "deferred", "hash_route_requires_browser"
            elif any(re.search(pattern, p.path) for pattern in self.profile.get("excluded_path_patterns", [])):
                state, reason = "deferred", "excluded_path"
            elif re.search(r"\.(?:png|jpe?g|gif|svg|webp|avif|mp4|pdf|zip|exe|dmg|apk|js|css|woff2?)$", p.path, re.I):
                state, reason = "deferred", "non_html_resource"
            elif p.query:
                siblings = [urlsplit(r[0]) for r in self.db.execute("SELECT url FROM tasks WHERE run_id=? AND kind='page' AND status!='deferred'", (self.run_id,))]
                count = sum(s.netloc == p.netloc and s.path == p.path and bool(s.query) for s in siblings)
                if count >= self.profile.get("query_variants_per_path", 2):
                    state, reason = "deferred", "query_variant_limit"
        if kind == "sitemap":
            count = self.db.execute("SELECT COUNT(*) FROM tasks WHERE run_id=? AND kind='sitemap' AND status!='deferred'", (self.run_id,)).fetchone()[0]
            if count >= self.limits["max_sitemaps"]:
                state, reason = "deferred", "sitemap_limit"
        if not self.store.get_url(url):
            state, reason = "deferred", "inventory_limit"
        self.db.execute("INSERT INTO tasks(run_id,url,kind,depth,parent,status,reason) VALUES(?,?,?,?,?,?,?)", (self.run_id, url, kind, depth, parent, state, reason))
        self.db.commit()
        if kind != "robots" and state == "queued":
            robot_url = origin(url) + "/robots.txt"
            if not self.db.execute("SELECT 1 FROM tasks WHERE run_id=? AND url=? AND kind='robots'", (self.run_id, robot_url)).fetchone():
                self._observe([robot_url], "robots-discovery:" + origin(url), "seed")
                self._enqueue(robot_url, "robots", 0, url)

    def _save_fetch(self, task):
        # Reserve the request before network I/O so interrupted attempts count.
        cur = self.db.execute("INSERT INTO fetches(run_id,url,error,checked_at) VALUES(?,?,?,?)", (self.run_id, task["url"], "incomplete_attempt", now()))
        self.db.commit()
        fetch_id = cur.lastrowid
        try:
            response = self.fetch(task["url"])
            directory = self.evidence_dir / self.run_id
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / (str(fetch_id) + ".body")
            path.write_bytes(response.body)
            evidence = {"path": str(path.resolve()), "sha256": hashlib.sha256(response.body).hexdigest(), "bytes": len(response.body)}
            pairs = None if response.headers_all is None else packed(safe_header_pairs(response.headers_all))
            captured = None if response.captured_header_names is None else packed(response.captured_header_names)
            self.db.execute("UPDATE fetches SET status=?,error=NULL,headers=?,evidence=?,headers_all=?,captured_header_names=? WHERE id=?",
                            (response.status, packed(safe_headers(response.headers)), packed(evidence), pairs, captured, fetch_id))
            self.db.commit()
            return response, evidence
        except (OSError, ValueError, http.client.HTTPException) as e:
            # Exception classes are enough; external exception text may contain secrets.
            self.db.execute("UPDATE fetches SET error=? WHERE id=?", (type(e).__name__, fetch_id))
            self.db.commit()
            self._status(task, "failed", "request_failed:" + type(e).__name__)
            return None, None

    def _robot_policy(self, task):
        record = self.db.execute("SELECT * FROM robots WHERE run_id=? AND origin=?", (self.run_id, origin(task["url"]))).fetchone()
        if not record:
            self._status(task, "blocked", "robots_unavailable")
            return False
        if record["status"] != "available":
            self._status(task, "blocked", "origin_rate_limited" if record["status"] == "rate_limited" else "robots_unknown_or_denied")
            return False
        policy = RobotsPolicy(record["body"])
        if not policy.allowed(task["url"]):
            self._status(task, "blocked", "robots_disallow")
            return False
        owner = getattr(self.fetch, "__self__", None)
        if owner and hasattr(owner, "set_delay"):
            owner.set_delay(origin(task["url"]), policy.delay)
        return True

    def _robots_owner(self, task):
        seen = set()
        while task["parent"] and task["url"] not in seen:
            seen.add(task["url"])
            previous = self.db.execute("SELECT * FROM tasks WHERE run_id=? AND url=? AND kind='robots'", (self.run_id, task["parent"])).fetchone()
            if not previous:
                break
            task = dict(previous)
        return origin(task["url"]), len(seen)

    def _process(self, task):
        if task["kind"] != "robots" and not self._robot_policy(task):
            return
        self._status(task, "running")
        response, evidence = self._save_fetch(task)
        if response is None:
            return
        body, headers = response.body, {k.lower(): v for k, v in response.headers.items()}
        details = {"evidence": evidence, "headers": safe_headers(headers), "body_mode": "original_http_no_javascript"}
        self.store.record_check(task["url"], self.run_id, response.status, details=details)
        if task["kind"] == "robots" and response.status in {301, 302, 303, 307, 308}:
            owner, hops = self._robots_owner(task)
            try:
                target = normalize_url(headers.get("location", ""), task["url"])
            except ValueError:
                target = ""
            existing = self.db.execute("SELECT * FROM tasks WHERE run_id=? AND url=? AND kind='robots'", (self.run_id, target)).fetchone()
            if hops >= 5 or not in_scope(target, self.profile["allowed_hosts"]) or existing:
                self._status(task, "blocked", "robots_redirect_limit_or_unverified_target")
                self._exclude(target, task["url"], "robots_redirect_unverified")
                return
            self._observe([target], "robots-redirect:" + task["url"], "redirect", task["url"])
            self.store.add_relation(self.run_id, task["url"], target, "redirect")
            self._enqueue(target, "robots", 0, task["url"])
            self._status(task, "done", "robots_redirect_observed")
            return
        if task["kind"] == "robots":
            text = body.decode("utf-8-sig", errors="replace")
            if response.status in {404, 410}:
                status, text = "available", ""
            elif response.status == 200 and not text.lstrip().lower().startswith(("<html", "<!doctype html")):
                status = "available"
            else:
                status = "unknown"
            owner, _ = self._robots_owner(task)
            self.db.execute("INSERT OR REPLACE INTO robots VALUES(?,?,?,?)", (self.run_id, owner, status, text))
            self.db.commit()
            if status == "available":
                for url in RobotsPolicy(text).sitemaps:
                    self._observe([url], "robots:" + task["url"], "sitemap", task["url"])
                    self._enqueue(url, "sitemap", 0, task["url"])
                self._status(task, "done")
            else:
                self._status(task, "failed", "robots_response_unknown")
            return
        if response.status in {301, 302, 303, 307, 308}:
            try:
                target = normalize_url(headers.get("location", ""), task["url"])
            except ValueError:
                self._status(task, "failed", "invalid_redirect_location")
                return
            self._observe([target], "redirect:" + task["url"], "redirect", task["url"])
            if not in_scope(target, self.profile["allowed_hosts"]):
                self._status(task, "blocked", "redirect_target_outside_scope")
                return
            self.store.add_relation(self.run_id, task["url"], target, "redirect")
            self._enqueue(target, task["kind"], task["depth"], task["url"])
            self._status(task, "done", "redirect_observed")
            return
        if response.status in {401, 403, 429}:
            if response.status == 429:
                self.db.execute("UPDATE robots SET status='rate_limited' WHERE run_id=? AND origin=?", (self.run_id, origin(task["url"])))
                self.db.commit()
            self._status(task, "blocked", "http_" + str(response.status))
            return
        if response.status != 200:
            self._status(task, "failed" if response.status >= 500 or task["kind"] == "sitemap" else "done", "http_" + str(response.status))
            return
        try:
            if task["kind"] == "sitemap":
                data = parse_sitemap(body)
                source = "sitemap:" + task["url"]
                self._observe(data["pages"], source, "sitemap", task["url"], coverage="complete")
                for item in data["pages"]:
                    self._enqueue(item["url"], "page", 0, task["url"])
                for child in data["children"]:
                    self._observe([child], "sitemap-index:" + task["url"], "sitemap", task["url"])
                    self.store.add_relation(self.run_id, task["url"], child, "sitemap_child")
                    self._enqueue(child, "sitemap", 0, task["url"])
                for item in data["alternates"]:
                    self._observe([item], "sitemap-alternate:" + task["url"], "sitemap", task["url"])
                    self.store.add_relation(self.run_id, item["from_url"], item["url"], "hreflang:" + item["hreflang"])
                    self._enqueue(item["url"], "page", 0, task["url"])
            elif "html" in headers.get("content-type", "").lower() or body.lstrip().startswith((b"<!DOCTYPE html", b"<!doctype html", b"<html")):
                data = parse_html(body.decode("utf-8", errors="replace"), task["url"])
                details.update({"title": data["title"], "noindex_observed": data["noindex"], "robots_directives": data["robots_directives"], "canonicals": [redact_url(u) for u in data["canonicals"]]})
                self.store.record_check(task["url"], self.run_id, response.status, details=details)
                for relation, urls in [("link", data["links"]), ("canonical", data["canonicals"])]:
                    self._observe(urls, "html:" + task["url"] + ":" + relation, "html", task["url"])
                    for url in urls:
                        self.store.add_relation(self.run_id, task["url"], url, relation)
                        self._enqueue(url, "page", task["depth"] + 1, task["url"])
                for alt in data["alternates"]:
                    self._observe([alt], "html-alternate:" + task["url"], "html", task["url"])
                    self.store.add_relation(self.run_id, task["url"], alt["url"], "hreflang:" + alt["hreflang"])
                    self._enqueue(alt["url"], "page", task["depth"] + 1, task["url"])
            self._status(task, "done")
        except ValueError as e:
            self._status(task, "failed", str(e))

    def run(self, max_requests=50, max_depth=1, max_sitemaps=25, max_urls=100000, resume=None):
        if min(max_requests, max_depth, max_sitemaps) < 0 or max_urls <= 0:
            raise ValueError("invalid_discovery_limits")
        self.limits = {"max_depth": max_depth, "max_sitemaps": max_sitemaps, "max_urls": max_urls}
        settings = {"profile": self.profile, **self.limits}
        if resume:
            row = self.db.execute("SELECT * FROM runs WHERE id=? AND kind='discover'", (resume,)).fetchone()
            if not row or json.loads(row["settings"]) != settings:
                raise ValueError("resume_requires_same_profile_and_scope")
            self.run_id, self.captured_at = resume, row["started_at"]
            self.db.execute("UPDATE tasks SET status='queued',reason='recovered_after_interruption' WHERE run_id=? AND status='running'", (resume,))
            self.db.execute("UPDATE runs SET status='running',finished_at=NULL WHERE id=?", (resume,))
            self.db.commit()
        else:
            self.run_id = self.store.begin_run("discover", settings)
            self.captured_at = self.db.execute("SELECT started_at FROM runs WHERE id=?", (self.run_id,)).fetchone()[0]
            for kind, field in [("page", "seeds"), ("sitemap", "sitemaps")]:
                for url in self.profile.get(field, []):
                    self._observe([url], "profile:" + field, "seed")
                    self._enqueue(url, kind)
        while self.db.execute("SELECT COUNT(*) FROM fetches WHERE run_id=?", (self.run_id,)).fetchone()[0] < max_requests:
            task = self.db.execute("SELECT * FROM tasks WHERE run_id=? AND status='queued' ORDER BY CASE kind WHEN 'robots' THEN 0 WHEN 'sitemap' THEN 1 ELSE 2 END,depth,id LIMIT 1", (self.run_id,)).fetchone()
            if not task:
                break
            self._process(dict(task))
        counts = {key: 0 for key in ("done", "failed", "blocked", "deferred", "queued", "running")}
        counts.update({r[0]: r[1] for r in self.db.execute("SELECT status,COUNT(*) FROM tasks WHERE run_id=? GROUP BY status", (self.run_id,))})
        status = "partial" if any(counts[k] for k in ("failed", "blocked", "deferred", "queued", "running")) else "completed"
        self.store.finish_run(self.run_id, status)
        requests = self.db.execute("SELECT COUNT(*) FROM fetches WHERE run_id=?", (self.run_id,)).fetchone()[0]
        return {"run_id": self.run_id, "status": status, "requests": requests, **counts,
                "coverage_claim": "bounded_discovery_not_full_site"}
