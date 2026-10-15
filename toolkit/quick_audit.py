"""Bounded initial-HTML audit. Browser and webmaster results are separate capabilities."""
import csv
import hashlib
import http.client
import json
import re
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/seo-update-url/scripts'))
from url_inventory.extract import RobotsPolicy, parse_sitemap, _robots_octets
from url_inventory.identity import normalize_url, redact_url
from url_inventory.network import HttpClient, safe_headers
from crawlability.site import _allowed, get_profile
from crawlability.html_compat import HTMLParser


def now():
    return datetime.now(timezone.utc).isoformat()


def resolve_url(value, base=None):
    """Resolve untrusted HTTP URLs without letting malformed markup abort a run."""
    try:
        return normalize_url(value, base)
    except (ValueError, TypeError, UnicodeError):
        return None


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titles, self.h1, self.links, self.canonicals = [], [], [], []
        self.descriptions, self.robots, self.jsonld = [], [], []
        self.base, self.active, self.script = None, None, None
        self.lang = ''
        self.images_without_alt = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in {'title', 'h1'}:
            self.active = []
            (self.titles if tag == 'title' else self.h1).append(self.active)
        if tag == 'html':
            self.lang = a.get('lang', '')
        if tag == 'base' and self.base is None and a.get('href'):
            self.base = a['href']
        if tag == 'meta' and a.get('name', '').lower() == 'description':
            self.descriptions.append(a.get('content', ''))
        if tag == 'meta' and a.get('name', '').lower() in {'robots', 'googlebot', 'bingbot', 'yandex'}:
            self.robots.append({'agent': a['name'].lower(), 'value': a.get('content', '')})
        if tag == 'link' and 'canonical' in a.get('rel', '').lower().split():
            self.canonicals.append(a.get('href', ''))
        if tag == 'a' and a.get('href'):
            self.links.append(a['href'])
        if tag == 'img' and 'alt' not in a:
            self.images_without_alt += 1
        if tag == 'script' and a.get('type', '').lower() == 'application/ld+json':
            self.script = []
            self.jsonld.append(self.script)

    def handle_endtag(self, tag):
        if tag in {'title', 'h1'}:
            self.active = None
        if tag == 'script':
            self.script = None

    def handle_data(self, data):
        if self.active is not None:
            self.active.append(data)
        if self.script is not None:
            self.script.append(data)


