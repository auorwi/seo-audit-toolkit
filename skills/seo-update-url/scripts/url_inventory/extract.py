"""Discovery extraction, not SEO verdicts. Uses bounded, DTD-free XML parsing."""

import csv
import gzip
import io
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urlsplit

from .identity import normalize_url


def bounded_decode(body, max_bytes=8_000_000):
    if len(body) > max_bytes:
        raise ValueError("body_too_large")
    if body.startswith(b"\x1f\x8b"):
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(body)) as f:
                body = f.read(max_bytes + 1)
        except (OSError, EOFError) as e:
            raise ValueError("invalid_gzip") from e
    if len(body) > max_bytes:
        raise ValueError("decompressed_body_too_large")
    return body


class _NoDTD(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise ValueError("doctype_not_allowed")


def parse_sitemap(body, max_bytes=8_000_000):
    body = bounded_decode(body, max_bytes)
    try:
        root = ET.fromstring(body, parser=ET.XMLParser(target=_NoDTD()))
    except ET.ParseError as e:
        raise ValueError("invalid_sitemap_xml") from e
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}" if root.tag.startswith("{http://www.sitemaps.org/schemas/sitemap/0.9}") else ""
    kind = root.tag.removeprefix(ns)
    if kind not in {"urlset", "sitemapindex"}:
        raise ValueError("not_a_sitemap")
    result = {"kind": "index" if kind == "sitemapindex" else "urlset", "children": [], "pages": [], "alternates": []}
    item_tag = "sitemap" if kind == "sitemapindex" else "url"
    if any(child.tag != ns + item_tag for child in root):
        raise ValueError("invalid_sitemap_child_structure")
    for item in root.findall(ns + item_tag):
        loc = (item.findtext(ns + "loc") or "").strip()
        url = normalize_url(loc)  # Sitemap locations must be absolute.
        if kind == "sitemapindex":
            result["children"].append(url)
        else:
            result["pages"].append({"url": url, "lastmod": item.findtext(ns + "lastmod")})
            for a in item.findall("{http://www.w3.org/1999/xhtml}link"):
                if a.get("rel", "").lower() == "alternate" and a.get("href"):
                    result["alternates"].append({"url": normalize_url(a.get("href")), "from_url": url, "hreflang": a.get("hreflang", "")})
    return result


class _Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.base = None
        self.refs = []
        self.title = []
        self.in_title = False
        self.noindex = False
        self.robots_directives = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "base" and self.base is None and a.get("href"):
            self.base = a["href"]
        if tag == "title":
            self.in_title = True
        if tag == "meta" and a.get("name", "").lower() in {"robots", "googlebot", "bingbot", "yandex"}:
            name = a["name"].lower()
            directives = [v for v in re.split(r"[,\s]+", a.get("content", "").lower()) if v]
            self.robots_directives.setdefault(name, []).extend(directives)
            self.noindex |= name == "robots" and "noindex" in directives
        if a.get("href") and tag == "a":
            self.refs.append(("links", a["href"], ""))
        if a.get("href") and tag == "link":
            rels = a.get("rel", "").lower().split()
            if "canonical" in rels:
                self.refs.append(("canonicals", a["href"], ""))
            if "alternate" in rels and a.get("hreflang"):
                self.refs.append(("alternates", a["href"], a["hreflang"]))

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)


def parse_html(text, page_url):
    parser = _Links()
    parser.feed(text)
    base = page_url
    if parser.base:
        try:
            base = normalize_url(parser.base, page_url)
        except ValueError:
            pass
    result = {"links": [], "canonicals": [], "alternates": [], "noindex": parser.noindex,
              "robots_directives": parser.robots_directives,
              "title": " ".join("".join(parser.title).split())}
    for kind, href, lang in parser.refs:
        if href.startswith("#") and not href.startswith(("#/", "#!/")):
            continue
        try:
            url = normalize_url(href, base)
        except ValueError:
            continue
        value = {"url": url, "hreflang": lang} if kind == "alternates" else url
        if value not in result[kind]:
            result[kind].append(value)
    return result


