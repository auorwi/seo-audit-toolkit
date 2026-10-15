"""One-hop GET, pinned public DNS, bounded responses, no cookies or redirects."""

import http.client
import ipaddress
import re
import socket
import ssl
import time
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

from .extract import bounded_decode
from .identity import in_scope, normalize_url, redact_url

CAPTURED_HEADERS = {"content-type", "content-length", "content-encoding", "location", "etag",
    "last-modified", "cache-control", "retry-after", "x-robots-tag", "date", "cf-ray", "x-request-id",
    "x-correlation-id", "link", "refresh"}


@dataclass
class Response:
    url: str
    status: int
    headers: dict
    body: bytes
    headers_all: list | None = None
    captured_header_names: list | None = None


def validate_addresses(addresses, allow_benchmark_alias=False, scheme="https"):
    def allowed(value):
        ip = ipaddress.ip_address(value)
        return ip.is_global or (allow_benchmark_alias and scheme == "https" and ip.version == 4 and ip in ipaddress.ip_network("198.18.0.0/15"))
    if not addresses or not all(allowed(a) for a in addresses):
        raise ValueError("non_public_dns_target")
    return addresses


def safe_headers(headers):
    return dict(safe_header_pairs(list(headers.items())))


def safe_header_pairs(headers):
    result = []
    for key, value in headers:
        key = key.lower()
        if key in CAPTURED_HEADERS:
            if key=='location':value=redact_url(value)
            elif key=='link':value=re.sub(r'<([^>]+)>',lambda m:'<'+redact_url(m.group(1))+'>',value)
            elif key=='refresh':
                value=re.sub(r'(?i)(url\s*=\s*[\"\']?)([^\"\']+)',lambda m:m.group(1)+redact_url(m.group(2)),value)
            result.append((key,value))
    return result


class HttpClient:
    def __init__(self, allowed_hosts, delay=1.0, timeout=20, max_bytes=8_000_000, allow_benchmark_alias=False):
        if allow_benchmark_alias:raise ValueError('benchmark_alias_not_allowed_for_live_collection')
        if delay < 0 or timeout <= 0 or max_bytes <= 0:
            raise ValueError("invalid_network_limits")
        self.allowed_hosts, self.delay, self.timeout, self.max_bytes = allowed_hosts, delay, timeout, max_bytes
        self.last_request = {}
        self.host_delays = {}
        self.allow_benchmark_alias = allow_benchmark_alias

    def set_delay(self, origin, delay):
        self.host_delays[urlsplit(origin).hostname] = max(self.delay, delay)

    def get(self, url):
        url = normalize_url(url)
        if not in_scope(url, self.allowed_hosts):
            raise ValueError("outside_scope_or_sensitive_url")
        p = urlsplit(url)
        port = p.port or (443 if p.scheme == "https" else 80)
        addresses = list(dict.fromkeys(item[4][0] for item in socket.getaddrinfo(p.hostname, port, type=socket.SOCK_STREAM)))
        ip = validate_addresses(addresses, self.allow_benchmark_alias, p.scheme)[0]
        delay = self.host_delays.get(p.hostname, self.delay)
        wait = self.last_request.get(p.hostname, 0) + delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.last_request[p.hostname] = time.monotonic()
        if p.scheme == "https":
            conn = http.client.HTTPSConnection(p.hostname, port, timeout=self.timeout, context=ssl.create_default_context())
        else:
            conn = http.client.HTTPConnection(p.hostname, port, timeout=self.timeout)
        # Keep TLS hostname verification/SNI while connecting only to a validated IP.
        conn._create_connection = lambda address, timeout, source_address=None: socket.create_connection((ip, port), timeout, source_address)
        target = quote(p.path or "/", safe="/%:@!$&'()*+,;=-._~")
        if p.query:
            target += "?" + quote(p.query, safe="%=&?/:@!$'()*+,;~-._")
        try:
            conn.request("GET", target, headers={"User-Agent": "SeoAuditToolkit/0.1", "Accept-Encoding": "gzip", "Accept": "text/html,application/xml,text/plain,*/*;q=0.5"})
            response = conn.getresponse()
            wire_headers = response.getheaders()
            headers = {k.lower(): v for k, v in wire_headers}
            body = response.read(self.max_bytes + 1)
            body = bounded_decode(body, self.max_bytes)
            return Response(url, response.status, headers, body, safe_header_pairs(wire_headers), sorted(CAPTURED_HEADERS))
        finally:
            conn.close()