def page_findings(profile, url, html, headers, evidence):
    parser = Page()
    parser.feed(html)
    parser.close()
    title = [' '.join(''.join(t).split()) for t in parser.titles]
    headings = [' '.join(''.join(t).split()) for t in parser.h1]
    findings = []

    def add(rule, detail, classification='review'):
        identity = json.dumps([profile['site'], rule, url], ensure_ascii=False)
        findings.append({'issue_id': hashlib.sha256(identity.encode()).hexdigest()[:24],
                         'rule': rule, 'url': url, 'classification': classification,
                         'detail': detail, 'observed_at': evidence['captured_at'], 'evidence': evidence})

    if not any(title):
        add('missing_title', 'No nonempty title in the initial HTML.')
    elif len(title) > 1:
        add('multiple_titles', 'Multiple title elements in the initial HTML.')
    if not any(v.strip() for v in parser.descriptions):
        add('missing_description', 'No nonempty meta description in the initial HTML; check rendered content and page intent.')
    if not any(headings):
        add('missing_h1', 'No nonempty H1 in the initial HTML; review rendered headings and page structure.')
    if len(parser.canonicals) > 1:
        add('multiple_canonicals', 'Multiple canonical link elements; confirm intended canonical.')
    diagnostics = []
    base = resolve_url(parser.base, url) if parser.base else url
    if base is None:
        diagnostics.append('invalid_base')
        base = url
    canonical_targets = []
    for canonical in parser.canonicals:
        target = resolve_url(canonical, base)
        canonical_targets.append(redact_url(target) if target else '[invalid URL]')
        if not target:
            add('invalid_canonical', 'A canonical element has an empty or invalid target.')
        elif not _allowed(target, profile):
            add('canonical_outside_scope', 'Canonical points outside this audit scope; it may be intentional and was not fetched.')
    directives = [row['value'] for row in parser.robots] + [headers.get('x-robots-tag', '')]
    if any(re.search(r'(?i)(?:^|[,\s:])(?:noindex|none)(?:$|[,\s])', v) for v in directives):
        add('noindex_declared', 'A noindex/none directive is declared. Confirm whether this page should be indexed.')
    for script in parser.jsonld:
        try:
            json.loads(''.join(script), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
        except (ValueError, TypeError):
            add('invalid_jsonld_syntax', 'An application/ld+json block is not valid JSON.', 'confirmed')
            break
    if parser.images_without_alt:
        add('images_without_alt', str(parser.images_without_alt) + ' image elements lack an alt attribute; assess their purpose in rendered context.')
    links = []
    for value in parser.links:
        if re.match(r'(?i)^(?:mailto|tel|javascript|data):', value):
            continue
        target = resolve_url(value, base)
        if target:
            links.append(target)
        else:
            diagnostics.append('invalid_link')
    return {'title': title, 'descriptions': parser.descriptions, 'h1': headings,
            'lang': parser.lang, 'canonicals': canonical_targets,
            'jsonld_blocks': len(parser.jsonld), 'robots': parser.robots}, findings, links, diagnostics


def audit(profile, output, *, max_pages=10, max_requests=40, delay=1.0, timeout=20,
          fetch=None, follow_links=True):
    """Use the supplied scope; live HttpClient also requires its matching activated profile."""
    if not isinstance(max_pages, int) or not 1 <= max_pages <= 10000:
        raise ValueError('max-pages must be between 1 and 10000')
    if not isinstance(max_requests, int) or not 1 <= max_requests <= 100000:
        raise ValueError('max-requests must be between 1 and 100000')
    if delay < 0 or timeout <= 0:
        raise ValueError('Invalid network timing')
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output directory must be new or empty')
    seeds = profile.get('seeds', [])
    if not seeds or any(not _allowed(u, profile) for u in seeds):
        raise ValueError('Profile needs in-scope public seed URLs')
    if fetch is None:
        try:
            active = get_profile()
        except ValueError:
            raise ValueError('Live HTTP requires a matching activated SEO_SITE_PROFILE; use the audit CLI --profile') from None
        keys = ('site', 'allowed_hosts', 'allowed_schemes', 'test_only_allow_loopback', 'fixture_port')
        defaults = {'allowed_schemes': ['http', 'https'], 'test_only_allow_loopback': False}
        if any(active.get(k, defaults.get(k)) != profile.get(k, defaults.get(k)) for k in keys):
            raise ValueError('Live HTTP requires a matching activated SEO_SITE_PROFILE; use the audit CLI --profile')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'evidence').mkdir(exist_ok=True)
    client = HttpClient(profile['allowed_hosts'], delay=delay, timeout=timeout) if fetch is None else None
    fetch = client.get if client else fetch
    report = {'schema_version': 1, 'kind': 'initial_html_quick_audit', 'site': profile['site'],
              'at': now(), 'status': 'completed_scoped_http_audit', 'pages': [], 'findings': [],
              'gaps': [], 'requests': [], 'sitemaps': [],
              'coverage': {'browser_rendering': False, 'webmaster_platforms': False,
                           'full_specialist_audits': False, 'limits_reached': False,
                           'max_pages': max_pages, 'max_requests': max_requests,
                           'page_limit_counts': 'page requests, including redirects and errors',
                           'full_site_coverage': 'unknown'}}
    policies, rate_limited, seen, known_sitemaps = {}, set(), set(), set()
    queue = deque((normalize_url(u), 'page') for u in seeds)
    sitemap_queue = deque((normalize_url(u), 'sitemap') for u in profile.get('sitemaps', []))
    queries = {}
    page_count = 0
    redirect_edges = {}
    successful = set()

    def gap(url, reason):
        report['gaps'].append({'url': redact_url(url), 'reason': reason})

    def get(url, kind):
        if len(report['requests']) >= max_requests:
            report['coverage']['limits_reached'] = True
            gap(url, 'request_budget')
            return None
        record = {'url': redact_url(url), 'kind': kind, 'captured_at': now()}
        report['requests'].append(record)
        try:
            raw = fetch(url)
            value = raw if isinstance(raw, dict) else vars(raw)
            headers = safe_headers({k.lower(): v for k, v in value['headers'].items()})
            body = value['body']
            if not isinstance(body, bytes) or len(body) > 8_000_000:
                raise ValueError('Invalid or oversized body')
            name = 'evidence/' + str(len(report['requests'])) + '.body'
            (output / name).write_bytes(body)
            evidence = {'path': name, 'sha256': hashlib.sha256(body).hexdigest(),
                        'bytes': len(body), 'captured_at': record['captured_at']}
            record.update(status=value['status'], headers=headers, evidence=evidence)
            return {'status': value['status'], 'headers': headers, 'body': body, 'evidence': evidence}
        except (OSError, ValueError, http.client.HTTPException) as error:
            record['error'] = type(error).__name__
            gap(url, 'request_failed:' + type(error).__name__)
            return None

    def policy(url):
        p = urlsplit(url)
        origin = p.scheme + '://' + p.netloc
        if origin in policies:
            return policies[origin]
        target, redirects = origin + '/robots.txt', set()
        result = None
        for _ in range(6):
            if target in redirects:
                break
            redirects.add(target)
            response = get(target, 'robots')
            if response is None:
                break
            status = response['status']
            if status in {301, 302, 303, 307, 308}:
                location = response['headers'].get('location')
                if not location:
                    break
                target = resolve_url(location, target)
                if target is None:
                    gap(url, 'invalid_redirect')
                    break
                if not _allowed(target, profile):
                    break
                continue
            if status in {404, 410}:
                result = RobotsPolicy('', agent='SeoAuditToolkit')
            elif status == 200:
                text = response['body'].decode('utf-8-sig', errors='replace')
                if not text.lstrip().lower().startswith(('<html', '<!doctype html')):
                    result = RobotsPolicy(text, agent='SeoAuditToolkit')
            break
        policies[origin] = result
        if result is None:
            gap(url, 'robots_unavailable')
        else:
            if client:
                client.set_delay(origin, result.delay)
            for sitemap in result.sitemaps:
                if _allowed(sitemap, profile):
                    sitemap_queue.append((sitemap, 'sitemap'))
        return result

    while queue or sitemap_queue:
        # Duplicate discoveries do not represent outstanding coverage or consume limits.
        for pending in (queue, sitemap_queue):
            while pending and pending[0] in seen:
                pending.popleft()
        if not queue and not sitemap_queue:
            break
        if len(report['requests']) >= max_requests:
            report['coverage']['limits_reached'] = True
            break
        if queue and page_count >= max_pages:
            report['coverage']['limits_reached'] = True
        if queue and page_count < max_pages:
            url, kind = queue.popleft()
        elif sitemap_queue:
            url, kind = sitemap_queue.popleft()
        else:
            break
        if (url, kind) in seen:
            continue
        seen.add((url, kind))
        if not _allowed(url, profile):
            continue
        parsed = urlsplit(url)
        if parsed.hostname in rate_limited:
            gap(url, 'host_rate_limited')
            continue
        if kind == 'page':
            # Exclusion regexes match the same normalized URI path used by robots.
            path = _robots_octets(parsed.path)
            if any(re.search(pattern, path) for pattern in profile.get('excluded_path_patterns', [])):
                continue
            if re.search(r'(?i)\.(?:png|jpe?g|gif|svg|webp|pdf|zip|exe|dmg|mp4|js|css|woff2?)$', path):
                continue
            if parsed.query:
                key = (parsed.netloc, path)
                if queries.get(key, 0) >= profile.get('query_variants_per_path', 2):
                    gap(url, 'query_variant_limit')
                    continue
                queries[key] = queries.get(key, 0) + 1
        elif len(known_sitemaps) >= 10:
            gap(url, 'sitemap_limit')
            report['coverage']['limits_reached'] = True
            continue
        robots = policy(url)
        if robots is None:
            continue
        if not robots.allowed(url):
            gap(url, 'robots_disallow')
            continue
        if len(report['requests']) >= max_requests:
            # robots retrieval may have consumed the final request slot.
            (queue if kind == 'page' else sitemap_queue).appendleft((url, kind))
            report['coverage']['limits_reached'] = True
            break
        if kind == 'page':
            page_count += 1
        else:
            known_sitemaps.add(url)
        response = get(url, kind)
        if response is None:
            continue
        status, headers = response['status'], response['headers']
        if status == 429:
            rate_limited.add(parsed.hostname)
        if status in {301, 302, 303, 307, 308}:
            location = headers.get('location')
            target = resolve_url(location, url) if location else None
            if location and target is None:
                gap(url, 'invalid_redirect')
            elif target and _allowed(target, profile):
                source, destination = (url, kind), (target, kind)
                redirect_edges[source] = destination
                chain, current = {source}, destination
                while current in redirect_edges and current not in chain:
                    chain.add(current)
                    current = redirect_edges[current]
                if current in chain:
                    gap(url, 'redirect_loop')
                else:
                    (queue if kind == 'page' else sitemap_queue).append(destination)
            else:
                gap(url, 'redirect_outside_scope' if target else 'redirect_without_location')
            continue
        if status != 200:
            gap(url, 'http_' + str(status))
            continue
        if kind == 'sitemap':
            try:
                data = parse_sitemap(response['body'])
                report['sitemaps'].append({'url': url, 'kind': data['kind'], 'entries': len(data['pages']),
                                           'children': len(data['children']), 'evidence': response['evidence']})
                successful.add((url, kind))
                for child in data['children'][:100]:
                    sitemap_queue.append((child, 'sitemap'))
                if follow_links:
                    for item in data['pages'][:10000]:
                        queue.append((item['url'], 'page'))
                    if len(data['pages']) > 10000:
                        gap(url, 'sitemap_entry_queue_limit')
            except ValueError:
                gap(url, 'invalid_sitemap_xml')
            continue
        media_type = headers.get('content-type', '').split(';', 1)[0].strip().lower()
        if media_type not in {'text/html', 'application/xhtml+xml'}:
            gap(url, 'non_html_or_unknown_content_type')
            continue
        encoding = re.search(r'charset\s*=\s*["\']?([\w-]+)', headers.get('content-type', ''), re.I)
        try:
            html = response['body'].decode(encoding.group(1) if encoding else 'utf-8', errors='replace')
        except LookupError:
            html = response['body'].decode('utf-8', errors='replace')
        fields, findings, links, diagnostics = page_findings(profile, url, html, headers, response['evidence'])
        for reason in set(diagnostics):
            gap(url, reason)
        report['pages'].append({'url': url, 'status': status, 'fields': fields, 'evidence': response['evidence']})
        successful.add((url, kind))
        report['findings'].extend(findings)
        if follow_links:
            for link in links[:10000]:
                if not urlsplit(link).fragment and _allowed(link, profile):
                    if len(queue) < 10000:
                        queue.append((normalize_url(link), 'page'))
                    else:
                        gap(url, 'link_queue_limit')
                        break
    for source, destination in redirect_edges.items():
        chain = {source}
        while destination in redirect_edges and destination not in chain:
            chain.add(destination)
            destination = redirect_edges[destination]
        if destination not in chain and destination not in successful:
            gap(source[0], 'redirect_unresolved_target')
    report['coverage'].update(page_requests=page_count, html_pages=len(report['pages']),
                              http_requests=len(report['requests']), queued=len(queue) + len(sitemap_queue))
    if report['gaps'] or report['coverage']['limits_reached']:
        report['status'] = 'partial'
    write_report(report, output)
    return report


