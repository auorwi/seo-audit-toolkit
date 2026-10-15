#!/usr/bin/env python3
"""Standalone 001 updateURL. Exit: 0 complete, 2 partial, 1 error."""

import argparse
import os
import json
import sys
from contextlib import contextmanager
from pathlib import Path

from url_inventory.discover import Discovery
from url_inventory.extract import parse_import
from url_inventory.identity import normalize_url
from url_inventory.network import HttpClient
from url_inventory.report import latest_run, write_report
from url_inventory.store import Inventory

DEFAULT_PROFILE = None


@contextmanager
def inventory_lock(directory):
    import fcntl
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".inventory.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise ValueError("inventory_locked: another process is using this inventory") from e
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def load_profile(path):
    if path is None:raise ValueError('SEO_SITE_PROFILE_or_explicit_profile_required')
    os.environ['SEO_SITE_PROFILE']=str(path)
    shared=Path(__file__).resolve().parents[2]/'seo-crawlability/scripts'
    if str(shared) not in sys.path:sys.path.insert(0,str(shared))
    from crawlability.site import get_profile
    return get_profile()


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("import", "import-dom", "discover", "reclassify", "report", "status"):
        command = commands.add_parser(name)
        command.add_argument("--data", type=Path, required=True, help="Persistent data directory outside installed skill")
        command.add_argument("--profile", type=Path, help="Explicit profile, or SEO_SITE_PROFILE, or existing DATA/profile.json")
        if name in {"import", "import-dom"}:
            command.add_argument("--file", type=Path, required=True)
            command.add_argument("--source-id", required=True)
        if name == "import":
            command.add_argument("--kind", required=True, choices=["historical", "gsc", "bing", "yandex", "cms", "routes", "logs", "export"])
            command.add_argument("--captured-at", required=True, help="Original source date YYYY-MM-DD or ISO8601 timestamp with timezone")
            command.add_argument("--coverage", choices=["sample", "complete", "unknown"], default="sample")
            command.add_argument("--url-column")
            command.add_argument("--format", choices=["json", "csv", "txt"])
        if name == "discover":
            command.add_argument("--max-requests", type=int, default=50)
            command.add_argument("--max-depth", type=int, default=1)
            command.add_argument("--max-sitemaps", type=int, default=10)
            command.add_argument("--max-urls", type=int, default=100000)
            command.add_argument("--delay", type=float, default=1.0)
            command.add_argument("--timeout", type=float, default=20)
            command.add_argument("--resume")
        if name == "report":
            command.add_argument("--output", type=Path, required=True)
    return result


def import_dom(store, path, source_id):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or "page_url" not in data or "captured_at" not in data or not isinstance(data.get("links"), list):
        raise ValueError("dom_export_requires_page_url_captured_at_links")
    base = normalize_url(data["page_url"])
    rows, edges = [{"url": base}], []
    for relation, items in [("link", data["links"]), ("canonical", data.get("canonicals", []))]:
        if not isinstance(items, list):
            raise ValueError("dom_links_must_be_lists")
        for item in items:
            url = normalize_url(item, base)
            rows.append({"url": url})
            edges.append((base, url, relation))
    for item in data.get("alternates", []):
        url = normalize_url(item["url"], base)
        rows.append({"url": url})
        edges.append((base, url, "hreflang:" + item.get("hreflang", "")))
    result = store.record_source(rows, source_id=source_id, kind="browser", captured_at=data["captured_at"], coverage="sample", locator=base)
    for source, target, relation in edges:
        store.add_relation(result["run_id"], source, target, relation)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        local_profile = args.data / "profile.json"
        profile = load_profile(args.profile or (local_profile if local_profile.is_file() else (Path(os.environ["SEO_SITE_PROFILE"]) if os.environ.get("SEO_SITE_PROFILE") else DEFAULT_PROFILE)))
        with inventory_lock(args.data):
            store = Inventory(args.data / "inventory.sqlite", profile["allowed_hosts"])
            try:
                if args.command == "import":
                    fmt = args.format or args.file.suffix.lstrip(".").lower()
                    rows = parse_import(args.file.read_bytes(), fmt, args.url_column)
                    result = store.record_source(rows, source_id=args.source_id, kind=args.kind, captured_at=args.captured_at,
                                                 coverage=args.coverage, locator=str(args.file.resolve()))
                elif args.command == "import-dom":
                    result = import_dom(store, args.file, args.source_id)
                elif args.command == "discover":
                    client = HttpClient(profile["allowed_hosts"], delay=args.delay, timeout=args.timeout,
                                        allow_benchmark_alias=profile.get("allow_system_dns_alias", False))
                    runner = Discovery(store, client.get, profile, args.data / "evidence")
                    result = runner.run(max_requests=args.max_requests, max_depth=args.max_depth,
                                        max_sitemaps=args.max_sitemaps, max_urls=args.max_urls, resume=args.resume)
                elif args.command == "reclassify":
                    result = store.reclassify()
                elif args.command == "report":
                    result = write_report(store, args.output)
                else:
                    result = {**store.summary(), "latest_run": latest_run(store)}
            finally:
                store.close()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result.get("status") == "partial" or result.get("rejected", 0) else 0
    except (ValueError, OSError, KeyError, TypeError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