def parse_import(body, fmt, url_column=None):
    text = body.decode("utf-8-sig")
    if fmt == "json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError("invalid_json") from e
        if isinstance(data, dict):
            data = next((data[k] for k in ("records", "urls", "rows") if k in data), None)
        if not isinstance(data, list):
            raise ValueError("expected_url_records")
    elif fmt == "csv":
        reader = csv.DictReader(io.StringIO(text))
        known = {"url", "page", "pages", "top pages", "网页", "网址", "页面", "链接"}
        matches = [c for c in (reader.fieldnames or []) if c.strip().lower() in known]
        col = url_column or (matches[0] if len(matches) == 1 else None)
        if not col or col not in (reader.fieldnames or []):
            raise ValueError("specify_url_column")
        data = [{**row, "url": row[col]} for row in reader if row.get(col, "").strip()]
    elif fmt == "txt":
        data = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    else:
        raise ValueError("unsupported_import_format")
    result = []
    for row in data:
        if isinstance(row, str):
            row = {"url": row}
        if not isinstance(row, dict) or not isinstance(row.get("url"), str):
            raise ValueError("record_requires_url")
        # Do not ingest arbitrary exported account data into reports.
        result.append({k: row[k] for k in ("url", "id", "page_type", "family", "group", "source_ids", "coverage_note", "route_family") if k in row})
    return result


def _robots_octets(value,pattern=False):
    """RFC 9309 §2.2.2: compare unreserved escapes as bytes, keep reserved escapes."""
    unreserved="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    def escape(match):
        char=chr(int(match[1],16))
        return char if char in unreserved else '%'+match[1].upper()
    value=re.sub(r'%([0-9A-Fa-f]{2})',escape,value)
    def literal(char):
        if char=='$' or (char=='*' and not pattern):return '%'+format(ord(char),'02X')
        return char if ord(char)<128 else ''.join('%'+format(octet,'02X') for octet in char.encode('utf-8'))
    return ''.join(literal(char) for char in value)


class RobotsPolicy:
    def __init__(self, text, agent="SeoAuditToolkit"):
        groups, agents, rules = [], [], []
        self.sitemaps = []
        self.delay = 0.0
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, value = [s.strip() for s in line.split(":", 1)]
            key = key.lower()
            if key == "sitemap" and value:
                try:
                    self.sitemaps.append(normalize_url(value))
                except ValueError:
                    pass
            elif key == "user-agent":
                if rules:
                    groups.append((agents, rules))
                    agents, rules = [], []
                agents.append(value.lower())
            elif key in {"allow", "disallow", "crawl-delay"} and agents:
                rules.append((key, value))
        if agents:
            groups.append((agents, rules))
        best, selected = -1, []
        for agents, rules in groups:
            weights = [0 if a == "*" else len(a) for a in agents if a == "*" or a in agent.lower()]
            if not weights:
                continue
            weight = max(weights)
            if weight > best:
                best, selected = weight, list(rules)
            elif weight == best:
                selected.extend(rules)
        self.rules = []
        for key, value in selected:
            if key == "crawl-delay":
                try:
                    self.delay = max(self.delay, float(value))
                except ValueError:
                    pass
            elif value:
                end = value.endswith("$")
                value = _robots_octets(value[:-1] if end else value,pattern=True)
                pattern = re.escape(value).replace(r"\*", ".*")
                self.rules.append((re.compile("^" + pattern + ("$" if end else "")), len(value.encode("utf-8")), key == "allow"))

    def allowed(self, url):
        p = urlsplit(url)
        target = _robots_octets(p.path + ("?" + p.query if p.query else ""))
        matches = [(length, allow) for pattern, length, allow in self.rules if pattern.search(target)]
        return max(matches)[1] if matches else True