def write_report(report, output):
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    fields = ['issue_id', 'rule', 'url', 'classification', 'detail', 'observed_at', 'evidence_path']
    with (output / 'issues.csv').open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for finding in report['findings']:
            row = {k: finding[k] for k in fields[:-1]}
            row['evidence_path'] = finding['evidence']['path']
            writer.writerow({k: ("'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@', '\t', '\r')) else v) for k, v in row.items()})
    lines = ['# SEO initial HTML audit: ' + report['site'], '', 'Captured: ' + report['at'],
             'Status: ' + report['status'], '',
             'This report covers public HTTP responses and initial HTML. Browser rendering, search engine indexing,',
             'CWV, business correctness and full specialist audits have not been verified. Full-site coverage is unknown.', '',
             'HTML pages: ' + str(len(report['pages'])) + '; HTTP requests: ' + str(len(report['requests'])),
             '', '## Observations requiring review', '']
    for f in report['findings']:
        safe_url = f['url'].replace('`', '%60')
        lines.append('- `' + f['rule'] + '` — ' + f['detail'] + ' URL: `' + safe_url + '`; evidence: `' + f['evidence']['path'] + '`.')
    if not report['findings']:
        lines.append('No findings from the checks that ran. This is not a full-site pass.')
    lines.extend(['', '## Coverage gaps', ''])
    for g in report['gaps']:
        lines.append('- ' + g['reason'] + ': `' + g['url'].replace('`', '%60') + '`')
    if report['coverage']['limits_reached']:
        lines.append('- A configured limit was reached. Unvisited URLs are not evaluated.')
    (output / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
